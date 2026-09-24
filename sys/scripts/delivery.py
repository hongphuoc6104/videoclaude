"""Voice direction: how each narration chunk is read.

A plain TTS pass reads every sentence at one speed, one level and one pause, so
a story's climax sounds exactly like its setup (measured on job thu-5p-h007g:
speed within 5%, loudness within 0.8 dB across all ten scenes). The brief's
`delivery` profile (copied from horror/channel.json) gives each scene a style
from its required points, and a few text cues adjust single lines: quoted
speech, short lines in tense scenes, questions, "…" beats and the line that
closes a tense scene. The words are never changed; only speed, level and the
silence between chunks. Pure functions: no audio, no TTS runtime.
"""
import re

ENDS = '.!?…'


def split_dialogue(texts):
    """Give quoted speech its own chunk (`…hoảng loạn: “Đừng cười nữa!` -> two
    chunks) and end a chunk at a written beat (`tia sáng… Nó đang mở.`), so the
    beat gets its own silence."""
    out = []
    for text in [x for t in texts for x in re.split(r'(?<=…)\s+|(?<=\.\.\.)\s+', t)]:
        rest = text
        while True:
            i = rest.find('“', 1)
            if i < 0 or not rest[:i].strip():
                break
            out.append(rest[:i].rstrip())
            rest = rest[i:]
        out.append(rest)
    parts = [x for x in out if x.strip()]
    # One-word sound cues such as “Cốc… cốc… cốc.” can fail Gwen's duration
    # check when each beat is synthesized alone. Keep the exact words and
    # punctuation, but let the voice read them with an adjacent sentence.
    joined = []
    for i, part in enumerate(parts):
        if len(re.findall(r'\w+', part)) == 1 and joined:
            joined[-1] += ' ' + part
        elif len(re.findall(r'\w+', part)) == 1 and i + 1 < len(parts):
            parts[i + 1] = part + ' ' + parts[i + 1]
        else:
            joined.append(part)
    return joined


def dialogue_flags(texts):
    """True for every chunk inside a quotation, including follow-on chunks of a
    multi-sentence quote (“Đừng cười nữa! | Tôi nhận tội rồi! | …dưới đó!”)."""
    flags, open_ = [], False
    for t in texts:
        s = t.lstrip()
        flags.append(open_ or s[:1] in '“"')
        for ch in t:
            if ch == '“':
                open_ = True
            elif ch == '”':
                open_ = False
            elif ch == '"':
                open_ = not open_
    return flags


def bare(text):
    return text.rstrip().rstrip('”"\'’ ')


def words(text):
    return len(re.findall(r'\w+', text))


def scene_style(scene, profile):
    roles = [profile['roles'][r] for r in scene.get('requirements') or [] if r in profile['roles']]
    if not roles:
        return 'setup'
    return min(roles, key=profile['priority'].index)


def direct(scenes, profile, mood=None):
    """Per scene: style, chunk texts, per-chunk speed and gain (dB), the gap after
    every chunk but the last, and the pause after the scene (`tail`)."""
    m = (profile.get('moods') or {}).get(mood or profile.get('mood'), {})
    speed_k, pause_k = m.get('speed', 1.0), m.get('pause', 1.0)
    lines = profile['lines']
    short, dia, rev = lines['short'], lines['dialogue'], lines['reveal']
    out = []
    for k, sc in enumerate(scenes):
        role = scene_style(sc, profile)
        st = profile['styles'][role]
        texts = split_dialogue(sc['texts'])
        spoken = dialogue_flags(texts)
        n = len(texts)
        speed = [st['speed'] * speed_k] * n
        gain = [0.0] * n
        cues = [[] for _ in texts]
        gaps = [st['sentence'] if bare(t)[-1:] in ENDS else st['minor'] for t in texts]

        def at_least(i, seconds):
            if 0 <= i < n:
                gaps[i] = max(gaps[i], seconds)

        for i, t in enumerate(texts):
            end = bare(t)[-1:]
            if spoken[i]:
                cues[i].append('dialogue')
                gain[i] = dia['shout_gain_db'] if end == '!' else dia['gain_db']
                if i and not spoken[i - 1]:
                    at_least(i - 1, dia['pause_before'])
                if i + 1 < n and spoken[i + 1]:
                    gaps[i] = dia['inner']
                else:
                    at_least(i, dia['pause_after'])
                continue
            if t.rstrip().endswith(('…', '...')):
                cues[i].append('beat')
                at_least(i, lines['beat_pause'])
            if end == '?':
                cues[i].append('question')
                at_least(i, lines['question_pause'])
            if st.get('tense') and words(t) <= short['max_words']:
                cues[i].append('short')
                at_least(i - 1, short['pause_before'])
                at_least(i, short['pause_after'])
        last = n - 1
        if st.get('tense') and n > 1 and not spoken[last]:
            cues[last].append('reveal')
            at_least(last - 1, rev['pause_before'])
            gain[last] = rev['gain_db']
            speed[last] *= rev['speed']
        tail = profile.get('end_tail', st['tail']) if k == len(scenes) - 1 else st['tail']
        out.append({'scene_id': sc['scene_id'], 'style': role, 'texts': texts,
                    'speeds': [round(x, 3) for x in speed], 'gains': gain, 'cues': cues,
                    'gaps': [round(g * pause_k, 3) for g in gaps[:-1]], 'tail': round(tail * pause_k, 3)})
    return out
