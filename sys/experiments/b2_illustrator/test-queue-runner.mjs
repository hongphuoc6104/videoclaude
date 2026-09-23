import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {prepareRequests,journalByQueueId,toolStateBlockers} from './queue-runner.mjs';
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'vp-queue-'));
const file=path.join(dir,'ref.png');fs.writeFileSync(file,'reference');
const request={testCase:'scene-1',prompt:'Borrow a book',ratio:'9:16',outDir:dir,characterRefPath:file,charMediaId:'mascot-id'};
test('reference content and media identity are captured',()=>{
 const [r]=prepareRequests([request]);assert.equal(r.character.mediaId,'mascot-id');assert.equal(r.identity.references.length,1);assert.equal(r.identity.references[0].sha256.length,64);
});
test('missing base media ID blocks before browser operations',()=>assert.throws(()=>prepareRequests([{...request,baseRefPath:file}]),/MEDIA_ID/));
test('duplicate scene IDs and oversized batches are rejected',()=>{
 assert.throws(()=>prepareRequests([request,request]),/DUPLICATE/);
 assert.throws(()=>prepareRequests(Array(5).fill(request)),/SIZE/);
});
test('ratio and character reference are required',()=>{
 assert.throws(()=>prepareRequests([{...request,ratio:'1:1'}]),/INVALID/);
 assert.throws(()=>prepareRequests([{...request,characterRefPath:null}]),/CHARACTER/);
});
test('a declared text-only request has no character and its own identity',()=>{
 const [plain]=prepareRequests([request]);
 const [none]=prepareRequests([{...request,characterRefPath:null,charMediaId:null,noCharacter:true,styleNote:'No character reference is attached.'}]);
 assert.equal(none.character,null);assert.equal(none.identity.references.length,0);
 assert.equal(none.identity.noCharacter,true);assert.equal(none.styleNote,'No character reference is attached.');
 assert.equal(plain.identity.noCharacter,undefined,'canonical requests keep their historical identity');
 assert.equal(plain.identity.styleNote,undefined);
 assert.throws(()=>prepareRequests([{...request,noCharacter:true}]),/CONFLICT/);
});
test('a story character reference carries its own note into the identity',()=>{
 const [story]=prepareRequests([{...request,charMediaId:'story-id',styleNote:'Match the attached character reference exactly.'}]);
 assert.equal(story.character.mediaId,'story-id');assert.equal(story.identity.styleNote,'Match the attached character reference exactly.');
});
test.after(()=>fs.rmSync(dir,{recursive:true,force:true}));

function journal(folder,name,events){fs.writeFileSync(path.join(folder,name+'.ndjson'),events.map(e=>JSON.stringify(e)).join('\n')+'\n');}
test('tool state may be dropped only when every item is on disk or explicitly released',()=>{
 const store=fs.mkdtempSync(path.join(os.tmpdir(),'vp-journal-'));
 journal(store,'a',[{state:'prepared'},{event:'submitting',state:'submitting',queueId:'REQ-A'},{event:'generated',state:'generated'},{event:'collected',state:'collected'}]);
 journal(store,'b',[{state:'prepared'},{event:'submitting',state:'submitting',queueId:'REQ-B'},{event:'unknown',state:'unknown'}]);
 journal(store,'c',[{state:'prepared'},{event:'submitting',state:'submitting',queueId:'REQ-C'},{event:'generated',state:'generated'}]);
 const known=journalByQueueId(store);
 assert.deepEqual(Object.fromEntries(known),{'REQ-A':'collected','REQ-B':'unknown','REQ-C':'generated'});
 const queue=[{id:'REQ-A'},{id:'REQ-B'},{id:'REQ-C'},{id:'REQ-X'}];
 assert.deepEqual(toolStateBlockers(queue,known),['REQ-B','REQ-C','REQ-X'],'unknown, uncollected and foreign items block');
 assert.deepEqual(toolStateBlockers(queue,known,['REQ-B','REQ-C','REQ-X']),['REQ-C','REQ-X'],
  'release covers only sent-and-never-collected items; a generated result must be collected first');
 assert.deepEqual(toolStateBlockers([{id:'REQ-A'}],known),[]);
});
