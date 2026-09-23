/**
 * Queue UI adapter. Local journal is authoritative; never resubmit an unknown attempt.
 * Sends each group in storage-sized chunks and, when enabled, moves to the next Chrome profile
 * when Flow answers "out of quota" with no image (see profile-rotation.mjs).
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {AttemptStore} from './attempt-store.mjs';
import {findToolFrame, toolUrl, safeResults} from './controller.mjs';
import {DEFAULT_FAILURE_PATTERNS,classifyFailure,itemErrorText,stateErrorText,loadRotationPolicy,ProfileLedger,nextProfile,toolUrlFor,referencesFor,appendSwitchLog} from './profile-rotation.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
function reference(file,mediaId) {
 if(!file)return null;
 if(!mediaId)throw Error('REFERENCE_MEDIA_ID_REQUIRED');
 const bytes=fs.readFileSync(file), ext=path.extname(file).toLowerCase();
 const mimeType={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'}[ext];
 if(!mimeType)throw Error('REFERENCE_FORMAT_UNSUPPORTED');
 return {mediaId,base64:bytes.toString('base64'),mimeType,name:path.basename(file),sha256:hash(bytes)};
}
const cfg = fs.existsSync(path.resolve(here, '../../config.json')) ? JSON.parse(fs.readFileSync(path.resolve(here, '../../config.json'), 'utf8')) : {};
const configuredModel = cfg.flow_model || 'Nano Banana 2';
const modelLabel = configuredModel.startsWith('🍌') ? configuredModel : `🍌 ${configuredModel}`;
const CANONICAL_NOTE='Match the attached canonical character and scene references.';

export function prepareRequests(specs) {
 if(!Array.isArray(specs)||!specs.length||specs.length>4)throw Error('QUEUE_SIZE_1_TO_4_REQUIRED');
 if(new Set(specs.map(s=>s.testCase)).size!==specs.length)throw Error('DUPLICATE_REQUEST_ID');
 return specs.map(s=>{
  if(!/^[\w-]+$/.test(s.testCase)||!s.prompt||!['9:16','16:9'].includes(s.ratio))throw Error('INVALID_QUEUE_REQUEST');
  const character=reference(s.characterRefPath,s.charMediaId),base=reference(s.baseRefPath,s.baseMediaId);
  // A request without a character must say so; a missing reference is never silently allowed.
  if(!character&&s.noCharacter!==true)throw Error('CHARACTER_REFERENCE_REQUIRED');
  if(character&&s.noCharacter===true)throw Error('CHARACTER_REFERENCE_CONFLICT');
  const styleNote=s.styleNote||CANONICAL_NOTE;
  // Extra identity keys only when they differ from the historical canonical request, so old journals still match.
  const extra={...(character?{}:{noCharacter:true}),...(styleNote===CANONICAL_NOTE?{}:{styleNote})};
  return {spec:s,character,base,styleNote,identity:{toolUrl,id:s.testCase,prompt:s.prompt,ratio:s.ratio,preserve:s.preserve||'',change:s.change||'',literalText:s.literalText||'',model:configuredModel,references:[character,base].filter(Boolean).map(({mediaId,sha256})=>({mediaId,sha256})),outDir:path.resolve(s.outDir),...extra}};
 });
}

/* ---------------------------------------------------------------------------------------------
 * Tool storage budget.
 *
 * The tool keeps every result's base64 in one localStorage value. Chrome allows about 5 MiB of
 * UTF-16 text per origin: measured 2026-09-23, a 5,166,163-char state held 22 images and the 23rd
 * image was generated but "Persistence failure after result" (the tool could not save it).
 * Observed result sizes: mean 164-231 K chars, largest 327,132 chars; request config up to ~5 K.
 * Before each dispatch the runner measures the whole origin, estimates one image generously,
 * and sends only as many images as fit under 80 % of the quota. When the rest does not fit,
 * it compacts (backup, drop, reload) — allowed only when every item is safely on disk.
 * ------------------------------------------------------------------------------------------- */
export const LOCAL_STORAGE_QUOTA_CHARS=5242880;
export const STORAGE_BUDGET_FRACTION=0.8;
export const CHARS_PER_IMAGE_FLOOR=360000;
/** Chars one more image will need: never below the floor, and 15 % above the largest item seen. */
export function estimateCharsPerImage(items=[]) {
 const largest=Math.max(0,...items.filter(i=>i?.hasResult||i?.result?.base64).map(i=>i.itemChars??JSON.stringify(i).length));
 return Math.max(CHARS_PER_IMAGE_FLOOR,Math.ceil(largest*1.15));
}
/** How many more images fit in the tool's storage now. */
export function storageCapacity({usedChars,perImageChars,quotaChars=LOCAL_STORAGE_QUOTA_CHARS,fraction=STORAGE_BUDGET_FRACTION}) {
 return Math.max(0,Math.floor((quotaChars*fraction-usedChars)/perImageChars));
}

const TOOL_STATE_KEY='VP_LAB_STATE_V2';
const NOT_PRODUCED_EXCLUDED=new Set(['captcha','login','storage']);

/**
 * Flow answered and the tool recorded an error with no image and no media id: nothing was produced.
 * Never true for a storage failure (the image was generated, the tool could not save it) or for a
 * CAPTCHA / sign-in answer: those stop the queue and need an operator.
 */
export function noMedia(item,patterns=DEFAULT_FAILURE_PATTERNS) {
 if(!['UNKNOWN','FAILED'].includes(item?.status)||item.mediaId||item.result?.base64||item.hasResult)return false;
 const text=itemErrorText(item);
 return Boolean(text)&&!NOT_PRODUCED_EXCLUDED.has(classifyFailure(text,patterns));
}

/** One scan of every journal: last state by the tool's queue id, and which profile produced each media id. */
export function journalIndex(directory) {
 const byQueueId=new Map(),owners=new Map();
 for(const name of fs.existsSync(directory)?fs.readdirSync(directory).filter(x=>x.endsWith('.ndjson')):[]) {
  const events=fs.readFileSync(path.join(directory,name),'utf8').split('\n').filter(Boolean).map(line=>JSON.parse(line));
  const submission=events.find(e=>e.event==='submitting');
  if(submission?.queueId)byQueueId.set(submission.queueId,events.filter(e=>e.state).at(-1)?.state);
  const generated=events.find(e=>e.event==='generated');
  if(generated?.mediaId&&submission?.profile)owners.set(generated.mediaId,submission.profile);
 }
 return {byQueueId,owners};
}
/** Last known state of every journaled request, by the tool's queue id. */
export function journalByQueueId(directory) {return journalIndex(directory).byQueueId;}

/** Items the tool state may drop: saved to disk by us, answered with no media, or explicitly released (sent, never collected). */
export function toolStateBlockers(queue,journal,release=[]) {
 return (queue||[]).filter(item=>{
  const known=journal.get(item.id);
  if(['collected','accepted','failed_no_media'].includes(known))return false;
  if(noMedia(item)&&['submitting','unknown'].includes(known))return false;  // finished with no output: nothing to lose
  return !(release.includes(item.id)&&['submitting','unknown'].includes(known));
 }).map(item=>item.id);
}

/** Back up the whole tool state, drop it and reload the tool. Refuses while any item is not safely on disk. */
export async function resetToolState(page,store,{release=[],reason='localStorage near its limit',profile=null}={}) {
 let frame=await findToolFrame(page);
 const raw=await frame.evaluate(key=>localStorage.getItem(key)||'{}',TOOL_STATE_KEY);
 const blockers=toolStateBlockers(JSON.parse(raw).queue,journalByQueueId(store.directory),release);
 if(blockers.length)throw Error('TOOL_STATE_HAS_UNSAVED_ITEMS: '+blockers.join(','));
 const folder=path.join(safeResults(),'tool-state');fs.mkdirSync(folder,{recursive:true});
 fs.writeFileSync(path.join(folder,`${Date.now()}.json`),JSON.stringify({at:new Date().toISOString(),reason,release,profile,state:raw}),{flag:'wx'});
 await frame.evaluate(key=>localStorage.removeItem(key),TOOL_STATE_KEY);
 await page.reload({waitUntil:'domcontentloaded'});
 frame=await findToolFrame(page);
 await frame.getByRole('button',{name:'Initialize Generation',exact:true}).waitFor({timeout:30000});
 const after=JSON.parse(await frame.evaluate(key=>localStorage.getItem(key)||'{}',TOOL_STATE_KEY));
 if(after.status==='UNKNOWN'||(after.queue||[]).length)throw Error('TOOL_STATE_RESET_FAILED');
 return frame;
}

/**
 * The browser side of one tool tab. Snapshots carry no image data (only sizes and flags), so
 * polling does not copy megabytes of base64 over CDP every half second; a result is read once.
 */
export function playwrightDriver(page) {
 let frame=null;
 const tool=async()=>frame||(frame=await findToolFrame(page));
 return {
  url:()=>page.url(),
  async snapshot() {
   return (await tool()).evaluate(key=>{
    const raw=localStorage.getItem(key)||'{}';let used=0;
    for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);used+=k.length+(localStorage.getItem(k)||'').length;}
    const s=JSON.parse(raw);
    return {status:s.status??null,stateChars:raw.length,usedChars:used,
     error:s.error??null,errorMessage:s.errorMessage??null,pauseReason:s.pauseReason??null,lastError:s.lastError??null,
     items:(s.queue||[]).map(i=>({id:i.id,status:i.status,mediaId:i.mediaId||null,error:i.error??null,errorMessage:i.errorMessage??null,
      hasResult:Boolean(i.result?.base64),itemChars:JSON.stringify(i).length,topic:i.config?.topic??null,aspectRatio:i.config?.aspectRatio??null,
      characterRefMediaId:i.characterRefMediaId??null,baseImageMediaId:i.baseImageMediaId??null,timestamps:i.timestamps??null}))};
   },TOOL_STATE_KEY);
  },
  async item(id) {
   return (await tool()).evaluate(([key,id])=>(JSON.parse(localStorage.getItem(key)||'{}').queue||[]).find(i=>i.id===id)||null,[TOOL_STATE_KEY,id]);
  },
  /** Fill the form for one request and add it to the tool's queue. Adds, never starts. */
  async enqueue(r,refs) {
   const f=await tool();
   const plain=ref=>ref&&{mediaId:ref.mediaId,base64:ref.base64,mimeType:ref.mimeType,name:ref.name,sha256:ref.sha256};
   await f.evaluate(({character,base})=>{
    const el=document.getElementById('character-selector');
    let fiber=el?.[Object.keys(el).find(k=>k.startsWith('__reactFiber$'))];
    while(fiber&&!(typeof fiber.type==='function'&&fiber.type.name==='App'))fiber=fiber.return;
    let h=fiber?.memoizedState;
    while(h&&!(h.memoizedState?.topic&&h.queue?.dispatch))h=h.next;
    if(!h?.next?.next?.queue?.dispatch)throw Error('REFERENCE_HOOK_NOT_FOUND');
    h.next.queue.dispatch(base);h.next.next.queue.dispatch(character);
   },{character:plain(refs.character),base:plain(refs.base)});
   const clear=f.getByRole('button',{name:'Clear Character',exact:true});
   if(refs.character)await clear.waitFor();
   else{await f.waitForTimeout(300);if(await clear.count())throw Error('CHARACTER_SLOT_NOT_EMPTY');}
   const boxes=f.getByRole('textbox');
   await boxes.nth(0).fill(r.spec.prompt);await boxes.nth(1).fill(r.styleNote);
   await boxes.nth(2).fill(r.spec.preserve||'');await boxes.nth(3).fill(r.spec.change||'');await boxes.nth(4).fill(r.spec.literalText||'');
   await f.getByRole('button',{name:r.spec.ratio,exact:true}).click();
   await f.getByRole('combobox').nth(2).selectOption({label:modelLabel});
   const before=await this.snapshot();
   await f.getByRole('button',{name:'Initialize Generation',exact:true}).click();
   return (await this.snapshot()).items.filter(i=>!before.items.some(p=>p.id===i.id));
  },
  async setWorkers() {await (await tool()).getByRole('combobox').nth(3).selectOption({label:'4 Workers'});},
  async start() {await (await tool()).getByRole('button',{name:'Start Queue',exact:true}).click();},
  async reset(store,options) {frame=await resetToolState(page,store,options);},
 };
}

/** A request sent again after its attempt was answered "out of quota" with no image. */
export function resendIdentity(identity,n) {return n?{...identity,resend:n}:identity;}
const isQuotaNoMedia=a=>a.state==='failed_no_media'&&a.events.at(-1)?.evidence?.classification==='quota';
/** The attempt that currently stands for a request: follows quota resends, at most `limit` of them. */
export function resolveChain(store,identity,limit) {
 let attempt=store.prepare(identity),resend=0;
 while(isQuotaNoMedia(attempt)&&resend<limit){resend++;attempt=store.prepare(resendIdentity(identity,resend));}
 return {attempt,resend};
}

export async function runQueue(specs,bound,deps={}) {
 try { return await executeQueue(specs,bound,deps); }
 catch(error) {
  // Only report not-submitted when durable records prove the standing attempt of every request was never dispatched.
  let notSubmitted=false;
  try {
   const requests=prepareRequests(specs),store=deps.store||new AttemptStore(path.join(safeResults(),'production-attempts'));
   const limit=(deps.policy||loadRotationPolicy()).priority.length;
   notSubmitted=requests.every(r=>resolveChain(store,r.identity,limit).attempt.state==='prepared');
  } catch {}
  return {status:'blocked',reason:error.message,generationSubmitted:!notSubmitted};
 }
}

const currentProfile=(bound,policy)=>bound.profile||(bound.identity?.observedProfile?path.basename(bound.identity.observedProfile):policy.home);

export async function executeQueue(specs,bound,deps={}) {
 const requests=prepareRequests(specs);
 const store=deps.store||new AttemptStore(path.join(safeResults(),'production-attempts'));
 const policy=deps.policy||loadRotationPolicy();
 const ledger=deps.ledger||new ProfileLedger(path.join(safeResults(),'profile-exhaustion.json'));
 const switchLog=deps.switchLog||path.join(safeResults(),'profile-switches.ndjson');
 const makeDriver=deps.driver||(b=>playwrightDriver(b.page));
 const now=deps.now||(()=>new Date());
 const pollMs=deps.pollMs??500,itemTimeoutMs=deps.itemTimeoutMs??180000;
 const limit=policy.priority.length;
 const chains=requests.map(r=>resolveChain(store,r.identity,limit));
 // A group already sent is never sent again: return what the journal holds, per request.
 if(chains.every(c=>c.attempt.state!=='prepared'))return collectResults(store,chains,requests);
 // A standing attempt that may have reached Flow without a known outcome blocks the whole group.
 if(chains.some(c=>['submitting','unknown'].includes(c.attempt.state)))throw Error('FLOW_RECONCILIATION_REQUIRED: existing attempt; no resubmission');
 const needsOwners=requests.some(r=>r.character||r.base);
 const owners=needsOwners?journalIndex(store.directory).owners:new Map();

 let pending=chains.map((c,i)=>c.attempt.state==='prepared'?i:-1).filter(i=>i>=0);
 let profile=currentProfile(bound,policy),driver=null,dispatched=false,started=null;
 const failed=new Map(),switches=[];
 // No further dispatch in this call. Before anything was sent the whole call fails as not submitted;
 // afterwards each request not yet sent is reported as such (its journal still reads prepared).
 const stop=reason=>{
  if(!dispatched)throw Error(reason);
  for(const i of pending)failed.set(i,`FLOW_NOT_SUBMITTED: ${reason}`);
  pending=[];
 };
 while(pending.length) {
  // 1. Never dispatch on a profile known to be out of image quota.
  if(ledger.isExhausted(profile,now())) {
   const until=ledger.entry(profile)?.resetAt;
   if(!policy.enabled){stop(`FLOW_PROFILE_QUOTA_EXHAUSTED: ${profile} until ${until}; automatic_account_switching is off`);break;}
   const target=nextProfile(policy,ledger,profile,now());
   if(!target) {
    appendSwitchLog(switchLog,{event:'all_exhausted',from:profile,requests:pending.map(i=>requests[i].spec.testCase)});
    stop(`FLOW_QUOTA_ALL_PROFILES_EXHAUSTED: no configured profile left in ${JSON.stringify(policy.priority)}; ${profile} resets ${until}`);break;
   }
   if(typeof bound.switchProfile!=='function'){stop('PROFILE_SWITCH_UNAVAILABLE: session cannot switch profiles');break;}
   const record={event:'switch',from:profile,to:target,reason:'quota',exhausted:ledger.entry(profile),requests:pending.map(i=>requests[i].spec.testCase)};
   try {bound=await bound.switchProfile(target,toolUrlFor(policy,target));}
   catch(error) {
    appendSwitchLog(switchLog,{...record,event:'switch_failed',error:error.message});
    stop(`PROFILE_SWITCH_FAILED: ${error.message}`);break;
   }
   switches.push(appendSwitchLog(switchLog,{...record,observedProfile:bound.identity?.observedProfile||null,toolUrl:bound.toolUrl||null}));
   profile=target;driver=null;
   continue;
  }
  driver||=await makeDriver(bound);
  const expectedUrl=bound.toolUrl||toolUrlFor(policy,profile)||toolUrl;
  if(!driver.url().startsWith(expectedUrl)){stop('WRONG_TOOL_URL');break;}
  // 2. CAPTCHA or sign-in anywhere in the tool: hard stop, never worked around.
  let snap=await driver.snapshot();
  const hard=[stateErrorText(snap),...snap.items.map(itemErrorText)].find(t=>['captcha','login'].includes(classifyFailure(t,policy.patterns)));
  if(hard){stop(`FLOW_CAPTCHA_OR_SIGN_IN_REQUIRED: ${hard}`);break;}
  // 3. Storage: send only what fits; compact first when the whole remainder does not fit.
  let perImage=estimateCharsPerImage(snap.items),fits=storageCapacity({usedChars:snap.usedChars,perImageChars:perImage});
  if(snap.status==='UNKNOWN'||fits<pending.length) {
   try {
    await driver.reset(store,{reason:snap.status==='UNKNOWN'?'tool latched UNKNOWN':`storage: ${snap.usedChars} chars used, ${pending.length} more need ${pending.length*perImage}`,profile});
    snap=await driver.snapshot();perImage=estimateCharsPerImage(snap.items);
    fits=storageCapacity({usedChars:snap.usedChars,perImageChars:perImage});
   } catch(error) {
    // Items not yet on disk keep the tool as it is; still usable only if some room is left and nothing latched it.
    if(snap.status==='UNKNOWN'||fits===0){stop(error.message);break;}
   }
  }
  if(snap.status==='UNKNOWN'||snap.items.some(i=>!['COMPLETED','ACCEPTED'].includes(i.status))){stop('UNRESOLVED_FLOW_QUEUE');break;}
  if(fits===0){stop(`TOOL_STORAGE_BUDGET_EXHAUSTED: ${snap.usedChars} chars used after compaction; other data fills the tool's storage`);break;}
  // 4. References this profile can use (a media id belongs to the account that made it).
  const chunk=[],refs=new Map();
  for(const i of pending) {
   if(chunk.length===fits)break;
   const plan=referencesFor(policy,profile,requests[i],owners);
   if(plan.ok){chunk.push(i);refs.set(i,plan);}
   else failed.set(i,`FLOW_NOT_SUBMITTED: ${plan.reason}`);
  }
  pending=pending.filter(i=>!failed.has(i));
  if(!chunk.length) {
   if(!dispatched)throw Error([...failed.values()][0].replace(/^FLOW_NOT_SUBMITTED: /,''));
   break;
  }
  // 5. Queue the chunk in the tool, check every mapping, journal the whole chunk, then Start.
  const ids=[];
  try {
   for(const i of chunk) {
    const r=requests[i],plan=refs.get(i),added=await driver.enqueue(r,plan);
    if(added.length!==1||added[0].topic!==r.spec.prompt||(added[0].characterRefMediaId??null)!==(plan.character?.mediaId??null)
     ||(added[0].baseImageMediaId??null)!==(plan.base?.mediaId??null)||added[0].aspectRatio!==r.spec.ratio)throw Error('QUEUE_REFERENCE_MAPPING_FAILED');
    ids.push(added[0].id);
   }
   await driver.setWorkers();
   if((await driver.snapshot()).items.filter(i=>i.status==='QUEUED').length!==ids.length)throw Error('UNEXPECTED_QUEUED_REQUEST');
  } catch(error){stop(error.message);break;}
  // Mark the entire chunk before Start. A crash anywhere makes retry conservative.
  chunk.forEach((i,k)=>store.beginSubmission(chains[i].attempt,{queueId:ids[k],screenshot:null,profile,toolUrl:expectedUrl,
   resend:chains[i].resend||undefined,storage:{usedChars:snap.usedChars,perImageChars:perImage,capacity:fits}}));
  dispatched=true;started??=Date.now();
  pending=pending.filter(i=>!chunk.includes(i));
  await driver.start();
  // 6. Each request resolves on its own: one stuck or failed item never holds back the finished ones.
  const t0=Date.now(),done=new Set(),quota=[],quotaText=new Map();let halt=null;
  while(Date.now()-t0<itemTimeoutMs) {
   const current=await driver.snapshot();
   for(let k=0;k<chunk.length;k++) {
    const i=chunk[k];
    if(done.has(i))continue;
    const item=current.items.find(x=>x.id===ids[k]);
    if(!item){failed.set(i,'QUEUE_DISAPPEARED_RECONCILE_NO_RESUBMIT');done.add(i);continue;}
    if(item.mediaId&&item.hasResult) {
     const full=await driver.item(ids[k]);
     if(!full?.mediaId||!full.result?.base64)continue;  // read again on the next poll
     store.recordGenerated(chains[i].attempt,{mediaId:full.mediaId,result:full.result,queueId:full.id,timestamps:full.timestamps});
     done.add(i);continue;
    }
    if(!['UNKNOWN','FAILED'].includes(item.status))continue;
    done.add(i);
    const text=itemErrorText(item),kind=classifyFailure(text,policy.patterns);
    if(noMedia(item,policy.patterns)) {
     store.recordNoMedia(chains[i].attempt,{queueId:item.id,status:item.status,error:text,classification:kind==='quota'?'quota':kind||'no_media',profile});
     if(kind==='quota'){quota.push(i);quotaText.set(i,text);continue;}
     failed.set(i,`FLOW_NO_MEDIA: ${text}`);
     if(kind==='rate_limit')halt??=`FLOW_RATE_LIMITED: ${text}`;
     continue;
    }
    const label={captcha:'FLOW_CAPTCHA',login:'FLOW_SIGN_IN_REQUIRED',storage:'TOOL_STORAGE_FAILURE'}[kind];
    failed.set(i,`${label||`FLOW_ITEM_${item.status}`}_RECONCILE_NO_RESUBMIT: ${text||'no result'}`);
    if(label)halt??=`${label}: ${text}`;
   }
   if(done.size===chunk.length)break;
   await new Promise(resolve=>setTimeout(resolve,pollMs));
  }
  for(const i of chunk)if(!done.has(i))failed.set(i,'FLOW_TIMEOUT_RECONCILE_NO_RESUBMIT');
  // Write every image of this chunk to disk now, so the tool state may be compacted before the next chunk.
  for(const i of chunk)if(store.read(chains[i].attempt).state==='generated')collectAttempt(store,chains[i].attempt,requests[i],started);
  // 7. Out of quota: record it, and send the unanswered requests again from the next profile.
  if(quota.length) {
   const evidence={queueIds:quota.map(i=>ids[chunk.indexOf(i)]),errors:[...new Set(quota.map(i=>quotaText.get(i)))]};
   const entry=ledger.markExhausted(profile,evidence,{now:now(),resetHours:policy.resetHours});
   appendSwitchLog(switchLog,{event:'exhausted',profile,resetAt:entry.resetAt,...evidence});
   const again=[];
   for(const i of quota) {
    if(chains[i].resend>=limit){failed.set(i,`FLOW_QUOTA_NO_MEDIA: sent ${chains[i].resend+1} times, every profile answered out of quota`);continue;}
    const resend=chains[i].resend+1;
    chains[i]={attempt:store.prepare(resendIdentity(requests[i].identity,resend)),resend};
    again.push(i);
   }
   pending=[...again,...pending];
  }
  if(halt){stop(halt);break;}
 }
 const result=collectResults(store,chains,requests,started,failed);
 return switches.length?{...result,profileSwitches:switches}:result;
}

/** Write one generated image to its output folder, validate the real bytes and mark it collected. */
function collectAttempt(store,attempt,request,started=null) {
 const a=store.read(attempt);
 const event=a.events.find(e=>e.event==='generated'),r=event.result;
 const submission=a.events.find(e=>e.event==='submitting');
 const shot=submission.screenshot;
 const ext={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}[r.mimeType];
 if(!ext)throw Error('OUTPUT_FORMAT_UNSUPPORTED');
 const folder=path.resolve(request.spec.outDir);fs.mkdirSync(folder,{recursive:true});
 const file=path.join(folder,`${a.identity}${ext}`);fs.writeFileSync(file,Buffer.from(r.base64,'base64'));
 const validation=JSON.parse(execFileSync('python3',[path.join(here,'validate_asset.py'),file,'--ratio',request.spec.ratio],{encoding:'utf8'}));
 const result={path:file,forge_id:a.mediaId,media_id:a.mediaId,before_submit:shot,screenshot:shot,technical_validation:validation,
  latency:started?(Date.now()-started)/1000:null,request_id:request.spec.testCase,profile:submission.profile||null};
 store.recordCollected(a,result);
 return result;
}

function collectResults(store,chains,requests,started=null,failed=new Map()) {
 const items=[],failures=[];
 for(let i=0;i<chains.length;i++) {
  const a=store.read(chains[i].attempt);
  if(a.state==='collected'&&fs.existsSync(a.events.at(-1).collection.path)){items.push(a.events.at(-1).collection);continue;}
  if(!['generated','collected'].includes(a.state)) {
   const evidence=a.events.at(-1).evidence;
   const known=a.state==='failed_no_media'?(isQuotaNoMedia(a)?`FLOW_QUOTA_NO_MEDIA: ${evidence.error}`:`FLOW_NO_MEDIA: ${evidence.error}`)
    :a.state==='prepared'?'FLOW_NOT_SUBMITTED: request was not dispatched':`FLOW_RECONCILIATION_REQUIRED: attempt ${a.state}`;
   items.push(null);failures.push({index:i,request_id:requests[i].spec.testCase,reason:failed.get(i)||known});
   continue;
  }
  // Generated but not written (or its file is gone): rewrite from the journaled bytes, never regenerate.
  if(a.state==='collected'){items.push(rewriteCollected(a,requests[i]));continue;}
  items.push(collectAttempt(store,a,requests[i],started));
 }
 return failures.length?{items,failures}:{items};
}
/** A collected attempt whose file was removed: restore the same bytes from the journal. */
function rewriteCollected(a,request) {
 const collection=a.events.at(-1).collection,r=a.events.find(e=>e.event==='generated').result;
 fs.mkdirSync(path.resolve(request.spec.outDir),{recursive:true});
 fs.writeFileSync(collection.path,Buffer.from(r.base64,'base64'));
 return collection;
}
