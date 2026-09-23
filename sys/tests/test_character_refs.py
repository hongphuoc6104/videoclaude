"""Who each Flow image is drawn from: the channel host (mascot), a story character's own reference, or nobody.
Flow is faked; nothing is submitted."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

import adapters
import b2_bridge
from pilot import ROOT, Blocked, read, write
import test_images_v2 as images_tests

HOST = read(ROOT / 'config.json')['canonical_character']


class AdapterReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        mascot = self.root / HOST['reference_path']
        mascot.parent.mkdir(parents=True)
        Image.new('RGB', (200, 400), 'white').save(mascot)
        write(self.root / 'config.json', {'flow_require_ui_evidence': False, 'canonical_character': HOST})
        self.p = SimpleNamespace(root=self.root)
        self.out = self.root / 'attempt/download'
        self.out.mkdir(parents=True)
        self.addCleanup(self.tmp.cleanup)

    def reference(self, name, media, canonical=False):
        path = self.root / 'refs' / name / 'result.png'
        path.parent.mkdir(parents=True)
        Image.new('RGB', (90, 160), 'gray').save(path)
        write(path.with_suffix('.json'), {'type': 'character-reference', 'forgeId': media, 'canonical': canonical})
        return str(path)

    def scene(self, *extra):
        calls = []
        def fake(**kwargs):
            calls.append(kwargs)
            image = self.out / 'result.jpg'
            Image.new('RGB', (90, 160)).save(image)
            return {'path': str(image), 'forge_id': 'new-media'}
        with patch.object(b2_bridge, 'generate_b2_image', side_effect=fake):
            adapters.gflow(self.p, 'image', '--id', 'x', '--prompt', 'A dark corridor', '--ratio', '9:16', '--out', str(self.out), *extra)
        return calls[0] if calls else None, read(self.out.parent / 'ui-proof.json')

    def test_story_character_uses_its_own_reference(self):
        ref = self.reference('lan', 'lan-media')
        call, proof = self.scene('--character-ref', ref, '--character', 'job-lan-1')
        self.assertEqual((call['char_ref_path'], call['char_media_id'], call['canonical'], call['no_character']),
                         (ref, 'lan-media', False, False))
        self.assertEqual((proof['characters'], proof['attached_character']), (['job-lan-1'], 'job-lan-1'))

    def test_host_scene_uses_the_canonical_mascot(self):
        ref = self.reference('host', HOST['media_id'], canonical=True)
        call, _ = self.scene('--character-ref', ref, '--character', 'job-host-1')
        self.assertEqual((call['char_ref_path'], call['char_media_id'], call['canonical']),
                         (str(self.root / HOST['reference_path']), HOST['media_id'], True))

    def test_scene_without_people_is_text_only(self):
        call, proof = self.scene('--no-character')
        self.assertEqual((call['char_ref_path'], call['char_media_id'], call['no_character']), (None, None, True))
        self.assertIsNone(proof['attached_character'])

    def test_unresolved_characters_never_fall_back_to_the_mascot(self):
        with self.assertRaisesRegex(Blocked, 'CHARACTER_REFERENCE_UNRESOLVED'):
            self.scene('--character', 'job-lan-1')
        with self.assertRaisesRegex(Blocked, 'CHARACTER_REFERENCE_UNRESOLVED'):
            self.scene()
        bare = self.root / 'bare.png'
        Image.new('RGB', (9, 16)).save(bare)
        with self.assertRaisesRegex(Blocked, 'no Flow media id'):
            self.scene('--character-ref', str(bare), '--character', 'job-lan-1')

    def test_host_reference_is_the_mascot_image_without_flow(self):
        call, proof = self.scene('--canonical')
        self.assertIsNone(call)
        self.assertEqual(read(self.out / 'result.json')['forgeId'], HOST['media_id'])
        self.assertEqual(proof['tool'], 'canonical-mascot')

    def test_story_registration_keeps_the_reference_and_its_media_id(self):
        ref = self.root / 'REF-lan.png'
        Image.new('RGB', (90, 160), 'red').save(ref)
        with patch.object(b2_bridge, 'generate_b2_image') as flow:
            adapters.gflow(self.p, 'character', 'create', '--name', 'job-lan-1', '--prompt', 'p', '--image', str(ref),
                           '--media-id', 'lan-media', '--out', str(self.out))
        flow.assert_not_called()
        self.assertEqual((self.out / 'result.png').read_bytes(), ref.read_bytes())
        self.assertEqual(read(self.out / 'result.json'), {'type': 'character-reference', 'name': 'job-lan-1',
                                                          'forgeId': 'lan-media', 'canonical': False})
        with self.assertRaisesRegex(Blocked, 'media-id'):
            adapters.gflow(self.p, 'character', 'create', '--name', 'job-lan-1', '--image', str(ref), '--out', str(self.out))

    def test_batch_specs_follow_each_job(self):
        ref = self.reference('lan', 'lan-media')
        jobs = [{'id': 'a', 'prompt': 'Lan at the door', 'ratio': '9:16', 'character': ['job-lan-1'], 'character_refs': [ref]},
                {'id': 'b', 'prompt': 'An empty road', 'ratio': '9:16', 'character': [], 'character_refs': []}]
        write(self.root / 'jobs.json', {'jobs': jobs})
        seen = []
        def fake(specs, timeout):
            seen.extend(specs)
            out = []
            for s in specs:
                image = Path(s['outDir']) / 'r.png'
                image.parent.mkdir(parents=True, exist_ok=True)
                Image.new('RGB', (9, 16)).save(image)
                out.append({'path': str(image), 'media_id': 'm-' + s['testCase'], 'screenshot': None})
            return out
        with patch.object(b2_bridge, 'generate_b2_batch', side_effect=fake):
            adapters.gflow(self.p, 'batch', str(self.root / 'jobs.json'), '--out', str(self.root / 'batch'))
        self.assertEqual((seen[0]['characterRefPath'], seen[0]['charMediaId'], seen[0]['noCharacter']), (ref, 'lan-media', False))
        self.assertEqual((seen[1]['characterRefPath'], seen[1]['noCharacter']), (None, True))
        self.assertNotIn('Stickman', seen[0]['prompt'] + seen[1]['prompt'])


class QueueSpecTests(unittest.TestCase):
    def test_stickman_guidance_only_for_the_host(self):
        host = b2_bridge.queue_spec('a', 'Host waves', '9:16', '/tmp/x', char_ref_path='/tmp/m.png', char_media_id='m', canonical=True)
        story = b2_bridge.queue_spec('b', 'Lan waits', '9:16', '/tmp/x', char_ref_path='/tmp/l.png', char_media_id='l')
        empty = b2_bridge.queue_spec('c', 'A road', '9:16', '/tmp/x', no_character=True)
        self.assertIn('Stickman CH01', host['prompt'])
        self.assertEqual(story['prompt'], 'Lan waits')
        self.assertEqual(empty['prompt'], 'A road')
        self.assertEqual([x['styleNote'] for x in (host, story, empty)],
                         [b2_bridge.STYLE_NOTES[k] for k in ('canonical', 'story', 'none')])
        with self.assertRaisesRegex(Blocked, 'CHARACTER_REFERENCE_REQUIRED'):
            b2_bridge.queue_spec('d', 'x', '9:16', '/tmp/x')
        with self.assertRaisesRegex(Blocked, 'CHARACTER_REFERENCE_REQUIRED'):
            b2_bridge.queue_spec('e', 'x', '9:16', '/tmp/x', char_ref_path='/tmp/l.png', char_media_id='l', no_character=True)


class PipelineReferenceArgsTests(unittest.TestCase):
    setUp = images_tests.ImagesV2Tests.setUp
    tearDown = images_tests.ImagesV2Tests.tearDown
    preflight = images_tests.ImagesV2Tests.preflight
    provider = images_tests.ImagesV2Tests.provider
    run_stage = images_tests.ImagesV2Tests.run_stage
    approve = images_tests.ImagesV2Tests.approve
    references = images_tests.ImagesV2Tests.references
    finish = images_tests.ImagesV2Tests.finish

    def flags(self, host=None):
        # config.json is protected once a job exists, so the host id is patched instead of rewritten.
        with patch('image_pipeline.canonical_ids', return_value={host or HOST['id']}):
            self.finish()
        refs = [c for c in self.calls if c[0] == 'image' and '--character' not in c]
        regs = [c for c in self.calls if c[0] == 'character']
        scenes = [c for c in self.calls if c[0] == 'image' and '--character' in c]
        return refs, regs, scenes

    def test_story_characters_get_generated_references_not_the_mascot(self):
        refs, regs, scenes = self.flags()
        self.assertEqual(len(refs), 2)
        self.assertTrue(all('--no-character' in c and '--canonical' not in c for c in refs))
        self.assertEqual(len(regs), 2)
        for c in regs:
            self.assertTrue(c[c.index('--media-id') + 1].startswith('TEST-MEDIA-'))
        for c in scenes:
            names = list(c[c.index('--character') + 1:])
            files = list(c[c.index('--character-ref') + 1:c.index('--character')])
            self.assertEqual(len(files), len(names))
            self.assertTrue(all(Path(f).is_file() for f in files))

    def test_host_reference_and_registration_are_canonical(self):
        refs, regs, _ = self.flags(host='CH01')
        self.assertEqual(['--canonical' in c for c in refs], [True, False])
        self.assertEqual(['--canonical' in c for c in regs], [True, False])
        self.assertNotIn('--media-id', regs[0])



class SessionCheckTests(unittest.TestCase):
    """Anything that fails before a queue command is sent cannot have reached Flow."""

    def test_session_check_failures_are_not_submitted(self):
        failures = [Blocked('B-2 Illustrator session command timed out after 5.0s: status'),
                    b2_bridge.not_submitted('socket not found')]
        for error in failures:
            with self.subTest(error=str(error)), patch('b2_bridge.send_raw_command', side_effect=error):
                with self.assertRaises(Blocked) as ctx:
                    b2_bridge.ensure_connected()
                self.assertIs(ctx.exception.generation_submitted, False)

    def test_refused_connect_is_not_submitted(self):
        replies = iter([{'status': 'disconnected'}, {'status': 'blocked', 'reason': 'NO_CHROME_CONTEXT'}])
        with patch('b2_bridge.send_raw_command', side_effect=lambda *a, **k: next(replies)):
            with self.assertRaises(Blocked) as ctx:
                b2_bridge.ensure_connected()
        self.assertIs(ctx.exception.generation_submitted, False)

    def test_one_failed_request_does_not_discard_the_others(self):
        out = Path(tempfile.mkdtemp())
        good = out / 'b.png'; good.write_bytes(b'image')
        reply = {'items': [None, {'request_id': 'b', 'path': str(good), 'media_id': 'm'}],
                 'failures': [{'index': 0, 'request_id': 'a', 'reason': 'FLOW_ITEM_UNKNOWN_RECONCILE_NO_RESUBMIT: x'}]}
        with patch('b2_bridge.require_queue_acceptance'), patch('b2_bridge.ensure_connected'), \
             patch('b2_bridge.send_raw_command', return_value=reply):
            items = b2_bridge.generate_b2_batch([{'testCase': 'a'}, {'testCase': 'b'}])
            self.assertEqual(items[0], {'failed': 'FLOW_ITEM_UNKNOWN_RECONCILE_NO_RESUBMIT: x', 'request_id': 'a'})
            self.assertEqual(items[1]['media_id'], 'm')
            with self.assertRaisesRegex(Blocked, 'FLOW_ITEM_UNKNOWN') as ctx:
                with patch('b2_bridge.queue_spec', return_value={'testCase': 'a'}), \
                     patch('b2_bridge.send_raw_command', return_value={'items': [None], 'failures': reply['failures'][:1]}):
                    b2_bridge.generate_b2_image('p', no_character=True, out_dir=out, test_case='a')
            self.assertIsNot(getattr(ctx.exception, 'generation_submitted', True), False, 'sent, so unknown')

    def test_retry_safe_failures_are_marked_not_submitted_and_switches_are_kept_with_the_run(self):
        out = Path(tempfile.mkdtemp())
        batch = out / 'batch'
        reply = {'items': [None, None],
                 'failures': [{'index': 0, 'request_id': 'a', 'reason': 'FLOW_NOT_SUBMITTED: FLOW_QUOTA_ALL_PROFILES_EXHAUSTED: none left'},
                              {'index': 1, 'request_id': 'b', 'reason': 'FLOW_NO_MEDIA: Expected object response with media fields'}],
                 'profileSwitches': [{'event': 'switch', 'from': 'Profile 10', 'to': 'Profile 102'}]}
        specs = [{'testCase': 'a', 'outDir': str(batch / 'a')}, {'testCase': 'b', 'outDir': str(batch / 'b')}]
        with patch('b2_bridge.require_queue_acceptance'), patch('b2_bridge.ensure_connected'), \
             patch('b2_bridge.send_raw_command', return_value=reply):
            items = b2_bridge.generate_b2_batch(specs)
            self.assertIs(items[0].get('not_submitted'), True)
            self.assertNotIn('not_submitted', items[1], 'a no-media answer keeps its own one-retry rule')
            self.assertEqual(json.loads((batch / 'profile-switches.json').read_text())[0]['to'], 'Profile 102')
            single = {'items': [None], 'failures': reply['failures'][:1]}
            with patch('b2_bridge.queue_spec', return_value=specs[0]), \
                 patch('b2_bridge.send_raw_command', return_value=single):
                with self.assertRaisesRegex(Blocked, 'ALL_PROFILES_EXHAUSTED') as ctx:
                    b2_bridge.generate_b2_image('p', no_character=True, out_dir=out, test_case='a')
            self.assertIs(ctx.exception.generation_submitted, False)

    def test_a_timeout_during_a_queue_command_stays_unknown(self):
        with patch('b2_bridge.require_queue_acceptance'), patch('b2_bridge.ensure_connected'), \
             patch('b2_bridge.send_raw_command', side_effect=Blocked('timed out after 240s: tool-snapshot:queue')):
            with self.assertRaises(Blocked) as ctx:
                b2_bridge.generate_b2_batch([{'testCase': 'x'}])
        self.assertIsNot(getattr(ctx.exception, 'generation_submitted', True), False)


if __name__ == '__main__':
    unittest.main()
