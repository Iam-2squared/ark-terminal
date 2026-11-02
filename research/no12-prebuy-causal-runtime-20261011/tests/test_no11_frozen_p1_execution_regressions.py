"""Regression coverage for decimal funding and received execution boundaries.

All prices, account balances and model files here are synthetic. Frozen source
code executes unchanged; these tests neither connect to RSS nor place orders.
"""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_h235_capital_v5_shadow as cap
import no11_h235_asof_forward_shadow as h
import no11_shadow_portfolio as ledger
import test_no11_frozen_p1_h235_capital as funding_fixture
import test_no11_frozen_p1_execution_service as execution_fixture

at = execution_fixture.at


class DecimalFundingRegressions(unittest.TestCase):
    def setUp(self):
        self.f = funding_fixture.FrozenV5BindingTests()
        self.f.setUp()

    def tearDown(self):
        self.f.tearDown()

    def test_decimal_text_boundary_preserves_inputs_without_rounding(self):
        self.f.batch['results'][0]['raw_reference'] = 101.70000000000002
        before = deepcopy(self.f.batch)
        req = cap.build_request(self.f.batch, self.f.scenario, self.f.arrival)
        self.assertEqual(req['preorderedCandidates'][0]['raw_reference'], '101.70000000000002')
        self.assertEqual(self.f.batch, before)

    def test_actual_frozen_allocator_accepts_non_binary_exact_decimal_prices(self):
        for price in (0.1, 12.3, 100.1, 101.7, 101.70000000000002, 101.25, 1500.1):
            with self.subTest(price=price):
                self.f.batch['results'][0]['raw_reference'] = price
                result = cap.fund_shadow(self.f.batch, self.f.scenario, self.f.arrival)
                self.assertEqual(result['capital']['fundedCount'], 1)
                item = result['capital']['allocations'][0]
                self.assertEqual(Decimal(item['debitJpy']),
                                 Decimal(str(price)) * Decimal('1.0005') * item['quantity'])
                self.assertFalse(result['orderTransmission'])

    def test_old_float_request_reproduces_the_original_debit_mismatch(self):
        self.f.batch['results'][0]['raw_reference'] = 101.7
        req = cap.build_request(self.f.batch, self.f.scenario, self.f.arrival)
        req['preorderedCandidates'][0]['raw_reference'] = 101.7
        with self.assertRaisesRegex(Exception, '^FROZEN_ALLOCATOR_DEBIT_MISMATCH$'):
            cap.native_v5.run_request(req)


class ReceivedBoundaryRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = execution_fixture.features.load_feature_runtime(h.ROOT)

    def setUp(self):
        # Reuse fixture construction, not inherited tests (no duplicated counts).
        self.f = execution_fixture.ReceivedExecutionTests()
        self.f.runtime = self.runtime
        self.f.setUp()

    def tearDown(self):
        self.f.tearDown()

    def pending_buy(self):
        self.f.runner.advance(self.f.feed, self.f.inference, at(575, 12))
        return next(iter(self.f.runner.portfolio.state()['orders']))

    def held_buy(self):
        oid = self.pending_buy()
        self.f.append_bar(575, self.f.feed['rows'][-1]['C'] - .05)
        self.f.runner.advance(self.f.feed, self.f.inference, at(576, 12))
        self.assertEqual(self.f.runner.summary()['positionCount'], 1)
        return oid

    def test_eod_requests_cancel_without_releasing_cash_or_inventing_fill(self):
        oid = self.pending_buy()
        reserve = self.f.runner.summary()['reservedCashJpy']
        result = self.f.runner.heartbeat(at(920))
        self.assertEqual(result['reservedCashJpy'], reserve)
        self.assertEqual(result['cashJpy'], '1000000')
        self.assertEqual(result['positionCount'], 0)
        self.assertEqual(result['pendingOrders'], 1)
        self.assertEqual(self.f.runner.portfolio.state()['orders'][oid]['status'], 'CANCEL_REQUESTED')
        self.f.runner.heartbeat(at(920, 1))
        self.assertEqual(self.f.runner.summary()['reservedCashJpy'], reserve)

    def test_cheap_post_cutoff_quote_cannot_fill_a_pre_cutoff_buy(self):
        oid = self.pending_buy()
        self.f.append_bar(920, self.f.feed['rows'][-1]['C'] - .05)
        result = self.f.runner.advance(self.f.feed, self.f.inference, at(921, 12))
        self.assertEqual(result['positionCount'], 0)
        self.assertEqual(result['pendingOrders'], 0)
        self.assertEqual(result['cashJpy'], '1000000')
        self.assertEqual(self.f.runner.portfolio.state()['orders'][oid]['status'], 'CANCELLED')
        self.assertFalse(result['firstSellFillBuyHalt'])
        self.assertEqual(result['brokerTransmissions'], 0)

    def test_unknown_buy_remains_unknown_at_eod(self):
        oid = self.pending_buy()
        o = self.f.runner.portfolio.state()['orders'][oid]
        self.f.runner.portfolio.update({
            'schemaId': ledger.UPDATE, 'eventId': h.digest(['unknown-eod']),
            'orderId': oid, 'symbol': o['symbol'], 'side': 'BUY',
            'knownAtJst': at(576), 'cumulativeQuantity': 0,
            'cumulativeValueJpy': '0', 'status': 'UNKNOWN', 'syntheticOnly': True,
        }, at(576))
        self.f.append_bar(920, self.f.feed['rows'][-1]['C'] - .05)
        result = self.f.runner.advance(self.f.feed, self.f.inference, at(921, 12))
        self.assertEqual(self.f.runner.portfolio.state()['orders'][oid]['status'], 'UNKNOWN')
        self.assertTrue(result['reconciliationBlocked'])
        self.assertEqual(result['pendingOrders'], 1)
        self.assertEqual(result['positionCount'], 0)

    def test_late_receipt_does_not_make_pre_intent_close_a_post_intent_fill(self):
        self.pending_buy()
        quote = deepcopy(self.f.feed['rows'][-1])
        quote['knownAtJst'] = at(575, 20)
        before = self.f.runner.portfolio.state()
        self.f.runner._simulated_updates({quote['Code']: quote}, at(575, 30))
        self.assertEqual(self.f.runner.portfolio.state(), before)

    def test_h235_tamper_rejected_before_pending_fill_or_mark(self):
        self.pending_buy()
        self.f.append_bar(575, self.f.feed['rows'][-1]['C'] - .05)
        before = self.f.runner.portfolio.state()
        path = next(self.f.root.glob('h235-asof-*.json'))
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'H235_RESULT_HASH_CHANGED'):
            self.f.runner.advance(self.f.feed, self.f.inference, at(576, 12))
        self.assertEqual(self.f.runner.portfolio.state(), before)

    def test_held_prefix_change_rejected_before_new_mark_or_stream_push(self):
        self.held_buy()
        before = self.f.runner.portfolio.state()
        self.f.append_bar(576, self.f.feed['rows'][-1]['C'] + .1)
        self.f.feed['rows'][0]['Va'] += 1
        with self.assertRaisesRegex(ValueError, 'HELD_SOURCE_CHANGED'):
            self.f.runner.advance(self.f.feed, self.f.inference, at(577, 12))
        self.assertEqual(self.f.runner.portfolio.state(), before)
        self.assertEqual(self.f.runner.streams[execution_fixture.market.CODE].trace[-1]['state']['as_of'], 36)

    def test_held_prefix_removal_rejected_before_new_mark(self):
        self.held_buy()
        before = self.f.runner.portfolio.state()
        self.f.append_bar(576, self.f.feed['rows'][-1]['C'] + .1)
        self.f.feed['rows'].pop(0)
        with self.assertRaisesRegex(ValueError, 'HELD_SOURCE_REMOVED'):
            self.f.runner.advance(self.f.feed, self.f.inference, at(577, 12))
        self.assertEqual(self.f.runner.portfolio.state(), before)

    def test_malformed_result_hash_rejected_before_any_state_change(self):
        before = self.f.runner.portfolio.state()
        with self.assertRaisesRegex(ValueError, 'H235_RESULT_REQUIRED'):
            self.f.runner.advance(self.f.feed, {'h235PrivateResultSha256': '/' * 64}, at(575, 12))
        self.assertEqual(self.f.runner.portfolio.state(), before)


if __name__ == '__main__':
    unittest.main()
