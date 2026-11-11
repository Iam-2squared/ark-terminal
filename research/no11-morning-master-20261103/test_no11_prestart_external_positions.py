"""Offline prestart holdings regressions; no Excel, broker or LIVE invocation."""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_no11_prestart_source_retry as fixtures

retry = fixtures.retry
NOW = fixtures.NOW
DAY = fixtures.DAY


def positions_observation(fixture, at=NOW):
    value = fixtures.observation(fixture['transport'], at)
    value['schemaId'] = 'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1'
    value['productionReady'] = False
    rows = [
        {'symbol': '1111', 'account': '一般', 'quantity': 100, 'orderQuantity': 0},
        {'symbol': '2222', 'account': '特定', 'quantity': 200, 'orderQuantity': 0},
    ]
    value['snapshot']['positions'] = deepcopy(rows)
    value['brokerObservation']['positions'] = deepcopy(rows)
    return value


class ExternalPositionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = fixtures.fixture(Path(self.temp.name))
        self.helper = fixtures.PrestartRetryTests(
            'test_exact_failed_before_registration_is_eligible_without_changing_originals')
        self.helper.f = self.f

    def test_two_holdings_pass_without_erasing_or_adopting_observation(self):
        plan = retry.audit(self.f['store'], now=NOW)
        observed = positions_observation(self.f)
        before = deepcopy(observed)
        result = retry.audit_broker(plan, observed, now=NOW)
        self.assertEqual(result['brokerPositions'], 2)
        self.assertEqual(result['brokerOrders'], 0)
        self.assertEqual(result['brokerExecutions'], 0)
        self.assertEqual(result['rssOrderIds'], 0)
        self.assertFalse(result['accountPositionsAdoptedAsArk'])
        self.assertFalse(result['orderTransmission'])
        self.assertEqual(observed, before)
        self.assertFalse(Path(plan['claimFile']).exists())

    def test_holdings_claim_pins_full_observation_and_preserves_all_originals(self):
        original = {p: p.read_bytes() for p in self.f['root'].rglob('*') if p.is_file()}
        manifest, path = self.helper.staged()
        observed, process, physical = self.helper.evidence()
        fixtures.put(observed, positions_observation(self.f))
        raw = observed.read_bytes()
        result = retry.claim(path, observed, process, physical,
                             operator_approved=True, now=NOW)
        self.assertEqual(result['status'], 'CLAIMED_ONCE')
        self.assertEqual(retry.verify_claim(path, now=NOW)['plan'], manifest['plan'])
        self.assertEqual(observed.read_bytes(), raw)
        for p, before in original.items():
            self.assertEqual(p.read_bytes(), before)
        self.assertFalse((path.parent / 'controller-entry.claimed').exists())
        changed = positions_observation(self.f)
        changed['brokerObservation']['positions'][0]['quantity'] = 200
        changed['snapshot']['positions'][0]['quantity'] = 200
        fixtures.put(observed, changed)
        with self.assertRaisesRegex(ValueError, 'CLAIM_EVIDENCE_CHANGED'):
            retry.verify_claim(path, now=NOW)
        self.assertTrue(Path(manifest['plan']['claimFile']).exists())

    def test_any_order_execution_or_id_still_prevents_fresh_start(self):
        plan = retry.audit(self.f['store'], now=NOW)
        for key in ('orders', 'executions', 'idRows'):
            with self.subTest(table=key):
                observed = positions_observation(self.f)
                observed['brokerObservation'][key] = [{'existing': 'unresolved activity'}]
                if key != 'idRows':
                    observed['snapshot'][key] = deepcopy(observed['brokerObservation'][key])
                with self.assertRaisesRegex(ValueError, 'BROKER_HISTORY_NOT_EMPTY'):
                    retry.audit_broker(plan, observed, now=NOW)

    def test_position_sell_reservation_is_not_silently_ignored(self):
        plan = retry.audit(self.f['store'], now=NOW)
        observed = positions_observation(self.f)
        for section in ('snapshot', 'brokerObservation'):
            observed[section]['positions'][0]['orderQuantity'] = 100
        with self.assertRaisesRegex(ValueError, 'BROKER_POSITION_ORDER_RESERVATION_PRESENT'):
            retry.audit_broker(plan, observed, now=NOW)

    def test_malformed_holdings_are_not_certified(self):
        plan = retry.audit(self.f['store'], now=NOW)
        for key, value in (('symbol', 'invalid'), ('account', ''), ('quantity', -1),
                           ('quantity', True), ('quantity', 0.5), ('quantity', None)):
            with self.subTest(key=key, value=value):
                observed = positions_observation(self.f)
                for section in ('snapshot', 'brokerObservation'):
                    observed[section]['positions'][0][key] = value
                with self.assertRaises(ValueError):
                    retry.audit_broker(plan, observed, now=NOW)

    def test_stale_or_inconsistent_holdings_still_block(self):
        plan = retry.audit(self.f['store'], now=NOW)
        observed = positions_observation(self.f, NOW - timedelta(seconds=91))
        with self.assertRaises(ValueError):
            retry.audit_broker(plan, observed, now=NOW)
        observed = positions_observation(self.f)
        observed['snapshot']['positions'][0]['quantity'] = 1
        with self.assertRaises(ValueError):
            retry.audit_broker(plan, observed, now=NOW)

    def test_registered_ark_run_remains_ineligible_even_with_no_today_orders(self):
        (self.f['run'] / 'run-contract.json').write_bytes(b'EXISTING_ARK_RUN')
        with self.assertRaisesRegex(ValueError, 'RUN_HAS_REGISTERED_OR_UNVERIFIED_STATE'):
            retry.audit(self.f['store'], now=NOW)

    def test_original_service_excludes_holdings_and_refuses_personal_sell(self):
        # Execute the ACTUAL native methods, not a rewritten ownership algorithm.
        # Normalization/source-I/O and storage are mocked; no service constructor,
        # model, external subprocess, broker connection or dispatch is invoked.
        source = fixtures.ENGINE / 'tools/no11_broker_execution_service.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                   and n.name == 'BrokerExecution')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)
                   and n.name in ('observe_envelope', '_sell_safe')]
        self.assertEqual(len(methods), 2)
        state = {'orders': {}, 'positions': {}, 'commands': {}}
        checkpoints = {}
        def require(ok, code):
            if not ok:
                raise ValueError('NO11_BROKER_SERVICE_' + code)
        def save(key, value, at):
            checkpoints[key] = deepcopy(value)
        book = SimpleNamespace(
            snapshot=lambda at: deepcopy(state),
            source_checkpoint=lambda key: deepcopy(checkpoints.get(key)),
            checkpoint_source=save, observe_account=Mock(), apply_receipt=Mock())
        observed = positions_observation(self.f)
        normalized = deepcopy(observed['brokerObservation'])
        normalized['snapshotSha256'] = 'a' * 64
        normalized['buyingPower'] = 100000
        namespace = {
            'need': require, 'deepcopy': deepcopy, '__builtins__': __builtins__,
            'ERRORS': (ValueError, TypeError, KeyError, OSError, RuntimeError),
            'safe_reason': str,
            'json': __import__('json'),
            'attribution': SimpleNamespace(
                inspect_source=lambda *args: {'latchedIssues': []},
                symbol=lambda value: retry.review.symbol(value) + '.T'),
            'ledger': SimpleNamespace(TERMINAL=set(), ACCOUNT_SCHEMA='OFFLINE_ACCOUNT',
                                      digest=lambda value: 'b' * 64),
        }
        module = ast.Module(body=deepcopy(methods), type_ignores=[])
        ast.fix_missing_locations(module)
        exec(compile(module, str(source), 'exec'), namespace)
        service = SimpleNamespace(
            session=DAY, bridge=lambda request: deepcopy(normalized), book=book,
            source=None, config={'evidenceMode': 'BROKER_OBSERVATION',
                                 'ledger': {'account': '一般', 'externalSymbols': []}},
            _fees=lambda: {}, halt_entry=Mock(), summary=lambda at: deepcopy(state),
            _source_current=lambda at: True)
        result = namespace['observe_envelope'](service, observed, NOW.isoformat())
        self.assertEqual(checkpoints['broker.externalSymbols'], ['1111.T', '2222.T'])
        self.assertEqual(result['positions'], {})
        self.assertEqual(result['orders'], {})
        self.assertEqual(result['commands'], {})
        book.apply_receipt.assert_not_called()
        service.halt_entry.assert_not_called()
        self.assertEqual(len(service.source['positions']), 2)
        for symbol in ('1111.T', '2222.T'):
            with self.subTest(symbol=symbol):
                with self.assertRaisesRegex(ValueError, 'PERSONAL_POSITION_CONFLICT'):
                    namespace['_sell_safe'](service, {
                        'symbol': symbol, 'side': 'SELL', 'account': '一般',
                        'quantity': 100}, NOW.isoformat())


if __name__ == '__main__':
    unittest.main(verbosity=2)
