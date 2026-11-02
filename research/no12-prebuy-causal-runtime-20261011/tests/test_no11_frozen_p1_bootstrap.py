"""Saved-source preparation and paired read-only lifecycle; synthetic tests only."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_received_session_bootstrap as b
import no11_received_pipeline_service as service
import no11_frozen_p1_feature_runtime as features
import test_no11_frozen_p1_rss_state_stream as stream
import test_no11_p1_forward_shadow as p1base

DAY = '2026-10-26'
PRIOR = '2026-10-23'
NOW = DAY + 'T09:10:00.000+09:00'
CODE = '7203.T'


class BootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = features.load_feature_runtime(b.ROOT)
        plan_url = (TOOLS.parent / 'runtime/no11_rss_chart_50_prescreen.mjs').as_uri()
        mask_url = (TOOLS.parent / 'runtime/no11_observed_pass_watch_gate.mjs').as_uri()
        script = ('import {makeNo11G1Chart50Plan} from ' + json.dumps(plan_url) + ';'
                  'import {OBSERVED_PASS_GATE_ID} from ' + json.dumps(mask_url) + ';'
                  'const mask={schemaId:OBSERVED_PASS_GATE_ID,asOfSession:"2026-10-23",'
                  'observedPassSymbols:["7203.T"],observedPassCount:1,planId:"test-plan",'
                  'strictNoUnknownFallback:true,shadowOnly:true,productionReady:false,orderTransmission:false};'
                  'const chartPlan=makeNo11G1Chart50Plan({mask,sessionDate:"2026-10-26",'
                  'priorityRows:[{symbol:"7203.T",minMarginPct:1,meanMarginPct:2}]});'
                  'console.log(JSON.stringify({mask,plan:{schemaId:"ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1",'
                  'chartPlan,productionReady:false,orderTransmission:false}}));')
        r = subprocess.run(['node', '--input-type=module', '-e', script],
                           capture_output=True, text=True, check=True, timeout=25)
        cls.scope = json.loads(r.stdout)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ('daily', 'runtime', 'private', 'prepared', 'capture'):
            (self.root / name).mkdir()
        self.master = {'schemaId': 'ARK_NO11_DATED_MASTER_RECEIPT_V1', 'sessionDate': DAY,
                       'knownAtJst': DAY + 'T08:50:00+09:00', 'rows': [{
                           'symbol': CODE, 'asOfSession': DAY, 'rawPreviousClose': 100,
                           'segment': 'PRIME', 'sector': '01', 'commonEquity': True,
                           'corporateActionsCleared': True, 'priceBasisVerified': True}],
                       'productionReady': False, 'orderTransmission': False}
        self.plan = self.write('plan.json', self.scope['plan'])
        self.mask = self.write('mask.json', self.scope['mask'])
        self.master_path = self.write('master.json', self.master)
        self.previous = self.write('previous.json', stream.previous(False))
        self.config = {'schemaId': b.CONFIG, 'sessionDate': DAY,
                       'dailyRun': str(self.root / 'daily'), 'datedMaster': str(self.master_path),
                       'runtimeRoot': str(self.root / 'runtime'), 'privateRoot': str(self.root / 'private'),
                       'previousContext': str(self.previous), 'productionReady': False,
                       'orderTransmission': False}

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, value):
        file = self.root / name
        file.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return file

    def snapshot(self, changes=None):
        rows = []
        for m in (540, 541, 542):
            price = 100 + (m - 540) * .1
            rows.append({'Date': PRIOR, 'Code': CODE, 'Time': f'{m//60:02d}:{m%60:02d}',
                         'O': price, 'H': price + .2, 'L': price - .2, 'C': price + .01,
                         'Vo': 100, 'knownAtJst': PRIOR + f'T{(m+1)//60:02d}:{(m+1)%60:02d}:08+09:00'})
        obj = {'schemaId': b.CAPTURE, 'sessionDate': PRIOR,
               'source': 'RssChart_1M_AND_RssMarket_CUMULATIVE_READONLY',
               'observedEndJst': PRIOR + 'T09:04:00+09:00', 'chartRows': rows,
               'productionReady': False, 'orderTransmission': False, 'shadowOnly': True}
        if changes:
            changes(obj)
        data = json.dumps(obj, separators=(',', ':')).encode()
        file = self.root / ('snapshot-' + hashlib.sha256(data).hexdigest() + '.json')
        file.write_bytes(data)
        return file

    def make_prior(self, files):
        return b.prior_from_captures(files, [CODE], DAY, PRIOR, self.master, NOW)

    def test_config_explicit_readonly_and_previous_source(self):
        c = b.validate_config(self.config)
        self.assertEqual(c['samples'], 390)
        self.assertEqual(c['historyBars'], 120)
        for update in ({'orderTransmission': True}, {'unexpected': 1},
                       {'previousCaptureFiles': []}, {'samples': True}):
            with self.assertRaises(ValueError):
                b.validate_config(dict(self.config, **update))
        c = deepcopy(self.config)
        del c['previousContext']
        with self.assertRaisesRegex(ValueError, 'EXACTLY_ONE_PREVIOUS_SOURCE'):
            b.validate_config(c)

    def test_missing_source_no_fabrication_and_no_collector(self):
        c = dict(self.config, datedMaster=str(self.root / 'missing.json'))
        with self.assertRaisesRegex(ValueError, 'PRIVATE_SOURCE_MISSING'):
            b.validate_config(c)
        with mock.patch.object(b.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(ValueError, 'PRIVATE_SOURCE_MISSING'):
                b.main(['--config', str(self.write('bad-config.json', c))])
            spawn.assert_not_called()

    def broker_config(self, **changes):
        # The bootstrap only enforces the observation boundary. The service
        # validates these nested ledger/order terms before using the config.
        obj = {'schemaId': b.BROKER_CONFIG, 'sessionDate': DAY,
               'evidenceMode': 'BROKER_OBSERVATION', 'ledger': {},
               'transport': {'mode': 'OBSERVE_ONLY'}, 'orderTerms': {},
               'originalArrivalTable': {}, 'orderTransmission': False}
        obj.update(changes)
        return self.write('broker.json', obj)

    def broker_bootstrap(self, **changes):
        return dict(self.config, h235ModelRoot=str(self.root / 'runtime'),
                    brokerExecutionConfig=str(self.broker_config(**changes)))

    def test_broker_observation_optional_and_service_always_readonly(self):
        prepared = {'files': {'plan': str(self.plan), 'mask': str(self.mask),
                             'master': str(self.master_path), 'previous': str(self.previous)}}
        args = b.service_args(b.validate_config(self.config), prepared, self.root / 'private')
        self.assertNotIn('--broker-execution-config', args)
        self.assertNotIn('--broker-execution-readonly', args)
        for mode in ('DISABLED', 'OBSERVE_ONLY'):
            with self.subTest(mode=mode):
                cfg = b.validate_config(self.broker_bootstrap(transport={'mode': mode}))
                args = b.service_args(cfg, prepared, self.root / 'private')
                self.assertEqual(args.count('--broker-execution-config'), 1)
                self.assertEqual(args[args.index('--broker-execution-config') + 1], cfg['brokerExecutionConfig'])
                self.assertEqual(args.count('--broker-execution-readonly'), 1)
                self.assertIn('--h235-model-root', args)

    def test_broker_observation_requires_h235_model(self):
        cfg = self.broker_bootstrap()
        del cfg['h235ModelRoot']
        with self.assertRaisesRegex(ValueError, 'H235_REQUIRED_FOR_BROKER_OBSERVATION'):
            b.validate_config(cfg)

    def test_broker_bootstrap_rejects_live_replay_wrong_session_or_implicit_flags(self):
        changes = [({'transport': {'mode': 'LIVE'}}, 'BROKER_CONFIG_NOT_READONLY'),
                   ({'transport': {'mode': 'OFFLINE_REPLAY'}}, 'BROKER_CONFIG_NOT_READONLY'),
                   ({'transport': None}, 'BROKER_CONFIG_NOT_READONLY'),
                   ({'orderTransmission': True}, 'BROKER_CONFIG_NOT_READONLY'),
                   ({'orderTransmission': 0}, 'BROKER_CONFIG_NOT_READONLY'),
                   ({'evidenceMode': 'OFFLINE_REPLAY'}, 'BROKER_CONFIG_OBSERVATION_REQUIRED'),
                   ({'sessionDate': PRIOR}, 'BROKER_CONFIG_SESSION_MISMATCH'),
                   ({'schemaId': 'OTHER'}, 'BROKER_CONFIG_CONTRACT_INVALID')]
        for update, reason in changes:
            with self.subTest(update=update), self.assertRaisesRegex(ValueError, reason):
                b.validate_config(self.broker_bootstrap(**update))
        cfg = self.broker_bootstrap()
        obj = json.loads(Path(cfg['brokerExecutionConfig']).read_text())
        del obj['orderTransmission']
        Path(cfg['brokerExecutionConfig']).write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, 'BROKER_CONFIG_CONTRACT_INVALID'):
            b.validate_config(cfg)

    def test_broker_config_rechecked_before_service_arguments(self):
        cfg = b.validate_config(self.broker_bootstrap())
        self.broker_config(transport={'mode': 'LIVE'}, orderTransmission=True)
        prepared = {'files': {'plan': str(self.plan), 'mask': str(self.mask),
                             'master': str(self.master_path), 'previous': str(self.previous)}}
        with self.assertRaisesRegex(ValueError, 'BROKER_CONFIG_NOT_READONLY'):
            b.service_args(cfg, prepared, self.root / 'private')

    def test_broker_invalid_launch_never_starts_collector(self):
        cfg = self.write('bad-broker-bootstrap.json', self.broker_bootstrap(transport={'mode': 'LIVE'}))
        with mock.patch.object(b.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(ValueError, 'BROKER_CONFIG_NOT_READONLY'):
                b.main(['--config', str(cfg)])
            spawn.assert_not_called()

    def test_supplemental_workbook_path_passed_from_pinned_config_only(self):
        book = self.root / 'read only ids.xlsx'
        book.write_bytes(b'synthetic-workbook-identity-only')
        cfg = b.validate_config(dict(self.config, orderIdWorkbookPath=str(book)))
        prepared = {'files': {'plan': str(self.plan)}}
        with mock.patch.dict(os.environ, {'ARK_NO11_ORDER_ID_WORKBOOK_PATH': 'UNTRUSTED_OVERRIDE'}):
            args = b.collector_command(cfg, prepared, self.root / 'ready', self.root / 'stop')
        self.assertEqual(args[args.index('-OrderIdWorkbookPath') + 1], str(book))
        plain = b.collector_command(b.validate_config(self.config), prepared,
                                    self.root / 'ready', self.root / 'stop')
        self.assertNotIn('-OrderIdWorkbookPath', plain)
        macro = self.root / 'ids.xlsm'; macro.write_bytes(b'not-an-allowed-template')
        with self.assertRaisesRegex(ValueError, 'ORDER_ID_WORKBOOK_TYPE'):
            b.validate_config(dict(self.config, orderIdWorkbookPath=str(macro)))

    def test_current_master_is_validated_by_actual_node_pipeline(self):
        self.assertEqual(b.validate_scope(DAY, self.plan, self.mask, self.master_path, NOW), [CODE])
        self.master['rows'][0]['corporateActionsCleared'] = False
        self.master_path = self.write('master-bad.json', self.master)
        with self.assertRaisesRegex(ValueError, 'SOURCE_EXPORT_OR_VALIDATION_FAILED'):
            b.validate_scope(DAY, self.plan, self.mask, self.master_path, NOW)

    def test_plan_roundtrip_retains_javascript_order_dependent_hash(self):
        copied = b.immutable(self.root / 'prepared', 'plan', self.scope['plan'])
        self.assertEqual(b.validate_scope(DAY, copied, self.mask, self.master_path, NOW), [CODE])

    def test_source_snapshot_can_build_prior_ohlcv_without_inventing_va(self):
        source = self.snapshot()
        original = source.read_bytes()
        result = self.make_prior([source])
        item = result['symbols'][CODE]
        self.assertEqual(item['knownAtJst'], NOW)
        self.assertEqual(item['previousSession'], PRIOR)
        self.assertEqual(len(item['rows']), 3)
        self.assertTrue(all('Va' not in row for row in item['rows']))
        self.assertFalse(item['fullPreviousSessionCoverageCertified'])
        self.assertEqual(source.read_bytes(), original)
        self.assertFalse(result['orderTransmission'])

    def test_prior_hash_and_closed_bar_time_are_checked(self):
        source = self.snapshot()
        source.write_bytes(source.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'PREVIOUS_CAPTURE_HASH_MISMATCH'):
            self.make_prior([source])
        wrong = self.snapshot(lambda o: o['chartRows'][0].update(knownAtJst=PRIOR + 'T09:00:05+09:00'))
        with self.assertRaisesRegex(ValueError, 'PREVIOUS_BAR_NOT_CLOSED_WHEN_READ'):
            self.make_prior([wrong])

    def test_revised_prior_bar_excludes_symbol_instead_of_overwriting(self):
        a = self.snapshot()
        c = self.snapshot(lambda o: o['chartRows'][0].update(C=100.02))
        result = self.make_prior([a, c])
        self.assertEqual(result['symbols'], {})
        self.assertEqual(result['omittedSymbols'], [CODE])

    def test_wrong_session_and_unknown_price_basis_are_rejected(self):
        bad = self.snapshot(lambda o: o.update(sessionDate='2026-10-22'))
        with self.assertRaisesRegex(ValueError, 'PREVIOUS_CAPTURE_CONTRACT_INVALID'):
            self.make_prior([bad])
        source = self.snapshot()
        self.master['rows'][0]['priceBasisVerified'] = False
        with self.assertRaisesRegex(ValueError, 'PREVIOUS_PRICE_BASIS_NOT_EVIDENCED'):
            self.make_prior([source])

    def test_actual_state9_previous_normalization_and_missing_symbol_counts(self):
        previous = stream.previous(False)
        valid, blocked = b.previous_coverage(previous, [CODE, '9999.T'], DAY, PRIOR, self.runtime)
        self.assertEqual(valid, [CODE])
        self.assertIn('9999.T', blocked)
        self.assertNotIn('Va', previous['symbols'][CODE]['rows'][0])

    def test_prepare_packages_existing_inputs_and_leaves_originals_untouched(self):
        before = self.master_path.read_bytes()
        with mock.patch.object(b, 'stamp', return_value=NOW), \
             mock.patch.object(b, 'export_scope', return_value=(self.plan, self.mask)):
            prepared = b.prepare(b.validate_config(self.config), self.root / 'prepared')
        self.assertEqual(prepared['sourceCoverage']['usablePreviousContextCount'], 1)
        self.assertEqual(prepared['sourceCoverage']['selectedCount'], 1)
        self.assertEqual(self.master_path.read_bytes(), before)
        self.assertFalse(prepared['orderTransmission'])
        p = prepared['files']
        self.assertEqual(b.validate_scope(DAY, p['plan'], p['mask'], p['master'], NOW), [CODE])

    def test_preparation_never_invents_future_known_at(self):
        with mock.patch.object(b, 'stamp', return_value='2026-10-25T09:10:00+09:00'):
            with self.assertRaisesRegex(ValueError, 'PREPARATION_REQUIRES_ACTUAL_SESSION_DATE'):
                b.prepare(b.validate_config(self.config), self.root / 'prepared')

    def test_export_prefix_requires_one_actual_existing_file(self):
        self.assertEqual(b.output_path('VALUE=' + str(self.plan), 'VALUE='), self.plan)
        with self.assertRaisesRegex(ValueError, 'EXPORT_PATH_NOT_UNIQUE'):
            b.output_path('VALUE=' + str(self.plan) + '\nVALUE=' + str(self.plan), 'VALUE=')

    def test_collector_command_no_shell_and_has_ready_stop_prepared_plan(self):
        c = b.validate_config(self.config)
        ready = self.root / 'r.json'
        args = b.collector_command(c, {'files': {'plan': str(self.plan)}}, ready, self.root / 'stop')
        self.assertEqual(args[0], 'powershell.exe')
        self.assertIn('-PreparedPlanFile', args)
        self.assertIn('-ReadyFile', args)
        self.assertIn('-StopFile', args)
        self.assertNotIn('shell=True', repr(args))
        self.assertNotIn('RssStockOrder', repr(args))

    def test_ready_handshake_binds_pid_plan_bytes_and_private_capture_root(self):
        process = mock.Mock(pid=4242)
        capture = self.root / 'daily' / ('chart50-shadow-' + DAY + '-091000-4242')
        capture.mkdir()
        value = {'schemaId': b.READY, 'sessionDate': DAY, 'processId': 4242,
                 'captureFolder': str(capture), 'planFile': str(self.plan),
                 'planFileSha256': hashlib.sha256(self.plan.read_bytes()).hexdigest(),
                 'productionReady': False, 'orderTransmission': False}
        ready = self.write('ready.json', value)
        prepared = {'files': {'plan': str(self.plan)}}
        self.assertEqual(b.ready_capture(ready, process, self.config, prepared), capture)
        value['processId'] = 4243
        self.write('ready.json', value)
        with self.assertRaisesRegex(ValueError, 'COLLECTOR_READY_IDENTITY_MISMATCH'):
            b.ready_capture(ready, process, self.config, prepared)

    def test_normal_shutdown_requires_explicit_temporary_book_close_ack(self):
        process = mock.Mock(pid=42)
        process.wait.return_value = 0
        ready, stop, marker = self.root / 'ready.json', self.root / 'stop', self.root / 'recovery.json'
        ack = {'schemaId': b.CLOSED, 'processId': 42, 'temporaryWorkbookClosed': True,
               'orderTransmission': False}
        Path(str(ready) + '.closed.json').write_text(json.dumps(ack))
        b.shutdown_collector(process, ready, stop, marker, timeout=.01)
        self.assertTrue(stop.exists())
        self.assertFalse(marker.exists())
        process.kill.assert_not_called()
        process.terminate.assert_not_called()

    def test_missing_cleanup_ack_latches_manual_review(self):
        process = mock.Mock(pid=42)
        process.wait.return_value = 0
        marker = self.root / 'recovery.json'
        with self.assertRaisesRegex(ValueError, 'COLLECTOR_CLEANUP_NOT_CONFIRMED'):
            b.shutdown_collector(process, self.root / 'ready', self.root / 'stop', marker, timeout=.01)
        self.assertTrue(marker.exists())
        process.kill.assert_not_called()

    def test_timeout_does_not_kill_excel_and_blocks_automatic_restart(self):
        process = mock.Mock(pid=42)
        process.wait.side_effect = subprocess.TimeoutExpired('collector', .01)
        marker = self.root / 'recovery.json'
        with self.assertRaisesRegex(ValueError, 'COLLECTOR_STOP_TIMEOUT_MANUAL_CLEANUP_REQUIRED'):
            b.shutdown_collector(process, self.root / 'ready', self.root / 'stop', marker, timeout=.01)
        self.assertTrue(json.loads(marker.read_text())['originalExcelMustNotBeKilled'])
        process.kill.assert_not_called()
        process.terminate.assert_not_called()

    def test_consumer_supervisor_can_stop_before_first_two_snapshots(self):
        root = self.root / 'private'
        args = ['--session', DAY, '--capture-folder', str(self.root / 'capture'),
                '--plan', str(self.plan), '--mask', str(self.mask),
                '--dated-master', str(self.master_path), '--previous-context', str(self.previous),
                '--runtime-root', str(self.root / 'runtime'), '--private-root', str(root)]
        with mock.patch.object(service, 'now_jst', return_value=NOW), \
             mock.patch.object(service.features, 'load_feature_runtime', return_value=self.runtime), \
             mock.patch.object(service.forward, 'FrozenP1Scorer', return_value=p1base.FakeScorer()), \
             mock.patch.object(service.time, 'sleep') as sleep:
            service.main(args, should_stop=lambda: True)
        sleep.assert_not_called()
        self.assertTrue((root / ('p1-shadow-' + DAY + '.sqlite')).exists())

    def test_recovery_marker_prevents_a_new_collector(self):
        (self.root / 'private' / 'bootstrap-recovery-required.json').write_text('{}')
        config = self.write('config.json', self.config)
        with mock.patch.object(b.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(ValueError, 'PREVIOUS_CLEANUP_REQUIRES_REVIEW'):
                b.main(['--config', str(config)])
            spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
