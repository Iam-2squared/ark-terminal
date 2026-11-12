"""Offline synthetic tests only: real SQLite ledger, no broker/Excel/PC I/O."""
from __future__ import annotations

from copy import deepcopy
import ast
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / 'no12-prebuy-causal-runtime-20261011/tools'
sys.path.insert(0, str(TOOLS))
import no11_broker_execution_ledger as ledger
import no11_capital_decision_audit as audit
import no11_operational_hardening as hardening
import no11_oneclick_display_v2 as display
import install_no11_oneclick_display_v2 as old
import install_no11_oneclick_display_overlay_compat as overlay
import no11_nightly_resume as n
import test_no11_oneclick_display_v2 as fixtures
import test_no11_oneclick_display_overlay_compat as overlay_fixtures

DAY = '2026-11-12'
AT = DAY + 'T10:30:40+09:00'


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def timestamp(value, day):
    result = datetime.fromisoformat(value)
    if result.date().isoformat() != day or result.utcoffset().total_seconds() != 32400:
        raise ValueError('NO11_TEST_SESSION')
    return result


TIME = SimpleNamespace(digest=digest, timestamp=timestamp, minute=lambda dt: dt.hour * 60 + dt.minute)


def require(ok, code):
    if not ok:
        raise ValueError('NO11_BROKER_SERVICE_' + code)


def row(key='a', admitted=True, clock='10:30:25'):
    return {'candidateId': key * 64, 'admission': admitted,
            'decisionAtJst': DAY + 'T' + clock + '+09:00'}


def calculation(rows, *, quantity=100, reject=None):
    result = {'allocations': [], 'intents': [], 'rejected': []}
    for r in rows:
        if not r['admission']:
            continue
        key = r['candidateId']
        if reject:
            result['rejected'].append({'entry_id': key, 'reason': reject})
        else:
            result['allocations'].append({'entry_id': key, 'quantity': quantity})
            if quantity:
                result['intents'].append({'entryId': key, 'quantity': quantity})
    return result


class DecisionAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.database = Path(self.tmp.name) / 'broker.sqlite'
        self.config = {'schemaId': ledger.CONFIG_SCHEMA, 'sessionDate': DAY,
                       'account': '一般', 'evidenceMode': 'BROKER_OBSERVATION',
                       'allocatedCashJpy': '1000000', 'externalSymbols': [],
                       'maxSymbols': 3, 'lotSize': 100,
                       'productionReady': False, 'orderTransmission': False}
        self.book = ledger.BrokerExecutionLedger(self.database, self.config)
        self.addCleanup(lambda: self.book.close())
        self.submit = Mock()
        self.service = SimpleNamespace(book=self.book, session=DAY, arrival={},
            _capital_input=lambda quotes, at: {}, clock=lambda: AT,
            submit_intents=self.submit, last_decision=None)
        self.decisions = SimpleNamespace(calculate_capital=Mock(
            side_effect=lambda batch, account, arrival: calculation(batch['results'])))

    def fund(self, rows, at=AT):
        return audit.fund_with_audit(self.service, {'results': rows}, {}, at,
            time_api=TIME, decisions=self.decisions, require=require)

    def records(self):
        records = []
        for payload, in self.book.db.execute('SELECT payload FROM broker_events ORDER BY seq'):
            event = json.loads(payload)
            if event.get('name', '').startswith(audit.PREFIX) and event['name'] != audit.LATEST:
                records.append(event['value'])
        return records

    def test_first_rejection_survives_later_empty_result(self):
        self.decisions.calculate_capital.side_effect = lambda b, a, x: calculation(b['results'], reject='ENTRY_BLOCKED_OR_PENDING')
        self.fund([row()])
        self.fund([row(), row('b', False, '10:41:24')], DAY + 'T10:41:25+09:00')
        saved = self.records()
        self.assertEqual(len(saved), 2)
        self.assertEqual(saved[0]['evaluatedAtJst'], AT)
        self.assertEqual(saved[0]['candidates'][0]['disposition'], 'CAPITAL_REJECTED')
        self.assertEqual(saved[0]['candidates'][0]['rejectionReason'], 'ENTRY_BLOCKED_OR_PENDING')
        self.assertEqual(saved[1]['candidates'][0]['disposition'], 'H235_NOT_ADMITTED')
        self.assertEqual(self.service.last_decision, {'allocations': [], 'intents': [], 'rejected': []})

    def test_same_minute_rule_preserved_and_boundary_skip_is_explained(self):
        self.fund([row(clock='10:30:59')], DAY + 'T10:31:00+09:00')
        self.decisions.calculate_capital.assert_not_called()
        self.submit.assert_not_called()
        item = self.records()[0]['candidates'][0]
        self.assertEqual(item['disposition'], 'SKIPPED_MINUTE_BOUNDARY')
        self.assertEqual(item['ageSeconds'], 1)
        self.assertTrue(item['within90Seconds'])
        self.assertFalse(item['sameMinute'])
        self.assertIn('a' * 64, self.book.source_checkpoint('capital.consumed'))

    def test_zero_quantity_distinguished_from_rejection_and_no_signal(self):
        self.decisions.calculate_capital.side_effect = lambda b, a, x: calculation(b['results'], quantity=0)
        self.fund([row()])
        item = self.records()[0]['candidates'][0]
        self.assertEqual(item['disposition'], 'ALLOCATED_ZERO_QUANTITY')
        self.assertEqual(item['quantity'], 0)
        self.assertFalse(self.records()[0]['orderAcceptanceConfirmed'])

    def test_evidence_is_written_before_submission_and_repeat_never_resends(self):
        def submit(intents, at):
            self.assertEqual(self.records()[-1]['candidates'][0]['disposition'], 'BUY_INTENT_CREATED')
            self.assertIn('a' * 64, self.book.source_checkpoint('capital.consumed'))
        self.submit.side_effect = submit
        result = self.fund([row()])
        self.assertEqual(len(result['intents']), 1)
        self.assertIsNone(self.fund([row()]))
        self.assertEqual(self.submit.call_count, 1)
        self.assertEqual(len(self.records()), 1)

    def test_no_reconstruction_or_replay_for_legacy_consumed_candidates(self):
        r = row()
        self.book.checkpoint_source('capital.consumed', {r['candidateId']: digest(r)}, AT)
        before = self.book.snapshot(AT)['eventSeq']
        self.assertIsNone(self.fund([r]))
        self.assertEqual(self.book.snapshot(AT)['eventSeq'], before)
        self.assertEqual(self.records(), [])
        self.submit.assert_not_called()

    def test_future_and_changed_candidates_fail_without_fabricating_history(self):
        with self.assertRaisesRegex(ValueError, 'CANDIDATE_FROM_FUTURE'):
            self.fund([row(clock='10:31:00')])
        self.assertEqual(self.records(), [])
        self.fund([row()])
        altered = row(admitted=False)
        with self.assertRaisesRegex(ValueError, 'CANDIDATE_CHANGED'):
            self.fund([altered])
        self.assertEqual(len(self.records()), 1)

    def test_audit_write_failure_prevents_consumption_and_submission(self):
        with patch.object(self.book, 'checkpoint_source', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                self.fund([row()])
        self.assertIsNone(self.book.source_checkpoint('capital.consumed'))
        self.submit.assert_not_called()

    def test_calculation_exception_is_redacted_and_does_not_submit(self):
        self.decisions.calculate_capital.side_effect = ValueError('private-secret-path')
        with self.assertRaisesRegex(ValueError, 'private-secret-path'):
            self.fund([row()])
        saved = self.records()[0]
        self.assertEqual(saved['errorCode'], 'UNCLASSIFIED_REDACTED')
        self.assertNotIn('private-secret-path', json.dumps(saved))
        self.assertIsNone(self.book.source_checkpoint('capital.consumed'))
        self.submit.assert_not_called()

    def test_event_chain_survives_reopen_without_reissuing_candidate(self):
        self.fund([row()])
        self.book.close()
        self.book = ledger.BrokerExecutionLedger(self.database, self.config)
        self.service.book = self.book
        self.assertEqual(len(self.records()), 1)
        self.assertIsNone(self.fund([row()]))
        self.assertEqual(self.submit.call_count, 1)

    def test_native_results_and_submissions_unchanged_for_supported_cases(self):
        # Execute the original method itself with the same inputs and mocks.
        namespace = {'need': require, 'h': TIME, 'decisions': self.decisions}
        exec('class Native:\n' + hardening.OLD_FUND, namespace)
        for qty, rejection, admitted in ((100, None, True), (0, None, True),
                                         (0, 'MAX_POSITION_CAP', True), (0, None, False)):
            with self.subTest(qty=qty, rejection=rejection, admitted=admitted):
                self.decisions.calculate_capital.side_effect = lambda b, a, x: calculation(b['results'], quantity=qty, reject=rejection)
                native_book = SimpleNamespace(source_checkpoint=lambda key: None, checkpoint_source=Mock())
                native_submit = Mock()
                native = SimpleNamespace(book=native_book, session=DAY, arrival={},
                    _capital_input=lambda q, at: {}, clock=lambda: AT,
                    submit_intents=native_submit, last_decision=None)
                r = row(str(qty + len(self.records()))[-1], admitted)
                expected = namespace['Native'].fund(native, {'results': [r]}, {}, AT)
                # Use isolated candidate identity for each execution.
                r['candidateId'] = digest([qty, rejection, admitted])
                expected = namespace['Native'].fund(native, {'results': [r]}, {}, AT)
                actual = self.fund([r])
                self.assertEqual(actual, expected)
                self.assertEqual(self.submit.call_args, native_submit.call_args)


class NodeTickFailureEvidenceTests(unittest.TestCase):
    """Run the derived native run_tick code with a fake, non-trading Node child."""

    def pristine_source(self):
        raw = ((TOOLS / 'no11_received_pipeline_service.py').read_bytes()
               .decode('utf-8-sig').replace('\r\n', '\n').encode('utf-8'))
        # CI stages the reviewed native edit BEFORE invoking this test suite;
        # local tests may instead run against the original untouched source.
        old = hardening.OLD_NODE_FAILURE.encode('utf-8')
        new = hardening.NEW_NODE_FAILURE.encode('utf-8')
        if raw.count(new) == 1:
            raw = raw.replace(new, old, 1)
        self.assertEqual(raw.count(old), 1)
        return raw

    def invoke(self, stderr, *, stdout='', exit_code=2, fail_evidence=False):
        source = self.pristine_source()
        generated = hardening.pipeline_node(source)
        parsed = ast.parse(generated)
        fn = next(n for n in parsed.body
                  if isinstance(n, ast.FunctionDef) and n.name == 'run_tick')
        send = Mock(return_value=SimpleNamespace(
            returncode=exit_code, stderr=stderr, stdout=stdout))
        atomic = Mock(side_effect=[None, OSError('disk full')] if fail_evidence else None)
        ns = {
            'Path': Path, 'TICK': Path('offline-no-node.mjs'),
            'subprocess': SimpleNamespace(run=send), 'atomic_private': atomic,
            'os': os, 're': re, 'hashlib': hashlib,
            'now_jst': lambda: DAY + 'T12:53:32+09:00',
            'need': require
        }
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<derived-run-tick>', 'exec'), ns)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            try:
                value = ns['run_tick']({'orderTransmission': False}, root)
                outcome = ('RETURNED', value)
            except ValueError as exc:
                outcome = ('RAISED', str(exc))
        return outcome, send, atomic

    def test_generic_node_failure_is_persisted_without_private_stderr(self):
        raw = 'Error: secret-account-path and exception details\n    at secret.js:4:2\n'
        (kind, code), child, writes = self.invoke(raw, stdout='broker-private-lines')
        self.assertEqual((kind, code), ('RAISED', 'NO11_SERVICE_NODE_TICK_FAILED'))
        self.assertEqual(writes.call_count, 2)
        path, record = writes.call_args.args
        self.assertEqual(path.name[:18], 'node-tick-failure-')
        self.assertEqual(record['schemaId'], 'ARK_NO11_NODE_TICK_FAILURE_EVIDENCE_V1')
        self.assertEqual(record['returnCode'], 2)
        self.assertEqual(record['stderrBytes'], len(raw.encode()))
        self.assertEqual(record['stderrSha256'], hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(record['stdoutSha256'], hashlib.sha256(b'broker-private-lines').hexdigest())
        self.assertEqual(record['stderrShape'], 'OTHER')
        self.assertEqual(record['safeCodeLines'], [])
        self.assertFalse(record['rawErrorStored'])
        self.assertFalse(record['orderTransmission'])
        self.assertNotIn('secret-account-path', json.dumps(record))
        child.assert_called_once()

    def test_empty_node_stderr_is_preserved_as_unexplained(self):
        (kind, code), _, writes = self.invoke('', exit_code=3221225477)
        self.assertEqual((kind, code), ('RAISED', 'NO11_SERVICE_NODE_TICK_FAILED'))
        record = writes.call_args.args[1]
        self.assertEqual(record['stderrShape'], 'EMPTY')
        self.assertEqual(record['returnCode'], 3221225477)
        self.assertEqual(record['stderrBytes'], 0)

    def test_known_error_code_preserves_original_failure_semantics(self):
        known = 'NO11_PIPELINE_ACCEPTED_CAPTURE_REMOVED\n'
        (kind, code), _, writes = self.invoke(known)
        self.assertEqual((kind, code), ('RAISED', known.strip()))
        self.assertEqual(writes.call_args.args[1]['stderrShape'], 'SINGLE_SAFE_CODE')
        self.assertEqual(writes.call_args.args[1]['safeCodeLines'], [known.strip()])

    def test_warning_plus_safe_line_is_audited_but_still_fails_closed(self):
        raw = 'node warning: runtime context\nNO11_PIPELINE_CAPTURE_LIMIT\n'
        (kind, code), _, writes = self.invoke(raw)
        self.assertEqual((kind, code), ('RAISED', 'NO11_SERVICE_NODE_TICK_FAILED'))
        self.assertEqual(writes.call_args.args[1]['safeCodeLines'], ['NO11_PIPELINE_CAPTURE_LIMIT'])

    def test_native_capture_in_progress_exception_still_skips_without_record(self):
        (kind, value), _, writes = self.invoke('NO11_PIPELINE_CAPTURE_WRITE_IN_PROGRESS')
        self.assertEqual((kind, value), ('RETURNED', None))
        self.assertEqual(writes.call_count, 1)

    def test_failure_to_persist_evidence_never_silently_continues(self):
        source = self.pristine_source()
        generated = hardening.pipeline_node(source)
        self.assertNotEqual(generated, source)
        self.assertIn(b'NO11_SERVICE_NODE_TICK_FAILED', generated)
        self.assertIn(b"'brokerStateChanged': False", generated)
        self.assertEqual(len(generated.splitlines()) - len(source.splitlines()), 18)
        with self.assertRaisesRegex(OSError, 'disk full'):
            self.invoke('runtime exited unexpectedly', fail_evidence=True)


class DisplayChainTests(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.InstallTests('test_audit_is_readonly_and_does_not_run_processes')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.case.launcher.write_bytes(overlay_fixtures.make_source())
        with patch.object(old, 'gate'), patch.object(old, 'parse_launcher'):
            old.install(self.case.store, apply=True)
            overlay.install(self.case.store, apply=True)

    def test_both_verifiers_accept_the_proven_overlay_without_rewriting_journals(self):
        paths = [self.case.store / old.JOURNAL, self.case.store / overlay.JOURNAL]
        before = [p.read_bytes() for p in paths]
        self.assertEqual(old.install(self.case.store), 'ALREADY_APPLIED')
        self.assertEqual(overlay.install(self.case.store), 'ALREADY_APPLIED')
        self.assertEqual([p.read_bytes() for p in paths], before)

    def test_overlay_verifier_rejects_missing_display_sidecar(self):
        (self.case.home / old.DISPLAY).unlink()
        with self.assertRaises(ValueError):
            overlay.install(self.case.store)
        with self.assertRaises(ValueError):
            old.install(self.case.store)

    def test_overlay_verifier_rejects_changed_contract(self):
        (self.case.home / old.CONTRACT).write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            overlay.install(self.case.store)

    def test_overlay_verifier_rejects_changed_display_bytes(self):
        path = self.case.home / old.DISPLAY
        path.write_bytes(path.read_bytes() + b'# changed\n')
        with self.assertRaises(ValueError):
            overlay.install(self.case.store)

    def test_old_failure_and_closed_newer_attempt_is_not_called_current_failure(self):
        root = self.case.f['root'] / 'test-private'
        root.mkdir()
        run = root / ('session-' + DAY + '-' + 'a' * 32)
        run.mkdir()
        fixtures.put(root / ('received-session-' + DAY + '.active.json'),
                     {'schemaId': 'ARK_NO11_RECEIVED_ACTIVE_RUN_V1', 'sessionDate': DAY, 'runRoot': str(run)})
        boot = fixtures.put(root / 'config.json', {'privateRoot': str(root)})
        fail = fixtures.put(run / 'controller-failure.json', {'reason': 'NO11_BROKER_SOURCE_UNAVAILABLE'})
        os.utime(fail, ns=(1000000000, 1000000000))
        fixtures.put(run / 'attempt-0002/attempt.json', {'status': 'CLOSED'})
        result = display.run_evidence({'bootstrapConfigFile': str(boot)}, DAY)
        self.assertEqual(result['state'], 'FAILURE_SCOPE_UNVERIFIED')
        out = fixtures.presentation(run=result)
        self.assertNotIn('TRADING STOPPED', out['text'])
        self.assertIn('停止理由要確認', out['text'])
        self.assertFalse(out['liveVerified'])

    def test_preopen_overlay_delta_preserves_all_permission_lines_and_callbacks(self):
        before = self.case.launcher.read_bytes()
        after = hardening.launcher_preopen(before)
        for token in (b'$trade.Enabled=', b'$nightly.Enabled=', b'$review.Enabled='):
            self.assertEqual([x for x in before.splitlines() if token in x],
                             [x for x in after.splitlines() if token in x])
        self.assertEqual(before.split(b'$refresh.Add_Click')[1], after.split(b'$refresh.Add_Click')[1])
        self.assertIn(b"if($view.phase -ceq 'PREOPEN')", after)
        with self.assertRaises(ValueError):
            hardening.launcher_preopen(after)


if __name__ == '__main__':
    unittest.main(verbosity=2)
