"""Horror channel bank, required user choices and fiction-safety policy (no pilot job, no media)."""
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pilot import ROOT, Blocked
from content_contract import validate_brief, ContractError
from horror import bank, policy

FULL = ['--ratio', '16:9', '--length', '15-20', '--seed', 'auto', '--mode', 'review']


class HorrorBankTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for name in ('channel.json', 'seeds.json'):
            shutil.copy(ROOT / 'horror' / name, root / name)
        self.patches = [patch.object(bank, 'ROOT', root), patch.object(bank, 'LEDGER', root / 'ledger.json'),
                        patch.object(bank, 'BRIEFS', root / 'briefs'), patch.object(bank, 'REPO', root)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def draw(self, argv, interactive=False):
        args = bank.parser().parse_args(['draw', 'job-1'] + argv)
        return bank.cmd_draw(args, interactive)

    def test_nothing_chosen_asks_all_four_questions_without_defaults(self):
        with self.assertRaises(bank.NeedInput) as ctx:
            self.draw([])
        questions = {q['key']: q for q in ctx.exception.questions}
        self.assertEqual(list(questions), ['aspect_ratio', 'length', 'seed', 'mode'])
        self.assertEqual([c['value'] for c in questions['aspect_ratio']['choices']], ['16:9', '9:16'])
        self.assertEqual(questions['seed']['choices'][0]['value'], bank.AUTO)
        self.assertFalse((bank.LEDGER).exists(), 'nothing may be reserved before the user answers')

    def test_only_missing_choices_are_asked(self):
        with self.assertRaises(bank.NeedInput) as ctx:
            self.draw(['--ratio', '9:16', '--seed', 'H003'])
        self.assertEqual([q['key'] for q in ctx.exception.questions], ['length', 'mode'])
        self.assertEqual(ctx.exception.rerun(), 'python3 horror/bank.py start job-1 --ratio 9:16 --seed H003 --length <lựa chọn> --mode <lựa chọn>')

    def test_interactive_prompts_fill_missing_choices(self):
        answers = io.StringIO('2\n3\n1\n2\n')  # 9:16, 20-30, auto seed, auto mode
        with patch('sys.stdin', answers), patch('sys.stderr', io.StringIO()):
            result = self.draw([], interactive=True)
        self.assertEqual(result['choices'], {'aspect_ratio': '9:16', 'length': '20-30', 'seed': 'auto', 'mode': 'auto'})

    def test_invalid_choice_is_rejected(self):
        with self.assertRaisesRegex(bank.Stop, '--ratio'):
            self.draw(['--ratio', 'dual', '--length', '10-15', '--seed', 'auto', '--mode', 'review'])

    def test_landscape_brief_reads_vietnamese_and_is_valid(self):
        result = self.draw(FULL)
        brief = json.loads(Path(result['brief']).read_text())
        validate_brief(ROOT, brief)
        self.assertEqual((brief['aspect_ratio'], brief['audio_language']), ('16:9', 'vi'))
        self.assertEqual((brief['scene_count'], brief['duration']), (28, {'min_seconds': 900, 'max_seconds': 1200}))
        self.assertEqual(result['seed'], 'H001')
        self.assertEqual(bank.ledger()['seeds']['H001']['status'], 'reserved')
        policy.check(ROOT, 'job-1', brief)

    def test_portrait_brief_has_no_audio_language(self):
        brief = json.loads(Path(self.draw(['--ratio', '9:16', '--length', '10-15', '--seed', 'H005', '--mode', 'auto'])['brief']).read_text())
        validate_brief(ROOT, brief)
        self.assertNotIn('audio_language', brief)
        self.assertIn(bank.SEED_TAG + 'H005 (dùng để đánh dấu đã làm)', brief['planning']['domain_requirements'])

    def test_reserved_seed_cannot_be_taken_twice(self):
        self.draw(['--ratio', '9:16', '--length', '10-15', '--seed', 'H002', '--mode', 'review'])
        args = bank.parser().parse_args(['draw', 'job-2', '--ratio', '9:16', '--length', '10-15', '--seed', 'H002', '--mode', 'review'])
        with self.assertRaisesRegex(bank.Stop, 'reserved'):
            bank.cmd_draw(args)

    def test_policy_blocks_handwritten_or_foreign_briefs(self):
        brief = json.loads(Path(self.draw(FULL)['brief']).read_text())
        with self.assertRaisesRegex(Blocked, 'chưa được giữ chỗ cho job other'):
            policy.check(ROOT, 'other', brief)
        brief['planning']['domain_requirements'] = [x for x in brief['planning']['domain_requirements'] if not x.startswith(bank.SEED_TAG)]
        with self.assertRaisesRegex(Blocked, 'horror/bank.py start'):
            policy.check(ROOT, 'job-1', brief)

    def test_seed_bank_is_well_formed(self):
        items = bank.seeds()
        self.assertGreaterEqual(len(items), 10)
        for seed in items:
            if seed['basis']['type'] == 'public_domain':
                self.assertTrue(seed['basis']['work'] and seed['basis']['year'], seed['id'])


def content(narration, visible=()):
    return {'scenes': [{'id': 'SC01', 'narration': narration, 'images': [
        {'id': 'IMG1', 'description': 'Một hành lang tối', 'preserve': '', 'change': 'Thêm bóng người',
         'visible_text': [{'text': t, 'placement': 'giữa', 'object': 'biển'} for t in visible]}]}]}


class HorrorLintTests(unittest.TestCase):
    brief = {'planning': {'domain_requirements': [bank.SEED_TAG + 'H001 (dùng để đánh dấu đã làm)']}}

    def lint(self, *a):
        policy.lint(ROOT, 'job', self.brief, content(*a))

    def test_negated_phrases_pass(self):
        self.lint('Đây không phải chuyện có thật. Truyện không máu me, và đừng tự tử vì sợ hãi.')

    def test_claiming_truth_is_blocked(self):
        with self.assertRaisesRegex(ContractError, 'CLAIMS_TRUE'):
            self.lint('Đây là câu chuyện có thật mà tôi được nghe kể.')

    def test_gore_and_ritual_are_blocked(self):
        with self.assertRaisesRegex(ContractError, 'GORE'):
            self.lint('Anh thấy một vũng máu dưới chân cầu thang.')
        with self.assertRaisesRegex(ContractError, 'RITUAL'):
            self.lint('Đêm nay bạn hãy thử đứng trước gương và gọi tên cô ấy.')

    def test_real_places_blocked_in_narration_and_image_text(self):
        with self.assertRaisesRegex(ContractError, 'REAL_PLACE'):
            self.lint('Căn nhà ở ngay trung tâm Hà Nội.')
        with self.assertRaisesRegex(ContractError, 'SC01/images/IMG1'):
            self.lint('Một dãy trọ cuối hẻm.', ['Đà Lạt'])

    def test_non_bank_content_is_untouched(self):
        policy.lint(ROOT, 'job', {'planning': {'domain_requirements': []}}, content('Chuyện có thật ở Hà Nội.'))


if __name__ == '__main__':
    unittest.main()
