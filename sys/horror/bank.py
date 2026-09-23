#!/usr/bin/env python3
"""Kho hạt giống truyện kinh dị: chọn truyện, sinh brief, đánh dấu đã làm.

Một video = một hạt giống. Hạt giống chỉ là mô-típ có nguồn gốc rõ ràng (tác phẩm
đã hết bảo hộ, mô-típ dân gian hoặc tự viết); lời kể luôn viết mới.

Không có lựa chọn mặc định cho tỷ lệ khung, thời lượng, truyện và chế độ duyệt.
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
import contextlib
import fcntl
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
LEDGER = ROOT / 'ledger.json'
BRIEFS = ROOT / 'briefs'
SEED_TAG = 'Mã hạt giống truyện: '
AUTO = 'auto'
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
    return spec['choices']


def resolve_options(args, cfg, led, items, interactive):
    """Trả về dict lựa chọn đầy đủ; hỏi hoặc dừng khi thiếu. Không bao giờ tự điền."""
    given = {'aspect_ratio': args.ratio, 'length': args.length, 'seed': args.seed, 'mode': args.mode}
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
            {'id': 'R1', 'text': 'Người dẫn chuyện mở đầu bằng một câu móc gợi tò mò và nói rõ đây là truyện hư cấu'},
            {'id': 'R2', 'text': f"Dựng bối cảnh và nhân vật chính đời thường, gần gũi: {seed['premise']}. Bối cảnh: {seed['setting']}"},
            {'id': 'R3', 'text': f'Leo thang ít nhất ba điềm lạ, điềm sau căng hơn điềm trước: {dread}'},
            {'id': 'R4', 'text': f"Cao trào và cú lật: {seed['twist']}"},
            {'id': 'R5', 'text': 'Kết truyện để lại dư âm, không giải thích quá mức điều bí ẩn'},
            {'id': 'R6', 'text': 'Người dẫn chuyện khép lại, nhắc đây là truyện hư cấu và mời người xem kể cảm nhận; không kêu gọi thử làm theo bất cứ điều gì'},
        ],
        'language': cfg['language'],
        'tone': cfg['tone'],
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
            'pacing': cfg['pacing'],
            'domain_requirements': list(cfg['domain_requirements']) + [
                f"Người dẫn chuyện: {host['name']} — {host['appearance']}; {host['outfit']}",
                f"Thể loại: {seed['subgenre']}",
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
    if ratio == '16:9':
        brief['audio_language'] = 'vi'
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
                                'choices': {k: choice[k] for k in ('aspect_ratio', 'length', 'mode')}}
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
    freed = [k for k, v in led['seeds'].items() if v.get('job') == args.job and v.get('status') == 'reserved']
    if not freed:
        raise Stop(f'Job {args.job} không giữ chỗ truyện nào đang chờ')
    for key in freed:
        led['seeds'].pop(key)
    write_json(LEDGER, led)
    return {'released': freed, 'job': args.job}


COMMANDS = {'status': cmd_status, 'next': cmd_next, 'show': cmd_show, 'draw': cmd_draw,
            'start': cmd_start, 'mark': cmd_mark, 'release': cmd_release}
WRITERS = {'draw', 'start', 'mark', 'release'}


def parser():
    ap = argparse.ArgumentParser(description='Kho truyện kinh dị: chọn truyện và sinh brief')
    ap.add_argument('command', choices=sorted(COMMANDS))
    ap.add_argument('job', nargs='?', help='mã job của pilot (draw/start/mark/release)')
    ap.add_argument('--ratio', help='16:9 hoặc 9:16 (bắt buộc chọn, không có mặc định)')
    ap.add_argument('--length', help='10-15, 15-20 hoặc 20-30 (phút)')
    ap.add_argument('--seed', help='mã hạt giống, hoặc auto để lấy truyện kế tiếp')
    ap.add_argument('--mode', help='review hoặc auto')
    ap.add_argument('--no-input', action='store_true', help='không hỏi; thiếu lựa chọn thì trả needs_input')
    ap.add_argument('--count', type=int, default=10)
    ap.add_argument('--note', default='')
    ap.add_argument('--force', action='store_true')
    return ap


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command in ('draw', 'start', 'mark', 'release') and not args.job:
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
