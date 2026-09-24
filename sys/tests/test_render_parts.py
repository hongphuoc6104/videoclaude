"""Segmented render: scene-aligned parts, content-hash cache, retry/block, joins.

Remotion is never started: render_parts.run_remotion is replaced by a fake that
encodes tiny real H.264 parts with ffmpeg, so the probing, concat join and
audio mux run for real on small files.
"""
import json, math, subprocess, sys, tempfile, unittest, wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import render_parts
from pilot import Blocked, read, write

FPS = 30
W, H = 64, 36


def wav(path, seconds):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes(b'\0\0' * round(seconds * 48000))


def scenes_of(lengths):
    out, t = [], 0.0
    for i, length in enumerate(lengths, 1):
        out.append({'id': f'SC{i:02}', 'title': 'TEST', 'start': t, 'end': t + length, 'image': f'{i}-SC{i:02}.png',
                    'images': [{'id': 'B1', 'src': f'{i}-SC{i:02}.png', 'at': 0, 'effect': 'zoom_in', 'focus': {'x': .5, 'y': .5}}]})
        t += length
    return out


class FakeRemotion:
    """Stands in for `node render.mjs DIR --parts REQ`: writes real tiny H.264 parts."""
    def __init__(self, fail=(), short=()):
        self.fail, self.short, self.calls = set(fail), set(short), []

    def __call__(self, root, out, request, timeout):
        req = read(request); self.calls.append([p['from'] for p in req['parts']]); results = []
        for part in req['parts']:
            if part['from'] in self.fail:
                results.append({'id': part['id'], 'ok': False, 'error': 'TEST renderer crash'}); continue
            frames = part['to'] - part['from'] - (1 if part['from'] in self.short else 0)
            color = '#%02x%02x40' % (part['from'] % 256, (part['from'] // 256) % 256)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c={color}:s={W}x{H}:r={FPS}',
                            '-frames:v', str(frames), '-c:v', 'libx264', '-g', str(FPS), '-pix_fmt', 'yuv420p',
                            part['output']], check=True)
            results.append({'id': part['id'], 'ok': True})
        write(req['result'], results)
        return 0, 'TEST', ''


class SplitTest(unittest.TestCase):
    def test_parts_start_only_at_scene_starts_and_long_scenes_stay_whole(self):
        scenes = scenes_of([3, 2, 9, 2, 3, 1.5, 2.5])      # SC03 (9 s) is longer than the 4 s target
        total = math.ceil(scenes[-1]['end'] * FPS)
        parts = render_parts.split(scenes, [], total, FPS, 4)
        starts = {render_parts.first_frame(s['start'], FPS) for s in scenes}
        self.assertEqual(parts[0][0], 0); self.assertEqual(parts[-1][1], total)
        self.assertTrue(all(a[1] == b[0] for a, b in zip(parts, parts[1:])))
        self.assertTrue(all(a in starts for a, _ in parts))
        long = (render_parts.first_frame(5, FPS), render_parts.first_frame(14, FPS))
        self.assertTrue(any(a <= long[0] and long[1] <= b for a, b in parts), parts)
        self.assertGreater(len(parts), 2)

    def test_never_cuts_inside_a_subtitle_cue(self):
        scenes = scenes_of([3, 3, 3, 3])
        cues = [{'text': 'x', 'start': 2.5, 'end': 3.5}]      # still on screen when SC02 starts
        self.assertNotIn(90, render_parts.cut_points(scenes, cues, 360, FPS))
        self.assertIn(180, render_parts.cut_points(scenes, cues, 360, FPS))
        self.assertTrue(all(a != 90 for a, _ in render_parts.split(scenes, cues, 360, FPS, 3)))

    def test_non_frame_aligned_scene_start_uses_renderer_frame(self):
        # Frame 91 (t=3.0333) is the first frame the renderer shows SC02 when it starts at 3.01 s.
        self.assertEqual(render_parts.first_frame(3.01, FPS), 91)
        self.assertEqual(render_parts.first_frame(3.0, FPS), 90)

    def test_short_video_is_one_part(self):
        self.assertEqual(render_parts.split(scenes_of([2, 2]), [], 120, FPS, 120), [(0, 120)])


class SegmentedRenderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); base = Path(self.tmp.name)
        self.out, self.cache = base / 'render', base / 'cache/render-parts'
        self.scenes = scenes_of([2, 2, 2, 2, 2, 2])            # 12 s; 4 s target -> 3 parts
        duration = 12.0
        public = self.out / 'public'; public.mkdir(parents=True)
        for s in self.scenes: (public / s['image']).write_bytes(b'TEST IMAGE ' + s['id'].encode())
        wav(public / 'narration.wav', duration)
        cues = [{'text': s['id'], 'start': s['start'], 'end': s['end'], 'scene_id': s['id']} for s in self.scenes]
        props = {'duration': duration, 'scenes': self.scenes, 'cues': cues, 'segments': [], 'aspect_ratio': '9:16',
                 'width': W, 'height': H, 'hideSubtitles': False, 'audioSrc': 'narration.wav'}
        self.total = math.ceil(duration * FPS)
        write(self.out / 'plans.json', [{'file': 'video.mp4', 'fps': FPS, 'width': W, 'height': H,
                                        'durationInFrames': self.total, 'props': props}])
        self.cfg = {'render_segment_seconds': 4, 'fps': FPS}

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, fake):
        with patch.object(render_parts, 'run_remotion', side_effect=fake):
            return render_parts.render_all(ROOT, self.out, self.cache, self.cfg, 60)

    def frames(self, path):
        return render_parts.stream_info(path)['frames']

    def test_first_run_renders_joins_and_muxes_full_audio(self):
        fake = FakeRemotion(); manifest = self.render(fake)
        parts = manifest['plans'][0]['parts']
        self.assertEqual([(p['from'], p['to']) for p in parts], [(0, 120), (120, 240), (240, 360)])
        self.assertEqual(fake.calls, [[0, 120, 240]])
        self.assertEqual(manifest['plans'][0]['join'], 'copy')
        video = self.out / 'video.mp4'
        self.assertEqual(self.frames(video), self.total)
        self.assertAlmostEqual(render_parts.media_seconds(video, 'a'), 12.0, delta=.05)
        self.assertAlmostEqual(render_parts.media_seconds(video, 'v'), 12.0, delta=.02)
        self.assertEqual(len(list(self.cache.glob('*.mp4'))), 3)
        self.assertEqual(read(self.out / 'render-parts.json')['plans'][0]['checked']['frames'], self.total)

    def test_cache_hit_renders_nothing(self):
        self.render(FakeRemotion())
        (self.out / 'video.mp4').unlink()
        again = FakeRemotion(); manifest = self.render(again)
        self.assertEqual(again.calls, [])
        self.assertEqual({p['source'] for p in manifest['plans'][0]['parts']}, {'cache'})
        self.assertEqual(self.frames(self.out / 'video.mp4'), self.total)

    def test_one_changed_scene_rerenders_only_its_part(self):
        first = self.render(FakeRemotion())['plans'][0]['parts']
        (self.out / 'public' / self.scenes[3]['image']).write_bytes(b'TEST IMAGE SC04 redrawn')   # SC04: 6-8 s, part 2
        again = FakeRemotion(); second = self.render(again)['plans'][0]['parts']
        self.assertEqual(again.calls, [[120]])
        self.assertEqual([p['source'] for p in second], ['cache', 'rendered', 'cache'])
        self.assertEqual([p['key'] for p in first][::2], [p['key'] for p in second][::2])
        self.assertNotEqual(first[1]['key'], second[1]['key'])

    def test_subtitle_change_only_touches_its_part_and_hidden_subtitles_ignore_cues(self):
        plan = read(self.out / 'plans.json')[0]
        keys = lambda pl: [render_parts.part_key(pl, a, b, self.out / 'public', render_parts.digest, 'R', self.cfg)
                           for a, b in [(0, 120), (120, 240), (240, 360)]]
        before = keys(plan); plan['props']['cues'][5]['text'] = 'changed'
        after = keys(plan)
        self.assertEqual(before[:2], after[:2]); self.assertNotEqual(before[2], after[2])
        plan['props']['hideSubtitles'] = True; hidden = keys(plan); plan['props']['cues'][0]['text'] = 'again'
        self.assertEqual(hidden, keys(plan))

    def test_failed_part_is_retried_once_then_blocks_and_next_run_renders_only_missing(self):
        broken = FakeRemotion(fail={120})
        with self.assertRaisesRegex(Blocked, r'Render part 2/3 of video.mp4 \(frames 120-239.*failed twice.*next run renders only the missing'):
            self.render(broken)
        self.assertEqual(broken.calls, [[0, 120, 240], [120]])
        log = (self.out / 'parts/video-part-02.log').read_text()
        self.assertIn('attempt 1', log); self.assertIn('attempt 2', log); self.assertIn('TEST renderer crash', log)
        self.assertFalse((self.out / 'video.mp4').exists())
        healthy = FakeRemotion(); manifest = self.render(healthy)
        self.assertEqual(healthy.calls, [[120]])
        self.assertEqual([p['source'] for p in manifest['plans'][0]['parts']], ['cache', 'rendered', 'cache'])
        self.assertEqual(self.frames(self.out / 'video.mp4'), self.total)

    def test_failure_on_first_attempt_only_is_healed_by_the_retry(self):
        class Flaky(FakeRemotion):
            def __call__(self, root, out, request, timeout):
                self.fail = {240} if not self.calls else set()
                return super().__call__(root, out, request, timeout)
        flaky = Flaky(); self.render(flaky)
        self.assertEqual(flaky.calls, [[0, 120, 240], [240]])

    def test_part_frame_count_mismatch_blocks(self):
        short = FakeRemotion(short={0})
        with self.assertRaisesRegex(Blocked, r'Render part 1/3.*frame count 119 != expected 120'):
            self.render(short)
        self.assertEqual(short.calls, [[0, 120, 240], [0]])
        self.assertFalse(any(p.name.startswith('video') for p in self.out.glob('*.mp4')))

    def test_joined_frame_count_mismatch_blocks(self):
        real = render_parts.concat
        with patch.object(render_parts, 'concat', side_effect=lambda files, dest, re: real(files[:-1], dest, re)):
            with self.assertRaisesRegex(Blocked, r'Joined video.mp4 has 240 frames, timeline needs 360'):
                self.render(FakeRemotion())

    def test_audio_length_mismatch_blocks(self):
        wav(self.out / 'public/narration.wav', 10.0)
        with self.assertRaisesRegex(Blocked, 'Audio narration.wav lasts'):
            self.render(FakeRemotion())

    def test_forgetting_a_wrong_part_rerenders_only_that_part(self):
        self.render(FakeRemotion())
        aside = render_parts.forget(self.out / 'render-parts.json', 3)
        self.assertEqual(aside.parent, self.cache / 'rejected'); self.assertTrue(aside.is_file())
        again = FakeRemotion(); self.render(again)
        self.assertEqual(again.calls, [[240]])
        second_aside = render_parts.forget(self.out / 'render-parts.json', 3)
        self.assertNotEqual(aside, second_aside)
        self.assertTrue(aside.is_file() and second_aside.is_file())
        with self.assertRaises(Blocked): render_parts.forget(self.out / 'render-parts.json', 4)

    def test_changed_renderer_invalidates_every_part(self):
        self.render(FakeRemotion())
        with patch.object(render_parts, 'renderer_hash', return_value='TEST other renderer'):
            again = FakeRemotion(); self.render(again)
        self.assertEqual(again.calls, [[0, 120, 240]])


class AdapterWiringTest(unittest.TestCase):
    def test_render_runs_prepare_then_parts_and_returns_the_manifest(self):
        import adapters
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); job = root / 'job'; out = job / 'revisions/render/1'; out.mkdir(parents=True)
            wav(job / 'voice.wav', 4.0); (job / 'a.png').write_bytes(b'TEST A'); (job / 'b.png').write_bytes(b'TEST B')
            write(root / 'config.json', {'render_segment_seconds': 2, 'fps': FPS})
            for name in render_parts.RENDERER_FILES:
                (root / name).parent.mkdir(parents=True, exist_ok=True); (root / name).write_text('TEST ' + name)
            audio = {'wav': 'voice.wav', 'duration': 4.0, 'segments': [{'scene_id': 'SC01', 'text': 'Một hai.', 'start': 0, 'end': 2},
                                                                       {'scene_id': 'SC02', 'text': 'Ba bốn.', 'start': 2, 'end': 4}]}
            payloads = {'content': {}, 'images': {}, 'audio': audio}
            p = SimpleNamespace(root=root, job=lambda j: job, path=lambda j, s: job / s, payload=lambda j, m: payloads[m],
                                brief=lambda j: ({'aspect_ratio': '9:16'}, 1, 'TEST'))
            planned = [{'id': 'SC01', 'title': 'T', 'image': 'a.png', 'start': 0, 'end': 2},
                       {'id': 'SC02', 'title': 'T', 'image': 'b.png', 'start': 2, 'end': 4}]
            commands, real_run = [], subprocess.run
            def node(cmd, **kw):
                if cmd[0] != 'node': return real_run(cmd, **kw)   # ffmpeg joins/stills run for real
                commands.append(cmd[2:])
                props = read(out / 'props.json')
                write(out / 'layout.json', {'passed': True, 'applies': True, 'checked_cues': 2, 'failures': []})
                write(out / 'plans.json', [{'file': 'video.mp4', 'fps': FPS, 'width': W, 'height': H, 'durationInFrames': 120,
                                            'props': {**props, 'width': W, 'height': H, 'hideSubtitles': False, 'audioSrc': 'narration.wav'}}])
                return subprocess.CompletedProcess(cmd, 0, 'prepared', '')
            fake = FakeRemotion()
            with patch('scripts.story_plan.timeline', return_value=planned), patch('adapters.subprocess.run', side_effect=node), \
                 patch.object(render_parts, 'run_remotion', side_effect=fake):
                result = adapters.render(p, 'TEST', out)
            self.assertEqual(commands, [[str(out.resolve()), '--prepare']])
            self.assertEqual(fake.calls, [[0, 60]])
            self.assertEqual(result['render_parts'], 'revisions/render/1/render-parts.json')
            self.assertEqual(result['stills'], ['revisions/render/1/SC01.png', 'revisions/render/1/SC02.png'])
            self.assertTrue(all((job / s).stat().st_size for s in result['stills']))
            self.assertEqual(render_parts.stream_info(out / 'video.mp4')['frames'], 120)
            self.assertTrue((job / 'cache/render-parts').is_dir())
            self.assertIn('segmented render: 2 part(s)', (out / 'render.log').read_text())


class RendererPrepareTest(unittest.TestCase):
    def test_prepare_writes_plans_without_rendering(self):
        """Real node call: --prepare resolves the output plans and frame counts only (16:9 has no cue check)."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / 'public').mkdir()
            write(out / 'props.json', {'duration': 61.01, 'aspect_ratio': '16:9', 'audio_language': 'vi', 'scenes': [], 'cues': [],
                                       'audio_files': {'vi': 'mix.wav'}})
            subprocess.run(['node', str(ROOT / 'renderer/render.mjs'), str(out), '--prepare'], cwd=ROOT, check=True, timeout=120)
            plans = read(out / 'plans.json')
            self.assertEqual([(x['file'], x['fps'], x['width'], x['height'], x['durationInFrames']) for x in plans],
                             [('video.mp4', 30, 1920, 1080, 1831)])
            self.assertEqual(plans[0]['props']['audioSrc'], 'mix.wav')
            self.assertFalse(read(out / 'layout.json')['applies'])
            self.assertFalse((out / 'video.mp4').exists())


if __name__ == '__main__':
    unittest.main()
