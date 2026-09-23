#!/usr/bin/env python3
"""Time the real renderer on a synthetic long video; no Flow, no TTS, no pilot job.

Builds a render folder shaped like adapters.render output (scene images with
beats, a narration track with pauses, the CC0 bed mix, props.json) and runs
renderer/render.mjs on it. Reports wall time per phase and the realtime factor.

  python3 scripts/render_benchmark.py --minutes 20 --ratio 16:9 --out /tmp/bench
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import sound  # noqa: E402

SR = 24000


def narration(seconds, scenes):
    """Speech-like bursts with sentence pauses, so ducking and file size resemble a real voice track."""
    rng = np.random.default_rng(1)
    x = np.zeros(int(seconds * SR))
    segments, per = [], seconds / scenes
    for i in range(scenes):
        t = i * per + .3
        while t < (i + 1) * per - 1:
            length = min(rng.uniform(2.5, 6), (i + 1) * per - t - .5)
            n = int(length * SR)
            carrier = np.sin(2 * np.pi * rng.uniform(110, 160) * np.arange(n) / SR)
            x[int(t * SR):int(t * SR) + n] = .25 * carrier * (.5 + .5 * np.sin(2 * np.pi * 4 * np.arange(n) / SR))
            segments.append({'scene_id': f'SC{i + 1:02}', 'start': round(t, 3), 'end': round(t + length, 3), 'text': 'Câu thử số %d.' % len(segments)})
            t += length + rng.uniform(.4, 1.2)
    return x, segments


def images(public, scenes, beats, size):
    out = []
    for i in range(scenes):
        row = []
        for k in range(beats):
            name = f'{i}-{k}.jpg'
            im = Image.new('RGB', size, (20 + i * 5 % 60, 22, 30 + k * 20))
            draw = ImageDraw.Draw(im)
            for r in range(0, max(size), 90):
                draw.ellipse([size[0] // 2 - r, size[1] // 2 - r, size[0] // 2 + r, size[1] // 2 + r], outline=(60 + k * 30, 50, 40))
            draw.text((60, 60), f'SC{i + 1:02} beat {k + 1}', fill=(230, 220, 200))
            im.save(public / name, quality=90)
            row.append(name)
        out.append(row)
    return out


def build(out, minutes, ratio, scenes, beats, concurrency):
    if out.exists():
        shutil.rmtree(out)
    public = out / 'public'
    public.mkdir(parents=True)
    seconds = minutes * 60
    voice, segments = narration(seconds, scenes)
    sound.write_wav(public / 'narration.wav', voice, SR)
    size = (1920, 1080) if ratio == '16:9' else (1080, 1920)
    files = images(public, scenes, beats, size)
    per = seconds / scenes
    effects = ['zoom_in', 'fade', 'zoom_out', 'slide_left', 'hold', 'cut']
    plan = [{'id': f'SC{i + 1:02}', 'title': f'Cảnh {i + 1}', 'start': round(i * per, 3), 'end': round((i + 1) * per, 3),
             'image': files[i][0],
             'images': [{'id': f'B{i}-{k}', 'src': files[i][k], 'at': round(k * per / beats, 3),
                         'effect': effects[(i + k) % len(effects)], 'focus': {'x': .5, 'y': .45}} for k in range(beats)]}
            for i in range(scenes)]
    content = {'scenes': [{'id': s['id'], 'narration': ' '.join(x['text'] for x in segments if x['scene_id'] == s['id'])} for s in plan]}
    used = sound.build(content, {'sound': {'bed': 'drone', 'sfx': False}}, {'segments': segments}, 'vi',
                       public / 'narration.wav', public / 'mix.wav')
    cues = [{'start': x['start'], 'end': x['end'], 'text': x['text']} for x in segments]
    props = {'duration': seconds, 'scenes': plan, 'segments': segments, 'cues': cues, 'aspect_ratio': ratio,
             'audio_language': 'vi', 'render_concurrency': concurrency, 'audio_files': {'vi': 'mix.wav'}}
    (out / 'props.json').write_text(json.dumps(props, ensure_ascii=False))
    return {'scenes': scenes, 'beats': scenes * beats, 'sound': [x['id'] for x in used]}


def machine():
    gpu = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], capture_output=True, text=True)
    mem = next((int(line.split()[1]) // 1024 for line in open('/proc/meminfo') if line.startswith('MemTotal')), None)
    return {'host': platform.node(), 'cpus': os.cpu_count(), 'memory_mb': mem,
            'gpu': gpu.stdout.strip() if gpu.returncode == 0 else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--minutes', type=float, default=20)
    ap.add_argument('--ratio', choices=['16:9', '9:16'], default='16:9')
    ap.add_argument('--scenes', type=int, default=40)
    ap.add_argument('--beats', type=int, default=3, help='images per scene')
    ap.add_argument('--concurrency', type=int, default=None, help='Remotion workers (default: config render_concurrency)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    concurrency = a.concurrency or json.loads((ROOT / 'config.json').read_text()).get('render_concurrency', 4)
    started = time.time()
    info = build(a.out, a.minutes, a.ratio, a.scenes, a.beats, concurrency)
    prepared = time.time()
    r = subprocess.run(['node', str(ROOT / 'renderer/render.mjs'), str(a.out.resolve())], cwd=ROOT, capture_output=True, text=True)
    finished = time.time()
    (a.out / 'render.log').write_text(r.stdout + '\n' + r.stderr)
    video = a.out / 'video.mp4'
    probe = json.loads(subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(video)],
                                      capture_output=True, text=True).stdout or '{}') if video.exists() else {}
    stills = sorted(a.out.glob('SC*.png'), key=lambda f: f.stat().st_mtime)
    render = finished - prepared
    report = {**machine(), 'ratio': a.ratio, 'minutes': a.minutes, 'render_concurrency': concurrency, **info,
              'ok': r.returncode == 0 and video.exists(),
              'prepare_seconds': round(prepared - started, 1), 'render_seconds': round(render, 1),
              # stills are cut from the finished video with ffmpeg, after the render
              'stills_seconds': round(stills[-1].stat().st_mtime - video.stat().st_mtime, 1) if stills and video.exists() else None,
              'realtime_factor': round(render / (a.minutes * 60), 2),
              'video_seconds': float(probe.get('format', {}).get('duration', 0)) or None,
              'video_mb': round(video.stat().st_size / 1e6, 1) if video.exists() else None,
              'adapter_timeout_seconds': 3600, 'error': r.stderr[-800:] if r.returncode else None}
    (a.out / 'benchmark.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report['ok'] else 2)


if __name__ == '__main__':
    main()
