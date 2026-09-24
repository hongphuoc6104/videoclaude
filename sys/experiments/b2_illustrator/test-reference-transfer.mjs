/** Reference uploads are test fixtures here; no Flow tab or image generation. */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {ReferenceTransferStore,ensureReferenceTransfer} from './reference-transfer.mjs';
import {projectUrlFromTool,explicitMediaIds,requestContainsSource,responseCandidateIds} from './flow-reference-upload.mjs';

const root=fs.mkdtempSync(path.join(os.tmpdir(),'vp-ref-transfer-'));
test.after(()=>fs.rmSync(root,{recursive:true,force:true}));
const SOURCE='11111111-1111-4111-8111-111111111111';
const TARGET='22222222-2222-4222-8222-222222222222';
const bytes=Buffer.from('TEST ONLY saved image bytes');
const sourceSha256=crypto.createHash('sha256').update(bytes).digest('hex');
const identity={profile:'Profile 102',owner:'Profile 10',sourceMediaId:SOURCE,sourceSha256,
 toolUrl:'https://flow.google.com/project/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/tool/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'};
const ref={mediaId:SOURCE,sha256:sourceSha256,path:path.join(root,'source.png')};
fs.writeFileSync(ref.path,bytes);

function proof(folder,id=TARGET) {
 fs.mkdirSync(folder,{recursive:true});
 const screenshot=path.join(folder,crypto.randomUUID()+'.png');fs.writeFileSync(screenshot,'TEST ONLY observed upload tile');
 return {targetMediaId:id,evidence:{profile:identity.profile,sourceMediaId:identity.sourceMediaId,sourceSha256,
  networkMediaId:id,tileMediaId:id,screenshot,
  uploadRequestSha256:sourceSha256,networkBodySha256:sourceSha256,tileBytesSha256:sourceSha256,
  uploadPayloadContainsSource:true,
  screenshotSha256:crypto.createHash('sha256').update(fs.readFileSync(screenshot)).digest('hex')}};
}

test('identity property order cannot create a second upload journal',()=>{
 const store=new ReferenceTransferStore(path.join(root,'canonical-key'));
 const reordered=Object.fromEntries(Object.entries(identity).reverse());
 assert.equal(store.file(identity),store.file(reordered));
 store.prepare(identity);
 assert.equal(store.read(reordered).state,'prepared');
});

test('upload evidence maps only the exact source bytes and target profile, then reuses the journal',async()=>{
 const store=new ReferenceTransferStore(path.join(root,'success')),folder=path.join(root,'success-proof');
 let calls=0;
 const upload=async()=>{calls++;return proof(folder);};
 assert.equal(await ensureReferenceTransfer(store,identity,ref,upload),TARGET);
 assert.equal(await ensureReferenceTransfer(store,identity,ref,upload),TARGET);
 assert.equal(calls,1);assert.equal(store.read(identity).state,'registered');
 assert.equal(store.read(identity).evidence.networkMediaId,TARGET);
 const changed={...identity,sourceSha256:'f'.repeat(64)};
 assert.equal(store.resolved(changed),null,'different source bytes require a different registration');
});

test('failed or ambiguous upload cannot be retried automatically',async()=>{
 const store=new ReferenceTransferStore(path.join(root,'ambiguous'));
 let calls=0;
 await assert.rejects(ensureReferenceTransfer(store,identity,ref,async()=>{calls++;throw Error('UI_TIMEOUT');}),/UI_TIMEOUT/);
 await assert.rejects(ensureReferenceTransfer(store,identity,ref,async()=>{calls++;return proof(root);}),/RECONCILIATION_REQUIRED/);
 assert.equal(calls,1);assert.equal(store.read(identity).state,'uploading');
});

test('a concurrent upload lock refuses a second begin before any UI action',()=>{
 const store=new ReferenceTransferStore(path.join(root,'locked'));
 store.prepare(identity);
 const lock=store.file(identity)+'.lock';fs.writeFileSync(lock,'TEST ONLY held by another worker');
 assert.throws(()=>store.begin(identity),/RECONCILIATION_REQUIRED/);
 assert.equal(store.read(identity).state,'prepared');
 fs.unlinkSync(lock);
 store.begin(identity);assert.equal(store.read(identity).state,'uploading');
});

test('missing, contradictory or changed UI/network proof never registers a media ID',async()=>{
 const store=new ReferenceTransferStore(path.join(root,'bad-proof'));
 const bad=proof(path.join(root,'bad-proof-image'));
 bad.evidence.tileMediaId='33333333-3333-4333-8333-333333333333';
 await assert.rejects(ensureReferenceTransfer(store,identity,ref,async()=>bad),/EVIDENCE_INCOMPLETE/);
 assert.equal(store.read(identity).state,'uploading');
 const goodStore=new ReferenceTransferStore(path.join(root,'tamper'));
 const good=proof(path.join(root,'tamper-proof'));
 await ensureReferenceTransfer(goodStore,identity,ref,async()=>good);
 fs.writeFileSync(good.evidence.screenshot,'CHANGED');
 assert.throws(()=>goodStore.resolved(identity),/SAVED_EVIDENCE_CHANGED/);
});

test('only explicit media IDs count; a project UUID or generic id cannot be guessed',()=>{
 assert.equal(projectUrlFromTool(identity.toolUrl),'https://flow.google.com/project/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
 assert.throws(()=>projectUrlFromTool('https://example.com/project/a/tool/b'),/TOOL_URL_UNSUPPORTED/);
 assert.deepEqual([...explicitMediaIds({projectId:SOURCE,id:SOURCE,asset:{mediaId:TARGET}})],[TARGET]);
 assert.deepEqual([...explicitMediaIds({id:SOURCE,projectId:TARGET})],[]);
});

test('unrelated JSON response request cannot attest an uploaded image',()=>{
 const raw={postDataBuffer:()=>Buffer.from('unrelated request')};
 const binary={postDataBuffer:()=>Buffer.concat([Buffer.from('multipart-header'),bytes,Buffer.from('multipart-tail')])};
 const encoded={postDataBuffer:()=>Buffer.from(JSON.stringify({image:bytes.toString('base64')}))};
 const formEncoded={postDataBuffer:()=>Buffer.from(`f.req=${encodeURIComponent(JSON.stringify({image:bytes.toString('base64')}))}`)};
 assert.equal(requestContainsSource(raw,bytes),false);
 assert.equal(requestContainsSource(binary,bytes),true);
 assert.equal(requestContainsSource(encoded,bytes),true);
 assert.equal(requestContainsSource(formEncoded,bytes),true);
 assert.equal(requestContainsSource({postDataBuffer:()=>null},bytes),false);
});

test('Flow batchexecute UUIDs are only candidates for a source-bound UI tile',()=>{
 const body=`)]}'\n[["wrb.fr","upload","[\\"${TARGET}\\",\\"${SOURCE}\\"]",null,null,null,"generic"]]`;
 const url='https://flow.google.com/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=upload';
 assert.deepEqual(responseCandidateIds(body,url),[TARGET,SOURCE]);
 assert.deepEqual(responseCandidateIds(body,'https://example.com/data/batchexecute'),[]);
 assert.deepEqual(responseCandidateIds(JSON.stringify({asset:{mediaId:TARGET},projectId:SOURCE}),url),[TARGET]);
});
