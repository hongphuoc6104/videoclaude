/** Observe a Flow project upload; never infer a new media ID from a filename.
 *
 * This adapter is intentionally strict. An upload whose UI tile and successful
 * network response do not expose the same media ID remains ambiguous in the
 * durable transfer journal and blocks generation until manually reconciled.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fastScreenshot,findToolFrame} from './controller.mjs';
import {signInOrCaptcha} from './session.mjs';

const sha256=value=>crypto.createHash('sha256').update(value).digest('hex');
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const TILE='img[data-media-id]';

export function projectUrlFromTool(toolUrl) {
 const url=new URL(toolUrl);
 const match=url.pathname.match(/^(\/project\/[0-9a-f-]+)\/tool\/[0-9a-z-]+/i);
 if(url.hostname!=='flow.google.com'||!match)throw Error('REFERENCE_TRANSFER_TOOL_URL_UNSUPPORTED');
 return url.origin+match[1];
}

/** Only explicit mediaId/media_id fields count; generic UUIDs may be project or request IDs. */
export function explicitMediaIds(value,found=new Set()) {
 if(Array.isArray(value)){for(const child of value)explicitMediaIds(child,found);return found;}
 if(!value||typeof value!=='object')return found;
 for(const [key,child] of Object.entries(value)) {
  if(['mediaId','media_id'].includes(key)&&typeof child==='string'&&uuid.test(child))found.add(child);
  else if(child&&typeof child==='object')explicitMediaIds(child,found);
 }
 return found;
}

export function requestContainsSource(request,sourceBytes) {
 const body=request.postDataBuffer?.();
 if(!body||!sourceBytes?.length)return false;
 const payload=Buffer.isBuffer(body)?body:Buffer.from(body);
 return payload.includes(sourceBytes)||payload.includes(Buffer.from(sourceBytes.toString('base64')));
}

function responseAllowed(response,sourceBytes) {
 const url=new URL(response.url());
 const google=url.hostname==='flow.google.com'||url.hostname.endsWith('.googleapis.com');
 const type=response.headers()['content-type']||'';
 return google&&['POST','PUT','PATCH'].includes(response.request().method())
  &&response.status()>=200&&response.status()<300&&type.includes('json')
  &&requestContainsSource(response.request(),sourceBytes);
}

/** Upload a saved image in the already-verified target profile's project UI. */
export async function uploadReferenceViaUi(bound,ref,identity,evidenceDir) {
 const page=bound?.page;
 if(!page||page.isClosed()||bound.profile!==identity.profile||bound.toolUrl!==identity.toolUrl
   ||!page.url().startsWith(identity.toolUrl))throw Error('REFERENCE_TRANSFER_WRONG_PROFILE_OR_TAB');
 const sourceBytes=fs.readFileSync(ref.path);
 if(sha256(sourceBytes)!==identity.sourceSha256)
  throw Error('REFERENCE_TRANSFER_SOURCE_CHANGED');
 const projectUrl=projectUrlFromTool(identity.toolUrl);
 const sourceName=path.basename(ref.path);
 fs.mkdirSync(evidenceDir,{recursive:true});
 const responses=[],responseTasks=[];
 const onResponse=response=>{
  if(!responseAllowed(response,sourceBytes))return;
  responseTasks.push((async()=>{
   try {
    const body=await response.body();
    if(body.length>2_000_000)return;
    const ids=[...explicitMediaIds(JSON.parse(body.toString('utf8')))];
    if(ids.length)responses.push({ids,source:new URL(response.url()).origin+new URL(response.url()).pathname,
     status:response.status(),bodySha256:sha256(body),uploadRequestSha256:sha256(response.request().postDataBuffer())});
   } catch {}
  })());
 };
 try {
  await page.goto(projectUrl,{waitUntil:'domcontentloaded',timeout:30000});
  const blocked=await signInOrCaptcha(page);
  if(blocked)throw Error(blocked);
  const uploadButton=page.getByRole('button',{name:/^(Add media menu|Trình đơn thêm nội dung nghe nhìn)$/});
  await uploadButton.waitFor({timeout:20000});
  const prior=await page.locator(TILE).evaluateAll(xs=>xs.map(x=>x.getAttribute('data-media-id')||''));
  page.on('response',onResponse);
  await uploadButton.click();
  const chooserPromise=page.waitForEvent('filechooser',{timeout:15000});
  await page.getByRole('menuitem',{name:/^(Upload|Tải lên)$/}).click();
  const chooser=await chooserPromise;
  await chooser.setFiles(ref.path);
  const afterUploadBlock=await signInOrCaptcha(page);
  if(afterUploadBlock)throw Error(afterUploadBlock);
  const observation=await page.waitForFunction(({prior,selector,sourceName})=>{
   const needsConsent=[...document.querySelectorAll('[role="dialog"]')].some(x=>
    /Rights to this image|Image rights|Quyền sử dụng hình ảnh này/i.test(x.textContent||''));
   if(needsConsent)return 'consent';
   const added=[...document.querySelectorAll(selector)].filter(x=>
    !prior.includes(x.getAttribute('data-media-id')||'') &&
    x.closest('flow-image-tile')?.querySelector('.footer-title')?.textContent?.trim()===sourceName);
   return added.length>0?'tile':false;
  },{prior,selector:TILE,sourceName},{timeout:90000});
  if(await observation.jsonValue()==='consent')throw Error('REFERENCE_UPLOAD_USER_CONSENT_REQUIRED');
  await Promise.allSettled(responseTasks);
  const added=await page.locator(TILE).evaluateAll((xs,{prior,sourceName})=>xs.map((x,index)=>({index,
   src:x.getAttribute('src')||'',mediaId:x.getAttribute('data-media-id')||'',
   filename:x.closest('flow-image-tile')?.querySelector('.footer-title')?.textContent?.trim()||''}))
   .filter(x=>!prior.includes(x.mediaId)&&x.filename===sourceName),{prior,sourceName});
  if(added.length!==1)throw Error('REFERENCE_TRANSFER_UI_TILE_AMBIGUOUS');
  const ids=[...new Set(responses.flatMap(x=>x.ids))];
  if(ids.length!==1)throw Error('REFERENCE_TRANSFER_NETWORK_MEDIA_ID_UNVERIFIED');
  const mediaId=ids[0],tile=added[0];
  if(tile.mediaId!==mediaId)throw Error('REFERENCE_TRANSFER_UI_MEDIA_ID_UNVERIFIED');
  const tileResponse=await page.request.get(tile.src,{timeout:30000});
  if(!tileResponse.ok())throw Error('REFERENCE_TRANSFER_TILE_BYTES_UNAVAILABLE');
  const tileBytes=await tileResponse.body();
  if(!tileBytes.length)throw Error('REFERENCE_TRANSFER_TILE_BYTES_UNAVAILABLE');
  const screenshot=path.join(evidenceDir,crypto.randomUUID()+'.png');
  await fastScreenshot(page,screenshot);
  const response=responses.find(x=>x.ids.includes(mediaId));
  return {targetMediaId:mediaId,evidence:{profile:identity.profile,sourceMediaId:identity.sourceMediaId,
   sourceSha256:identity.sourceSha256,networkMediaId:mediaId,tileMediaId:mediaId,
   networkSource:response.source,networkStatus:response.status,networkBodySha256:response.bodySha256,
   uploadRequestSha256:response.uploadRequestSha256,uploadPayloadContainsSource:true,
   projectUrl,tileBytesSha256:sha256(tileBytes),screenshot,screenshotSha256:sha256(fs.readFileSync(screenshot)),
   observedAt:new Date().toISOString()}};
 } finally {
  page.off('response',onResponse);
  // An upload cannot be called successful if we cannot return to the same tool.
  await page.goto(identity.toolUrl,{waitUntil:'domcontentloaded',timeout:30000});
  const blocked=await signInOrCaptcha(page);
  if(blocked)throw Error(blocked);
  await findToolFrame(page);
 }
}
