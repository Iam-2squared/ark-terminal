"""Synthetic R34 accounting tests only; no market data or strategy replay."""
import copy
from decimal import Decimal
import unittest
from scripts.phase57_cash_capital_r34 import CashBook, quantity_for_target

T0 = '2025-05-30T09:31:00+09:00'
T1 = '2025-05-30T09:32:00+09:00'
T2 = '2025-05-30T09:33:00+09:00'


def entry(i, rank=1, price='1000', qty=100, now=T0, **changes):
    out = dict(entryId=f'e{i}', symbol=f'S{i}', timestamp=now, entryKnownAt=now,
               effectiveEntryPrice=price, quantity=qty, newEligibleRank=rank,
               savedV1Score='10', rankKnownAt=now, side='LONG', account='CASH')
    out.update(changes)
    return out


def exit_event(i, now=T1, price='1000', confirmed=True):
    return dict(entryId=f'e{i}', timestamp=now, knownAt=now,
                price=price, confirmed=confirmed)


class CashOnlyTests(unittest.TestCase):
    def test_only_three_registered_capacities(self):
        for cap in (3, 4, 5):
            b = CashBook(cap)
            out = b.step(T0, [entry(i, rank=i+1) for i in range(7)])
            self.assertEqual(out['openSymbols'], cap)
            self.assertEqual(sum(r['status']=='REJECTED' for r in out['events']), 7-cap)
        for cap in (0, 1, 2, 6, 10, 3.0, True):
            with self.assertRaisesRegex(ValueError, 'MAX3_4_5_ONLY'):
                CashBook(cap)

    def test_rank_score_symbol_deterministic(self):
        rows = [entry(3, 1, savedV1Score='9'), entry(2, 1), entry(1, 1), entry(4, 2)]
        a = CashBook().step(T0, rows)
        b = CashBook().step(T0, reversed(rows))
        self.assertEqual(a, b)
        self.assertEqual([r['entryId'] for r in a['events']], ['e1','e2','e3','e4'])

    def test_cash_insufficient_skips_whole_request(self):
        b = CashBook()
        out = b.step(T0, [entry(1, price='10001'), entry(2, 2, price='10000')])
        self.assertEqual(out['events'][0]['reason'], 'INSUFFICIENT_AVAILABLE_CASH')
        self.assertEqual(out['events'][1]['status'], 'ACCEPTED')
        self.assertEqual(b.cash, 0)

    def test_no_double_buy_cost(self):
        b = CashBook()
        b.step(T0, [entry(1, price='1000.5')])
        self.assertEqual(b.cash, Decimal('899950.0'))

    def test_sell_cost_matches_r24_pp_convention(self):
        b = CashBook()
        b.step(T0, [entry(1)])
        r = b.step(T1, exits=[exit_event(1, price='1100')])
        self.assertEqual(Decimal(r['events'][0]['sellCostJpy']), Decimal('50'))
        self.assertEqual(b.cash, Decimal('1009950'))
        self.assertEqual(b.realized, Decimal('9950'))

    def test_exit_cash_release_precedes_same_time_entry(self):
        b = CashBook()
        b.step(T0, [entry(1, qty=1000)])
        out = b.step(T1, [entry(2, qty=100, now=T1)], [exit_event(1)])
        self.assertEqual([r['kind'] for r in out['events']], ['EXIT', 'ENTRY'])
        self.assertEqual(out['events'][1]['status'], 'ACCEPTED')
        self.assertEqual(b.cash, Decimal('899500'))

    def test_exit_releases_capacity(self):
        b = CashBook()
        b.step(T0, [entry(i) for i in (1,2,3)])
        out = b.step(T1, [entry(4, now=T1)], [exit_event(2)])
        self.assertEqual(out['events'][1]['status'], 'ACCEPTED')
        self.assertEqual(len(b.positions), 3)

    def test_unresolved_releases_neither_cash_nor_slot(self):
        b = CashBook()
        b.step(T0, [entry(i) for i in (1,2,3)])
        cash = b.cash
        out = b.step(T1, [entry(4, now=T1)], [exit_event(2, price=None, confirmed=False)])
        self.assertEqual(out['events'][0]['status'], 'UNRESOLVED_NO_CASH_RELEASE')
        self.assertEqual(out['events'][1]['reason'], 'MAX_CONCURRENT_SYMBOLS')
        self.assertEqual(b.cash, cash)
        self.assertTrue(b.positions['e2']['unresolved'])

    def test_no_cash_from_unheld_exit(self):
        b = CashBook()
        out = b.step(T0, exits=[exit_event(99, now=T0, price='9999999')])
        self.assertEqual(out['events'][0]['status'], 'NOT_HELD_NO_CASH_RELEASE')
        self.assertEqual(b.cash, Decimal('1000000'))

    def test_no_credit_margin_or_short_inputs(self):
        for changes in ({'account':'MARGIN'}, {'side':'SHORT'}, {'creditLimit':1000000}):
            b = CashBook()
            with self.assertRaises(ValueError):
                b.step(T0, [entry(1, **changes)])
            self.assertEqual(b.cash, Decimal('1000000'))
            self.assertEqual(b.positions, {})

    def test_future_outcomes_rejected_not_used_as_priority(self):
        for key in ('futureHigh', 'bucket', 'exitTimestamp', 'finalPnl', 'capture'):
            with self.assertRaisesRegex(ValueError, 'ENTRY_ALLOWLIST'):
                CashBook().step(T0, [entry(1, **{key:999})])

    def test_future_rank_and_entry_known_at_rejected(self):
        for key in ('rankKnownAt', 'entryKnownAt'):
            with self.assertRaisesRegex(ValueError, 'FUTURE_'):
                CashBook().step(T0, [entry(1, **{key:T1})])

    def test_lot_and_numeric_guards(self):
        for qty in (0, -100, 99, 150, 100.0, True):
            with self.assertRaisesRegex(ValueError, '100_SHARE_LOT'):
                CashBook().step(T0, [entry(1, qty=qty)])
        for price in ('nan', 'Infinity', '0', '-1', None, True):
            with self.assertRaises(ValueError):
                CashBook().step(T0, [entry(1, price=price)])

    def test_quantizer_does_not_choose_weights(self):
        self.assertEqual(quantity_for_target('333333.33', '1000.5'), 300)
        self.assertEqual(quantity_for_target('99', '1'), 0)
        with self.assertRaisesRegex(ValueError, 'NEGATIVE_TARGET'):
            quantity_for_target('-1', '1')

    def test_no_duplicate_symbol_or_entry(self):
        b = CashBook()
        out = b.step(T0, [entry(1), entry(2, symbol='S1')])
        self.assertEqual(out['events'][1]['reason'], 'SYMBOL_ALREADY_OPEN')
        with self.assertRaisesRegex(ValueError, 'ENTRY_ALREADY_PROCESSED'):
            b.step(T1, [entry(1, now=T1)])

    def test_batch_failure_is_atomic_even_after_valid_exit(self):
        b = CashBook()
        b.step(T0, [entry(1)])
        before = copy.deepcopy(b.__dict__)
        with self.assertRaises(ValueError):
            b.step(T1, [entry(2, now=T1, account='MARGIN')], [exit_event(1)])
        self.assertEqual(b.__dict__, before)

    def test_duplicate_exit_and_batch_replay_rejected(self):
        b = CashBook()
        b.step(T0, [entry(1)])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_EXIT'):
            b.step(T1, exits=[exit_event(1), exit_event(1)])
        b.step(T1, exits=[exit_event(1)])
        with self.assertRaisesRegex(ValueError, 'CHRONOLOGICAL'):
            b.step(T1, exits=[exit_event(1)])

    def test_exact_minute_and_timezone(self):
        for when in ('2025-05-30T09:31:01+09:00', '2025-05-30T09:31:00'):
            with self.assertRaises(ValueError):
                CashBook().step(when)
        b = CashBook()
        b.step('2025-05-30T00:31:00+00:00', [entry(1)])
        self.assertEqual(len(b.positions), 1)

    def test_no_overnight_substitute(self):
        b = CashBook()
        b.step(T0, [entry(1)])
        with self.assertRaisesRegex(ValueError, 'UNRESOLVED_OVERNIGHT'):
            b.step('2025-06-02T09:00:00+09:00')
        self.assertEqual(len(b.positions), 1)

    def test_unknown_mark_never_zero_or_cost_equity(self):
        b = CashBook()
        b.step(T0, [entry(1)])
        s = b.snapshot(T1)
        self.assertIsNone(s['equityJpy'])
        self.assertIsNone(s['grossExposureJpy'])
        self.assertEqual(Decimal(s['lockedPurchaseCostJpy']), Decimal('100000'))

    def test_stale_mark_not_forward_filled(self):
        b = CashBook()
        b.step(T0, [entry(1)])
        s = b.snapshot(T1, {'e1':dict(timestamp=T0, knownAt=T0, price='9999')})
        self.assertIsNone(s['equityJpy'])

    def test_future_mark_rejected(self):
        b = CashBook()
        b.step(T0, [entry(1)])
        with self.assertRaisesRegex(ValueError, 'FUTURE_MARK'):
            b.snapshot(T1, {'e1':dict(timestamp=T2, knownAt=T2, price='9999')})

    def test_fresh_mark_exposure_and_no_leverage(self):
        b = CashBook()
        b.step(T0, [entry(1)])
        s = b.snapshot(T1, {'e1':dict(timestamp=T1, knownAt=T1, price='1200')})
        self.assertEqual(Decimal(s['equityJpy']), Decimal('1020000'))
        self.assertLessEqual(Decimal(s['grossExposureRatio']), Decimal(1))
        self.assertEqual(s['borrowedCashJpy'], '0')
        self.assertTrue(all(v is False for v in s['safety'].values()))

    def test_loss_accounting_and_flat_snapshot(self):
        b = CashBook()
        b.step(T0, [entry(1)])
        b.step(T1, exits=[exit_event(1, price='900')])
        s = b.snapshot(T1)
        self.assertEqual(Decimal(s['equityJpy']), Decimal('989950'))
        self.assertEqual(Decimal(s['realizedPnlJpy']), Decimal('-10050'))


if __name__ == '__main__':
    unittest.main()
