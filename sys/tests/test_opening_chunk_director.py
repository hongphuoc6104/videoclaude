"""First-chunk gate tests use fake agy replies; no production job is run."""

import copy
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pilot import Blocked, ROOT, read, write
from scripts import long_script, opening_chunk_director, outline_director


def sample():
    brief = read(ROOT / 'examples/story-v3/brief.json')
    brief['video_type'] = 'horror_story'
    brief['script_director'] = {'enabled': True, 'max_rewrites': 2, 'min_each': 1, 'min_total': 10}
    content = read(ROOT / 'examples/story-v3/content.json')
    plan = {'outline': content['outline'], 'characters': content['characters']}
    chunk = {'scenes': content['scenes'][:2],
             'coverage': [c for c in content['coverage'] if c['scene_id'] in ('SC01', 'SC02')],
             'claims': [], 'revision_response': [], 'open_questions': [],
             'story_so_far': 'The speaker introduces a room; a lodger enters.'}
    return brief, plan, chunk


def h001c_excerpt():
    """Abbreviated interrupted opening; deliberately independent of the old run directory."""
    brief, plan, chunk = sample()
    brief['topic'] = 'Tiếng gõ sau tấm gương'
    brief['required_points'][0]['text'] = 'Open without locating the source of the knocks.'
    brief['required_points'].append(
        {'id': 'R4', 'text': 'Later reveal: the knocks originate behind the mirror.'})
    plan['outline'][0]['purpose'] = 'A host raises a question about old belongings without naming the source of the knocks.'
    plan['outline'][-1]['purpose'] = 'The knocks originate behind the mirror at the climax.'
    plan['characters'][0] = {
        'id': 'CH01', 'name': 'Người dẫn chuyện',
        'appearance': 'Round white head, two oval black eyes, open smile with coral tongue.',
        'outfit': 'One light ocean blue short-sleeved shirt.'}
    plan['characters'][1] = {
        'id': 'CH02', 'name': 'An', 'appearance': 'Gaunt student with round glasses.',
        'outfit': 'Grey t-shirt, dark jeans, and unbuttoned dark blue plaid overshirt outdoors.'}
    scene1, scene2 = chunk['scenes']
    scene1['narration'] = ('Có bao giờ bạn tự hỏi về món đồ cũ trong phòng trọ? '
                           'Câu chuyện đêm nay bắt đầu ở nơi có tiếng gõ lạ lùng sau tấm gương soi.')
    scene1['images'] = [
        {'id': 'SC01_I1', 'description': 'Host with a warm slight smile by a desk lamp.',
         'preserve': 'A mirror facing away on the host table.',
         'change': 'Establish the host table.'},
        {'id': 'SC01_I2', 'description': 'Mirror reflects an empty rented room.',
         'preserve': 'Same mirror and table.',
         'change': 'Focus on the mirror without turning it or moving rooms.', 'based_on': 'SC01_I1'},
    ]
    scene1['beats'] = [
        {'id': 'SC01_B1', 'image_id': 'SC01_I1',
         'purpose': 'Show the host by the lamp.', 'anchor': {'vi': {'quote': 'Có bao giờ bạn tự hỏi', 'occurrence': 1}}},
        {'id': 'SC01_B2', 'image_id': 'SC01_I2',
         'purpose': 'Show the rusty nail beside the mirror.',
         'anchor': {'vi': {'quote': 'tiếng gõ lạ lùng', 'occurrence': 1}}},
    ]
    scene2['narration'] = 'An đi vào con hẻm để tìm phòng trọ rẻ.'
    scene2['images'] = [
        {'id': 'SC02_I1', 'description': 'An in a grey t-shirt and jeans walks outside in the alley.',
         'preserve': 'The wet alley.', 'change': 'An enters the frame.'},
    ]
    scene2['beats'] = [
        {'id': 'SC02_B1', 'image_id': 'SC02_I1', 'purpose': 'An walks into the alley.',
         'anchor': {'vi': {'quote': 'An đi vào con hẻm', 'occurrence': 1}}},
    ]
    return brief, plan, chunk


def evidence(scene_id, source, item_id, quote):
    return {'scene_id': scene_id, 'source': source, 'item_id': item_id, 'quote': quote}


def grade(brief, plan, chunk, failures=()):
    first = chunk['scenes'][0]
    second = chunk['scenes'][1]
    opening_evidence = [evidence('SC01', 'narration', '', first['narration'][-61:]),
                        evidence('SC01', 'outline_purpose', '', plan['outline'][0]['purpose'][:50])]
    if 'opening_without_spoiler' in failures:
        opening_evidence.append(evidence(plan['outline'][-1]['scene_id'], 'outline_purpose', '',
                                         plan['outline'][-1]['purpose'][:50]))
    criteria = {
        'opening_without_spoiler': {'met': 'opening_without_spoiler' not in failures,
            'evidence': opening_evidence,
            'notes': 'The opening either protects or exposes the late reveal.'},
        'character_visual_identity': {'met': 'character_visual_identity' not in failures,
            'evidence': [evidence('SC01', 'image_description', 'SC01_I1', first['images'][0]['description']),
                         evidence('SC01', 'canonical_mascot', '', 'friendly open smile with coral tongue'),
                         evidence('SC02', 'image_description', 'SC02_I1', second['images'][0]['description']),
                         evidence('SC02', 'character_outfit', 'CH02', plan['characters'][1]['outfit'])],
            'notes': 'The host smile and the outside outfit must match identity sources.'},
        'image_continuity': {'met': 'image_continuity' not in failures,
            'evidence': [evidence('SC01', 'image_preserve', 'SC01_I1', first['images'][0]['preserve']),
                         evidence('SC01', 'image_description', 'SC01_I2', first['images'][1]['description'])],
            'notes': 'The facing-away host mirror cannot reflect another room without a transition.'},
        'beat_image_alignment': {'met': 'beat_image_alignment' not in failures,
            'evidence': [evidence('SC01', 'beat_purpose', 'SC01_B2', first['beats'][1]['purpose']),
                         evidence('SC01', 'image_description', 'SC01_I2', first['images'][1]['description'])],
            'notes': 'The beat promises a rusty nail which the image never describes.'},
    }
    return {'pass': True, 'criteria': criteria,
            'revision_requests': [
                {'criterion': key, 'scene_ids': ['SC01'] if key != 'character_visual_identity' else ['SC01', 'SC02'],
                 'instruction': 'Revise the named scenes to resolve this specific mismatch.'}
                for key in failures]}


class OpeningChunkCriticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.brief, self.plan, self.chunk = h001c_excerpt()

    def assess(self, response):
        with patch('scripts.agy_pipeline.invoke', return_value={'structured_output': response}):
            return opening_chunk_director.assess(ROOT, self.brief, self.plan, self.chunk, self.out, 0)

    def test_abbreviated_h001c_failures_have_exact_evidence_and_computed_verdict(self):
        failures = opening_chunk_director.CRITERIA
        record = self.assess(grade(self.brief, self.plan, self.chunk, failures))
        self.assertFalse(record['pass'], 'the fake model pass flag cannot override failed criteria')
        self.assertEqual(record['failed_criteria'], list(failures))
        self.assertTrue((self.out / 'opening-chunk-candidate-round-0.json').exists())
        self.assertTrue((self.out / 'opening-chunk-critique-raw-round-0.json').exists())
        self.assertEqual(read(self.out / 'opening-chunk-critique-round-0.json')['input_sha256'],
                         opening_chunk_director.hash_input(self.brief, self.plan, self.chunk))

    def test_canonical_mascot_evidence_accepts_declared_id(self):
        response = grade(self.brief, self.plan, self.chunk, ('character_visual_identity',))
        mascot_citation = next(row for row in response['criteria']['character_visual_identity']['evidence']
                               if row['source'] == 'canonical_mascot')
        mascot_citation['item_id'] = 'channel-mascot'
        record = self.assess(response)
        self.assertEqual(record['failed_criteria'], ['character_visual_identity'])

    def test_valid_subtle_hook_can_pass_and_hash_detects_changed_sources(self):
        self.chunk['scenes'][0]['narration'] = 'Có bao giờ bạn tự hỏi về món đồ cũ trong phòng trọ? Một tiếng gõ vang lên ở nơi không ai nhìn thấy.'
        response = grade(self.brief, self.plan, self.chunk)
        response['pass'] = False
        record = self.assess(response)
        self.assertTrue(record['pass'])
        self.assertTrue(opening_chunk_director.saved_pass_matches(self.brief, self.plan, self.chunk, record))
        changed = copy.deepcopy(self.chunk)
        changed['story_so_far'] += ' Another event.'
        self.assertFalse(opening_chunk_director.saved_pass_matches(self.brief, self.plan, changed, record))
        changed_plan = copy.deepcopy(self.plan)
        changed_plan['outline'][0]['purpose'] += ' New direction.'
        self.assertFalse(opening_chunk_director.saved_pass_matches(self.brief, changed_plan, self.chunk, record))

    def test_false_quote_or_missing_conflict_side_blocks_protocol(self):
        for mutation in ('wrong_quote', 'missing_beat_image'):
            with self.subTest(mutation=mutation):
                response = grade(self.brief, self.plan, self.chunk, ('beat_image_alignment',))
                if mutation == 'wrong_quote':
                    response['criteria']['opening_without_spoiler']['evidence'][0]['quote'] = 'invented'
                else:
                    response['criteria']['beat_image_alignment']['evidence'].pop()
                with self.assertRaisesRegex(Blocked, 'OPENING_CHUNK_DIRECTOR_PROTOCOL'):
                    self.assess(response)


class OpeningChunkFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.brief, self.plan, self.chunk = sample()

    def out(self, name):
        folder = self.base / 'agent-attempts' / name
        folder.mkdir(parents=True)
        return folder

    def generate(self, out, writer, critic):
        with patch.object(long_script, 'chunk_size', return_value=2), \
             patch('scripts.agy_pipeline.invoke', side_effect=writer), \
             patch.object(outline_director, 'assess', return_value={
                 'pass': True, 'outline_sha256': outline_director.hash_plan(self.plan)}), \
             patch.object(opening_chunk_director, 'assess', side_effect=critic):
            return long_script.generate(ROOT, self.brief, 1, 'test-hash', 'Write story.',
                                        'Style.', [], None, None, out)

    def writer(self, prompts, rewrite=False, stop_after=None):
        content = read(ROOT / 'examples/story-v3/content.json')
        plan = self.plan
        def fake(prompt, schema, workspace, **kwargs):
            prompts.append(prompt)
            if 'outline' in schema['properties']:
                return {'structured_output': copy.deepcopy(plan)}
            if stop_after is not None and len(prompts) > stop_after:
                raise Blocked('TEST_STOP')
            match = re.search(r'Write scenes (SC\d+)–(SC\d+) only', prompt)
            self.assertIsNotNone(match)
            ids = [s['id'] for s in content['scenes'] if match.group(1) <= s['id'] <= match.group(2)]
            chunk = {'scenes': [copy.deepcopy(s) for s in content['scenes'] if s['id'] in ids],
                     'coverage': [copy.deepcopy(c) for c in content['coverage'] if c['scene_id'] in ids],
                     'claims': [], 'revision_response': [], 'open_questions': [],
                     'story_so_far': 'Summary for ' + ', '.join(ids)}
            if rewrite and 'FIRST CHUNK REVISION' in prompt:
                chunk['story_so_far'] += ' revised'
                chunk['scenes'][0]['narration'] += ' Một điều bất thường vẫn chưa có lời giải.'
            return {'structured_output': chunk}
        return fake

    def test_failed_opening_rewrites_only_first_chunk_before_next_call(self):
        prompts = []
        records = [{'pass': False, 'revision_requests': [{
                       'criterion': 'opening_without_spoiler', 'scene_ids': ['SC01'],
                       'instruction': 'Remove the source of the knocks from the hook.'}]},
                   {'pass': True, 'revision_requests': []}]
        out = self.out('rewrite')
        with self.assertRaisesRegex(Blocked, 'TEST_STOP'):
            self.generate(out, self.writer(prompts, rewrite=True, stop_after=3), records)
        self.assertEqual(len(prompts), 4)  # plan, bad opening, revised opening, SC03
        self.assertIn('FIRST CHUNK REVISION', prompts[-2])
        self.assertIn('Remove the source of the knocks', prompts[-2])
        state = read(out / 'long-script.json')
        self.assertIn('SC01-SC02', state['chunks'])
        self.assertNotIn('SC03-SC04', state['chunks'])

    def test_exhausted_rewrites_block_without_caching_opening(self):
        prompts = []
        failed = {'pass': False, 'revision_requests': [{'criterion': 'beat_image_alignment',
                   'scene_ids': ['SC01'], 'instruction': 'Show the cited object in the beat image.'}]}
        out = self.out('exhausted')
        with self.assertRaisesRegex(Blocked, 'OPENING_CHUNK_DIRECTOR_NEEDS_ATTENTION'):
            self.generate(out, self.writer(prompts, rewrite=True), [failed] * 3)
        self.assertEqual(len(prompts), 4)  # plan plus three writer candidates
        self.assertEqual(read(out / 'long-script.json')['chunks'], {})

    def test_later_chunks_get_no_additional_semantic_critique(self):
        prompts = []
        out = self.out('complete')
        result = self.generate(out, self.writer(prompts),
                               [{'pass': True, 'revision_requests': []}])
        self.assertEqual(result['chunks'], 3)
        self.assertEqual(len(prompts), 4)  # one plan and three two-scene writer calls
        self.assertEqual(list(out.glob('opening-chunk-critique-*.json')), [])

    def prior(self, name, opening_pass=None, suffix=False):
        folder = self.out(name)
        key = long_script.key_of(self.brief, 'test-hash', [], None, 'Write story.', 'Style.', 2)
        chunks = {'SC01-SC02': copy.deepcopy(self.chunk)}
        if suffix:
            content = read(ROOT / 'examples/story-v3/content.json')
            chunks['SC03-SC04'] = {
                'scenes': content['scenes'][2:4],
                'coverage': [c for c in content['coverage'] if c['scene_id'] in ('SC03', 'SC04')],
                'claims': [], 'revision_response': [], 'open_questions': [],
                'story_so_far': 'Old summary for scenes three and four.'}
        write(folder / 'attempt.json', {'state': 'blocked'})
        write(folder / 'long-script.json', {
            'key': key, 'plan': self.plan,
            'outline_director_pass': {'pass': True, 'outline_sha256': outline_director.hash_plan(self.plan)},
            'opening_chunk_pass': opening_pass, 'chunks': chunks})

    def test_resume_rechecks_unverified_opening_and_invalidates_dependent_suffix(self):
        self.prior('old-unverified', suffix=True)
        out = self.out('new-unverified')
        prompts = []
        failed = {'pass': False, 'revision_requests': [{'criterion': 'opening_without_spoiler',
                   'scene_ids': ['SC01'], 'instruction': 'Keep the location of the knocking secret.'}]}
        with self.assertRaisesRegex(Blocked, 'TEST_STOP'):
            self.generate(out, self.writer(prompts, rewrite=True, stop_after=1),
                          [failed, {'pass': True, 'revision_requests': []}])
        self.assertEqual(len(prompts), 2)  # revised first chunk, then freshly requested SC03
        self.assertIn('FIRST CHUNK REVISION', prompts[0])
        self.assertIn('Write scenes SC03–SC04', prompts[1])
        self.assertEqual(read(out / 'long-script.json')['chunks'].keys(), {'SC01-SC02'})

    def test_resume_reuses_only_matching_saved_pass(self):
        passed = {'pass': True,
                  'input_sha256': opening_chunk_director.hash_input(self.brief, self.plan, self.chunk)}
        self.prior('old-passed', opening_pass=passed)
        out = self.out('new-passed')
        prompts = []
        with self.assertRaisesRegex(Blocked, 'TEST_STOP'):
            self.generate(out, self.writer(prompts, stop_after=0),
                          [AssertionError('matching pass must avoid another critique')])
        self.assertEqual(len(prompts), 1)
        self.assertIn('Write scenes SC03–SC04', prompts[0])
        self.assertEqual(read(out / 'long-script.json')['opening_chunk_pass'], passed)


if __name__ == '__main__':
    unittest.main()
