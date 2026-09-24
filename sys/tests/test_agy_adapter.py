import copy,json,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pilot import Pilot,ROOT,Blocked,read
from scripts.agy_pipeline import generate,invoke

class AgyAdapterTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  for n in ['schemas','.agents','renderer','tests','examples','scripts']:shutil.copytree(ROOT/n,self.root/n)
  for n in ['pilot.py','workflow.py','machine_review.py','image_pipeline.py','prompt_templates.py','content_contract.py','config.json','AGENTS.md','GEMINI.md']:shutil.copy(ROOT/n,self.root/n)
  self.p=Pilot(self.root);self.p.new('agy',read(ROOT/'examples/m1/brief.json'))
 def tearDown(self):self.p.db.close();self.tmp.cleanup()
 def approve_control(self):self.p.approve('agy','control',1,'TEST ONLY')
 def response(self):
  d=read(ROOT/'examples/m1/content.json');_,rev,h=self.p.brief('agy');d.update(brief_revision=rev,brief_hash=h)
  return {'status':'SUCCESS','conversation_id':'TEST-ID','structured_output':d}
 def test_gate_before_external_request(self):
  with patch('scripts.agy_pipeline.invoke') as call:
   with self.assertRaises(Blocked):generate(self.p,'agy')
   call.assert_not_called()
 def test_valid_generation_stops_for_review(self):
  self.approve_control()
  with patch('scripts.agy_pipeline.invoke',return_value=self.response()):self.assertEqual(generate(self.p,'agy')['action'],'review')
  self.assertEqual(self.p.rows('agy')['content']['state'],'awaiting_review')
  with patch('scripts.agy_pipeline.invoke') as call:
   with self.assertRaises(Blocked):generate(self.p,'agy')
   call.assert_not_called()
 def test_invalid_response_no_submission(self):
  self.approve_control();data=self.response();data['structured_output']['coverage']=[]
  with patch('scripts.agy_pipeline.invoke',return_value=data):
   with self.assertRaises(ValueError):generate(self.p,'agy')
  self.assertEqual(self.p.rows('agy')['content']['revision'],0)
  self.assertFalse((self.p.job('agy')/'draft/content.json').exists())
 def test_timeout_no_retry(self):
  self.approve_control()
  with patch('scripts.agy_pipeline.invoke',side_effect=Blocked('AGY_TIMEOUT')) as call:
   with self.assertRaises(Blocked):generate(self.p,'agy')
   self.assertEqual(call.call_count,1)
  attempts=list((self.p.job('agy')/'agent-attempts').glob('*/attempt.json'))
  self.assertEqual(read(attempts[0])['state'],'blocked')
 def test_protocol_rejects_success_without_structured_output(self):
  from types import SimpleNamespace
  with patch('scripts.agy_pipeline.shutil.which',return_value='/fake/agy'),patch('scripts.agy_pipeline.Path.home',return_value=self.root),patch('scripts.agy_pipeline.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{"status":"SUCCESS"}',stderr='')):
   with self.assertRaisesRegex(Blocked,'missing structured_output'):invoke('x',{},self.root)
 def test_cli_passes_bounded_timeout_and_optional_effort(self):
  from types import SimpleNamespace
  result=SimpleNamespace(returncode=0,stdout='{"status":"SUCCESS","structured_output":{}}',stderr='')
  with patch('scripts.agy_pipeline.shutil.which',return_value='/fake/agy'),patch('scripts.agy_pipeline.Path.home',return_value=self.root),patch('scripts.agy_pipeline.subprocess.run',return_value=result) as run:
   invoke('outline',{},self.root,timeout=300,effort='medium')
  args=run.call_args.args[0]
  self.assertEqual(args[args.index('--print-timeout')+1],'300s')
  self.assertEqual(args[args.index('--effort')+1],'medium')
  self.assertEqual(run.call_args.kwargs['timeout'],315)
  with patch('scripts.agy_pipeline.shutil.which',return_value='/fake/agy'),patch('scripts.agy_pipeline.Path.home',return_value=self.root),patch('scripts.agy_pipeline.subprocess.run',return_value=result) as run:
   invoke('other',{},self.root)
  self.assertNotIn('--effort',run.call_args.args[0])
  with self.assertRaisesRegex(ValueError,'AGY_EFFORT'):
   invoke('bad',{},self.root,effort='unbounded')
 def test_rehearsal_wrapper_forwards_stage_options(self):
  from types import SimpleNamespace
  from unittest.mock import Mock
  from scripts.rehearse_content import instrument_invoke
  original=Mock(return_value={'status':'SUCCESS','structured_output':{}})
  adapter=SimpleNamespace(invoke=original)
  records=[]
  instrument_invoke(adapter,records)
  adapter.invoke('outline',{},self.root,timeout=360,effort='high')
  original.assert_called_once_with('outline',{},self.root,conversation=None,timeout=360,effort='high')
  self.assertEqual(records[0]['print_timeout_seconds'],360)
  self.assertEqual(records[0]['effort'],'high')
 def test_near_timeout_records_safe_diagnostic_and_does_not_retry(self):
  from types import SimpleNamespace
  stdout=json.dumps({'status':'SUCCESS','response':'unfinished scene with SECRET_TOKEN'})
  result=SimpleNamespace(returncode=0,stdout=stdout,stderr='SECRET_TOKEN')
  with patch('scripts.agy_pipeline.shutil.which',return_value='/fake/agy'),patch('scripts.agy_pipeline.Path.home',return_value=self.root),patch('scripts.agy_pipeline.subprocess.run',return_value=result) as run,patch('scripts.agy_pipeline.time.monotonic',side_effect=[0,299]):
   with self.assertRaisesRegex(Blocked,'AGY_TIMEOUT_INCOMPLETE'):invoke('x',{},self.root,timeout=300)
  self.assertEqual(run.call_count,1)
  diagnostics=list(self.root.glob('agy-diagnostic-*.json'))
  self.assertEqual(len(diagnostics),1)
  details=read(diagnostics[0])
  self.assertEqual(details['reason'],'near_print_timeout_without_structured_output')
  self.assertEqual(details['response_bytes'],len('unfinished scene with SECRET_TOKEN'.encode()))
  self.assertNotIn('SECRET_TOKEN',diagnostics[0].read_text())
 def test_api_provider_blocked(self):
  from pilot import write
  write(self.root/'.gemini/antigravity-cli/settings.json',{'modelProvider':'gemini'})
  with patch('scripts.agy_pipeline.Path.home',return_value=self.root),patch('scripts.agy_pipeline.shutil.which',return_value='/fake/agy'),patch('scripts.agy_pipeline.subprocess.run') as call:
   with self.assertRaisesRegex(Blocked,'AGY_API_PROVIDER'):invoke('x',{},self.root)
   call.assert_not_called()
 def test_detailed_prompt_includes_humanizer_and_content_skill(self):
  self.approve_control()
  calls=[]
  def fake_invoke(prompt,schema,workspace,conversation=None,timeout=180):
   calls.append(prompt);return self.response()
  with patch('scripts.agy_pipeline.invoke',side_effect=fake_invoke):generate(self.p,'agy')
  self.assertEqual(len(calls),1)
  prompt=calls[0]
  humanizer_text=(self.root/'.agents/skills/vp-content/references/narration-style.md').read_text()
  content_text=(self.root/'.agents/skills/vp-content/SKILL.md').read_text()
  self.assertEqual(prompt.count(humanizer_text),1)
  self.assertIn(content_text,prompt)
 def test_narration_reference_has_no_rewrite_reply_format(self):
  skill_path=self.root/'.agents/skills/vp-content/references/narration-style.md'
  self.assertTrue(skill_path.exists())
  text=skill_path.read_text()
  self.assertIn('# Lời dẫn tự nhiên',text)
  for banned in ['Định dạng trả lời','Bản viết lại','Đã sửa gì','Đã xóa hẳn','Cần bạn xác nhận']:
   self.assertNotIn(banned,text)
 def test_ai_tells_reference_exists_but_not_loaded_into_prompt(self):
  ref_path=self.root/'.agents/skills/vp-content/references/ai-tells.md'
  self.assertTrue(ref_path.exists())
  ref_text=ref_path.read_text()
  self.assertIn('oai_citation',ref_text)
  self.approve_control()
  calls=[]
  def fake_invoke(prompt,schema,workspace,conversation=None,timeout=180):
   calls.append(prompt);return self.response()
  with patch('scripts.agy_pipeline.invoke',side_effect=fake_invoke):generate(self.p,'agy')
  self.assertNotIn('oai_citation',calls[0])
  self.assertNotIn(ref_text,calls[0])
