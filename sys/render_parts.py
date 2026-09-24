"""Segmented video render: long timelines are rendered as short parts and joined.

The Remotion composition is a pure function of the frame number (every scene,
beat, Ken Burns move and subtitle cue is looked up from the absolute time), so
rendering frames [start, end) of the SAME composition gives exactly the frames a
single pass would give. Parts are cut only at scene starts, never inside a
subtitle cue, rendered video-only (muted), verified, cached by a content hash,
joined with the ffmpeg concat demuxer (stream copy when every part has the same
codec parameters) and the full mastered audio track is muxed once at the end,
so the joins can never click or drift.

Flow for one output plan (renderer/outputs.mjs decides the plans):
  split -> key every part -> reuse cached parts -> render the missing ones
  (one automatic retry) -> join -> mux audio -> verify frame count/audio length.
"""
import hashlib, json, math, os, shutil, subprocess, time
from pathlib import Path
from pilot import Blocked, read, write, digest

VERSION = 1
DEFAULT_SEGMENT_SECONDS = 120
RENDERER_FILES = ('renderer/index.tsx', 'renderer/render.mjs', 'renderer/outputs.mjs')
REMOTION_PACKAGES = ('remotion', '@remotion/renderer', '@remotion/bundler')
# Plan props that cannot change a muted frame's pixels. Scenes and cues are
# keyed per part (only the slice a part shows); everything else stays in the key.
NOT_PIXELS = {'scenes', 'en_scenes', 'cues', 'segments', 'audio_files', 'audioSrc',
              'duration', 'en_duration', 'render_concurrency'}
# Config keys that change the picture itself (resolution/fps come from the plan).
PIXEL_CONFIG = ('fps',)
# Same AAC settings Remotion used when it encoded the audio itself.
AUDIO_CODEC = ['-c:a', 'aac', '-b:a', '320k', '-ar', '48000']


# ---------------------------------------------------------------- splitting
def first_frame(seconds, fps):
    """First frame f with f/fps >= seconds, using the renderer's own float maths."""
    f = max(0, math.ceil(seconds * fps))
    while f > 0 and (f - 1) / fps >= seconds: f -= 1
    while f / fps < seconds: f += 1
    return f


def visible(item, frame, fps):
    t = frame / fps
    return item['start'] <= t < item['end']


def on_screen(item, start, end, fps):
    """True when the renderer shows item (scene or cue, start <= t < end) on a frame in [start, end)."""
    return first_frame(item['start'], fps) < end and first_frame(item['end'], fps) > start


def cut_points(scenes, cues, total, fps):
    """Frames where a new part may start: the first frame of a scene, unless a
    subtitle cue stays on screen across that cut."""
    points = set()
    for scene in scenes:
        b = first_frame(scene['start'], fps)
        if 0 < b < total and not any(visible(c, b - 1, fps) and visible(c, b, fps) for c in cues):
            points.add(b)
    return sorted(points)


def split(scenes, cues, total, fps, seconds):
    """Parts [(start, end), ...] of about `seconds`, cut only at scene starts.
    A scene longer than the target stays whole; a tiny tail joins the part before."""
    target = max(1, round(seconds * fps)) if seconds and seconds > 0 else total
    points = cut_points(scenes, cues, total, fps)
    parts, start = [], 0
    while total - start > target * 1.25:
        later = [c for c in points if c > start]
        if not later: break
        below = [c for c in later if c - start <= target]
        above = [c for c in later if c - start > target]
        options = ([max(below)] if below else []) + ([min(above)] if above else [])
        pick = min(options, key=lambda c: abs(c - start - target))
        parts.append((start, pick)); start = pick
    parts.append((start, total))
    if len(parts) > 1 and parts[-1][1] - parts[-1][0] < target * .25:
        tail = parts.pop(); parts[-1] = (parts[-1][0], tail[1])
    return parts


# ---------------------------------------------------------------- cache keys
def renderer_hash(root):
    h = hashlib.sha256()
    for name in RENDERER_FILES:
        h.update(name.encode()); h.update(Path(root, name).read_bytes())
    for pkg in REMOTION_PACKAGES:
        meta = Path(root, 'node_modules', pkg, 'package.json')
        h.update(pkg.encode()); h.update(str(read(meta).get('version') if meta.is_file() else 'missing').encode())
    return h.hexdigest()


def part_key(plan, start, end, public, file_hash, renderer, cfg):
    """Hash of everything that can change the pixels of frames [start, end)."""
    props, fps = plan['props'], plan['fps']
    shown = sorted((s for s in props['scenes'] if on_screen(s, start, end, fps)), key=lambda s: s['start'])
    # Frames not covered by any scene fall back to the last scene in the renderer.
    cursor, gap = start, False
    for s in shown:
        if first_frame(s['start'], fps) > cursor: gap = True
        cursor = max(cursor, first_frame(s['end'], fps))
    if (gap or cursor < end or not shown) and props['scenes']:
        last = props['scenes'][-1]
        if last not in shown: shown.append(last)
    def image(name):
        return file_hash(Path(public) / name) if name else None
    scenes = []
    for s in shown:
        s = json.loads(json.dumps(s))
        s['image'] = image(s.get('image'))
        for beat in s.get('images', []): beat['src'] = image(beat.get('src'))
        scenes.append(s)
    cues = [] if props.get('hideSubtitles') else [c for c in props.get('cues', []) if on_screen(c, start, end, fps)]
    body = {'version': VERSION, 'renderer': renderer, 'fps': fps, 'total_frames': plan['durationInFrames'],
            'range': [start, end], 'width': plan['width'], 'height': plan['height'],
            'props': {k: v for k, v in props.items() if k not in NOT_PIXELS},
            'config': {k: cfg.get(k) for k in PIXEL_CONFIG}, 'scenes': scenes, 'cues': cues}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# ---------------------------------------------------------------- probing
def stream_info(path):
    """Frame count (packets) and the codec parameters that must match for a stream-copy join."""
    data = json.loads(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_data_hash', 'sha256',
         '-show_entries', 'stream=codec_name,profile,width,height,pix_fmt,r_frame_rate,time_base,nb_read_packets,extradata_hash',
         '-of', 'json', str(path)], text=True))
    streams = data.get('streams') or []
    if not streams: return None
    s = streams[0]
    first = json.loads(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-read_intervals', '%+#1',
         '-show_entries', 'packet=flags', '-of', 'json', str(path)], text=True)).get('packets') or [{}]
    return {'frames': int(s.get('nb_read_packets') or 0), 'keyframe_first': 'K' in first[0].get('flags', ''),
            'params': {k: s.get(k) for k in ('codec_name', 'profile', 'width', 'height', 'pix_fmt',
                                              'r_frame_rate', 'time_base', 'extradata_hash')}}


def media_seconds(path, kind):
    data = json.loads(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-select_streams', kind + ':0', '-show_entries', 'stream=duration',
         '-of', 'json', str(path)], text=True))
    streams = data.get('streams') or []
    return float(streams[0]['duration']) if streams and streams[0].get('duration') not in (None, 'N/A') else None


def check_part(path, plan, start, end):
    """None when the part file is exactly the frames [start, end) of this plan."""
    if not Path(path).is_file() or not Path(path).stat().st_size: return 'no output file'
    try: info = stream_info(path)
    except (subprocess.CalledProcessError, ValueError) as ex: return f'unreadable part: {ex}'
    if not info: return 'no video stream'
    p = info['params']
    if info['frames'] != end - start: return f"frame count {info['frames']} != expected {end - start}"
    if (p['width'], p['height']) != (plan['width'], plan['height']): return f"size {p['width']}x{p['height']} != plan"
    if p['r_frame_rate'] not in (f"{plan['fps']}/1", str(plan['fps'])): return f"fps {p['r_frame_rate']} != {plan['fps']}"
    # Remotion's NVENC path tags 4:2:0 as full range (yuvj420p); both are plain 8-bit 4:2:0.
    if p['codec_name'] != 'h264' or p['pix_fmt'] not in ('yuv420p', 'yuvj420p'):
        return f"codec {p['codec_name']}/{p['pix_fmt']} != h264/yuv420p"
    if not info['keyframe_first']: return 'part does not start with a keyframe'
    return None


# ---------------------------------------------------------------- Remotion
def run_remotion(root, out, request, timeout):
    """Render the requested parts in one Remotion process (one bundle, one browser).
    Tests replace this function; it is the only place node is called for parts."""
    try:
        r = subprocess.run(['node', str(Path(root) / 'renderer/render.mjs'), str(Path(out).resolve()), '--parts', str(request)],
                           cwd=root, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as ex:
        def text(x): return x.decode(errors='replace') if isinstance(x, bytes) else (x or '')
        return -1, text(ex.stdout), text(ex.stderr) + f'\nTimed out after {timeout}s'


# ---------------------------------------------------------------- join
def concat(files, dest, reencode):
    listing = Path(dest).with_suffix('.ffconcat')
    listing.write_text('ffconcat version 1.0\n' + ''.join(f"file '{Path(f).resolve()}'\n" for f in files))
    codec = ['-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p'] if reencode else ['-c', 'copy']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing),
                    '-map', '0:v:0', *codec, '-movflags', '+faststart', str(dest)], check=True, capture_output=True, text=True)
    listing.unlink()


def mux(video, audio, dest, seconds):
    """Full mastered track muxed once: padded/cut to the exact picture length."""
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(video), '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0',
                    '-c:v', 'copy', *AUDIO_CODEC, '-af', 'apad', '-t', f'{seconds:.6f}', '-movflags', '+faststart', str(dest)],
                   check=True, capture_output=True, text=True)


def wav_seconds(path):
    import wave
    try:
        with wave.open(str(path)) as w: return w.getnframes() / w.getframerate()
    except Exception:
        return media_seconds(path, 'a')


# ---------------------------------------------------------------- driver
def render_all(root, out, cache_dir, cfg, timeout, log=None):
    """Render every plan in out/plans.json into out/<plan file>.
    Returns the manifest written to out/render-parts.json; raises Blocked with the
    failing part's index and log after one automatic retry."""
    root, out, cache_dir = Path(root), Path(out), Path(cache_dir)
    log = log if log is not None else []
    plans = read(out / 'plans.json')
    public = out / 'public'
    seconds = cfg.get('render_segment_seconds', DEFAULT_SEGMENT_SECONDS)
    renderer = renderer_hash(root)
    hashes = {}
    def file_hash(path):
        key = str(path)
        if key not in hashes: hashes[key] = digest(path)
        return hashes[key]
    work = out / 'parts'; work.mkdir(exist_ok=True); cache_dir.mkdir(parents=True, exist_ok=True)
    manifest = {'segment_seconds': seconds, 'renderer': renderer, 'cache': str(cache_dir), 'plans': []}
    parts = []
    for n, plan in enumerate(plans):
        fps, total = plan['fps'], plan['durationInFrames']
        if total < 1: raise Blocked(f"Render plan {plan['file']} has no frames")
        props = plan['props']
        cues = [] if props.get('hideSubtitles') else props.get('cues', [])
        ranges = split(props['scenes'], cues, total, fps, seconds)
        if ranges[0][0] != 0 or ranges[-1][1] != total or any(a[1] != b[0] for a, b in zip(ranges, ranges[1:])):
            raise Blocked('Render split does not cover the timeline exactly')
        entry = {'file': plan['file'], 'fps': fps, 'frames': total, 'parts': []}
        for i, (a, b) in enumerate(ranges):
            key = part_key(plan, a, b, public, file_hash, renderer, cfg)
            ids = [s['id'] for s in props['scenes'] if on_screen(s, a, b, fps)]
            part = {'plan': n, 'index': i, 'count': len(ranges), 'from': a, 'to': b, 'key': key,
                    'seconds': round((b - a) / fps, 3), 'scenes': ids, 'cache': str(cache_dir / f'{key}.mp4'),
                    'source': 'cache', 'attempts': 0, 'fps': fps, 'total': total}
            entry['parts'].append(part); parts.append(part)
        manifest['plans'].append(entry)

    todo = []
    for part in parts:
        plan = plans[part['plan']]
        if check_part(part['cache'], plan, part['from'], part['to']) is None: continue
        Path(part['cache']).unlink(missing_ok=True)
        part['source'] = 'rendered'; todo.append(part)
    log.append(f"segmented render: {len(parts)} part(s), {len(parts) - len(todo)} from cache, {len(todo)} to render")

    for attempt in (1, 2):
        if not todo: break
        request = work / f'request-{attempt}.json'; result = work / f'result-{attempt}.json'
        result.unlink(missing_ok=True)
        jobs = []
        for part in todo:
            part['attempts'] = attempt
            output = work / f"{part['key']}.mp4"; output.unlink(missing_ok=True)
            jobs.append({'id': part['key'], 'plan': part['plan'], 'from': part['from'], 'to': part['to'],
                         'fps': part['fps'], 'total': part['total'], 'output': str(output.resolve())})
        write(request, {'result': str(result.resolve()), 'parts': jobs})
        started = time.time()
        code, stdout, stderr = run_remotion(root, out, request, timeout)
        log.append(f'--- parts attempt {attempt}: exit {code} in {time.time() - started:.1f}s ---\n{stdout}\n{stderr}')
        reported = {x['id']: x for x in (read(result) if result.is_file() else [])}
        failed = []
        for part in todo:
            plan = plans[part['plan']]; output = work / f"{part['key']}.mp4"
            report = reported.get(part['key'], {})
            problem = check_part(output, plan, part['from'], part['to'])
            if problem is None and report.get('ok', True):
                os.replace(output, part['cache'])
                write(Path(part['cache']).with_suffix('.json'), {'key': part['key'], 'file': plan['file'], 'from': part['from'],
                      'to': part['to'], 'scenes': part['scenes'], 'rendered_at': time.time()})
                continue
            output.unlink(missing_ok=True)
            reason = report.get('error') or problem or f'renderer exit {code}'
            part['error'] = reason
            label = f"{Path(plan['file']).stem}-part-{part['index'] + 1:02}"
            part['log'] = str((work / f'{label}.log').relative_to(out))
            with open(work / f'{label}.log', 'a') as fh:
                fh.write(f"attempt {attempt}: frames {part['from']}-{part['to'] - 1}; {reason}\n"
                         f"--- renderer stderr (tail) ---\n{stderr[-4000:]}\n")
            failed.append(part)
        todo = failed
    write(out / 'render-parts.json', manifest)
    if todo:
        part = todo[0]
        raise Blocked(f"Render part {part['index'] + 1}/{part['count']} of {plans[part['plan']]['file']} "
                      f"(frames {part['from']}-{part['to'] - 1}, scenes {', '.join(part['scenes'])}) failed twice: "
                      f"{part['error'][:300]}; see {part['log']}. {len(todo)} part(s) missing; "
                      f"the next run renders only the missing parts.")

    for n, (plan, entry) in enumerate(zip(plans, manifest['plans'])):
        files = [p['cache'] for p in entry['parts']]
        infos = [stream_info(f) for f in files]
        entry['join'] = 'copy' if all(i['params'] == infos[0]['params'] for i in infos) else 'reencode'
        silent = work / f"{Path(plan['file']).stem}.video.mp4"
        concat(files, silent, entry['join'] == 'reencode')
        joined = stream_info(silent)['frames']
        if joined != plan['durationInFrames']:
            raise Blocked(f"Joined {plan['file']} has {joined} frames, timeline needs {plan['durationInFrames']}")
        seconds_total = plan['durationInFrames'] / plan['fps']
        audio = public / plan['props'].get('audioSrc', 'narration.wav')
        track = wav_seconds(audio)
        if track is None or abs(track - plan['props']['duration']) > 1 / plan['fps'] + .01:
            raise Blocked(f"Audio {audio.name} lasts {track}s, timeline {plan['props']['duration']}s")
        dest = out / plan['file']
        mux(silent, audio, dest, seconds_total)
        silent.unlink()
        final = stream_info(dest)['frames']; a = media_seconds(dest, 'a'); v = media_seconds(dest, 'v')
        if final != plan['durationInFrames']:
            raise Blocked(f"{plan['file']} has {final} frames after muxing, timeline needs {plan['durationInFrames']}")
        if a is None or v is None or abs(a - v) > .05 or abs(v - seconds_total) > .5 / plan['fps']:
            raise Blocked(f"{plan['file']} audio {a}s / video {v}s do not match the timeline {seconds_total:.3f}s")
        entry.update(checked={'frames': final, 'video_seconds': v, 'audio_seconds': a, 'track_seconds': track})
        log.append(f"{plan['file']}: {len(files)} part(s) joined by {entry['join']}, {final} frames, audio {a:.3f}s")
    write(out / 'render-parts.json', manifest)
    return manifest


def stills(video, scenes, fps, frames, out):
    """Representative still per scene: its middle frame, cut from the finished video."""
    paths = []
    for scene in scenes:
        frame = min(frames - 1, math.floor((scene['start'] + scene['end']) / 2 * fps + .5))
        dest = Path(out) / (scene['id'] + '.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{frame / fps:.3f}', '-i', str(video), '-frames:v', '1', str(dest)],
                       check=True, capture_output=True)
        paths.append(dest)
    return paths


def forget(manifest_path, index, file=None):
    """Set one cached part aside (cache/render-parts/rejected/) so the next render
    re-renders only that part; for a part that looks wrong although its inputs did not change."""
    manifest = read(manifest_path)
    plans = [x for x in manifest['plans'] if file in (None, x['file'])]
    if len(plans) != 1: raise Blocked('Choose the output file with --file: ' + ', '.join(x['file'] for x in manifest['plans']))
    parts = plans[0]['parts']
    if not 1 <= index <= len(parts): raise Blocked(f'Part must be 1..{len(parts)}')
    cached = Path(parts[index - 1]['cache'])
    if not cached.is_file(): return None
    aside = cached.parent / 'rejected' / cached.name; aside.parent.mkdir(exist_ok=True)
    # A second rejection of the same key must preserve the earlier file.
    suffix = 2
    while aside.exists():
        aside = aside.parent / f'{cached.stem}-{suffix}{cached.suffix}'
        suffix += 1
    os.replace(cached, aside)
    return aside


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Set one cached render part aside so the next render re-renders only it.')
    ap.add_argument('command', choices=['forget'])
    ap.add_argument('manifest', help='runs/JOB/revisions/render/N/render-parts.json')
    ap.add_argument('--part', type=int, required=True, help='1-based part number from the manifest')
    ap.add_argument('--file', help='output file when the job has several (dual)')
    a = ap.parse_args()
    print(forget(a.manifest, a.part, a.file) or 'part not in cache; the next render renders it anyway')
