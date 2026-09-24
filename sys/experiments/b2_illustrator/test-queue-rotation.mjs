/**
 * executeQueue against an in-memory tool (no browser, no Flow). Each fake tab is one Chrome
 * profile's copy of the tool: it records exactly which prompts were started there, so the
 * tests can prove nothing already dispatched is ever sent again.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {AttemptStore} from './attempt-store.mjs';
import {executeQueue,runQueue,journalByQueueId,toolStateBlockers,storageCapacity,estimateCharsPerImage,
 LOCAL_STORAGE_QUOTA_CHARS,CHARS_PER_IMAGE_FLOOR} from './queue-runner.mjs';
import {ProfileLedger,DEFAULT_FAILURE_PATTERNS} from './profile-rotation.mjs';
import {ReferenceTransferStore} from './reference-transfer.mjs';

const root=fs.mkdtempSync(path.join(os.tmpdir(),'vp-rotation-'));
test.after(()=>fs.rmSync(root,{recursive:true,force:true}));
const png=path.join(root,'tall.png');
execFileSync('python3',['-c',`from PIL import Image;Image.new('RGB',(90,160),'white').save(${JSON.stringify(png)})`]);
const PNG64=fs.readFileSync(png).toString('base64');
const mascot=path.join(root,'mascot.png');fs.copyFileSync(png,mascot);
const NOW=new Date('2026-09-24T10:00:00+07:00');
const QUOTA='RESOURCE_EXHAUSTED: image generation quota exceeded for this account';

let seq=0;
class FakeTab {
 /** outcome(prompt) -> {error} | {imageChars} ; extraChars = other localStorage data of the origin. */
 constructor(profile,{url=`https://flow.test/${profile}`,outcome=()=>({}),extraChars=0,items=[],stateError=null}={}) {
  Object.assign(this,{profile,toolUrl:url,outcome,extraChars,items:[...items],stateError,status:'IDLE',started:[],resets:0});
 }
 url(){return this.toolUrl;}
 summary(i){return {id:i.id,status:i.status,mediaId:i.mediaId||null,error:i.error||null,hasResult:Boolean(i.result?.base64),
  itemChars:i.itemChars||600,topic:i.topic,aspectRatio:i.aspectRatio,characterRefMediaId:i.characterRefMediaId??null,baseImageMediaId:i.baseImageMediaId??null}}
 async snapshot(){return {status:this.status,error:this.stateError,usedChars:this.extraChars+this.items.reduce((n,i)=>n+(i.itemChars||600),0),items:this.items.map(i=>this.summary(i))};}
 async item(id){return this.items.find(i=>i.id===id)||null;}
 async enqueue(r,refs){
  const item={id:`REQ-${++seq}`,status:'QUEUED',topic:r.spec.prompt,aspectRatio:r.spec.ratio,
   characterRefMediaId:refs.character?.mediaId??null,baseImageMediaId:refs.base?.mediaId??null};
  this.items.push(item);return [this.summary(item)];
 }
 async setWorkers(){}
 async start(){
  for(const item of this.items.filter(i=>i.status==='QUEUED')) {
   this.started.push(item.topic);
   const o=this.outcome(item.topic,this);
   if(o.error){Object.assign(item,{status:'UNKNOWN',error:o.error});this.status='UNKNOWN';}
   else if(o.stuck){item.status='PROCESSING';}
   else Object.assign(item,{status:'COMPLETED',mediaId:`media-${this.profile}-${item.id}`,itemChars:o.imageChars||600,
    result:{base64:PNG64,mimeType:'image/png'},timestamps:{submit:1}});
  }
 }
 async reset(store,{release=[]}={}){
  const blockers=toolStateBlockers(this.items,journalByQueueId(store.directory),release);
  if(blockers.length)throw Error('TOOL_STATE_HAS_UNSAVED_ITEMS: '+blockers.join(','));
  this.items=[];this.status='IDLE';this.resets++;
 }
}

function world(name,{tabs,enabled=true,profiles,priority=['Profile 10','Profile 102','Profile 13','Profile 14']}) {
 const dir=path.join(root,name);fs.mkdirSync(dir,{recursive:true});
 const store=new AttemptStore(path.join(dir,'attempts'));
 const transferStore=new ReferenceTransferStore(path.join(dir,'reference-transfers'));
 const ledger=new ProfileLedger(path.join(dir,'profile-exhaustion.json'));
 const switchLog=path.join(dir,'profile-switches.ndjson');
 const policy={enabled,home:'Profile 10',priority,homeToolUrl:tabs['Profile 10']?.toolUrl,resetHours:null,
  profiles:profiles||Object.fromEntries(Object.values(tabs).map(t=>[t.profile,{tool_url:t.toolUrl,reference_media:'shared'}])),
  patterns:DEFAULT_FAILURE_PATTERNS};
 const switched=[];
 const bind=profile=>({profile,toolUrl:tabs[profile].toolUrl,identity:{observedProfile:`/data/${profile}`},tab:tabs[profile],
  switchProfile:async(target,url)=>{
   switched.push({target,url});
   if(!tabs[target])throw Error('FLOW_SIGN_IN_REQUIRED: https://accounts.google.com/');
   return bind(target);
  }});
 const deps={store,transferStore,transferEvidenceDir:path.join(dir,'transfer-evidence'),ledger,switchLog,policy,driver:b=>b.tab,now:()=>NOW,pollMs:1,itemTimeoutMs:200};
 return {dir,store,transferStore,ledger,switchLog,policy,switched,deps,bound:bind('Profile 10'),
  log:()=>fs.existsSync(switchLog)?fs.readFileSync(switchLog,'utf8').trim().split('\n').map(l=>JSON.parse(l)):[]};
}
const specs=(dir,prompts,extra={})=>prompts.map((prompt,k)=>({testCase:`s${k+1}`,prompt,ratio:'9:16',outDir:path.join(dir,'out'),noCharacter:true,styleNote:'No character reference is attached.',...extra}));

test('real storage numbers: capacity under the 80 % budget',()=>{
 assert.equal(LOCAL_STORAGE_QUOTA_CHARS,5242880);
 assert.equal(estimateCharsPerImage([]),CHARS_PER_IMAGE_FLOOR,'floor covers the largest image seen (327,132 chars) plus config');
 assert.equal(estimateCharsPerImage([{hasResult:true,itemChars:400000}]),460000,'a larger image raises the estimate');
 assert.equal(storageCapacity({usedChars:0,perImageChars:360000}),11,'empty tool: a group of 4 always fits');
 assert.equal(storageCapacity({usedChars:2789441,perImageChars:360000}),3,'the 17-image backup (2.79 M) no longer fits a group of 4');
 assert.equal(storageCapacity({usedChars:5166163,perImageChars:360000}),0,'22 images (5.17 M): nothing more fits');
});

test('a group that does not fit is sent in storage-sized chunks, compacting only after each chunk is on disk',async()=>{
 // 3.2 M chars of other data in the origin: after compaction only two images fit at a time.
 const tabs={'Profile 10':new FakeTab('Profile 10',{extraChars:3200000,outcome:()=>({imageChars:200000})})};
 const w=world('chunks',{tabs});
 const result=await executeQueue(specs(w.dir,['a','b','c','d']),w.bound,w.deps);
 assert.equal(result.failures,undefined);assert.equal(result.items.length,4);
 assert.deepEqual(tabs['Profile 10'].started,['a','b','c','d'],'each prompt started exactly once');
 assert.ok(tabs['Profile 10'].resets>=2,'compacted between chunks');
 for(const item of result.items)assert.ok(fs.existsSync(item.path));
 const again=await executeQueue(specs(w.dir,['a','b','c','d']),w.bound,w.deps);
 assert.equal(again.items.length,4);assert.equal(tabs['Profile 10'].started.length,4,'replay reads the journal, sends nothing');
});

test('no room and unsaved items in the tool: refuses before sending anything',async()=>{
 const foreign={id:'REQ-FOREIGN',status:'COMPLETED',mediaId:'m',result:{base64:'x'},itemChars:300000,topic:'manual'};
 const tabs={'Profile 10':new FakeTab('Profile 10',{extraChars:3900000,items:[foreign]})};
 const w=world('full',{tabs});
 const out=await runQueue(specs(w.dir,['a']),w.bound,w.deps);
 assert.equal(out.status,'blocked');assert.match(out.reason,/TOOL_STATE_HAS_UNSAVED_ITEMS: REQ-FOREIGN/);
 assert.equal(out.generationSubmitted,false);assert.deepEqual(tabs['Profile 10'].started,[]);
});

test('out of quota: the unanswered requests continue on the next profile, finished ones are not re-sent',async()=>{
 const tabs={
  'Profile 10':new FakeTab('Profile 10',{outcome:p=>['c','d'].includes(p)?{error:QUOTA}:{}}),
  'Profile 102':new FakeTab('Profile 102'),
 };
 const w=world('rotate',{tabs});
 const result=await executeQueue(specs(w.dir,['a','b','c','d']),w.bound,w.deps);
 assert.equal(result.failures,undefined);
 assert.deepEqual(result.items.map(i=>i.profile),['Profile 10','Profile 10','Profile 102','Profile 102']);
 assert.deepEqual(tabs['Profile 102'].started,['c','d'],'only the requests answered with no image move');
 assert.deepEqual(tabs['Profile 10'].started,['a','b','c','d']);
 assert.equal(w.ledger.isExhausted('Profile 10',NOW),true);
 assert.equal(w.ledger.entry('Profile 10').resetAt,new Date('2026-09-25T00:00:00+07:00').toISOString(),'resets next local midnight');
 const log=w.log();
 assert.deepEqual(log.map(e=>e.event),['exhausted','switch']);
 assert.equal(log[1].from,'Profile 10');assert.equal(log[1].to,'Profile 102');assert.deepEqual(log[1].requests,['s3','s4']);
 assert.equal(result.profileSwitches.length,1);
 // Journal: the first attempt proves no image; the resend is its own attempt.
 const states=fs.readdirSync(w.store.directory).filter(f=>f.endsWith('.ndjson')).map(f=>fs.readFileSync(path.join(w.store.directory,f),'utf8').trim().split('\n').map(l=>JSON.parse(l)));
 const noMedia=states.filter(e=>e.at(-1).state==='failed_no_media');
 assert.equal(noMedia.length,2);assert.equal(noMedia[0].at(-1).evidence.classification,'quota');
 assert.equal(states.filter(e=>e[0].request.resend===1&&e.at(-1).state==='collected').length,2);
 // The next group starts directly on the next profile and never touches the exhausted one.
 const next=await executeQueue(specs(w.dir,['e']),w.bound,w.deps);
 assert.equal(next.items[0].profile,'Profile 102');assert.equal(tabs['Profile 10'].started.length,4);
});

test('an unknown outcome in the same chunk is never sent to the next profile',async()=>{
 const tabs={
  'Profile 10':new FakeTab('Profile 10',{outcome:p=>p==='a'?{stuck:true}:p==='b'?{error:QUOTA}:{}}),
  'Profile 102':new FakeTab('Profile 102'),
 };
 const w=world('unknown',{tabs});
 const result=await executeQueue(specs(w.dir,['a','b']),w.bound,w.deps);
 assert.deepEqual(tabs['Profile 102'].started,['b']);
 assert.equal(result.failures.length,1);assert.equal(result.failures[0].request_id,'s1');
 assert.match(result.failures[0].reason,/FLOW_TIMEOUT_RECONCILE_NO_RESUBMIT/);
 const replay=await runQueue(specs(w.dir,['a','b']),w.bound,w.deps);
 assert.match(replay.failures[0].reason,/FLOW_RECONCILIATION_REQUIRED/,'replay reports, never re-sends');
 assert.equal(tabs['Profile 10'].started.filter(p=>p==='a').length,1);
});

test('every profile out of quota: stop, record each, and the next call refuses before sending',async()=>{
 const tabs={
  'Profile 10':new FakeTab('Profile 10',{outcome:()=>({error:QUOTA})}),
  'Profile 102':new FakeTab('Profile 102',{outcome:()=>({error:'Daily limit reached for image generation'})}),
 };
 const w=world('exhausted',{tabs});   // Profile 13 and 14 have no tool URL: not usable
 const result=await executeQueue(specs(w.dir,['a','b']),w.bound,w.deps);
 assert.equal(result.items.filter(Boolean).length,0);
 for(const f of result.failures)assert.match(f.reason,/^FLOW_NOT_SUBMITTED: FLOW_QUOTA_ALL_PROFILES_EXHAUSTED/);
 assert.deepEqual(w.log().map(e=>e.event),['exhausted','switch','exhausted','all_exhausted']);
 assert.equal(w.ledger.isExhausted('Profile 102',NOW),true);
 const blocked=await runQueue(specs(w.dir,['a','b']),w.bound,w.deps);
 assert.equal(blocked.status,'blocked');assert.match(blocked.reason,/ALL_PROFILES_EXHAUSTED/);
 assert.equal(blocked.generationSubmitted,false,'nothing produced and the standing attempts were never sent');
 assert.equal(tabs['Profile 10'].started.length+tabs['Profile 102'].started.length,4);
});

test('rotation off: quota stops the queue and switches nothing',async()=>{
 const tabs={'Profile 10':new FakeTab('Profile 10',{outcome:()=>({error:QUOTA})}),'Profile 102':new FakeTab('Profile 102')};
 const w=world('off',{tabs,enabled:false});
 const result=await executeQueue(specs(w.dir,['a']),w.bound,w.deps);
 assert.match(result.failures[0].reason,/FLOW_NOT_SUBMITTED: FLOW_PROFILE_QUOTA_EXHAUSTED: Profile 10/);
 assert.deepEqual(w.switched,[]);assert.deepEqual(tabs['Profile 102'].started,[]);
});

test('CAPTCHA and storage failures are hard stops: no retry, no switch, no compaction',async()=>{
 const tabs={'Profile 10':new FakeTab('Profile 10',{outcome:p=>p==='a'?{error:'CAPTCHA verification required'}:{error:'Persistence failure after result'}}),'Profile 102':new FakeTab('Profile 102')};
 const w=world('hard',{tabs});
 const result=await executeQueue(specs(w.dir,['a','b']),w.bound,w.deps);
 assert.match(result.failures[0].reason,/^FLOW_CAPTCHA_RECONCILE_NO_RESUBMIT/);
 assert.match(result.failures[1].reason,/^TOOL_STORAGE_FAILURE_RECONCILE_NO_RESUBMIT/,'the image was generated: never a no-media retry');
 assert.deepEqual(w.switched,[]);assert.equal(w.ledger.isExhausted('Profile 10',NOW),false);
 const next=await runQueue(specs(w.dir,['c']),w.bound,w.deps);
 assert.match(next.reason,/FLOW_CAPTCHA_OR_SIGN_IN_REQUIRED/);assert.equal(next.generationSubmitted,false);
 assert.deepEqual(tabs['Profile 10'].started,['a','b']);
});

test('a switch that lands on a sign-in page stops without sending anything there',async()=>{
 const tabs={'Profile 10':new FakeTab('Profile 10',{outcome:()=>({error:QUOTA})})};
 const w=world('signin',{tabs,profiles:{'Profile 10':{tool_url:tabs['Profile 10'].toolUrl},'Profile 102':{tool_url:'https://flow.test/102'}}});
 const result=await executeQueue(specs(w.dir,['a']),w.bound,w.deps);
 assert.match(result.failures[0].reason,/FLOW_NOT_SUBMITTED: PROFILE_SWITCH_FAILED: FLOW_SIGN_IN_REQUIRED/);
 assert.deepEqual(w.log().map(e=>e.event),['exhausted','switch_failed']);
});

test('reference media of another account are not used unless mapped',async()=>{
 const tabs={'Profile 10':new FakeTab('Profile 10',{outcome:()=>({error:QUOTA})}),'Profile 102':new FakeTab('Profile 102')};
 const ref={characterRefPath:mascot,charMediaId:'mascot-10',noCharacter:false,styleNote:undefined};
 const unmapped=world('refs-unmapped',{tabs,profiles:{'Profile 10':{tool_url:tabs['Profile 10'].toolUrl},'Profile 102':{tool_url:tabs['Profile 102'].toolUrl}}});
 const blocked=await executeQueue(specs(unmapped.dir,['a'],ref),unmapped.bound,unmapped.deps);
 assert.match(blocked.failures[0].reason,/FLOW_NOT_SUBMITTED: REFERENCE_CHARACTER_REGISTRATION_UNVERIFIED/);
 assert.deepEqual(tabs['Profile 102'].started,[]);
 const tabs2={'Profile 10':new FakeTab('Profile 10',{outcome:()=>({error:QUOTA})}),'Profile 102':new FakeTab('Profile 102')};
 const mapped=world('refs-mapped',{tabs:tabs2,profiles:{'Profile 10':{tool_url:tabs2['Profile 10'].toolUrl},'Profile 102':{tool_url:tabs2['Profile 102'].toolUrl,media_ids:{'mascot-10':'mascot-102'}}}});
 const ok=await executeQueue(specs(mapped.dir,['a'],ref),mapped.bound,mapped.deps);
 assert.equal(ok.items[0].profile,'Profile 102');
 assert.equal(tabs2['Profile 102'].items[0].characterRefMediaId,'mascot-102');
});

const SOURCE_BASE='11111111-1111-4111-8111-111111111111';
const TARGET_BASE='22222222-2222-4222-8222-222222222222';
function verifiedUpload(tab,target=TARGET_BASE) {
 tab.uploads=[];
 tab.uploadReference=async(ref,identity,evidenceDir)=>{
  tab.uploads.push({source:ref.mediaId,profile:identity.profile});
  fs.mkdirSync(evidenceDir,{recursive:true});
  const screenshot=path.join(evidenceDir,crypto.randomUUID()+'.png');fs.writeFileSync(screenshot,'TEST ONLY visible uploaded tile');
  return {targetMediaId:target,evidence:{profile:identity.profile,sourceMediaId:identity.sourceMediaId,sourceSha256:identity.sourceSha256,
   networkMediaId:target,tileMediaId:target,screenshot,
   uploadRequestSha256:identity.sourceSha256,networkBodySha256:identity.sourceSha256,
   tileBytesSha256:identity.sourceSha256,uploadPayloadContainsSource:true,
   screenshotSha256:crypto.createHash('sha256').update(fs.readFileSync(screenshot)).digest('hex')}};
 };
}
function seedCollectedBase(w,mediaId=SOURCE_BASE,file=png) {
 const source=w.store.prepare({id:`source-${mediaId}`});
 w.store.beginSubmission(source,{queueId:`source-${mediaId}`,profile:'Profile 10'});
 w.store.recordGenerated(source,{mediaId,result:{base64:fs.readFileSync(file).toString('base64'),mimeType:'image/png'}});
 w.store.recordCollected(source,{path:file});
}

test('foreign base is registered before the quota resend, with verified ID and durable reuse',async()=>{
 const tabs={'Profile 10':new FakeTab('Profile 10',{outcome:()=>({error:QUOTA})}),
  'Profile 102':new FakeTab('Profile 102')};
 verifiedUpload(tabs['Profile 102']);
 const profiles={'Profile 10':{tool_url:tabs['Profile 10'].toolUrl},
  'Profile 102':{tool_url:tabs['Profile 102'].toolUrl,reference_media:'own',media_ids:{[SOURCE_BASE]:'33333333-3333-4333-8333-333333333333'}}};
 const w=world('transfer-base',{tabs,profiles});
 seedCollectedBase(w);
 const request=specs(w.dir,['dependent'],{baseRefPath:png,baseMediaId:SOURCE_BASE});
 const result=await executeQueue(request,w.bound,w.deps);
 assert.equal(result.failures,undefined);
 assert.equal(tabs['Profile 102'].uploads.length,1,'a stale static base map cannot skip verified upload');
 assert.deepEqual(tabs['Profile 102'].started,['dependent']);
 assert.equal(tabs['Profile 102'].items[0].baseImageMediaId,TARGET_BASE);
 assert.equal(result.items[0].profile,'Profile 102');
 const record=fs.readdirSync(w.transferStore.directory).map(x=>JSON.parse(fs.readFileSync(path.join(w.transferStore.directory,x))));
 assert.equal(record.length,1);assert.equal(record[0].state,'registered');
 const attempts=fs.readdirSync(w.store.directory).filter(x=>x.endsWith('.ndjson')).flatMap(x=>
  fs.readFileSync(path.join(w.store.directory,x),'utf8').trim().split('\n').map(line=>JSON.parse(line)));
 const submitted=attempts.find(x=>x.event==='submitting'&&x.profile==='Profile 102');
 assert.deepEqual(submitted.mappedReferences.base,{sourceMediaId:SOURCE_BASE,targetMediaId:TARGET_BASE,
  sha256:crypto.createHash('sha256').update(fs.readFileSync(png)).digest('hex')});
 const replay=await executeQueue(request,w.bound,w.deps);
 assert.equal(replay.items.length,1);assert.equal(tabs['Profile 102'].uploads.length,1);
});

test('an upload failure stays ambiguous and never resends a pending image or the upload',async()=>{
 const tabs={'Profile 10':new FakeTab('Profile 10',{outcome:()=>({error:QUOTA})}),
  'Profile 102':new FakeTab('Profile 102')};
 let uploads=0;tabs['Profile 102'].uploadReference=async()=>{uploads++;throw Error('UPLOAD_FAILED_AFTER_FILE_CHOSEN');};
 const w=world('transfer-failure',{tabs,profiles:{'Profile 10':{tool_url:tabs['Profile 10'].toolUrl},
  'Profile 102':{tool_url:tabs['Profile 102'].toolUrl,reference_media:'own'}}});
 seedCollectedBase(w);
 const request=specs(w.dir,['dependent'],{baseRefPath:png,baseMediaId:SOURCE_BASE});
 const first=await executeQueue(request,w.bound,w.deps);
 assert.match(first.failures[0].reason,/REFERENCE_TRANSFER_FAILED: UPLOAD_FAILED_AFTER_FILE_CHOSEN/);
 assert.deepEqual(tabs['Profile 102'].started,[]);
 const second=await runQueue(request,w.bound,w.deps);
 assert.match(second.reason,/REFERENCE_TRANSFER_RECONCILIATION_REQUIRED/);
 assert.equal(uploads,1);assert.deepEqual(tabs['Profile 102'].started,[]);
});

test('sign-in and CAPTCHA on the new profile stop before upload and generation',async()=>{
 for(const [label,error] of [['login','Please sign in'],['captcha','CAPTCHA verification required']]) {
  const tabs={'Profile 10':new FakeTab('Profile 10',{outcome:()=>({error:QUOTA})}),
   'Profile 102':new FakeTab('Profile 102',{stateError:error})};
  let uploads=0;tabs['Profile 102'].uploadReference=async()=>{uploads++;throw Error('SHOULD_NOT_UPLOAD');};
  const w=world('transfer-'+label,{tabs,profiles:{'Profile 10':{tool_url:tabs['Profile 10'].toolUrl},
   'Profile 102':{tool_url:tabs['Profile 102'].toolUrl,reference_media:'own'}}});
  const request=specs(w.dir,['dependent'],{baseRefPath:png,baseMediaId:SOURCE_BASE});
  const result=await executeQueue(request,w.bound,w.deps);
  assert.match(result.failures[0].reason,/FLOW_CAPTCHA_OR_SIGN_IN_REQUIRED/);
  assert.equal(uploads,0);assert.deepEqual(tabs['Profile 102'].started,[]);
 }
});

test('ambiguous image status is never treated as no-media for transfer or rotation',async()=>{
 const tabs={'Profile 10':new FakeTab('Profile 10',{outcome:()=>({stuck:true})}),
  'Profile 102':new FakeTab('Profile 102')};
 let uploads=0;tabs['Profile 102'].uploadReference=async()=>{uploads++;throw Error('SHOULD_NOT_UPLOAD');};
 const w=world('transfer-ambiguous',{tabs});
 const result=await executeQueue(specs(w.dir,['dependent'],{baseRefPath:png,baseMediaId:SOURCE_BASE}),w.bound,w.deps);
 assert.match(result.failures[0].reason,/FLOW_TIMEOUT_RECONCILE_NO_RESUBMIT/);
 assert.equal(uploads,0);assert.equal(w.switched.length,0);
});

test('a foreign base with no collected source-byte journal is refused before upload',async()=>{
 const tabs={'Profile 10':new FakeTab('Profile 10',{outcome:()=>({error:QUOTA})}),
  'Profile 102':new FakeTab('Profile 102')};
 let uploads=0;tabs['Profile 102'].uploadReference=async()=>{uploads++;throw Error('SHOULD_NOT_UPLOAD');};
 const w=world('transfer-no-provenance',{tabs,profiles:{'Profile 10':{tool_url:tabs['Profile 10'].toolUrl},
  'Profile 102':{tool_url:tabs['Profile 102'].toolUrl,reference_media:'own'}}});
 const result=await executeQueue(specs(w.dir,['dependent'],{baseRefPath:png,baseMediaId:SOURCE_BASE}),w.bound,w.deps);
 assert.match(result.failures[0].reason,/REFERENCE_BASE_PROVENANCE_UNVERIFIED/);
 assert.equal(uploads,0);assert.deepEqual(tabs['Profile 102'].started,[]);
});

test('a collected base changed after Flow generation is refused before upload',async()=>{
 const tabs={'Profile 10':new FakeTab('Profile 10',{outcome:()=>({error:QUOTA})}),
  'Profile 102':new FakeTab('Profile 102')};
 let uploads=0;tabs['Profile 102'].uploadReference=async()=>{uploads++;throw Error('SHOULD_NOT_UPLOAD');};
 const w=world('transfer-tampered-base',{tabs,profiles:{'Profile 10':{tool_url:tabs['Profile 10'].toolUrl},
  'Profile 102':{tool_url:tabs['Profile 102'].toolUrl,reference_media:'own'}}});
 const copy=path.join(w.dir,'saved-base.png');fs.copyFileSync(png,copy);
 seedCollectedBase(w,SOURCE_BASE,copy);
 fs.writeFileSync(copy,'TAMPERED AFTER COLLECTION');
 const result=await executeQueue(specs(w.dir,['dependent'],{baseRefPath:copy,baseMediaId:SOURCE_BASE}),w.bound,w.deps);
 assert.match(result.failures[0].reason,/REFERENCE_BASE_PROVENANCE_UNVERIFIED/);
 assert.equal(uploads,0);assert.deepEqual(tabs['Profile 102'].started,[]);
});
