"""Original decisions through actual adapters, with an explicit fake broker.

There is no Excel, live configuration, or broker connection in these tests.
The Node normalizer/compiler and SQLite ledger are real, not mocked copies.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_broker_execution_service as s
import no11_broker_execution_ledger as ledger
import no11_h235_asof_forward_shadow as h
import test_no11_frozen_p1_h235_asof as models
from test_no11_frozen_p1_execution_bundle import arrival

DAY = '2026-10-26'
def at(minute=571, second=12):
    return DAY + 'T%02d:%02d:%02d+09:00' % (minute // 60, minute % 60, second)


def excel():
    value = {'processId': 123, 'startedAtUtc': '2026-10-25T23:00:00.0000000Z',
             'accountWorkbookIdentity': 'a' * 64, 'orderIdWorkbookIdentity': 'b' * 64}
    value['sessionKey'] = hashlib.sha256('\n'.join(str(value[k]) for k in
        ('processId', 'startedAtUtc', 'accountWorkbookIdentity', 'orderIdWorkbookIdentity')).encode()).hexdigest()
    return value


def envelope(minute=571, second=10, *, ids=(), orders=(), executions=(), positions=(), session=None):
    raw = {'schemaId': 'ARK_NO11_BROKER_OBSERVATION_V1', 'status': 'OBSERVED',
        'capturedAt': at(minute, second - 2), 'captureCompletedAt': at(minute, second),
        'readOnly': True, 'excelSession': deepcopy(session or excel()), 'idRows': list(ids),
        'orders': deepcopy(list(orders)), 'executions': deepcopy(list(executions)),
        'positions': deepcopy(list(positions)), 'buyingPower': 1000000,
        'cashScope': 'ALL_CHANNELS_ALL_STATUSES_CASH_ONLY', 'completeTables': True, 'rowsTruncated': False,
        'sameSnapshotVerified': True, 'verificationBasis': 'DOUBLE_READ_EQUAL_NOT_ATOMIC_FEED',
        'actualFeedTimestampCertified': False, 'buyingPowerFreshnessCertified': False,
        'productionReady': False, 'orderTransmission': False}
    flags = dict.fromkeys(('executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed',
        'rssOrderFunctionAllowed', 'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed',
        'productionUpdateAllowed', 'transmitted', 'productionReady'), False)
    account = {'schemaId': 'ARK_ACCOUNT_READONLY_SNAPSHOT_V2', 'source': 'MARKETSPEED_II_RSS',
        'mode': 'READ_ONLY', 'safety': flags, 'capturedAt': at(minute, second - 1),
        'captureCompletedAt': at(minute, second - 1),
        **{k: deepcopy(raw[k]) for k in ('orders', 'executions', 'positions', 'buyingPower')}}
    return {'schemaId': 'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1', 'status': 'OBSERVED',
        'snapshot': account, 'brokerObservation': raw, 'readOnly': True,
        'productionReady': False, 'orderTransmission': False}


def config():
    return {'schemaId': s.CONFIG, 'sessionDate': DAY, 'evidenceMode': 'OFFLINE_REPLAY',
        'ledger': {'schemaId': ledger.CONFIG_SCHEMA, 'sessionDate': DAY, 'account': '特定',
            'allocatedCashJpy': '1000000', 'externalSymbols': [], 'evidenceMode': 'OFFLINE_REPLAY',
            'productionReady': False, 'orderTransmission': False},
        'transport': {'mode': 'OBSERVE_ONLY', 'orderTransmission': False},
        'orderTerms': {'orderType': 'MARKET', 'limitPrice': None, 'timeInForce': 'DAY',
                       'sor': False, 'accountType': 0, 'accountTypeVerified': True},
        'originalArrivalTable': 'synthetic-fixture-is-injected',
        'productionReady': False, 'orderTransmission': False}


def broker_rows(command, *, filled, phase=None, price=101.25, minute=571, second=14, number='1001'):
    buy = command['side'] == 'BUY'
    status = phase or ('約定' if filled == command['quantity'] else '出来有' if filled else '執行中')
    id_row = {'rssOrderId': command['rssOrderId'], 'functionName': command['functionName'],
        'orderDate': DAY, 'orderTime': command['createdAtJst'][11:19], 'orderNumber': number,
        'result': '発注済み'}
    order = {'orderNumber': number, 'status': status, 'symbol': command['symbol'][:-2],
        'account': '特定', 'side': '買付' if buy else '売付', 'trade': '現物',
        'executionCondition': '本日中', 'quantity': command['quantity'], 'filledQty': filled,
        'market': '東証', 'orderReceivedAt': command['createdAtJst'][:19] + '+09:00',
        'inputRoute': 'MARKET SPEED', 'orderType': '通常注文'}
    fills = [{'executionDate': at(minute, second), 'symbol': command['symbol'][:-2], 'account': '特定',
        'side': order['side'], 'trade': '現物', 'market': '東証', 'quantity': filled, 'price': price}] if filled else []
    return id_row, order, fills


class CoordinatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models_tmp = tempfile.TemporaryDirectory()
        root = Path(cls.models_tmp.name)
        manifest = models.synthetic_models(root, None)
        scorer = h.FrozenH235AsOf(root, DAY, manifest=manifest)
        cls.batch = {'schemaId': 'ARK_NO11_H235_ASOF_PRIVATE_RANK_BATCH_V1', 'policy': scorer.policy,
            'results': [scorer.score(models.valid_input())], 'capitalV5Executed': False, 'brokerOrders': 0,
            'productionReady': False, 'orderTransmission': False}

    @classmethod
    def tearDownClass(cls):
        cls.models_tmp.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.current = at()
        self.calls = []
        self.cfg = config()
        self.fee_path = self.root / 'charge-evidence.json'
        self.write_fees([])
        self.cfg['feesEvidenceFile'] = str(self.fee_path)
        self.open()
        self.e.observe_envelope(envelope(), self.current)

    def write_fees(self, rows):
        value = {'schemaId': 'ARK_NO11_BROKER_CHARGE_EVIDENCE_V1',
                 'sessionDate': DAY, 'orders': rows}
        self.fee_path.write_text(json.dumps(value), encoding='utf-8')

    def open(self, *, injected=True):
        self.e = s.BrokerExecution(self.root, self.cfg, arrival(), None, {'symbols': {}}, '2026-10-23',
            replay_dispatch=self.dispatch if injected else None, clock=lambda: self.current)

    def dispatch(self, packet):
        self.calls.append(deepcopy(packet))
        command = packet['command']
        return {'schemaId': 'ARK_NO11_MSII_TRANSPORT_RESULT_V1', 'commandId': command['commandId'],
            'commandSha256': command['commandSha256'], 'rssOrderId': command['rssOrderId'],
            'status': 'SENT_AWAITING_RECONCILIATION', 'dispatchAttempted': True,
            'simulatedSink': True, 'orderTransmission': False}

    def tearDown(self):
        self.e.close()
        self.tmp.cleanup()

    def buy(self):
        result = self.e.fund(deepcopy(self.batch), {}, self.current)
        self.assertTrue(result['originalAllocatorExecuted'])
        self.assertEqual(len(self.calls), 1)
        return self.calls[0]['command']

    def test_original_capital_to_partial_cancel_eod_sell_and_restart_no_resend(self):
        command = self.buy()
        self.assertGreater(command['quantity'], 100)
        self.assertEqual(self.e.book.snapshot(self.current)['positionCount'], 0)
        ident, buy, fills = broker_rows(command, filled=100)
        holding = {'symbol': '7203', 'account': '特定', 'quantity': 100}
        self.current = at(second=22)
        self.e.observe_envelope(envelope(second=20, ids=[ident], orders=[buy], executions=fills, positions=[holding]), self.current)
        state = self.e.book.snapshot(self.current)
        self.assertEqual(state['positions'][command['intentId'] if command['intentId'] in state['positions'] else self.batch['results'][0]['candidateId']]['quantity'], 100)
        self.assertEqual(state['cashJpy'], '989875')
        self.assertIn('FEES_OR_TAXES_UNRECONCILED', state['blockers'])
        self.assertTrue(state['orders'][command['intentId']]['brokerBindingVerified'])
        reserve = Decimal(state['reservedCashJpy'])
        self.assertGreater(reserve, 0)
        self.e.cancel_buys(self.current)
        cancel = self.calls[-1]['command']
        self.assertEqual(cancel['functionName'], 'RssCancelOrder')
        self.assertEqual(cancel['arguments'], [str(cancel['rssOrderId']), '0', '1001'])
        self.assertEqual(Decimal(self.e.book.snapshot(self.current)['reservedCashJpy']), reserve)
        cancel_id = dict(ident, rssOrderId=cancel['rssOrderId'], functionName='RssCancelOrder', orderTime=self.current[11:19])
        buy['status'] = '取消中（出来有）'
        self.current = at(second=27)
        self.e.observe_envelope(envelope(second=25, ids=[ident, cancel_id], orders=[buy], executions=fills, positions=[holding]), self.current)
        self.assertEqual(Decimal(self.e.book.snapshot(self.current)['reservedCashJpy']), reserve)
        buy['status'] = '取消済（出来有）'
        self.current = at(second=32)
        self.e.observe_envelope(envelope(second=30, ids=[ident, cancel_id], orders=[buy], executions=fills, positions=[holding]), self.current)
        self.assertEqual(self.e.book.snapshot(self.current)['reservedCashJpy'], '0')
        self.current = at(920, 12)
        self.e.observe_envelope(envelope(920, 10, ids=[ident, cancel_id], orders=[buy], executions=fills, positions=[holding]), self.current)
        result = self.e.evaluate_exits({}, self.current)
        self.assertEqual(result['intents'][0]['exitReason'], 'EOD_1520')
        sell = self.calls[-1]['command']
        self.assertEqual(sell['side'], 'SELL')
        self.assertEqual(sell['quantity'], 100)
        sell_id, sell_order, sell_fills = broker_rows(sell, filled=100, price=102, minute=920, second=14, number='1002')
        self.current = at(920, 22)
        latest = envelope(920, 20, ids=[ident, cancel_id, sell_id], orders=[buy, sell_order], executions=fills + sell_fills)
        self.e.observe_envelope(latest, self.current)
        state = self.e.book.snapshot(self.current)
        self.assertEqual(state['cashJpy'], '1000075')
        self.assertEqual(state['positionCount'], 0)
        self.assertTrue(state['firstSellFillBuyHalt'])
        self.assertFalse(state['newBuysAllowed'])
        before = len(self.calls)
        self.e.close()
        self.current = at(920, 23)
        self.open()
        self.e.observe_envelope(latest, self.current)
        self.e.heartbeat(self.current, observe=False)
        self.assertEqual(len(self.calls), before)
        self.assertEqual(self.e.book.snapshot(self.current)['cashJpy'], state['cashJpy'])
        self.assertFalse(self.e.summary()['realFillsAppliedToShadow'])

    def test_readonly_mode_produces_draft_without_reservation_or_transport(self):
        self.e.replay_dispatch = None
        self.e.fund(deepcopy(self.batch), {}, self.current)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.e.book.snapshot(self.current)['orders'], {})
        self.assertEqual(len(self.e.drafts), 1)
        self.assertEqual(self.e.drafts[0]['arguments'][1], '0')
        self.assertFalse(self.e.summary()['orderTransmission'])

    def test_loss_after_begin_is_unknown_and_restart_does_not_resend(self):
        def lost(packet):
            self.calls.append(packet)
            raise RuntimeError('lost reply')
        self.e.replay_dispatch = lost
        self.e.fund(deepcopy(self.batch), {}, self.current)
        state = self.e.book.snapshot(self.current)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(next(iter(state['orders'].values()))['phase'], 'UNKNOWN')
        self.assertGreater(Decimal(state['reservedCashJpy']), 0)
        self.e.close()
        self.open()
        self.e.observe_envelope(envelope(), self.current)
        self.e.fund(deepcopy(self.batch), {}, self.current)
        self.assertEqual(len(self.calls), 1)

    def test_crash_after_begin_has_no_retry(self):
        def crashed(packet):
            self.calls.append(packet)
            raise KeyboardInterrupt
        self.e.replay_dispatch = crashed
        with self.assertRaises(KeyboardInterrupt):
            self.e.fund(deepcopy(self.batch), {}, self.current)
        self.assertEqual(next(iter(self.e.book.snapshot(self.current)['commands'].values()))['state'], 'IN_FLIGHT')
        self.e.close()
        self.open()
        self.e.observe_envelope(envelope(), self.current)
        self.e.fund(deepcopy(self.batch), {}, self.current)
        self.assertEqual(len(self.calls), 1)

    def test_restart_abandons_prepared_order_without_sending_or_reusing_rss_id(self):
        # Crash after the reservation committed, before begin_dispatch was
        # entered. Recovery must not infer that a broker cancellation occurred.
        with patch.object(self.e, '_dispatch', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.e.fund(deepcopy(self.batch), {}, self.current)
        before = self.e.book.snapshot(self.current)
        order = next(iter(before['orders'].values()))
        command = before['commands'][order['commandId']]
        self.assertEqual(command['state'], 'PREPARED')
        self.assertIsNone(command['begunAtJst'])
        self.assertGreater(Decimal(before['reservedCashJpy']), 0)
        self.assertEqual(self.calls, [])
        self.e.close()
        self.open()
        after = self.e.book.snapshot(self.current)
        self.assertEqual(after['orders'][order['intentId']]['phase'], 'LOCAL_WITHDRAWN')
        self.assertEqual(after['commands'][order['commandId']]['state'], 'NOT_SENT')
        self.assertFalse(after['commands'][order['commandId']]['brokerObserved'])
        self.assertEqual(after['reservedCashJpy'], '0')
        self.e.observe_envelope(envelope(), self.current)
        self.assertGreater(self.e._fresh_id(self.current), command['command']['rssOrderId'])
        self.e.fund(deepcopy(self.batch), {}, self.current)
        self.assertEqual(self.calls, [])

    def test_restart_abandons_prepared_cancel_and_retains_unfilled_buy_reserve(self):
        command = self.buy()
        ident, buy, _ = broker_rows(command, filled=0)
        self.current = at(second=22)
        observed = envelope(second=20, ids=[ident], orders=[buy])
        self.e.observe_envelope(observed, self.current)
        reserve = self.e.book.snapshot(self.current)['reservedCashJpy']
        with patch.object(self.e, '_dispatch', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.e.cancel_buys(self.current)
        before = self.e.book.snapshot(self.current)
        cancels = [c for c in before['commands'].values() if c['command']['kind'] == 'CANCEL']
        self.assertEqual(len(cancels), 1)
        cancel = cancels[0]
        self.assertEqual(cancel['state'], 'PREPARED')
        self.assertIsNone(cancel['begunAtJst'])
        self.assertTrue(before['orders'][command['intentId']]['cancelRequested'])
        self.e.close()
        self.open()
        after = self.e.book.snapshot(self.current)
        order = after['orders'][command['intentId']]
        recovered = after['commands'][cancel['command']['commandId']]
        self.assertEqual(recovered['state'], 'NOT_SENT')
        self.assertFalse(recovered['brokerObserved'])
        self.assertFalse(order['cancelRequested'])
        self.assertEqual(order['phase'], 'ACKNOWLEDGED')
        self.assertEqual(order['observedPhase'], 'ACKNOWLEDGED')
        self.assertEqual(after['reservedCashJpy'], reserve)
        self.assertGreater(Decimal(reserve), 0)
        self.e.observe_envelope(observed, self.current)
        self.assertGreater(self.e._fresh_id(self.current), cancel['command']['rssOrderId'])
        self.assertEqual(len(self.calls), 1)

    def test_receipt_transaction_integrity_failure_propagates_and_replay_can_recover(self):
        command = self.buy()
        ident, buy, fills = broker_rows(command, filled=100)
        holding = {'symbol': '7203', 'account': '特定', 'quantity': 100}
        self.current = at(second=22)
        observed = envelope(second=20, ids=[ident], orders=[buy], executions=fills, positions=[holding])
        before = self.e.book.snapshot(self.current)
        source_before = self.e.book.source_checkpoint('broker.normalized')
        with patch.object(self.e.book, '_invariants', side_effect=ValueError('NO11_BROKER_LEDGER_POSITION_QUANTITY_INVARIANT')):
            with self.assertRaisesRegex(ValueError, 'POSITION_QUANTITY_INVARIANT'):
                self.e.observe_envelope(observed, self.current)
        after = self.e.book.snapshot(self.current)
        self.assertEqual(after['positions'], {})
        self.assertEqual(after['cashJpy'], before['cashJpy'])
        self.assertEqual(after['reservedCashJpy'], before['reservedCashJpy'])
        self.assertEqual(self.e.book.source_checkpoint('broker.normalized'), source_before)
        self.assertFalse(self.e.book.source_checkpoint('broker.receiptSemantics'))
        self.e.observe_envelope(observed, self.current)
        recovered = self.e.book.snapshot(self.current)
        self.assertEqual(recovered['orders'][command['intentId']]['cumulativeQuantity'], 100)
        self.assertEqual(sum(p['quantity'] for p in recovered['positions'].values()), 100)
        self.assertEqual(recovered['cashJpy'], '989875')
        self.assertEqual(len(self.calls), 1)

    def test_file_observation_does_not_downgrade_ledger_integrity_failure_to_source_error(self):
        command = self.buy()
        ident, buy, fills = broker_rows(command, filled=100)
        holding = {'symbol': '7203', 'account': '特定', 'quantity': 100}
        self.current = at(second=22)
        observed = envelope(second=20, ids=[ident], orders=[buy], executions=fills, positions=[holding])
        filename = self.root / 'account-observation.json'
        filename.write_text(json.dumps(observed), encoding='utf-8')
        with patch.dict(s.os.environ, {'ARK_NO11_ACCOUNT_OBSERVATION_FILE': str(filename)}):
            with patch.object(self.e.book, '_invariants', side_effect=ValueError('NO11_BROKER_LEDGER_POSITION_QUANTITY_INVARIANT')):
                with self.assertRaisesRegex(ValueError, 'POSITION_QUANTITY_INVARIANT'):
                    self.e.observe_file(self.current)
            self.assertIsNone(self.e.last_raw_hash)
            self.assertEqual(self.e.book.snapshot(self.current)['positions'], {})
            self.assertTrue(self.e.observe_file(self.current))
        self.assertEqual(self.e.book.snapshot(self.current)['orders'][command['intentId']]['cumulativeQuantity'], 100)
        self.assertEqual(len(self.calls), 1)

    def test_malformed_fee_file_keeps_confirmed_quantity_and_existing_sell_path(self):
        command = self.buy()
        self.fee_path.write_text('{not-json', encoding='utf-8')
        ident, buy, fills = broker_rows(command, filled=100)
        holding = {'symbol': '7203', 'account': '特定', 'quantity': 100}
        self.current = at(second=22)
        self.e.observe_envelope(envelope(second=20, ids=[ident], orders=[buy], executions=fills, positions=[holding]), self.current)
        state = self.e.book.snapshot(self.current)
        self.assertEqual(state['orders'][command['intentId']]['cumulativeQuantity'], 100)
        self.assertEqual(sum(p['quantity'] for p in state['positions'].values()), 100)
        self.assertEqual(state['cashJpy'], '989875')
        self.assertIn('FEES_OR_TAXES_UNRECONCILED', state['blockers'])
        self.assertIn('charges', self.e.book.source_checkpoint('broker.unresolved'))
        self.assertTrue(self.e._capital_input({'7203.T': {'C': 101.25}}, self.current)['entryBlocked'])
        self.current = at(920, 22)
        self.e.observe_envelope(envelope(920, 20, ids=[ident], orders=[buy], executions=fills, positions=[holding]), self.current)
        result = self.e.evaluate_exits({}, self.current)
        self.assertEqual(result['intents'][0]['exitReason'], 'EOD_1520')
        self.assertEqual(self.calls[-1]['command']['kind'], 'ORDER')
        self.assertEqual(self.calls[-1]['command']['side'], 'SELL')
        self.assertEqual(self.calls[-1]['command']['quantity'], 100)

    def test_unresolved_observation_after_completed_buy_blocks_new_buy_but_allows_sell(self):
        original = s.decisions.calculate_capital(deepcopy(self.batch), self.e._capital_input({}, self.current), arrival())['intents'][0]
        command = self.buy()
        ident, buy, fills = broker_rows(command, filled=command['quantity'])
        holding = {'symbol': '7203', 'account': '特定', 'quantity': command['quantity']}
        self.write_fees([{'sessionDate': DAY, 'brokerOrderNumber': '1001', 'knownAtJst': at(second=20),
            'sourceSha256': 'f' * 64, 'cumulativeQuantity': command['quantity'],
            'cumulativeFeesJpy': '0', 'cumulativeTaxesJpy': '0'}])
        self.current = at(second=22)
        self.e.observe_envelope(envelope(second=20, ids=[ident], orders=[buy], executions=fills, positions=[holding]), self.current)
        self.assertTrue(self.e.book.snapshot(self.current)['newBuysAllowed'])
        self.assertFalse(self.e.book.source_checkpoint('broker.unresolved'))
        # The previously proven fill stays owned even if the current order
        # list temporarily omits the row. This creates a controller blocker.
        self.current = at(second=27)
        self.e.observe_envelope(envelope(second=25, ids=[ident], executions=fills, positions=[holding]), self.current)
        state = self.e.book.snapshot(self.current)
        self.assertEqual(state['orders'][command['intentId']]['phase'], 'FILLED')
        self.assertTrue(state['newBuysAllowed'])
        self.assertIn(command['intentId'], self.e.book.source_checkpoint('broker.unresolved'))
        self.assertTrue(self.e._capital_input({'7203.T': {'C': 101.25}}, self.current)['entryBlocked'])
        next_buy = dict(original, intentId='d' * 64, entryId='separate-entry', symbol='6758.T', createdAtJst=self.current)
        with self.assertRaisesRegex(ValueError, 'NEW_BUY_ADMISSION'):
            self.e.submit_intents([next_buy], self.current)
        self.assertEqual(len(self.calls), 1)
        self.current = at(920, 22)
        self.e.observe_envelope(envelope(920, 20, ids=[ident], executions=fills, positions=[holding]), self.current)
        result = self.e.evaluate_exits({}, self.current)
        self.assertEqual(result['intents'][0]['exitReason'], 'EOD_1520')
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[-1]['command']['side'], 'SELL')
        self.assertEqual(self.calls[-1]['command']['quantity'], command['quantity'])

    def test_delayed_id_does_not_classify_own_fill_as_personal_or_assume_ownership(self):
        command = self.buy()
        ident, buy, fills = broker_rows(command, filled=100)
        holding = {'symbol': '7203', 'account': '特定', 'quantity': 100}
        self.current = at(second=22)
        self.e.observe_envelope(envelope(second=20, orders=[buy], executions=fills, positions=[holding]), self.current)
        self.assertEqual(self.e.book.snapshot(self.current)['positionCount'], 0)
        self.assertFalse(self.e.entry_halted)
        self.assertNotIn('7203.T', self.e.book.source_checkpoint('broker.externalSymbols') or [])
        self.current = at(second=27)
        self.e.observe_envelope(envelope(second=25, ids=[ident], orders=[buy], executions=fills, positions=[holding]), self.current)
        self.assertEqual(self.e.book.snapshot(self.current)['positionCount'], 1)

    def test_external_holdings_never_become_local_orders(self):
        self.current = at(second=14)
        self.e.observe_envelope(envelope(second=12, positions=[{'symbol': '7203', 'account': '特定', 'quantity': 100}]), self.current)
        result = self.e.fund(deepcopy(self.batch), {}, self.current)
        self.assertEqual(result['intents'], [])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.e.book.snapshot(self.current)['positions'], {})

    def test_whole_batch_validation_precedes_any_submission(self):
        account = self.e._capital_input({}, self.current)
        intents = s.decisions.calculate_capital(deepcopy(self.batch), account, arrival())['intents']
        bad = dict(intents[0], intentId='d' * 64, entryId='second', symbol='6758.T', quantity=99)
        with self.assertRaisesRegex(ValueError, 'QUANTITY|LOT'):
            self.e.submit_intents([intents[0], bad], self.current)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.e.book.snapshot(self.current)['orders'], {})

    def test_prepare_failure_withdraws_only_unsent_batch(self):
        account = self.e._capital_input({}, self.current)
        first = s.decisions.calculate_capital(deepcopy(self.batch), account, arrival())['intents'][0]
        first['quantity'] = 100
        bad = dict(first, intentId='d' * 64, entryId='second', symbol='6758.T', quantity=10000000)
        with self.assertRaisesRegex(ValueError, 'BOUND'):
            self.e.submit_intents([first, bad], self.current)
        self.assertEqual(self.calls, [])
        state = self.e.book.snapshot(self.current)
        self.assertEqual(state['reservedCashJpy'], '0')
        self.assertEqual(state['orders'][first['intentId']]['phase'], 'LOCAL_WITHDRAWN')

    def test_future_or_rewritten_candidate_cannot_send(self):
        future = deepcopy(self.batch)
        future['results'][0]['decisionAtJst'] = at(572)
        with self.assertRaisesRegex(ValueError, 'CANDIDATE_FROM_FUTURE'):
            self.e.fund(future, {}, self.current)
        self.assertEqual(self.calls, [])
        self.buy()
        changed = deepcopy(self.batch)
        changed['results'][0]['raw_reference'] += 1
        with self.assertRaisesRegex(ValueError, 'CANDIDATE_CHANGED'):
            self.e.fund(changed, {}, self.current)
        self.assertEqual(len(self.calls), 1)

    def test_stale_candidates_are_consumed_without_retroactive_order(self):
        self.current = at(572, 12)
        self.e.observe_envelope(envelope(572, 10), self.current)
        self.assertIsNone(self.e.fund(deepcopy(self.batch), {}, self.current))
        self.assertEqual(self.calls, [])
        self.assertEqual(len(self.e.book.source_checkpoint('capital.consumed')), 1)

    def test_malformed_envelope_cannot_skip_cross_book_match(self):
        for field in ('snapshot', 'readOnly', 'schemaId'):
            value = envelope()
            del value[field]
            with self.assertRaisesRegex(ValueError, 'ACCOUNT_ENVELOPE'):
                self.e.observe_envelope(value, self.current)

    def test_observed_account_requires_independent_buying_power_refresh(self):
        self.e.close()
        other = self.root / 'observed'
        other.mkdir()
        self.cfg['evidenceMode'] = self.cfg['ledger']['evidenceMode'] = 'BROKER_OBSERVATION'
        self.e = s.BrokerExecution(other, self.cfg, arrival(), None, {'symbols': {}}, '2026-10-23', clock=lambda: self.current)
        self.e.observe_envelope(envelope(), self.current)
        result = self.e.fund(deepcopy(self.batch), {}, self.current)
        self.assertEqual(result['intents'], [])
        self.assertFalse(self.e.summary()['buyingPowerRefreshVerified'])
        self.assertEqual(self.calls, [])

    def test_readonly_guard_rejects_live_configuration_before_assets_or_sink(self):
        value = config()
        value['evidenceMode'] = value['ledger']['evidenceMode'] = 'BROKER_OBSERVATION'
        value['orderTransmission'] = True
        value['transport'] = {'mode': 'LIVE', 'orderTransmission': True, 'operatorEnabled': True,
                              'approvedForSession': True, 'sessionDate': DAY}
        with self.assertRaisesRegex(ValueError, 'READONLY_LAUNCHER'):
            s.validate_config(value, DAY, read_only=True)

    def test_config_change_cannot_reuse_session_ledger(self):
        self.e.close()
        changed = deepcopy(self.cfg)
        changed['orderTerms']['sor'] = True
        with self.assertRaisesRegex(ValueError, 'RECOVERY_CONFIG'):
            s.BrokerExecution(self.root, changed, arrival(), None, {'symbols': {}}, '2026-10-23', clock=lambda: self.current)
        self.open()


if __name__ == '__main__':
    unittest.main()
