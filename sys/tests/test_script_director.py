"""Script director uses a fake agy; no external request or production state."""
import copy
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pilot import Pilot, ROOT, Blocked, read
import workflow
from scripts import agy_pipeline
from scripts import long_script


class ScriptDirectorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for name in ('schemas', '.agents', 'renderer', 'examples', 'scripts'):
            shutil.copytree(ROOT / name, root / name)
        for name in ('pilot.py', 'workflow.py', 'machine_review.py', 'image_pipeline.py',
                     'content_contract.py', 'prompt_templates.py', 'adapters.py', 'config.json',
                     'AGENTS.md', 'GEMINI.md'):
            shutil.copy(ROOT / name, root / name)
        (root / 'horror').mkdir()
        shutil.copy(ROOT / 'horror/narration-style.md', root / 'horror/narration-style.md')
        self.p = Pilot(root)
        self.addCleanup(self.p.db.close)
        self.job = 'director-test'
        brief = read(ROOT / 'examples/story-v3/brief.json')
        brief['script_director'] = {'enabled': True, 'max_rewrites': 2, 'min_each': 1, 'min_total': 10}
        workflow.new(self.p, self.job, brief)
        _, revision, stamp = self.p.brief(self.job)
        self.first = read(ROOT / 'examples/story-v3/content.json')
        self.first.update(brief_revision=revision, brief_hash=stamp)
        self.second = copy.deepcopy(self.first)
        scene = self.second['scenes'][0]
        old = scene['narration']
        new = old.replace('giữ sự tôn trọng', 'giữ trọn sự tôn trọng')
        scene['narration'] = new
        scene['beats'][0]['anchor']['vi']['quote'] = new
        self.second['coverage'][0]['quote'] = new
        self.second['revision_response'] = [self.sd_response(1)]
        self.third = copy.deepcopy(self.second)
        scene = self.third['scenes'][0]
        newer = new.replace('giữ trọn sự tôn trọng', 'giữ thật trọn sự tôn trọng')
        scene['narration'] = newer
        scene['beats'][0]['anchor']['vi']['quote'] = newer
        self.third['coverage'][0]['quote'] = newer
        self.third['revision_response'] = [self.sd_response(2)]

    @staticmethod
    def sd_response(writer_round, status='addressed'):
        return {'request_id': f'SD{writer_round}-pacing_rhythm', 'status': status,
                'explanation': 'The requested line was revised.' if status == 'addressed' else 'Could not resolve the pacing.',
                'scene_ids': ['SC01']}

    @staticmethod
    def public_payload(payload):
        copy_of_payload = copy.deepcopy(payload)
        copy_of_payload['revision_response'] = []
        return copy_of_payload

    @staticmethod
    def grade(passed):
        scores = {key: {'score': 2, 'evidence': ['SC01: Đồng nghiệp vừa làm sai'], 'notes': 'Specific observation.'}
                  for key in ('dread_escalation', 'pacing_rhythm', 'climax_payoff',
                              'oral_storytelling_voice', 'cliche_budget', 'hook_per_scene')}
        if not passed:
            scores['pacing_rhythm']['score'] = 0
        return {'scores': scores, 'revision_requests': [] if passed else [
            {'criterion': 'pacing_rhythm', 'scene_ids': ['SC01'],
             'instruction': 'Separate the scare line after two short sentences.'}]}

    def fake(self, pass_on_round):
        prompts = []
        detail_count = 0

        def invoke(prompt, schema, workspace, **kwargs):
            nonlocal detail_count
            prompts.append(prompt)
            properties = schema['properties']
            if 'scores' in properties:
                return {'structured_output': self.grade(detail_count >= pass_on_round)}
            if 'outline' in properties and 'schema_version' not in properties:
                return {'structured_output': {'outline': self.first['outline']}}
            detail_count += 1
            source = self.first if detail_count == 1 else self.second if detail_count == 2 else self.third
            return {'structured_output': copy.deepcopy(source)}

        return invoke, prompts

    def run_with_fake(self, pass_on_round):
        fake, prompts = self.fake(pass_on_round)
        with patch('scripts.script_director.enabled', return_value=True), \
                patch('scripts.agy_pipeline.invoke', side_effect=fake):
            result = agy_pipeline.generate(self.p, self.job)
        return result, prompts

    def test_full_horror_script_critic_has_bounded_cli_options(self):
        from scripts import script_director
        brief = dict(self.p.brief(self.job)[0], video_type='horror_story')
        with tempfile.TemporaryDirectory() as folder:
            with patch('scripts.agy_pipeline.invoke', return_value={
                    'structured_output': self.grade(True)}) as invoke:
                record = script_director.assess(self.p.root, brief,
                                                self.first, Path(folder), 0)
        self.assertTrue(record['pass'])
        self.assertEqual(invoke.call_args.kwargs, {'timeout': 600, 'effort': 'high'})

    def test_failed_first_round_regenerates_full_draft_and_anchors(self):
        result, prompts = self.run_with_fake(2)
        self.assertEqual(self.p.rows(self.job)['content']['state'], 'awaiting_review')
        self.assertEqual(len(prompts), 6)  # plan, writer, critic, plan, writer, critic
        self.assertIn('freshly place every coverage/claim quote', prompts[4])
        self.assertIn('SD1-pacing_rhythm', prompts[3])
        self.assertIn('SD1-pacing_rhythm', prompts[4])
        self.assertEqual(read(self.p.job(self.job) / 'draft/content.json'), self.public_payload(self.second))
        attempt = next((self.p.job(self.job) / 'agent-attempts').iterdir())
        self.assertFalse(read(attempt / 'script-director-round-0.json')['pass'])
        self.assertTrue(read(attempt / 'script-director-round-1.json')['pass'])
        self.assertEqual(read(attempt / 'script-director-revision-round-1.json')['writer_responses']['SD1-pacing_rhythm'][0]['status'], 'addressed')

    def test_auto_exhaustion_never_submits_draft(self):
        # The workflow mode is immutable, so use a fresh job for auto.
        self.p.db.close()
        root = self.p.root
        self.p = Pilot(root)
        self.addCleanup(self.p.db.close)
        self.job = 'director-auto'
        brief = read(ROOT / 'examples/story-v3/brief.json')
        brief['script_director'] = {'enabled': True, 'max_rewrites': 2, 'min_each': 1, 'min_total': 10}
        workflow.new(self.p, self.job, brief, 'auto')
        _, revision, stamp = self.p.brief(self.job)
        for content in (self.first, self.second, self.third):
            content.update(brief_revision=revision, brief_hash=stamp)
        fake, prompts = self.fake(99)
        with patch('scripts.script_director.enabled', return_value=True), \
                patch('scripts.agy_pipeline.invoke', side_effect=fake):
            with self.assertRaisesRegex(Blocked, 'SCRIPT_DIRECTOR_NEEDS_ATTENTION'):
                agy_pipeline.generate(self.p, self.job)
        self.assertEqual(len(prompts), 9)
        self.assertFalse((self.p.job(self.job) / 'draft/content.json').exists())

    def test_review_exhaustion_lists_findings(self):
        result, prompts = self.run_with_fake(99)
        self.assertEqual(self.p.rows(self.job)['content']['state'], 'awaiting_review')
        self.assertEqual(len(prompts), 9)
        questions = read(self.p.job(self.job) / 'draft/content.json')['open_questions']
        self.assertTrue(any('pacing_rhythm' in q for q in questions))

    def test_short_writer_cannot_omit_sd_response(self):
        self.second['revision_response'] = []
        fake, _ = self.fake(2)
        with patch('scripts.script_director.enabled', return_value=True), \
                patch('scripts.agy_pipeline.invoke', side_effect=fake):
            with self.assertRaisesRegex(Blocked, 'missing writer response for SD1-pacing_rhythm'):
                agy_pipeline.generate(self.p, self.job)
        self.assertFalse((self.p.job(self.job) / 'draft/content.json').exists())

    def test_writer_cannot_claim_addressed_without_narration_change(self):
        self.second = copy.deepcopy(self.first)
        self.second['revision_response'] = [self.sd_response(1)]
        fake, _ = self.fake(2)
        with patch('scripts.script_director.enabled', return_value=True), \
                patch('scripts.agy_pipeline.invoke', side_effect=fake):
            with self.assertRaisesRegex(Blocked, 'claims addressed without narration change'):
                agy_pipeline.generate(self.p, self.job)

    def test_unresolved_sd_response_reaches_review_open_questions(self):
        self.second['revision_response'] = [self.sd_response(1, 'unresolved')]
        self.run_with_fake(2)
        payload = read(self.p.job(self.job) / 'draft/content.json')
        self.assertTrue(any('SD1-pacing_rhythm' in question for question in payload['open_questions']))
        self.assertEqual(payload['revision_response'], [])

    def test_unresolved_sd_response_stops_auto(self):
        self.p.db.close()
        root = self.p.root
        self.p = Pilot(root)
        self.addCleanup(self.p.db.close)
        self.job = 'director-auto-unresolved'
        brief = read(ROOT / 'examples/story-v3/brief.json')
        brief['script_director'] = {'enabled': True, 'max_rewrites': 2, 'min_each': 1, 'min_total': 10}
        workflow.new(self.p, self.job, brief, 'auto')
        _, revision, stamp = self.p.brief(self.job)
        for content in (self.first, self.second, self.third):
            content.update(brief_revision=revision, brief_hash=stamp)
        self.second['revision_response'] = [self.sd_response(1, 'unresolved')]
        fake, _ = self.fake(2)
        with patch('scripts.script_director.enabled', return_value=True), \
                patch('scripts.agy_pipeline.invoke', side_effect=fake):
            with self.assertRaisesRegex(Blocked, 'SCRIPT_DIRECTOR_NEEDS_ATTENTION: writer left'):
                agy_pipeline.generate(self.p, self.job)
        self.assertFalse((self.p.job(self.job) / 'draft/content.json').exists())

    def run_long(self, omit_sd=False):
        critic_round = 0
        calls = []

        def invoke(prompt, schema, workspace, **kwargs):
            nonlocal critic_round
            calls.append(prompt)
            properties = schema['properties']
            if 'scores' in properties:
                critic_round += 1
                return {'structured_output': self.grade(critic_round == 2)}
            if 'characters' in properties and 'scenes' not in properties:
                return {'structured_output': {'outline': self.first['outline'],
                                              'characters': self.first['characters']}}
            label = prompt.split('\nWrite scenes ', 1)[1].split(' ', 1)[0]
            first, last = label.split('–')
            source = self.first if critic_round == 0 else self.second
            ids = [s['id'] for s in source['scenes'] if first <= s['id'] <= last]
            return {'structured_output': {'scenes': copy.deepcopy([s for s in source['scenes'] if s['id'] in ids]),
                                          'coverage': copy.deepcopy([c for c in source['coverage'] if c['scene_id'] in ids]),
                                          'claims': [], 'revision_response': copy.deepcopy(source['revision_response']) if 'SC01' in ids and not omit_sd else [], 'open_questions': [],
                                          'story_so_far': 'Events of ' + ', '.join(ids) + '.'}}

        with patch('scripts.script_director.enabled', return_value=True), \
                patch('scripts.agy_pipeline.invoke', side_effect=invoke), \
                patch.object(long_script, 'chunk_size', return_value=2):
            agy_pipeline.generate(self.p, self.job)
        return calls

    def test_long_script_rewrites_every_chunk_with_fresh_anchors(self):
        calls = self.run_long()
        self.assertEqual(len(calls), 10)  # plan + 3 chunks + critic, twice
        self.assertIn('SD1-pacing_rhythm', calls[6])
        self.assertEqual(read(self.p.job(self.job) / 'draft/content.json'), self.public_payload(self.second))

    def test_long_writer_cannot_hide_missing_response_behind_merge_default(self):
        with self.assertRaisesRegex(Blocked, 'missing writer response for SD1-pacing_rhythm'):
            self.run_long(omit_sd=True)
        self.assertFalse((self.p.job(self.job) / 'draft/content.json').exists())


if __name__ == '__main__':
    unittest.main()
