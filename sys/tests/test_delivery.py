"""Voice direction (scripts/delivery.py) and its path through tts_worker and the mix."""
import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import soundfile as sf
import sound,tts_worker
from pilot import read,write
from scripts.delivery import dialogue_flags,direct,split_dialogue
from tests.test_audio import SR,fake_vieneu

PROFILE={k:v for k,v in json.loads((Path(__file__).resolve().parents[1]/'horror/channel.json').read_text())['delivery'].items() if k!='note'}

def scene(sid,reqs,*texts):
 return {'scene_id':sid,'requirements':list(reqs),'texts':list(texts)}

class DirectionTests(unittest.TestCase):
 def test_quoted_speech_and_written_beats_get_their_own_chunks(self):
  self.assertEqual(split_dialogue(['Ông lão ngồi bật dậy: “Ai đó?”','Tôi hé tia sáng… Nó đang mở.']),
                   ['Ông lão ngồi bật dậy:','“Ai đó?”','Tôi hé tia sáng…','Nó đang mở.'])

 def test_one_word_knocks_stay_with_the_surrounding_sentence(self):
  self.assertEqual(split_dialogue(['Ba tiếng gõ bật ra từ phía sau mặt kính: “Cốc… cốc… cốc.”']),
                   ['Ba tiếng gõ bật ra từ phía sau mặt kính: “Cốc… cốc… cốc.”'])
  self.assertEqual(split_dialogue(['Hai giây im bặt.','An nín thở.','“Cốc.”','Tiếng thứ tư bật lên.']),
                   ['Hai giây im bặt.','An nín thở. “Cốc.”','Tiếng thứ tư bật lên.'])

 def test_multi_sentence_quote_stays_dialogue_until_it_closes(self):
  self.assertEqual(dialogue_flags(['Tôi gào lên:','“Đừng cười nữa!','Tôi nhận tội rồi!”','Vị khách lùi lại.']),
                   [False,True,True,False])

 def test_scene_style_follows_the_strongest_required_point(self):
  out=direct([scene('SC01',['R1'],'Mở.'),scene('SC02',['R3','R4'],'Căng.'),scene('SC03',['R6'],'Khép.')],PROFILE)
  self.assertEqual([d['style'] for d in out],['host_open','climax','host_close'])
  self.assertEqual(out[-1]['tail'],PROFILE['end_tail'])
  self.assertEqual(out[0]['tail'],PROFILE['styles']['host_open']['tail'])

 def test_climax_reads_differently_from_setup(self):
  setup,climax=direct([scene('SC02',['R2'],'Một câu kể bình thường khá dài về căn nhà.','Câu thứ hai cũng dài như vậy thôi.'),
                        scene('SC08',['R4'],'Một câu kể bình thường khá dài về căn nhà.','Câu thứ hai cũng dài như vậy thôi.')],PROFILE)
  self.assertNotEqual(setup['speeds'][0],climax['speeds'][0])
  self.assertEqual(setup['gains'],[0.0,0.0],'setup has no quiet closing line')
  self.assertIn('reveal',climax['cues'][-1])
  self.assertEqual(climax['gains'][-1],PROFILE['lines']['reveal']['gain_db'])
  self.assertLess(climax['speeds'][-1],climax['speeds'][0])
  self.assertGreaterEqual(climax['gaps'][-1],PROFILE['lines']['reveal']['pause_before'])

 def test_dialogue_is_set_apart_and_quieter_unless_shouted(self):
  d=direct([scene('SC05',['R3'],'Ông lão ngồi bật dậy trong bóng tối mịt mùng: “Ai đó?”','Tôi đứng chôn chân suốt một tiếng đồng hồ trong đêm.')],PROFILE)[0]
  self.assertEqual(d['texts'][1],'“Ai đó?”')
  self.assertEqual(d['gains'][1],PROFILE['lines']['dialogue']['gain_db'])
  self.assertGreaterEqual(d['gaps'][0],PROFILE['lines']['dialogue']['pause_before'])
  self.assertGreaterEqual(d['gaps'][1],PROFILE['lines']['dialogue']['pause_after'])
  shout=direct([scene('SC09',['R4'],'Tôi gào lên: “Đừng cười nữa!','Tôi nhận tội rồi!”','Vị khách lùi sát vào vách tường và nhìn tôi.')],PROFILE)[0]
  self.assertEqual(shout['gains'][1:3],[PROFILE['lines']['dialogue']['shout_gain_db']]*2)
  self.assertEqual(shout['gaps'][1],PROFILE['lines']['dialogue']['inner'])

 def test_short_lines_questions_and_beats_hold_longer(self):
  d=direct([scene('SC06',['R3'],'Tôi bước lại gần chiếc giường gỗ trong căn phòng tối om.','Nó đang mở.','Có ai ở đó không?','Tôi chờ…','Rồi một tiếng gõ khẽ vang lên từ phía dưới sàn.')],PROFILE)[0]
  L=PROFILE['lines']
  self.assertGreaterEqual(d['gaps'][0],L['short']['pause_before'])
  self.assertIn('short',d['cues'][1])
  self.assertGreaterEqual(d['gaps'][2],L['question_pause'])
  self.assertGreaterEqual(d['gaps'][3],L['beat_pause'])

 def test_mood_scales_speed_and_pauses(self):
  base=direct([scene('SC02',['R2'],'Câu một khá dài.','Câu hai.')],PROFILE,'psychological')[0]
  tense=direct([scene('SC02',['R2'],'Câu một khá dài.','Câu hai.')],PROFILE,'tense')[0]
  self.assertGreater(tense['speeds'][0],base['speeds'][0])
  self.assertLess(tense['gaps'][0],base['gaps'][0])

 def test_words_are_never_changed(self):
  texts=['Ông lão ngồi bật dậy: “Ai đó?” rồi im.','Tôi hé tia sáng… Nó đang mở.']
  d=direct([scene('SC05',['R3'],*texts)],PROFILE)[0]
  self.assertEqual(''.join(d['texts']).replace(' ',''),''.join(texts).replace(' ',''))

class DirectedWorkerTests(unittest.TestCase):
 def run_worker(self,d,scenes):
  req={'settings':dict(tts_voice='Voice One',tts_temperature=.6,tts_top_p=.9,tts_backend='onnx',tts_precision='fp32',tts_device='cpu'),
       'cache_dir':str(d/'cache'),'scenes':scenes}
  (d/'out').mkdir();write(d/'out/request.json',req);tts_worker.run(d/'out/request.json',d/'out')
  return read(d/'out/tts-result.json')

 def test_directed_lines_get_their_speed_level_and_pause(self):
  with fake_vieneu() as Fake,tempfile.TemporaryDirectory() as d:
   d=Path(d)
   res=self.run_worker(d,[{'scene_id':'SC01','narration':'A. A.','texts':['A.','A.'],'speeds':[1.0,.9],'gains':[0,-6],'gaps':[1.0],'tail':.5}])
   self.assertEqual(res['scenes'],[{'scene_id':'SC01','mode':'per-sentence'}])
   self.assertEqual(len(list((d/'cache').glob('*.wav'))),2,'same words at another speed is another take')
   a,_=sf.read(str(d/'out'/res['segments'][0]['path']));b,_=sf.read(str(d/'out'/res['segments'][1]['path']))
   self.assertAlmostEqual(np.abs(b).max()/np.abs(a).max(),10**(-6/20),places=2)
   self.assertAlmostEqual(a.size/SR,.2+1.0,places=2)
   self.assertAlmostEqual(res['segments'][0]['voiced'],.2,places=2)

 def test_undirected_request_keeps_its_cache_keys(self):
  """Old jobs (no delivery) must still hit the cache written before direction existed."""
  with fake_vieneu() as Fake,tempfile.TemporaryDirectory() as d:
   d=Path(d);sc={'scene_id':'SC01','narration':'A.','texts':['A.'],'gaps':[],'tail':.3}
   self.run_worker(d,[sc])
   key=tts_worker.cache_key('A.',dict(voice='v1',temperature=.6,top_p=.9,backend='onnx',precision='fp32',mode='v3turbo',speed=1.0,retake=0),'9.9.9-test',SR)
   self.assertTrue((d/'cache'/(key+'.wav')).exists())

class SpeechEndTests(unittest.TestCase):
 def test_bed_and_anchors_use_where_the_voice_stops(self):
  spans=[{'text':'Một hai ba.','start':0.,'end':3.,'speech_end':1.}]
  self.assertAlmostEqual(sound.anchor_seconds('Một hai ba.',{'quote':'ba','occurrence':1},spans),8/11,places=3)

class HorrorBriefTests(unittest.TestCase):
 def test_horror_brief_carries_the_profile_and_a_matching_speech_rate(self):
  from horror import bank
  from content_contract import validate_brief
  from pilot import ROOT
  cfg=bank.channel();seed=bank.seeds()[0]
  b=bank.make_brief(seed,cfg,{'length':'4-6','pov':'first','mood':'tense','aspect_ratio':'16:9'})
  validate_brief(ROOT,b)
  self.assertEqual(b['delivery']['mood'],'tense')
  self.assertNotIn('note',b['delivery'])
  self.assertTrue(b['planning']['speech_rates']['vi']['includes_pauses'])

if __name__=='__main__':unittest.main()
