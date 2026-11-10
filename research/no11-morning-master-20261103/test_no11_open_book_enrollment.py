"""Regression of actual-open paths differing from the older DATA registration.

Excel COM is the only discovery boundary substituted here. The real installer,
registration parser, filesystem transaction, bridge source transform and
handoff path adapter execute. No real workbook/provider/account operations.
"""
from __future__ import annotations
from contextlib import ExitStack, redirect_stdout
import io
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import test_no11_live_xlsb_preflight as fixtures
import install_no11_live_xlsb_preflight as installer
import no11_live_book_path_rebind as helper
import no11_nightly_resume as n

HERE = Path(__file__).resolve().parent


class OpenBookEnrollmentTests(unittest.TestCase):
    def fixture(self):
        f = fixtures.LiveThreeBookTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        original_bridge = f.root / 'original-automatic-bridge.py'
        original_bridge.write_bytes((HERE / 'launcher_automatic_bridge_v4.py').read_bytes())
        binding = n.read(f.binding)
        binding.update(bridge=str(original_bridge), bridgeSha256=n.digest(original_bridge.read_bytes()),
                       settings=str(f.settings), sessionDate='2026-11-06')
        f.binding.write_bytes(n.encode(binding))
        f.observed = {}
        folder = f.root / '取得済み books (new location)'
        folder.mkdir()
        for role in helper.ROLES:
            p = folder / ('Ark_No11_' + role + ' (version 2).xlsb')
            p.write_bytes(b'EXISTING USER SAVED WORKBOOK FIXTURE')
            f.observed[role] = str(p)
        f.original_data = f.root / 'completed-market-data'
        f.original_data.mkdir()
        (f.original_data / 'capture.log').write_bytes(b'SAVED COMPLETED 4328 AND 142 CAPTURE')
        (f.original_data / 'checkpoint.json').write_bytes(b'PREEXISTING COMPLETE CHECKPOINT')
        f.original_bridge = original_bridge
        return f

    def export(self, f, locations=None):
        locations = f.observed if locations is None else locations
        def run(argv, **kwargs):
            self.assertIn('-Discover', argv)
            self.assertNotIn('-IApproveOrdersForToday', argv)
            dest = Path(argv[argv.index('-OutputFile') + 1])
            record = {'schemaId': 'ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1',
                'books': [{'role': role, 'path': path, 'name': Path(path).name,
                           'sheet': helper.ROLES[role][1], 'date1904': False}
                          for role, path in locations.items()], 'orderTransmission': False}
            dest.write_bytes(n.encode(record))
            return types.SimpleNamespace(returncode=0, stdout=b'', stderr=b'')
        return run

    def apply(self, f, do_apply=True, export=None):
        with patch.object(installer, 'check_quiet'), \
             patch.object(installer, 'powershell_syntax'), \
             patch.object(installer.subprocess, 'run', side_effect=export or self.export(f)), \
             redirect_stdout(io.StringIO()):
            return installer.install(f.store, do_apply, False)

    def test_real_discovery_result_not_rejected_for_obsolete_registered_location(self):
        f = self.fixture()
        binding = n.read(f.binding)
        with patch.object(installer.subprocess, 'run', side_effect=self.export(f)):
            observed = installer.actual_open_books(binding, f.books)
        # This is precisely the old failing predicate, not a new mock bypass.
        self.assertFalse(helper.same_locations(observed, f.books))
        self.assertEqual(observed, f.observed)

    def test_explicit_enrollment_synchronizes_both_consumers_and_preserves_originals(self):
        f = self.fixture()
        before = {p: p.read_bytes() for p in
                  [f.registration, f.resolver, f.white, f.observer, f.original_bridge,
                   *f.original_data.iterdir(), *map(Path, f.books.values()),
                   *map(Path, f.observed.values())]}
        self.assertEqual(self.apply(f), 'PASS')
        settings = n.read(f.settings)
        binding = n.read(f.binding)
        record = n.read(Path(binding['dataWorkbookRegistration']))
        self.assertEqual(helper.registry_paths(record), f.observed)
        self.assertEqual(n.digest(Path(binding['dataWorkbookRegistration']).read_bytes()),
                         binding['dataWorkbookRegistrationSha256'])
        for role, (field, _) in helper.ROLES.items():
            self.assertEqual(settings[field], f.observed[role])
        self.assertEqual(settings['bootstrapConfigFile'], f.config['bootstrapConfigFile'])
        self.assertFalse(settings['automaticOrderAuthorization'])
        self.assertFalse(binding['orderTransmission'])
        self.assertIn(helper.MARK.encode(), Path(binding['bridge']).read_bytes())
        self.assertEqual(n.digest(Path(binding['bridge']).read_bytes()), binding['bridgeSha256'])
        for p, raw in before.items():
            self.assertEqual(p.read_bytes(), raw, str(p))
        self.assertEqual(self.apply(f), 'ALREADY_APPLIED')

    def test_audit_does_not_write_configuration_or_registry(self):
        f = self.fixture()
        before = {p: p.read_bytes() for p in [f.settings, f.binding, f.registration,
                                             f.launcher, f.trade]}
        self.assertEqual(self.apply(f, False), 'READY')
        self.assertFalse((f.store / installer.JOURNAL).exists())
        self.assertEqual(list(f.store.glob('open-three-book-enrollment-*')), [])
        for p, raw in before.items():
            self.assertEqual(p.read_bytes(), raw)

    def test_moved_old_book_is_not_required_to_re_enroll_current_open_book(self):
        f = self.fixture()
        Path(f.books['Account']).unlink()
        self.assertEqual(self.apply(f), 'PASS')
        self.assertEqual(n.read(f.settings)['accountWorkbookPath'], f.observed['Account'])

    def test_books_changed_during_install_are_rejected_before_any_write(self):
        f = self.fixture()
        calls = 0
        def export(argv, **kwargs):
            nonlocal calls
            calls += 1
            return self.export(f, f.observed if calls == 1 else f.books)(argv, **kwargs)
        before = f.binding.read_bytes(), f.settings.read_bytes()
        with self.assertRaisesRegex(ValueError, 'OPEN_BOOKS_CHANGED_DURING_INSTALL'):
            self.apply(f, export=export)
        self.assertEqual(before, (f.binding.read_bytes(), f.settings.read_bytes()))
        self.assertFalse((f.store / installer.JOURNAL).exists())

    def test_failed_discovery_never_changes_registration(self):
        f = self.fixture()
        before = f.binding.read_bytes(), f.settings.read_bytes()
        def failed(*args, **kwargs):
            return types.SimpleNamespace(returncode=2, stdout=b'', stderr=b'NO11_DATA_BOOK_COM_ATTACH\n')
        with self.assertRaisesRegex(ValueError, 'EXCEL_THREE_OR_RSS_BOOKS_NOT_OPEN'):
            self.apply(f, export=failed)
        self.assertEqual(before, (f.binding.read_bytes(), f.settings.read_bytes()))
        self.assertFalse((f.store / installer.JOURNAL).exists())

    def handoff(self, f, old_path=None):
        root = f.original_data
        selected = [str(3000 + i) + '.T' for i in range(46)]
        spec, pins = {}, {}
        for name in ('chartReceipt', 'passMask', 'previousStage'):
            p = root / (name + '.json')
            p.write_bytes(n.encode({'selectedSymbols': selected, 'source': 'SYNTHETIC_TEST_ONLY'}))
            spec[name] = str(p)
            pins[name] = n.digest(p.read_bytes())
        obj = {'schemaId': 'ARK_NO11_MORNING_MASTER_HANDOFF_V1',
            'sessionDate': '2026-11-10', 'previousSession': '2026-11-09',
            'selectedSymbols': selected, 'sourcePins': pins, 'spec': spec,
            'orderIdWorkbookPath': old_path or f.config['orderIdWorkbookPath'],
            'reviewStatus': 'NOT_REVIEWED', 'datedMasterCreated': False,
            'productionReady': False, 'orderTransmission': False,
            'testOnlyEligibleEntryCount': 37}
        raw = n.encode(obj)
        p = root / ('morning-handoff-' + n.digest(raw) + '.json')
        p.write_bytes(raw)
        pointer = root / '2026-11-10.json'
        pointer.write_bytes(n.encode({'handoff': str(p), 'handoffSha256': n.digest(raw)}))
        return p, pointer, obj

    def test_completed_46_symbol_handoff_and_pointer_remain_immutable(self):
        f = self.fixture()
        self.apply(f)
        hand, pointer, original = self.handoff(f)
        protected = {p: p.read_bytes() for p in f.original_data.iterdir()}
        binding = dict(n.read(f.binding), sessionDate='2026-11-10',
                       handoff=str(hand), handoffSha256=n.digest(hand.read_bytes()))
        with redirect_stdout(io.StringIO()):
            updated = helper.rebind_handoff(binding, '2026-11-10')
        new = n.read(Path(updated['handoff']))
        expected = dict(original, orderIdWorkbookPath=f.observed['OrderIds'])
        self.assertEqual(new, expected)
        self.assertEqual(len(new['selectedSymbols']), 46)
        self.assertEqual(new['testOnlyEligibleEntryCount'], 37)
        for p, raw in protected.items():
            self.assertEqual(p.read_bytes(), raw)
        self.assertEqual(helper.rebind_handoff(updated, '2026-11-10'), updated)
        # Generated copy must not alias the source inode.
        Path(updated['handoff']).write_bytes(b'MUTATION OF DERIVED COPY')
        self.assertEqual(hand.read_bytes(), protected[hand])
        self.assertEqual(pointer.read_bytes(), protected[pointer])

    def test_unknown_old_handoff_path_and_wrong_session_are_not_relabelled(self):
        f = self.fixture()
        self.apply(f)
        hand, _, _ = self.handoff(f, str(f.root / 'UNRELATED_ORDER_BOOK.xlsb'))
        binding = dict(n.read(f.binding), sessionDate='2026-11-10',
                       handoff=str(hand), handoffSha256=n.digest(hand.read_bytes()))
        with self.assertRaisesRegex(ValueError, 'UNREGISTERED_OLD_ORDER_PATH'):
            helper.rebind_handoff(binding, '2026-11-10')
        with self.assertRaisesRegex(ValueError, 'HANDOFF_CONTRACT'):
            helper.rebind_handoff(binding, '2026-11-11')

    def test_source_receipt_change_never_becomes_an_accepted_location_update(self):
        f = self.fixture()
        self.apply(f)
        hand, _, obj = self.handoff(f)
        Path(obj['spec']['previousStage']).write_bytes(n.encode({'tampered': True}))
        binding = dict(n.read(f.binding), sessionDate='2026-11-10',
                       handoff=str(hand), handoffSha256=n.digest(hand.read_bytes()))
        with self.assertRaisesRegex(ValueError, 'HANDOFF_SOURCE_CHANGED'):
            helper.rebind_handoff(binding, '2026-11-10')

    def test_all_four_commit_boundaries_can_resume_without_erasing_data(self):
        for interrupted_after in (1, 2, 3, 4):
            with self.subTest(after=interrupted_after):
                f = self.fixture()
                original = installer.atomic_replace
                count = 0
                def cut(*args):
                    nonlocal count
                    original(*args)
                    count += 1
                    if count == interrupted_after:
                        raise KeyboardInterrupt('SIMULATED_POWER_CUT')
                with patch.object(installer, 'atomic_replace', side_effect=cut):
                    with self.assertRaises(KeyboardInterrupt):
                        self.apply(f)
                self.assertEqual(n.checkpoint(f.store / installer.JOURNAL)['phase'], 'PREPARED')
                self.assertEqual(self.apply(f), 'PASS')
                self.assertEqual((f.original_data / 'checkpoint.json').read_bytes(),
                                 b'PREEXISTING COMPLETE CHECKPOINT')

    def test_bridge_patch_keeps_original_approval_and_all_other_code(self):
        raw = (HERE / 'launcher_automatic_bridge_v4.py').read_bytes()
        updated = helper.transform_bridge(raw)
        self.assertEqual(helper.transform_bridge(updated), updated)
        old_text = raw.decode('utf-8-sig').replace('\r\n', '\n')
        new_text = updated.decode('utf-8-sig').replace('\r\n', '\n')
        self.assertEqual(new_text.replace(helper.HOOK, '', 1), old_text)
        self.assertLess(new_text.index("need(same_day_operator_approved is True"),
                        new_text.index(helper.MARK))
        self.assertNotIn('RssStockOrder(', helper.HOOK)


if __name__ == '__main__':
    unittest.main(verbosity=2)
