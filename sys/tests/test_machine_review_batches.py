"""Media review accounting and resumability; fake AGY replies are test data only."""
import json
import tempfile
import unittest
import uuid
import wave
from pathlib import Path
from unittest.mock import patch

import adapters
from pilot import Blocked, digest, hashobj, read, write
from scripts.story_plan import timeline
import machine_review as mr


class FakeJob:
    def __init__(self, root, brief):
        self.root, self._brief = root, brief
        self.payloads = {}

    def job(self, _job):
        return self.root

    def path(self, _job, rel):
        return self.root / rel

    def payload(self, _job, module):
        return self.payloads[module]

    def brief(self, _job):
        return self._brief, 1, 'TEST BRIEF'


class MediaBatchReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.brief = {'topic': 'TEST ONLY fictional story', 'aspect_ratio': '16:9',
                      'audio_language': 'vi'}
        self.p = FakeJob(self.root, self.brief)
        self.snapshot = {'modules': {'content': {'hash': 'content-hash'}}}
        self.calls = []
        self.make_fixture(4, 1)

    def put(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return rel

    def make_fixture(self, count, references):
        scenes = [{'id': f'SC{index:02}', 'title': f'TEST scene {index}',
                   'narration': f'TEST narration for scene {index}.'}
                  for index in range(1, count + 1)]
        content = {'schema_version': '2.0', 'topic': 'TEST ONLY',
                   'characters': [{'id': f'CH{index:02}', 'name': f'Character {index}'}
                                  for index in range(1, references + 1)],
                   'scenes': scenes,
                   'coverage': [{'scene_id': scene['id'], 'quote': scene['narration']}
                                for scene in scenes], 'outline': [], 'claims': []}
        refs = []
        aliases = []
        for index in range(1, references + 1):
            rel = self.put(f'revisions/images/1/REF-CH{index:02}.jpg',
                           f'TEST reference {index}'.encode())
            refs.append({'character_id': f'CH{index:02}', 'name': f'Character {index}',
                         'path': rel, 'sha256': digest(self.root / rel)})
            aliases.append(self.put(f'flow/registered-{index}.jpg', (self.root / rel).read_bytes()))
        items = []
        for index, scene in enumerate(scenes, 1):
            image_count = 4 + (index in (9, 13)) * 2 if count == 20 else 2
            for number in range(1, image_count + 1):
                rel = self.put(f'revisions/images/1/{scene["id"]}_I{number}_16x9.jpg',
                               f'TEST image {scene["id"]} {number}'.encode())
                prompt = f'TEST illustrated scene {scene["id"]} image {number}.'
                items.append({'scene_id': scene['id'], 'image_id': scene['id'],
                              'ratio': '16:9', 'path': rel, 'sha256': digest(self.root / rel),
                              'prompt': prompt, 'actual_prompt': 'Draw: ' + prompt,
                              'source': 'TEST FLOW', 'references': []})
        for index, alias in enumerate(aliases, 1):
            sha = digest(self.root / alias)
            journal = f'flow/registration-{index}/request.json'
            confirmation = f'flow/registration-{index}/confirmation.json'
            write(self.root / journal, {'path': alias, 'sha256': sha})
            write(self.root / confirmation, {'pending_media_review': True})
            items[0]['references'].append({'character_id': f'CH{index:02}',
                                           'registration_journal': journal,
                                           'confirmation': confirmation,
                                           'registration_hash': sha, 'sha256': sha})
        images = {'schema_version': '3.0', 'content_hash': 'content-hash',
                  'items': items, 'references': refs, 'proofs': []}
        wav_rel = 'revisions/audio/1/narration.wav'
        wav = self.root / wav_rel
        wav.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(wav), 'wb') as stream:
            stream.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\x01\x02' * (8000 * count))
        segments = [{'scene_id': scene['id'], 'text': scene['narration'],
                     'start': index, 'end': index + 1}
                    for index, scene in enumerate(scenes)]
        audio = {'voice': 'TEST', 'backend': 'TEST', 'wav': wav_rel,
                 'srt': 'revisions/audio/1/subtitles.srt', 'duration': count,
                 'segments': segments}
        self.p.payloads = {'content': content, 'audio': audio, 'images': images}
        self.aliases = aliases
        self.refresh_metadata()

    def refresh_metadata(self):
        content, audio, images = (self.p.payloads[module]
                                  for module in ('content', 'audio', 'images'))
        for item in images['items'] + images['references']:
            item['sha256'] = digest(self.root / item['path'])
        self.put(audio['srt'], adapters.make_srt(audio['segments']).encode('utf-8'))
        envelopes = []
        for module, rel in (('content', 'revisions/content/1/output.json'),
                            ('audio', 'revisions/audio/1/output.json'),
                            ('images', 'revisions/images/1/output.json')):
            envelope = {'module': module, 'payload': self.p.payloads[module],
                        'files': [], 'input_versions': {'content': 'content-hash'}
                        if module != 'content' else {}}
            write(self.root / rel, envelope)
            envelopes.append(rel)
        timing_rel = 'reviews/media/1/visual-timing.json'
        write(self.root / timing_rel, {'vi': timeline(content, images, audio, 'vi', '16:9')})
        self.paths = envelopes + [item['path'] for item in images['references'] + images['items']]
        self.paths += self.aliases + [audio['wav'], audio['srt'], timing_rel]
        self.refresh_manifest()

    def refresh_manifest(self):
        review_rel = 'reviews/media/1/review.md'
        review = '# Media — test — revision 1\n' + '\n'.join(
            str(self.root / rel) for rel in self.paths)
        self.put(review_rel, review.encode())
        hashes = {rel: digest(self.root / rel) for rel in self.paths}
        hashes[review_rel] = digest(self.root / review_rel)
        write(self.root / 'reviews/media/1/manifest.json',
              {'stage': 'media', 'revision': 1, 'snapshot': self.snapshot,
               'assets': self.paths, 'review': review_rel, 'asset_hashes': hashes})

    def fake_invoke(self, _prompt, _schema, out, **_kwargs):
        request = read(out / 'request.json')
        self.calls.append(request['batch_id'])
        required = request['required_inspected_files']
        scenes = request['inline'].get('scenes', [])
        names = ' '.join(scene['id'] for scene in scenes)
        checks = {key: {'verdict': 'pass', 'evidence':
                         f'TEST ONLY {names} lamp and room details at 0.2s and 0.8s.'}
                  for key in request['criteria']}
        observations = {}
        for path in required:
            if path.endswith('.wav'):
                observations[path] = {'kind': 'audio',
                                      'heard': [{'scene_id': scene['id'], 'at_seconds': index + 0.25,
                                                 'spoken_words': f'Words from {scene["id"]}'}
                                                for index, scene in enumerate(scenes)],
                                      'audible_detail': 'TEST ONLY soft voice with a clear pause after the phrase.'}
            else:
                observations[path] = {'kind': 'image',
                                      'visible_detail': 'TEST ONLY one figure beside a lamp against a dark blue wall.',
                                      'continuity_detail': 'TEST ONLY same sleeve and lamp position as preceding view.',
                                      'visible_text': []}
        return {'structured_output': {'identity': request['identity'],
                'batch_id': request['batch_id'], 'inspected_files': required,
                'observations': observations, 'checks': checks}}

    def run_review(self):
        def trace(_raw, required):
            return {'conversation_id': str(uuid.uuid5(uuid.NAMESPACE_URL, '|'.join(required))),
                    'transcript_sha256': 'TEST ONLY',
                    'view_file': {path: {'step': index + 1, 'mime': []}
                                  for index, path in enumerate(required)}}
        with patch('machine_review._verify_tool_trace', side_effect=trace), \
             patch('scripts.agy_pipeline.invoke', side_effect=self.fake_invoke):
            return mr.review(self.p, 'test', 'media', self.paths, self.snapshot)

    def test_exact_asset_accounting_and_cache_resume(self):
        report_path = self.run_review()
        report = read(self.root / report_path)
        self.assertEqual(self.calls, ['references', 'scenes-01-02', 'scenes-03-04'])
        self.assertEqual(set(report['original_manifest_files']),
                         {str(self.root / rel) for rel in self.paths})
        self.assertEqual(len(report['deterministically_verified_files']), 5)
        self.assertTrue(all(path.endswith(('.jpg', '.wav'))
                            for path in report['agy_viewed_files']))
        self.calls.clear()
        self.assertEqual(self.run_review(), report_path)
        self.assertEqual(self.calls, [])

    def test_full_96_file_plan_has_ten_scene_calls(self):
        self.make_fixture(20, 3)
        plan, *_ = mr._media_plan(self.p, 'test', self.paths, self.snapshot)
        self.assertEqual(len(plan['files']), 96)
        self.assertEqual(len(plan['batches']), 11)
        self.assertEqual(len([batch for batch in plan['batches'] if batch['kind'] == 'scenes']), 10)
        report = read(self.root / self.run_review())
        self.assertEqual(len(report['original_manifest_files']), 96)
        self.assertEqual(len(report['deterministically_verified_files']), 5)
        self.assertEqual(len(report['current_to_viewed_images']), 90)
        self.assertEqual(len([name for name in self.calls if name.startswith('scenes-')]), 10)

    def test_srt_missing_cue_blocks_even_with_updated_manifest_hash(self):
        srt = self.root / self.p.payloads['audio']['srt']
        srt.write_text('\n'.join(srt.read_text().splitlines()[:-4]))
        self.refresh_manifest()
        with self.assertRaisesRegex(Blocked, 'SRT cues differ'):
            mr._media_plan(self.p, 'test', self.paths, self.snapshot)

    def test_metadata_payload_tamper_blocks_even_with_updated_manifest_hash(self):
        output = self.root / 'revisions/content/1/output.json'
        data = read(output)
        data['payload']['topic'] = 'TAMPERED TOPIC'
        write(output, data)
        self.refresh_manifest()
        with self.assertRaisesRegex(Blocked, 'envelope does not match'):
            mr._media_plan(self.p, 'test', self.paths, self.snapshot)

    def test_missing_inline_subtitle_cues_blocks_before_agy(self):
        original = mr._attach_batch_details
        def omit(*args, **kwargs):
            batch = original(*args, **kwargs)
            if batch['id'] == 'scenes-01-02':
                batch['inline']['subtitle_cues'] = []
            return batch
        with patch('machine_review._attach_batch_details', side_effect=omit):
            with self.assertRaisesRegex(Blocked, 'subtitle data omitted'):
                mr._media_plan(self.p, 'test', self.paths, self.snapshot)

    def test_one_changed_image_reuses_unaffected_scene_and_reference_batches(self):
        self.run_review()
        self.calls.clear()
        changed = self.root / 'revisions/images/1/SC01_I1_16x9.jpg'
        changed.write_bytes(b'TEST CHANGED IMAGE SC01 I1')
        self.refresh_metadata()
        self.run_review()
        self.assertEqual(self.calls, ['scenes-01-02'])

    def test_changed_boundary_image_reruns_next_scene_pair(self):
        self.run_review()
        self.calls.clear()
        changed = self.root / 'revisions/images/1/SC02_I2_16x9.jpg'
        changed.write_bytes(b'TEST CHANGED SC02 BOUNDARY')
        self.refresh_metadata()
        self.run_review()
        self.assertEqual(self.calls, ['scenes-01-02', 'scenes-03-04'])

    def test_quality_failure_is_durable(self):
        def fail(prompt, schema, out, **kwargs):
            response = self.fake_invoke(prompt, schema, out, **kwargs)
            if read(out / 'request.json')['batch_id'] == 'scenes-03-04':
                response['structured_output']['checks']['visual_continuity'] = {
                    'verdict': 'fail', 'evidence': 'TEST ONLY SC03 SC04 figure changes pose before narration.'}
            return response
        def trace(_raw, required):
            return {'conversation_id': str(uuid.uuid5(uuid.NAMESPACE_URL, '|'.join(required))),
                    'transcript_sha256': 'TEST ONLY',
                    'view_file': {path: {'step': index + 1, 'mime': []}
                                  for index, path in enumerate(required)}}
        with patch('machine_review._verify_tool_trace', side_effect=trace), \
             patch('scripts.agy_pipeline.invoke', side_effect=fail):
            with self.assertRaisesRegex(Blocked, 'visual_continuity'):
                mr.review(self.p, 'test', 'media', self.paths, self.snapshot)
        self.assertTrue(list(self.root.glob('machine-reviews/batch-cache/*/rejected.json')))
        with self.assertRaisesRegex(Blocked, 'saved quality failure'):
            self.run_review()

    def test_generic_image_observation_blocks(self):
        def filler(prompt, schema, out, **kwargs):
            response = self.fake_invoke(prompt, schema, out, **kwargs)
            if read(out / 'request.json')['batch_id'] == 'scenes-01-02':
                image = next(path for path in response['structured_output']['observations']
                             if path.endswith('.jpg'))
                response['structured_output']['observations'][image]['visible_detail'] = (
                    'I opened the file and it looks fine with no issues anywhere.')
            return response
        def trace(_raw, required):
            return {'conversation_id': str(uuid.uuid5(uuid.NAMESPACE_URL, '|'.join(required))),
                    'transcript_sha256': 'TEST ONLY',
                    'view_file': {path: {'step': index + 1, 'mime': []}
                                  for index, path in enumerate(required)}}
        with patch('machine_review._verify_tool_trace', side_effect=trace), \
             patch('scripts.agy_pipeline.invoke', side_effect=filler):
            with self.assertRaisesRegex(Blocked, 'generic per-file observation'):
                mr.review(self.p, 'test', 'media', self.paths, self.snapshot)

    def test_missing_image_inspection_cannot_approve(self):
        def incomplete(prompt, schema, out, **kwargs):
            response = self.fake_invoke(prompt, schema, out, **kwargs)
            if read(out / 'request.json')['batch_id'] == 'scenes-01-02':
                response['structured_output']['inspected_files'].pop()
            return response
        def trace(_raw, required):
            return {'conversation_id': str(uuid.uuid5(uuid.NAMESPACE_URL, '|'.join(required))),
                    'transcript_sha256': 'TEST ONLY',
                    'view_file': {path: {'step': index + 1, 'mime': []}
                                  for index, path in enumerate(required)}}
        with patch('machine_review._verify_tool_trace', side_effect=trace), \
             patch('scripts.agy_pipeline.invoke', side_effect=incomplete):
            with self.assertRaisesRegex(Blocked, 'did not inspect'):
                mr.review(self.p, 'test', 'media', self.paths, self.snapshot)
        self.assertFalse(list(self.root.glob('machine-reviews/media-*/response.json')))

    def test_cached_transcript_change_blocks_final_aggregation(self):
        self.run_review()
        def changed(_raw, required):
            return {'conversation_id': str(uuid.uuid5(uuid.NAMESPACE_URL, '|'.join(required))),
                    'transcript_sha256': 'CHANGED',
                    'view_file': {path: {'step': index + 1, 'mime': []}
                                  for index, path in enumerate(required)}}
        with patch('machine_review._verify_tool_trace', side_effect=changed):
            with self.assertRaisesRegex(Blocked, 'TRACE_CHANGED'):
                mr.review(self.p, 'test', 'media', self.paths, self.snapshot)

    def test_missing_planned_image_id_blocks_even_if_manifest_matches(self):
        for scene in self.p.payloads['content']['scenes']:
            scene['images'] = [{'id': f'{scene["id"]}_I1'}, {'id': f'{scene["id"]}_I2'}]
        for item in self.p.payloads['images']['items']:
            item['image_id'] = Path(item['path']).stem.split('_16x9')[0]
        self.p.payloads['images']['items'] = [item for item in self.p.payloads['images']['items']
                                               if item['image_id'] != 'SC02_I2']
        self.paths.remove('revisions/images/1/SC02_I2_16x9.jpg')
        with self.assertRaisesRegex(Blocked, 'planned image ID'):
            mr._media_plan(self.p, 'test', self.paths, self.snapshot)

    def test_trace_rejects_real_style_truncated_text_reply(self):
        conversation = str(uuid.uuid4())
        transcript = (self.root / conversation / '.system_generated/logs/transcript.jsonl')
        transcript.parent.mkdir(parents=True)
        path = str(self.root / self.p.payloads['audio']['srt'])
        rows = [
            {'step_index': 1, 'source': 'MODEL', 'type': 'PLANNER_RESPONSE', 'status': 'DONE',
             'tool_calls': [{'name': 'view_file', 'args': {'AbsolutePath': json.dumps(path)}}]},
            {'step_index': 2, 'source': 'MODEL', 'type': 'GENERIC', 'status': 'DONE',
             'truncated_fields': ['content'],
             'content': f'File Path: `file://{path}`\nTotal Lines: 2124\nTotal Bytes: 34794\n'
                        'Showing lines 1 to 800\nContent truncated: showing bytes 0-46082'}]
        transcript.write_text('\n'.join(json.dumps(row) for row in rows))
        with self.assertRaisesRegex(Blocked, 'TRACE_INCOMPLETE'):
            mr._verify_tool_trace({'conversation_id': conversation}, [path], self.root)


if __name__ == '__main__':
    unittest.main()
