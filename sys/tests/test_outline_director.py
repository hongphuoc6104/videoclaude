"""The outline gate uses fake agy replies and never touches a production job."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pilot import Blocked, ROOT, read, write
from scripts import long_script, outline_director, opening_chunk_director


def historical(case):
    """Compact fixtures with exact bad SC purposes from the two interrupted H001 plans."""
    req = ['R1'] + ['R2'] * 3 + ['R3'] * 9 + ['R4'] * 4 + ['R5'] * 2 + ['R6']
    outline = [{'scene_id': f'SC{i:02}', 'purpose': f'Minh observes a new detail in scene {i}.',
                'requirements': [req[i - 1]], 'transition': 'The next event follows.'}
               for i in range(1, 21)]
    if case == 'a':
        replacements = {
            1: 'Người dẫn chuyện mở bằng câu hỏi về đồ vật lạ trong căn phòng trọ giá rẻ bất thường.',
            11: "Ông Bảy ấp úng chối quanh rằng chắc do chuột chạy trên mái tôn. Khi quay đi, ông Bảy lẩm bẩm 'lại ba tiếng... vẫn chưa chịu đi sao' mà Minh nghe thấy.",
            16: 'Tiếng gõ thứ tư không còn là tiếng gõ cửa thông thường, mà là tiếng điểm danh đếm số người hiện diện trong căn phòng.',
            17: 'Ba chiếc đinh sợi chỉ đỏ và ba người thuê trọ trước đây chưa từng rời đi, mà đã bị hút lại phía sau tấm gương.',
            20: "Người dẫn chuyện hỏi: 'Nếu đêm nay bạn nghe thấy tiếng gõ lúc hai giờ sáng... bạn có dám kiểm tra mặt sau tấm gương của mình không?'",
        }
    else:
        replacements = {
            1: 'Người dẫn chuyện hỏi điều gì sẽ xảy ra nếu tiếng gõ đêm khuya không đến từ cánh cửa mà từ phía sau mặt gương?',
            11: 'Minh nhìn thấy ở góc dưới mặt sau tấm gương một tờ giấy vàng xỉn và các ký tự mực đỏ đã phai mờ.',
            16: "Tiếng gõ thứ tư này không nằm sau tấm gương nữa, mà vang lên sát rạt ngay sau lưng Minh, ngay phía sau vành tai cậu.",
            17: 'Ba tiếng gõ là tiếng điểm danh số người từng ở trong căn phòng trước đó; tiếng thứ tư đếm thêm Minh, người thứ tư có mặt trong phòng.',
            20: 'Người dẫn chuyện mời khán giả chia sẻ cảm nhận về câu chuyện dưới phần bình luận.',
        }
    for index, purpose in replacements.items():
        outline[index - 1]['purpose'] = purpose
    return {'outline': outline, 'characters': [
        {'id': 'CH01', 'name': 'Người dẫn chuyện', 'appearance': 'Đầu tròn trắng, mắt đen.', 'outfit': 'Áo xanh nhạt.'},
        {'id': 'CH02', 'name': 'Minh', 'appearance': 'Sinh viên dáng gầy, tóc đen.', 'outfit': 'Áo sơ mi xám.'},
    ]}


def grade(plan, failures=(), bad_quote=False):
    rows = plan['outline']
    positions = {
        'hook_without_spoiler': 0,
        'genuine_false_relief': 10,
        'seed_twist_and_payoff': 15,
        'continuity_pov_and_claims': 16,
        'host_closing_no_dare': -1,
    }
    criteria = {}
    requests = []
    for key, index in positions.items():
        scene = rows[index]
        quote = scene['purpose'][:60]
        if bad_quote and key == 'hook_without_spoiler':
            quote = 'This sentence is not in the purpose.'
        criteria[key] = {'met': key not in failures,
                         'evidence': [{'scene_id': scene['scene_id'], 'quote': quote}],
                         'notes': f'Check the exact event described in {scene["scene_id"]}.'}
        if key in failures:
            requests.append({'criterion': key, 'scene_ids': [scene['scene_id']],
                             'instruction': f'Rework {scene["scene_id"]} to satisfy {key} while keeping the seed event.'})
    return {'pass': True, 'criteria': criteria, 'revision_requests': requests}


class OutlineDirectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.brief = read(ROOT / 'examples/story-v3/brief.json')
        self.brief.update(video_type='horror_story', scene_count=20,
                          script_director={'enabled': True, 'max_rewrites': 2,
                                           'min_each': 1, 'min_total': 10})
        self.brief['required_points'] = [
            {'id': f'R{i}', 'text': text} for i, text in enumerate((
                'Host opens without spoiling the source.',
                'A student rents a cheap room from an evasive owner.',
                'Three knocks at two; empty hall; reversed mirror; faded yellow paper.',
                'The knocks come from behind the mirror; the fourth counts one more person in the room.',
                'Leave an uneasy aftermath without explaining everything.',
                'Host invites comments without daring the viewer to try anything.'), 1)]
        self.plan_a = historical('a')
        self.plan_b = historical('b')

    def output(self, name='new'):
        out = self.base / 'agent-attempts' / name
        out.mkdir(parents=True)
        return out

    def generate(self, out, fake, brief=None):
        with patch('scripts.agy_pipeline.invoke', side_effect=fake):
            return long_script.generate(ROOT, brief or self.brief, 1, 'test-hash', 'Write story.',
                                        'Style.', [], None, None, out)

    def test_historical_outlines_fail_before_any_chunk_and_keep_evidence(self):
        cases = (
            (self.plan_a, ('genuine_false_relief', 'seed_twist_and_payoff',
                           'continuity_pov_and_claims', 'host_closing_no_dare')),
            (self.plan_b, ('hook_without_spoiler', 'genuine_false_relief',
                           'seed_twist_and_payoff', 'continuity_pov_and_claims')),
        )
        for index, (plan, failures) in enumerate(cases):
            with self.subTest(index=index):
                out = self.output(f'case-{index}')
                calls = []

                def fake(prompt, schema, workspace, **kwargs):
                    calls.append(prompt)
                    if 'criteria' in schema['properties']:
                        return {'structured_output': grade(plan, failures)}
                    if 'outline' in schema['properties']:
                        return {'structured_output': copy.deepcopy(plan)}
                    self.fail('No scene chunk may be written for a rejected outline')

                with self.assertRaisesRegex(Blocked, 'OUTLINE_DIRECTOR_NEEDS_ATTENTION'):
                    self.generate(out, fake)
                self.assertEqual(len(calls), 6)  # plan + critique, then two bounded replans
                self.assertIn('OUTLINE DIRECTOR REPLAN', calls[2])
                self.assertEqual(read(out / 'outline-critique-round-0.json')['failed_criteria'], list(failures))
                self.assertFalse(read(out / 'outline-critique-round-0.json')['pass'], 'model pass flag is ignored')
                self.assertTrue((out / 'outline-candidate-round-2.json').exists())
                self.assertFalse((out / 'outline.json').exists())
                self.assertEqual(read(out / 'long-script.json')['plan'], None)
                self.assertEqual(list(out.glob('chunk-*.json')), [])

    def test_false_or_misplaced_evidence_blocks_before_chunk(self):
        for invalid in ('quote', 'section'):
            with self.subTest(invalid=invalid):
                out = self.output(invalid)
                response = grade(self.plan_b, bad_quote=invalid == 'quote')
                if invalid == 'section':
                    response['criteria']['host_closing_no_dare']['evidence'] = [
                        {'scene_id': 'SC01', 'quote': self.plan_b['outline'][0]['purpose'][:60]}]

                def fake(prompt, schema, workspace, **kwargs):
                    if 'criteria' in schema['properties']:
                        return {'structured_output': response}
                    if 'outline' in schema['properties']:
                        return {'structured_output': copy.deepcopy(self.plan_b)}
                    self.fail('No chunk expected')

                with self.assertRaisesRegex(Blocked, 'OUTLINE_DIRECTOR_PROTOCOL'):
                    self.generate(out, fake)
                self.assertTrue((out / 'outline-critique-raw-round-0.json').exists())
                self.assertFalse((out / 'outline.json').exists())

    def test_reused_plan_is_critically_checked_before_any_chunk(self):
        out = self.output('latest')
        prior = self.output('prior')
        key = long_script.key_of(self.brief, 'test-hash', [], None, 'Write story.', 'Style.',
                                 long_script.chunk_size(ROOT, self.brief))
        write(prior / 'attempt.json', {'state': 'blocked'})
        write(prior / 'long-script.json', {'key': key, 'plan': self.plan_b, 'chunks': {}})
        calls = []

        def fake(prompt, schema, workspace, **kwargs):
            calls.append(prompt)
            if 'criteria' in schema['properties']:
                return {'structured_output': grade(self.plan_b)}
            if 'outline' in schema['properties']:
                self.fail('A finished plan should be reused')
            raise Blocked('TEST_CHUNK_REACHED')

        with self.assertRaisesRegex(Blocked, 'TEST_CHUNK_REACHED'):
            self.generate(out, fake)
        self.assertEqual(len(calls), 2)  # critique, then first missing chunk
        self.assertTrue(read(out / 'outline-critique-round-0.json')['pass'])
        self.assertEqual(read(out / 'long-script.json')['plan'], self.plan_b)

    def test_verified_pass_reuses_plan_and_finished_chunk_without_new_critique(self):
        out = self.output('latest-passed')
        prior = self.output('prior-passed')
        key = long_script.key_of(self.brief, 'test-hash', [], None, 'Write story.', 'Style.',
                                 long_script.chunk_size(ROOT, self.brief))
        saved = {'pass': True, 'outline_sha256': outline_director.hash_plan(self.plan_b)}
        write(prior / 'attempt.json', {'state': 'blocked'})
        first = {'saved': True, 'story_so_far': 'Minh enters the room.',
                 'scenes': [{'id': 'SC01', 'narration': 'Opening.'},
                            {'id': 'SC02', 'narration': 'Arrival.'}]}
        write(prior / 'long-script.json', {'key': key, 'plan': self.plan_b,
                                           'outline_director_pass': saved,
                                           'opening_chunk_pass': {
                                               'pass': True,
                                               'input_sha256': opening_chunk_director.hash_input(
                                                   self.brief, self.plan_b, first)},
                                           'chunks': {'SC01-SC02': first}})
        calls = []

        def fake(prompt, schema, workspace, **kwargs):
            calls.append(prompt)
            if 'criteria' in schema['properties'] or 'outline' in schema['properties']:
                self.fail('A verified pass must be reused without a new outline call')
            raise Blocked('TEST_NEXT_CHUNK')

        with patch.object(long_script, 'check_chunk', return_value=set()) as checked:
            with self.assertRaisesRegex(Blocked, 'TEST_NEXT_CHUNK'):
                self.generate(out, fake)
        self.assertEqual(checked.call_count, 1)
        self.assertTrue(checked.call_args.args[3]['saved'])
        self.assertEqual(len(calls), 1)
        self.assertIn('Write scenes SC03–SC04', calls[0])
        self.assertEqual(read(out / 'long-script.json')['outline_director_pass'], saved)

    def test_mismatched_pass_hash_is_not_trusted(self):
        out = self.output('latest-wrong-hash')
        prior = self.output('prior-wrong-hash')
        key = long_script.key_of(self.brief, 'test-hash', [], None, 'Write story.', 'Style.',
                                 long_script.chunk_size(ROOT, self.brief))
        write(prior / 'attempt.json', {'state': 'blocked'})
        write(prior / 'long-script.json', {'key': key, 'plan': self.plan_b,
                                           'outline_director_pass': {'pass': True, 'outline_sha256': 'wrong'},
                                           'chunks': {}})
        calls = []

        def fake(prompt, schema, workspace, **kwargs):
            calls.append(prompt)
            if 'criteria' in schema['properties']:
                return {'structured_output': grade(self.plan_b)}
            raise Blocked('TEST_CHUNK_REACHED')

        with self.assertRaisesRegex(Blocked, 'TEST_CHUNK_REACHED'):
            self.generate(out, fake)
        self.assertEqual(len(calls), 2)
        self.assertTrue(read(out / 'outline-critique-round-0.json')['pass'])

    def test_successful_replan_discards_chunks_from_old_outline(self):
        out = self.output('replanned')
        prior = self.output('old-outline')
        key = long_script.key_of(self.brief, 'test-hash', [], None, 'Write story.', 'Style.',
                                 long_script.chunk_size(ROOT, self.brief))
        write(prior / 'attempt.json', {'state': 'blocked'})
        write(prior / 'long-script.json', {'key': key, 'plan': self.plan_b,
                                           'chunks': {'SC01-SC02': {'stale': True}}})
        revised = copy.deepcopy(self.plan_b)
        revised['outline'][0]['purpose'] = 'Người dẫn chuyện hỏi về ba tiếng gõ lúc hai giờ sáng khi hành lang hoàn toàn vắng.'
        calls = []
        critique_round = 0

        def fake(prompt, schema, workspace, **kwargs):
            nonlocal critique_round
            calls.append(prompt)
            if 'criteria' in schema['properties']:
                critique_round += 1
                return {'structured_output': grade(self.plan_b, ('hook_without_spoiler',))
                        if critique_round == 1 else grade(revised)}
            if 'outline' in schema['properties']:
                return {'structured_output': copy.deepcopy(revised)}
            raise Blocked('TEST_FRESH_FIRST_CHUNK')

        with self.assertRaisesRegex(Blocked, 'TEST_FRESH_FIRST_CHUNK'):
            self.generate(out, fake)
        self.assertEqual(len(calls), 4)  # critique, replan, critique, first fresh chunk
        self.assertIn('Write scenes SC01–SC02', calls[-1])
        self.assertEqual(read(out / 'long-script.json')['plan'], revised)
        self.assertNotEqual(read(out / 'outline-critique-round-0.json')['outline_sha256'],
                            read(out / 'outline-critique-round-1.json')['outline_sha256'])

    def test_non_horror_does_not_call_outline_critic(self):
        brief = dict(self.brief, video_type='other')
        self.assertFalse(outline_director.enabled(brief))
        self.assertFalse(outline_director.enabled(dict(self.brief, script_director={'enabled': False})))


if __name__ == '__main__':
    unittest.main()
