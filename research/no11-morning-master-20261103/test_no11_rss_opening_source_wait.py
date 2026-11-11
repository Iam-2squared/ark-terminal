"""Offline tests: synthetic sources only; no Excel, orders or user files."""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import Mock

import no11_rss_opening_source_wait as candidate

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / 'no12-prebuy-causal-runtime-20261011'
ORIGINAL = HERE.parent / 'no11-rss-funding-live-20261103/no11_rss_buying_power.py'
AT = '2026-11-11T14:10:50.100000+09:00'
REASON = 'NO11_BROKER_ACCOUNT_CHANGED_DURING_CAPTURE'


class OpeningWaitTests(unittest.TestCase):
    def setUp(self):
        self.elapsed = 0.0
        self.messages = []
        self.config = {
            'sessionDate': '2026-11-11',
            'transport': {
                'expiresAtJst': '2026-11-11T15:30:00+09:00',
                'expectedExcelPid': 1234,
                'expectedExcelStartedAt': '2026-11-11T08:00:00.0000000+09:00',
                'rssSessionKey': 'a' * 64,
            },
        }
        self.source = {'excelSession': {
            'processId': 1234, 'startedAtUtc': '2026-11-10T23:00:00.0000000Z',
            'sessionKey': 'a' * 64}}
        self.normalizer = Mock(side_effect=self.normalize)
        self.reader = Mock(side_effect=lambda path: (self.envelope(), 'b' * 64))

    def envelope(self, *, unavailable=False, reason=REASON, sequence=2):
        raw = {'schemaId': 'ARK_NO11_BROKER_OBSERVATION_V1',
               'status': 'UNAVAILABLE' if unavailable else 'OBSERVED',
               'readOnly': True, 'productionReady': False, 'orderTransmission': False}
        if unavailable:
            raw['reason'] = reason
        return {'schemaId': 'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1',
                'runId': 'c' * 32, 'sequence': sequence, 'status': 'OBSERVED',
                'readOnly': True, 'productionReady': False, 'orderTransmission': False,
                'snapshot': {}, 'brokerObservation': raw}

    def normalize(self, envelope, day, at, bridge):
        if envelope['brokerObservation']['status'] != 'OBSERVED':
            raise ValueError('NO11_BROKER_SOURCE_UNAVAILABLE')
        return deepcopy(self.source)

    def sleep(self, duration):
        self.elapsed += duration

    def clock(self):
        return (datetime.fromisoformat(AT) + timedelta(seconds=self.elapsed)).isoformat()

    def call(self, **changes):
        options = dict(clock=self.clock, monotonic=lambda: self.elapsed,
                       sleep=self.sleep, diagnostic=self.messages.append,
                       timeout_seconds=0.5, poll_seconds=0.1)
        options.update(changes)
        return candidate.read_opening_source(
            self.config, AT, self.reader, Mock(), self.normalizer,
            lambda config: 'synthetic-observer.json', **options)

    def test_normal_sample_is_not_delayed(self):
        result = self.call()
        self.assertEqual(result[2], self.source)
        self.assertEqual(self.reader.call_count, 1)
        self.assertEqual(self.elapsed, 0)
        self.assertEqual(self.messages, [])

    def test_transient_read_retries_without_reusing_old_good_sample(self):
        first = self.envelope(unavailable=True, sequence=1)
        second = self.envelope()
        before = deepcopy((first, second))
        self.reader.side_effect = [(first, 'd' * 64), (second, 'e' * 64)]
        result = self.call()
        self.assertIs(result[0], second)
        self.assertEqual(result[1], 'e' * 64)
        self.assertEqual(result[3], self.clock())
        self.assertEqual((first, second), before)
        self.assertEqual(self.reader.call_count, 2)
        self.assertEqual(self.normalizer.call_count, 2)
        self.assertEqual(self.messages, ['NO11_RSS_OPENING_UNAVAILABLE_CAUSE=' + REASON])

    def test_persistent_unavailable_times_out(self):
        self.reader.side_effect = lambda path: (self.envelope(unavailable=True), 'b' * 64)
        with self.assertRaisesRegex(ValueError, 'SOURCE_WAIT_TIMEOUT'):
            self.call()
        self.assertLessEqual(self.reader.call_count, 6)

    def test_unclassified_identity_tail_or_schema_errors_never_retry(self):
        for reason in ('BROKER_SOURCE_UNAVAILABLE',
                       'NO11_BROKER_EXCEL_SESSION_CHANGED_DURING_CAPTURE',
                       'NO11_BROKER_TAIL_NOT_CERTIFIABLY_EMPTY',
                       'NO11_BROKER_ACCOUNT_BROKER_TABLE_MISMATCH'):
            with self.subTest(reason=reason):
                self.reader.reset_mock()
                self.reader.side_effect = lambda path: (self.envelope(unavailable=True, reason=reason), 'b' * 64)
                with self.assertRaisesRegex(ValueError, 'UNAVAILABLE_NOT_RETRYABLE'):
                    self.call()
                self.assertEqual(self.reader.call_count, 1)

    def test_private_error_text_is_redacted(self):
        self.reader.side_effect = lambda path: (self.envelope(unavailable=True, reason='password=PRIVATE'), 'b' * 64)
        with self.assertRaisesRegex(ValueError, 'UNCLASSIFIED_REDACTED') as raised:
            self.call()
        self.assertNotIn('PRIVATE', str(raised.exception) + ''.join(self.messages))

    def test_other_native_validation_failure_is_not_masked(self):
        for reason in ('NO11_BROKER_CAPTURE_CLOCK', 'NO11_BROKER_ACCOUNT_SNAPSHOT_MISMATCH',
                       'NO11_BROKER_EXCEL_SESSION_KEY', 'NO11_RSS_FUNDING_NORMALIZED_SOURCE_HASH'):
            with self.subTest(reason=reason):
                self.reader.reset_mock()
                self.normalizer.side_effect = ValueError(reason)
                with self.assertRaisesRegex(ValueError, '^' + reason + '$'):
                    self.call()
                self.assertEqual(self.reader.call_count, 1)

    def test_file_or_parser_error_is_not_retried(self):
        self.reader.side_effect = OSError('synthetic read failure')
        with self.assertRaises(OSError):
            self.call()
        self.assertEqual(self.reader.call_count, 1)

    def test_restarted_excel_or_reused_pid_is_rejected(self):
        for key, value in (('processId', 9999), ('sessionKey', 'e' * 64),
                           ('startedAtUtc', '2026-11-10T23:00:00.0000001Z')):
            with self.subTest(field=key):
                original = deepcopy(self.source)
                self.source['excelSession'][key] = value
                with self.assertRaisesRegex(ValueError, 'EXCEL_SESSION_CHANGED'):
                    self.call()
                self.source = original

    def test_cutoff_day_change_expiry_and_clock_reversal_stop_wait(self):
        for stamp in ('2026-11-11T15:20:00+09:00', '2026-11-12T09:00:00+09:00',
                      '2026-11-11T14:10:49+09:00'):
            with self.subTest(stamp=stamp):
                self.elapsed = 0
                self.reader.side_effect = [(self.envelope(unavailable=True, sequence=1), 'b' * 64),
                                           (self.envelope(), 'b' * 64)]
                with self.assertRaisesRegex(ValueError, 'ENTRY_WINDOW_CLOSED|CLOCK_REVERSED'):
                    self.call(clock=lambda: stamp)
        self.config['transport']['expiresAtJst'] = AT
        with self.assertRaisesRegex(ValueError, 'TRANSPORT_EXPIRED'):
            self.call()

    def test_observer_restart_or_nonadvancing_sequence_is_rejected(self):
        for field, value in (('runId', 'd' * 32), ('sequence', 0), ('sequence', 1)):
            with self.subTest(field=field, value=value):
                self.elapsed = 0
                next_value = self.envelope()
                next_value[field] = value
                self.reader.side_effect = [(self.envelope(unavailable=True, sequence=1), 'b' * 64),
                                           (next_value, 'b' * 64)]
                with self.assertRaisesRegex(ValueError, 'OBSERVER_CHANGED|OBSERVATION_NOT_ADVANCED'):
                    self.call()

    def test_bad_wait_parameters_are_rejected(self):
        for value in (-1, 0, float('inf'), float('nan'), True, 61):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'WAIT_BOUNDS'):
                    self.call(timeout_seconds=value)

    def test_transform_preserves_frozen_functions_and_windows_encodings(self):
        original = ORIGINAL.read_bytes().decode('utf-8-sig').replace('\r\n', '\n')
        for bom, newline in ((b'', '\n'), (b'', '\r\n'), (b'\xef\xbb\xbf', '\r\n')):
            raw = bom + original.replace('\n', newline).encode()
            result = candidate.transform(raw)
            self.assertTrue(result.startswith(bom))
            if newline == '\r\n':
                self.assertNotIn(b'\n', result.replace(b'\r\n', b''))
            old_tree = ast.parse(original)
            new_tree = ast.parse(result.decode('utf-8-sig'))
            old = {n.name: ast.dump(n) for n in old_tree.body if isinstance(n, ast.FunctionDef)}
            new = {n.name: ast.dump(n) for n in new_tree.body if isinstance(n, ast.FunctionDef)}
            self.assertEqual(set(new) - set(old), {'read_opening_source'})
            for name in set(old) - {'resolve_opening'}:
                self.assertEqual(old[name], new[name], name)
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_SOURCE'):
            candidate.transform((original + '# unexpected edit\n').encode())

    def test_actual_native_normalizer_and_funding_receipt_preserve_external_holdings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Load definitions only; never construct a ledger or a live service.
            old_path = list(sys.path)
            sys.path.insert(0, str(ENGINE / 'tools'))
            try:
                module = ModuleType('candidate_funding_offline')
                exec(compile(candidate.transform(ORIGINAL.read_bytes()).decode('utf-8-sig'),
                             'candidate_funding_offline.py', 'exec'), module.__dict__)
            finally:
                sys.path[:] = old_path
            js = '''
import {brokerExcelSessionKey} from SNAPSHOT_URI;
import {LOCKED_FLAGS} from LOCKED_URI;
const identity={processId:1234,startedAtUtc:'2026-11-10T23:00:00.0000000Z',accountWorkbookIdentity:'a'.repeat(64),orderIdWorkbookIdentity:'b'.repeat(64)};
identity.sessionKey=brokerExcelSessionKey(identity);
const rows=[{symbol:'1111',account:'一般',quantity:100},{symbol:'2222',account:'特定',quantity:200}];
const o={schemaId:'ARK_NO11_BROKER_OBSERVATION_V1',status:'OBSERVED',readOnly:true,productionReady:false,orderTransmission:false,capturedAt:'2026-11-11T14:10:49+09:00',captureCompletedAt:'2026-11-11T14:10:50+09:00',excelSession:identity,idRows:[],orders:[],executions:[],positions:rows,buyingPower:100000,sameSnapshotVerified:true,verificationBasis:'DOUBLE_READ_EQUAL_NOT_ATOMIC_FEED',actualFeedTimestampCertified:false,buyingPowerFreshnessCertified:false,cashScope:'ALL_CHANNELS_ALL_STATUSES_CASH_ONLY',completeTables:true,rowsTruncated:false};
const s={schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',mode:'READ_ONLY',source:'MARKETSPEED_II_RSS',safety:{...LOCKED_FLAGS},capturedAt:o.capturedAt,captureCompletedAt:o.captureCompletedAt,orders:[],executions:[],positions:rows,buyingPower:100000};
console.log(JSON.stringify({schemaId:'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1',runId:'c'.repeat(32),sequence:2,status:'OBSERVED',readOnly:true,productionReady:false,orderTransmission:false,brokerObservation:o,snapshot:s}));
'''
            js = js.replace('SNAPSHOT_URI', json.dumps((ENGINE / 'tools/no11_broker_snapshot.mjs').as_uri()))
            js = js.replace('LOCKED_URI', json.dumps((HERE.parents[1] / 'integration/no1-1-msii/runtime/locked_intent.mjs').as_uri()))
            done = subprocess.run(['node', '--input-type=module', '-e', js],
                                  capture_output=True, text=True, encoding='utf-8', check=True, timeout=10)
            observed = json.loads(done.stdout)
            self.config['transport']['rssSessionKey'] = observed['brokerObservation']['excelSession']['sessionKey']
            def bridge(request):
                reply = subprocess.run(['node', str(ENGINE / 'tools/no11_broker_bridge.mjs')],
                    input=json.dumps(request), capture_output=True, text=True, encoding='utf-8', timeout=10)
                if reply.returncode:
                    raise ValueError(reply.stderr.strip())
                return json.loads(reply.stdout)
            self.config.update(fundingPolicy='RSS_BUYING_POWER', evidenceMode='BROKER_OBSERVATION',
                orderTransmission=True, productionReady=False, feeCourse='ZERO',
                ledger={'sessionDate':'2026-11-11','account':'一般','allocatedCashJpy':'AUTO_RSS_BUYING_POWER',
                        'evidenceMode':'BROKER_OBSERVATION','maxSymbols':3,'lotSize':100,'externalSymbols':[]},
                orderTerms={'sor':True,'accountType':1,'accountTypeVerified':True,'orderType':'MARKET',
                            'timeInForce':'DAY','limitPrice':None},
                accountObservationFile=str(root / 'synthetic.json'))
            self.config['transport'].update(mode='LIVE', orderTransmission=True, operatorEnabled=True,
                                           approvedForSession=True, sessionDate='2026-11-11')
            first = deepcopy(observed)
            first['sequence'] = 1
            first['brokerObservation'].update(status='UNAVAILABLE', reason=REASON)
            remaining = [first, observed]
            writes = []
            def reader(path, limit=None):
                if str(path) == self.config['accountObservationFile']:
                    value = remaining.pop(0)
                    return value, hashlib.sha256(json.dumps(value).encode()).hexdigest()
                raw = Path(path).read_bytes()
                return json.loads(raw), hashlib.sha256(raw).hexdigest()
            def write_once(path, value):
                writes.append(path)
                with Path(path).open('xb') as stream:
                    stream.write(json.dumps(value, ensure_ascii=False).encode())
            native_wait = module.read_opening_source
            module.read_opening_source = lambda *args: native_wait(*args,
                clock=self.clock, monotonic=lambda:self.elapsed, sleep=self.sleep,
                diagnostic=self.messages.append, timeout_seconds=0.5, poll_seconds=0.1)
            db = root / 'broker-execution-2026-11-11.sqlite'
            allocation, proof, _ = module.resolve_opening(root, self.config, db, AT, reader, bridge, write_once)
            self.assertEqual(allocation['allocatedCashJpy'], '100000')
            self.assertEqual(allocation['externalSymbols'], ['1111.T', '2222.T'])
            self.assertFalse(db.exists())
            self.assertEqual(len(writes), 1)
            self.assertFalse(proof['orderTransmission'])
            # Reuse the pinned funding receipt. No new source read or cash reset.
            reused = module.resolve_opening(root, self.config, db, self.clock(), reader, bridge, write_once)
            self.assertEqual(reused[0], allocation)
            self.assertEqual(len(writes), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
