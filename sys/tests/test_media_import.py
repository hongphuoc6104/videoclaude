"""Real Pilot gates with fake local audio/Flow outputs; no production service."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from pilot import ROOT, Blocked, Pilot, digest, hashobj, read, write
import adapters
import media_import
import machine_review
import workflow


class MediaImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ['schemas', '.agents', 'renderer', 'examples', 'scripts']:
            shutil.copytree(ROOT / name, self.root / name)
        shutil.copytree(ROOT / 'horror', self.root / 'horror',
                        ignore=shutil.ignore_patterns('ledger.json', 'briefs', '.ledger.lock'))
        for name in ['pilot.py', 'workflow.py', 'machine_review.py', 'image_pipeline.py',
                     'media_import.py', 'content_contract.py', 'prompt_templates.py',
                     'adapters.py', 'config.json', 'AGENTS.md', 'GEMINI.md']:
            shutil.copy(ROOT / name, self.root / name)
        self.p = Pilot(self.root)
        self.addCleanup(self.p.db.close)
        self.addCleanup(self.temp.cleanup)
        self._counter = 0
        self.new_job('source')
        self.make_source_media()

    def fake_review(self, p, job, stage, assets, snapshot):
        self._counter += 1
        path = p.job(job) / 'machine-reviews' / f'test-{self._counter}.json'
        write(path, {'test_only': True, 'stage': stage, 'files': assets})
        return str(path.relative_to(p.job(job)))

    def new_job(self, job, mutate=None):
        workflow.new(self.p, job, read(ROOT / 'examples/m1/brief.json'), 'auto')
        content = read(ROOT / 'examples/story-v3/content.json')
        if mutate:
            mutate(content)
        _, rev, stamp = self.p.brief(job)
        content.update(brief_revision=rev, brief_hash=stamp)
        write(self.p.job(job) / 'draft/content.json', content)
        self.p.run(job, 'content')
        workflow.prepare(self.p, job, 'content')
        with patch('machine_review.review', side_effect=self.fake_review):
            workflow.approve(self.p, job, 'content', 1, 'Test machine review', machine=True)

    def fake_audio(self, p, job, out):
        segments = []
        combined = b''
        seconds = 8
        for i, scene in enumerate(p.payload(job, 'content')['scenes']):
            raw = b'\x00\x20' * (48000 * seconds)
            name = out / f'{scene["id"]}.wav'
            with wave.open(str(name), 'wb') as f:
                f.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
                f.writeframes(raw)
            combined += raw
            segments.append({'scene_id': scene['id'], 'text': scene['narration'],
                'path': str(name.relative_to(p.job(job))), 'start': i * seconds,
                'end': (i + 1) * seconds})
        wav = out / 'narration.wav'
        with wave.open(str(wav), 'wb') as f:
            f.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
            f.writeframes(combined)
        srt = out / 'subtitles.srt'
        srt.write_text(adapters.make_srt(segments))
        return {'voice': 'TEST', 'backend': 'onnx', 'wav': str(wav.relative_to(p.job(job))),
                'srt': str(srt.relative_to(p.job(job))), 'duration': len(segments) * seconds,
                'segments': segments}

    def fake_flow(self, p, *args, **kwargs):
        folder = Path(args[args.index('--out') + 1])
        if args[0] == 'batch':
            # The batch adapter sees no completion journal and safely falls
            # back to the single-image fake provider below.
            return SimpleNamespace(returncode=0, stdout='TEST batch only', stderr='')
        chars = list(args[args.index('--character') + 1:]) if '--character' in args else []
        Image.new('RGB', (720, 1280), 'blue').save(folder / 'result.png')
        registration = args[0] == 'character'
        if not registration:
            write(folder / 'result.json', {'jobId': args[args.index('--id') + 1],
                'type': 'image', 'prompt': args[args.index('--prompt') + 1],
                'ratio': args[args.index('--ratio') + 1], 'characters': chars,
                'source': 'google-flow-browser', 'status': 'downloaded',
                'forgeId': 'TEST-MEDIA-' + args[args.index('--id') + 1]})
        write(folder.parent / 'ui-proof.json', {'passed': True,
            'mode': 'character-register' if registration else 'image', 'characters': chars,
            **({'base_image': args[args.index('--base-image') + 1]}
               if '--base-image' in args else {})})
        Image.new('RGB', (40, 40), 'blue').save(folder.parent / 'before-submit.png')
        return SimpleNamespace(returncode=0, stdout='TEST ONLY', stderr='')

    def make_source_media(self):
        with patch('adapters.audio', side_effect=self.fake_audio), \
             patch('adapters.gflow', side_effect=self.fake_flow), \
             patch('machine_review.review', side_effect=self.fake_review):
            workflow.prepare(self.p, 'source', 'media')

    def test_full_import_creates_new_revisions_and_fresh_media_review(self):
        self.new_job('target')
        with patch('adapters.audio', side_effect=AssertionError('TTS must not run')), \
             patch('adapters.gflow', side_effect=AssertionError('Flow must not run')):
            result = media_import.import_media(self.p, 'target', 'source')
        self.assertEqual(result['stages'][1]['state'], 'awaiting_review')
        self.assertEqual(result['stages'][1]['revision'], 1)
        self.assertFalse((self.p.job('target') / 'reviews/media/1/decision.json').exists())
        self.assertEqual(self.p.rows('target')['audio']['revision'], 1)
        self.assertEqual(self.p.rows('target')['images']['revision'], 2)
        self.assertEqual(self.p.payload('target', 'images')['checkpoint'], 'final')
        self.assertEqual(self.p.payload('target', 'audio')['duration'], self.p.payload('source', 'audio')['duration'])
        self.assertEqual(len(self.p.payload('target', 'images')['items']),
                         len(self.p.payload('source', 'images')['items']))
        self.assertIn(self.p.payload('target', 'audio')['import_receipt'],
                      workflow.current(self.p, 'target', 'media')['assets'])
        self.p.validate('target', 'audio')
        self.p.validate('target', 'images')

    def test_imported_media_passes_real_deterministic_review_plan(self):
        """Cross the real importer/reviewer boundary without calling AGY."""
        self.new_job('target')
        media_import.import_media(self.p, 'target', 'source')
        manifest = workflow.current(self.p, 'target', 'media')
        self.assertIsNotNone(manifest)
        plan, _content, _audio, _images, tracks, verified = machine_review._media_plan(
            self.p, 'target', manifest['assets'], manifest['snapshot'])
        self.assertEqual(len(plan['files']), len(manifest['assets']))
        self.assertEqual(len(plan['batches']), 1 + (len(self.p.payload('target', 'content')['scenes']) + 1) // 2)
        self.assertEqual(len(tracks), 1)
        receipt = self.p.payload('target', 'images')['import_receipt']
        self.assertIn(str(self.p.path('target', receipt)), verified['deterministically_verified_files'])
        self.assertTrue(verified['import_provenance_files'])
        reference = next(ref for item in self.p.payload('target', 'images')['items']
                         for ref in item['references'])
        journal = read(self.p.path('target', reference['registration_journal']))
        self.assertNotEqual(journal['path'], reference['registration_image'])
        self.assertIn(str(self.p.path('target', reference['registration_image'])), plan['files'])
        self.assertFalse(self.p.path('target', manifest['decision']).exists())

    def test_public_cli_import_audio_only(self):
        self.new_job('target')
        result = subprocess.run([sys.executable, str(self.root / 'pilot.py'),
            'import-media', 'target', '--from', 'source', '--part', 'audio'],
            cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output['stages'][1]['state'], 'pending')
        self.assertEqual(self.p.rows('target')['audio']['state'], 'approved')

    def test_public_cli_import_selective_image_cache(self):
        self.new_job('target', lambda c: c['scenes'][1]['images'][0].update(
            description=c['scenes'][1]['images'][0]['description'] + ' Wider desk view.'))
        result = subprocess.run([sys.executable, str(self.root / 'pilot.py'),
            'import-media', 'target', '--from', 'source', '--part', 'image-cache'],
            cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual((output['reused_images'], output['generated_images']), (5, 1))
        self.assertEqual(self.p.payload('target', 'images')['checkpoint'], 'references')

    def test_audio_only_allows_changed_image_plan_but_not_changed_narration(self):
        self.new_job('target', lambda c: c['scenes'][0]['images'][0].update(
            description=c['scenes'][0]['images'][0]['description'] + ' Wider desk view.'))
        result = media_import.import_media(self.p, 'target', 'source', 'audio')
        self.assertEqual(result['stages'][1]['state'], 'pending')
        self.assertEqual(self.p.rows('target')['audio']['state'], 'approved')
        self.assertEqual(self.p.rows('target')['images']['state'], 'pending')
        with self.assertRaisesRegex(Blocked, 'image plans differ'):
            media_import.import_media(self.p, 'target', 'source', 'images')
        self.new_job('other', lambda c: c['scenes'][0].update(narration=c['scenes'][0]['narration'] + ' Khác.'))
        with self.assertRaisesRegex(Blocked, 'narration differs'):
            media_import.import_media(self.p, 'other', 'source', 'audio')

    def test_selective_image_cache_reuses_unchanged_scenes_without_new_requests(self):
        self.new_job('target', lambda c: c['scenes'][1]['images'][0].update(
            description=c['scenes'][1]['images'][0]['description'] + ' Wider desk view.'))
        media_import.import_media(self.p, 'target', 'source', 'audio')
        result = media_import.import_media(self.p, 'target', 'source', 'image-cache')
        self.assertEqual((result['reused_images'], result['generated_images']), (5, 1))
        self.assertEqual(self.p.rows('target')['images']['state'], 'pending')
        self.assertEqual(self.p.payload('target', 'images')['checkpoint'], 'references')
        image_calls = []
        def record_flow(p, *args, **kwargs):
            if args[0] == 'image':
                image_calls.append(args)
            return self.fake_flow(p, *args, **kwargs)
        with patch('adapters.gflow', side_effect=record_flow), \
             patch('machine_review.review', side_effect=self.fake_review):
            review = workflow.prepare(self.p, 'target', 'media')
        self.assertEqual(len(image_calls), 1)
        self.assertEqual(len(self.p.payload('target', 'images')['items']), 6)
        self.assertEqual(review['stage'], 'media')
        self.p.validate('target', 'images')
        plan, _, _, _, _, verified = machine_review._media_plan(
            self.p, 'target', review['assets'], review['snapshot'])
        self.assertEqual(len(plan['batches']), 4)
        self.assertTrue(verified['import_provenance_files'])
        self.assertFalse(self.p.path('target', review['decision']).exists())
        workflow.reject(self.p, 'target', 'media', review['revision'],
                        'Redraw the imported opening scene', scene='SC01')
        image_calls.clear()
        with patch('adapters.gflow', side_effect=record_flow), \
             patch('machine_review.review', side_effect=self.fake_review):
            repaired = workflow.prepare(self.p, 'target', 'media')
        self.assertEqual(repaired['revision'], 2)
        self.assertEqual(len(image_calls), 1)
        self.p.validate('target', 'images')

    def test_selective_reuse_preserves_a_based_on_chain_and_fails_on_tamper(self):
        def add_chain(content):
            scene = content['scenes'][0]
            image = copy.deepcopy(scene['images'][0])
            image.update(id='SC01_I2', based_on='SC01_I1',
                         description='Góc gần hơn trong cùng văn phòng.',
                         preserve='Giữ cùng hai nhân vật và bàn báo cáo.',
                         change='Máy quay tiến gần hơn.')
            scene['images'].append(image)
            beat = copy.deepcopy(scene['beats'][0])
            beat.update(id='SC01_B2', image_id='SC01_I2',
                        anchor={'vi': {'quote': 'Hãy thử cách nói rõ việc', 'occurrence': 1}})
            scene['beats'].append(beat)
        self.new_job('chain-source', add_chain)
        with patch('adapters.audio', side_effect=self.fake_audio), \
             patch('adapters.gflow', side_effect=self.fake_flow), \
             patch('machine_review.review', side_effect=self.fake_review):
            workflow.prepare(self.p, 'chain-source', 'media')
        def destination(content):
            add_chain(content)
            content['scenes'][1]['images'][0]['description'] += ' Wider desk view.'
        self.new_job('chain-target', destination)
        media_import.import_media(self.p, 'chain-target', 'chain-source', 'audio')
        result = media_import.import_media(self.p, 'chain-target', 'chain-source', 'image-cache')
        self.assertEqual((result['reused_images'], result['generated_images']), (6, 1))
        calls = []
        def record_flow(p, *args, **kwargs):
            if args[0] == 'image':
                calls.append(args)
            return self.fake_flow(p, *args, **kwargs)
        with patch('adapters.gflow', side_effect=record_flow), \
             patch('machine_review.review', side_effect=self.fake_review):
            workflow.prepare(self.p, 'chain-target', 'media')
        self.assertEqual(len(calls), 1)
        payload = self.p.payload('chain-target', 'images')
        first, second = payload['items'][:2]
        self.assertEqual(first['image_id'], 'SC01_I1')
        self.assertEqual(second['image_id'], 'SC01_I2')
        journal = read(self.p.path('chain-target', second['request']))
        self.assertEqual(journal['identity']['base_image']['sha256'], first['sha256'])
        self.p.validate('chain-target', 'images')
        def break_chain(content):
            destination(content)
            content['scenes'][0]['images'][1]['based_on'] = None
        self.new_job('chain-change', break_chain)
        changed = media_import.import_media(self.p, 'chain-change', 'chain-source', 'image-cache')
        self.assertEqual((changed['reused_images'], changed['generated_images']), (4, 3))
        self.p.path('chain-target', second['request']).write_text('{}')
        with self.assertRaises(Blocked):
            self.p.validate('chain-target', 'images')

    def test_selective_cache_rejects_non_image_content_change(self):
        self.new_job('target', lambda c: c['scenes'][1].update(
            action=c['scenes'][1]['action'] + ' rồi dừng lại.'))
        with self.assertRaisesRegex(Blocked, 'only scene image plans may differ'):
            media_import.import_media(self.p, 'target', 'source', 'image-cache')
        self.assertEqual(self.p.rows('target')['images']['revision'], 0)

    def test_source_tampering_or_missing_asset_blocks_before_import(self):
        self.new_job('target')
        item = self.p.payload('source', 'images')['items'][0]
        path = self.p.path('source', item['path'])
        path.write_bytes(path.read_bytes() + b'tamper')
        with self.assertRaises(Blocked):
            media_import.import_media(self.p, 'target', 'source')
        self.assertEqual(self.p.rows('target')['images']['revision'], 0)
        self.assertEqual(self.p.rows('target')['audio']['revision'], 0)

    def test_missing_source_audio_blocks_before_import(self):
        self.new_job('target')
        source_audio = self.p.payload('source', 'audio')
        self.p.path('source', source_audio['segments'][0]['path']).unlink()
        with self.assertRaises(Blocked):
            media_import.import_media(self.p, 'target', 'source', 'audio')
        self.assertEqual(self.p.rows('target')['audio']['revision'], 0)

    def test_ambiguous_same_target_blocks_import(self):
        self.new_job('target')
        item = self.p.payload('source', 'images')['items'][0]
        original = read(self.p.path('source', item['request']))
        ambiguous = copy.deepcopy(original)
        ambiguous['state'] = 'ambiguous'
        folder = self.p.job('source') / 'flow/attempts' / ('f' * 64)
        write(folder / 'request.json', ambiguous)
        with self.assertRaisesRegex(Blocked, 'unresolved Flow request'):
            media_import.import_media(self.p, 'target', 'source', 'images')

    def test_imported_copy_tampering_is_detected(self):
        self.new_job('target')
        media_import.import_media(self.p, 'target', 'source', 'audio')
        payload = self.p.payload('target', 'audio')
        self.p.path('target', payload['segments'][0]['path']).write_bytes(b'tamper')
        with self.assertRaises(Blocked):
            media_import.check_imported_audio(self.p, 'target', payload)

    def test_old_integrity_source_imports_without_rewriting_baseline(self):
        old = read(self.p.job('source') / 'integrity.json')
        path = self.root / 'pilot.py'
        path.write_text(path.read_text() + '\n# changed protected code for successor job\n')
        with self.assertRaisesRegex(Blocked, 'Protected implementation changed'):
            self.p.integrity('source')
        self.new_job('target')
        result = media_import.import_media(self.p, 'target', 'source')
        self.assertEqual(result['stages'][1]['state'], 'awaiting_review')
        self.assertEqual(read(self.p.job('source') / 'integrity.json'), old)

    def test_forged_content_decision_without_event_cannot_be_source(self):
        workflow.new(self.p, 'forged', read(ROOT / 'examples/m1/brief.json'), 'auto')
        content = read(ROOT / 'examples/story-v3/content.json')
        _, revision, stamp = self.p.brief('forged')
        content.update(brief_revision=revision, brief_hash=stamp)
        write(self.p.job('forged') / 'draft/content.json', content)
        self.p.run('forged', 'content')
        manifest = workflow.prepare(self.p, 'forged', 'content')
        report = self.p.job('forged') / 'machine-reviews/forged-report.json'
        write(report, {'test_only': True})
        write(self.p.path('forged', manifest['decision']), {'approved': True, 'actor': 'machine',
            'manifest_hash': hashobj(manifest), 'report': str(report.relative_to(self.p.job('forged'))),
            'report_hash': digest(report)})
        self.new_job('target')
        with self.assertRaisesRegex(Blocked, 'genuine auto decision'):
            media_import.import_media(self.p, 'target', 'forged', 'audio')

    def test_missing_copied_flow_evidence_is_detected(self):
        self.new_job('target')
        media_import.import_media(self.p, 'target', 'source')
        payload = self.p.payload('target', 'images')
        self.p.path('target', payload['items'][0]['request']).unlink()
        with self.assertRaises(Blocked):
            media_import.check_imported_images(self.p, 'target', payload)

    def test_normal_flow_branch_still_checks_journal_and_gate(self):
        self.p.validate('source', 'audio')
        self.p.validate('source', 'images')
        bad = copy.deepcopy(self.p.payload('source', 'images'))
        bad['items'][0]['request'] = 'flow/attempts/missing/request.json'
        with self.assertRaises(Exception):
            self.p.checks('source', 'images', bad)
        workflow.new(self.p, 'early', read(ROOT / 'examples/m1/brief.json'), 'auto')
        with self.assertRaisesRegex(Blocked, 'Kịch bản chưa được duyệt'):
            self.p.gate('early', 'images')

    def test_arbitrary_producer_and_reject_part_cannot_bypass_gate(self):
        self.new_job('target')
        with self.assertRaisesRegex(Blocked, 'verified media import producer'):
            self.p.run('target', 'audio', producer=lambda out: self.fake_audio(self.p, 'target', out))
        self.assertEqual(self.p.rows('target')['audio']['revision'], 0)
        review = workflow.current(self.p, 'source', 'media')
        with self.assertRaisesRegex(Blocked, 'chỉ dùng cho import-media'):
            workflow.reject(self.p, 'source', 'media', review['revision'], 'Test', part='images', scene='SC01')
        self.assertEqual(self.p.rows('source')['images']['state'], 'approved')


if __name__ == '__main__':
    unittest.main()
