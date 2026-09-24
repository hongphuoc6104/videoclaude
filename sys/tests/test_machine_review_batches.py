"""Batched reviewer protocol tests. Mocked responses are never production evidence."""
import json
import tempfile
import unittest
import uuid
import wave
from pathlib import Path
from unittest.mock import patch

from pilot import Blocked, digest, read
import machine_review as mr


class FakeJob:
    def __init__(self, root):
        self.root = root
        self.payloads = {}

    def job(self, _job):
        return self.root

    def path(self, _job, path):
        return self.root / path

    def payload(self, _job, module):
        return self.payloads[module]

    def brief(self, _job):
        return ({'topic': 'TEST ONLY fictional story', 'aspect_ratio': '16:9'}, 1, 'test')


class MediaBatchReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.p = FakeJob(self.root)
        self.scenes = [f'SC{i:02}' for i in range(1, 5)]
        self.paths = []
        for name in ('content.json', 'audio.json', 'images.json', 'subtitles.srt', 'visual-timing.json'):
            self.put(name, b'TEST ONLY metadata')
        (self.root / 'visual-timing.json').write_text(json.dumps({
            'vi': [{'id': sid, 'start': index, 'end': index + 1}
                   for index, sid in enumerate(self.scenes)]}))
        self.put('REF-CH01.jpg', b'TEST ONLY reference image')
        self.put('flow-reference.jpg', b'TEST ONLY reference image')
        items = []
        for sid in self.scenes:
            for number in (1, 2):
                name = f'{sid}_I{number}.jpg'
                self.put(name, f'TEST ONLY {name}'.encode())
                items.append({'scene_id': sid, 'path': name, 'prompt': 'TEST ONLY'})
        self.p.payloads['content'] = {'scenes': [{'id': sid, 'narration': f'TEST ONLY {sid}'}
                                                 for sid in self.scenes]}
        self.p.payloads['images'] = {'items': items,
                                     'references': [{'scene_id': 'REF-CH01', 'path': 'REF-CH01.jpg'}]}
        wav = self.root / 'narration.wav'
        with wave.open(str(wav), 'wb') as stream:
            stream.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\x01\x02' * 32000)
        self.paths.append('narration.wav')
        self.p.payloads['audio'] = {'wav': 'narration.wav', 'segments': [
            {'scene_id': sid, 'text': sid, 'start': index, 'end': index + 1}
            for index, sid in enumerate(self.scenes)]}
        self.snapshot = {'modules': {'audio': 'TEST ONLY', 'images': 'TEST ONLY'}}
        self.calls = []

    def put(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.paths.append(name)

    def fake_invoke(self, _prompt, _schema, out, **_kwargs):
        request = read(out / 'request.json')
        self.calls.append(request['batch_id'])
        required = request['required_inspected_files']
        scene_names = ' '.join(scene['id'] for scene in request.get('scenes', []))
        checks = {key: {'verdict': 'pass', 'evidence':
                         f'TEST ONLY {scene_names} detailed observation at seconds 0.2 and 0.8 for scene and audio.'}
                  for key in request['criteria']}
        observations = {}
        for path in required:
            if path.endswith('.wav'):
                observations[path] = {'kind': 'audio',
                                      'heard': [{'scene_id': scene['id'], 'at_seconds': index + 0.25,
                                                 'spoken_words': f'Words from {scene["id"]}'}
                                                for index, scene in enumerate(request['scenes'])],
                                      'audible_detail': 'TEST ONLY soft voice with a clear pause after the phrase.'}
            elif path.endswith('.jpg'):
                observations[path] = {'kind': 'image',
                                      'visible_detail': 'TEST ONLY one figure beside a lamp against a dark blue wall.',
                                      'continuity_detail': 'TEST ONLY same sleeve and lamp position as preceding view.',
                                      'visible_text': []}
            else:
                observations[path] = {'kind': 'text', 'line_or_field': 'line 1',
                                      'detail': 'TEST ONLY first line describes the scene and its measured timing.'}
        return {'structured_output': {'identity': request['identity'],
                'batch_id': request['batch_id'], 'inspected_files': required,
                'observations': observations, 'checks': checks}}

    def run_review(self):
        def trace(_raw, required):
            conversation = str(uuid.uuid5(uuid.NAMESPACE_URL, '|'.join(required)))
            return {'conversation_id': conversation, 'transcript_sha256': 'TEST ONLY',
                    'view_file': {path: {'step': index + 1, 'mime': []}
                                  for index, path in enumerate(required)}}
        with patch('machine_review._verify_tool_trace', side_effect=trace):
            return mr.review(self.p, 'test', 'media', self.paths, self.snapshot)

    def expected_prefix(self):
        plan, *_ = mr._media_plan(self.p, 'test', self.paths, self.snapshot)
        return [batch['id'] for batch in plan['batches']
                if batch['kind'] != 'scenes']

    def test_all_files_and_exact_audio_frames_before_final_report(self):
        with patch('scripts.agy_pipeline.invoke', side_effect=self.fake_invoke):
            report_path = self.run_review()
            self.assertEqual(self.calls, self.expected_prefix() + ['scenes-01-02', 'scenes-03-04'])
            report = read(self.root / report_path)
            self.assertEqual(set(report['inspected_files']), {str(self.root / x) for x in self.paths})
            self.assertEqual(report['audio_coverage'][0]['frames'], 32000)
            self.assertEqual(len(report['batches']), len(self.expected_prefix()) + 2)
            self.assertEqual(len(report['text_coverage']), 5)
            self.calls.clear()
            self.assertEqual(self.run_review(), report_path)
            self.assertEqual(self.calls, [])

    def test_resume_skips_only_completed_batches(self):
        def interrupt(prompt, schema, out, **kwargs):
            request = read(out / 'request.json')
            if request['batch_id'] == 'scenes-03-04':
                raise Blocked('TEST ONLY interrupted batch')
            return self.fake_invoke(prompt, schema, out, **kwargs)
        with patch('scripts.agy_pipeline.invoke', side_effect=interrupt):
            with self.assertRaisesRegex(Blocked, 'interrupted'):
                self.run_review()
        self.assertEqual(self.calls, self.expected_prefix() + ['scenes-01-02'])
        with patch('scripts.agy_pipeline.invoke', side_effect=self.fake_invoke):
            self.run_review()
        self.assertEqual(self.calls, self.expected_prefix() + ['scenes-01-02', 'scenes-03-04'])

    def test_missing_inspection_cannot_pass_or_create_report(self):
        def incomplete(prompt, schema, out, **kwargs):
            response = self.fake_invoke(prompt, schema, out, **kwargs)
            request = read(out / 'request.json')
            if request['batch_id'] == 'scenes-01-02':
                response['structured_output']['inspected_files'].pop()
            return response
        with patch('scripts.agy_pipeline.invoke', side_effect=incomplete):
            with self.assertRaises(Blocked):
                self.run_review()
        self.assertFalse(list(self.root.glob('machine-reviews/media-*/response.json')))

    def test_unsupported_audio_stays_pending_and_can_resume_after_tool_is_fixed(self):
        def unsupported(prompt, schema, out, **kwargs):
            response = self.fake_invoke(prompt, schema, out, **kwargs)
            if read(out / 'request.json')['batch_id'] == 'scenes-01-02':
                data = response['structured_output']
                clip = next(path for path in data['inspected_files'] if path.endswith('.wav'))
                data['inspected_files'].remove(clip)
                del data['observations'][clip]
                data['checks']['pronunciation_and_prosody'] = {
                    'verdict': 'unsupported',
                    'evidence': 'TEST ONLY the audio-capable tool was unavailable for this WAV clip.'}
            return response
        with patch('scripts.agy_pipeline.invoke', side_effect=unsupported):
            with self.assertRaisesRegex(Blocked, 'unsupported'):
                self.run_review()
        self.assertFalse(list(self.root.glob('machine-reviews/media-*/scenes-01-02/rejected.json')))
        with patch('scripts.agy_pipeline.invoke', side_effect=self.fake_invoke):
            self.run_review()
        self.assertEqual(self.calls, self.expected_prefix() + ['scenes-01-02',
                                                                'scenes-01-02', 'scenes-03-04'])

    def test_missing_per_file_observation_cannot_pass(self):
        def vague(prompt, schema, out, **kwargs):
            response = self.fake_invoke(prompt, schema, out, **kwargs)
            if read(out / 'request.json')['batch_id'] == 'scenes-01-02':
                response['structured_output']['observations'].popitem()
            return response
        with patch('scripts.agy_pipeline.invoke', side_effect=vague):
            with self.assertRaisesRegex(Blocked, 'did not inspect'):
                self.run_review()

    def test_generic_per_file_observation_cannot_pass(self):
        def filler(prompt, schema, out, **kwargs):
            response = self.fake_invoke(prompt, schema, out, **kwargs)
            if read(out / 'request.json')['batch_id'] == 'scenes-01-02':
                path = next(path for path in response['structured_output']['observations']
                            if path.endswith('.jpg'))
                response['structured_output']['observations'][path]['visible_detail'] = (
                    'I opened the file and it looks fine with no issues anywhere.')
            return response
        with patch('scripts.agy_pipeline.invoke', side_effect=filler):
            with self.assertRaisesRegex(Blocked, 'generic per-file observation'):
                self.run_review()

    def test_real_quality_failure_is_durable_and_prevents_retry(self):
        def fail_scene(prompt, schema, out, **kwargs):
            response = self.fake_invoke(prompt, schema, out, **kwargs)
            if read(out / 'request.json')['batch_id'] == 'scenes-03-04':
                response['structured_output']['checks']['visual_continuity'] = {
                    'verdict': 'fail', 'evidence': 'TEST ONLY SC03 figure teleports before narration describes movement.'}
            return response
        with patch('scripts.agy_pipeline.invoke', side_effect=fail_scene):
            with self.assertRaisesRegex(Blocked, 'visual_continuity'):
                self.run_review()
        self.assertTrue(list(self.root.glob('machine-reviews/media-*/scenes-03-04/rejected.json')))
        before = list(self.calls)
        with patch('scripts.agy_pipeline.invoke', side_effect=self.fake_invoke):
            with self.assertRaisesRegex(Blocked, 'saved quality failure'):
                self.run_review()
        self.assertEqual(self.calls, before)

    def test_audio_gap_and_clip_tamper_fail_closed(self):
        self.p.payloads['audio']['segments'][1]['start'] = 1.1
        with self.assertRaisesRegex(Blocked, 'gap'):
            mr._media_plan(self.p, 'test', self.paths, self.snapshot)
        self.p.payloads['audio']['segments'][1]['start'] = 1
        with patch('scripts.agy_pipeline.invoke', side_effect=self.fake_invoke):
            self.run_review()
        clip = next(self.root.glob('machine-reviews/media-*/clips/scenes-01-02-vi.wav'))
        clip.write_bytes(b'TAMPERED')
        with patch('scripts.agy_pipeline.invoke', side_effect=self.fake_invoke):
            with self.assertRaisesRegex(Blocked, 'audio clip unreadable'):
                self.run_review()

    def test_changed_manifest_gets_new_identity(self):
        with patch('scripts.agy_pipeline.invoke', side_effect=self.fake_invoke):
            first = self.run_review()
            (self.root / 'SC01_I1.jpg').write_bytes(b'TEST ONLY changed image')
            second = self.run_review()
        self.assertNotEqual(first, second)
        self.assertEqual(len(list(self.root.glob('machine-reviews/media-*/response.json'))), 2)

    def test_long_utf8_text_source_is_losslessly_covered_by_all_chunks(self):
        original = (('001: Gõ cửa, đèn xanh.\r\n' * 1200) + 'Kết thúc.').encode('utf-8')
        self.put('long-subtitles.srt', original)
        plan, *_ = mr._media_plan(self.p, 'test', self.paths, self.snapshot)
        chunks = plan['text_sources'][str(self.root / 'long-subtitles.srt')]
        self.assertGreater(len(chunks), 1)
        self.assertEqual(b''.join(original[item['start_byte']:item['end_byte']]
                                  for item in chunks), original)
        with patch('scripts.agy_pipeline.invoke', side_effect=self.fake_invoke):
            report = read(self.root / self.run_review())
        entry = next(item for item in report['text_coverage']
                     if item['source'].endswith('long-subtitles.srt'))
        self.assertEqual(entry['bytes'], len(original))
        self.assertEqual(entry['chunks'], len(chunks))

    def test_missing_planned_image_id_blocks_even_if_manifest_agrees_with_payload(self):
        for scene in self.p.payloads['content']['scenes']:
            scene['images'] = [{'id': f'{scene["id"]}_I1'}, {'id': f'{scene["id"]}_I2'}]
        for item in self.p.payloads['images']['items']:
            item['image_id'] = Path(item['path']).stem
            item['ratio'] = '16:9'
        self.p.payloads['images']['items'] = [item for item in self.p.payloads['images']['items']
                                              if item['image_id'] != 'SC02_I2']
        self.paths.remove('SC02_I2.jpg')
        with self.assertRaisesRegex(Blocked, 'planned image ID'):
            mr._media_plan(self.p, 'test', self.paths, self.snapshot)

    def test_dual_language_requires_every_english_clip_too(self):
        self.put('narration-en.wav', (self.root / 'narration.wav').read_bytes())
        self.p.payloads['audio']['en'] = {'wav': 'narration-en.wav',
                                           'segments': list(self.p.payloads['audio']['segments'])}
        timing = read(self.root / 'visual-timing.json')
        timing['en'] = timing['vi']
        (self.root / 'visual-timing.json').write_text(json.dumps(timing))
        with patch('scripts.agy_pipeline.invoke', side_effect=self.fake_invoke):
            report = read(self.root / self.run_review())
        self.assertEqual({track['lang'] for track in report['audio_coverage']}, {'vi', 'en'})
        for batch in (item for item in report['batches'] if item['batch_id'].startswith('scenes-')):
            self.assertEqual(len([path for path in batch['response']['inspected_files']
                                  if path.endswith('.wav')]), 2)

    def test_trace_requires_successful_view_file_for_each_path(self):
        conversation = str(uuid.uuid4())
        transcript = (self.root / conversation / '.system_generated/logs/transcript.jsonl')
        transcript.parent.mkdir(parents=True)
        paths = [str(self.root / 'SC01_I1.jpg'), str(self.root / 'narration.wav'),
                 str(self.root / 'content.json')]
        rows = []
        for index, path in enumerate(paths):
            rows.append({'step_index': index * 2 + 1, 'source': 'MODEL',
                         'type': 'PLANNER_RESPONSE', 'status': 'DONE',
                         'tool_calls': [{'name': 'view_file',
                                         'args': {'AbsolutePath': json.dumps(path)}}]})
            suffix = Path(path).suffix
            mime = 'image/jpeg' if suffix == '.jpg' else 'audio/wav' if suffix == '.wav' else None
            source = Path(path).read_bytes()
            complete_text = (f'File Path: `file://{path}`\nTotal Lines: 1\n'
                             f'Total Bytes: {len(source)}\nShowing lines 1 to 1\n1: content')
            rows.append({'step_index': index * 2 + 2, 'source': 'MODEL', 'type': 'GENERIC',
                         'status': 'DONE', 'content': complete_text if not mime else 'The entire, complete content',
                         'media': [{'mime_type': mime}] if mime else []})
        transcript.write_text('\n'.join(json.dumps(row) for row in rows))
        trace = mr._verify_tool_trace({'conversation_id': conversation}, paths, self.root)
        self.assertEqual(set(trace['view_file']), set(paths))
        rows[3]['status'] = 'ERROR'
        transcript.write_text('\n'.join(json.dumps(row) for row in rows))
        with self.assertRaisesRegex(Blocked, 'TRACE_INCOMPLETE'):
            mr._verify_tool_trace({'conversation_id': conversation}, paths, self.root)
        transcript.unlink()
        with self.assertRaisesRegex(Blocked, 'TRACE_UNAVAILABLE'):
            mr._verify_tool_trace({'conversation_id': conversation}, paths, self.root)

    def test_real_style_truncated_text_reply_cannot_count_full_source(self):
        conversation = str(uuid.uuid4())
        transcript = (self.root / conversation / '.system_generated/logs/transcript.jsonl')
        transcript.parent.mkdir(parents=True)
        path = str(self.root / 'subtitles.srt')
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

    def test_cached_trace_change_or_removal_blocks_resume(self):
        conversation = str(uuid.uuid4())
        brain = self.root / '.gemini/antigravity-cli/brain'
        transcript = brain / conversation / '.system_generated/logs/transcript.jsonl'
        transcript.parent.mkdir(parents=True)
        path = str(self.root / 'content.json')
        size = Path(path).stat().st_size
        rows = [
            {'step_index': 1, 'source': 'MODEL', 'type': 'PLANNER_RESPONSE', 'status': 'DONE',
             'tool_calls': [{'name': 'view_file', 'args': {'AbsolutePath': json.dumps(path)}}]},
            {'step_index': 2, 'source': 'MODEL', 'type': 'GENERIC', 'status': 'DONE',
             'content': f'File Path: `file://{path}`\nTotal Lines: 1\nTotal Bytes: {size}\nShowing lines 1 to 1'}]
        transcript.write_text('\n'.join(json.dumps(row) for row in rows))
        with patch('machine_review.Path.home', return_value=self.root):
            proof = mr._verify_tool_trace({'conversation_id': conversation}, [path])
            mr._verify_cached_trace(proof, [path])
            transcript.write_text(transcript.read_text() + '\n')
            with self.assertRaisesRegex(Blocked, 'TRACE_CHANGED'):
                mr._verify_cached_trace(proof, [path])
            transcript.unlink()
            with self.assertRaisesRegex(Blocked, 'TRACE_UNAVAILABLE'):
                mr._verify_cached_trace(proof, [path])


if __name__ == '__main__':
    unittest.main()
