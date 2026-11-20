"""Independent observed-row allocation tests; no Excel, account, or sender."""
from copy import deepcopy
from itertools import product
from pathlib import Path
import hashlib
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import no11_broker_fill_attribution as a
import no11_broker_execution_ledger as ledger
import test_no11_frozen_p1_broker_execution_ledger as lf

DAY = '2026-10-26'
def at(second): return DAY + 'T09:30:%02d+09:00' % second


def seal(snapshot):
    result = deepcopy(snapshot)
    result.pop('snapshotSha256', None)
    result['snapshotSha256'] = hashlib.sha256(ledger.ordered_json_bytes(result)).hexdigest()
    return result


def fixture(quantity=200, filled=100, price=100.1):
    origin = {'sessionDate': DAY, 'intentId': 'a' * 64, 'rssSessionKey': 'b' * 64,
        'rssOrderId': 81, 'createdAtJst': at(10), 'symbol': '7203.T', 'side': 'BUY',
        'account': '特定', 'quantity': quantity}
    order = {'orderNumber': '12345', 'symbol': '7203', 'account': '特定', 'side': '買付',
        'trade': '現物', 'market': '東証', 'quantity': quantity, 'filledQty': filled,
        'status': '約定' if filled == quantity else '出来有' if filled else '執行中',
        'orderReceivedAt': at(10)}
    execution = {'symbol': '7203', 'account': '特定', 'side': '買付', 'trade': '現物',
                 'market': '東証', 'quantity': filled, 'price': price, 'executionDate': at(12)}
    snapshot = {'schemaId': a.SNAPSHOT, 'sessionDate': DAY, 'sessionKey': 'b' * 64,
        'capturedAt': at(18), 'captureCompletedAt': at(20), 'snapshotSha256': 'c' * 64,
        'idRows': [{'rssOrderId': 81, 'functionName': 'RssStockOrder', 'orderDate': DAY,
                    'orderTime': '09:30:10', 'orderNumber': '12345'}],
        'orders': [order], 'executions': [execution] if filled else [], 'positions': [],
        'readOnly': True, 'productionReady': False, 'orderTransmission': False,
        'sameSnapshotVerified': True, 'verificationBasis': 'DOUBLE_READ_EQUAL_NOT_ATOMIC_FEED',
        'cashScope': 'ALL_CHANNELS_ALL_STATUSES_CASH_ONLY', 'completeTables': True,
        'rowsTruncated': False, 'actualFeedTimestampCertified': False, 'buyingPowerFreshnessCertified': False}
    return origin, seal(snapshot)


def run(origin, snapshot, previous=None, **kwargs):
    through = kwargs.pop('through', at(22))
    return a.attribute_order(origin, seal(snapshot), session=DAY, through=through,
                             source_state=previous, evidence_mode='OFFLINE_REPLAY', **kwargs)


class AttributionTests(unittest.TestCase):
    def test_single_order_exact_decimal_and_original_fill_time(self):
        o, s = fixture()
        result = run(o, s)
        r = result['receipt']
        self.assertEqual(r['cumulativeGrossJpy'], '10010')
        self.assertEqual(r['filledAtJst'], at(12))
        self.assertTrue(r['quantityAttributionVerified'])
        self.assertTrue(r['attributionVerified'])
        self.assertIsNone(r['cumulativeFeesJpy'])
        self.assertIsNone(r['cumulativeTaxesJpy'])
        self.assertFalse(result['orderTransmission'])

    def test_identical_rows_preserve_multiplicity(self):
        o, s = fixture(filled=200)
        s['executions'][0]['quantity'] = 100
        s['executions'].append(deepcopy(s['executions'][0]))
        result = run(o, s)
        self.assertEqual(result['receipt']['cumulativeGrossJpy'], '20020')
        self.assertEqual(list(result['sourceState']['executionRows'].values()), [2])

    def test_two_possible_order_prices_remain_unresolved_quantity_preserved(self):
        o, s = fixture()
        s['orders'].append(dict(s['orders'][0], orderNumber='67890'))
        s['executions'].append(dict(s['executions'][0], price=101.1))
        r = run(o, s)
        self.assertIn('AMBIGUOUS_ORDER_EXECUTION_PRICE', r['blockers'])
        self.assertEqual(r['receipt']['cumulativeQuantity'], 100)
        self.assertIsNone(r['receipt']['cumulativeGrossJpy'])
        self.assertTrue(r['receipt']['quantityAttributionVerified'])
        self.assertFalse(r['receipt']['attributionVerified'])

    def test_equal_price_aggregate_row_can_split_without_false_ambiguity(self):
        o, s = fixture()
        s['orders'].append(dict(s['orders'][0], orderNumber='67890'))
        s['executions'][0]['quantity'] = 200
        r = run(o, s)['receipt']
        self.assertEqual(r['cumulativeGrossJpy'], '10010')
        self.assertIsNone(r['filledAtJst'])

    def test_order_time_constraint_can_prove_unique_gross(self):
        o, s = fixture()
        s['orders'].append(dict(s['orders'][0], orderNumber='67890', orderReceivedAt=at(15)))
        s['executions'].append(dict(s['executions'][0], price=101.1, executionDate=at(17)))
        r = run(o, s)['receipt']
        self.assertEqual(r['cumulativeGrossJpy'], '10010')

    def test_quantity_mismatch_does_not_create_a_fill_price(self):
        o, s = fixture()
        s['executions'] = []
        r = run(o, s)
        self.assertIsNone(r['receipt']['cumulativeGrossJpy'])
        self.assertIn('ORDER_EXECUTION_QUANTITY_OR_TIME_MISMATCH', r['blockers'])

    def test_cancelled_partial_position_is_not_erased(self):
        o, s = fixture()
        s['orders'][0]['status'] = '取消済（出来有）'
        r = run(o, s)['receipt']
        self.assertEqual(r['status'], 'CANCELLED')
        self.assertEqual(r['cumulativeQuantity'], 100)
        self.assertEqual(r['cumulativeGrossJpy'], '10010')

    def test_no_fill_ack_has_zero_gross_not_unknown_cost(self):
        o, s = fixture(filled=0)
        r = run(o, s)['receipt']
        self.assertEqual(r['status'], 'ACKNOWLEDGED')
        self.assertEqual(r['cumulativeGrossJpy'], '0')
        self.assertIsNone(r['filledAtJst'])

    def test_wrong_broker_number_never_substituted_by_symbol(self):
        o, s = fixture()
        s['orders'][0]['orderNumber'] = '999'
        with self.assertRaisesRegex(ValueError, 'ORDER_DISAPPEARED'):
            run(o, s)

    def test_identity_and_cumulative_regression_rejected(self):
        for field, value in [('account', '一般'), ('side', '売付'), ('quantity', 300)]:
            o, s = fixture()
            s['orders'][0][field] = value
            with self.assertRaisesRegex(ValueError, 'ORDER_IDENTITY_CHANGED'):
                run(o, s)
        o, s = fixture()
        o['cumulativeQuantity'] = 150
        with self.assertRaisesRegex(ValueError, 'CUMULATIVE_FILL_REVERSED'):
            run(o, s)

    def test_excel_restart_requires_already_proven_broker_binding(self):
        o, s = fixture()
        s['sessionKey'] = 'd' * 64
        with self.assertRaisesRegex(ValueError, 'ORIGIN_NOT_BOUND'):
            run(o, s)
        o.update(brokerOrderNumber='12345', brokerBindingVerified=True)
        r = run(o, s)
        self.assertEqual(r['receipt']['cumulativeGrossJpy'], '10010')
        self.assertFalse(r['bindingFromCurrentId'])
        self.assertEqual(r['receipt']['rssSessionKey'], 'b' * 64)

    def test_id_remapping_rejected_even_when_symbol_matches(self):
        o, s = fixture()
        o.update(brokerOrderNumber='999', brokerBindingVerified=True)
        with self.assertRaisesRegex(ValueError, 'BROKER_NUMBER_CHANGED'):
            run(o, s)

    def test_source_revision_is_latched_after_restart(self):
        o, s = fixture()
        first = run(o, s)
        s['capturedAt'], s['captureCompletedAt'], s['snapshotSha256'] = at(19), at(21), 'd' * 64
        s['executions'][0]['price'] = 99.9
        r = run(o, s, first['sourceState'])
        self.assertIn('EXECUTION_ROWS_REMOVED_OR_REVISED', r['blockers'])
        self.assertIsNone(r['receipt']['cumulativeGrossJpy'])
        s['executions'][0]['price'] = 100.1
        s['capturedAt'], s['captureCompletedAt'] = at(20), at(22)
        self.assertIn('EXECUTION_ROWS_REMOVED_OR_REVISED', run(o, s, r['sourceState'])['blockers'])

    def test_input_immutable_and_replay_has_same_event_id(self):
        o, s = fixture()
        before = deepcopy((o, s))
        first, second = run(o, s), run(o, s)
        self.assertEqual(first['receipt']['eventId'], second['receipt']['eventId'])
        self.assertEqual(before, (o, s))

    def test_fee_evidence_is_separate_and_bound_to_order(self):
        o, s = fixture()
        fees = {'sessionDate': DAY, 'brokerOrderNumber': '12345', 'knownAtJst': at(20),
                'sourceSha256': 'f' * 64, 'cumulativeQuantity': 100,
                'cumulativeFeesJpy': '11', 'cumulativeTaxesJpy': '0'}
        self.assertEqual(run(o, s, fees=fees)['receipt']['cumulativeFeesJpy'], '11')
        fees['brokerOrderNumber'] = '999'
        result = run(o, s, fees=fees)
        self.assertIn('FEE_EVIDENCE_UNUSABLE', result['blockers'])
        self.assertIsNone(result['receipt']['cumulativeFeesJpy'])
        self.assertEqual(result['receipt']['cumulativeQuantity'], 100)

    def test_100ns_future_capture_and_impossible_date_rejected(self):
        o, s = fixture()
        s['captureCompletedAt'] = at(22).replace('+09:00', '.0000001+09:00')
        with self.assertRaisesRegex(ValueError, 'FUTURE_SNAPSHOT'):
            run(o, s)
        with self.assertRaisesRegex(ValueError, 'CLOCK'):
            a.instant('2026-02-29T09:00:00+09:00')

    def test_market_mismatch_never_credits_a_tse_price(self):
        o, s = fixture()
        s['executions'][0]['market'] = 'JNX'
        r = run(o, s)
        self.assertIn('EXECUTION_MARKET_UNRESOLVED', r['blockers'])
        self.assertIsNone(r['receipt']['cumulativeGrossJpy'])

    def test_snapshot_hash_uses_real_normalizer_member_order_and_detects_tampering(self):
        o, s = fixture()
        body = {k: v for k, v in s.items() if k != 'snapshotSha256'}
        self.assertNotEqual(s['snapshotSha256'], ledger.digest(body))
        s['executions'][0]['price'] = 99.9
        with self.assertRaisesRegex(ValueError, 'SNAPSHOT_HASH_CHANGED'):
            a.attribute_order(o, s, session=DAY, through=at(22), evidence_mode='OFFLINE_REPLAY')

    def test_snapshot_must_keep_double_read_completeness_and_readonly_guards(self):
        for patch in [{'readOnly': False}, {'completeTables': False}, {'rowsTruncated': True},
                      {'sameSnapshotVerified': False}, {'actualFeedTimestampCertified': True},
                      {'buyingPowerFreshnessCertified': True}, {'productionReady': True}]:
            o, s = fixture()
            s.update(patch)
            with self.assertRaisesRegex(ValueError, 'NORMALIZED_READONLY_SOURCE_REQUIRED'):
                run(o, s)

    def test_event_identity_is_unchanged_after_mutable_ledger_fields_are_populated(self):
        o, s = fixture()
        first = run(o, s)
        after = dict(o, brokerOrderNumber='12345', brokerBindingVerified=True,
                     cumulativeQuantity=100, knownGrossJpy='10010', grossVerifiedThroughQuantity=100,
                     filledAtJst=at(12),
                     fillTimeVerified=True, phase='PARTIAL', lastReceiptSha256='e' * 64)
        replay = run(after, s, first['sourceState'])
        self.assertEqual(first['receipt'], replay['receipt'])
        self.assertEqual(first['allocationEvidence'], replay['allocationEvidence'])

    def test_group_above_price_solver_capacity_keeps_confirmed_target_quantity(self):
        o, s = fixture()
        for index in range(300):
            s['orders'].append(dict(s['orders'][0], orderNumber=str(20000 + index)))
            s['executions'].append(deepcopy(s['executions'][0]))
        result = run(o, s)
        self.assertIn('PRICE_ATTRIBUTION_CAPACITY', result['blockers'])
        self.assertEqual(result['receipt']['cumulativeQuantity'], 100)
        self.assertIsNone(result['receipt']['cumulativeGrossJpy'])
        self.assertTrue(result['receipt']['quantityAttributionVerified'])

    def test_an_execution_row_cannot_be_treated_as_an_indivisible_unique_fill(self):
        o, s = fixture(quantity=100, filled=100, price=100)
        s['orders'].append(dict(s['orders'][0], orderNumber='67890'))
        s['executions'][0]['quantity'] = 150
        s['executions'].append(dict(s['executions'][0], quantity=50, price=102))
        result = run(o, s)
        self.assertIn('AMBIGUOUS_ORDER_EXECUTION_PRICE', result['blockers'])
        self.assertIsNone(result['receipt']['cumulativeGrossJpy'])

    def test_fee_record_cannot_cover_a_different_or_missing_cumulative_quantity(self):
        o, s = fixture()
        for q in [0, 200, None, True]:
            fee = {'sessionDate': DAY, 'brokerOrderNumber': '12345', 'knownAtJst': at(20),
                   'sourceSha256': 'f' * 64, 'cumulativeQuantity': q,
                   'cumulativeFeesJpy': '0', 'cumulativeTaxesJpy': '0'}
            result = run(o, s, fees=fee)
            self.assertIn('FEE_EVIDENCE_UNUSABLE', result['blockers'])
            self.assertIsNone(result['receipt']['cumulativeFeesJpy'])
            self.assertEqual(result['receipt']['cumulativeQuantity'], 100)

    def test_fee_knowledge_after_the_snapshot_is_not_backdated(self):
        o, s = fixture()
        fees = {'sessionDate': DAY, 'brokerOrderNumber': '12345', 'knownAtJst': at(21),
                'sourceSha256': 'f' * 64, 'cumulativeQuantity': 100,
                'cumulativeFeesJpy': '11', 'cumulativeTaxesJpy': '0'}
        result = run(o, s, fees=fees)
        self.assertEqual(result['receipt']['knownAtJst'], at(21))
        self.assertEqual(result['receipt']['quantityKnownAtJst'], at(20))
        self.assertEqual(result['receipt']['cumulativeFeesJpy'], '11')

    def test_fee_evidence_predating_the_fill_does_not_pretend_charges_are_zero(self):
        o, s = fixture()
        fees = {'sessionDate': DAY, 'brokerOrderNumber': '12345', 'knownAtJst': at(11),
                'sourceSha256': 'f' * 64, 'cumulativeQuantity': 100,
                'cumulativeFeesJpy': '0', 'cumulativeTaxesJpy': '0'}
        result = run(o, s, fees=fees)
        self.assertIn('FEE_EVIDENCE_UNUSABLE', result['blockers'])
        self.assertIsNone(result['receipt']['cumulativeFeesJpy'])
        self.assertEqual(result['receipt']['knownAtJst'], at(20))

    def test_fee_evidence_must_not_predate_when_the_fill_quantity_became_known(self):
        o, s = fixture()
        fees = {'sessionDate': DAY, 'brokerOrderNumber': '12345', 'knownAtJst': at(13),
                'sourceSha256': 'f' * 64, 'cumulativeQuantity': 100,
                'cumulativeFeesJpy': '0', 'cumulativeTaxesJpy': '0'}
        result = run(o, s, fees=fees)
        self.assertIn('FEE_EVIDENCE_UNUSABLE', result['blockers'])
        self.assertEqual(result['receipt']['cumulativeQuantity'], 100)
        self.assertIsNone(result['receipt']['cumulativeFeesJpy'])

    def test_noncanonical_or_out_of_range_fee_record_cannot_hide_positive_shares(self):
        o, s = fixture()
        for invalid in [float('nan'), float('inf'), '999999999999999']:
            fees = {'sessionDate': DAY, 'brokerOrderNumber': '12345', 'knownAtJst': at(20),
                    'sourceSha256': 'f' * 64, 'cumulativeQuantity': 100,
                    'cumulativeFeesJpy': invalid, 'cumulativeTaxesJpy': '0'}
            with self.subTest(value=invalid):
                result = run(o, s, fees=fees)
                self.assertIn('FEE_EVIDENCE_UNUSABLE', result['blockers'])
                self.assertEqual(result['receipt']['cumulativeQuantity'], 100)
                self.assertEqual(result['receipt']['cumulativeGrossJpy'], '10010')
                self.assertIsNone(result['receipt']['cumulativeFeesJpy'])

    def test_bound_fee_evidence_can_be_reused_for_unchanged_fill_quantity(self):
        o, s = fixture()
        fees = {'sessionDate': DAY, 'brokerOrderNumber': '12345', 'knownAtJst': at(20),
                'sourceSha256': 'f' * 64, 'cumulativeQuantity': 100,
                'cumulativeFeesJpy': '11', 'cumulativeTaxesJpy': '0'}
        first = run(o, s, fees=fees)
        o.update(cumulativeQuantity=100, quantityKnownAtJst=at(20), brokerOrderNumber='12345',
                 brokerBindingVerified=True, filledAtJst=at(12), fillTimeVerified=True)
        s['capturedAt'], s['captureCompletedAt'] = at(21), at(22)
        result = run(o, s, first['sourceState'], fees=fees)
        self.assertEqual(result['receipt']['cumulativeFeesJpy'], '11')
        self.assertNotIn('FEE_EVIDENCE_UNUSABLE', result['blockers'])

    def test_old_fee_cannot_cover_newly_observed_matching_executions(self):
        o, s = fixture()
        first = run(o, s)
        o.update(cumulativeQuantity=100, quantityKnownAtJst=at(20), brokerOrderNumber='12345',
                 brokerBindingVerified=True, filledAtJst=at(12), fillTimeVerified=True)
        s['orders'].append(dict(s['orders'][0], orderNumber='67890'))
        s['executions'].append(dict(s['executions'][0]))
        s['capturedAt'], s['captureCompletedAt'] = at(21), at(22)
        fees = {'sessionDate': DAY, 'brokerOrderNumber': '12345', 'knownAtJst': at(20),
                'sourceSha256': 'f' * 64, 'cumulativeQuantity': 100,
                'cumulativeFeesJpy': '11', 'cumulativeTaxesJpy': '0'}
        result = run(o, s, first['sourceState'], fees=fees)
        self.assertIn('FEE_EVIDENCE_UNUSABLE', result['blockers'])
        self.assertEqual(result['receipt']['cumulativeQuantity'], 100)
        self.assertIsNone(result['receipt']['cumulativeFeesJpy'])

    def test_conflicting_money_does_not_roll_back_confirmed_quantity_in_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            book = ledger.BrokerExecutionLedger(Path(directory) / 'broker.sqlite', lf.config())
            try:
                account = {'schemaId': ledger.ACCOUNT_SCHEMA, 'sessionDate': DAY, 'account': '特定',
                    'knownAtJst': at(0), 'buyingPowerJpy': '100000', 'externalSymbols': [],
                    'evidenceMode': 'OFFLINE_REPLAY', 'sourceSnapshotSha256': 'c' * 64}
                account['eventId'] = ledger.digest(account)
                book.observe_account(account, at(0))
                intent = lf.intent(quantity=200, when=at(10))
                command = lf.command(intent, rss_id=81, session_key='b' * 64)
                book.prepare_order(intent, command, at(10))
                book.begin_dispatch(command['commandId'], at(10))
                _, snapshot = fixture()
                origin = book.snapshot()['orders'][intent['intentId']]
                fees = {'sessionDate': DAY, 'brokerOrderNumber': '12345', 'knownAtJst': at(20),
                        'sourceSha256': 'f' * 64, 'cumulativeQuantity': 100,
                        'cumulativeFeesJpy': '11', 'cumulativeTaxesJpy': '1'}
                first = run(origin, snapshot, fees=fees)
                book.apply_receipt(first['receipt'], at(22))
                cash_before = book.snapshot()['cashJpy']
                origin = book.snapshot()['orders'][intent['intentId']]
                # Emulate a crash after receipt commit but before the source
                # multiset checkpoint. The ledger's proven amounts survive.
                snapshot['capturedAt'], snapshot['captureCompletedAt'] = at(23), at(25)
                snapshot['orders'][0].update(filledQty=200, status='約定')
                snapshot['executions'][0].update(quantity=200, price=40)
                fees.update(knownAtJst=at(25), cumulativeQuantity=200,
                            cumulativeFeesJpy='5', cumulativeTaxesJpy='0')
                next_receipt = run(origin, snapshot, fees=fees, through=at(27))
                self.assertIn('CUMULATIVE_CONSIDERATION_CONFLICT', next_receipt['blockers'])
                self.assertIn('CUMULATIVE_CHARGES_CONFLICT', next_receipt['blockers'])
                self.assertEqual(next_receipt['receipt']['cumulativeQuantity'], 200)
                for key in ('cumulativeGrossJpy', 'cumulativeFeesJpy', 'cumulativeTaxesJpy'):
                    self.assertIsNone(next_receipt['receipt'][key])
                book.apply_receipt(next_receipt['receipt'], at(27))
                state = book.snapshot()
                self.assertEqual(state['positions'][intent['entryId']]['quantity'], 200)
                self.assertEqual(state['cashJpy'], cash_before)
                self.assertEqual(state['orders'][intent['intentId']]['grossVerifiedThroughQuantity'], 100)
                self.assertFalse(state['newBuysAllowed'])
                replay = run(state['orders'][intent['intentId']], snapshot, fees=fees, through=at(27))
                self.assertEqual(replay['receipt'], next_receipt['receipt'])
                self.assertTrue(book.apply_receipt(replay['receipt'], at(27))['idempotentReplay'])
            finally:
                book.close()

    def test_positive_quantity_requires_increasing_consideration_for_a_new_price_proof(self):
        o, s = fixture(filled=200, price=50.05)
        o.update(cumulativeQuantity=100, knownGrossJpy='10010', grossVerifiedThroughQuantity=100)
        result = run(o, s)
        self.assertEqual(result['receipt']['cumulativeQuantity'], 200)
        self.assertIsNone(result['receipt']['cumulativeGrossJpy'])
        self.assertIn('CUMULATIVE_CONSIDERATION_CONFLICT', result['blockers'])

    def test_amount_outside_ledger_range_preserves_the_bound_quantity(self):
        o, s = fixture(quantity=1000000000, filled=1000000000, price=9999999999999)
        result = run(o, s)
        self.assertEqual(result['receipt']['cumulativeQuantity'], 1000000000)
        self.assertIsNone(result['receipt']['cumulativeGrossJpy'])
        self.assertIn('CONSIDERATION_OUT_OF_RANGE', result['blockers'])

    def test_persisted_first_fill_survives_excel_restart_and_later_price_ambiguity(self):
        o, s = fixture()
        first = run(o, s)
        o.update(cumulativeQuantity=100, brokerOrderNumber='12345', brokerBindingVerified=True,
                 filledAtJst=at(12), fillTimeVerified=True)
        s['sessionKey'] = 'd' * 64
        s['capturedAt'], s['captureCompletedAt'] = at(20), at(22)
        s['idRows'] = []
        s['orders'].append(dict(s['orders'][0], orderNumber='67890'))
        s['executions'].append(dict(s['executions'][0], price=101.1))
        result = run(o, s, first['sourceState'])
        self.assertFalse(result['bindingFromCurrentId'])
        self.assertIsNone(result['receipt']['cumulativeGrossJpy'])
        self.assertEqual(result['receipt']['filledAtJst'], at(12))
        self.assertTrue(result['receipt']['fillTimeVerified'])

    def test_new_earlier_fill_latches_a_time_conflict_but_keeps_quantity_and_price_proof(self):
        o, s = fixture()
        first = run(o, s)
        o.update(cumulativeQuantity=100, brokerOrderNumber='12345', brokerBindingVerified=True,
                 filledAtJst=at(12), fillTimeVerified=True)
        s['orders'][0].update(filledQty=200, status='約定')
        s['executions'].append(dict(s['executions'][0], executionDate=at(11)))
        s['capturedAt'], s['captureCompletedAt'] = at(20), at(22)
        result = run(o, s, first['sourceState'])
        self.assertEqual(result['receipt']['cumulativeQuantity'], 200)
        self.assertEqual(result['receipt']['cumulativeGrossJpy'], '20020')
        self.assertTrue(result['receipt']['fillTimeConflict'])
        self.assertFalse(result['receipt']['fillTimeVerified'])
        self.assertIsNone(result['receipt']['filledAtJst'])
        o.update(cumulativeQuantity=200, fillTimeConflict=True, fillTimeVerified=False)
        replay = run(o, s, result['sourceState'])
        self.assertEqual(replay['receipt'], result['receipt'])

    def test_large_integer_consideration_is_formatted_without_decimal_context_rounding(self):
        ticks = 123456789012345678901234567890123456
        self.assertEqual(a.decimal_text(ticks), '123456789012345678901234567890.123456')


class FlowProofTests(unittest.TestCase):
    def test_bounded_integer_flow_agrees_with_exhaustive_per_share_assignments(self):
        rng = random.Random(800)
        for _ in range(100):
            rows = [{'quantity': rng.randint(1, 3), 'priceTicks': rng.randint(1, 9),
                     'timeNs': rng.choice([10, 20])} for _ in range(rng.randint(1, 3))]
            count = sum(r['quantity'] for r in rows)
            target = rng.randint(0, count)
            orders = [{'filledQty': target, 'acceptedNs': 10},
                      {'filledQty': count - target, 'acceptedNs': rng.choice([10, 20])}]
            prices = []
            # Independent exhaustive reference: split each source row at EVERY
            # share boundary, not only whole rows or predetermined test cases.
            for split in product(*(range(r['quantity'] + 1) for r in rows)):
                if sum(split) != target:
                    continue
                if any(r['timeNs'] < orders[1]['acceptedNs'] and amount != r['quantity']
                       for r, amount in zip(rows, split)):
                    continue
                prices.append(sum(r['priceTicks'] * amount for r, amount in zip(rows, split)))
            lower = a._min_cost(rows, orders, 0, True)
            other = a._min_cost(rows, orders, 0, False)
            upper = None if other is None else sum(r['priceTicks'] * r['quantity'] for r in rows) - other
            self.assertEqual(lower, min(prices) if prices else None)
            self.assertEqual(upper, max(prices) if prices else None)


if __name__ == '__main__':
    unittest.main()
