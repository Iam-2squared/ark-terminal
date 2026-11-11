"""Offline behavioral checks for a single failed-before-registration retry.

Fixtures use the repository's original native code plus the official installed
RSS-funding transformation. No test starts PowerShell, Excel, RSS, or a broker.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / 'no12-prebuy-causal-runtime-20261011'
FUNDING = HERE.parent / 'no11-rss-funding-live-20261103'
sys.path.insert(0, str(HERE))
import no11_prestart_source_retry as retry

spec = importlib.util.spec_from_file_location('prestart_test_rss_patches', FUNDING / 'patches.py')
funding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(funding)

JST = timezone(timedelta(hours=9))
DAY = '2026-11-11'
NOW = datetime(2026, 11, 11, 13, 0, 0, tzinfo=JST)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value))
    return path


def fixture(root):
    store = root / 'unified-launcher'
    store.mkdir()
    engine = root / 'engine'
    (engine / 'tools').mkdir(parents=True)
    (engine / 'windows').mkdir()
    names = (
        'tools/no11_received_session_bootstrap.py',
        'tools/no11_received_session_controller.py',
        'tools/no11_received_run_recovery.py',
        'tools/no11_verified_weekly_shadow_scope.mjs',
        'tools/no11_received_pipeline_tick.mjs',
        'windows/Run-No11ReceivedSessionOperatorLive.ps1',
        'windows/Observe-No11AccountReadOnly.ps1',
        'windows/Read-No11BrokerSnapshot.ps1',
    )
    for name in names:
        raw = (ENGINE / name).read_bytes()
        text = raw.decode('utf-8-sig').replace('\r\n', '\n')
        if name == 'tools/no11_received_session_bootstrap.py':
            text = funding.change_bootstrap(text)
        elif name == 'windows/Run-No11ReceivedSessionOperatorLive.ps1':
            text = funding.change_operator(text)
        (engine / name).write_bytes(text.replace('\n', '\r\n').encode('utf-8'))
    shutil.copyfile(FUNDING / 'no11_rss_buying_power.py', engine / 'tools/no11_rss_buying_power.py')
    shutil.copyfile(FUNDING / 'No11RssFundingContract.ps1', engine / 'windows/No11RssFundingContract.ps1')
    private = root / 'live-private'
    private.mkdir()
    daily = root / 'daily-run'
    daily.mkdir()
    weekly = root / 'weekly-run'
    weekly.mkdir()
    runtime = root / 'model-runtime'
    runtime.mkdir()
    h235 = root / 'h235'
    h235.mkdir()
    dispatch = private / 'dispatch'
    dispatch.mkdir()
    python = root / 'python.exe'
    python.write_bytes(b'OFFLINE_FIXTURE_NEVER_EXECUTED')
    books = [root / name for name in ('account.xlsx', 'ids.xlsx', 'market.xlsx')]
    for book in books:
        book.write_bytes(b'OFFLINE_FIXTURE_NOT_AN_EXCEL_WORKBOOK')
    chart = put(daily / 'chart.json', {'sessionDate': DAY, 'orderTransmission': False})
    mask = put(daily / 'mask.json', {'sessionDate': DAY, 'orderTransmission': False})
    master = put(private / 'master.json', {'sessionDate': DAY, 'orderTransmission': False})
    previous = put(private / 'previous.json', {'sessionDate': DAY, 'orderTransmission': False})
    transport = {
        'mode': 'LIVE', 'sessionDate': DAY, 'orderTransmission': True,
        'operatorEnabled': True, 'approvedForSession': True,
        'rssSessionKey': sha(('1234\n2026-11-10T23:00:00.0000000Z\n' +
                              sha(str(books[0]).lower().encode()) + '\n' +
                              sha(str(books[1]).lower().encode())).encode()),
        'expectedExcelPid': 1234,
        'expectedExcelHwnd': 5678,
        'expectedExcelStartedAt': DAY + 'T08:00:00+09:00',
        'expiresAtJst': DAY + 'T15:30:00+09:00',
        'dispatchDirectory': str(dispatch), 'workbookPath': str(books[1]),
        'guardValue': 'ARK_NO11_SEND_ONCE', 'guardCell': 'BD1',
        'triggerCell': 'BD2', 'sessionCell': 'BD3', 'formulaCell': 'BD4',
        'worksheetName': 'ARK_ORDER_IDS_READONLY',
        'expectedOpenWorkbooks': [str(p) for p in books],
    }
    broker = put(private / 'broker.json', {
        'schemaId': 'ARK_NO11_BROKER_EXECUTION_CONFIG_V1',
        'sessionDate': DAY, 'fundingPolicy': 'RSS_BUYING_POWER',
        'feeCourse': 'ZERO', 'evidenceMode': 'BROKER_OBSERVATION',
        'productionReady': False, 'orderTransmission': True,
        'transport': transport,
        'ledger': {'sessionDate': DAY, 'maxSymbols': 3, 'lotSize': 100, 'account': '一般',
                   'allocatedCashJpy': 'AUTO_RSS_BUYING_POWER'},
        'orderTerms': {'orderType': 'MARKET', 'timeInForce': 'DAY',
                       'sor': True, 'accountType': 1, 'accountTypeVerified': True},
    })
    config = put(private / 'bootstrap.json', {
        'schemaId': 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1',
        'sessionDate': DAY, 'productionReady': False, 'orderTransmission': False,
        'dailyRun': str(daily), 'weeklySourceRun': str(weekly),
        'runtimeRoot': str(runtime), 'privateRoot': str(private),
        'h235ModelRoot': str(h235), 'brokerExecutionConfig': str(broker),
        'orderIdWorkbookPath': str(books[1]),
        'precomputedChartReceipt': str(chart), 'precomputedG1Mask': str(mask),
        'datedMaster': str(master), 'previousContext': str(previous),
        'samples': 390, 'historyBars': 120, 'warmupSeconds': 20,
    })
    settings = put(store / 'settings.json', {
        'schemaId': 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
        'bootstrapConfigFile': str(config), 'accountWorkbookPath': str(books[0]),
        'orderIdWorkbookPath': str(books[1]), 'marketWorkbookPath': str(books[2]),
        'normalMaxPositions': 3, 'sameDayApprovalRequired': True,
        'automaticOrderAuthorization': False, 'orderTransmission': False,
    })
    binding = put(store / 'automatic-inputs.json', {
        'schemaId': 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
        'engine': str(engine), 'python': str(python), 'settings': str(settings),
        'sessionDate': DAY, 'orderTransmission': False,
    })
    marker = put(store / ('TRADE-' + DAY + '.launch.json'), {
        'schemaId': 'ARK_NO11_UNIFIED_START_REQUEST_V1', 'kind': 'TRADE',
        'asOfDate': DAY, 'sourceSha256': sha(config.read_bytes()),
        'operatorRequestedAtJst': DAY + 'T09:01:11+09:00',
        'externalBrokerApprovalStillRequired': True,
    })
    request = put(store / ('PREOPEN-' + DAY + '.request.json'), {
        'schemaId': 'ARK_NO11_PREOPEN_STANDBY_REQUEST_V1',
        'sessionDate': DAY, 'sameDayExplicitOrderApproval': True,
        'orderTransmissionAtArm': False, 'tradeLaunchedAtArm': False,
        'nonce': 'f' * 32,
    })
    claim = store / ('PREOPEN-' + DAY + '.execution-claimed')
    claim.write_bytes(('PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED|' + DAY + '|' + 'f' * 32 + '\n').encode())
    run = private / ('session-' + DAY + '-' + '1' * 32)
    run.mkdir()
    failure = put(run / 'controller-failure.json', {
        'reason': 'NO11_BOOTSTRAP_SOURCE_EXPORT_OR_VALIDATION_FAILED',
        'productionReady': False, 'orderTransmission': False,
    })
    return {
        'root': root, 'store': store, 'engine': engine, 'private': private,
        'run': run, 'failure': failure, 'bootstrap': config, 'broker': broker,
        'settings': settings, 'binding': binding, 'marker': marker,
        'preopen': request, 'preopenClaim': claim, 'transport': transport,
        'books': books, 'dispatch': dispatch,
    }


def observation(transport, at=NOW):
    tables = {'orders': [], 'executions': [], 'positions': []}
    return {
        'schemaId': 'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1',
        'status': 'OBSERVED', 'readOnly': True, 'orderTransmission': False,
        'snapshot': dict(deepcopy(tables), buyingPower=100000),
        'brokerObservation': {
            'schemaId': 'ARK_NO11_BROKER_OBSERVATION_V1', 'status': 'OBSERVED',
            'readOnly': True, 'orderTransmission': False, 'productionReady': False,
            'completeTables': True, 'sameSnapshotVerified': True,
            'rowsTruncated': False, 'idRows': [], **deepcopy(tables),
            'captureCompletedAt': at.isoformat(), 'capturedAt': (at - timedelta(seconds=1)).isoformat(),
            'buyingPower': 100000,
            'excelSession': {
                'processId': transport['expectedExcelPid'],
                'startedAtUtc': '2026-11-10T23:00:00.0000000Z',
                'sessionKey': transport['rssSessionKey'],
                'accountWorkbookIdentity': sha(transport['expectedOpenWorkbooks'][0].lower().encode()),
                'orderIdWorkbookIdentity': sha(transport['expectedOpenWorkbooks'][1].lower().encode()),
            },
        },
    }


class PrestartRetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = fixture(Path(self.temp.name))

    def audit(self):
        return retry.audit(self.f['store'], now=NOW)

    def staged(self):
        manifest = retry.stage(self.f['store'], self.f['root'] / 'retry-package', now=NOW)
        return manifest, Path(manifest['manifestFile'])

    def evidence(self):
        transport = self.f['transport']
        common = {'sessionDate': DAY, 'observedAtJst': NOW.isoformat(),
                  'orderTransmission': False}
        process = put(self.f['root'] / 'process-proof.json', dict(common,
            schemaId='ARK_NO11_PRESTART_RETRY_PROCESS_V1', enumerationSucceeded=True,
            matchingWorkers=0, unreadableWorkers=0, oneClickProcesses=0, checkerPid=4444))
        physical = put(self.f['root'] / 'transport-proof.json', dict(common,
            schemaId='ARK_NO11_PRESTART_RETRY_TRANSPORT_V1', registeredThreeBooksVerified=True,
            controlCellsVerified=True, triggerZero=True, excelPid=transport['expectedExcelPid'],
            excelHwnd=transport['expectedExcelHwnd'], rssSessionKey=transport['rssSessionKey'],
            excelStartedAtUtc='2026-11-10T23:00:00.0000000Z'))
        observed = put(self.f['root'] / 'broker-observation.json', observation(transport))
        return observed, process, physical

    def test_exact_failed_before_registration_is_eligible_without_changing_originals(self):
        originals = {p: p.read_bytes() for p in self.f['root'].rglob('*') if p.is_file()}
        plan = self.audit()
        self.assertEqual(plan['sessionDate'], DAY)
        self.assertEqual(Path(plan['failureRun']), self.f['run'])
        self.assertEqual(Path(plan['bootstrapFile']), self.f['bootstrap'])
        self.assertFalse(Path(plan['claimFile']).exists())
        for p, raw in originals.items():
            self.assertEqual(p.read_bytes(), raw)

    def test_any_registered_run_or_collector_or_database_evidence_blocks(self):
        artifacts = (
            'run-contract.json', 'prepared-inputs.json', 'collector-ready.json',
            'collector-private.log', 'attempt-0001/attempt.json',
            'inference/broker-execution-' + DAY + '.sqlite',
            'inference/broker-execution-' + DAY + '.sqlite-wal',
            'inference/pipeline-current.json',
        )
        for name in artifacts:
            with self.subTest(name=name):
                p = self.f['run'] / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b'EXISTING_STATE')
                with self.assertRaises(ValueError):
                    self.audit()
                p.unlink()
                if p.parent != self.f['run']:
                    p.parent.rmdir()

    def test_active_pointer_or_dispatch_history_blocks(self):
        for p in (self.f['private'] / ('received-session-' + DAY + '.active.json'),
                  self.f['dispatch'] / 'command.json'):
            with self.subTest(path=p.name):
                p.write_bytes(b'EXISTING_STATE')
                with self.assertRaises(ValueError):
                    self.audit()
                p.unlink()

    def test_other_same_day_run_cannot_be_ignored(self):
        run = self.f['private'] / ('session-' + DAY + '-' + '2' * 32)
        run.mkdir()
        (run / 'run-contract.json').write_bytes(b'REGISTERED_OTHER_RUN')
        with self.assertRaises(ValueError):
            self.audit()

    def test_unrelated_failure_is_not_eligible(self):
        for reason in ('NO11_BOOTSTRAP_COLLECTOR_FAILED', 'SESSION_CONTROLLER_INTERRUPTED_OR_FAILED'):
            with self.subTest(reason=reason):
                put(self.f['failure'], {'reason': reason, 'productionReady': False, 'orderTransmission': False})
                with self.assertRaises(ValueError):
                    self.audit()

    def test_changed_bootstrap_config_cannot_reuse_original_trade_marker(self):
        self.f['bootstrap'].write_bytes(self.f['bootstrap'].read_bytes() + b' ')
        with self.assertRaises(ValueError):
            self.audit()

    def test_unknown_installed_bootstrap_is_not_transformed(self):
        source = self.f['engine'] / 'tools/no11_received_session_bootstrap.py'
        source.write_bytes(source.read_bytes() + b'\n# UNKNOWN_LOCAL_CHANGE\n')
        with self.assertRaises(ValueError):
            self.audit()

    def test_explicit_preopen_approval_and_exact_execution_claim_are_required(self):
        original = self.f['preopen'].read_bytes()
        request = json.loads(original)
        request['sameDayExplicitOrderApproval'] = False
        put(self.f['preopen'], request)
        with self.assertRaises(ValueError):
            self.audit()
        self.f['preopen'].write_bytes(original)
        self.f['preopenClaim'].write_bytes(
            ('PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED|' + DAY + '|' + 'e' * 32 + '\n').encode())
        with self.assertRaises(ValueError):
            self.audit()

    def test_unknown_native_controller_and_operator_do_not_enter_retry(self):
        for name in ('tools/no11_received_session_controller.py',
                     'windows/Run-No11ReceivedSessionOperatorLive.ps1'):
            with self.subTest(source=name):
                p = self.f['engine'] / name
                before = p.read_bytes()
                p.write_bytes(before + b'\n# UNKNOWN_OPERATOR_CHANGE\n')
                with self.assertRaises(ValueError):
                    self.audit()
                p.write_bytes(before)

    def test_broker_today_and_explicit_funding_contract_are_required(self):
        original = json.loads(self.f['broker'].read_bytes())
        for field, value in (('sessionDate', '2026-11-10'), ('fundingPolicy', 'UNKNOWN'),
                             ('orderTransmission', False)):
            with self.subTest(field=field):
                changed = deepcopy(original)
                changed[field] = value
                put(self.f['broker'], changed)
                with self.assertRaises(ValueError):
                    self.audit()
        put(self.f['broker'], original)

    def test_clock_must_be_same_live_session(self):
        for at in (NOW - timedelta(days=1), NOW.replace(hour=8), NOW.replace(hour=15, minute=21)):
            with self.subTest(at=at):
                with self.assertRaises(ValueError):
                    retry.audit(self.f['store'], now=at)

    def test_existing_retry_claim_is_never_reused(self):
        plan = self.audit()
        claim = Path(plan['claimFile'])
        claim.write_bytes(b'AMBIGUOUS_PRIOR_RETRY')
        with self.assertRaises(ValueError):
            self.audit()
        self.assertEqual(claim.read_bytes(), b'AMBIGUOUS_PRIOR_RETRY')

    def test_fresh_complete_empty_broker_observation_is_accepted(self):
        plan = self.audit()
        result = retry.audit_broker(plan, observation(self.f['transport']), now=NOW)
        self.assertIsInstance(result, dict)

    def test_stale_future_or_incomplete_broker_snapshot_is_refused(self):
        plan = self.audit()
        for age in (91, -1):
            with self.subTest(age=age):
                obs = observation(self.f['transport'], NOW - timedelta(seconds=age))
                with self.assertRaises(ValueError):
                    retry.audit_broker(plan, obs, now=NOW)
        for field, value in (('completeTables', False), ('sameSnapshotVerified', False),
                             ('rowsTruncated', True)):
            with self.subTest(field=field):
                obs = observation(self.f['transport'])
                obs['brokerObservation'][field] = value
                with self.assertRaises(ValueError):
                    retry.audit_broker(plan, obs, now=NOW)

    def test_any_order_execution_position_or_rss_id_prevents_fresh_start(self):
        plan = self.audit()
        for key in ('orders', 'executions', 'positions', 'idRows'):
            with self.subTest(table=key):
                obs = observation(self.f['transport'])
                obs['brokerObservation'][key] = [{'existing': 'broker state'}]
                if key != 'idRows':
                    obs['snapshot'][key] = deepcopy(obs['brokerObservation'][key])
                with self.assertRaises(ValueError):
                    retry.audit_broker(plan, obs, now=NOW)

    def test_excel_process_restart_or_session_key_mismatch_is_rejected(self):
        plan = self.audit()
        for field, value in (('processId', 9999), ('startedAtUtc', '2026-11-11T03:00:00Z'),
                             ('sessionKey', 'd' * 64)):
            with self.subTest(field=field):
                obs = observation(self.f['transport'])
                obs['brokerObservation']['excelSession'][field] = value
                with self.assertRaises(ValueError):
                    retry.audit_broker(plan, obs, now=NOW)

    def test_other_workbook_identity_cannot_reuse_same_excel_session(self):
        plan = self.audit()
        for field in ('accountWorkbookIdentity', 'orderIdWorkbookIdentity'):
            with self.subTest(field=field):
                obs = observation(self.f['transport'])
                obs['brokerObservation']['excelSession'][field] = '0' * 64
                with self.assertRaises(ValueError):
                    retry.audit_broker(plan, obs, now=NOW)

    def test_stage_is_isolated_preserves_rss_funding_and_all_existing_bytes(self):
        before = {p: p.read_bytes() for p in self.f['root'].rglob('*') if p.is_file()}
        package = self.f['root'] / 'retry-package'
        manifest = retry.stage(self.f['store'], package, now=NOW)
        self.assertEqual(manifest['sessionDate'], DAY)
        bootstrap = Path(manifest['bootstrapScript']).read_text(encoding='utf-8-sig')
        self.assertIn('import no11_rss_buying_power as rss_funding', bootstrap)
        self.assertIn('rss_funding.validate(obj)', bootstrap)
        self.assertIn('verified_weekly_original', bootstrap)
        for p, raw in before.items():
            self.assertEqual(p.read_bytes(), raw)
        for name, digest in manifest['files'].items():
            self.assertEqual(sha((package / name).read_bytes()), digest)
        with self.assertRaises((ValueError, FileExistsError)):
            retry.stage(self.f['store'], package, now=NOW)

    def test_derived_operator_changes_only_four_location_anchors(self):
        manifest, _ = self.staged()
        original = (self.f['engine'] / 'windows/Run-No11ReceivedSessionOperatorLive.ps1').read_text()
        staged = Path(manifest['operatorScript']).read_text()
        before_lines, after_lines = original.splitlines(), staged.splitlines()
        self.assertEqual(len(before_lines), len(after_lines))
        changes = [(old, new) for old, new in zip(before_lines, after_lines) if old != new]
        self.assertEqual(len(changes), 4)
        self.assertEqual({old.split('=', 1)[0] for old, _ in changes if old.startswith('$')},
                         {'$engine', '$controller', '$observer'})
        self.assertEqual(sum(old.startswith('. (Join-Path') for old, _ in changes), 1)
        # Every original condition, observer lifetime and funding wait remains.
        self.assertEqual([line for line in before_lines if line.lstrip().startswith('Need ')],
                         [line for line in after_lines if line.lstrip().startswith('Need ')])
        self.assertIn('Wait-No11RssFundingObservation $sourceFile $today $child', staged)
        self.assertIn('if(-not $child.WaitForExit(30000))', staged)

    def test_modified_package_or_original_state_is_rejected_before_claim(self):
        manifest, path = self.staged()
        files = (Path(manifest['bootstrapScript']), Path(manifest['operatorScript']),
                 self.f['broker'], self.f['settings'])
        for source in files:
            with self.subTest(source=source.name):
                original = source.read_bytes()
                source.write_bytes(original + b' ')
                with self.assertRaises(ValueError):
                    retry.verify_manifest(path, now=NOW)
                source.write_bytes(original)

    def test_rehashing_staged_core_or_helper_does_not_hide_a_changed_derivation(self):
        manifest, path = self.staged()
        original_manifest = path.read_bytes()
        for name in ('core.py', 'no11_weekly_filtered_lineage.py', 'no11_manual_reconnect_review.py'):
            with self.subTest(source=name):
                source = Path(manifest['packageDir']) / name
                original = source.read_bytes()
                source.write_bytes(original + b'\n# REHASHED_UNAPPROVED_REPLACEMENT\n')
                changed = deepcopy(manifest)
                changed['files'][name] = sha(source.read_bytes())
                put(path, changed)
                with self.assertRaises(ValueError):
                    retry.verify_manifest(path, now=NOW)
                source.write_bytes(original)
                path.write_bytes(original_manifest)

    def test_native_operator_recognizes_explicit_controller_delegation(self):
        manifest, _ = self.staged()
        wrapper = Path(manifest['controllerScript']).read_text()
        self.assertIn('--operator-approved-broker-live', wrapper)
        self.assertIn('allow_explicit_live=allow_explicit_live', wrapper)
        self.assertIn('core.controller_main', wrapper)

    def test_claim_requires_explicit_approval_and_is_permanent_once(self):
        manifest, path = self.staged()
        evidence = self.evidence()
        claim_path = Path(manifest['plan']['claimFile'])
        preserved = {self.f[key]: self.f[key].read_bytes()
                     for key in ('marker', 'preopen', 'preopenClaim', 'bootstrap', 'broker', 'failure')}
        with self.assertRaises(ValueError):
            retry.claim(path, *evidence, operator_approved=False, now=NOW)
        self.assertFalse(claim_path.exists())
        receipt = retry.claim(path, *evidence, operator_approved=True, now=NOW)
        self.assertEqual(receipt['status'], 'CLAIMED_ONCE')
        self.assertFalse(receipt['orderTransmission'])
        original_claim = claim_path.read_bytes()
        self.assertEqual(retry.verify_claim(path, now=NOW)['plan'], manifest['plan'])
        with self.assertRaises((ValueError, FileExistsError)):
            retry.claim(path, *evidence, operator_approved=True, now=NOW)
        self.assertEqual(claim_path.read_bytes(), original_claim)
        for source, raw in preserved.items():
            self.assertEqual(source.read_bytes(), raw)

    def test_missing_or_nonzero_worker_proof_cannot_claim(self):
        manifest, path = self.staged()
        observed, processes, physical = self.evidence()
        original = json.loads(processes.read_bytes())
        for field, value in (('enumerationSucceeded', False), ('matchingWorkers', 1),
                             ('unreadableWorkers', 1), ('oneClickProcesses', 1),
                             ('matchingWorkers', False)):
            with self.subTest(field=field, value=value):
                changed = dict(original)
                changed[field] = value
                put(processes, changed)
                with self.assertRaises(ValueError):
                    retry.claim(path, observed, processes, physical, operator_approved=True, now=NOW)
                self.assertFalse(Path(manifest['plan']['claimFile']).exists())

    def test_changed_excel_controls_or_physical_identity_cannot_claim(self):
        manifest, path = self.staged()
        observed, processes, physical = self.evidence()
        original = json.loads(physical.read_bytes())
        for field, value in (('registeredThreeBooksVerified', False), ('controlCellsVerified', False),
                             ('triggerZero', False), ('excelPid', 9999), ('excelHwnd', 8888),
                             ('rssSessionKey', '0' * 64)):
            with self.subTest(field=field):
                changed = dict(original)
                changed[field] = value
                put(physical, changed)
                with self.assertRaises(ValueError):
                    retry.claim(path, observed, processes, physical, operator_approved=True, now=NOW)
                self.assertFalse(Path(manifest['plan']['claimFile']).exists())

    def test_claim_evidence_cannot_change_or_expire_before_native_entry(self):
        manifest, path = self.staged()
        evidence = self.evidence()
        retry.claim(path, *evidence, operator_approved=True, now=NOW)
        for proof in evidence:
            with self.subTest(proof=proof.name):
                original = proof.read_bytes()
                proof.write_bytes(original + b' ')
                with self.assertRaises(ValueError):
                    retry.verify_claim(path, now=NOW)
                proof.write_bytes(original)
        with self.assertRaises(ValueError):
            retry.verify_claim(path, now=NOW + timedelta(seconds=91))
        self.assertTrue(Path(manifest['plan']['claimFile']).exists())

    def test_live_entry_refuses_missing_windows_or_approval_before_native_import(self):
        _, path = self.staged()
        with patch.object(retry, 'os', SimpleNamespace(name='posix')):
            with self.assertRaisesRegex(ValueError, 'WINDOWS_LIVE_REQUIRED'):
                retry.controller_entry(path, ['--config', str(self.f['bootstrap']),
                                              '--operator-approved-broker-live'])
        with patch.object(retry, 'os', SimpleNamespace(name='nt')):
            with self.assertRaisesRegex(ValueError, 'OPERATOR_LIVE_APPROVAL_REQUIRED'):
                retry.controller_entry(path, ['--config', str(self.f['bootstrap'])])
        self.assertFalse((path.parent / 'controller-entry.claimed').exists())

    def test_approved_live_entry_delegates_to_native_controller_only_once(self):
        manifest, path = self.staged()
        retry.claim(path, *self.evidence(), operator_approved=True, now=NOW)
        raw_config = {'sessionDate': DAY, 'offlineFixture': True}
        approved_config = object()
        bootstrap = SimpleNamespace(
            load_json=Mock(return_value=(raw_config, b'OFFLINE_FIXTURE')),
            validate_config=Mock(return_value=approved_config),
        )
        loader = SimpleNamespace(exec_module=Mock())
        spec = SimpleNamespace(loader=loader)
        importer = SimpleNamespace(util=SimpleNamespace(
            spec_from_file_location=Mock(return_value=spec),
            module_from_spec=Mock(return_value=bootstrap),
        ))
        controller = SimpleNamespace(__file__=manifest['plan']['controllerSource'],
                                     execute=Mock())
        windows = SimpleNamespace(name='nt', path=os.path, fsync=os.fsync, getpid=os.getpid)
        argv = ['--config', str(self.f['bootstrap']), '--operator-approved-broker-live']
        with patch.object(retry, 'os', windows), \
                patch.object(retry, 'clock', return_value=NOW), \
                patch.object(retry, 'importlib', importer), \
                patch.object(retry.sys, 'path', list(sys.path)), \
                patch.dict(sys.modules, {'no11_received_session_controller': controller}):
            retry.controller_entry(path, argv)
            controller.execute.assert_called_once_with(approved_config, bootstrap,
                                                       allow_explicit_live=True)
            bootstrap.load_json.assert_called_once_with(self.f['bootstrap'], 100_000)
            bootstrap.validate_config.assert_called_once_with(raw_config,
                                                               allow_explicit_live=True)
            self.assertEqual(bootstrap.HERE, self.f['engine'] / 'tools')
            self.assertEqual(bootstrap.WINDOWS, self.f['engine'] / 'windows')
            entry = path.parent / 'controller-entry.claimed'
            original_entry = entry.read_bytes()
            with self.assertRaises(FileExistsError):
                retry.controller_entry(path, argv)
            self.assertEqual(entry.read_bytes(), original_entry)
            self.assertEqual(controller.execute.call_count, 1)
            loader.exec_module.assert_called_once_with(bootstrap)


if __name__ == '__main__':
    unittest.main(verbosity=2)
