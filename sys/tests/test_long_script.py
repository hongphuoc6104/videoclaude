"""Chunked long-form script generation; agy is faked, nothing leaves the machine."""
import copy
import unittest
from unittest.mock import patch

from pilot import ROOT, Blocked, read
import test_workflow as workflow_tests
import workflow as wf
from scripts import long_script


def story():
    return read(ROOT / 'examples/story-v3/brief.json'), read(ROOT / 'examples/story-v3/content.json')


class FakeAgy:
    """Plan first, then one chunk per call built from the example script; records prompts."""

    def __init__(self, content, break_at=None, edit=None):
        self.content, self.break_at, self.edit, self.prompts = content, break_at, edit, []

    def __call__(self, prompt, schema, out, **kwargs):
        self.prompts.append(prompt)
        if len(self.prompts) == self.break_at:
            raise Blocked('AGY_TIMEOUT: no automatic retry; inspect the saved attempt')
        if 'outline' in schema['properties']:
            return {'structured_output': {'outline': self.content['outline'], 'characters': self.content['characters']}}
        ids = [s['id'] for s in self.content['scenes'] if self.within(prompt, s['id'])]
        chunk = {'scenes': [s for s in self.content['scenes'] if s['id'] in ids],
                 'coverage': [c for c in self.content['coverage'] if c['scene_id'] in ids],
                 'claims': [], 'revision_response': [], 'open_questions': [],
                 'story_so_far': 'Events of ' + ', '.join(ids) + '.'}
        if self.edit:
            self.edit(chunk)
        return {'structured_output': copy.deepcopy(chunk)}

    @staticmethod
    def within(prompt, scene):
        head = prompt[prompt.index('\nWrite scenes ') + len('\nWrite scenes '):].split(' ', 1)[0]
        first, last = head.split('–')
        return first <= scene <= last


class LongScriptTests(unittest.TestCase):
    setUp = workflow_tests.WorkflowTests.setUp
    approve = workflow_tests.WorkflowTests.approve

    def start(self):
        wf.new(self.p, self.job, read(ROOT / 'examples/story-v3/brief.json'))
        _, self.revision, self.hash = self.p.brief(self.job)
        self.content = dict(story()[1], brief_revision=self.revision, brief_hash=self.hash)

    def run_content(self, agy):
        with patch.object(long_script, 'chunk_size', return_value=2), patch('scripts.agy_pipeline.invoke', side_effect=agy):
            return wf.advance(self.p, self.job, 'content')

    def test_short_briefs_keep_the_single_call_path(self):
        b, _ = story()
        self.assertEqual(read(ROOT / 'config.json')['content_chunk_scenes'], 6)
        self.assertFalse(long_script.enabled(ROOT, b))  # 6 scenes
        self.assertTrue(long_script.enabled(ROOT, dict(b, scene_count=28)))
        self.assertEqual([len(x) for x in long_script.split(dict(b, scene_count=28), 6)], [6, 6, 6, 6, 4])

    def test_plan_then_chunks_merge_into_the_same_script(self):
        self.start()
        agy = FakeAgy(self.content)
        self.run_content(agy)
        self.assertEqual(len(agy.prompts), 4)  # plan + three chunks of two scenes
        self.assertEqual(read(self.p.job(self.job) / 'draft/content.json'), self.content)
        style = (self.p.root / '.agents/skills/vp-content/references/narration-style.md').read_text()
        self.assertNotIn(style, agy.prompts[0])
        self.assertTrue(all(x.count(style) == 1 for x in agy.prompts[1:]))
        self.assertIn('Write scenes SC03–SC04 only (2 of 6)', agy.prompts[2])
        self.assertIn('Events of SC01, SC02.', agy.prompts[2])  # running summary reaches later chunks
        self.assertIn(self.content['scenes'][1]['narration'], agy.prompts[2])  # last scenes for continuity
        self.assertEqual(wf.current(self.p, self.job, 'content')['stage'], 'content')

    def test_blocked_attempt_reuses_finished_calls(self):
        self.start()
        first = FakeAgy(self.content, break_at=3)
        with self.assertRaisesRegex(Blocked, 'AGY_TIMEOUT'):
            self.run_content(first)
        second = FakeAgy(self.content)
        self.run_content(second)
        self.assertEqual(len(second.prompts), 2)  # only the chunk that timed out and the last one
        self.assertIn('Write scenes SC03–SC04', second.prompts[0])
        self.assertEqual(read(self.p.job(self.job) / 'draft/content.json'), self.content)

    def test_short_or_wrong_chunks_stop_early(self):
        self.start()
        agy = FakeAgy(self.content)
        with patch.object(long_script, 'word_targets', return_value={'vi': (100, 150)}):
            with self.assertRaisesRegex(Blocked, 'CHUNK_LENGTH SC01–SC02: vi narration averages 25 words'):
                self.run_content(agy)
        self.assertEqual(len(agy.prompts), 2, 'no further calls after a bad chunk')
        def break_anchor(chunk):
            chunk['scenes'][1]['beats'][0]['anchor']['vi']['quote'] = 'not in the narration'
        agy = FakeAgy(self.content, edit=break_anchor)
        with self.assertRaisesRegex(Exception, 'ANCHOR'):
            self.run_content(agy)
        self.assertEqual(len(agy.prompts), 1, 'the plan of the blocked attempt is reused')
        agy = FakeAgy(self.content, edit=lambda chunk: chunk['scenes'].pop())
        with self.assertRaisesRegex(Blocked, 'CHUNK_SCENES SC01–SC02'):
            self.run_content(agy)

    def test_chunks_cannot_invent_characters(self):
        self.start()
        def stranger(chunk):
            chunk['scenes'][0]['character_ids'].append('STRANGER')
        with self.assertRaisesRegex(Blocked, 'CHUNK_CHARACTERS SC01'):
            self.run_content(FakeAgy(self.content, edit=stranger))

    def test_revision_responses_merge_per_request(self):
        requests = [{'request_id': '7', 'note': 'x'}, {'request_id': '8', 'note': 'y'}]
        parts = [{'revision_response': [{'request_id': '7', 'status': 'addressed', 'explanation': 'A.', 'scene_ids': ['SC01']}]},
                 {'revision_response': [{'request_id': '7', 'status': 'unresolved', 'explanation': 'B.', 'scene_ids': ['SC03']}]}]
        merged = long_script.merge_responses(requests, parts)
        self.assertEqual(merged[0], {'request_id': '7', 'status': 'addressed', 'explanation': 'A. B.', 'scene_ids': ['SC01', 'SC03']})
        self.assertEqual((merged[1]['status'], merged[1]['scene_ids']), ('unresolved', []))

    def test_word_targets_follow_brief_duration(self):
        b, _ = story()
        b = dict(b, scene_count=40, duration={'min_seconds': 1200, 'max_seconds': 1800})
        self.assertEqual(long_script.word_targets(b), {'vi': (108, 162)})
        self.assertEqual(set(long_script.word_targets(dict(b, aspect_ratio='dual'))), {'vi', 'en'})


if __name__ == '__main__':
    unittest.main()
