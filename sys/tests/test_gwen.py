"""Gwen-TTS engine in tts_worker (qwen_tts and torch faked; no model weights)."""
import contextlib,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pilot import read,write
import adapters,tts_worker
import numpy as np
from tests.test_audio import fake_torch

SR=24000

def speech(seconds,lead=.1,tail=.2):
 """A take: silence, a tone body, silence."""
 body=(np.sin(np.arange(int(SR*seconds))*.05)*.3).astype(np.float32)
 return np.concatenate([np.zeros(int(SR*lead),np.float32),body,np.zeros(int(SR*tail),np.float32)])

class FakeQwen:
 """Stands in for qwen_tts.Qwen3TTSModel. takes: queue of body lengths (s) to
 return, else a plausible 0.25 s per syllable; oom: raise a CUDA OOM."""
 calls=[];takes=[];oom=False;loads=[]
 def __init__(self):self.model=types.SimpleNamespace(speech_tokenizer=types.SimpleNamespace(get_output_sample_rate=lambda:SR))
 @classmethod
 def from_pretrained(cls,name,**kw):cls.loads.append(dict(name=name,**kw));return cls()
 def create_voice_clone_prompt(self,ref_audio,ref_text):return ['prompt']
 def generate_voice_clone(self,text,language,voice_clone_prompt,**kw):
  if FakeQwen.oom:raise RuntimeError('CUDA out of memory. Tried to allocate 228.00 MiB')
  FakeQwen.calls.append(dict(text=text,**kw))
  secs=FakeQwen.takes.pop(0) if FakeQwen.takes else .25*tts_worker.syllables(text)
  return [speech(secs)],SR

@contextlib.contextmanager
def fake_gwen(capability=(8,6)):
 FakeQwen.calls=[];FakeQwen.takes=[];FakeQwen.oom=False;FakeQwen.loads=[]
 mod=types.ModuleType('qwen_tts');mod.Qwen3TTSModel=FakeQwen
 with fake_torch(capability=capability) as t,patch.dict(sys.modules,{'qwen_tts':mod}),patch('importlib.metadata.version',return_value='0.1.1-test'):
  t.bfloat16='bf16';t.float32='fp32'
  yield FakeQwen

class GwenWorkerTests(unittest.TestCase):
 def req(self,cache,texts=('Câu một.','Câu hai.'),**settings):
  cfg=dict(tts_engine='gwen',tts_voice='pham-tuyen-gwen',tts_temperature=.65,tts_top_p=.95,tts_device='auto')
  cfg.update(settings)
  return {'settings':cfg,'cache_dir':str(cache),'scenes':[{'scene_id':'SC01','narration':' '.join(texts),'texts':list(texts),
          'speeds':[1.0]*len(texts),'gains':[0]*len(texts),'gaps':[.5]*(len(texts)-1),'tail':.3}]}

 def synth(self,req,out):
  out.mkdir(parents=True,exist_ok=True);src=out/'request.json';write(src,req)
  tts_worker.run(src,out);return read(out/'tts-result.json')

 def test_reads_line_by_line_with_the_voice_folder_settings(self):
  with fake_gwen() as Fake,tempfile.TemporaryDirectory() as d:
   meta=self.synth(self.req(Path(d)/'cache'),Path(d)/'rev1')
   self.assertEqual([c['text'] for c in Fake.calls],['Câu một.','Câu hai.'])
   self.assertEqual(Fake.calls[0]['temperature'],.7,'sampling comes from voice.json, not the VieNeu settings')
   self.assertEqual(meta['engine']['engine'],'gwen');self.assertEqual(meta['voice'],'pham-tuyen-gwen')
   self.assertEqual(Fake.loads[0]['dtype'],'bf16');self.assertEqual(len(meta['segments']),2)
   import soundfile as sf
   self.assertEqual(sf.info(str(Path(d)/'rev1'/meta['segments'][0]['path'])).samplerate,48000,'the master step writes 48 kHz and rejects any frame-count change')

 def test_cache_hits_on_rerun_and_is_separate_from_vieneu(self):
  with fake_gwen() as Fake,tempfile.TemporaryDirectory() as d:
   d=Path(d);self.synth(self.req(d/'cache'),d/'rev1');self.synth(self.req(d/'cache'),d/'rev2')
   self.assertEqual(len(Fake.calls),2,'second run must be served from cache')
   vieneu=tts_worker.cache_key('Câu một.',{},'0.1.1-test',SR)
   self.assertNotIn(vieneu,[p.stem for p in (d/'cache').glob('*.wav')])

 def test_run_on_take_is_resampled(self):
  with fake_gwen() as Fake,tempfile.TemporaryDirectory() as d:
   Fake.takes=[30.0]
   meta=self.synth(self.req(Path(d)/'cache',texts=('Ai đó?',)),Path(d)/'rev1')
   self.assertEqual(len(Fake.calls),2);self.assertEqual(len(meta['fallbacks']),1)
   self.assertIn('re-sampled',meta['fallbacks'][0])

 def test_line_that_never_reads_right_fails_the_run(self):
  with fake_gwen() as Fake,tempfile.TemporaryDirectory() as d:
   Fake.takes=[.01]*3
   with self.assertRaisesRegex(RuntimeError,'could not read'):self.synth(self.req(Path(d)/'cache',texts=('Nó đang mở trừng trừng trong đêm.',)),Path(d)/'rev1')
   self.assertEqual(len(Fake.calls),3)

 def test_token_cap_follows_line_length(self):
  with fake_gwen() as Fake,tempfile.TemporaryDirectory() as d:
   self.synth(self.req(Path(d)/'cache',texts=('Ai đó?','Tôi nín thở, đứng chôn chân suốt một tiếng đồng hồ.')),Path(d)/'rev1')
   short,long_=[c['max_new_tokens'] for c in Fake.calls]
   self.assertLess(short,long_);self.assertLess(long_,2048)

 def test_oom_stops_instead_of_falling_back_to_vieneu(self):
  with fake_gwen() as Fake,tempfile.TemporaryDirectory() as d:
   Fake.oom=True
   with self.assertRaisesRegex(RuntimeError,'close other GPU programs'):self.synth(self.req(Path(d)/'cache'),Path(d)/'rev1')

 def test_needs_cuda(self):
  mod=types.ModuleType('qwen_tts');mod.Qwen3TTSModel=FakeQwen
  with fake_torch(cuda=False),patch.dict(sys.modules,{'qwen_tts':mod}),tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(RuntimeError,'needs a CUDA GPU'):self.synth(self.req(Path(d)/'cache'),Path(d)/'rev1')

 def test_pascal_uses_float32(self):
  with fake_gwen(capability=(6,1)) as Fake,tempfile.TemporaryDirectory() as d:
   meta=self.synth(self.req(Path(d)/'cache'),Path(d)/'rev1')
   self.assertEqual(Fake.loads[0]['dtype'],'fp32');self.assertEqual(meta['engine']['precision'],'float32')

 def test_adapter_uses_gwen_env(self):
  root=Path('/x')
  self.assertEqual(adapters.tts_python(root,{'tts_engine':'gwen','tts_device':'auto'}),root/'.venv-gwen/bin/python')

class PauseTests(unittest.TestCase):
 def test_pause_counts_existing_silence(self):
  a,b=speech(1,lead=0,tail=.2),speech(1,lead=.1,tail=0)
  self.assertAlmostEqual(tts_worker.pause_pad_samples(a,b,SR,.5)/SR,.2,delta=.02)
  self.assertEqual(tts_worker.pause_pad_samples(a,b,SR,.2),0)

 def test_plausible_bounds(self):
  self.assertTrue(tts_worker.plausible(speech(2.5),SR,'Tôi nín thở, đứng chôn chân suốt một giờ.'))
  self.assertFalse(tts_worker.plausible(speech(30),SR,'Ai đó?'))
  self.assertFalse(tts_worker.plausible(speech(.2),SR,'Tôi nín thở, đứng chôn chân suốt một tiếng đồng hồ.'))

if __name__=='__main__':unittest.main()
