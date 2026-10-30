"""Native EXIT and durable order-state tests. All prices, cash and fills synthetic."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_h235_asof_forward_shadow as h
import no11_original_exit_shadow as ex
import no11_shadow_portfolio as ledger
import test_no11_frozen_p1_h235_asof as models

DAY = '2026-10-26'


def at(minute, seconds=0):
    return DAY + 'T%02d:%02d:%02d+09:00' % (minute // 60, minute % 60, seconds)


def trace_row(t, close='3.5', context=1, primary='RISE', segment='s1', observed=True,
              pivot=None, events=(), path_events=(), protected='0'):
    m = 540 + t
    return {'bar_end_minute': m, 'knownAtJst': at(m, 8),
      'state': {'as_of': t, 'observed_at': t if observed else None,
        'current_semantics_observed': observed, 'numeric_status': 'ACCEPTED' if observed else 'NOT_AVAILABLE',
        'context': context, 'context_established_at': 0, 'primary': primary,
        'activity': 'BALANCED' if primary == 'RANGE' else 'RUNNING', 'close_u': close,
        'protected_before': protected, 'protected_after_effective_next': protected,
        'protected_effective_from': 0, 'local_pivot_confirmed': pivot, 'events': list(events),
        'balance': {'established_at': t} if primary == 'RANGE' else None,
        '_structure_pivots': [], '_context_extreme': close, 'stop': {'count': 2}, 'leg_direction': 1},
      'path': {'Primary_or_null': primary if observed else None, 'causal_segment_id': segment,
        'run_id': primary + '-run', 'dwell_observed_bars': 5, 'scheduled_t': t, 'bar_end': at(m)},
      'path_events': [{'event_type': name} for name in path_events]}


def pivot(kind, x, t):
    return {'kind': kind, 'x': str(x), 'extremum_t': t, 'confirmed_at': t, 'generation_reason': 'DC_CONFIRMED'}


def prefix():
    return [trace_row(30, pivot=pivot('L', 0, 30)),
            trace_row(31, pivot=pivot('H', 3, 31)),
            trace_row(32, pivot=pivot('L', 1, 32)), trace_row(33)]


def config(root):
    return {'schemaId': ledger.CONFIG, 'sessionDate': DAY, 'initialCashJpy': '1000000',
            'externalSymbols': [], 'originalArrivalTable': str(root / 'arrival.json'),
            'fillPolicy': 'NEXT_FRESH_RECEIVED_CLOSE_SIMULATION', 'syntheticAccountOnly': True,
            'productionReady': False, 'orderTransmission': False}


def arrival():
    return {'8': {'minute_counts': {str(m): [0, 0, 0] for m in range(540, 920)},
                  'minute_bucket': {str(m): 'AM_SYNTHETIC' for m in range(540, 920)},
                  'training_session_N': 10, 'B_median': 1.1, 'B_p75': 1.2}}


class NativeExitTests(unittest.TestCase):
    def run_exit(self, rows, start=at(573), now=at(574, 12)):
        return ex.decide_received_exit(session=DAY, entry_at=start, trace=rows, evaluated_at=now)

    def test_original_guard_C_equality_boundary(self):
        r = self.run_exit(prefix() + [trace_row(34, close='.5', primary='PULLBACK')])
        self.assertEqual(r['intent']['reason'], 'LOCAL_UP_STRUCTURE_GUARD_BROKEN')
        self.assertTrue(r['originalStructuralV3Executed'])
        self.assertFalse(r['orderTransmission'])

    def test_original_A_has_priority_over_sharp_drop(self):
        r = self.run_exit(prefix() + [trace_row(34, close='-.5', context=-1, primary='SHARP_DROP',
          events=['STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL'], path_events=['CONTEXT_CHANGE'])])
        self.assertEqual(r['intent']['reason'], 'UP_STRUCTURE_REVERSED')

    def test_original_B_range_retirement(self):
        r = self.run_exit(prefix() + [trace_row(34, context=0, primary='RANGE',
          events=['CONTEXT_RETIRED_BY_OBSERVED_BALANCE'], path_events=['RANGE_ENTER', 'CONTEXT_CHANGE'])])
        self.assertEqual(r['intent']['reason'], 'UP_STRUCTURE_RETIRED_BY_RANGE')

    def test_sharp_drop_requires_observed_post_entry_state(self):
        rows = [trace_row(33, context=-1, primary='DROP'), trace_row(34, context=-1, primary='SHARP_DROP')]
        self.assertEqual(self.run_exit(rows)['intent']['reason'], 'SHARP_DROP_FIRST_OBSERVED')
        rows[-1] = trace_row(34, context=-1, primary='SHARP_DROP', observed=False)
        self.assertIsNone(self.run_exit(rows)['intent'])

    def test_gap_reset_not_fake_structure_reversal(self):
        rows = prefix() + [trace_row(35, close='.5')]
        self.assertIsNone(self.run_exit(rows, now=at(575, 12))['intent'])

    def test_new_segment_down_not_synthetic_A(self):
        rows = prefix() + [trace_row(34, close='-9', context=-1, primary='DROP', segment='s2')]
        self.assertIsNone(self.run_exit(rows)['intent'])

    def test_unreceived_state_is_rejected(self):
        rows = prefix()
        rows[1]['knownAtJst'] = at(580)
        with self.assertRaisesRegex(ValueError, 'UNRECEIVED_OR_FUTURE_STATE'):
            self.run_exit(rows)

    def test_eod_intent_does_not_require_fresh_price_or_invent_fill(self):
        r = self.run_exit([], start=at(600, 15), now=at(920))
        self.assertEqual(r['intent']['reason'], 'EOD_1520')
        self.assertNotIn('fill_price', r)
        self.assertFalse(r['originalHistoricalFillReplay'])

    def test_current_guard_confirmation_only_effective_next_bar(self):
        rows = [trace_row(30, pivot=pivot('L', 0, 30)), trace_row(31, pivot=pivot('H', 3, 31)),
                trace_row(32, pivot=pivot('L', 1, 32))]
        r = self.run_exit(rows, start=at(572), now=at(572, 12))
        self.assertIsNone(r['intent'])

    def test_no_position_before_fill_and_clock_reversal(self):
        with self.assertRaisesRegex(ValueError, 'POSITION_CLOCK_OR_TRACE_INVALID'):
            self.run_exit([], start=at(600), now=at(599))
        rows = [trace_row(33, context=-1, primary='SHARP_DROP')]
        self.assertIsNone(self.run_exit(rows, start=at(573, 15))['intent'])


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg, self.tables = config(self.root), arrival()
        manifest = models.synthetic_models(self.root, None)
        scorer = h.FrozenH235AsOf(self.root, DAY, manifest=manifest)
        r = scorer.score(models.valid_input())
        self.batch = {'schemaId': 'ARK_NO11_H235_ASOF_PRIVATE_RANK_BATCH_V1', 'policy': scorer.policy,
                      'results': [r], 'capitalV5Executed': False, 'brokerOrders': 0,
                      'productionReady': False, 'orderTransmission': False}
        self.path = self.root / 'portfolio.sqlite'
        self.p = ledger.ShadowPortfolio(self.path, self.cfg, self.tables)
        self.serial = 0

    def tearDown(self):
        self.p.close()
        self.tmp.cleanup()

    def buy(self):
        result = self.p.fund(self.batch, at(571, 12))
        self.assertEqual(result['buyIntents'], 1)
        return result['orderIds'][0]

    def update(self, oid, qty, value, status, clock=at(571, 20), **overrides):
        self.serial += 1
        o = self.p.state()['orders'][oid]
        event = {'schemaId': ledger.UPDATE, 'eventId': h.digest(['test', self.serial]),
                 'orderId': oid, 'symbol': o['symbol'], 'side': o['side'], 'knownAtJst': clock,
                 'cumulativeQuantity': qty, 'cumulativeValueJpy': str(value),
                 'status': status, 'syntheticOnly': True}
        event.update(overrides)
        return self.p.update(event, clock), event

    def filled_buy(self):
        oid = self.buy()
        q = self.p.state()['orders'][oid]['quantity']
        self.update(oid, q, Decimal('101.25') * q, 'FILLED')
        return oid, q

    def test_capital_reserves_but_intent_does_not_fill_position(self):
        oid = self.buy()
        s = self.p.state()
        self.assertEqual(s['cash'], '1000000')
        self.assertEqual(s['positions'], {})
        self.assertGreater(Decimal(self.p.summary()['reservedCashJpy']), 0)
        self.assertEqual(s['orders'][oid]['quantity'] % 100, 0)

    def test_partial_buy_updates_only_observed_quantity_and_cash(self):
        oid = self.buy()
        q = self.p.state()['orders'][oid]['quantity']
        self.assertGreater(q, 100)
        self.update(oid, 100, '10125', 'PARTIAL')
        s = self.p.state()
        self.assertEqual(next(iter(s['positions'].values()))['quantity'], 100)
        self.assertEqual(Decimal(s['cash']), Decimal('989875'))
        self.assertGreater(Decimal(self.p.summary()['reservedCashJpy']), 0)

    def test_cancel_request_does_not_release_reserve_until_ack(self):
        oid = self.buy()
        before = self.p.summary()['reservedCashJpy']
        self.p.cancel(oid, at(571, 15))
        self.assertEqual(self.p.summary()['reservedCashJpy'], before)
        self.update(oid, 0, 0, 'CANCELLED')
        self.assertEqual(Decimal(self.p.summary()['reservedCashJpy']), 0)
        self.assertEqual(self.p.summary()['positionCount'], 0)

    def test_fill_during_cancel_request_is_not_lost(self):
        oid = self.buy()
        self.p.cancel(oid, at(571, 15))
        self.update(oid, 100, 10125, 'PARTIAL')
        self.assertEqual(self.p.state()['orders'][oid]['status'], 'CANCEL_REQUESTED')
        self.update(oid, 100, 10125, 'CANCELLED', at(571, 30))
        self.assertEqual(self.p.summary()['positionCount'], 1)
        self.assertEqual(Decimal(self.p.summary()['reservedCashJpy']), 0)

    def test_eod_sell_intent_keeps_cash_position_and_slot(self):
        _, q = self.filled_buy()
        cash = self.p.state()['cash']
        result = self.p.evaluate_exits({}, at(920))
        self.assertEqual(result['sellIntents'], 1)
        self.assertEqual(self.p.state()['cash'], cash)
        self.assertEqual(self.p.summary()['positionCount'], 1)
        self.assertFalse(self.p.summary()['firstSellFillBuyHalt'])
        self.assertEqual(next(o for o in self.p.state()['orders'].values() if o['side'] == 'SELL')['quantity'], q)

    def test_partial_sell_latches_buy_halt_without_freeing_full_slot(self):
        _, q = self.filled_buy()
        oid = self.p.evaluate_exits({}, at(920))['orderIds'][0]
        self.update(oid, 100, 11000, 'PARTIAL', at(920, 10))
        self.assertTrue(self.p.summary()['firstSellFillBuyHalt'])
        self.assertEqual(next(iter(self.p.state()['positions'].values()))['quantity'], q - 100)
        self.assertEqual(self.p.summary()['positionCount'], 1)
        self.update(oid, q, 110 * q, 'FILLED', at(920, 20))
        self.assertEqual(self.p.summary()['positionCount'], 0)

    def test_cancelled_sell_retains_position_and_allows_next_exit_intent(self):
        _, _ = self.filled_buy()
        oid = self.p.evaluate_exits({}, at(920))['orderIds'][0]
        self.update(oid, 0, 0, 'CANCELLED', at(920, 10))
        second = self.p.evaluate_exits({}, at(920, 20))['orderIds'][0]
        self.assertNotEqual(oid, second)
        self.assertEqual(self.p.summary()['positionCount'], 1)

    def test_duplicate_update_exactly_once_changed_update_fails(self):
        oid = self.buy()
        _, event = self.update(oid, 100, 10125, 'PARTIAL')
        before = self.p.summary()
        self.assertTrue(self.p.update(event, at(571, 22))['idempotentReplay'])
        self.assertEqual(self.p.summary(), before)
        event['cumulativeQuantity'] = 101
        with self.assertRaisesRegex(ValueError, 'EVENT_ID_CONTENT_CHANGED'):
            self.p.update(event, at(571, 23))
        self.assertEqual(self.p.summary(), before)

    def test_counter_reversal_and_identity_change_leave_ledger_unchanged(self):
        oid = self.buy()
        self.update(oid, 100, 10125, 'PARTIAL')
        before = self.p.state()
        for kwargs in ({'qty': 99, 'value': 10000}, {'qty': 101, 'value': 10200, 'symbol': '9999.T'}):
            with self.assertRaises(ValueError):
                self.update(oid, kwargs.pop('qty'), kwargs.pop('value'), 'PARTIAL', at(571, 30), **kwargs)
        self.assertEqual(self.p.state(), before)

    def test_over_budget_fill_is_not_applied(self):
        oid = self.buy()
        before = self.p.state()
        with self.assertRaisesRegex(ValueError, 'FILL_EXCEEDS_RESERVED_CASH'):
            self.update(oid, 100, 20000, 'PARTIAL')
        self.assertEqual(self.p.state(), before)

    def test_unknown_order_state_is_persistent_reconciliation_block(self):
        oid = self.buy()
        self.update(oid, 0, 0, 'UNKNOWN')
        self.assertTrue(self.p.summary()['reconciliationBlocked'])
        self.p.close()
        self.p = ledger.ShadowPortfolio(self.path, self.cfg, self.tables)
        self.assertTrue(self.p.summary()['reconciliationBlocked'])

    def test_restart_preserves_partial_sell_and_latch(self):
        _, _ = self.filled_buy()
        oid = self.p.evaluate_exits({}, at(920))['orderIds'][0]
        self.update(oid, 100, 11000, 'PARTIAL', at(920, 10))
        before = self.p.state()
        self.p.close()
        self.p = ledger.ShadowPortfolio(self.path, self.cfg, self.tables)
        self.assertEqual(self.p.state(), before)
        self.assertEqual(self.p.evaluate_exits({}, at(920, 20))['sellIntents'], 0)

    def test_after_sell_fill_new_candidate_does_not_call_capital(self):
        _, _ = self.filled_buy()
        oid = self.p.evaluate_exits({}, at(920))['orderIds'][0]
        self.update(oid, 100, 11000, 'PARTIAL', at(920, 10))
        new = deepcopy(self.batch)
        new['results'][0].update(candidateId='b' * 64, symbol='6501.T', decisionAtJst=at(920, 15))
        result = self.p.fund(new, at(920, 20))
        self.assertEqual(result['status'], 'AFTER_FIRST_SELL_FILL')
        self.assertEqual(result['buyIntents'], 0)

    def test_external_symbol_never_reserved(self):
        cfg = dict(self.cfg, externalSymbols=['7203.T'])
        other = ledger.ShadowPortfolio(self.root / 'external.sqlite', cfg, self.tables)
        try:
            self.assertEqual(other.fund(self.batch, at(571, 12))['buyIntents'], 0)
        finally:
            other.close()

    def test_real_account_or_changed_config_is_not_accepted(self):
        with self.assertRaisesRegex(ValueError, 'CONFIG_NOT_SHADOW'):
            ledger.ShadowPortfolio(self.root / 'bad.sqlite', dict(self.cfg, syntheticAccountOnly=False), self.tables)
        with self.assertRaisesRegex(ValueError, 'STATE_CHANGED_OR_DIFFERENT_CONFIG'):
            ledger.ShadowPortfolio(self.path, dict(self.cfg, initialCashJpy='2000000'), self.tables)

    def test_checksum_tamper_detected_on_restart(self):
        self.buy()
        self.p.close()
        db = sqlite3.connect(self.path)
        db.execute("UPDATE portfolio SET sha=?", ('0' * 64,))
        db.commit()
        db.close()
        with self.assertRaisesRegex(ValueError, 'STATE_CHANGED_OR_DIFFERENT_CONFIG'):
            ledger.ShadowPortfolio(self.path, self.cfg, self.tables)
        # Restore a fresh independent fixture solely for tearDown.
        self.p = ledger.ShadowPortfolio(self.root / 'cleanup.sqlite', self.cfg, self.tables)


if __name__ == '__main__':
    unittest.main()
