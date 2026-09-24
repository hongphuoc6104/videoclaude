"""Dedicated local-only environment; downloads public model weights on first use.

Two engines, picked by config tts_engine: 'gwen' (Gwen-TTS clone of a voice
folder under assets/voices/, run from .venv-gwen) or 'vieneu' (VieNeu v3 Turbo
presets, run from .venv-tts / .venv-tts-gpu)."""
import hashlib,json,os,re,sys,tempfile
from pathlib import Path
import numpy as np,soundfile as sf

CACHE_VERSION=1  # bump to invalidate every cached WAV (e.g. after a model/package upgrade)

def troughs(w,sr,thresh_db=-40.,win_s=0.01,min_s=0.10):
 """Silence runs strictly inside w, as (start,end) sample pairs."""
 win=max(1,int(win_s*sr));n=w.size//win
 if n==0:return []
 quiet=np.abs(w[:n*win]).reshape(n,win).mean(1)<=10**(thresh_db/20)
 runs=[];i=0
 while i<n:
  if not quiet[i]:i+=1;continue
  j=i
  while j<n and quiet[j]:j+=1
  if (j-i)*win>=min_s*sr:runs.append((i*win,j*win))
  i=j
 return [r for r in runs if r[0]>0 and r[1]<n*win]

def split_at(w,sr,texts):
 """Cut one scene waveform back into len(texts) sentence pieces, choosing the
 silence trough nearest each sentence's expected position and preferring long
 troughs. None when the audio cannot be split confidently."""
 k=len(texts)
 if k<2:return [w]
 runs=troughs(w,sr)
 if len(runs)<k-1:return None
 chars=np.cumsum([len(t) for t in texts],dtype=float)
 used=set();cuts=[]
 for b in range(k-1):
  want=w.size*chars[b]/chars[-1];best=score=None
  for idx,(s,e) in enumerate(runs):
   if idx in used:continue
   sc=abs((s+e)/2-want)/sr-0.5*min((e-s)/sr,0.8)
   if score is None or sc<score:best,score=idx,sc
  used.add(best);cuts.append(best)
 pieces=[];prev=0
 for idx in sorted(cuts):
  s,e=runs[idx];mid=int((s+e)//2)
  if mid<=prev:return None
  pieces.append(w[prev:mid]);prev=mid
 pieces.append(w[prev:])
 return pieces if all(p.size>int(.15*sr) for p in pieces) else None

def voiced_samples(w,sr,thresh_db=-40.,win_s=0.01):
 """Samples up to the end of the last audible window: the speech inside a chunk
 that also carries its following pause."""
 win=max(1,int(win_s*sr));n=w.size//win
 if n==0:return int(w.size)
 loud=np.nonzero(np.abs(w[:n*win]).reshape(n,win).mean(1)>10**(thresh_db/20))[0]
 return int(min(w.size,(loud[-1]+1)*win)) if loud.size else 0

def edge_silence(w,sr,thresh_db=-45.,win_s=0.01):
 """(lead, tail): silent samples at the start and end of w; all silent -> (len, 0).
 Same envelope rule as vieneu_utils.core_utils, kept here so the Gwen engine
 does not need VieNeu installed."""
 win=max(1,int(win_s*sr));n=w.size//win
 if n==0:return int(w.size),0
 above=np.flatnonzero(np.abs(w[:n*win]).reshape(n,win).mean(1)>10**(thresh_db/20))
 if not above.size:return int(w.size),0
 return int(above[0])*win,int(w.size)-(int(above[-1])+1)*win

def pause_pad_samples(prev,nxt,sr,pause_s):
 """Zeros to insert so the REAL pause (prev's trailing silence + zeros + nxt's
 leading silence) reaches pause_s; 0 when the takes already leave enough."""
 lead_prev,tail=edge_silence(prev,sr)
 if lead_prev==prev.size:tail=prev.size
 lead,_=edge_silence(nxt,sr)
 return max(0,int(pause_s*sr)-tail-lead)

def syllables(text):
 return max(1,len(re.findall(r'\w+',text)))

def plausible(w,sr,text):
 """Catches the two ways a sampled take goes wrong: it stops early (words
 dropped) or runs on (babble, repeated words). Measured Gwen takes of the
 horror passage speak at 0.22-0.36 s per syllable including edge silences."""
 lead,tail=edge_silence(w,sr);spoken=max(0,w.size-lead-tail)/sr;n=syllables(text)
 return 0.1*n<=spoken<=0.6*n+1.5

def cache_key(text,settings,package_version,sample_rate,cache_version=CACHE_VERSION,engine='vieneu'):
 """Content-addressed cache name: text + every setting that changes the audio +
 the installed model package version. Mirrors scripts/en_worker.py's cache_key,
 which is the correct pattern -- a cache keyed by scene/file NAME instead of by
 content will silently keep stale audio after a narration edit. Pure function
 (no vieneu import) so it stays importable/testable without the TTS runtime.
 """
 data=dict(engine=engine,package=package_version,language='vietnamese',
           sample_rate=sample_rate,text=text,settings=settings,cache_version=cache_version)
 return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()

ACRONYM_WHITELIST={'AI','VIP','TP','TP.HCM','UBND','CSGT','VTV','HTV','CEO','IELTS','TOEIC','ID','DNA','RNA','FBI','CIA'}

def normalize_text_for_tts(text):
 """Sanitize text for VieNeu/sea_g2p TTS:
 1. Normalize curly quotes/apostrophes to standard quotes/apostrophes.
 2. Lowercase all-caps English words (>= 2 letters) that are not recognized acronyms,
    preventing sea_g2p normalizer from spelling them out letter-by-letter as Vietnamese acronyms.
 """
 if not text:return text
 import re
 text=text.replace('“','"').replace('”','"').replace('’',"'").replace('‘',"'")
 def _repl(m):
  w=m.group(0)
  return w if w in ACRONYM_WHITELIST else w.lower()
 return re.sub(r'\b[A-Z]{2,}\b',_repl,text)

def resample(w,sr,target):
 """Change the sample rate with ffmpeg (soxr-free aresample, float in/out)."""
 if sr==target:return w
 import io,subprocess
 buf=io.BytesIO();sf.write(buf,w,sr,format='WAV',subtype='FLOAT')
 proc=subprocess.run(['ffmpeg','-v','error','-f','wav','-i','pipe:0','-af',f'aresample={target}','-c:a','pcm_f32le','-f','wav','pipe:1'],
                     input=buf.getvalue(),capture_output=True,check=True)
 return sf.read(io.BytesIO(proc.stdout),dtype='float32')[0]

def change_tempo(w,sr,speed):
 """Adjust audio tempo without changing pitch using ffmpeg atempo filter."""
 if abs(speed-1.0)<0.01:return w
 import io,subprocess
 buf_in=io.BytesIO()
 sf.write(buf_in,w,sr,format='WAV',subtype='PCM_16')
 cmd=['ffmpeg','-v','error','-f','wav','-i','pipe:0','-filter:a',f'atempo={speed}','-f','wav','pipe:1']
 proc=subprocess.run(cmd,input=buf_in.getvalue(),capture_output=True,check=True)
 buf_out=io.BytesIO(proc.stdout)
 out_w,_=sf.read(buf_out,dtype='float32')
 return out_w

class Gwen:
 """Gwen-TTS (g-group-ai-lab/gwen-tts-0.6B: Qwen3-TTS 0.6B finetuned on
 Vietnamese, MIT) cloning one voice folder: voice.json (model, reference text,
 sampling settings) + the reference clip. Exposes the few vieneu.Vieneu calls
 run() makes, so both engines share the cache, direction and assembly code.
 The codec speaks at 24 kHz; takes are resampled to OUTPUT_SR because the
 master step writes 48 kHz and refuses any frame-count change.

 One line per forward: batch 4 ran out of memory on a 4 GB RTX 3050 (measured
 2026-09-24; batch 1 peaks at 2.45 GB, ~1.3x real time). Sampling at the
 voice's temperature occasionally drops or repeats words, so every take is
 length-checked (plausible) and re-sampled up to `retries` times; notes lists
 each re-sample for tts-result.json."""
 OUTPUT_SR=48000
 def __init__(self,voice_dir,dtype='bfloat16',device='cuda:0',retries=2):
  import torch
  from qwen_tts import Qwen3TTSModel
  self.dir=Path(voice_dir);self.voice=json.loads((self.dir/'voice.json').read_text())
  ref=self.dir/self.voice['reference_audio']
  self.fingerprint=hashlib.sha256((self.dir/'voice.json').read_bytes()+ref.read_bytes()).hexdigest()[:16]
  self.model=Qwen3TTSModel.from_pretrained(self.voice['model'],device_map=device,dtype=getattr(torch,dtype),
                                           attn_implementation=self.voice.get('load',{}).get('attn_implementation','sdpa'))
  self.prompt=self.model.create_voice_clone_prompt(ref_audio=str(ref),ref_text=self.voice['reference_text'])
  self.native_sr=int(self.model.model.speech_tokenizer.get_output_sample_rate());self.sample_rate=self.OUTPUT_SR
  self._default_voice=self.dir.name;self.retries=retries;self.notes=[]
 def list_preset_voices(self):return [(self.voice.get('label',self.dir.name),self.dir.name)]
 def resolve_voice_name(self,name):return self.dir.name if name in (None,self.dir.name) else None
 def take(self,text):
  # 12.5 codec frames per second; the cap sits above plausible()'s ceiling so a
  # run-on take is caught by the check instead of silently clipped.
  cap=int(13*(0.8*syllables(text)+3))
  w,sr=self.model.generate_voice_clone(text=text,language=self.voice.get('language','Vietnamese'),
                                       voice_clone_prompt=self.prompt,**dict(self.voice['generate'],max_new_tokens=cap))
  return resample(np.asarray(w[0],dtype=np.float32),self.native_sr,self.sample_rate)
 def infer(self,text,**_):
  for attempt in range(self.retries+1):
   w=self.take(text)
   if plausible(w,self.sample_rate,text):return w
   self.notes.append(f'implausible take ({w.size/self.sample_rate:.1f} s for {syllables(text)} syllables), re-sampled: {text[:60]}')
  raise RuntimeError(f'Gwen could not read this line in {self.retries+1} tries: {text}')
 def infer_batch(self,texts,batch_size=1,**kw):return [self.infer(t,**kw) for t in texts]
 def save(self,w,path):sf.write(str(path),w,self.sample_rate)

def load_gwen(cfg):
 """tts_voice names a folder under assets/voices/. Needs CUDA: on CPU a story
 takes hours. Below compute capability 8 bf16 is emulated, so use fp32."""
 import torch
 if cfg.get('tts_device')=='cpu' or not torch.cuda.is_available():
  raise RuntimeError('tts_engine=gwen needs a CUDA GPU with about 2.5 GB free')
 dtype='bfloat16' if torch.cuda.get_device_capability(0)[0]>=8 else 'float32'
 voice_dir=Path(__file__).resolve().parent/'assets/voices'/str(cfg.get('tts_voice'))
 if not (voice_dir/'voice.json').exists():raise RuntimeError(f'No voice folder assets/voices/{cfg.get("tts_voice")}')
 tts=Gwen(voice_dir,dtype=dtype,retries=int(cfg.get('tts_check_retries',2)))
 return tts,dict(engine='gwen',backend='pytorch',precision=dtype,device=torch.cuda.get_device_name(0),batch_size=1)

def load_engine(cfg):
 """(Vieneu instance, engine description). tts_device: auto = CUDA when this
 interpreter has torch with a visible GPU, else ONNX/CPU; cuda = require GPU;
 cpu = always ONNX. tts_engine=gwen goes to load_gwen instead. The GPU path is PyTorch and batches chunks from many
 scenes into one forward (measured 6-7x real time on a Quadro P620 at batch 6,
 vs ~1x for ONNX/CPU on its Xeon E3-1240 v3). Below compute capability 8
 (Pascal/Turing) bf16 is emulated and fp16 crawls, so dtype is forced to fp32."""
 if cfg.get('tts_engine','vieneu')=='gwen':return load_gwen(cfg)
 from vieneu import Vieneu
 device=cfg.get('tts_device','auto')
 if device not in ('auto','cuda','cpu'):raise ValueError('tts_device must be auto, cuda or cpu')
 if device!='cpu':
  try:
   import torch;cuda=torch.cuda.is_available()
  except ImportError:cuda=False
  if cuda:
   dtype=cfg.get('tts_gpu_dtype','float32')
   if torch.cuda.get_device_capability(0)[0]<8:dtype='float32'
   batch=max(1,int(cfg.get('tts_batch_size',6)))
   tts=Vieneu(mode='v3turbo',backend='pytorch',device='cuda',dtype=dtype,max_batch_size=batch)
   return tts,dict(backend='pytorch',precision=dtype,device=torch.cuda.get_device_name(0),batch_size=batch)
  if device=='cuda':raise RuntimeError('tts_device=cuda but this environment has no usable CUDA GPU')
 precision=cfg.get('tts_precision','fp32')
 return Vieneu(mode='v3turbo',backend='onnx',precision=precision),dict(backend='onnx',precision=precision,device='cpu',batch_size=1)

def is_oom(ex):
 return 'out of memory' in str(ex).lower()

def run(source,out):
 from importlib.metadata import version
 source,out=Path(source),Path(out)
 req=json.loads(source.read_text())
 cfg=req['settings']
 st={}
 def use(tts,engine):
  voices={v:label for label,v in tts.list_preset_voices()}
  if not voices:raise RuntimeError('No local preset voices')
  voice_id=tts.resolve_voice_name(cfg.get('tts_voice')) or tts._default_voice
  if voice_id not in voices:raise RuntimeError('Requested local voice unavailable')
  st.update(tts=tts,engine=engine,voice=voice_id,label=voices[voice_id],sr=tts.sample_rate)
 use(*load_engine(cfg))
 fallbacks=[]

 # Step 1 (this change): cache filenames are content hashes instead of scene
 # names, so an edited narration or changed voice/settings can never reuse a
 # stale WAV. Step 2 (separate change): the cache directory itself moves to
 # runs/JOB/cache/tts so it survives across pilot.py's per-run revision dirs
 # -- until then it still lives under the revision (out/'raw') and buys
 # nothing across runs, but the keys are now safe to relocate.
 raw=Path(req['cache_dir']) if req.get('cache_dir') else out/'raw'
 raw.mkdir(parents=True,exist_ok=True)
 gwen=cfg.get('tts_engine','vieneu')=='gwen'
 package_version=version('qwen-tts' if gwen else 'vieneu')
 speed=float(cfg.get('tts_speed',1.0))

 def cached(text,retake,spd=None):
  """Cache file for text under the ACTIVE engine. backend/precision are part of
  the key: GPU and CPU takes differ, and a mid-run fallback must not mislabel
  audio. Batch size is not -- it only groups work, the take stays equivalent.
  spd is a directed per-line speed (see scripts/delivery.py); None = tts_speed."""
  e=st['engine'];spd=speed if spd is None else spd
  if gwen:
   # The voice folder's fingerprint covers its reference clip and sampling settings.
   key_settings=dict(voice=str(st['voice']),voice_fingerprint=st['tts'].fingerprint,precision=e['precision'],speed=spd,retake=retake)
   return raw/(cache_key(text,key_settings,package_version,st['sr'],engine='gwen')+'.wav')
  key_settings=dict(voice=str(st['voice']),temperature=cfg['tts_temperature'],top_p=cfg['tts_top_p'],
                    backend=e['backend'],precision=e['precision'],mode='v3turbo',speed=spd,retake=retake)
  return raw/(cache_key(text,key_settings,package_version,st['sr'])+'.wav')

 def generate(texts):
  """One waveform per text. GPU: all texts share batched forwards; on CUDA OOM
  the batch is halved, and at batch 1 the run falls back to ONNX/CPU."""
  while True:
   tts,e=st['tts'],st['engine']
   kw=dict(voice=st['voice'],temperature=cfg['tts_temperature'],top_p=cfg['tts_top_p'])
   if e['backend']!='pytorch':return [tts.infer(t,**kw) for t in texts]
   try:return tts.infer_batch(texts,batch_size=e['batch_size'],**kw)
   except Exception as ex:
    if not is_oom(ex):raise
    import gc,torch;gc.collect();torch.cuda.empty_cache()
    if gwen:raise RuntimeError('CUDA out of memory in Gwen-TTS (needs ~2.5 GB); close other GPU programs and rerun') from ex
    if e['batch_size']>1:
     fallbacks.append(f"CUDA OOM at batch {e['batch_size']}; retrying at {e['batch_size']//2}")
     e['batch_size']//=2;continue
    fallbacks.append('CUDA OOM at batch 1; switching to ONNX/CPU')
    st['tts']=tts=None;gc.collect();torch.cuda.empty_cache()
    use(*load_engine(dict(cfg,tts_device='cpu')))

 def prefetch(items):
  """Synthesize every (text, retake[, speed]) not yet cached in one batched call,
  so the GPU sees many scenes at once instead of one scene per forward."""
  todo=[];seen=set()
  for item in items:
   text,retake,spd=(tuple(item)+(None,))[:3]
   f=cached(text,retake,spd)
   if (text,retake,spd) in seen or (f.exists() and f.stat().st_size>1000):continue
   seen.add((text,retake,spd));todo.append((text,retake,spd))
  if not todo:return
  # Gwen's infer_batch reads one line at a time. A whole-story prefetch would
  # otherwise keep every finished waveform in RAM until the last line, losing
  # hours of work if a later line fails or the process is interrupted.
  chunk_size=10 if gwen else len(todo)
  for offset in range(0,len(todo),chunk_size):
   chunk=todo[offset:offset+chunk_size]
   wavs=generate([normalize_text_for_tts(t) for t,_,_ in chunk])
   for (text,retake,spd),w in zip(chunk,wavs):
    k=speed if spd is None else spd
    if isinstance(w,np.ndarray) and abs(k-1.0)>=0.01:w=change_tempo(w,st['sr'],k)
    target=cached(text,retake,spd)
    fd,temp_name=tempfile.mkstemp(prefix='.tts-',suffix='.wav',dir=raw)
    os.close(fd);temp=Path(temp_name)
    try:
     st['tts'].save(w,str(temp))
     os.replace(temp,target)
    finally:temp.unlink(missing_ok=True)

 def synth(text,retake=0,spd=None):
  """Synthesize once, cached by content hash so a crashed/rerun revision
  resumes without re-paying, and an edited scene never plays back old audio.

  `retake` is how many times this scene's delivery was rejected. Same words,
  same settings, so without it the cache would return the identical take and
  "read this one better" would be a no-op."""
  prefetch([(text,retake,spd)])
  return sf.read(str(cached(text,retake,spd)),dtype='float32')[0]

 def scene_level(sc):
  """Directed scenes (per-line speeds/gains) are always read line by line."""
  return 'speeds' not in sc and cfg.get('tts_scene_synthesis',True) and len(sc['narration'])<=cfg.get('tts_max_chars',256)
 def lines(sc):
  return list(zip(sc['texts'],[int(sc.get('retake',0))]*len(sc['texts']),sc.get('speeds') or [None]*len(sc['texts'])))
 first=[]
 for sc in req['scenes']:
  first+=[(sc['narration'],int(sc.get('retake',0)))] if scene_level(sc) else lines(sc)
 prefetch(first)

 # Scene-level synthesis keeps the intonation arc across sentences: vieneu infers
 # each chunk independently, so one call per sentence resets the prosody every
 # time. Split the waveform afterwards to keep one subtitle cue per sentence.
 sr=st['sr'];flat=[];modes=[]
 for sc in req['scenes']:
  texts=sc['texts'];pieces=None;retake=int(sc.get('retake',0))
  if scene_level(sc):
   pieces=split_at(synth(sc['narration'],retake),sr,texts)
  if pieces is None:
   prefetch(lines(sc))
   pieces=[synth(*x) for x in lines(sc)]
   # Directed level per line (quoted speech, a closing line read low). Mastering
   # is one static gain for the whole track, so these differences survive.
   pieces=[w*np.float32(10**(g/20)) for w,g in zip(pieces,sc.get('gains') or [0]*len(pieces))]
   for i in range(len(pieces)-1):
    pad=pause_pad_samples(pieces[i],pieces[i+1],sr,float(sc['gaps'][i]))
    pieces[i]=np.concatenate([pieces[i],np.zeros(pad,dtype=np.float32)])
   modes.append({'scene_id':sc['scene_id'],'mode':'per-sentence'})
  else:modes.append({'scene_id':sc['scene_id'],'mode':'scene'})
  flat.extend([{'scene_id':sc['scene_id'],'text':t,'wav':w,'voiced':voiced_samples(w,sr)} for t,w in zip(texts,pieces)])
  flat[-1]['pause']=float(sc['tail'])

 # The pause belongs to the chunk that is ending, so the timeline stays contiguous
 # (pilot.py:161) and the subtitle cue holds through the breath.
 results=[]
 for i,x in enumerate(flat):
  w=x['wav']
  if 'pause' in x:
   nxt=flat[i+1]['wav'] if i+1<len(flat) else np.zeros(1,dtype=np.float32)
   w=np.concatenate([w,np.zeros(pause_pad_samples(w,nxt,sr,x['pause']),dtype=np.float32)])
  path=f'segment-{i:03}.wav'
  sf.write(str(out/path),w,sr,subtype='PCM_16')
  results.append({'scene_id':x['scene_id'],'text':x['text'],'path':path,'voiced':x['voiced']/sr})
 fallbacks+=getattr(st['tts'],'notes',[])
 (out/'tts-result.json').write_text(json.dumps({'voice':str(st['voice']),'label':st['label'],'engine':st['engine'],'fallbacks':fallbacks,'settings':cfg,'scenes':modes,'segments':results},ensure_ascii=False,indent=2))

if __name__=='__main__':
 run(Path(sys.argv[1]),Path(sys.argv[2]))
