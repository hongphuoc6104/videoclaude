import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {classifyFailure,loadRotationPolicy,ProfileLedger,nextProfile,referencesFor,resetTimeFor,appendSwitchLog,toolUrlFor} from './profile-rotation.mjs';
import {openProfileTab,signInOrCaptcha} from './session.mjs';
import {AttemptStore} from './attempt-store.mjs';
import {noMedia} from './queue-runner.mjs';

const dir=fs.mkdtempSync(path.join(os.tmpdir(),'vp-profiles-'));
test.after(()=>fs.rmSync(dir,{recursive:true,force:true}));

test('failure classes: storage before quota, hard stops before everything',()=>{
 assert.equal(classifyFailure('RESOURCE_EXHAUSTED: quota exceeded'),'quota');
 assert.equal(classifyFailure('You have reached your daily limit'),'quota');
 assert.equal(classifyFailure('Not enough credits to generate'),'quota');
 assert.equal(classifyFailure("QuotaExceededError: Failed to execute 'setItem' on 'Storage': exceeded the quota"),'storage',
  'the browser storage error mentions quota but the image was generated');
 assert.equal(classifyFailure('Persistence failure after result'),'storage');
 assert.equal(classifyFailure('Please complete the CAPTCHA'),'captcha');
 assert.equal(classifyFailure('Sign in required'),'login');
 assert.equal(classifyFailure('Too many requests'),'rate_limit');
 assert.equal(classifyFailure('Expected object response with media fields'),'other');
 assert.equal(classifyFailure(''),null);
 assert.equal(classifyFailure('Kontingent erschöpft',{quota:['kontingent']}),'quota','patterns are configurable');
});

test('no-media never covers a storage failure or a CAPTCHA/sign-in answer',()=>{
 assert.equal(noMedia({status:'UNKNOWN',error:'Persistence failure after result'}),false);
 assert.equal(noMedia({status:'FAILED',error:'captcha required'}),false);
 assert.equal(noMedia({status:'FAILED',error:QUOTA_TEXT()}),true,'quota answer: nothing produced');
 assert.equal(noMedia({status:'FAILED',error:QUOTA_TEXT(),hasResult:true}),false);
});
function QUOTA_TEXT(){return 'RESOURCE_EXHAUSTED';}

test('policy merges shared and machine files; per-profile entries merge key by key',()=>{
 const shared=path.join(dir,'shared.json'),local=path.join(dir,'local.json');
 fs.writeFileSync(shared,JSON.stringify({flow_profile_directory:'Profile 10',priority:['Profile 10','Profile 102'],automatic_account_switching:false,
  profiles:{'Profile 102':{note:'second',tool_url:'https://flow/102'}},failure_patterns:{quota:['hết lượt']}}));
 fs.writeFileSync(local,JSON.stringify({tool_url:'https://flow/10',automatic_account_switching:true,profiles:{'Profile 102':{reference_media:'shared'}}}));
 const p=loadRotationPolicy({shared,local});
 assert.equal(p.enabled,true);assert.equal(p.home,'Profile 10');
 assert.deepEqual(p.profiles['Profile 102'],{note:'second',tool_url:'https://flow/102',reference_media:'shared'});
 assert.equal(toolUrlFor(p,'Profile 10'),'https://flow/10');assert.equal(toolUrlFor(p,'Profile 13'),null);
 assert.equal(classifyFailure('Bạn đã hết lượt tạo ảnh',p.patterns),'quota');
 assert.equal(loadRotationPolicy({shared:path.join(dir,'missing.json'),local:path.join(dir,'missing2.json')}).enabled,false,'off unless explicitly enabled');
});

test('the ledger survives restarts and releases a profile at its reset time',()=>{
 const file=path.join(dir,'ledger.json'),now=new Date('2026-09-24T23:30:00+07:00');
 assert.equal(resetTimeFor(now).toISOString(),new Date('2026-09-25T00:00:00+07:00').toISOString());
 assert.equal(resetTimeFor(now,6).toISOString(),new Date('2026-09-25T05:30:00+07:00').toISOString());
 new ProfileLedger(file).markExhausted('Profile 10',{queueIds:['REQ-1']},{now});
 const again=new ProfileLedger(file);
 assert.equal(again.isExhausted('Profile 10',now),true);
 assert.equal(again.isExhausted('Profile 10',new Date('2026-09-25T00:00:01+07:00')),false);
 assert.deepEqual(again.entry('Profile 10').evidence,{queueIds:['REQ-1']});
});

test('next profile: priority order, skipping exhausted, disabled and unconfigured profiles',()=>{
 const ledger=new ProfileLedger(path.join(dir,'next.json')),now=new Date('2026-09-24T10:00:00Z');
 const policy={home:'Profile 10',homeToolUrl:'https://t/10',priority:['Profile 10','Profile 102','Profile 13','Profile 14'],
  profiles:{'Profile 102':{tool_url:'https://t/102'},'Profile 13':{tool_url:'https://t/13',enabled:false},'Profile 14':{tool_url:'https://t/14'}}};
 assert.equal(nextProfile(policy,ledger,'Profile 10',now),'Profile 102');
 ledger.markExhausted('Profile 102',{},{now});
 assert.equal(nextProfile(policy,ledger,'Profile 10',now),'Profile 14');
 ledger.markExhausted('Profile 14',{},{now});ledger.markExhausted('Profile 10',{},{now});
 assert.equal(nextProfile(policy,ledger,'Profile 14',now),null);
});

test('references: own, shared, mapped or refused',()=>{
 const policy={home:'Profile 10',profiles:{'Profile 102':{media_ids:{m10:'m102'}},'Profile 13':{reference_media:'shared'}}};
 const request={character:{mediaId:'m10'},base:{mediaId:'b102'}};
 const owners=new Map([['b102','Profile 102']]);
 assert.equal(referencesFor(policy,'Profile 10',{character:{mediaId:'m10'},base:null},owners).ok,true);
 const mapped=referencesFor(policy,'Profile 102',request,owners);
 assert.equal(mapped.character.mediaId,'m102');assert.equal(mapped.base.mediaId,'b102');
 assert.equal(referencesFor(policy,'Profile 13',request,owners).ok,true);
 assert.match(referencesFor(policy,'Profile 14',request,owners).reason,/REFERENCE_MEDIA_NOT_ON_PROFILE/);
});

test('switch log is append-only',()=>{
 const file=path.join(dir,'switches.ndjson');
 appendSwitchLog(file,{event:'switch',from:'Profile 10',to:'Profile 102'});appendSwitchLog(file,{event:'exhausted',profile:'Profile 102'});
 assert.deepEqual(fs.readFileSync(file,'utf8').trim().split('\n').map(l=>JSON.parse(l).event),['switch','exhausted']);
});

test('no-media evidence is required and a generated attempt can never become no-media',()=>{
 const store=new AttemptStore(path.join(dir,'attempts'));
 const a=store.prepare({id:'x'});store.beginSubmission(a,{queueId:'REQ-1'});
 assert.throws(()=>store.recordNoMedia(a,{queueId:'REQ-1'}),/evidence required/i);
 assert.throws(()=>store.recordNoMedia(a,{queueId:'REQ-1',error:'x',mediaId:'m'}),/evidence required/i);
 const done=store.recordNoMedia(a,{queueId:'REQ-1',error:'RESOURCE_EXHAUSTED',classification:'quota'});
 assert.equal(done.state,'failed_no_media');assert.equal(done.generationSubmitted,true);
 const b=store.prepare({id:'y'});store.beginSubmission(b,{queueId:'REQ-2'});store.recordGenerated(b,{mediaId:'m'});
 assert.throws(()=>store.recordNoMedia(b,{queueId:'REQ-2',error:'late'}),/Cannot transition/);
 assert.equal(new AttemptStore(path.join(dir,'attempts')).load({id:'x'}).state,'failed_no_media','reloads without recovery to unknown');
});

function fakePage(url,{profilePath,executable='/opt/google/chrome/google-chrome',frames=[]}={}) {
 const page={current:url,visited:[],
  url:()=>page.current,frames:()=>frames,
  locator:selector=>({innerText:async()=>selector==='#profile_path'?profilePath:executable}),
  goto:async target=>{page.visited.push(target);page.current=page.redirect||target;}};
 return page;
}
const fakeBrowser=pages=>({contexts:()=>[{pages:()=>pages}]});

test('switching opens the profile through Chrome, verifies it on chrome://version, then binds the tool tab',async()=>{
 const pages=[];let launched=null;
 const launch=(exe,args)=>{launched={exe,args};const nonce=args.at(-1);pages.push(fakePage(nonce,{profilePath:'/data/Profile 102'}));};
 const bound=await openProfileTab({browser:fakeBrowser(pages),dataDir:'/data',profile:'Profile 102',executable:'/opt/google/chrome/google-chrome',
  url:'https://flow/102',launch,findFrame:async()=>({}),pollMs:1,exists:()=>true});
 assert.deepEqual(launched.args.slice(0,2),['--user-data-dir=/data','--profile-directory=Profile 102']);
 assert.match(launched.args[2],/^https:\/\/flow\/102\?vp-switch=/);
 assert.equal(bound.profile,'Profile 102');assert.equal(bound.toolUrl,'https://flow/102');assert.deepEqual(pages[0].visited,['chrome://version/','https://flow/102']);
});

test('switching refuses a wrong profile, a sign-in page, a CAPTCHA and a missing tab',async()=>{
 const make=(profilePath,extra={})=>{const pages=[];return {pages,launch:(exe,args)=>{const p=fakePage(args.at(-1),{profilePath,...extra});Object.assign(p,extra.page||{});pages.push(p);}};};
 const base={dataDir:'/data',profile:'Profile 102',executable:'/opt/google/chrome/google-chrome',url:'https://flow/102',findFrame:async()=>({}),pollMs:1,exists:()=>true};
 let w=make('/data/Profile 13');
 await assert.rejects(openProfileTab({...base,browser:fakeBrowser(w.pages),launch:w.launch}),/PROFILE_PATH_MISMATCH/);
 w=make('/data/Profile 102',{page:{redirect:'https://accounts.google.com/v3/signin/identifier?continue=x'}});
 await assert.rejects(openProfileTab({...base,browser:fakeBrowser(w.pages),launch:w.launch}),/FLOW_SIGN_IN_REQUIRED/);
 const challenge={url:()=>'https://www.google.com/recaptcha/enterprise/bframe?k=1',frameElement:async()=>({isVisible:async()=>true})};
 w=make('/data/Profile 102',{frames:[challenge]});
 await assert.rejects(openProfileTab({...base,browser:fakeBrowser(w.pages),launch:w.launch,findFrame:async()=>{throw Error('APP_FRAME_NOT_READY');}}),/FLOW_CAPTCHA_REQUIRED/);
 await assert.rejects(openProfileTab({...base,browser:fakeBrowser([]),launch:()=>{},timeoutMs:20}),/PROFILE_SWITCH_TAB_NOT_FOUND/);
 await assert.rejects(openProfileTab({...base,profile:'../x',browser:fakeBrowser([]),launch:()=>{}}),/Invalid profile/);
 const anchorOnly={url:()=>'https://www.google.com/recaptcha/enterprise/anchor?k=1',frameElement:async()=>({isVisible:async()=>true})};
 assert.equal(await signInOrCaptcha(fakePage('https://flow/102',{frames:[anchorOnly]})),null,'the normal reCAPTCHA badge is not a challenge');
});
