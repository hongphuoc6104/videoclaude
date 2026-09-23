#!/usr/bin/env python3
"""Chính sách kênh truyện kinh dị, cắm vào pilot qua config.

- check (brief_policies): truyện kinh dị phải rút từ kho horror/bank.py, không viết brief tay.
- lint (content_policies): chặn lời dẫn/hình khẳng định chuyện có thật, hướng dẫn nghi lễ
  làm theo được, máu me/tự hại, và địa danh có thật. Danh sách từ nằm trong
  horror/channel.json (blocked_terms) để sửa không cần đụng mã.

Bộ lọc từ khóa chỉ là lưới an toàn thô; duyệt nội dung vẫn phải đọc toàn bộ kịch bản.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from horror import bank

SIGNALS = ('kinh dị', 'truyện ma', 'rùng rợn', 'horror')
NEGATIONS = ('không phải', 'chẳng phải', 'không hề', 'không có', 'đừng', 'không', 'chẳng')
HINT = ('Truyện kinh dị phải rút từ kho: python3 horror/bank.py start {job}\n'
        '  (lệnh sẽ hỏi tỷ lệ khung, thời lượng, truyện và chế độ duyệt nếu chưa chọn)')


class PolicyError(Exception):
    pass


def is_horror(brief):
    text = ' '.join(str(brief.get(k, '')) for k in ('topic', 'goal', 'video_type')).lower()
    return brief.get('video_type') == 'horror_story' or any(s in text for s in SIGNALS)


def seed_of(brief):
    for line in brief.get('planning', {}).get('domain_requirements', []):
        if line.startswith(bank.SEED_TAG):
            return line[len(bank.SEED_TAG):].split(' (')[0].strip()
    return None


def check(root, job, brief):
    seed_id = seed_of(brief)
    if seed_id is None:
        if is_horror(brief):
            fail(HINT.format(job=job))
        return
    if seed_id not in {x['id'] for x in bank.seeds()}:
        fail(f'Hạt giống {seed_id} không có trong kho; dựng lại brief bằng: python3 horror/bank.py start {job}')
    record = bank.ledger()['seeds'].get(seed_id, {})
    if record.get('job') != job:
        holder = record.get('job')
        fail(f'Hạt giống {seed_id} chưa được giữ chỗ cho job {job}'
             + (f' (đang thuộc job {holder})' if holder else ''))
    if brief.get('aspect_ratio') not in ('16:9', '9:16'):
        fail('Truyện kinh dị chỉ đọc tiếng Việt: chọn khung 16:9 hoặc 9:16')


def negated(text, start):
    """Cụm từ bị phủ định ngay trước nó ('không phải chuyện có thật', 'không máu me')."""
    before = text[max(0, start - 14):start].lower().rstrip()
    return any(before.endswith(n) for n in NEGATIONS)


def find_terms(text, terms, case_sensitive):
    hits = []
    for term in terms:
        flags = 0 if case_sensitive else re.I
        for m in re.finditer(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, flags):
            if case_sensitive or not negated(text, m.start()):
                hits.append(term)
                break
    return hits


def lint(root, job, brief, content):
    """Lỗi chặn cho nội dung kinh dị; không áp dụng cho brief không sinh từ kho."""
    if seed_of(brief) is None:
        return
    from content_contract import ContractError, error
    terms = bank.channel().get('blocked_terms', {})
    errors = []
    rules = [('CLAIMS_TRUE', 'claims_true', False, 'Lời dẫn khẳng định truyện có thật',
              'Truyện luôn là hư cấu; bỏ câu khẳng định có thật.'),
             ('RITUAL', 'ritual', False, 'Lời dẫn giống hướng dẫn nghi lễ hoặc thách người xem làm theo',
              'Kể là nhân vật đã làm gì, không hướng dẫn hay rủ người xem làm theo.'),
             ('GORE', 'gore_self_harm', False, 'Có chi tiết máu me hoặc tự hại',
              'Gợi sợ bằng bóng tối/âm thanh; bỏ mô tả máu, vết thương, cách tự hại.'),
             ('REAL_PLACE', 'real_places', True, 'Có địa danh thật',
              'Đổi thành bối cảnh hư cấu tả chung, không tên tỉnh/thành/địa điểm có thật.')]
    for scene in content['scenes']:
        parts = [('narration', scene['narration'])]
        parts += [(f"images/{im['id']}", ' '.join([im['description'], im['preserve'], im['change']]
                                                  + [x['text'] for x in im['visible_text']]))
                  for im in scene['images']]
        for where, text in parts:
            for code, key, case, message, fix in rules:
                hits = find_terms(text, terms.get(key, []), case)
                if hits:
                    errors.append(error(code, f"{scene['id']}/{where}", f"{message}: {', '.join(hits)}", fix))
    if errors:
        raise ContractError(errors)


def fail(message):
    try:
        from pilot import Blocked
    except ImportError:
        raise PolicyError(message) from None
    raise Blocked(message)
