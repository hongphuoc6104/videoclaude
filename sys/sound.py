"""Background bed and sound effects under the narration; CC0 only.

Every sound comes from assets/audio/library.json. An item is either generated
here from a fixed recipe and seed (released by this project as CC0-1.0), or a
file someone added with its CC0-1.0 licence, author, source URL and sha256.
Anything else is refused.

The mix is made at the video stage: the bed loops under the narration and is
pulled down while someone speaks; effects land on the words the script
anchored them to. The narration itself is never changed. Each render writes
sound.json listing every sound used, with its licence and source.
"""
import hashlib
import json
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
LIBRARY = ROOT / 'assets/audio/library.json'
LICENSE = 'CC0-1.0'
GAIN = {'bed_gap': 10 ** (-20 / 20), 'bed_speech': 10 ** (-31 / 20), 'sfx': 10 ** (-10 / 20)}


class SoundError(ValueError):
    pass


# ------------------------------------------------------------------ library

def library(path=LIBRARY):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    items = {}
    for item in data['items']:
        where = item.get('id', '?')
        if item['id'] in items:
            raise SoundError(f'{where}: duplicate id')
        if item.get('license') != LICENSE:
            raise SoundError(f'{where}: licence must be {LICENSE}; other licences are not accepted')
        if item.get('kind') not in ('bed', 'sfx'):
            raise SoundError(f'{where}: kind must be bed or sfx')
        if not item.get('title') or not item.get('author'):
            raise SoundError(f'{where}: title and author are required')
        if item.get('source') == 'generated':
            if item.get('generator', {}).get('name') not in GENERATORS:
                raise SoundError(f'{where}: unknown generator')
        elif item.get('source') == 'file':
            file = ROOT / item.get('file', '')
            if not item.get('source_url') or not file.is_file():
                raise SoundError(f'{where}: a file item needs file and source_url')
            if hashlib.sha256(file.read_bytes()).hexdigest() != item.get('sha256'):
                raise SoundError(f'{where}: sha256 does not match the file')
        else:
            raise SoundError(f'{where}: source must be generated or file')
        items[item['id']] = item
    return items


def ids(kind, path=LIBRARY):
    return [k for k, v in library(path).items() if v['kind'] == kind]


# ------------------------------------------------------------------ recipes

def band(x, sr, low, high):
    """Zero-phase band-pass by FFT mask; enough for noise shaping, no scipy needed."""
    spec = np.fft.rfft(x)
    freq = np.fft.rfftfreq(len(x), 1 / sr)
    spec[(freq < low) | (freq > high)] = 0
    return np.fft.irfft(spec, len(x))


def smooth_noise(rng, n, sr, rate):
    """Slow random wobble in [0, 1] changing about `rate` times per second."""
    points = rng.random(int(n / sr * rate) + 3)
    return np.interp(np.arange(n) / sr * rate, np.arange(len(points)), points)


def env(n, sr, attack, decay):
    t = np.arange(n) / sr
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def norm(x, peak):
    return x / (np.max(np.abs(x)) or 1) * peak


def drone(sr, rng, seconds=60):
    t = np.arange(int(sr * seconds)) / sr
    tones = sum(a * np.sin(2 * np.pi * f * t + rng.random() * 6.28)
                for f, a in [(55, 1), (55.35, .8), (82.4, .35), (110.2, .15)])
    swell = .65 + .35 * np.sin(2 * np.pi * t / 23 + rng.random() * 6.28)
    rumble = band(rng.standard_normal(len(t)), sr, 25, 180) * 4
    return norm(tones * swell + rumble, .5)


def wind(sr, rng, seconds=60):
    n = int(sr * seconds)
    noise = rng.standard_normal(n)
    low, high = band(noise, sr, 80, 450), band(noise, sr, 350, 1400)
    gust = smooth_noise(rng, n, sr, .25)
    return norm(low * (.4 + gust) + high * gust ** 2 * .5, .5)


def pulse(sr, rng, seconds=60):
    base = drone(sr, rng, seconds) * .7
    beat = heartbeat(sr, rng)
    period = int(sr * 1.6)
    for start in range(int(sr * .5), len(base) - len(beat), period):
        base[start:start + len(beat)] += beat * .35
    return norm(base, .5)


def low_hit(sr, rng):
    n = int(sr * 2.2)
    sweep = np.sin(2 * np.pi * np.cumsum(np.linspace(80, 32, n)) / sr)
    return norm(sweep * env(n, sr, .005, .6) + band(rng.standard_normal(n), sr, 30, 300) * env(n, sr, .002, .12) * 3, .9)


def heartbeat(sr, rng):
    one = int(sr * .18)
    thump = np.sin(2 * np.pi * 48 * np.arange(one) / sr) * env(one, sr, .004, .05)
    out = np.zeros(int(sr * .8))
    out[:one] += thump
    out[int(sr * .28):int(sr * .28) + one] += thump * .7
    return norm(out, .9)


def knock(sr, rng):
    one = int(sr * .12)
    t = np.arange(one) / sr
    hit = np.sin(2 * np.pi * 190 * t) * env(one, sr, .001, .025) + band(rng.standard_normal(one), sr, 200, 2500) * env(one, sr, .0005, .008)
    out = np.zeros(int(sr * 1.1))
    for i, gap in enumerate([0, .3, .6]):
        start = int(sr * gap)
        out[start:start + one] += hit * (1 - .1 * i)
    return norm(out, .9)


def gust(sr, rng):
    n = int(sr * 2.6)
    shape = np.sin(np.pi * np.arange(n) / n) ** 2
    return norm(band(rng.standard_normal(n), sr, 250, 1800) * shape, .8)


def creak(sr, rng):
    n = int(sr * 1.4)
    pitch = np.linspace(95, 68, n) * (1 + .04 * (smooth_noise(rng, n, sr, 12) - .5))
    saw = 2 * ((np.cumsum(pitch) / sr) % 1) - 1
    grains = (smooth_noise(rng, n, sr, 30) > .45).astype(float)
    shaped = band(saw, sr, 300, 2400) * grains * np.sin(np.pi * np.arange(n) / n)
    return norm(shaped, .8)


GENERATORS = {'drone': drone, 'wind': wind, 'pulse': pulse, 'low_hit': low_hit,
              'heartbeat': heartbeat, 'knock': knock, 'gust': gust, 'creak': creak}


def render_item(item, sr):
    if item['source'] == 'generated':
        g = item['generator']
        return GENERATORS[g['name']](sr, np.random.default_rng(g['seed']))
    x, rate = read_wav(ROOT / item['file'])
    x = x.mean(axis=1) if x.ndim == 2 else x
    if rate != sr:
        x = np.interp(np.arange(int(len(x) * sr / rate)) * rate / sr, np.arange(len(x)), x)
    return x


# ------------------------------------------------------------------ wav

def read_wav(path):
    with wave.open(str(path), 'rb') as w:
        if w.getsampwidth() != 2:
            raise SoundError(f'{path}: only 16-bit PCM WAV is supported')
        data = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64) / 32768
        channels, sr = w.getnchannels(), w.getframerate()
    return (data.reshape(-1, channels) if channels > 1 else data), sr


def write_wav(path, x, sr):
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1 if x.ndim == 1 else x.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# ------------------------------------------------------------------ mix

def loop(x, n, sr, fade=2.0):
    """Repeat a clip to n samples with equal-power crossfades at each seam."""
    f = min(int(sr * fade), len(x) // 3)
    ramp = np.sin(np.linspace(0, np.pi / 2, f))
    body = x.copy()
    body[:f] = x[:f] * ramp + x[-f:] * ramp[::-1]
    body = body[:-f]
    reps = int(np.ceil(n / len(body)))
    return np.tile(body, reps)[:n]


def speech_envelope(n, sr, spans, attack=.12, release=.7):
    """1 while someone speaks, 0 in pauses, with soft edges so the bed moves smoothly."""
    mask = np.zeros(n)
    for start, end in spans:
        mask[int(start * sr):int(end * sr)] = 1
    width = int(sr * (attack + release) / 2) or 1
    return np.clip(np.convolve(mask, np.ones(width) / width, mode='same') * 1.6, 0, 1)


def mix(narration, sr, spans, bed=None, events=()):
    """narration: float array (mono or stereo). events: (seconds, sfx samples, gain)."""
    voice = narration if narration.ndim == 1 else narration.mean(axis=1)
    n = len(voice)
    out = voice.copy()
    if bed is not None:
        speech = speech_envelope(n, sr, spans)
        gain = GAIN['bed_gap'] * (1 - speech) + GAIN['bed_speech'] * speech
        fade = np.minimum(1, np.minimum(np.arange(n) / (sr * 3), (n - np.arange(n)) / (sr * 4)))
        out += loop(bed, n, sr) * gain * fade
    for at, clip, g in events:
        start = int(at * sr)
        piece = clip[:max(0, n - start)]
        out[start:start + len(piece)] += piece * g
    peak = np.max(np.abs(out))
    if peak > .97:
        out *= .97 / peak
    return out if narration.ndim == 1 else np.repeat(out[:, None], narration.shape[1], axis=1)


def anchor_seconds(text, anchor, spans):
    """Where an anchored phrase is spoken: inside the sentence chunk that holds it when chunk texts are known
    (Vietnamese TTS segments), otherwise interpolated across the scene (same rule as visual beats)."""
    from scripts.story_plan import occurrence
    offset = occurrence(text, anchor)
    start, end = spans[0]['start'], spans[-1]['end']
    cursor = 0
    for seg in spans:
        pos = text.find(seg.get('text', '\0'), cursor)
        if pos < 0:
            continue
        if pos <= offset < pos + len(seg['text']):
            return seg['start'] + (offset - pos) / max(1, len(seg['text'])) * (seg['end'] - seg['start'])
        cursor = pos + len(seg['text'])
    return start + offset / max(1, len(text)) * (end - start)


def build(content, brief, audio, language, narration_path, out_path, lib=None):
    """Mix one language track; return the manifest rows of every sound used."""
    lib = lib or library()
    plan = brief.get('sound') or {}
    x, sr = read_wav(narration_path)
    rows = audio['en']['scenes'] if language == 'en' else audio['segments']
    spans = [(s['start'], s['end']) for s in rows]
    scenes = {}
    for s in rows:
        scenes.setdefault(s['scene_id'], []).append(s)
    used, events = [], []
    bed = None
    if plan.get('bed'):
        item = lib[plan['bed']]
        bed = render_item(item, sr)
        used.append(item)
    if plan.get('sfx'):
        cache = {}
        for sc in content['scenes']:
            text = sc.get('narration_en' if language == 'en' else 'narration', '')
            for cue in sc.get('sfx', []):
                anchor = cue['anchor'].get(language)
                if not anchor or sc['id'] not in scenes:
                    continue
                if cue['id'] not in cache:
                    cache[cue['id']] = render_item(lib[cue['id']], sr)
                    used.append(lib[cue['id']])
                events.append((anchor_seconds(text, anchor, scenes[sc['id']]), cache[cue['id']], GAIN['sfx']))
    write_wav(out_path, mix(x, sr, spans, bed, events), sr)
    return [{k: item.get(k) for k in ('id', 'kind', 'title', 'license', 'author', 'source', 'source_url', 'generator')
             if item.get(k) is not None} for item in used]


def main(argv):
    """python3 sound.py check | preview ID OUT.wav"""
    if argv[:1] == ['check']:
        lib = library()
        print(json.dumps({'items': len(lib), 'bed': ids('bed'), 'sfx': ids('sfx'), 'license': LICENSE}, ensure_ascii=False))
    elif argv[:1] == ['preview'] and len(argv) == 3:
        write_wav(argv[2], render_item(library()[argv[1]], 24000), 24000)
    else:
        raise SystemExit(main.__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
