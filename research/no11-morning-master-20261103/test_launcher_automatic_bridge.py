"""Synthetic integration tests; never run automatic collection or broker orders."""
from copy import deepcopy
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import launcher_automatic_bridge as b
import automatic_launcher_install as installer

ENGINE = Path(__file__).resolve().parents[1] / 'no12-prebuy-causal-runtime-20261011'
DAY = '2026-11-04'


class LauncherPatchTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ENGINE / 'windows/Start-No11UnifiedLauncher.ps1').read_bytes()

    def test_original_trade_gets_one_hook_after_approval_before_config(self):
        text = b.patch_launcher(self.raw).decode('utf-8-sig').replace('\r\n', '\n')
        body = text[text.index('function RunTrade('):text.index('function RunWeekly(')]
        self.assertEqual(text.count(b.MARKER), 1)
        self.assertLess(body.index('Need $approved'), body.index(b.MARKER))
        self.assertLess(body.index(b.MARKER), body.index(b.START))
        self.assertIn('TRADE_ALREADY_STARTED_NO_DUPLICATE', body)

    def test_local_ui_and_rss_funding_edits_are_preserved(self):
        raw = self.raw.replace(b'function RunTrade(', b'# existing local UI2 change\nfunction RunTrade(')
        raw = raw.replace(b'AUTO_SECURITIES_ACCOUNT_CASH_ONLY', b'AUTO_RSS_BUYING_POWER')
        after = b.patch_launcher(raw)
        normalized = after.decode('utf-8-sig').replace('\r\n', '\n')
        original = raw.decode('utf-8-sig').replace('\r\n', '\n')
        self.assertEqual(normalized.replace(b.HOOK, '', 1), original)
        self.assertIn(b'AUTO_RSS_BUYING_POWER', after)

    def test_patch_idempotent(self):
        after = b.patch_launcher(self.raw)
        self.assertEqual(b.patch_launcher(after), after)

    def test_bom_and_crlf_preserved(self):
        text = self.raw.decode('utf-8-sig').replace('\r\n', '\n')
        raw = b'\xef\xbb\xbf' + text.replace('\n', '\r\n').encode()
        after = b.patch_launcher(raw)
        self.assertTrue(after.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n', after.replace(b'\r\n', b''))

    def test_changed_anchor_is_not_guessed(self):
        with self.assertRaisesRegex(ValueError, 'CONFIG_ANCHOR_CHANGED'):
            b.patch_launcher(self.raw.replace(b'LIVE_BOOTSTRAP_CONFIG', b'OTHER_BOOTSTRAP'))

    def test_partial_hook_is_not_silently_reapplied(self):
        with self.assertRaisesRegex(ValueError, 'PARTIAL_OR_DIFFERENT_HOOK'):
            b.patch_launcher(self.raw + ('\n' + b.MARKER).encode())

    def test_no_start_or_order_permit_in_bridge(self):
        text = Path(b.__file__).read_text(encoding='utf-8')
        for bad in ('RssStockOrder(', 'RssCancelOrder(', 'subprocess.Popen(', 'input(', 'EXTERNALLY_REVIEWED'):
            self.assertNotIn(bad, text)
        self.assertIn("'INITIAL_BROKER_CONNECTION_NOT_CONFIGURED'", text)


class ReferencePatchTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ENGINE / 'windows/Capture-No11SessionReferenceReadOnly.ps1').read_bytes()

    def test_only_explicitly_configured_third_book_is_allowed(self):
        after = installer.patch_reference(self.raw).decode('utf-8-sig').replace('\r\n', '\n')
        self.assertIn('CONFIGURED_BROKER_BOOK_IDENTITY', after)
        self.assertIn('ARK_ORDER_IDS_READONLY', after)
        self.assertIn('FullName', installer.REPLACEMENT)
        self.assertIn('-in @(2,3)', installer.REPLACEMENT)
        self.assertNotIn('.Close(', installer.REPLACEMENT)
        self.assertNotIn('.Open(', installer.REPLACEMENT)
        self.assertNotIn('.Save', installer.REPLACEMENT)

    def test_reference_other_local_edits_unchanged(self):
        raw = self.raw + b'\n# local retry customization\n'
        after = installer.patch_reference(raw).decode('utf-8-sig').replace('\r\n', '\n')
        restored = after.replace(installer.REPLACEMENT, installer.ANCHOR, 1)
        self.assertEqual(restored, raw.decode('utf-8-sig').replace('\r\n', '\n'))

    def test_reference_patch_is_idempotent(self):
        after = installer.patch_reference(self.raw)
        self.assertEqual(installer.patch_reference(after), after)

    def test_unknown_reference_check_blocks_install(self):
        with self.assertRaisesRegex(ValueError, 'REFERENCE_BOOK_CHECK_CHANGED'):
            installer.patch_reference(self.raw.replace(b'Workbooks.Count -eq 2', b'Workbooks.Count -eq 7'))


class BrokerMergeTests(unittest.TestCase):
    def setUp(self):
        self.prepared = {'schemaId': 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1',
            'sessionDate': DAY, 'productionReady': False, 'orderTransmission': False,
            'orderIdWorkbookPath': 'broker.xlsx', 'runtimeRoot': 'p1', 'h235ModelRoot': 'h235',
            'precomputedChartReceipt': 'chart41.json', 'precomputedG1Mask': 'mask.json',
            'weeklySourceRun': 'seed429', 'privateRoot': 'new-input-output',
            'datedMaster': 'new-master', 'previousContext': 'new-context'}
        self.old = {**self.prepared, 'privateRoot': 'EXISTING_LEDGER_ROOT',
                    'brokerExecutionConfig': 'EXISTING_BROKER_FILE', 'samples': 390}
        self.broker = {'schemaId': 'ARK_NO11_BROKER_EXECUTION_CONFIG_V1',
            'sessionDate': DAY, 'fundingPolicy': 'RSS_BUYING_POWER', 'feeCourse': 'ZERO',
            'productionReady': False, 'orderTransmission': True,
            'transport': {'sessionDate': DAY, 'mode': 'LIVE', 'operatorEnabled': True,
                          'approvedForSession': True, 'orderTransmission': True,
                          'workbookPath': 'broker.xlsx'},
            'ledger': {'maxSymbols': 3, 'lotSize': 100, 'account': '一般',
                       'allocatedCashJpy': 'AUTO_RSS_BUYING_POWER'},
            'orderTerms': {'sor': True, 'accountType': 1, 'accountTypeVerified': True,
                           'orderType': 'MARKET', 'timeInForce': 'DAY'}}

    def merge(self):
        return b.merge_current_broker(self.prepared, self.old, self.broker, DAY)

    def test_same_day_reuses_ledger_root_and_original_broker(self):
        before = deepcopy((self.prepared, self.old, self.broker))
        result = self.merge()
        self.assertEqual(result['privateRoot'], 'EXISTING_LEDGER_ROOT')
        self.assertEqual(result['brokerExecutionConfig'], 'EXISTING_BROKER_FILE')
        self.assertEqual(result['datedMaster'], 'new-master')
        self.assertEqual(result['samples'], 390)
        self.assertEqual((self.prepared, self.old, self.broker), before)
        self.assertFalse(result['orderTransmission'])

    def test_old_broker_cannot_be_redated(self):
        self.old['sessionDate'] = '2026-11-02'
        with self.assertRaisesRegex(ValueError, 'CURRENT_SESSION'):
            self.merge()

    def test_missing_physical_approval_not_created(self):
        self.broker['transport']['approvedForSession'] = False
        with self.assertRaisesRegex(ValueError, 'EXISTING_SESSION_TRANSPORT_REQUIRED'):
            self.merge()
        self.assertFalse(self.broker['transport']['approvedForSession'])

    def test_old_47_chart_cannot_replace_current_41(self):
        self.old['precomputedChartReceipt'] = 'old47.json'
        with self.assertRaisesRegex(ValueError, 'INPUT_SCOPE_DIFFERS'):
            self.merge()

    def test_funding_account_lot_and_max3_unchanged(self):
        for key, value in [('maxSymbols', 1), ('lotSize', 1), ('account', 'OTHER'),
                           ('allocatedCashJpy', 'AUTO_SECURITIES_ACCOUNT_CASH_ONLY')]:
            original = self.broker['ledger'][key]
            self.broker['ledger'][key] = value
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_ACCOUNT_CAPITAL_TERMS'):
                self.merge()
            self.broker['ledger'][key] = original

    def test_no_shadow_bootstrap_fallback(self):
        self.prepared['shadowAccountConfig'] = 'shadow.json'
        with self.assertRaisesRegex(ValueError, 'AUTOMATIC_BOOTSTRAP_CONTRACT'):
            self.merge()


class LocalAtomicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_compare_before_replace_and_absent_creation(self):
        file = self.root / 'config.json'
        b.replace_bytes(file, b'one', None)
        b.replace_bytes(file, b'two', b'one')
        with self.assertRaisesRegex(ValueError, 'CONCURRENT_EDIT'):
            b.replace_bytes(file, b'wrong', b'one')
        self.assertEqual(file.read_bytes(), b'two')

    def test_lock_does_not_remove_other_process_lock(self):
        file = self.root / 'running.lock'
        with b.lock(file):
            before = file.read_bytes()
            with self.assertRaisesRegex(ValueError, 'ALREADY_RUNNING'):
                with b.lock(file):
                    self.fail('must not enter')
            self.assertEqual(file.read_bytes(), before)
        self.assertFalse(file.exists())

    def test_lock_released_after_handled_error(self):
        file = self.root / 'running.lock'
        with self.assertRaises(RuntimeError):
            with b.lock(file):
                raise RuntimeError('fixture')
        self.assertFalse(file.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows PowerShell 5.1 integration')
    def test_patched_native_powershell_parse_and_offline_selftests(self):
        # Real original scripts execute only their -OfflineSelfTest branches.
        windows = self.root / 'research/runtime/windows'
        windows.mkdir(parents=True)
        for dependency in ('Run-No11ReceivedSessionOperatorLive.ps1',
                           'Prepare-No11WeeklyAfterCloseReadOnly.ps1', 'Start-No11LiveUiReadOnly.ps1'):
            (windows / dependency).write_text('# unused offline dependency\n')
        for name, transform, expected in [
            ('Start-No11UnifiedLauncher.ps1', b.patch_launcher, 'NO11_UNIFIED_OFFLINE_SELFTEST=PASS'),
            ('Capture-No11SessionReferenceReadOnly.ps1', installer.patch_reference, 'NO11_REFERENCE_OFFLINE_SELFTEST=PASS')]:
            target = windows / name
            target.write_bytes(transform((ENGINE / 'windows' / name).read_bytes()))
            b.parse_ps(target)
            result = b.invoke(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                               'Bypass', '-File', str(target), '-OfflineSelfTest'], 'FIXTURE_PS_SELFTEST')
            self.assertIn(expected, result)
            self.assertIn('ORDER_TRANSMISSION=False', result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
