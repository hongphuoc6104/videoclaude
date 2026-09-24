/** Durable, profile-scoped provenance for moving a saved reference into Flow.
 *
 * An upload is a separate external action from image generation. Once it might have
 * started, an interrupted result is ambiguous and cannot be uploaded again by the
 * queue. A later operator must reconcile it from real Flow evidence.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const sha256=value=>crypto.createHash('sha256').update(value).digest('hex');
const mediaId=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function atomicWrite(file,value) {
 const temp=`${file}.${process.pid}.${crypto.randomUUID()}.tmp`;
 const fd=fs.openSync(temp,'wx',0o600);
 try {fs.writeFileSync(fd,JSON.stringify(value,null,2)+'\n');fs.fsyncSync(fd);} finally {fs.closeSync(fd);}
 try {fs.renameSync(temp,file);} finally {if(fs.existsSync(temp))fs.unlinkSync(temp);}
}

export class ReferenceTransferStore {
 constructor(directory){this.directory=directory;}
 key(identity){return sha256(JSON.stringify(identity));}
 file(identity){return path.join(this.directory,this.key(identity)+'.json');}
 withLock(identity,fn) {
  const lock=this.file(identity)+'.lock';let fd;
  try {fd=fs.openSync(lock,'wx',0o600);}
  catch(error) {if(error.code==='EEXIST')throw Error('REFERENCE_TRANSFER_RECONCILIATION_REQUIRED');throw error;}
  try {return fn();}
  finally {fs.closeSync(fd);fs.unlinkSync(lock);}
 }
 prepare(identity) {
  if(!identity.profile||!identity.owner||!identity.sourceMediaId||!identity.sourceSha256||!identity.toolUrl)
   throw Error('REFERENCE_TRANSFER_IDENTITY_INCOMPLETE');
  if(!/^[a-f0-9]{64}$/i.test(identity.sourceSha256))throw Error('REFERENCE_TRANSFER_SOURCE_HASH_INVALID');
  fs.mkdirSync(this.directory,{recursive:true});
  const file=this.file(identity),initial={schema:'vp-reference-transfer-1',identity,state:'prepared',
   events:[{event:'prepared',at:new Date().toISOString()}]};
  try {
   const fd=fs.openSync(file,'wx',0o600);
   try {fs.writeFileSync(fd,JSON.stringify(initial,null,2)+'\n');fs.fsyncSync(fd);} finally {fs.closeSync(fd);}
  } catch(error) {if(error.code!=='EEXIST')throw error;}
  return this.read(identity);
 }
 read(identity) {
  const record=JSON.parse(fs.readFileSync(this.file(identity),'utf8'));
  if(record.schema!=='vp-reference-transfer-1'||JSON.stringify(record.identity)!==JSON.stringify(identity))
   throw Error('REFERENCE_TRANSFER_JOURNAL_MISMATCH');
  if(!['prepared','uploading','registered'].includes(record.state))throw Error('REFERENCE_TRANSFER_JOURNAL_INVALID');
  return record;
 }
 begin(identity) {
  return this.withLock(identity,()=>{
   const record=this.read(identity);
   if(record.state!=='prepared')throw Error('REFERENCE_TRANSFER_RECONCILIATION_REQUIRED');
   record.state='uploading';record.events.push({event:'uploading',at:new Date().toISOString()});
   atomicWrite(this.file(identity),record);return record;
  });
 }
 register(identity,result) {
  return this.withLock(identity,()=>{
   const record=this.read(identity);
   if(record.state!=='uploading')throw Error('REFERENCE_TRANSFER_RECONCILIATION_REQUIRED');
   const id=result?.targetMediaId,evidence=result?.evidence;
   if(!mediaId.test(id||'')||evidence?.networkMediaId!==id||evidence?.tileMediaId!==id
     ||evidence?.profile!==identity.profile||evidence?.sourceMediaId!==identity.sourceMediaId
     ||evidence?.sourceSha256!==identity.sourceSha256
     ||!evidence?.screenshot||!evidence?.screenshotSha256
     ||!fs.existsSync(evidence.screenshot)||sha256(fs.readFileSync(evidence.screenshot))!==evidence.screenshotSha256)
    throw Error('REFERENCE_TRANSFER_EVIDENCE_INCOMPLETE');
   record.state='registered';record.targetMediaId=id;record.evidence=evidence;
   record.events.push({event:'registered',at:new Date().toISOString(),targetMediaId:id});
   atomicWrite(this.file(identity),record);return record;
  });
 }
 resolved(identity) {
  const record=this.prepare(identity);
  if(record.state==='prepared')return null;
  if(record.state!=='registered')throw Error('REFERENCE_TRANSFER_RECONCILIATION_REQUIRED');
  const evidence=record.evidence;
  if(!mediaId.test(record.targetMediaId||'')||evidence?.networkMediaId!==record.targetMediaId
    ||evidence?.tileMediaId!==record.targetMediaId||evidence?.profile!==identity.profile
    ||evidence?.sourceMediaId!==identity.sourceMediaId
    ||evidence?.sourceSha256!==identity.sourceSha256||!evidence?.screenshot
    ||!fs.existsSync(evidence.screenshot)||sha256(fs.readFileSync(evidence.screenshot))!==evidence.screenshotSha256)
   throw Error('REFERENCE_TRANSFER_SAVED_EVIDENCE_CHANGED');
  return record.targetMediaId;
 }
}

/** Upload once, or use a verified saved registration. Errors after begin() are ambiguous. */
export async function ensureReferenceTransfer(store,identity,ref,upload) {
 if(ref.sha256!==identity.sourceSha256)throw Error('REFERENCE_TRANSFER_SOURCE_HASH_MISMATCH');
 const existing=store.resolved(identity);
 if(existing)return existing;
 store.begin(identity);
 const result=await upload(ref,identity);
 return store.register(identity,result).targetMediaId;
}
