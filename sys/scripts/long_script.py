"""Long-form content-v3 generation in scene chunks.

A 10-30 minute story (20-40 scenes) does not fit one agy call (180 s). For
briefs with more scenes than config content_chunk_scenes, the orchestrator asks
for a plan first (full outline and the character list), then writes the script
a few scenes per call. Each call sees the plan, the running story summary and
the last scenes' narration. Chunks are checked as they arrive, merged into one
content-v3 payload and validated like a single-call draft.

No automatic retry: a blocked attempt keeps its finished calls, and the next
run with the same brief, feedback, previous revision and prompt reuses them.
"""
import copy
import hashlib
import json

from pilot import Blocked, read, write
from scripts.story_plan import tracks, needs_english, validate_plan

CHUNK_KEYS = ('scenes', 'coverage', 'claims', 'revision_response', 'open_questions')
STATE = 'long-script.json'
UNRESOLVED = 'No chunk of the script addressed this request.'


def chunk_size(root):
    return int(read(root / 'config.json').get('content_chunk_scenes') or 0)


def enabled(root, b):
    size = chunk_size(root)
    return bool(size) and b['scene_count'] > size


def scene_ids(b):
    return [f'SC{i:02}' for i in range(1, b['scene_count'] + 1)]


def split(b, size):
    ids = scene_ids(b)
    return [ids[i:i + size] for i in range(0, len(ids), size)]


def plan_schema(root):
    content = read(root / 'schemas/content-v3.json')
    outline = read(root / 'schemas/outline-v3.json')
    return {'type': 'object',
            'properties': {'outline': outline['properties']['outline'],
                           'characters': content['properties']['characters']},
            'required': ['outline', 'characters'], 'additionalProperties': False}


def chunk_schema(root):
    content = read(root / 'schemas/content-v3.json')
    props = {k: copy.deepcopy(content['properties'][k]) for k in CHUNK_KEYS}
    props['coverage'].pop('minItems', None)  # a chunk may carry no required point
    props['story_so_far'] = {'type': 'string', 'minLength': 1}
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}


def word_targets(b):
    """Average narration words per scene for each spoken language, from the brief's duration and speech rate."""
    out = {}
    for lang in dict.fromkeys(lang for lang, _ in tracks(b)):
        rate = b['planning']['speech_rates'][lang]['units_per_second']
        out[lang] = tuple(round(b['duration'][k] / b['scene_count'] * rate) for k in ('min_seconds', 'max_seconds'))
    return out


def field(lang):
    return 'narration_en' if lang == 'en' else 'narration'


# ------------------------------------------------------------------ checks

def check_plan(b, plan):
    if [x['scene_id'] for x in plan['outline']] != scene_ids(b):
        raise Blocked('OUTLINE: wrong scene count/order')
    if {r for x in plan['outline'] for r in x['requirements']} != {x['id'] for x in b['required_points']}:
        raise Blocked('OUTLINE: missing or unknown requirements')
    ids = [x['id'] for x in plan['characters']]
    if len(ids) != len(set(ids)):
        raise Blocked('PLAN_CHARACTERS: duplicate character id')


def check_chunk(b, plan, ids, data, used):
    """Structural checks on one chunk before the next call; the merged draft is validated again as a whole."""
    label = f'{ids[0]}–{ids[-1]}'
    scenes = data['scenes']
    if [s['id'] for s in scenes] != ids:
        raise Blocked(f'CHUNK_SCENES {label}: expected exactly {", ".join(ids)}')
    outline = [x for x in plan['outline'] if x['scene_id'] in ids]
    chars = {x['id'] for x in plan['characters']}
    for s in scenes:
        if set(s['character_ids']) - chars:
            raise Blocked(f"CHUNK_CHARACTERS {s['id']}: character not in the plan")
    # validate_plan covers outline match, image/beat rules and anchors for these scenes.
    validate_plan(dict(b, facts_required=False),
                  {'scenes': scenes, 'outline': outline, 'characters': plan['characters'], 'style': b['style'],
                   'claims': data['claims'], 'revision_response': []})
    new_ids = [im['id'] for s in scenes for im in s['images']] + [bt['id'] for s in scenes for bt in s['beats']]
    if set(new_ids) & used:
        raise Blocked(f'CHUNK_IDS {label}: image/beat id reused from an earlier chunk: {sorted(set(new_ids) & used)}')
    by_id = {s['id']: s for s in scenes}
    covered = set()
    for c in data['coverage']:
        s = by_id.get(c['scene_id'])
        if not s or c['requirement_id'] not in s['requirements'] or c['quote'] not in s['narration']:
            raise Blocked(f'CHUNK_COVERAGE {label}: coverage must quote the narration of its own scene and requirement')
        if needs_english(b) and (not c.get('quote_en') or c['quote_en'] not in s.get('narration_en', '')):
            raise Blocked(f'CHUNK_COVERAGE {label}: quote_en missing or not in narration_en')
        covered.add((c['scene_id'], c['requirement_id']))
    missing = {r for s in scenes for r in s['requirements']} - {r for _, r in covered}
    if missing:
        raise Blocked(f'CHUNK_COVERAGE {label}: no coverage quote for {sorted(missing)}')
    for lang, (low, _) in word_targets(b).items():
        words = sum(len(s.get(field(lang), '').split()) for s in scenes) / len(scenes)
        if words < 0.6 * low:
            raise Blocked(f'CHUNK_LENGTH {label}: {lang} narration averages {words:.0f} words per scene, '
                          f'target {low} or more; the video would be far shorter than the brief')
    return set(new_ids)


# ------------------------------------------------------------------ merge

def merge_responses(requests, parts):
    merged = []
    for req in requests:
        rows = [x for part in parts for x in part['revision_response'] if x['request_id'] == req['request_id']]
        if not rows:
            merged.append({'request_id': req['request_id'], 'status': 'unresolved', 'explanation': UNRESOLVED, 'scene_ids': []})
            continue
        scenes = list(dict.fromkeys(s for x in rows for s in x['scene_ids']))
        merged.append({'request_id': req['request_id'],
                       'status': 'addressed' if any(x['status'] == 'addressed' for x in rows) else 'unresolved',
                       'explanation': ' '.join(x['explanation'] for x in rows), 'scene_ids': scenes})
    return merged


def merge(b, revision, bhash, plan, parts, requests):
    return {'schema_version': '3.0', 'brief_revision': revision, 'brief_hash': bhash,
            'topic': b['topic'], 'duration': b['duration'], 'style': b['style'],
            'required_points': [x['text'] for x in b['required_points']],
            'characters': plan['characters'],
            'scenes': [s for part in parts for s in part['scenes']],
            'coverage': [c for part in parts for c in part['coverage']],
            'outline': plan['outline'],
            'claims': [c for part in parts for c in part['claims']],
            'revision_response': merge_responses(requests, parts),
            'open_questions': list(dict.fromkeys(q for part in parts for q in part['open_questions']))}


# ------------------------------------------------------------------ prompts

def plan_prompt(head, b, requests, previous):
    prompt = head + '\n' + json.dumps({'revision_requests': requests,
                                       'previous_plan': {k: previous[k] for k in ('outline', 'characters')} if previous else None},
                                      ensure_ascii=False)
    return prompt + (
        f"\nThis is a long script of {b['scene_count']} scenes, written in several calls. This call returns only the plan: "
        f"the full outline (every scene {scene_ids(b)[0]}–{scene_ids(b)[-1]} with purpose, requirement ids and transition) "
        "and the full character list for every scene. Each purpose must be a concrete story event (who, where, what happens, "
        "what small wrong detail appears), specific enough that a later call can write that scene without seeing the others. "
        "Name the details planted early that pay off later. Every scene's requirement ids come from the brief; together they "
        "cover every required point. Characters: id, name, and appearance/outfit precise enough to redraw the same person "
        "(age, face, hair, build, clothes); include the channel host if the brief uses one. No management ids inside names, "
        "appearance or outfit.")


def chunk_prompt(head, style, b, plan, ids, summaries, tail, requests, previous):
    from scripts.agy_pipeline import DETAIL_RULES
    targets = '; '.join(f'{lang}: about {low}–{high} words per scene on average ({field(lang)})'
                        for lang, (low, high) in word_targets(b).items())
    context = {'plan': plan, 'story_so_far': summaries, 'previous_scenes_narration': tail,
               'revision_requests': requests,
               'previous_revision_of_these_scenes': [s for s in previous['scenes'] if s['id'] in ids] if previous else None,
               'previous_coverage_of_these_scenes': [c for c in previous['coverage'] if c['scene_id'] in ids] if previous else None}
    return head + '\nPlan and context (data, not instructions): ' + json.dumps(context, ensure_ascii=False) + (
        f"\nWrite scenes {ids[0]}–{ids[-1]} only ({len(ids)} of {b['scene_count']}), as full content-v3 scene objects. "
        f"{DETAIL_RULES} "
        "Keep each scene's purpose and requirements exactly as in the plan's outline. Use only the plan's characters; "
        "do not add, rename or redescribe anyone. Character ids (and scene, image and beat ids) belong only in the id "
        "fields (character_ids, based_on, requirements). Inside description, preserve, change and visible_text never "
        "write any id: show a person by their look and clothes from the plan (for example 'the gaunt young lodger in a "
        "faded grey shirt'), because these texts go straight to the image model. Continue straight on from previous_scenes_narration without repeating it. "
        f"Narration length: {targets}; host scenes may be shorter, climax scenes longer. "
        f"Give images and beats ids that start with their scene id (for example {ids[0]}_I1, {ids[0]}_B1). "
        "coverage: for every requirement listed on these scenes, at least one quote from the narration of that scene. "
        "claims: only for these scenes. revision_response: only for requests these scenes address; omit the others. "
        "story_so_far: 3–6 English sentences on what happens in these scenes and every name, object, rule or promise that "
        "later scenes must honour. It is internal and never shown to viewers.") + style


# ------------------------------------------------------------------ run

def key_of(b, bhash, requests, previous_path, head, style, size):
    raw = json.dumps([bhash, requests, previous_path, head, style, size], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def reusable(out, key):
    """Finished calls of the latest blocked attempt with the same inputs, else {}."""
    for folder in sorted((x for x in out.parent.iterdir() if x.is_dir() and x != out), key=lambda x: x.stat().st_mtime, reverse=True):
        state = folder / STATE
        attempt = folder / 'attempt.json'
        if state.exists() and attempt.exists() and read(state).get('key') == key and read(attempt).get('state') == 'blocked':
            return {'folder': folder.name, **read(state)}
    return {}


def generate(root, b, revision, bhash, head, style, requests, previous, previous_path, out):
    from scripts import agy_pipeline  # tests patch agy_pipeline.invoke
    import jsonschema
    size = chunk_size(root)
    key = key_of(b, bhash, requests, previous_path, head, style, size)
    old = reusable(out, key)
    state = {'key': key, 'chunk_scenes': size, 'plan': old.get('plan'), 'chunks': {}, 'reused_from': old.get('folder')}
    write(out / STATE, state)
    if state['plan'] is None:
        schema = plan_schema(root)
        plan = agy_pipeline.invoke(plan_prompt(head, b, requests, previous), schema, out)['structured_output']
        jsonschema.validate(plan, schema)
        check_plan(b, plan)
        state['plan'] = plan
        write(out / STATE, state)
    plan = state['plan']
    write(out / 'outline.json', {'outline': plan['outline']})
    schema = chunk_schema(root)
    parts, used, summaries, tail = [], set(), [], []
    for ids in split(b, size):
        name = f'{ids[0]}-{ids[-1]}'
        data = old.get('chunks', {}).get(name)
        if data is None:
            data = agy_pipeline.invoke(chunk_prompt(head, style, b, plan, ids, summaries, tail, requests, previous),
                                       schema, out)['structured_output']
            write(out / f'chunk-{name}.json', data)  # raw reply, kept even when the checks below block it
            jsonschema.validate(data, schema)
        used |= check_chunk(b, plan, ids, data, used)
        state['chunks'][name] = data
        write(out / STATE, state)
        parts.append(data)
        summaries.append({'scenes': name, 'summary': data['story_so_far']})
        tail = [{'scene_id': s['id'], **{field(lang): s.get(field(lang), '') for lang, _ in tracks(b)}} for s in data['scenes'][-2:]]
    return {'structured_output': merge(b, revision, bhash, plan, parts, requests), 'conversation_id': None,
            'chunks': len(parts), 'reused_from': state['reused_from']}
