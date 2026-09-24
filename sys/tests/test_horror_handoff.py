"""A successor keeps a horror seed reserved through crashes and rollbacks."""
import json
import copy
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pilot import ROOT, Pilot, Blocked
import workflow
from horror import bank


class HorrorHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ('schemas', '.agents', 'renderer', 'examples', 'scripts', 'assets'):
            shutil.copytree(ROOT / name, self.root / name)
        shutil.copytree(ROOT / 'horror', self.root / 'horror',
                        ignore=shutil.ignore_patterns('ledger.json', 'briefs', '.ledger.lock'))
        for name in ('pilot.py', 'workflow.py', 'machine_review.py', 'image_pipeline.py',
                     'media_import.py', 'content_contract.py', 'prompt_templates.py',
                     'adapters.py', 'config.json', 'AGENTS.md', 'GEMINI.md'):
            shutil.copy(ROOT / name, self.root / name)
        self.patches = [patch.object(bank, 'ROOT', self.root / 'horror'),
                        patch.object(bank, 'LEDGER', self.root / 'horror/ledger.json'),
                        patch.object(bank, 'BRIEFS', self.root / 'horror/briefs'),
                        patch.object(bank, 'REPO', self.root)]
        for item in self.patches:
            item.start()
        args = bank.parser().parse_args([
            'draw', 'old', '--ratio', '16:9', '--length', '10-15', '--seed', 'H001',
            '--mood', 'seed', '--pov', 'third', '--mode', 'auto', '--no-input'])
        bank.cmd_draw(args)
        brief = json.loads((self.root / 'horror/briefs/old.json').read_text())
        pilot = Pilot(self.root)
        try:
            workflow.new(pilot, 'old', brief, 'auto')
        finally:
            pilot.db.close()

    def tearDown(self):
        for item in self.patches:
            item.stop()
        self.temp.cleanup()

    def command(self, name='continue'):
        return bank.parser().parse_args([name, 'old', 'new'])

    def test_successor_copies_exact_choices_and_blocks_old_job(self):
        prior = bank.ledger()['seeds']['H001']['choices']
        result = bank.cmd_continue(self.command())
        record = bank.ledger()['seeds']['H001']
        self.assertEqual(result['job'], record['job'])
        self.assertEqual(record['handoff']['state'], 'complete')
        self.assertEqual(record['superseded_from'], 'old')
        self.assertEqual(record['choices'], prior)
        self.assertEqual((self.root / 'runs/old/briefs/1.json').read_bytes(),
                         (self.root / 'horror/briefs/new.json').read_bytes())
        lineage = json.loads((self.root / 'runs/new/lineage.json').read_text())
        self.assertEqual((lineage['source_job'], lineage['destination_job'], lineage['seed']),
                         ('old', 'new', 'H001'))
        pilot = Pilot(self.root)
        try:
            with self.assertRaisesRegex(Blocked, 'HORROR_SEED_SUPERSEDED'):
                pilot.status('old')
            self.assertEqual(workflow.status(pilot, 'new')['stages'][0]['state'], 'pending')
        finally:
            pilot.db.close()

    def test_partial_creation_rolls_back_only_when_no_new_db_identity(self):
        original = workflow.new

        def fail_after_files(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('injected failure after Pilot creation')

        with patch.object(workflow, 'new', side_effect=fail_after_files):
            with self.assertRaisesRegex(bank.Stop, 'Đã hoàn tác handoff'):
                bank.cmd_continue(self.command())
        self.assertEqual(bank.ledger()['seeds']['H001']['job'], 'old')
        self.assertFalse((self.root / 'runs/new').exists())
        self.assertFalse((self.root / 'horror/briefs/new.json').exists())
        pilot = Pilot(self.root)
        try:
            self.assertEqual(pilot.rows('new'), {})
            self.assertEqual(workflow.status(pilot, 'old')['stages'][0]['state'], 'pending')
        finally:
            pilot.db.close()

    def test_crash_after_db_commit_keeps_pending_until_reconcile(self):
        original = bank.write_json_atomic
        writes = 0

        def fail_final(path, value):
            nonlocal writes
            writes += 1
            if writes == 2:
                raise OSError('injected failure after DB commit')
            return original(path, value)

        with patch.object(bank, 'write_json_atomic', side_effect=fail_final):
            with self.assertRaisesRegex(bank.Stop, 'HANDOFF_PENDING_RECONCILE'):
                bank.cmd_continue(self.command())
        self.assertEqual(bank.ledger()['seeds']['H001']['handoff']['state'], 'creating')
        pilot = Pilot(self.root)
        try:
            self.assertTrue(pilot.rows('new'))
            with self.assertRaisesRegex(Blocked, 'HORROR_SEED_SUPERSEDED'):
                pilot.status('old')
            with self.assertRaisesRegex(Blocked, 'HORROR_HANDOFF_PENDING'):
                pilot.status('new')
        finally:
            pilot.db.close()
        result = bank.cmd_continue_reconcile(self.command('continue-reconcile'))
        self.assertEqual(result['reconciled'], 'finalized')
        self.assertEqual(bank.ledger()['seeds']['H001']['job'], 'new')

    def test_existing_successor_or_video_decision_refuses_transfer(self):
        (self.root / 'runs/new').mkdir(parents=True)
        with self.assertRaisesRegex(bank.Stop, 'NEW_JOB đã tồn tại'):
            bank.cmd_continue(self.command())
        (self.root / 'runs/new').rmdir()
        decision = self.root / 'runs/old/reviews/video/1/decision.json'
        decision.parent.mkdir(parents=True)
        decision.write_text('{}')
        with self.assertRaisesRegex(bank.Stop, 'đã có quyết định video'):
            bank.cmd_continue(self.command())
        self.assertEqual(bank.ledger()['seeds']['H001']['job'], 'old')

    def test_pending_before_job_creation_reconciles_to_original_owner(self):
        from pilot import hashobj
        led = bank.ledger()
        original = copy.deepcopy(led['seeds']['H001'])
        pilot = Pilot(self.root)
        try:
            source_hash = pilot.brief('old')[2]
        finally:
            pilot.db.close()
        pending = copy.deepcopy(original)
        pending.update(job='new', handoff={
            'state': 'creating', 'from': 'old', 'to': 'new', 'nonce': 'test-nonce',
            'lineage_hash': hashobj({'test': True}),
            'source_brief_sha256': source_hash, 'previous_record': original})
        led['seeds']['H001'] = pending
        bank.write_json_atomic(bank.LEDGER, led)
        with self.assertRaisesRegex(bank.Stop, 'không release seed'):
            bank.cmd_release(bank.parser().parse_args(['release', 'new']))
        with self.assertRaisesRegex(bank.Stop, 'không mark seed'):
            bank.cmd_mark(bank.parser().parse_args(['mark', 'new', '--force', '--note', 'test']))
        result = bank.cmd_continue_reconcile(self.command('continue-reconcile'))
        self.assertEqual(result['reconciled'], 'rolled_back')
        self.assertEqual(bank.ledger()['seeds']['H001'], original)
        self.assertFalse((self.root / 'runs/new').exists())


if __name__ == '__main__':
    unittest.main()
