/** Persistent local session; fixed commands only, no arbitrary browser execution. */
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
import {browserConfig,debugEndpoint,findToolFrame,inspect,machineConfig,safeResults,toolUrl,verifyBrowser} from './controller.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const socketPath=path.join(here,'results','controller','session.sock');

export class Session {
  constructor(connect,verify=async()=>null){this.connect=connect;this.verify=verify;this.identity=null;this.browser=null;this.attempted=false;}
  async start(){
    if(this.browser?.isConnected()) {this.identity=await this.verify(this.browser);return {status:'connected',reused:true,identity:this.identity};}
    if(this.attempted) throw Error('Session ended: no automatic reconnect; restart the service explicitly');
    this.attempted=true;
    this.browser=await this.connect();
    try {this.identity=await this.verify(this.browser);} catch(e) {await this.stop();throw e;}
    return {status:'connected',reused:false,identity:this.identity};
  }
  status(){return {status:this.browser?.isConnected()?'connected':this.attempted?'disconnected':'not_connected'};}
  async stop(){if(this.browser) await this.browser.close();this.browser=null;this.identity=null;}
}
/** Ask the running Chrome (same user-data-dir, so the same process) to open a window in `profile`. */
function launchChrome(executable,args){
  const child=spawn(executable,args,{detached:true,stdio:'ignore'});
  child.on('error',()=>{});child.unref();
}

/** A sign-in page or a visible CAPTCHA challenge on the tab: both are hard stops, never worked around. */
export async function signInOrCaptcha(page){
  const url=page.url();
  if(/^https:\/\/accounts\.google\.com\//.test(url)||/ServiceLogin|\/signin[/?]/i.test(url))return `FLOW_SIGN_IN_REQUIRED: ${url.split('?')[0]}`;
  for(const frame of page.frames()){
    if(!/\/recaptcha\/.*\/bframe/.test(frame.url()))continue;
    try {if(await (await frame.frameElement()).isVisible())return 'FLOW_CAPTCHA_REQUIRED: challenge visible';} catch {}
  }
  return null;
}

/**
 * Open the tool in another Chrome profile of the same user-data-dir and bind that tab.
 * Chrome forwards the command line to the running process, which opens a new window in the
 * profile; the tab is found by a one-time marker on the tool URL. Navigate that same tab
 * to chrome://version to check its profile path and executable, then return to the tool.
 * Chrome turns an externally launched chrome://version URL into a new tab on this machine.
 * It never signs in, never
 * types anything and never closes the previous profile's tab (its tool state stays for
 * reconciliation).
 */
export async function openProfileTab({browser,dataDir,profile,executable,url,launch=launchChrome,findFrame=findToolFrame,timeoutMs=30000,pollMs=250,exists=fs.existsSync}){
  if(path.basename(profile)!==profile||profile==='.'||profile==='..')throw Error('Invalid profile directory');
  if(!url)throw Error(`PROFILE_TOOL_URL_MISSING: ${profile}`);
  // Chrome would silently create a new, signed-out profile for an unknown directory.
  if(!exists(path.join(dataDir,profile)))throw Error(`PROFILE_NOT_FOUND: ${path.join(dataDir,profile)}`);
  const nonce=crypto.randomUUID();
  const markerUrl=new URL(url);
  markerUrl.searchParams.set('vp-switch',nonce);
  launch(executable,[`--user-data-dir=${dataDir}`,`--profile-directory=${profile}`,markerUrl.toString()]);
  const deadline=Date.now()+timeoutMs;let page=null;
  while(!page&&Date.now()<deadline){
    page=browser.contexts().flatMap(c=>c.pages()).find(p=>p.url().includes(nonce))||null;
    if(!page)await new Promise(resolve=>setTimeout(resolve,pollMs));
  }
  if(!page)throw Error(`PROFILE_SWITCH_TAB_NOT_FOUND: ${profile}`);
  await page.goto('chrome://version/',{waitUntil:'domcontentloaded',timeout:30000});
  const observedProfile=(await page.locator('#profile_path').innerText()).trim();
  const observedExecutable=(await page.locator('#executable_path').innerText()).trim();
  if(path.resolve(observedProfile)!==path.join(dataDir,profile))throw Error(`PROFILE_PATH_MISMATCH: expected ${profile}, got ${observedProfile}`);
  if(observedExecutable!==executable)throw Error('EXECUTABLE_PATH_MISMATCH');
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:30000});
  const blocked=await signInOrCaptcha(page);
  if(blocked)throw Error(blocked);
  try {await findFrame(page);}
  catch(error){throw Error((await signInOrCaptcha(page))||`TOOL_NOT_READY_ON_PROFILE: ${profile}: ${error.message}`);}
  return {identity:{observedProfile,executable:observedExecutable,verifiedAt:new Date().toISOString()},page,profile,toolUrl:url};
}

async function serve(){
  safeResults();
  if(fs.existsSync(socketPath)) throw Error('Session socket exists: use status; do not start a second session');
  const config={...JSON.parse(fs.readFileSync(path.join(here,'../../config.json'))),...JSON.parse(fs.readFileSync(path.join(here,'browser-profiles.json')))};
  const selected=browserConfig(config);
  let bound=null;
  const session=new Session(async()=>{
    const endpoint=debugEndpoint(fs.readFileSync(path.join(selected.dataDir,'DevToolsActivePort'),'utf8'));
    return chromium.connectOverCDP(endpoint,{timeout:60000});
  }, async browser=>{
    const context=browser.contexts()[0];
    if(!context) throw Error('NO_CHROME_CONTEXT');
    if(bound) {
      if(bound.page.isClosed()) throw Error('BOUND_TAB_CLOSED');
      return bound.identity;
    }
    bound={...await verifyBrowser(browser,config,true),profile:selected.profile,toolUrl,switchProfile};
    if(bound.page.isClosed())throw Error('BOUND_TAB_CLOSED');
    return bound.identity;
  });
  // Used by queue-runner only after Flow answered "out of quota" and rotation is enabled.
  const switchProfile=async(target,url)=>{
    if(!session.browser?.isConnected())throw Error('SESSION_DISCONNECTED');
    const next=await openProfileTab({browser:session.browser,dataDir:selected.dataDir,profile:target,url,
      executable:{...config,...machineConfig}.executable_path||'/opt/google/chrome/google-chrome'});
    bound={...next,switchProfile};
    console.log(JSON.stringify({event:'profile_switched',profile:target,at:new Date().toISOString()}));
    return bound;
  };
  const ensureBoundPage=async()=>{
    if(bound?.page && !bound.page.isClosed()) return bound;
    throw Error('BOUND_TAB_CLOSED: reconnect and verify the configured profile; do not replace the tab silently');
  };
  let queue=Promise.resolve();
  const server=net.createServer(client=>{
    let data='';
    client.on('error',()=>{});
    client.on('data',chunk=>{
      data+=chunk;
      if(data.length>8192){client.destroy();return;}
      if(!data.includes('\n'))return;
      client.removeAllListeners('data');
      const command=data.trim();
      // status only reads session state: answer at once instead of queueing behind a long generation.
      if(command==='status'){client.end(JSON.stringify(session.status())+'\n');return;}
      queue=queue.then(async()=>{
        try {
          let result;
          if(command==='connect') {
            result=await session.start();
            await ensureBoundPage();
            if(bound?.page && !bound.page.url().startsWith(bound.toolUrl||toolUrl)) {
              await bound.page.goto(bound.toolUrl||toolUrl,{waitUntil:'domcontentloaded',timeout:30000});
            }
            result={...result,profile:bound?.profile||null};
          }
          else if(command==='inspect') {
            if(session.status().status!=='connected') throw Error('CONNECT_FIRST: session unavailable');
            await ensureBoundPage();
            result=await inspect(config,session.browser,bound);
            fs.writeFileSync(path.join(safeResults(),`session-inspect-${Date.now()}.json`),JSON.stringify(result,null,2));
          } else if(['editor-inspect','reference-inspect'].includes(command) || command.startsWith('tool-snapshot')) {
            if(session.status().status!=='connected')throw Error('CONNECT_FIRST');
            await ensureBoundPage();
            const operations=await import('./browser-operations.mjs?revision='+Date.now());
            result=await operations.runOperation(command,bound);
          } else if(command==='stop') {
            if(bound && !bound.page.isClosed())await bound.page.close();
            await session.stop();result={status:'stopped'};
          } else throw Error('Unsupported session command');
          client.end(JSON.stringify(result)+'\n');
          if(command==='stop')server.close();
        }catch(e){client.end(JSON.stringify({status:'blocked',reason:e.message})+'\n');}
      });
    });
  });
  server.on('close',()=>{if(fs.existsSync(socketPath))fs.unlinkSync(socketPath);});
  server.on('error',e=>{console.error(e.message);process.exitCode=2;});
  server.listen(socketPath,()=>{fs.chmodSync(socketPath,0o600);console.log('Persistent session ready; run session.mjs connect once.');});
  for(const sig of ['SIGTERM','SIGINT'])process.on(sig,async()=>{await session.stop().catch(()=>{});server.close();});
}
async function client(command){
  await new Promise((resolve,reject)=>{
    const socket=net.createConnection(socketPath,()=>socket.write(command+'\n'));
    let response='';
    socket.setTimeout(180000,()=>socket.destroy(Error('SESSION_COMMAND_TIMEOUT: inspect status before retrying')));
    socket.on('data',d=>{response+=d;process.stdout.write(d);});
    socket.on('end',()=>{try {if(JSON.parse(response).status==='blocked')process.exitCode=2;}catch{process.exitCode=2;}resolve();});socket.on('error',reject);
  });
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 const cmd=process.argv[2];
 (cmd==='serve'?serve():client(cmd||'status')).catch(e=>{console.error(e.message);process.exitCode=2;});
}
