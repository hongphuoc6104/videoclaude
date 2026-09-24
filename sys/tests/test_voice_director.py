"""Voice director validation and cache; agy is always faked."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pilot import ROOT
from scripts.voice_director import direct_voice


BASE = [{'scene_id': 'SC01', 'style': 'rising', 'texts': ['Tôi đứng chờ.', 'Nó đang mở.'],
         'speeds': [0.9, 0.9], 'gains': [0.0, 0.0], 'cues': [[], ['reveal']],
         'gaps': [0.7], 'tail': 1.3}]
CFG = {'enabled': True, 'speed_min': 0.8, 'speed_max': 1.1,
       'max_shift': 0.15, 'pause_max': 2.0, 'scenes_per_call': 6}


def answer(speed=0.86):
    return {'scenes': [{'scene_id': 'SC01', 'style': 'rising', 'line_directions': [
        {'text': 'Tôi đứng chờ.', 'speed_multiplier': speed, 'pause_after_s': 0.8,
         'gain_db': 0, 'delivery_tag': 'neutral', 'reason': 'Hold before reveal'},
        {'text': 'Nó đang mở.', 'speed_multiplier': 0.85, 'pause_after_s': 1.5,
         'gain_db': 0, 'delivery_tag': 'reveal_slow', 'reason': 'Leave silence after reveal'}]}]}


class VoiceDirectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.cache = self.path / 'cache'
        self.audit = self.path / 'voice-direction.json'

    def tearDown(self):
        self.tmp.cleanup()

    def direct(self, retake=0):
        return direct_voice(BASE, 'tense', {'SC01': retake}, CFG, self.cache, self.audit, ROOT)

    def test_valid_direction_merges_and_keeps_words(self):
        with patch('scripts.agy_pipeline.invoke', return_value={'structured_output': answer()}) as invoke:
            final = self.direct()
        self.assertEqual(invoke.call_count, 1)
        self.assertEqual(final[0]['texts'], BASE[0]['texts'])
        self.assertEqual(final[0]['speeds'], [0.86, 0.85])
        self.assertEqual(final[0]['gaps'], [0.8])
        self.assertEqual(final[0]['tail'], 1.5)
        self.assertEqual(final[0]['gains'], [0.0, 0.0])
        report = json.loads(self.audit.read_text())
        self.assertEqual(report['batches'][0]['source'], 'agy')
        self.assertEqual(report['batches'][0]['reasons'][0]['line_directions'][1]['delivery_tag'], 'reveal_slow')

    def test_changed_text_retries_once_then_uses_baseline(self):
        bad = answer()
        bad['scenes'][0]['line_directions'][1]['text'] = 'Nó đang mở!'
        with patch('scripts.agy_pipeline.invoke', return_value={'structured_output': bad}) as invoke:
            final = self.direct()
        self.assertEqual(invoke.call_count, 2)
        self.assertEqual(final, BASE)
        self.assertEqual(json.loads(self.audit.read_text())['batches'][0]['source'], 'baseline_fallback')
        self.assertEqual(list(self.cache.glob('*.json')), [])

    def test_speed_and_nonfinite_rejected(self):
        for speed in (1.11, 1.05, float('nan')):
            with self.subTest(speed=speed):
                with patch('scripts.agy_pipeline.invoke', return_value={'structured_output': answer(speed)}):
                    self.assertEqual(self.direct(), BASE)

    def test_cache_hit_and_retake_invalidation(self):
        with patch('scripts.agy_pipeline.invoke', return_value={'structured_output': answer()}) as invoke:
            self.direct()
            self.direct()
            self.assertEqual(invoke.call_count, 1)
            cached = json.loads(self.audit.read_text())['batches'][0]
            self.assertEqual(cached['source'], 'agy')
            self.assertTrue(cached['cache_hit'])
            self.direct(retake=1)
            self.assertEqual(invoke.call_count, 2)

    def test_preserves_important_baseline_pause(self):
        bad = answer()
        bad['scenes'][0]['line_directions'][1]['pause_after_s'] = 0.5
        with patch('scripts.agy_pipeline.invoke', return_value={'structured_output': bad}):
            self.assertEqual(self.direct(), BASE)

    def test_long_scene_is_split_and_reassembled_at_line_boundaries(self):
        long = copy.deepcopy(BASE)
        long[0].update(texts=[f'Câu {i}.' for i in range(12)], speeds=[0.9] * 12,
                       gains=[0.0] * 12, cues=[[] for _ in range(12)],
                       gaps=[0.7] * 11, tail=1.3)

        def fake(prompt, schema, workspace, timeout):
            data = json.loads(prompt.split('Immutable input data:\n', 1)[1])
            scenes = []
            for scene in data['scenes']:
                lines = [{'text': text, 'speed_multiplier': speed,
                          'pause_after_s': scene['gaps'][i] if i < len(scene['gaps']) else scene['tail'],
                          'gain_db': 0, 'delivery_tag': 'neutral', 'reason': 'Keep measured pace'}
                         for i, (text, speed) in enumerate(zip(scene['texts'], scene['speeds']))]
                scenes.append({'scene_id': scene['scene_id'], 'style': scene['style'], 'line_directions': lines})
            return {'structured_output': {'scenes': scenes}}

        with patch('scripts.agy_pipeline.invoke', side_effect=fake) as invoke:
            final = direct_voice(long, 'tense', {}, CFG, self.cache, self.audit, ROOT)
        self.assertEqual(invoke.call_count, 2)
        self.assertEqual(final, long)
        report = json.loads(self.audit.read_text())
        self.assertEqual([b['line_ranges'][0]['start'] for b in report['batches']], [0, 10])


if __name__ == '__main__':
    unittest.main()
