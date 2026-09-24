#!/usr/bin/env python3
"""Kho hạt giống truyện kinh dị: chọn truyện, sinh brief, đánh dấu đã làm.

Một video = một hạt giống. Hạt giống chỉ là mô-típ có nguồn gốc rõ ràng (tác phẩm
đã hết bảo hộ, mô-típ dân gian hoặc tự viết); lời kể luôn viết mới.

Không có lựa chọn mặc định cho tỷ lệ khung, thời lượng, truyện, không khí, ngôi kể
và chế độ duyệt.
Thiếu lựa chọn nào thì:
  - chạy trong terminal: hỏi từng câu;
  - chạy bởi agent (không có terminal) hoặc --no-input: trả về needs_input với
    câu hỏi và các lựa chọn, thoát mã 3. Agent phải hỏi người dùng rồi chạy lại
    với đủ cờ; không tự chọn thay người dùng.

Dữ liệu:
  horror/seeds.json    hạt giống (người viết thêm/sửa)
  horror/channel.json  cấu hình kênh và danh sách câu hỏi
  horror/ledger.json   reserved/done theo id hạt giống; chỉ ghi qua lệnh
"""
import argparse
import copy
import contextlib
import fcntl
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
LEDGER = ROOT / 'ledger.json'
BRIEFS = ROOT / 'briefs'
SEED_TAG = 'Mã hạt giống truyện: '
MOOD_TAG = 'Không khí (mood): '
AUTO = 'auto'
SEED_MOOD = 'seed'
BASIS = {'public_domain': 'tác phẩm đã hết bảo hộ', 'folklore': 'mô-típ dân gian', 'original': 'truyện tự viết'}


class Stop(Exception):
    """Lỗi người dùng sửa được; in ra rồi thoát mã 2."""


class NeedInput(Exception):
    """Thiếu lựa chọn của người dùng; in câu hỏi rồi thoát mã 3."""

    def __init__(self, questions, job, given=None):
        self.questions = questions
        self.job = job
        self.given = given or []
        super().__init__('needs_input')

    def rerun(self):
        flags = self.given + [q['flag'] + ' <lựa chọn>' for q in self.questions]
        return f'python3 horror/bank.py start {self.job} ' + ' '.join(flags)


def read_json(path, default=None):
    if not path.exists():
        if default is None:
            raise Stop(f'Thiếu file {path}')
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_json_atomic(path, value):
    """Replace the ledger/lineage pointer without exposing a partial JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='.handoff-', delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def stamp():
    return time.strftime('%Y-%m-%d %H:%M:%S')


@contextlib.contextmanager
def ledger_lock():
    handle = open(ROOT / '.ledger.lock', 'w')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


def channel():
    return read_json(ROOT / 'channel.json')


def seeds():
    items = read_json(ROOT / 'seeds.json')['seeds']
    moods = channel()['moods']
    ids = [x['id'] for x in items]
    if len(ids) != len(set(ids)):
        raise Stop('seeds.json có id trùng')
    for x in items:
        if x.get('basis', {}).get('type') not in BASIS:
            raise Stop(f"{x['id']}: basis.type phải là một trong {sorted(BASIS)}")
        if x['basis']['type'] == 'public_domain' and not x['basis'].get('work'):
            raise Stop(f"{x['id']}: hạt giống từ tác phẩm phải ghi basis.work")
        if len(x.get('dread', [])) < 3:
            raise Stop(f"{x['id']}: cần ít nhất ba điềm lạ trong dread")
        if x.get('mood') not in moods:
            raise Stop(f"{x['id']}: mood phải là một trong {sorted(moods)}")
    return items


def ledger():
    return read_json(LEDGER, {'version': 1, 'seeds': {}})


def state_of(led, seed_id):
    return led['seeds'].get(seed_id, {}).get('status', 'todo')


def available(led, items):
    return [x for x in items if state_of(led, x['id']) == 'todo']


# ---------------------------------------------------------------- lựa chọn

def option_choices(key, cfg, led, items, limit=8):
    """Các lựa chọn của một câu hỏi. Hạt giống: truyện còn trống + tự lấy kế tiếp."""
    spec = cfg['options'][key]
    if spec.get('choices_from') == 'bank':
        pool = available(led, items)
        if not pool:
            raise Stop('Kho đã hết truyện chưa làm; thêm hạt giống vào horror/seeds.json')
        choices = [{'value': AUTO, 'label': f"{spec['auto_label']} ({pool[0]['id']} — {pool[0]['title']})"}]
        choices += [{'value': x['id'], 'label': f"{x['id']} — {x['title']} ({x['subgenre']})"} for x in pool[:limit]]
        return choices
    if spec.get('choices_from') == 'moods':
        return [{'value': SEED_MOOD, 'label': spec['seed_label']}] + [
            {'value': key, 'label': mood['label']} for key, mood in cfg['moods'].items()]
    return spec['choices']


def resolve_options(args, cfg, led, items, interactive):
    """Trả về dict lựa chọn đầy đủ; hỏi hoặc dừng khi thiếu. Không bao giờ tự điền."""
    given = {'aspect_ratio': args.ratio, 'length': args.length, 'seed': args.seed,
             'mood': args.mood, 'pov': args.pov, 'mode': args.mode}
    missing = []
    for key, value in given.items():
        choices = option_choices(key, cfg, led, items)
        values = [c['value'] for c in choices]
        if value is not None and key == 'seed' and value != AUTO:
            if value not in {x['id'] for x in items}:
                raise Stop(f'Không có hạt giống {value}; xem: python3 horror/bank.py next')
            if state_of(led, value) != 'todo':
                raise Stop(f'Hạt giống {value} đang {state_of(led, value)}; chọn truyện khác')
            continue
        if value is not None and value not in values:
            raise Stop(f"{cfg['options'][key]['flag']} phải là một trong: {', '.join(values)}")
        if value is None:
            missing.append((key, choices))
    if not missing:
        return given
    if not interactive:
        raise NeedInput([{'key': key, 'flag': cfg['options'][key]['flag'],
                          'question': cfg['options'][key]['question'], 'choices': choices}
                         for key, choices in missing], args.job,
                        [f"{cfg['options'][k]['flag']} {v}" for k, v in given.items() if v is not None])
    for key, choices in missing:
        given[key] = ask(cfg['options'][key]['question'], choices)
    return given


def ask(question, choices):
    sys.stderr.write(question + '\n')
    for number, c in enumerate(choices, 1):
        sys.stderr.write(f'  {number}. {c["label"]}\n')
    while True:
        sys.stderr.write('Chọn số: ')
        sys.stderr.flush()
        answer = sys.stdin.readline()
        if not answer:
            raise Stop('Đã dừng: chưa chọn ' + question)
        answer = answer.strip()
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1]['value']
        sys.stderr.write(f'Nhập một số từ 1 đến {len(choices)}.\n')


# ---------------------------------------------------------------- brief

def basis_line(seed):
    b = seed['basis']
    if b['type'] == 'public_domain':
        return (f"Nguồn cảm hứng: {b['work']} — {b['author']} ({b['year']}), {BASIS['public_domain']}. "
                f"Chỉ mượn mô-típ, kể lại hoàn toàn bằng lời mới. {b.get('note', '')}").strip()
    return f"Nguồn cảm hứng: {BASIS[b['type']]}. {b.get('note', '')}".strip()


def make_brief(seed, cfg, choice):
    length = next(c for c in cfg['options']['length']['choices'] if c['value'] == choice['length'])
    pov = next(c for c in cfg['options']['pov']['choices'] if c['value'] == choice['pov'])
    mood_key = seed['mood'] if choice['mood'] == SEED_MOOD else choice['mood']
    mood = cfg['moods'][mood_key]
    ratio = choice['aspect_ratio']
    host = cfg['host']
    dread = '; '.join(seed['dread'])
    brief = {
        'schema_version': '3.0',
        'topic': f"Truyện kinh dị hư cấu: {seed['title']}",
        'audience': cfg['audience'],
        'goal': f"Người nghe bị cuốn theo truyện \"{seed['title']}\" từ câu đầu tới câu cuối và thấy rợn người mà không cần máu me",
        'video_type': cfg['video_type'],
        'duration': {'min_seconds': length['min_seconds'], 'max_seconds': length['max_seconds']},
        'scene_count': length['scene_count'],
        'required_points': [
            {'id': 'R1', 'text': 'Người dẫn chuyện mở đầu bằng một câu móc gợi tò mò rồi nhường lời kể; không cần nói đây là truyện hư cấu (mô tả video ghi điều đó)'},
            {'id': 'R2', 'text': f"Dựng bối cảnh và nhân vật chính đời thường, gần gũi: {seed['premise']}. Bối cảnh: {seed['setting']}"},
            {'id': 'R3', 'text': f'Leo thang ít nhất ba điềm lạ, điềm sau căng hơn điềm trước: {dread}'},
            {'id': 'R4', 'text': f"Cao trào và cú lật: {seed['twist']}"},
            {'id': 'R5', 'text': 'Kết truyện để lại dư âm, không giải thích quá mức điều bí ẩn'},
            {'id': 'R6', 'text': 'Người dẫn chuyện khép lại và mời người xem kể cảm nhận; không cần nhắc đây là truyện hư cấu; không kêu gọi thử làm theo bất cứ điều gì'},
        ],
        'language': cfg['language'],
        'tone': f"{cfg['tone']}; {mood['tone']}",
        'style': cfg['style'],
        'aspect_ratio': ratio,
        'facts_required': False,
        'sources': [],
        'planning': {
            'success_criteria': [
                'Người nghe nhớ được ba điềm lạ và cú lật của truyện',
                'Không có chi tiết máu me, nghi lễ làm theo được hay địa danh có thật',
                'Xem hết video từ đầu đến cuối',
            ],
            'avoid': list(cfg['avoid']),
            'prior_knowledge': cfg['prior_knowledge'],
            'pacing': f"{cfg['pacing']}. {mood['pacing']}",
            'domain_requirements': list(cfg['domain_requirements']) + [
                f"Người dẫn chuyện: {host['name']} (mã nhân vật {host['id']}) — {host['appearance']}; {host['outfit']}",
                f"Thể loại: {seed['subgenre']}",
                f"{MOOD_TAG}{mood_key} — {mood['label']}",
                f"Ngôi kể: {pov['rule']}",
                basis_line(seed),
                f"{SEED_TAG}{seed['id']} (dùng để đánh dấu đã làm)",
            ],
            'assumptions': [
                'Tiêu chí ban đầu lấy từ hạt giống; cần kiểm tra khi duyệt kịch bản.',
                'Tốc độ giọng là ước lượng ban đầu, chưa phải số đo hiệu chỉnh.',
            ],
            'text_style': cfg['text_style'],
            'speech_rates': {lang: {'units_per_second': rate, 'uncertainty': 0.25, 'includes_pauses': False,
                                    'source': 'initial estimate; replace with measured voice rate'}
                             for lang, rate in [('vi', 3.6), ('en', 2.5)]},
        },
    }
    if cfg.get('visual_density'):
        # How often the picture must change (checked by story_plan.validate_plan on estimated scene length).
        brief['planning']['visual_density'] = {k: v for k, v in cfg['visual_density'].items() if k != 'note'}
    if cfg.get('script_director'):
        brief['script_director'] = {k: v for k, v in cfg['script_director'].items() if k != 'note'}
    if ratio == '16:9':
        brief['audio_language'] = 'vi'
    # CC0 bed follows the chosen mood; effects are placed by the script on the words that describe them.
    brief['sound'] = {'bed': mood['music'], 'sfx': True}
    # How the voice reads each scene and line (scripts/delivery.py); the mood scales speed and pauses.
    if cfg.get('delivery'):
        brief['delivery'] = {**{k: v for k, v in cfg['delivery'].items() if k != 'note'}, 'mood': mood_key}
        # Directed reading is slower and holds longer silences: 1169 words took 347 s on job thu-5p-h007g
        # (3.37 words/s including pauses) against 299 s undirected, so word targets must plan for it.
        brief['planning']['speech_rates']['vi'] = {'units_per_second': 3.3, 'uncertainty': 0.15, 'includes_pauses': True,
                                                   'source': 'measured: directed Phạm Tuyên narration, thu-5p-h007g, 2026-09-23'}
    return brief


# ---------------------------------------------------------------- lệnh

def cmd_status(args):
    led = ledger()
    items = seeds()
    counts = {'todo': 0, 'reserved': 0, 'done': 0}
    for x in items:
        counts[state_of(led, x['id'])] += 1
    return {'seeds': len(items), **counts,
            'reserved_jobs': sorted({v['job'] for v in led['seeds'].values() if v.get('status') == 'reserved'})}


def cmd_next(args):
    led = ledger()
    return {'available': [{'id': x['id'], 'title': x['title'], 'subgenre': x['subgenre'],
                           'basis': BASIS[x['basis']['type']]} for x in available(led, seeds())[:args.count]]}


def cmd_show(args):
    seed = next((x for x in seeds() if x['id'] == args.seed), None)
    if seed is None:
        raise Stop(f'Không có hạt giống {args.seed}')
    return dict(seed, status=state_of(ledger(), seed['id']))


def cmd_draw(args, interactive=False):
    """Hỏi đủ lựa chọn, giữ chỗ một hạt giống và ghi brief; chưa tạo job."""
    led = ledger()
    items = seeds()
    cfg = channel()
    if any(v.get('job') == args.job for v in led['seeds'].values()):
        raise Stop(f'Job {args.job} đã giữ chỗ một truyện; dùng mark hoặc release trước')
    choice = resolve_options(args, cfg, led, items, interactive)
    seed = available(led, items)[0] if choice['seed'] == AUTO else next(x for x in items if x['id'] == choice['seed'])
    path = BRIEFS / f'{args.job}.json'
    if path.exists():
        raise Stop(f'{path} đã có; xoá hoặc dùng mã job khác')
    write_json(path, make_brief(seed, cfg, choice))
    led['seeds'][seed['id']] = {'status': 'reserved', 'job': args.job, 'at': stamp(),
                                'brief': str(path.relative_to(REPO)),
                                'choices': {k: choice[k] for k in ('aspect_ratio', 'length', 'mood', 'pov', 'mode')}}
    write_json(LEDGER, led)
    return {'job': args.job, 'seed': seed['id'], 'title': seed['title'], 'brief': str(path), 'choices': choice}


def cmd_start(args, interactive=False):
    """draw + pilot new với đúng chế độ người dùng đã chọn."""
    drawn = cmd_draw(args, interactive)
    run = subprocess.run([sys.executable, 'pilot.py', 'new', args.job, '--brief', drawn['brief'],
                          '--mode', drawn['choices']['mode']], cwd=REPO, capture_output=True, text=True)
    sys.stderr.write(run.stderr)
    if run.returncode != 0:
        led = ledger()
        led['seeds'].pop(drawn['seed'], None)
        write_json(LEDGER, led)
        Path(drawn['brief']).unlink(missing_ok=True)
        raise Stop('pilot new thất bại, đã trả truyện về kho:\n' + (run.stdout or run.stderr).strip())
    return {**drawn, 'pilot': json.loads(run.stdout)}


def approved_video(job):
    sys.path.insert(0, str(REPO))
    from pilot import Pilot
    import workflow
    p = Pilot()
    try:
        workflow.published_videos(p, job)
        return True
    except Exception:
        return False
    finally:
        p.db.close()


def cmd_mark(args):
    led = ledger()
    targets = [k for k, v in led['seeds'].items() if v.get('job') == args.job]
    if not targets:
        raise Stop(f'Job {args.job} chưa giữ chỗ truyện nào')
    if any(led['seeds'][key].get('handoff', {}).get('state') == 'creating' for key in targets):
        raise Stop('Handoff đang chờ đối chiếu; không mark seed')
    if not args.force and not approved_video(args.job):
        raise Stop(f'Job {args.job} chưa có video được duyệt; duyệt xong mới mark, hoặc --force kèm --note')
    if args.force and not args.note.strip():
        raise Stop('--force cần --note ghi lý do')
    for seed_id in targets:
        led['seeds'][seed_id].update(status='done', at=stamp(), **({'note': args.note.strip()} if args.note.strip() else {}))
    write_json(LEDGER, led)
    return {'marked': targets, 'job': args.job}


def cmd_release(args):
    led = ledger()
    if any(v.get('job') == args.job and v.get('handoff', {}).get('state') == 'creating'
           for v in led['seeds'].values()):
        raise Stop('Handoff đang chờ đối chiếu; không release seed')
    freed = [k for k, v in led['seeds'].items() if v.get('job') == args.job and v.get('status') == 'reserved']
    if not freed:
        raise Stop(f'Job {args.job} không giữ chỗ truyện nào đang chờ')
    for key in freed:
        led['seeds'].pop(key)
    write_json(LEDGER, led)
    return {'released': freed, 'job': args.job}


def _video_decision_present(p, job):
    """Any saved video decision makes reuse unsafe, even if an old code gate is unavailable."""
    if any((REPO / 'runs' / job / 'reviews/video').glob('*/decision.json')):
        return True
    with p._db_lock:
        return p.db.execute(
            "SELECT 1 FROM events WHERE job=? AND module='video' "
            "AND event IN ('machine_approved','user_approved') LIMIT 1", (job,)).fetchone() is not None


def _saved_choices(record, brief, seed_id, mode):
    """Verify five explicit user selections; never reconstruct a new brief from defaults."""
    from horror.policy import seed_of
    choice = record.get('choices')
    keys = {'aspect_ratio', 'length', 'mood', 'pov', 'mode'}
    if not isinstance(choice, dict) or set(choice) != keys or any(not choice[k] for k in keys):
        raise Stop('Thiếu lựa chọn gốc của người dùng; không được đoán mặc định')
    cfg = channel()
    seed = next((x for x in seeds() if x['id'] == seed_id), None)
    lengths = {x['value']: x for x in cfg['options']['length']['choices']}
    povs = {x['value']: x for x in cfg['options']['pov']['choices']}
    if (seed is None or choice['length'] not in lengths or choice['pov'] not in povs
            or choice['mood'] not in {SEED_MOOD, *cfg['moods']}
            or choice['aspect_ratio'] not in ('16:9', '9:16')
            or choice['mode'] not in ('review', 'auto') or choice['mode'] != mode
            or choice['aspect_ratio'] != brief.get('aspect_ratio')
            or brief.get('duration') != {k: lengths[choice['length']][k]
                                         for k in ('min_seconds', 'max_seconds')}
            or brief.get('scene_count') != lengths[choice['length']]['scene_count']
            or seed_of(brief) != seed_id):
        raise Stop('Brief hiện tại không khớp lựa chọn đã lưu; không tự tạo lại')
    requirements = brief.get('planning', {}).get('domain_requirements', [])
    mood = seed['mood'] if choice['mood'] == SEED_MOOD else choice['mood']
    if (not any(x.startswith(MOOD_TAG + mood + ' — ') for x in requirements)
            or 'Ngôi kể: ' + povs[choice['pov']]['rule'] not in requirements):
        raise Stop('Mood/ngôi kể trong brief khác lựa chọn gốc')
    return choice


def _source_brief(p, old, seed_id, record):
    import workflow
    if not p.rows(old) or not p.job(old).is_dir():
        raise Stop('Job nguồn không tồn tại trong Pilot')
    mode = workflow.settings(p, old)['mode']  # read-only; no integrity refresh
    brief, revision, source_hash = p.brief(old)
    stored = (REPO / record.get('brief', '')).resolve()
    if (not stored.is_relative_to(BRIEFS.resolve()) or stored.name != old + '.json'
            or not stored.is_file() or read_json(stored) != brief):
        raise Stop('Brief nguồn không khớp bản đã giữ trong kho')
    choices = _saved_choices(record, brief, seed_id, mode)
    if _video_decision_present(p, old):
        raise Stop('Job nguồn đã có quyết định video; không chuyển hạt giống')
    return brief, revision, source_hash, choices


def _new_db_empty(p, new):
    if p.rows(new):
        return False
    for table in ('events', 'audio_edits', 'image_reviews', 'image_edits'):
        with p._db_lock:
            if p.db.execute(f'SELECT 1 FROM {table} WHERE job=? LIMIT 1', (new,)).fetchone():
                return False
    return True


def _remove_uncommitted(p, new, nonce, brief_hash):
    """Only a nonce-marked NEW tree with no committed DB identity may be removed."""
    from pilot import digest
    if not _new_db_empty(p, new):
        return False
    folder = p.job(new)
    if folder.exists():
        marker = folder / 'handoff-pending.json'
        if (not marker.is_file() or read_json(marker) != {'job': new, 'nonce': nonce}
                or folder.is_symlink()):
            return False
    brief_path = BRIEFS / f'{new}.json'
    if brief_path.exists() and (brief_path.is_symlink() or digest(brief_path) != brief_hash):
        return False
    if folder.exists():
        shutil.rmtree(folder)
    brief_path.unlink(missing_ok=True)
    return True


def _valid_created_job(p, old, new, seed_id, handoff):
    """Proof strong enough to finalize a pending handoff after a crash."""
    import workflow
    from pilot import hashobj, read
    folder = p.job(new)
    if not folder.is_dir() or folder.is_symlink():
        return False
    marker = folder / 'handoff-pending.json'
    lineage_file = folder / 'lineage.json'
    if not marker.is_file() or not lineage_file.is_file():
        return False
    if read(marker) != {'job': new, 'nonce': handoff['nonce']}:
        return False
    lineage = read(lineage_file)
    if (hashobj(lineage) != handoff['lineage_hash'] or lineage.get('source_job') != old
            or lineage.get('destination_job') != new or lineage.get('seed') != seed_id):
        return False
    try:
        p.integrity(new)
        if workflow.settings(p, new)['mode'] != lineage['choices']['mode']:
            return False
        if p.brief(new)[0] != p.brief(old)[0]:
            return False
        rows = p.rows(new)
        if rows['control']['state'] != 'approved' or rows['control']['revision'] != 1:
            return False
        for module in ('content', 'audio', 'images', 'render'):
            if rows[module]['state'] != 'pending' or rows[module]['revision'] != 0:
                return False
    except Exception:
        return False
    return True


def _final_record(pending, new):
    record = copy.deepcopy(pending)
    handoff = record['handoff']
    old = handoff['from']
    record['job'] = new
    record['at'] = stamp()
    record['brief'] = str((BRIEFS / f'{new}.json').relative_to(REPO))
    record['superseded_from'] = old
    record['handoff'] = {k: handoff[k] for k in ('from', 'to', 'nonce', 'lineage_hash')}
    record['handoff']['state'] = 'complete'
    return record


def cmd_continue(args):
    """Fail-closed two-phase handoff. Caller holds ledger_lock()."""
    from pilot import Pilot, locked, write, hashobj, digest
    import workflow
    old, new = args.job, args.successor
    if not old or not new or old == new:
        raise Stop('continue cần OLD_JOB và NEW_JOB khác nhau')
    with locked(REPO):
        p = Pilot(REPO)
        try:
            p.job(old);p.job(new)
            led = ledger()
            owned = [(seed, rec) for seed, rec in led['seeds'].items() if rec.get('job') == old]
            if len(owned) != 1 or owned[0][1].get('status') != 'reserved':
                raise Stop('OLD_JOB phải sở hữu đúng một hạt giống đang reserved, chưa done')
            seed_id, original = owned[0]
            if original.get('handoff', {}).get('state') == 'creating':
                raise Stop('Handoff đang chờ; dùng continue-reconcile OLD_JOB NEW_JOB')
            if (p.job(new).exists() or not _new_db_empty(p, new)
                    or (BRIEFS / f'{new}.json').exists()
                    or any(rec.get('job') == new for rec in led['seeds'].values())):
                raise Stop('NEW_JOB đã tồn tại hoặc đang giữ hạt giống khác')
            brief, revision, source_hash, choices = _source_brief(p, old, seed_id, original)
            nonce = secrets.token_hex(16)
            lineage = {'schema': 'horror-successor-1', 'source_job': old,
                       'destination_job': new, 'seed': seed_id, 'choices': choices,
                       'source_brief_revision': revision, 'source_brief_sha256': source_hash,
                       'at': stamp(), 'nonce': nonce}
            handoff = {'state': 'creating', 'from': old, 'to': new, 'nonce': nonce,
                       'lineage_hash': hashobj(lineage), 'source_brief_sha256': source_hash,
                       'previous_record': copy.deepcopy(original)}
            pending = copy.deepcopy(original)
            pending.update(job=new, handoff=handoff)
            led['seeds'][seed_id] = pending
            write_json_atomic(LEDGER, led)
            brief_path = BRIEFS / f'{new}.json'
            committed = False
            try:
                shutil.copyfile(p.path(old, f'briefs/{revision}.json'), brief_path)
                if digest(brief_path) != source_hash:
                    raise Stop('Bản brief chép sang job mới không khớp')
                p._handoff_nonce = nonce
                with p.creation_transaction(nonce):
                    workflow.new(p, new, brief, choices['mode'])
                    if p.brief(new)[0] != brief:
                        raise Stop('Pilot đã thay đổi brief khi tạo job kế nhiệm')
                    write(p.job(new) / 'lineage.json', lineage)
                    if not _valid_created_job(p, old, new, seed_id, handoff):
                        raise Stop('Job kế nhiệm chưa có control/workflow hợp lệ')
                committed = True
            except BaseException as exc:
                # An interrupted SQLite commit is uncertain until inspected.
                if _remove_uncommitted(p, new, nonce, source_hash):
                    led['seeds'][seed_id] = original
                    write_json_atomic(LEDGER, led)
                    raise Stop('Đã hoàn tác handoff; tạo job mới thất bại: ' + str(exc)) from exc
                raise Stop('HANDOFF_PENDING_RECONCILE: không chứng minh được NEW_JOB chưa tạo; '
                           'giữ cả hai job bị khóa. Chạy continue-reconcile OLD_JOB NEW_JOB') from exc
            finally:
                p._handoff_nonce = None
            if committed:
                led['seeds'][seed_id] = _final_record(pending, new)
                try:
                    write_json_atomic(LEDGER, led)
                except OSError as exc:
                    raise Stop('HANDOFF_PENDING_RECONCILE: job mới đã tạo nhưng ledger chưa chốt; '
                               'chạy continue-reconcile OLD_JOB NEW_JOB') from exc
            return {'continued_from': old, 'job': new, 'seed': seed_id,
                    'brief': str(brief_path), 'lineage': str(p.job(new) / 'lineage.json'),
                    'pilot': workflow.status(p, new)}
        finally:
            p.db.close()


def cmd_continue_reconcile(args):
    """Resolve a durable pending record only from verifiable DB/file state."""
    from pilot import Pilot, locked, digest
    old, new = args.job, args.successor
    if not old or not new:
        raise Stop('continue-reconcile cần OLD_JOB và NEW_JOB')
    with locked(REPO):
        p = Pilot(REPO)
        try:
            led = ledger()
            matches = [(seed, rec) for seed, rec in led['seeds'].items()
                       if rec.get('handoff', {}).get('state') == 'creating'
                       and rec['handoff'].get('from') == old
                       and rec['handoff'].get('to') == new]
            if len(matches) != 1:
                raise Stop('Không có đúng một handoff đang chờ cho cặp job này')
            seed_id, pending = matches[0]
            handoff = pending['handoff']
            if _video_decision_present(p, old):
                raise Stop('Job nguồn đã có quyết định video trong lúc chờ; cần rà thủ công')
            if _valid_created_job(p, old, new, seed_id, handoff):
                led['seeds'][seed_id] = _final_record(pending, new)
                write_json_atomic(LEDGER, led)
                return {'reconciled': 'finalized', 'source_job': old, 'job': new, 'seed': seed_id}
            source_hash = p.brief(old)[2]
            if source_hash != handoff['source_brief_sha256']:
                raise Stop('Brief nguồn đổi trong khi chờ; không tự hoàn tác')
            if _remove_uncommitted(p, new, handoff['nonce'], source_hash):
                led['seeds'][seed_id] = handoff['previous_record']
                write_json_atomic(LEDGER, led)
                return {'reconciled': 'rolled_back', 'source_job': old, 'job': new, 'seed': seed_id}
            raise Stop('HANDOFF_PENDING: DB hoặc file NEW_JOB còn trạng thái không chắc chắn; giữ khóa, cần rà thủ công')
        finally:
            p.db.close()


COMMANDS = {'status': cmd_status, 'next': cmd_next, 'show': cmd_show, 'draw': cmd_draw,
            'start': cmd_start, 'mark': cmd_mark, 'release': cmd_release,
            'continue': cmd_continue, 'continue-reconcile': cmd_continue_reconcile}
WRITERS = {'draw', 'start', 'mark', 'release', 'continue', 'continue-reconcile'}


def parser():
    ap = argparse.ArgumentParser(description='Kho truyện kinh dị: chọn truyện và sinh brief')
    ap.add_argument('command', choices=sorted(COMMANDS))
    ap.add_argument('job', nargs='?', help='mã job của pilot (draw/start/mark/release)')
    ap.add_argument('successor', nargs='?', help='NEW_JOB của continue/continue-reconcile')
    ap.add_argument('--ratio', help='16:9 hoặc 9:16 (bắt buộc chọn, không có mặc định)')
    ap.add_argument('--length', help='10-15, 15-20 hoặc 20-30 (phút)')
    ap.add_argument('--seed', help='mã hạt giống, hoặc auto để lấy truyện kế tiếp')
    ap.add_argument('--mood', help='seed (theo truyện), slow_burn, psychological, folk hoặc tense')
    ap.add_argument('--pov', help='third (ngôi thứ ba) hoặc first (ngôi thứ nhất)')
    ap.add_argument('--mode', help='review hoặc auto')
    ap.add_argument('--no-input', action='store_true', help='không hỏi; thiếu lựa chọn thì trả needs_input')
    ap.add_argument('--count', type=int, default=10)
    ap.add_argument('--note', default='')
    ap.add_argument('--force', action='store_true')
    return ap


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command in ('draw', 'start', 'mark', 'release', 'continue', 'continue-reconcile') and not args.job:
        raise Stop(f'Lệnh {args.command} cần mã job')
    if args.command == 'show' and not args.seed:
        raise Stop('show cần --seed')
    interactive = not args.no_input and sys.stdin.isatty()
    fn = COMMANDS[args.command]
    with ledger_lock() if args.command in WRITERS else contextlib.nullcontext():
        result = fn(args, interactive) if args.command in ('draw', 'start') else fn(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except NeedInput as ex:
        print(json.dumps({'needs_input': ex.questions,
                          'hint': 'Hỏi người dùng từng câu, không tự chọn thay; rồi chạy lại: ' + ex.rerun()},
                         ensure_ascii=False, indent=2))
        sys.exit(3)
    except Stop as ex:
        print(json.dumps({'blocked': str(ex)}, ensure_ascii=False, indent=2))
        sys.exit(2)
