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
const TILE='img[alt="Tile displaying a user\'s image"]';

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

function responseAllowed(response) {
 const url=new URL(response.url());
 const google=url.hostname==='flow.google.com'||url.hostname.endsWith('.googleapis.com');
 const type=response.headers()['content-type']||'';
 return google&&response.request().method()!=='GET'&&response.status()>=200&&response.status()<300&&type.includes('json');
}

/** Upload a saved image in the already-verified target profile's project UI. */
export async function uploadReferenceViaUi(bound,ref,identity,evidenceDir) {
 const page=bound?.page;
 if(!page||page.isClosed()||bound.profile!==identity.profile||bound.toolUrl!==identity.toolUrl
   ||!page.url().startsWith(identity.toolUrl))throw Error('REFERENCE_TRANSFER_WRONG_PROFILE_OR_TAB');
 if(sha256(fs.readFileSync(ref.path))!==identity.sourceSha256)
  throw Error('REFERENCE_TRANSFER_SOURCE_CHANGED');
 const projectUrl=projectUrlFromTool(identity.toolUrl);
 fs.mkdirSync(evidenceDir,{recursive:true});
 const responses=[],responseTasks=[];
 const onResponse=response=>{
  if(!responseAllowed(response))return;
  responseTasks.push((async()=>{
   try {
    const body=await response.body();
    if(body.length>2_000_000)return;
    const ids=[...explicitMediaIds(JSON.parse(body.toString('utf8')))];
    if(ids.length)responses.push({ids,source:new URL(response.url()).origin+new URL(response.url()).pathname,
     status:response.status(),bodySha256:sha256(body)});
   } catch {}
  })());
 };
 try {
  await page.goto(projectUrl,{waitUntil:'domcontentloaded',timeout:30000});
  const blocked=await signInOrCaptcha(page);
  if(blocked)throw Error(blocked);
  const uploadButton=page.getByRole('button',{name:'Add media menu',exact:true});
  await uploadButton.waitFor({timeout:20000});
  const prior=await page.locator(TILE).evaluateAll(xs=>xs.map(x=>x.getAttribute('src')||''));
  page.on('response',onResponse);
  await uploadButton.click();
  const chooserPromise=page.waitForEvent('filechooser',{timeout:15000});
  await page.getByRole('menuitem',{name:'Upload',exact:true}).click();
  const chooser=await chooserPromise;
  await chooser.setFiles(ref.path);
  const afterUploadBlock=await signInOrCaptcha(page);
  if(afterUploadBlock)throw Error(afterUploadBlock);
  await page.waitForFunction(({prior,selector})=>{
   const added=[...document.querySelectorAll(selector)].filter(x=>!prior.includes(x.getAttribute('src')||''));
   return added.length>0;
  },{prior,selector:TILE},{timeout:90000});
  await Promise.allSettled(responseTasks);
  const added=await page.locator(TILE).evaluateAll((xs,prior)=>xs.map((x,index)=>({index,
   src:x.getAttribute('src')||'',html:x.parentElement?.outerHTML||''})).filter(x=>!prior.includes(x.src)),prior);
  if(added.length!==1)throw Error('REFERENCE_TRANSFER_UI_TILE_AMBIGUOUS');
  const ids=[...new Set(responses.flatMap(x=>x.ids))];
  if(ids.length!==1)throw Error('REFERENCE_TRANSFER_NETWORK_MEDIA_ID_UNVERIFIED');
  const mediaId=ids[0],tile=added[0];
  let tileEvidence=tile.html;
  if(!tileEvidence.includes(mediaId)) {
   await page.locator(TILE).nth(tile.index).click();
   tileEvidence=page.url();
  }
  if(!tileEvidence.includes(mediaId))throw Error('REFERENCE_TRANSFER_UI_MEDIA_ID_UNVERIFIED');
  const screenshot=path.join(evidenceDir,crypto.randomUUID()+'.png');
  await fastScreenshot(page,screenshot);
  const response=responses.find(x=>x.ids.includes(mediaId));
  return {targetMediaId:mediaId,evidence:{profile:identity.profile,sourceMediaId:identity.sourceMediaId,
   sourceSha256:identity.sourceSha256,networkMediaId:mediaId,tileMediaId:mediaId,
   networkSource:response.source,networkStatus:response.status,networkBodySha256:response.bodySha256,
   projectUrl,tileSourceSha256:sha256(tile.src),screenshot,screenshotSha256:sha256(fs.readFileSync(screenshot)),
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
