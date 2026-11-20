"""Broker-shaped offline receipts exercise the dedicated, non-transmitting ledger."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import no11_broker_execution_ledger as ledger


DAY = '2026-10-26'


def at(seconds=0, fraction=''):
    hour, rest = divmod(9 * 3600 + 30 * 60 + seconds, 3600)
    minute, second = divmod(rest, 60)
    return f'{DAY}T{hour:02d}:{minute:02d}:{second:02d}' + ('.' + fraction if fraction else '') + '+09:00'


def config(cash='100000', **patch):
    return {'schemaId': ledger.CONFIG_SCHEMA, 'sessionDate': DAY, 'account': '特定',
            'allocatedCashJpy': cash, 'externalSymbols': [], 'evidenceMode': 'OFFLINE_REPLAY', **patch}


def intent(name='first', *, symbol='7203.T', side='BUY', quantity=200,
           price='100', charges='0', entry=None, when=None):
    return {'schemaId': ledger.INTENT_SCHEMA, 'intentId': ledger.digest(['intent', name, side]),
            'entryId': entry or 'entry-' + name, 'sessionDate': DAY, 'account': '特定',
            'symbol': symbol, 'side': side, 'quantity': quantity, 'band': 'A',
            'createdAtJst': when or at(1),
            'sourceKind': 'ORIGINAL_CAPITAL_V5' if side == 'BUY' else 'ORIGINAL_EXIT',
            'sourceDecisionSha256': ledger.digest(['original-decision', name, side]),
            'reservePriceJpy': price if side == 'BUY' else '0', 'reserveChargesJpy': charges}


def command(source, rss_id=101, *, kind='ORDER', target=None, when=None, session_key='excel-session-a'):
    terms = {'orderType': 'LIMIT', 'limitPrice': 100, 'timeInForce': 'DAY', 'sor': False,
             'accountType': 0, 'accountTypeVerified': True} if kind == 'ORDER' else None
    args = ([str(rss_id), '0', source['symbol'], '3' if source['side'] == 'BUY' else '1',
             '0', '0', str(source['quantity']), '1', '100', '1', '', '0', '', '', '', '', '0', '', '', '']
            if kind == 'ORDER' else [str(rss_id), '0', target])
    body = {'schemaId': ledger.COMMAND_SCHEMA,
            'commandId': ledger.digest(['command', source['intentId'], kind, session_key, rss_id]),
            'kind': kind, 'sessionDate': DAY, 'rssSessionKey': session_key, 'rssOrderId': rss_id,
            'intentId': source['intentId'], 'symbol': source['symbol'], 'side': source['side'],
            'quantity': source['quantity'], 'account': source['account'], 'targetOrderNumber': target,
            'functionName': 'RssStockOrder' if kind == 'ORDER' else 'RssCancelOrder', 'arguments': args,
            'createdAtJst': when or source['createdAtJst'], 'evidenceMode': 'SYNTHETIC_OFFLINE_ONLY',
            'orderTerms': terms}
    return dict(body, commandSha256=ledger.digest(body))


def seal_command(obj):
    obj = deepcopy(obj)
    obj.pop('commandSha256', None)
    return dict(obj, commandSha256=ledger.digest(obj))


class BrokerLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'broker.sqlite'
        self.config = config()
        self.book = ledger.BrokerExecutionLedger(self.path, self.config)
        self.bound()

    def tearDown(self):
        self.book.close()
        self.temp.cleanup()

    def reopen(self):
        self.book.close()
        self.book = ledger.BrokerExecutionLedger(self.path, self.config)

    def bound(self, *, when=None, amount='100000', external=None, reflected=None):
        stamp = when or at()
        body = {'schemaId': ledger.ACCOUNT_SCHEMA, 'sessionDate': DAY, 'account': '特定',
                'knownAtJst': stamp, 'buyingPowerJpy': amount,
                'externalSymbols': external or [], 'evidenceMode': 'OFFLINE_REPLAY',
                'sourceSnapshotSha256': ledger.digest(['account-source', stamp, amount, external, reflected])}
        if reflected is not None:
            body['reflectedOrders'] = reflected
        body['eventId'] = ledger.digest(body)
        return self.book.observe_account(body, stamp)

    def start(self, name='first', *, rss_id=101, when=None, **kwargs):
        source = intent(name, when=when or at(1), **kwargs)
        cmd = command(source, rss_id)
        self.book.prepare_order(source, cmd, source['createdAtJst'])
        self.book.begin_dispatch(cmd['commandId'], source['createdAtJst'])
        return source, cmd

    def receipt(self, source, cmd, *, quantity=0, gross='0', fees='0', taxes='0',
                phase='ACKNOWLEDGED', when=None, filled_at='auto', number=None,
                attribution=True, **patch):
        stamp = when or at(2)
        existing = self.book.snapshot()['orders'].get(source['intentId'])
        if filled_at == 'auto':
            filled_at = (existing and existing['filledAtJst']) or (stamp if quantity else None)
        body = {'schemaId': ledger.RECEIPT_SCHEMA, 'sessionDate': DAY,
                'intentId': source['intentId'], 'symbol': source['symbol'], 'side': source['side'],
                'account': source['account'], 'rssSessionKey': cmd['rssSessionKey'],
                'rssOrderId': cmd['rssOrderId'], 'brokerOrderNumber': number or str(10000 + cmd['rssOrderId']),
                'knownAtJst': stamp, 'cumulativeQuantity': quantity, 'cumulativeGrossJpy': gross,
                'cumulativeFeesJpy': fees, 'cumulativeTaxesJpy': taxes, 'status': phase,
                'evidenceMode': 'OFFLINE_REPLAY', 'sourceSnapshotSha256': ledger.digest(['receipt-source', stamp, phase, quantity, gross]),
                'allocationEvidenceSha256': ledger.digest(['attribution', source['intentId'], stamp, quantity, gross]),
                'quantityAttributionVerified': True, 'attributionVerified': attribution,
                'filledAtJst': filled_at, 'fillTimeVerified': filled_at is not None, **patch}
        body['eventId'] = ledger.digest(body)
        return body

    def apply(self, source, cmd, **kwargs):
        receipt = self.receipt(source, cmd, **kwargs)
        return self.book.apply_receipt(receipt, receipt['knownAtJst'])

    def filled_buy(self, *, name='first', quantity=200, charges='0', gross=None,
                   fees='0', taxes='0', when=None, symbol='7203.T', rss_id=101):
        source, cmd = self.start(name, quantity=quantity, charges=charges, symbol=symbol, rss_id=rss_id)
        self.apply(source, cmd, quantity=quantity, gross=gross or str(quantity * 100),
                   fees=fees, taxes=taxes, phase='FILLED', when=when or at(2))
        return source, cmd

    def sell_intent(self, buy, *, name='sale', quantity=None, when=None):
        return intent(name, side='SELL', quantity=quantity or buy['quantity'], entry=buy['entryId'],
                      symbol=buy['symbol'], when=when or at(3))

    def transport_result(self, cmd, outcome='UNKNOWN', *, when=None, definitely_not_invoked=False):
        body = {'commandId': cmd['commandId'], 'outcome': outcome, 'knownAtJst': when or at(2),
                'transportReceiptSha256': ledger.digest(['transport', cmd['commandId'], outcome, when]),
                'definitelyNotInvoked': definitely_not_invoked}
        body['eventId'] = ledger.digest(body)
        return body

    def test_preparation_reserves_but_never_creates_a_fill_or_changes_allocated_cash(self):
        source = intent(charges='25')
        cmd = command(source)
        self.book.prepare_order(source, cmd, at(1))
        view = self.book.snapshot()
        self.assertEqual(view['cashJpy'], '100000')
        self.assertEqual(view['reservedCashJpy'], '20025')
        self.assertEqual(view['availableCashJpy'], '79975')
        self.assertEqual(view['positions'], {})
        self.assertFalse(view['actualTransportRequested'])
        self.assertFalse(view['orderTransmission'])

    def test_buying_power_is_a_separate_cap_and_never_becomes_the_cash_balance(self):
        self.bound(when=at(1), amount='5000')
        self.assertEqual(self.book.snapshot()['cashJpy'], '100000')
        self.assertEqual(self.book.snapshot()['availableBuyJpy'], '5000')
        source = intent(when=at(2), quantity=100)
        with self.assertRaisesRegex(ValueError, 'ALLOCATION_OR_BUYING_POWER_BOUND'):
            self.book.prepare_order(source, command(source), at(2))

    def test_two_preparations_cannot_spend_the_same_observed_buying_power(self):
        self.bound(when=at(1), amount='30000')
        first = intent('one', when=at(2))
        self.book.prepare_order(first, command(first), at(2))
        second = intent('two', symbol='6501.T', when=at(3))
        with self.assertRaisesRegex(ValueError, 'ALLOCATION_OR_BUYING_POWER_BOUND'):
            self.book.prepare_order(second, command(second, 102), at(3))
        self.assertEqual(self.book.snapshot()['reservedCashJpy'], '20000')

    def test_buying_power_must_be_fresh_and_never_from_the_future(self):
        source = intent(when=at(31))
        with self.assertRaisesRegex(ValueError, 'FRESH_BUYING_POWER_REQUIRED'):
            self.book.prepare_order(source, command(source), at(31))
        payload = {'schemaId': ledger.ACCOUNT_SCHEMA, 'eventId': 'a' * 64, 'sessionDate': DAY,
                   'account': '特定', 'knownAtJst': at(32), 'buyingPowerJpy': '100000',
                   'externalSymbols': [], 'evidenceMode': 'OFFLINE_REPLAY', 'sourceSnapshotSha256': 'b' * 64}
        with self.assertRaisesRegex(ValueError, 'ACCOUNT_FROM_FUTURE'):
            self.book.observe_account(payload, at(31))

    def test_dispatch_commit_survives_restart_and_never_reissues_a_permit(self):
        source = intent()
        cmd = command(source)
        self.book.prepare_order(source, cmd, at(1))
        result = self.book.begin_dispatch(cmd['commandId'], at(1, '0000001'))
        permit = result['dispatchPermit']
        self.assertEqual(permit['state'], 'IN_FLIGHT_COMMITTED')
        self.assertEqual(permit['permitSha256'], ledger.digest({k: v for k, v in permit.items() if k != 'permitSha256'}))
        self.reopen()
        with self.assertRaisesRegex(ValueError, 'DISPATCH_ALREADY_STARTED'):
            self.book.begin_dispatch(cmd['commandId'], at(2))
        self.assertEqual(self.book.snapshot()['orders'][source['intentId']]['phase'], 'IN_FLIGHT')

    def test_concurrent_dispatch_calls_issue_only_one_committed_permit(self):
        source = intent()
        cmd = command(source)
        self.book.prepare_order(source, cmd, at(1))
        def worker(_):
            other = ledger.BrokerExecutionLedger(self.path, self.config)
            try:
                return other.begin_dispatch(cmd['commandId'], at(2))['status']
            except ValueError as exc:
                return str(exc)
            finally:
                other.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, range(2)))
        self.assertEqual(results.count('DISPATCH_BEGUN_ONCE'), 1)
        self.assertEqual(sum('DISPATCH_ALREADY_STARTED' in r for r in results), 1)

    def test_unknown_submission_survives_restart_and_does_not_release_the_reserve(self):
        source, cmd = self.start()
        result = self.transport_result(cmd)
        self.book.record_transport_result(cmd['commandId'], result, at(2))
        self.reopen()
        view = self.book.snapshot()
        self.assertEqual(view['orders'][source['intentId']]['phase'], 'UNKNOWN')
        self.assertEqual(view['reservedCashJpy'], '20000')
        self.assertFalse(view['newBuysAllowed'])
        with self.assertRaisesRegex(ValueError, 'DISPATCH_ALREADY_STARTED'):
            self.book.begin_dispatch(cmd['commandId'], at(3))

    def test_returning_from_the_sink_does_not_mean_broker_acceptance_or_a_fill(self):
        source, cmd = self.start()
        self.book.record_transport_result(cmd['commandId'], self.transport_result(cmd, 'RETURNED'), at(2))
        view = self.book.snapshot()
        self.assertEqual(view['positions'], {})
        self.assertEqual(view['cashJpy'], '100000')
        self.assertFalse(view['actualTransportObserved'])
        self.assertIn('DISPATCH_RECONCILIATION_REQUIRED', view['blockers'])

    def test_confirmed_not_invoked_releases_only_a_local_intent_and_cannot_be_resent(self):
        source, cmd = self.start()
        result = self.transport_result(cmd, 'NOT_SENT', definitely_not_invoked=True)
        self.book.record_transport_result(cmd['commandId'], result, at(2))
        view = self.book.snapshot()
        self.assertEqual(view['orders'][source['intentId']]['phase'], 'LOCAL_WITHDRAWN')
        self.assertEqual(view['reservedCashJpy'], '0')
        self.assertFalse(view['actualTransportObserved'])
        with self.assertRaisesRegex(ValueError, 'DISPATCH_ALREADY_STARTED'):
            self.book.begin_dispatch(cmd['commandId'], at(3))

    def test_not_sent_without_proof_cannot_resolve_unknown(self):
        _, cmd = self.start()
        with self.assertRaisesRegex(ValueError, 'NO_INVOKE_PROOF_REQUIRED'):
            self.book.record_transport_result(cmd['commandId'], self.transport_result(cmd, 'NOT_SENT'), at(2))
        self.assertEqual(self.book.snapshot()['reservedCashJpy'], '20000')

    def test_partial_fill_cancellation_request_and_final_ack_have_distinct_cash_effects(self):
        source, cmd = self.start(charges='20')
        self.apply(source, cmd, quantity=100, gross='9900', fees='5', phase='PARTIAL')
        view = self.book.snapshot()
        self.assertEqual(view['cashJpy'], '90095')
        self.assertEqual(view['reservedCashJpy'], '10015')
        cancel = command(source, 201, kind='CANCEL', target='10101', when=at(3))
        self.book.request_cancel(source['intentId'], cancel, at(3))
        self.assertEqual(self.book.snapshot()['reservedCashJpy'], '10015')
        self.book.begin_dispatch(cancel['commandId'], at(3))
        self.apply(source, cmd, quantity=100, gross='9900', fees='5', phase='CANCELLED', when=at(4))
        view = self.book.snapshot()
        self.assertEqual(view['cashJpy'], '90095')
        self.assertEqual(view['reservedCashJpy'], '0')
        self.assertEqual(view['positions'][source['entryId']]['quantity'], 100)

    def test_fill_during_cancel_request_is_applied_and_cancellation_stays_pending(self):
        source, cmd = self.start(quantity=300)
        self.apply(source, cmd)
        cancel = command(source, 201, kind='CANCEL', target='10101', when=at(3))
        self.book.request_cancel(source['intentId'], cancel, at(3))
        self.book.begin_dispatch(cancel['commandId'], at(3))
        self.apply(source, cmd, quantity=100, gross='10000', phase='PARTIAL', when=at(4))
        view = self.book.snapshot()
        self.assertEqual(view['orders'][source['intentId']]['phase'], 'CANCEL_REQUESTED')
        self.assertEqual(view['cashJpy'], '90000')
        self.assertEqual(view['reservedCashJpy'], '20000')
        self.apply(source, cmd, quantity=200, gross='20000', phase='CANCELLED', when=at(5))
        view = self.book.snapshot()
        self.assertEqual(view['cashJpy'], '80000')
        self.assertEqual(view['positions'][source['entryId']]['quantity'], 200)
        self.assertEqual(view['reservedCashJpy'], '0')

    def test_broker_cancel_pending_does_not_release_unfilled_reservations(self):
        source, cmd = self.start()
        self.apply(source, cmd, phase='CANCEL_PENDING')
        self.assertEqual(self.book.snapshot()['reservedCashJpy'], '20000')
        self.assertEqual(self.book.snapshot()['orders'][source['intentId']]['phase'], 'CANCEL_PENDING')

    def test_fill_racing_before_cancel_dispatch_invalidates_the_unused_cancel(self):
        source, cmd = self.start()
        self.apply(source, cmd)
        cancel = command(source, 201, kind='CANCEL', target='10101', when=at(3))
        self.book.request_cancel(source['intentId'], cancel, at(3))
        self.apply(source, cmd, quantity=200, gross='20000', phase='FILLED', when=at(4))
        with self.assertRaisesRegex(ValueError, 'DISPATCH_ALREADY_STARTED|ORDER_ALREADY_TERMINAL'):
            self.book.begin_dispatch(cancel['commandId'], at(5))
        self.assertEqual(self.book.snapshot()['commands'][cancel['commandId']]['state'], 'OBSOLETE')

    def test_unknown_order_cannot_be_resolved_by_local_cancel_preparation(self):
        source, cmd = self.start()
        self.apply(source, cmd, phase='UNKNOWN')
        cancel = command(source, 201, kind='CANCEL', target='10101', when=at(3))
        with self.assertRaisesRegex(ValueError, 'CANCEL_REQUIRES_KNOWN_ACTIVE_ORDER'):
            self.book.request_cancel(source['intentId'], cancel, at(3))

    def test_duplicate_receipt_is_exactly_once_and_same_id_changed_payload_is_rejected(self):
        source, cmd = self.start()
        receipt = self.receipt(source, cmd, quantity=100, gross='10000', phase='PARTIAL')
        self.book.apply_receipt(receipt, at(2))
        before = self.book.snapshot()
        self.reopen()
        result = self.book.apply_receipt(receipt, at(3))
        self.assertTrue(result['idempotentReplay'])
        self.assertEqual(self.book.snapshot(), before)
        changed = dict(receipt, cumulativeGrossJpy='10001')
        with self.assertRaisesRegex(ValueError, 'EVENT_ID_CONTENT_CHANGED'):
            self.book.apply_receipt(changed, at(3))
        self.assertEqual(self.book.snapshot(), before)

    def test_cumulative_quantity_gross_fees_and_tax_cannot_go_backwards(self):
        source, cmd = self.start(charges='20')
        self.apply(source, cmd, quantity=100, gross='10000', fees='5', taxes='2', phase='PARTIAL')
        original = self.book.snapshot()
        for patch, reason in [({'quantity': 0, 'gross': '0', 'phase': 'ACKNOWLEDGED', 'filled_at': None}, 'QUANTITY_REVERSED'),
                              ({'gross': '9999'}, 'GROSS_REVERSED'),
                              ({'fees': '4'}, 'FEES_REVERSED'),
                              ({'taxes': '1'}, 'TAXES_REVERSED')]:
            options = {'quantity': 100, 'gross': '10000', 'fees': '5', 'taxes': '2', 'phase': 'PARTIAL', 'when': at(3)}
            options.update(patch)
            with self.assertRaisesRegex(ValueError, reason):
                self.apply(source, cmd, **options)
            self.assertEqual(self.book.snapshot(), original)

    def test_quantity_without_any_new_priced_consideration_is_not_a_free_fill(self):
        source, cmd = self.start()
        self.apply(source, cmd, quantity=100, gross='10000', phase='PARTIAL')
        with self.assertRaisesRegex(ValueError, 'NEW_PRICED_QUANTITY_WITHOUT_CONSIDERATION'):
            self.apply(source, cmd, quantity=200, gross='10000', phase='FILLED', when=at(3))

    def test_receipt_clock_reversal_including_seventh_fractional_digit_is_rejected(self):
        source, cmd = self.start()
        self.apply(source, cmd, when=at(2, '0000002'))
        receipt = self.receipt(source, cmd, when=at(2, '0000001'))
        with self.assertRaisesRegex(ValueError, 'RECEIPT_CLOCK_REVERSED'):
            self.book.apply_receipt(receipt, at(3))
        self.assertEqual(ledger.instant(at(2, '0000002')) - ledger.instant(at(2, '0000001')), 1)

    def test_process_clock_reversal_is_not_hidden_by_a_new_receipt_id(self):
        source, cmd = self.start()
        self.apply(source, cmd, when=at(4))
        receipt = self.receipt(source, cmd, when=at(3))
        with self.assertRaisesRegex(ValueError, 'PROCESS_CLOCK_REVERSED'):
            self.book.apply_receipt(receipt, at(3))

    def test_unknown_positive_quantity_is_retained_without_inventing_price_or_fill_time(self):
        source, cmd = self.start()
        self.apply(source, cmd, quantity=100, gross=None, fees=None, taxes=None, phase='UNKNOWN',
                   attribution=False, filled_at=None)
        view = self.book.snapshot()
        self.assertEqual(view['positions'][source['entryId']]['quantity'], 100)
        self.assertIsNone(view['positions'][source['entryId']]['filledAtJst'])
        self.assertFalse(view['positions'][source['entryId']]['fillTimeVerified'])
        self.assertEqual(view['cashJpy'], '100000')
        self.assertEqual(view['reservedCashJpy'], '20000')
        self.assertIsNone(view['orders'][source['intentId']]['cumulativeGrossJpy'])
        self.assertFalse(view['newBuysAllowed'])
        self.reopen()
        self.assertEqual(self.book.snapshot(), view)

    def test_later_attributed_amount_resolves_the_unpriced_quantity_without_double_counting_shares(self):
        source, cmd = self.start()
        self.apply(source, cmd, quantity=100, gross=None, fees=None, taxes=None,
                   phase='UNKNOWN', attribution=False, filled_at=None)
        self.apply(source, cmd, quantity=100, gross='9990', phase='CANCELLED', when=at(3), filled_at=None)
        view = self.book.snapshot()
        self.assertEqual(view['positions'][source['entryId']]['quantity'], 100)
        self.assertEqual(view['cashJpy'], '90010')
        self.assertEqual(view['reservedCashJpy'], '0')
        self.assertEqual(view['unpricedOrders'], [])

    def test_cancel_ack_keeps_the_reserve_for_already_filled_but_unpriced_quantity(self):
        source, cmd = self.start()
        self.apply(source, cmd, quantity=100, gross=None, fees=None, taxes=None,
                   phase='CANCELLED', attribution=False, filled_at=None)
        view = self.book.snapshot()
        self.assertEqual(view['reservedCashJpy'], '10000')
        self.assertEqual(view['cashJpy'], '100000')
        self.assertFalse(view['newBuysAllowed'])

    def test_unknown_charges_hold_the_allowance_and_stop_new_buys_but_allow_existing_sells(self):
        buy, _ = self.filled_buy(charges='30', fees=None, taxes=None)
        view = self.book.snapshot()
        self.assertEqual(view['reservedCashJpy'], '30')
        self.assertIn('FEES_OR_TAXES_UNRECONCILED', view['blockers'])
        sell = self.sell_intent(buy)
        sell_cmd = command(sell, 202)
        self.book.prepare_order(sell, sell_cmd, at(3))
        self.book.begin_dispatch(sell_cmd['commandId'], at(3))
        self.assertEqual(self.book.snapshot()['orders'][sell['intentId']]['phase'], 'IN_FLIGHT')

    def test_later_charge_receipt_applies_only_the_delta_and_releases_the_allowance(self):
        source, cmd = self.filled_buy(charges='30', fees=None, taxes=None)
        self.apply(source, cmd, quantity=200, gross='20000', fees='12', taxes='3', phase='FILLED', when=at(3))
        view = self.book.snapshot()
        self.assertEqual(view['cashJpy'], '79985')
        self.assertEqual(view['reservedCashJpy'], '0')
        self.assertEqual(view['unknownChargeOrders'], [])

    def test_slippage_beyond_allocation_is_recorded_and_blocks_buy_instead_of_losing_a_fill(self):
        self.book.close()
        self.path.unlink()
        self.config = config(cash='50000')
        self.book = ledger.BrokerExecutionLedger(self.path, self.config)
        self.bound(amount='50000')
        source, cmd = self.start(quantity=500)
        self.apply(source, cmd, quantity=500, gross='60000', phase='FILLED')
        view = self.book.snapshot()
        self.assertEqual(view['cashJpy'], '-10000')
        self.assertEqual(view['availableCashJpy'], '0')
        self.assertEqual(view['positions'][source['entryId']]['quantity'], 500)
        self.assertTrue(view['accountShortfall'])
        self.assertIn('EXECUTION_RESERVATION_OVERRUN', view['blockers'])
        self.reopen()
        self.assertEqual(self.book.snapshot()['cashJpy'], '-10000')

    def test_first_positive_sell_fill_halts_buys_even_if_its_price_is_unavailable(self):
        buy, _ = self.filled_buy()
        sell = self.sell_intent(buy)
        cmd = command(sell, 202)
        self.book.prepare_order(sell, cmd, at(3))
        self.book.begin_dispatch(cmd['commandId'], at(3))
        self.apply(sell, cmd, quantity=100, gross=None, fees=None, taxes=None,
                   phase='UNKNOWN', when=at(4), attribution=False, filled_at=None)
        view = self.book.snapshot()
        self.assertEqual(view['positions'][buy['entryId']]['quantity'], 100)
        self.assertEqual(view['cashJpy'], '80000')
        self.assertTrue(view['firstSellFillBuyHalt'])
        self.reopen()
        self.assertTrue(self.book.snapshot()['firstSellFillBuyHalt'])

    def test_full_buy_sell_lifecycle_uses_attributed_cash_and_persistent_first_sell_halt(self):
        buy, _ = self.filled_buy(charges='20', fees='10')
        sell = self.sell_intent(buy)
        cmd = command(sell, 202)
        self.book.prepare_order(sell, cmd, at(3))
        self.book.begin_dispatch(cmd['commandId'], at(3))
        self.apply(sell, cmd, quantity=100, gross='11000', fees='4', taxes='3', phase='PARTIAL', when=at(4))
        self.apply(sell, cmd, quantity=200, gross='22000', fees='8', taxes='6', phase='FILLED', when=at(5))
        self.bound(when=at(6), amount='200000')
        view = self.book.snapshot()
        self.assertEqual(view['cashJpy'], '101976')
        self.assertEqual(view['positionCount'], 0)
        self.assertTrue(view['firstSellFillBuyHalt'])
        another = intent('next', symbol='6501.T', when=at(7))
        with self.assertRaisesRegex(ValueError, 'AFTER_FIRST_SELL_FILL'):
            self.book.prepare_order(another, command(another, 303), at(7))
        self.reopen()
        self.assertEqual(self.book.snapshot()['cashJpy'], '101976')

    def test_first_sell_fill_marks_other_buys_for_cancellation_without_fabricating_ack(self):
        first = intent('first')
        second = intent('second', symbol='6501.T')
        cmd1, cmd2 = command(first), command(second, 102)
        self.book.prepare_order(first, cmd1, at(1))
        self.book.prepare_order(second, cmd2, at(1))
        self.book.begin_dispatch(cmd1['commandId'], at(1))
        self.book.begin_dispatch(cmd2['commandId'], at(1))
        self.apply(first, cmd1, quantity=200, gross='20000', phase='FILLED')
        self.apply(second, cmd2)
        sell = self.sell_intent(first)
        cmd = command(sell, 202)
        self.book.prepare_order(sell, cmd, at(3))
        self.book.begin_dispatch(cmd['commandId'], at(3))
        self.apply(sell, cmd, quantity=100, gross='11000', phase='PARTIAL', when=at(4))
        pending = self.book.snapshot()['orders'][second['intentId']]
        self.assertTrue(pending['cancelNeeded'])
        self.assertEqual(pending['phase'], 'ACKNOWLEDGED')
        self.assertEqual(pending['reservedCashJpy'], '20000')

    def test_sell_reservations_prevent_two_orders_from_selling_the_same_shares(self):
        buy, _ = self.filled_buy(quantity=300)
        first = self.sell_intent(buy, quantity=200)
        self.book.prepare_order(first, command(first, 202), at(3))
        second = self.sell_intent(buy, name='sale-two', quantity=200, when=at(4))
        with self.assertRaisesRegex(ValueError, 'SELL_EXCEEDS_UNRESERVED_OWNED'):
            self.book.prepare_order(second, command(second, 203), at(4))

    def test_cancelled_sell_frees_only_its_remaining_share_reservation(self):
        buy, _ = self.filled_buy()
        sell = self.sell_intent(buy)
        cmd = command(sell, 202)
        self.book.prepare_order(sell, cmd, at(3))
        self.book.begin_dispatch(cmd['commandId'], at(3))
        self.apply(sell, cmd, quantity=100, gross='11000', phase='CANCELLED', when=at(4))
        retry = self.sell_intent(buy, name='residual', quantity=100, when=at(5))
        self.book.prepare_order(retry, command(retry, 203), at(5))
        self.assertEqual(self.book.snapshot()['positions'][buy['entryId']]['quantity'], 100)

    def test_unowned_or_external_position_cannot_be_imported_through_a_sell_intent(self):
        sell = intent('personal', side='SELL')
        with self.assertRaisesRegex(ValueError, 'SELL_NOT_ARK_OWNED'):
            self.book.prepare_order(sell, command(sell), at(1))
        self.bound(when=at(1), external=['7203.T'])
        buy = intent(when=at(2))
        with self.assertRaisesRegex(ValueError, 'EXTERNAL_SYMBOL_PROTECTED'):
            self.book.prepare_order(buy, command(buy), at(2))

    def test_max3_includes_unfilled_reservations_and_lots_remain_100_shares(self):
        for n, symbol in enumerate(['7203.T', '6501.T', '6758.T'], 1):
            source = intent(str(n), symbol=symbol, quantity=100, when=at(n))
            self.book.prepare_order(source, command(source, 100 + n), at(n))
        fourth = intent('four', symbol='8306.T', quantity=100, when=at(4))
        with self.assertRaisesRegex(ValueError, 'MAX3_SLOTS'):
            self.book.prepare_order(fourth, command(fourth, 104), at(4))
        odd = intent('odd', quantity=150, when=at(4))
        with self.assertRaisesRegex(ValueError, 'LOT_100_REQUIRED'):
            self.book.prepare_order(odd, command(odd, 105), at(4))

    def test_rss_session_and_id_are_reserved_across_orders_and_cancels_and_restart(self):
        source, cmd = self.start()
        self.apply(source, cmd)
        self.reopen()
        cancel = command(source, 101, kind='CANCEL', target='10101', when=at(3))
        with self.assertRaisesRegex(ValueError, 'RSS_ID_ALREADY_RESERVED'):
            self.book.request_cancel(source['intentId'], cancel, at(3))
        other = intent('other', symbol='6501.T', when=at(3))
        with self.assertRaisesRegex(ValueError, 'RSS_ID_ALREADY_RESERVED'):
            self.book.prepare_order(other, command(other, 101), at(3))
        self.book.prepare_order(other, command(other, 101, session_key='new-excel-session'), at(3))

    def test_same_broker_order_number_cannot_be_assigned_to_two_origins(self):
        first = intent('one')
        second = intent('two', symbol='6501.T')
        a, b = command(first), command(second, 102)
        self.book.prepare_order(first, a, at(1))
        self.book.prepare_order(second, b, at(1))
        self.book.begin_dispatch(a['commandId'], at(1))
        self.book.begin_dispatch(b['commandId'], at(1))
        self.apply(first, a)
        with self.assertRaisesRegex(ValueError, 'BROKER_ORDER_ASSIGNED_TWICE'):
            self.apply(second, b, number='10101', when=at(3))

    def test_changed_origin_identity_and_unattributed_money_are_rejected_atomically(self):
        source, cmd = self.start()
        before = self.book.snapshot()
        for patch in [{'rssOrderId': 102}, {'rssSessionKey': 'wrong'}, {'symbol': '6501.T'},
                      {'side': 'SELL'}, {'account': '一般'}, {'quantityAttributionVerified': False},
                      {'evidenceMode': 'BROKER_OBSERVATION'}]:
            receipt = self.receipt(source, cmd, quantity=100, gross='10000', phase='PARTIAL', **patch)
            with self.assertRaises(ValueError):
                self.book.apply_receipt(receipt, at(2))
            self.assertEqual(self.book.snapshot(), before)
        receipt = self.receipt(source, cmd, quantity=100, gross='10000', phase='PARTIAL', attribution=False)
        with self.assertRaisesRegex(ValueError, 'EXECUTION_AMOUNT_ATTRIBUTION_REQUIRED'):
            self.book.apply_receipt(receipt, at(2))

    def test_receipt_before_dispatch_commit_cannot_create_an_order_or_position(self):
        source = intent()
        cmd = command(source)
        self.book.prepare_order(source, cmd, at(1))
        with self.assertRaisesRegex(ValueError, 'RECEIPT_WITHOUT_DISPATCH_BEGIN'):
            self.apply(source, cmd, quantity=200, gross='20000', phase='FILLED')

    def test_command_trigger_and_canonical_arguments_cannot_be_changed_even_with_a_new_hash(self):
        source = intent()
        original = command(source)
        for index, value in [(1, '1'), (2, '6501.T'), (3, '1'), (6, '300'), (11, '1')]:
            changed = deepcopy(original)
            changed['arguments'][index] = value
            with self.assertRaisesRegex(ValueError, 'COMMAND_ARGUMENT'):
                self.book.prepare_order(source, seal_command(changed), at(1))
        self.assertEqual(self.book.snapshot()['orders'], {})

    def test_live_observed_commands_cannot_enter_an_offline_ledger(self):
        source = intent()
        cmd = command(source)
        cmd['evidenceMode'] = 'LIVE_OBSERVED'
        with self.assertRaisesRegex(ValueError, 'COMMAND_MODE_OR_SESSION'):
            self.book.prepare_order(source, seal_command(cmd), at(1))

    def test_source_checkpoints_survive_restart_and_receipt_before_checkpoint_is_replayable(self):
        source, cmd = self.start()
        receipt = self.receipt(source, cmd, quantity=100, gross='10000', phase='PARTIAL')
        self.book.apply_receipt(receipt, at(2))
        self.reopen()  # crash occurred before evaluator source checkpoint
        self.assertTrue(self.book.apply_receipt(receipt, at(3))['idempotentReplay'])
        value = {'sourceAt': at(2), 'seenExecutions': {'abc': 1}}
        saved = self.book.checkpoint_source('rss-order-evaluator', value, at(3))
        self.reopen()
        self.assertEqual(self.book.source_checkpoint('rss-order-evaluator'), value)
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_COMPARE_AND_SWAP'):
            self.book.checkpoint_source('rss-order-evaluator', {'changed': True}, at(4), expected_sha256='f' * 64)
        self.book.checkpoint_source('rss-order-evaluator', {'changed': True}, at(4), expected_sha256=saved['sha256'])

    def test_state_checksum_and_event_chain_tampering_are_detected_on_restart(self):
        self.start()
        self.book.close()
        raw = sqlite3.connect(self.path)
        raw.execute("UPDATE broker_events SET payload='{}' WHERE seq=1")
        raw.commit()
        raw.close()
        with self.assertRaisesRegex(ValueError, 'EVENT_CHAIN_CHANGED'):
            ledger.BrokerExecutionLedger(self.path, self.config)
        # Avoid closing a replaced/failed connection in tearDown.
        self.book = ledger.BrokerExecutionLedger(Path(self.temp.name) / 'clean.sqlite', self.config)

    def test_allocation_or_evidence_mode_cannot_change_on_restart(self):
        self.start()
        self.book.close()
        with self.assertRaisesRegex(ValueError, 'STATE_CHANGED_OR_DIFFERENT_CONFIG'):
            ledger.BrokerExecutionLedger(self.path, dict(self.config, allocatedCashJpy='200000'))
        self.book = ledger.BrokerExecutionLedger(self.path, self.config)

    def test_other_connection_sees_existing_reservations_before_admitting_new_money(self):
        self.bound(when=at(1), amount='30000')
        other = ledger.BrokerExecutionLedger(self.path, self.config)
        try:
            first = intent('one', when=at(2))
            self.book.prepare_order(first, command(first), at(2))
            second = intent('two', symbol='6501.T', when=at(3))
            with self.assertRaisesRegex(ValueError, 'ALLOCATION_OR_BUYING_POWER_BOUND'):
                other.prepare_order(second, command(second, 102), at(3))
        finally:
            other.close()

    def test_terminal_orders_cannot_be_reopened_by_stale_nonterminal_status(self):
        source, cmd = self.filled_buy()
        with self.assertRaisesRegex(ValueError, 'TERMINAL_ORDER_REOPENED|FALSE_PARTIAL_FILL'):
            self.apply(source, cmd, quantity=200, gross='20000', phase='CANCEL_PENDING', when=at(3))

    def test_late_additional_fill_on_cancelled_order_is_recorded_without_reopening_it(self):
        source, cmd = self.start()
        self.apply(source, cmd, quantity=100, gross='10000', phase='CANCELLED')
        self.apply(source, cmd, quantity=150, gross='15000', phase='CANCELLED', when=at(3))
        view = self.book.snapshot()
        self.assertEqual(view['cashJpy'], '85000')
        self.assertEqual(view['positions'][source['entryId']]['quantity'], 150)
        self.assertTrue(view['orders'][source['intentId']]['terminalRevisionObserved'])

    def test_local_withdrawal_is_available_only_before_any_dispatch(self):
        source = intent()
        cmd = command(source)
        self.book.prepare_order(source, cmd, at(1))
        self.book.withdraw_prepared(source['intentId'], at(2))
        self.assertEqual(self.book.snapshot()['reservedCashJpy'], '0')
        self.assertFalse(self.book.snapshot()['actualTransportRequested'])
        with self.assertRaisesRegex(ValueError, 'DISPATCH_ALREADY_STARTED'):
            self.book.begin_dispatch(cmd['commandId'], at(3))

    def test_expired_partial_order_keeps_owned_shares_and_releases_only_unfilled_cash(self):
        source, cmd = self.start()
        self.apply(source, cmd, quantity=100, gross='10000', phase='EXPIRED')
        view = self.book.snapshot()
        self.assertEqual(view['positions'][source['entryId']]['quantity'], 100)
        self.assertEqual(view['reservedCashJpy'], '0')
        self.assertEqual(view['cashJpy'], '90000')

    def test_maximum_rss_id_is_accepted_but_overflow_or_boolean_is_not(self):
        source = intent()
        for bad in [0, 2147483648, True]:
            with self.assertRaisesRegex(ValueError, 'RSS_ID'):
                self.book.prepare_order(source, command(source, bad), at(1))
        self.book.prepare_order(source, command(source, 2147483647), at(1))

    def test_impossible_or_non_jst_dates_and_overprecise_clocks_are_rejected(self):
        for stamp in ['2026-02-30T09:30:00+09:00', DAY + 'T24:00:00+09:00',
                      DAY + 'T09:30:00.12345678+09:00', DAY + 'T00:30:00Z']:
            with self.assertRaisesRegex(ValueError, 'CLOCK'):
                ledger.instant(stamp)

    def test_snapshot_is_a_copy_and_a_stale_snapshot_cannot_claim_current_cash_admission(self):
        self.start()
        view = self.book.snapshot()
        view['cashJpy'] = '999999999'
        view['orders'].clear()
        self.assertEqual(self.book.snapshot()['cashJpy'], '100000')
        self.assertEqual(len(self.book.snapshot()['orders']), 1)
        self.assertFalse(self.book.snapshot(at(100))['newBuysAllowed'])

    def test_evidence_mode_must_be_explicit_and_cannot_be_guessed_from_receipts(self):
        missing = dict(self.config)
        del missing['evidenceMode']
        with self.assertRaisesRegex(ValueError, 'EVIDENCE_MODE'):
            ledger.BrokerExecutionLedger(Path(self.temp.name) / 'unspecified.sqlite', missing)

    def test_new_personal_holding_between_preparation_and_dispatch_blocks_the_buy(self):
        source = intent()
        cmd = command(source)
        self.book.prepare_order(source, cmd, at(1))
        self.bound(when=at(2), external=['7203.T'])
        with self.assertRaisesRegex(ValueError, 'EXTERNAL_SYMBOL_PROTECTED'):
            self.book.begin_dispatch(cmd['commandId'], at(3))
        self.assertEqual(self.book.snapshot()['commands'][cmd['commandId']]['state'], 'PREPARED')

    def test_a_consumed_original_entry_is_not_reoffered_after_an_unfilled_cancel(self):
        source, cmd = self.start()
        self.apply(source, cmd, phase='CANCELLED')
        repeated = intent('new-intent-id', entry=source['entryId'], when=at(3))
        with self.assertRaisesRegex(ValueError, 'ENTRY_OR_SYMBOL_ALREADY_OWNED'):
            self.book.prepare_order(repeated, command(repeated, 102), at(3))

    def test_snapshot_never_reissues_a_saved_permit_and_offline_evidence_is_not_physical_observation(self):
        source, cmd = self.start()
        self.apply(source, cmd)
        view = self.book.snapshot()
        self.assertTrue(view['dispatchStarted'])
        self.assertTrue(view['observedOrderEvidencePresent'])
        self.assertFalse(view['actualTransportObserved'])
        self.assertFalse(view['actualTransportRequested'])
        self.assertNotIn('permit', view['commands'][cmd['commandId']])
        self.assertRegex(view['commands'][cmd['commandId']]['permitSha256'], r'^[a-f0-9]{64}$')

    def test_actual_js_compiler_and_permit_validator_accept_the_python_commit_contract(self):
        source = intent(price='100.15005')
        request = command(source)
        request['orderTerms']['limitPrice'] = 100.1
        program = """import fs from 'node:fs';
import {compileTransportCommand,validateDispatchPermit} from './research/no12-prebuy-causal-runtime-20261011/tools/no11_msii_transport.mjs';
const q=JSON.parse(fs.readFileSync(0,'utf8'));
const out=q.action==='compile'?compileTransportCommand(q.command):validateDispatchPermit(q.permit,q.command,q.now);
process.stdout.write(JSON.stringify(out));
"""
        def run(value):
            r = subprocess.run(['node', '--input-type=module', '-e', program],
                               input=json.dumps(value), text=True, encoding='utf-8', capture_output=True,
                               cwd=ledger.ROOT, timeout=10, check=True)
            return json.loads(r.stdout)
        compiled = run({'action': 'compile', 'command': request})
        self.book.prepare_order(source, compiled, at(1))
        result = self.book.begin_dispatch(compiled['commandId'], at(1, '0000001'))
        checked = run({'action': 'permit', 'command': compiled,
                       'permit': result['dispatchPermit'], 'now': at(1, '0000002')})
        self.assertEqual(checked, result['dispatchPermit'])
        self.assertEqual(self.book.snapshot()['reservedCashJpy'], '20030.01')

    def test_recovery_abandons_only_a_never_begun_order_and_preserves_its_rss_reservation(self):
        source = intent()
        cmd = command(source)
        self.book.prepare_order(source, cmd, at(1))
        self.reopen()
        result = self.book.abandon_prepared(cmd['commandId'], at(2))
        self.assertFalse(result['brokerCancellationAcknowledged'])
        self.assertEqual(self.book.snapshot()['reservedCashJpy'], '0')
        self.assertEqual(self.book.snapshot()['orders'][source['intentId']]['phase'], 'LOCAL_WITHDRAWN')
        other = intent('other', symbol='6501.T', when=at(3))
        with self.assertRaisesRegex(ValueError, 'RSS_ID_ALREADY_RESERVED'):
            self.book.prepare_order(other, command(other), at(3))
        with self.assertRaisesRegex(ValueError, 'DISPATCH_ALREADY_STARTED'):
            self.book.begin_dispatch(cmd['commandId'], at(3))

    def test_recovery_abandons_never_begun_cancel_without_releasing_order_money(self):
        source, cmd = self.start()
        self.apply(source, cmd, quantity=100, gross='10000', phase='PARTIAL')
        cancel = command(source, 201, kind='CANCEL', target='10101', when=at(3))
        self.book.request_cancel(source['intentId'], cancel, at(3))
        self.reopen()
        result = self.book.abandon_prepared(cancel['commandId'], at(4))
        view = self.book.snapshot()
        self.assertEqual(result['kind'], 'CANCEL')
        self.assertEqual(view['orders'][source['intentId']]['phase'], 'PARTIAL')
        self.assertFalse(view['orders'][source['intentId']]['cancelRequested'])
        self.assertEqual(view['reservedCashJpy'], '10000')
        self.assertEqual(view['cashJpy'], '90000')
        self.assertEqual(view['positions'][source['entryId']]['quantity'], 100)
        new_cancel = command(source, 202, kind='CANCEL', target='10101', when=at(5))
        self.book.request_cancel(source['intentId'], new_cancel, at(5))

    def test_recovery_cannot_abandon_a_begun_or_uncertain_command(self):
        _, cmd = self.start()
        self.reopen()
        with self.assertRaisesRegex(ValueError, 'ABANDON_REQUIRES_NEVER_DISPATCHED'):
            self.book.abandon_prepared(cmd['commandId'], at(2))
        self.book.record_transport_result(cmd['commandId'], self.transport_result(cmd), at(2))
        with self.assertRaisesRegex(ValueError, 'ABANDON_REQUIRES_NEVER_DISPATCHED'):
            self.book.abandon_prepared(cmd['commandId'], at(3))
        self.assertEqual(self.book.snapshot()['reservedCashJpy'], '20000')

    def test_fill_time_conflict_keeps_positive_fill_and_is_never_silently_recertified(self):
        source, cmd = self.start()
        self.apply(source, cmd, quantity=100, gross='10000', phase='PARTIAL')
        self.apply(source, cmd, quantity=200, gross='20000', phase='FILLED', when=at(3),
                   filled_at=None, fillTimeConflict=True)
        view = self.book.snapshot()
        self.assertEqual(view['positions'][source['entryId']]['quantity'], 200)
        self.assertEqual(view['cashJpy'], '80000')
        self.assertIsNone(view['positions'][source['entryId']]['filledAtJst'])
        self.assertEqual(view['positions'][source['entryId']]['firstReportedFillAtJst'], at(2))
        self.assertFalse(view['orders'][source['intentId']]['fillTimeVerified'])
        self.assertTrue(view['orders'][source['intentId']]['fillTimeConflict'])
        self.reopen()
        self.apply(source, cmd, quantity=200, gross='20000', phase='FILLED', when=at(4), filled_at=at(2))
        self.assertFalse(self.book.snapshot()['orders'][source['intentId']]['fillTimeVerified'])
        self.assertIsNone(self.book.snapshot()['positions'][source['entryId']]['filledAtJst'])


if __name__ == '__main__':
    unittest.main()
