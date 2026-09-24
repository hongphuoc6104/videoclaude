"""Video review accounting with synthetic files and fake AGY replies only."""
import json
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from pilot import Blocked, digest, hashobj, read, write
from scripts import video_review as vr
import machine_review


class FakeJob:
    def __init__(self, root):
        self.root = root
        self.content = {'scenes': [{'id': 'SC01', 'narration': 'First scene.'},
                                   {'id': 'SC02', 'narration': 'Second scene.'}]}
        self.audio = {'duration': 1000, 'segments': [
            {'scene_id': 'SC01', 'start': 0, 'end': 500, 'text': 'First scene.'},
            {'scene_id': 'SC02', 'start': 500, 'end': 1000, 'text': 'Second scene.'}]}
        self.video = {'video': 'revisions/render/1/video.mp4',
                      'render_parts': 'revisions/render/1/render-parts.json'}

    def job(self, job):
        return self.root

    def path(self, job, rel):
        return self.root / rel

    def payload(self, job, module):
        return {'content': self.content, 'audio': self.audio, 'render': self.video}[module]

    def brief(self, job):
        return {'aspect_ratio': '16:9', 'audio_language': 'vi'}, 1, 'TEST'


class VideoReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.p = FakeJob(self.root)
        source = self.root / self.p.video['video']
        source.parent.mkdir(parents=True)
        source.write_bytes(b'TEST synthetic final video')
        parts = self.root / self.p.video['render_parts']
        write(parts, {'plans': [{'file': 'video.mp4', 'frames': 30000, 'fps': 30,
                                'parts': [{'from': 0, 'to': 15000},
                                          {'from': 15000, 'to': 30000}],
                                'checked': {'frames': 30000, 'audio_seconds': 1000}}]})
        self.snapshot = {'modules': {'render': {'revision': 1, 'hash': 'TEST'}}}
        self.paths = [self.p.video['video']]
        review = self.root / 'reviews/video/1/review.md'
        review.parent.mkdir(parents=True)
        review.write_text('TEST video review')
        self.manifest = {'snapshot': self.snapshot, 'assets': self.paths,
                         'review': 'reviews/video/1/review.md',
                         'asset_hashes': {self.paths[0]: digest(source),
                                          'reviews/video/1/review.md': digest(review)}}
        self.probe = {'frames': 30000, 'fps': 30, 'rate': 48000,
                      'width': 1920, 'height': 1080,
                      'video_seconds': 1000, 'audio_seconds': 1000}

    def plan(self):
        with patch('workflow.current', return_value=self.manifest), \
             patch('workflow.approved', return_value=True), \
             patch('scripts.video_review._probe', return_value=self.probe):
            return vr._source_plan(self.p, 'test', self.paths, self.snapshot)

    def test_ten_review_intervals_cover_final_and_overlap_joins(self):
        plan = self.plan()
        self.assertEqual(len(plan['batches']), 10)
        self.assertEqual([b['core'] for b in plan['batches']],
                         [[i * 3000, (i + 1) * 3000] for i in range(10)])
        self.assertEqual(plan['batches'][4]['clip'], [11940, 15060])
        self.assertEqual(plan['batches'][5]['clip'], [14940, 18060])
        self.assertIn(2.0, plan['batches'][5]['inline']['render_joins_at_clip_seconds'])

    def test_changed_render_manifest_fails_even_if_review_paths_unchanged(self):
        path = self.root / self.p.video['render_parts']
        value = read(path)
        value['plans'][0]['parts'][1]['from'] = 15001
        write(path, value)
        with self.assertRaisesRegex(Blocked, 'do not cover'):
            self.plan()

    def test_missing_media_approval_blocks_video_plan(self):
        with patch('workflow.current', return_value=self.manifest), \
             patch('workflow.approved', return_value=False):
            with self.assertRaisesRegex(Blocked, 'media approval'):
                vr._source_plan(self.p, 'test', self.paths, self.snapshot)

    def test_exact_clips_are_decoded_from_final_mp4(self):
        source = self.root / 'tiny.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'testsrc2=size=160x90:rate=30:duration=3',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=3',
                        '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(source)],
                       check=True, capture_output=True)
        batch = {'source': str(source), 'source_sha256': digest(source),
                 'clip': [15, 75], 'probe': {'fps': 30, 'rate': 48000,
                                            'width': 160, 'height': 90}}
        video, audio, receipt = vr._clip_files(self.p, 'test', batch)
        self.assertEqual(vr._probe_video_only(video)['frames'], 60)
        self.assertEqual(receipt['audio_sha256'], digest(audio))
        self.assertEqual(vr._clip_files(self.p, 'test', batch)[:2], (video, audio))
        Path(audio).write_bytes(b'TAMPERED')
        with self.assertRaisesRegex(Blocked, 'cached review clip changed'):
            vr._clip_files(self.p, 'test', batch)

    def test_accepted_batches_resume_and_final_report_covers_every_core(self):
        plan = self.plan()
        plan['batches'] = plan['batches'][:2]
        plan['batches'][1]['core'] = [3000, 6000]
        plan['batches'][1]['clip'] = [2940, 6000]
        plan['batches'][0]['probe']['frames'] = 6000
        calls = []
        def clips(p, job, batch):
            folder = self.root / ('fake-' + batch['id'])
            folder.mkdir(exist_ok=True)
            v, a = folder / 'clip.mp4', folder / 'clip.wav'
            v.write_bytes(b'VIDEO ' + batch['id'].encode())
            a.write_bytes(b'AUDIO ' + batch['id'].encode())
            return str(v), str(a), {'video_sha256': digest(v), 'audio_sha256': digest(a)}
        def invoke(prompt, schema, out, **kwargs):
            request = read(out / 'request.json')
            calls.append(request['batch_id'])
            moments = {name: {'at_seconds': sec, 'detail':
                       f'TEST only: at the {name} the figure crosses the room while the narrator speaks clearly.'}
                       for name, sec in [('start', 0), ('middle', 50), ('end', 95)]}
            ids = request['inline']['scene_ids']
            result = {'identity': request['identity'], 'batch_id': request['batch_id'],
                      'inspected_files': request['required_inspected_files'],
                      'video_moments': moments, 'audio_moments': moments,
                      'scene_observations': {sid: 'TEST only: one figure reaches the blue door with no visible text.'
                                             for sid in ids},
                      'checks': {name: {'verdict': 'pass', 'evidence':
                                 f'TEST only {" ".join(ids)} has a clear visual and audible transition.'}
                                 for name in vr.CRITERIA}}
            return {'structured_output': result}
        def trace(raw, required):
            return {'conversation_id': str(uuid.uuid4()), 'transcript_sha256': 'TEST',
                    'view_file': {path: {'step': i + 1, 'mime': []}
                                  for i, path in enumerate(required)}}
        with patch('scripts.video_review._source_plan', return_value=plan), \
             patch('scripts.video_review._clip_files', side_effect=clips), \
             patch('scripts.agy_pipeline.invoke', side_effect=invoke), \
             patch('machine_review._verify_tool_trace', side_effect=trace), \
             patch('machine_review._verify_cached_trace'):
            result = vr.review_video_batches(self.p, 'test', self.paths, self.snapshot)
            self.assertEqual(len(read(self.root / result)['batches']), 2)
            self.assertEqual(calls, ['16x9-01', '16x9-02'])
            calls.clear()
            self.assertEqual(vr.review_video_batches(self.p, 'test', self.paths, self.snapshot), result)
            self.assertEqual(calls, [])

    def test_video_trace_requires_moving_video_media(self):
        movie = self.root / 'clip.mp4'
        movie.write_bytes(b'TEST')
        cid = str(uuid.uuid4())
        transcript = self.root / cid / '.system_generated/logs/transcript.jsonl'
        transcript.parent.mkdir(parents=True)
        rows = [{'step_index': 1, 'source': 'MODEL', 'type': 'PLANNER_RESPONSE', 'status': 'DONE',
                 'tool_calls': [{'name': 'view_file', 'args': {'AbsolutePath': json.dumps(str(movie))}}]},
                {'step_index': 2, 'source': 'MODEL', 'type': 'GENERIC', 'status': 'DONE',
                 'media': [{'mime_type': 'image/png'}]}]
        transcript.write_text('\n'.join(json.dumps(x) for x in rows))
        with self.assertRaisesRegex(Blocked, 'did not successfully view'):
            machine_review._verify_tool_trace({'conversation_id': cid}, [str(movie)], self.root)
        rows[1]['media'] = [{'mime_type': 'video/mp4'}]
        transcript.write_text('\n'.join(json.dumps(x) for x in rows))
        self.assertIn(str(movie), machine_review._verify_tool_trace(
            {'conversation_id': cid}, [str(movie)], self.root)['view_file'])


if __name__ == '__main__':
    unittest.main()
