/**
 * Chrome-profile rotation when a Flow account runs out of image quota.
 *
 * Pure policy and bookkeeping only: no browser code lives here. The session owns the
 * browser switch; queue-runner decides when a switch is needed. Everything a switch
 * decides is written to disk (exhaustion ledger + append-only switch log) so later runs
 * skip exhausted profiles and every switch is auditable.
 *
 * Hard stops are never rotated around: CAPTCHA, sign-in required, storage failure and
 * any unclassified error stop the queue exactly as before.
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));

/**
 * Case-insensitive regular expressions, checked in this order (first match wins).
 * The real Flow wording for an exhausted account has not been observed yet, so the quota
 * list is deliberately specific; add the observed text via `failure_patterns.quota` in
 * browser-profiles.json or machine.local.json. `storage` precedes `quota` because the
 * browser's own localStorage error ("QuotaExceededError ... exceeded the quota") is a
 * storage failure of the tool page, not an account quota: that image was generated.
 */
export const DEFAULT_FAILURE_PATTERNS=Object.freeze({
 captcha:['captcha','unusual traffic','verify (that )?you.?re (not a robot|human)'],
 login:['sign[ -]?in (is )?required','please sign in','not signed in','login required','unauthenticated','\\b401\\b','session (has )?expired','reauth'],
 storage:['persistence failure','quotaexceedederror','exceeded the quota','localstorage','storage (is )?full','failed to (persist|save state)'],
 quota:['resource_exhausted','quota','daily limit','generation limit','usage limit','limit reached','reached (your|the) (daily |usage |generation |image )?limit','out of credits','not enough credits','insufficient credits','no (more )?credits'],
 rate_limit:['rate.?limit','too many requests','\\b429\\b'],
});
const ORDER=['captcha','login','storage','quota','rate_limit'];

/** 'captcha' | 'login' | 'storage' | 'quota' | 'rate_limit' | 'other' | null (no text). */
export function classifyFailure(text,patterns=DEFAULT_FAILURE_PATTERNS) {
 const value=String(text??'').trim();
 if(!value)return null;
 for(const kind of ORDER) {
  for(const source of patterns[kind]||DEFAULT_FAILURE_PATTERNS[kind]||[]) {
   if(new RegExp(source,'i').test(value))return kind;
  }
 }
 return 'other';
}

/** Every error string the tool keeps for one queue item. */
export function itemErrorText(item) {
 return [item?.error,item?.errorMessage,item?.pauseReason].filter(x=>typeof x==='string'&&x.trim()).join(' | ');
}

/** State-level messages (a paused tool may explain why outside any item). */
export function stateErrorText(state) {
 const parts=[state?.error,state?.errorMessage,state?.pauseReason,state?.lastError].filter(x=>typeof x==='string'&&x.trim());
 return parts.join(' | ');
}

function readJson(file,fallback) {
 try {return JSON.parse(fs.readFileSync(file,'utf8'));} catch(error) {if(error.code==='ENOENT')return fallback;throw error;}
}

/**
 * Rotation policy from browser-profiles.json with machine.local.json on top (per-profile
 * entries merge key by key). `home` is the profile the session is configured for; it owns
 * the configured tool URL and the canonical reference media.
 */
export function loadRotationPolicy({shared=path.join(here,'browser-profiles.json'),local=path.join(here,'machine.local.json')}={}) {
 const a=readJson(shared,{}),b=readJson(local,{});
 const profiles={};
 for(const name of new Set([...Object.keys(a.profiles||{}),...Object.keys(b.profiles||{})]))
  profiles[name]={...(a.profiles||{})[name],...(b.profiles||{})[name]};
 const merged={...a,...b};
 const patterns={...DEFAULT_FAILURE_PATTERNS};
 for(const [kind,list] of Object.entries({...(a.failure_patterns||{}),...(b.failure_patterns||{})}))
  if(Array.isArray(list)&&list.length)patterns[kind]=[...(DEFAULT_FAILURE_PATTERNS[kind]||[]),...list.map(String)];
 return {
  enabled:merged.automatic_account_switching===true,
  home:merged.flow_profile_directory||'Default',
  priority:Array.isArray(merged.priority)&&merged.priority.length?merged.priority:[merged.flow_profile_directory||'Default'],
  homeToolUrl:merged.tool_url||null,
  resetHours:Number.isFinite(merged.quota_reset_hours)&&merged.quota_reset_hours>0?merged.quota_reset_hours:null,
  profiles,patterns,
 };
}

/** When an exhausted profile may be tried again: next local midnight, or a fixed number of hours if configured. */
export function resetTimeFor(now=new Date(),resetHours=null) {
 if(resetHours)return new Date(now.getTime()+resetHours*3600000);
 const next=new Date(now);next.setHours(24,0,0,0);return next;
}

/** Persistent per-profile exhaustion record. One small JSON file, rewritten atomically. */
export class ProfileLedger {
 constructor(file){this.file=file;}
 read(){return readJson(this.file,{schema:'vp-profile-exhaustion-1',profiles:{}});}
 isExhausted(profile,now=new Date()) {
  const entry=this.read().profiles[profile];
  return Boolean(entry&&new Date(entry.resetAt).getTime()>now.getTime());
 }
 entry(profile){return this.read().profiles[profile]||null;}
 markExhausted(profile,evidence,{now=new Date(),resetHours=null}={}) {
  const data=this.read();
  data.profiles[profile]={exhaustedAt:now.toISOString(),resetAt:resetTimeFor(now,resetHours).toISOString(),evidence};
  fs.mkdirSync(path.dirname(this.file),{recursive:true});
  const temp=`${this.file}.${process.pid}.tmp`;
  fs.writeFileSync(temp,JSON.stringify(data,null,2)+'\n');fs.renameSync(temp,this.file);
  return data.profiles[profile];
 }
}

/** The tool URL a profile generates with, or null when the profile is not set up for Flow. */
export function toolUrlFor(policy,profile) {
 if(policy.profiles[profile]?.tool_url)return policy.profiles[profile].tool_url;
 return profile===policy.home?policy.homeToolUrl:null;
}

/**
 * The first profile in priority order that is usable now: not the current one, not
 * exhausted, and configured with a tool URL. Returns null when none is left.
 */
export function nextProfile(policy,ledger,current,now=new Date()) {
 for(const profile of policy.priority) {
  if(profile===current||ledger.isExhausted(profile,now))continue;
  if(policy.profiles[profile]?.enabled===false)continue;
  if(!toolUrlFor(policy,profile))continue;
  return profile;
 }
 return null;
}

/**
 * The references a request may carry on `profile`. A Flow media id belongs to the account
 * that created it; another account cannot be assumed to read it. A reference is usable when
 * its owner is this profile, the profile maps it (`media_ids`), or the profile declares
 * `reference_media: "shared"`. Owners come from the attempt journals; media with no journal
 * owner (the registered mascot, older runs) belong to the home profile.
 * Returns {ok:true, character, base} with mapped ids, or {ok:false, reason}.
 */
export function referencesFor(policy,profile,request,owners=new Map()) {
 const settings=policy.profiles[profile]||{};
 const map=settings.media_ids||{};
 const out={ok:true};
 for(const role of ['character','base']) {
  const ref=request[role];
  if(!ref){out[role]=null;continue;}
  const owner=owners.get(ref.mediaId)||policy.home;
  if(owner===profile||settings.reference_media==='shared')out[role]=ref;
  else if(map[ref.mediaId])out[role]={...ref,mediaId:map[ref.mediaId],sourceMediaId:ref.mediaId};
  else return {ok:false,reason:`REFERENCE_MEDIA_NOT_ON_PROFILE: ${role} ${ref.mediaId} belongs to ${owner}; map it in profiles["${profile}"].media_ids or declare reference_media "shared"`};
 }
 return out;
}

/** Append-only audit line for every profile decision (switch, exhaustion, refusal). */
export function appendSwitchLog(file,record) {
 fs.mkdirSync(path.dirname(file),{recursive:true});
 const line=JSON.stringify({at:new Date().toISOString(),...record})+'\n';
 const fd=fs.openSync(file,'a',0o600);
 try {fs.writeFileSync(fd,line);fs.fsyncSync(fd);} finally {fs.closeSync(fd);}
 return JSON.parse(line);
}
