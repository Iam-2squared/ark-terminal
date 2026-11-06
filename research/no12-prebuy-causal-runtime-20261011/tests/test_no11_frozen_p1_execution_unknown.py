"""Synthetic-only UNKNOWN/cancel/partial-fill races across EXIT and restart."""
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_h235_asof_forward_shadow as h
import no11_shadow_portfolio as ledger
import test_no11_frozen_p1_execution_service as fixture

at = fixture.at


class UnknownOrderRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = fixture.features.load_feature_runtime(h.ROOT)

    def setUp(self):
        self.f = fixture.ReceivedExecutionTests()
        self.f.runtime = self.runtime
        self.f.setUp()
        self.f.runner.advance(self.f.feed, self.f.inference, at(575, 12))
        self.oid = next(iter(self.f.runner.portfolio.state()['orders']))

    def tearDown(self):
        self.f.tearDown()

    def update(self, quantity, status, clock):
        o = self.f.runner.portfolio.state()['orders'][self.oid]
        value = Decimal(o['unitReserve']) * quantity
        event = {'schemaId': ledger.UPDATE,
                 'eventId': h.digest([self.oid, quantity, status, clock]),
                 'orderId': self.oid, 'symbol': o['symbol'], 'side': 'BUY',
                 'knownAtJst': clock, 'cumulativeQuantity': quantity,
                 'cumulativeValueJpy': str(value), 'status': status,
                 'syntheticOnly': True}
        self.f.runner.portfolio.update(event, clock)

    def test_partial_unknown_survives_eod_and_sale_of_confirmed_quantity(self):
        self.update(100, 'UNKNOWN', at(575, 20))
        reserve = self.f.runner.summary()['reservedCashJpy']
        self.assertGreater(Decimal(reserve), 0)
        self.f.runner.heartbeat(at(920))
        state = self.f.runner.portfolio.state()
        self.assertEqual(state['orders'][self.oid]['status'], 'UNKNOWN')
        sell = next(o for o in state['orders'].values() if o['side'] == 'SELL')
        self.assertEqual(sell['quantity'], 100)
        self.f.append_bar(920, self.f.feed['rows'][-1]['C'] + .5)
        result = self.f.runner.advance(self.f.feed, self.f.inference, at(921, 12))
        self.assertEqual(result['positionCount'], 0)
        self.assertEqual(result['pendingOrders'], 1)
        self.assertEqual(result['reservedCashJpy'], reserve)
        self.assertTrue(result['firstSellFillBuyHalt'])
        self.assertTrue(result['reconciliationBlocked'])
        buy = self.f.runner.portfolio.state()['orders'][self.oid]
        self.assertEqual(buy['status'], 'UNKNOWN')
        self.assertEqual(buy['filled'], 100)
        self.assertEqual(result['brokerTransmissions'], 0)

    def test_incoming_unknown_overrides_cancel_requested_not_the_reverse(self):
        self.f.runner.portfolio.cancel(self.oid, at(575, 15))
        self.update(0, 'UNKNOWN', at(575, 20))
        before = self.f.runner.portfolio.state()
        self.assertEqual(before['orders'][self.oid]['status'], 'UNKNOWN')
        self.f.runner._simulated_updates({}, at(575, 30))
        self.assertEqual(self.f.runner.portfolio.state(), before)

    def test_local_cancel_request_cannot_resolve_unknown(self):
        self.update(0, 'UNKNOWN', at(575, 20))
        before = self.f.runner.portfolio.state()
        with self.assertRaisesRegex(ValueError, 'ORDER_RECONCILIATION_REQUIRED'):
            self.f.runner.portfolio.cancel(self.oid, at(575, 30))
        self.assertEqual(self.f.runner.portfolio.state(), before)

    def test_restart_keeps_partial_unknown_reserve_and_single_exit(self):
        self.update(100, 'UNKNOWN', at(575, 20))
        self.f.runner.heartbeat(at(920))
        before = self.f.runner.portfolio.state()
        self.f.runner.close()
        self.f.runner = fixture.wiring.ExecutionShadow(
            self.f.root, self.f.config, self.f.arrival, self.runtime,
            fixture.market.previous(), fixture.market.PRIOR)
        self.assertEqual(self.f.runner.portfolio.state(), before)
        result = self.f.runner.heartbeat(at(920, 10))
        self.assertEqual(result['sellIntentCount'], 1)
        self.assertEqual(result['pendingOrders'], 2)
        self.assertEqual(self.f.runner.portfolio.state()['orders'][self.oid]['status'], 'UNKNOWN')
        self.assertTrue(result['reconciliationBlocked'])

    def test_explicit_cancel_ack_does_not_automatically_clear_session_block(self):
        self.update(0, 'UNKNOWN', at(575, 20))
        self.update(0, 'CANCELLED', at(575, 30))
        result = self.f.runner.summary()
        self.assertEqual(result['pendingOrders'], 0)
        self.assertEqual(Decimal(result['reservedCashJpy']), 0)
        self.assertTrue(result['reconciliationBlocked'])
        self.assertFalse(result['orderTransmission'])


if __name__ == '__main__':
    unittest.main()
