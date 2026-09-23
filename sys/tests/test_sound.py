"""CC0 sound library, generated beds/effects, ducking mix and render wiring. No network, no media stage."""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np

import sound
from pilot import ROOT, read
from content_contract import validate_brief, ContractError
from scripts.story_plan import validate_plan
from scripts.agy_pipeline import sfx_note
from horror import bank

SR = 16000


TEMP = tempfile.TemporaryDirectory()


def tearDownModule():
    TEMP.cleanup()


def library_with(item):
    data = read(sound.LIBRARY)
    data['items'].append(item)
    path = Path(TEMP.name) / (item['id'] + '-' + item['license'] + '.json')
    path.write_text(json.dumps(data))
    return path


class LibraryTests(unittest.TestCase):
    def test_every_item_is_cc0_and_renders(self):
        lib = sound.library()
        self.assertEqual(sound.ids('bed'), ['drone', 'wind', 'pulse'])
        for item in lib.values():
            self.assertEqual(item['license'], 'CC0-1.0')
            x = sound.render_item(item, SR)
            self.assertTrue(np.isfinite(x).all() and 0 < np.max(np.abs(x)) <= 1, item['id'])

    def test_generation_is_deterministic(self):
        item = sound.library()['knock']
        self.assertTrue(np.array_equal(sound.render_item(item, SR), sound.render_item(item, SR)))

    def test_non_cc0_or_unsourced_files_are_refused(self):
        with self.assertRaisesRegex(sound.SoundError, 'CC0-1.0'):
            sound.library(library_with({'id': 'x', 'kind': 'bed', 'title': 't', 'author': 'a', 'license': 'CC-BY-4.0', 'source': 'generated',
                                        'generator': {'name': 'drone', 'seed': 1}}))
        with self.assertRaisesRegex(sound.SoundError, 'source_url'):
            sound.library(library_with({'id': 'x', 'kind': 'sfx', 'title': 't', 'author': 'a', 'license': 'CC0-1.0', 'source': 'file',
                                        'file': 'assets/audio/library.json'}))
        with self.assertRaisesRegex(sound.SoundError, 'sha256'):
            sound.library(library_with({'id': 'x', 'kind': 'sfx', 'title': 't', 'author': 'a', 'license': 'CC0-1.0', 'source': 'file',
                                        'file': 'assets/audio/library.json', 'source_url': 'https://example.org/x', 'sha256': '0'}))

    def test_horror_moods_use_library_beds(self):
        for key, mood in bank.channel()['moods'].items():
            self.assertIn(mood['music'], sound.ids('bed'), key)


class MixTests(unittest.TestCase):
    def voice(self, seconds=20, speech=((2, 8), (11, 17))):
        x = np.zeros(SR * seconds)
        for a, z in speech:
            t = np.arange(int((z - a) * SR)) / SR
            x[int(a * SR):int(z * SR)] = .3 * np.sin(2 * np.pi * 220 * t)
        return x, list(speech)

    def test_bed_ducks_under_speech_and_never_clips(self):
        voice, spans = self.voice()
        bed = np.full(SR * 30, .2)  # constant level, so the measured gain is the ducking alone
        under = sound.mix(voice, SR, spans, bed) - voice
        level = lambda a, z: float(np.mean(under[int(a * SR):int(z * SR)]))
        self.assertAlmostEqual(level(4, 6) / .2, sound.GAIN['bed_speech'], places=3)
        self.assertAlmostEqual(level(9.2, 9.8) / .2, sound.GAIN['bed_gap'], places=3)
        self.assertLess(level(0, .1), level(9.2, 9.8) * .1, 'bed fades in')
        real = sound.mix(voice, SR, spans, sound.render_item(sound.library()['drone'], SR))
        self.assertLessEqual(np.max(np.abs(real)), .97 + 1e-9)
        self.assertEqual(len(real), len(voice))

    def test_effect_lands_on_its_anchor(self):
        voice, spans = self.voice()
        hit = sound.render_item(sound.library()['knock'], SR)
        out = sound.mix(voice, SR, spans, None, [(9.0, hit, 1.0)])
        extra = np.abs(out - voice)
        self.assertEqual(float(extra[:int(8.99 * SR)].max()), 0.0)
        self.assertGreater(float(extra[int(9 * SR):int(9.2 * SR)].max()), .3)

    def test_anchor_time_uses_the_spoken_chunk(self):
        text = 'Đêm đó yên lặng. Rồi có tiếng gõ cửa ba lần.'
        spans = [{'start': 10, 'end': 12, 'text': 'Đêm đó yên lặng.'}, {'start': 12.5, 'end': 16, 'text': 'Rồi có tiếng gõ cửa ba lần.'}]
        at = sound.anchor_seconds(text, {'quote': 'tiếng gõ', 'occurrence': 1}, spans)
        self.assertTrue(12.5 < at < 14, at)

    def test_build_writes_mix_and_cc0_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            voice, _ = self.voice(12, ((1, 5), (6, 11)))
            sound.write_wav(Path(tmp) / 'narration.wav', voice, SR)
            content = {'scenes': [{'id': 'SC01', 'narration': 'Một. Hai có tiếng gõ.',
                                   'sfx': [{'id': 'knock', 'anchor': {'vi': {'quote': 'tiếng gõ', 'occurrence': 1}}}]}]}
            audio = {'segments': [{'scene_id': 'SC01', 'start': 1, 'end': 5, 'text': 'Một.'},
                                  {'scene_id': 'SC01', 'start': 6, 'end': 11, 'text': 'Hai có tiếng gõ.'}]}
            used = sound.build(content, {'sound': {'bed': 'wind', 'sfx': True}}, audio, 'vi',
                               Path(tmp) / 'narration.wav', Path(tmp) / 'mix.wav')
            mixed, rate = sound.read_wav(Path(tmp) / 'mix.wav')
        self.assertEqual((rate, len(mixed)), (SR, len(voice)))
        self.assertEqual([x['id'] for x in used], ['wind', 'knock'])
        self.assertTrue(all(x['license'] == 'CC0-1.0' and x['author'] for x in used))


class ContractTests(unittest.TestCase):
    def fixture(self):
        b = read(ROOT / 'examples/story-v3/brief.json')
        c = read(ROOT / 'examples/story-v3/content.json')
        return b, c

    def test_brief_bed_must_be_in_the_library(self):
        b, _ = self.fixture()
        validate_brief(ROOT, dict(b, sound={'bed': 'drone', 'sfx': False}))
        validate_brief(ROOT, dict(b, sound={'bed': None, 'sfx': True}))
        with self.assertRaisesRegex(ContractError, 'SOUND'):
            validate_brief(ROOT, dict(b, sound={'bed': 'orchestra', 'sfx': False}))

    def test_scene_effects_need_the_brief_library_and_a_real_anchor(self):
        b, c = self.fixture()
        scene = c['scenes'][0]
        quote = scene['narration'].split()[0]
        scene['sfx'] = [{'id': 'knock', 'anchor': {'vi': {'quote': quote, 'occurrence': 1}}}]
        validate_plan(dict(b, sound={'bed': None, 'sfx': True}), c)
        with self.assertRaisesRegex(ContractError, 'SFX'):
            validate_plan(b, c)
        bad = copy.deepcopy(c)
        bad['scenes'][0]['sfx'][0]['id'] = 'thunder'
        with self.assertRaisesRegex(ContractError, 'SFX'):
            validate_plan(dict(b, sound={'bed': None, 'sfx': True}), bad)
        bad['scenes'][0]['sfx'][0] = {'id': 'knock', 'anchor': {'vi': {'quote': 'không có trong lời dẫn', 'occurrence': 1}}}
        with self.assertRaisesRegex(ContractError, 'SFX_ANCHOR'):
            validate_plan(dict(b, sound={'bed': None, 'sfx': True}), bad)

    def test_writer_sees_the_effect_menu_only_when_enabled(self):
        self.assertIn('knock:', sfx_note({'sound': {'bed': 'drone', 'sfx': True}}))
        self.assertIn('Không thêm trường sfx', sfx_note({}))

    def test_render_timeout_grows_with_video_length(self):
        import adapters
        self.assertEqual(adapters.render_timeout({}, {'duration': 60, 'aspect_ratio': '9:16'}), 3600)
        self.assertEqual(adapters.render_timeout({}, {'duration': 1200, 'aspect_ratio': '16:9'}), 6600)
        self.assertEqual(adapters.render_timeout({'render_timeout_factor': 4}, {'duration': 1200, 'en_duration': 1300, 'aspect_ratio': 'dual'}), 10600)

    def test_renderer_plays_the_mixed_tracks(self):
        code = """import {outputPlans} from './renderer/outputs.mjs';
        const p={aspect_ratio:'16:9',audio_language:'vi',duration:900,scenes:[],audio_files:{vi:'mix.wav'}};
        const d={aspect_ratio:'dual',duration:60,en_duration:70,scenes:[],en_scenes:[],audio_files:{vi:'mix.wav',en:'mix_en.wav'}};
        console.log(JSON.stringify([outputPlans(p,false)[0].props.audioSrc, outputPlans(d,true).map(x=>x.props.audioSrc),
                                    outputPlans({aspect_ratio:'9:16',scenes:[]},false)[0].props.audioSrc]));"""
        result = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', code], cwd=ROOT, text=True))
        self.assertEqual(result, ['mix.wav', ['mix.wav', 'mix_en.wav'], 'narration.wav'])


if __name__ == '__main__':
    unittest.main()
