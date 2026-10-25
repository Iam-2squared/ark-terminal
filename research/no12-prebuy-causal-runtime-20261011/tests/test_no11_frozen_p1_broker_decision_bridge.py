"""Pinned decision adapters with synthetic balances, marks and receipts only.

The genuine frozen gate/allocation/EXIT functions execute. No broker, Excel,
network, account permission or transport is invoked by this suite.
"""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_broker_decision_bridge as bridge
import no11_broker_execution_ledger as ledger
import no11_h235_asof_forward_shadow as h
import no11_h235_capital_v5_shadow as cap
import no11_capital_v5_batch_capacity as native
import test_no11_frozen_p1_h235_asof as models
import test_no11_frozen_p1_execution_bundle as trace_fixtures
import test_no11_frozen_p1_broker_execution_ledger as ledger_fixtures

DAY = models.SESSION
at = models.stamp


def position(index=0, *, quantity=100, fill_time=at(573), verified=True):
    return {'entryId': 'synthetic-entry-' + str(index),
            'symbol': '%04d.T' % (9000 + index), 'account': '特定', 'band': 'B',
            'quantity': quantity, 'filledAtJst': fill_time, 'fillTimeVerified': verified}


def account(*, cash='1000000', positions=None):
    positions = [] if positions is None else deepcopy(positions)
    exposure = Decimal('100000') * len(positions)
    return {'schemaId': 'ARK_NO11_BROKER_CAPITAL_INPUT_V1', 'sessionDate': DAY,
            'decisionAtJst': at(571, 12), 'account': '特定', 'positions': positions,
            'availableCashJpy': cash, 'equityJpy': str(Decimal(cash) + exposure),
            'exposureJpy': str(exposure), 'externalSymbols': [],
            'entryBlocked': False, 'pendingOrders': False, 'reserveChargesJpy': '0'}


class CapitalDecisionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        manifest = models.synthetic_models(self.root, None)
        self.scorer = h.FrozenH235AsOf(self.root, DAY, manifest=manifest)
        self.row = self.scorer.score(models.valid_input())
        self.arrival = trace_fixtures.arrival()

    def tearDown(self):
        self.temp.cleanup()

    def batch(self, n=1, *, scores=None, prices=None):
        # Additional rows are explicit synthetic R0 contract fixtures. Their
        # probabilities/ML/bands remain internally consistent; they do not
        # claim to be outputs of private production model files.
        _, _, stair, _ = h.original_dependencies()
        rows = []
        for i in range(n):
            row = deepcopy(self.row)
            score = 1.0 if scores is None else scores[i % len(scores)]
            row.update(candidateId=h.digest(['synthetic-r0', i]), symbol='%04d.T' % (1000 + i),
                       raw_reference=100.0 if prices is None else prices[i % len(prices)],
                       ML=score, capital_score=score, B=row['M'] / score,
                       rank=stair.band(score), capacity_band=stair.band(score), admission=score >= 1)
            rows.append(row)
        return {'schemaId': 'ARK_NO11_H235_ASOF_PRIVATE_RANK_BATCH_V1',
                'policy': self.scorer.policy, 'results': sorted(rows, key=stair.candidate_order),
                'capitalV5Executed': False, 'brokerOrders': 0,
                'productionReady': False, 'orderTransmission': False}

    def native_result(self, batch, view, arrival=None):
        scenario = {'schemaId': cap.SCENARIO, 'evidenceMode': 'SYNTHETIC_OFFLINE_ONLY',
            'sessionDate': DAY, 'decisionAtJst': view['decisionAtJst'],
            'arkCapitalInputs': {'cash': view['availableCashJpy'], 'equity': view['equityJpy'],
                                 'exposure': view['exposureJpy']},
            'externalSymbols': view['externalSymbols'],
            'arkManagedSymbols': [p['symbol'] for p in view['positions']],
            'existingBands': [p['band'] for p in view['positions']],
            'afterFirstLegalSellFill': False, 'pendingBrokerOrders': False,
            'syntheticAccountOnly': True, 'productionReady': False, 'orderTransmission': False}
        return native.run_request(cap.build_request(batch, scenario, arrival or self.arrival))

    def test_original_native_parity_across_chart50_cash_bands_and_max3(self):
        for n in (0, 1, 3, 21, 47, 50):
            for occupied in (0, 1, 2, 3):
                for cash in ('0', '40020', '1000000'):
                    with self.subTest(n=n, occupied=occupied, cash=cash):
                        batch = self.batch(n, scores=[2.0, 1.75, 1.25, 1.0])
                        view = account(cash=cash, positions=[position(i) for i in range(occupied)])
                        expected = self.native_result(batch, view)
                        actual = bridge.calculate_capital(batch, view, self.arrival)
                        self.assertEqual(actual['allocations'], expected['allocations'])
                        self.assertEqual(actual['rejected'], expected['rejected'])
                        self.assertEqual(actual['allocatedDebitJpy'], expected['allocatedDebitJpy'])
                        self.assertEqual(len(actual['intents']), expected['fundedCount'])
                        self.assertLessEqual(len(actual['intents']) + occupied, 3)
                        self.assertFalse(actual['orderTransmission'])
                        self.assertFalse(actual['productionReady'])

    def test_zero_cash_validation_does_not_relabel_the_observed_balance(self):
        batch, view = self.batch(), account(cash='123456.75')
        allocator, _ = bridge.original_functions()
        with mock.patch.object(cap, 'build_request', wraps=cap.build_request) as validate, \
             mock.patch.object(allocator, 'allocation', wraps=allocator.allocation) as allocate:
            result = bridge.calculate_capital(batch, view, self.arrival)
        self.assertEqual(validate.call_args.args[1]['arkCapitalInputs'],
                         {'cash': '0', 'equity': '0', 'exposure': '0'})
        self.assertEqual(allocate.call_args.args[1:4], ('123456.75', '0', '123456.75'))
        self.assertGreater(len(result['intents']), 0)

    def test_buy_intents_match_durable_ledger_schema_and_reserve_without_fill(self):
        view, batch = account(), self.batch()
        before = deepcopy((view, batch, self.arrival))
        result = bridge.calculate_capital(batch, view, self.arrival)
        source = result['intents'][0]
        self.assertEqual(source['schemaId'], ledger.INTENT_SCHEMA)
        self.assertEqual(source['sessionDate'], DAY)
        self.assertEqual(source['reservePriceJpy'], '100.05000')
        self.assertEqual(source['sourceDecisionSha256'], h.digest(batch['results'][0]))
        book = ledger.BrokerExecutionLedger(self.root / 'intent.sqlite', ledger_fixtures.config(cash='1000000'))
        try:
            when = source['createdAtJst']
            bound = {'schemaId': ledger.ACCOUNT_SCHEMA, 'eventId': ledger.digest(['account', when]),
                     'sessionDate': DAY, 'account': '特定', 'knownAtJst': when,
                     'buyingPowerJpy': '1000000', 'externalSymbols': [], 'evidenceMode': 'OFFLINE_REPLAY',
                     'sourceSnapshotSha256': ledger.digest(['synthetic-bound', when])}
            book.observe_account(bound, when)
            book.prepare_order(source, ledger_fixtures.command(source), when)
            state = book.snapshot()
            self.assertEqual(state['positions'], {})
            self.assertEqual(state['cashJpy'], '1000000')
            self.assertGreater(Decimal(state['reservedCashJpy']), 0)
            self.assertFalse(state['actualTransportRequested'])
        finally:
            book.close()
        self.assertEqual((view, batch, self.arrival), before)

    def test_exact_100_share_threshold_and_zero_lot_admission_are_preserved(self):
        for cash, expected in [('40019.9999', 0), ('40020', 100), ('40020.0001', 100)]:
            with self.subTest(cash=cash):
                result = bridge.calculate_capital(self.batch(), account(cash=cash), self.arrival)
                self.assertEqual(result['allocations'][0]['quantity'], expected)
                self.assertEqual(len(result['intents']), int(expected > 0))
        batch = self.batch(5, scores=[2.0], prices=[10000000, 10000000, 10000000, 1, 1])
        result = bridge.calculate_capital(batch, account(), self.arrival)
        self.assertEqual(result['allocations'], self.native_result(batch, account())['allocations'])
        self.assertEqual([a['quantity'] for a in result['allocations']], [0, 0, 0])
        self.assertEqual(len(result['rejected']), 2)
        self.assertEqual(result['intents'], [])

    def test_native_b_reserve_gate_is_not_replaced_with_first_three_names(self):
        batch = self.batch(3)
        result = bridge.calculate_capital(batch, account(), self.arrival)
        self.assertEqual(result['allocations'], self.native_result(batch, account())['allocations'])
        self.assertEqual(len(result['intents']), 1)
        self.assertTrue(all(r['reason'] == 'SLOT2_RESERVE_FOR_FUTURE_QUALITY' for r in result['rejected']))

    def test_first_sell_fill_entry_halt_and_pending_gate_do_not_fund(self):
        for gate in ('entryBlocked', 'pendingOrders'):
            view = account()
            view[gate] = True
            allocator, _ = bridge.original_functions()
            with mock.patch.object(allocator, 'allocation', wraps=allocator.allocation) as allocate:
                result = bridge.calculate_capital(self.batch(3, scores=[2.0]), view, self.arrival)
            allocate.assert_not_called()
            self.assertEqual(result['intents'], [])
            self.assertEqual(len(result['rejected']), 3)

    def test_personal_symbols_and_existing_managed_symbol_cannot_buy(self):
        batch = self.batch(4, scores=[2.0])
        view = account(positions=[position()])
        view['externalSymbols'] = [batch['results'][0]['symbol']]
        view['positions'][0]['symbol'] = batch['results'][1]['symbol']
        result = bridge.calculate_capital(batch, view, self.arrival)
        excluded = set(view['externalSymbols']) | {view['positions'][0]['symbol']}
        self.assertTrue(all(i['symbol'] not in excluded for i in result['intents']))
        self.assertEqual(sum(r['reason'] == 'ALREADY_OWNED_OR_PERSONAL' for r in result['rejected']), 2)
        view['externalSymbols'].append(view['positions'][0]['symbol'])
        with self.assertRaisesRegex(ValueError, 'PERSONAL_AND_ARK_OVERLAP'):
            bridge.calculate_capital(batch, view, self.arrival)

    def test_partial_odd_quantity_keeps_its_max3_slot_without_becoming_a_buy_lot(self):
        view = account(positions=[position(0, quantity=37), position(1), position(2)])
        result = bridge.calculate_capital(self.batch(4, scores=[2.0]), view, self.arrival)
        self.assertEqual(result['intents'], [])
        self.assertTrue(all(r['reason'] == 'MAX_POSITION_CAP' for r in result['rejected']))
        for q in (True, 0, -1, 1.5, '100'):
            view['positions'][0]['quantity'] = q
            with self.assertRaisesRegex(ValueError, 'POSITION_QUANTITY'):
                bridge.calculate_capital(self.batch(), view, self.arrival)

    def test_whole_r0_source_and_rank_are_validated_even_when_entry_blocked(self):
        cases = [('ML', 9), ('rank', 'S'), ('capital_score', 9), ('originalModelsExecuted', 4),
                 ('selectedBlock', 7), ('sourceKind', 'HISTORICAL_FILL'), ('fill_price', 1),
                 ('newFits', 1), ('orderAuthorized', True)]
        for key, value in cases:
            batch = self.batch(47)
            batch['results'][-1][key] = value
            view = account()
            view['entryBlocked'] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                bridge.calculate_capital(batch, view, self.arrival)

    def test_r0_future_receipt_stale_reference_and_duplicate_symbol_are_rejected(self):
        for key, value in [('referenceKnownAtJst', at(571, 13)),
                           ('asofReferenceBarEndJst', at(572)),
                           ('asofReferenceBarEndJst', at(571, 1)),
                           ('asofReferenceBarEndJst', at(569))]:
            batch = self.batch()
            batch['results'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, 'R0_REFERENCE_NOT_RECEIVED_OR_STALE'):
                bridge.calculate_capital(batch, account(), self.arrival)
        batch = self.batch(2)
        batch['results'][1]['symbol'] = batch['results'][0]['symbol']
        with self.assertRaisesRegex(ValueError, 'R0_SYMBOL_DUPLICATE'):
            bridge.calculate_capital(batch, account(), self.arrival)

    def test_bad_balance_account_gate_and_exposure_are_blocked(self):
        for patch in ({'availableCashJpy': 'NaN'}, {'availableCashJpy': 'bad'},
                      {'availableCashJpy': True}, {'equityJpy': '1000001'},
                      {'entryBlocked': 0}, {'pendingOrders': 'false'}, {'account': '信用'}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                bridge.calculate_capital(self.batch(), dict(account(), **patch), self.arrival)
        view = account()
        view.update(exposureJpy='1', equityJpy='1000001')
        with self.assertRaisesRegex(ValueError, 'POSITION_MARKS'):
            bridge.calculate_capital(self.batch(), view, self.arrival)


class ExitDecisionBridgeTests(unittest.TestCase):
    def calculate(self, positions, *, now=at(574, 12), traces=None, history=None):
        return bridge.calculate_exits(positions, traces or {}, session=DAY, at=now,
                                      order_history=history or {})

    def test_structural_exit_calls_unchanged_original_and_keeps_observed_quantity(self):
        owned = position(quantity=200)
        trace = trace_fixtures.prefix() + [trace_fixtures.trace_row(34, close='.5', primary='PULLBACK')]
        original = bridge.exits.decide_received_exit(session=DAY, entry_at=owned['filledAtJst'],
                                                     trace=trace, evaluated_at=at(574, 12))
        before = deepcopy(owned)
        actual = self.calculate([owned], traces={owned['symbol']: trace})
        source = actual['intents'][0]
        self.assertEqual(source['schemaId'], ledger.INTENT_SCHEMA)
        self.assertEqual(source['sessionDate'], DAY)
        self.assertEqual(source['quantity'], 200)
        self.assertEqual(source['exitReason'], 'LOCAL_UP_STRUCTURE_GUARD_BROKEN')
        self.assertEqual(source['sourceDecisionSha256'], h.digest(original))
        self.assertEqual(owned, before)
        self.assertFalse(actual['orderTransmission'])

    def test_unknown_fill_time_eod_executes_the_pinned_original_function(self):
        owned = position(quantity=300, fill_time=None, verified=False)
        execution, pins = bridge.original_execution()
        self.assertEqual(pins['execution.py'], '311fa97b4dccf5ce74af5a81e17d39c986c97573')
        with mock.patch.object(execution, 'eod_intent', wraps=execution.eod_intent) as eod, \
             mock.patch.object(bridge, 'original_execution', return_value=(execution, pins)):
            result = self.calculate([owned], now=at(920))
        eod.assert_called_once_with({'quantity': 300, 'side': 'LONG', 'margin': False})
        intent = result['intents'][0]
        self.assertEqual(intent['exitReason'], 'EOD_1520')
        self.assertEqual(intent['schemaId'], ledger.INTENT_SCHEMA)
        self.assertEqual(intent['sessionDate'], DAY)
        self.assertEqual(intent['quantity'], 300)
        self.assertIsNone(owned['filledAtJst'])
        self.assertFalse(owned['fillTimeVerified'])

    def test_unknown_or_unverified_fill_time_does_not_fabricate_structural_entry(self):
        for supplied in (None, at(573)):
            owned = position(fill_time=supplied, verified=False)
            trace = trace_fixtures.prefix() + [trace_fixtures.trace_row(34, close='.5', primary='PULLBACK')]
            with mock.patch.object(bridge.exits, 'decide_received_exit') as structural:
                result = self.calculate([owned], traces={owned['symbol']: trace})
            structural.assert_not_called()
            self.assertEqual(result['intents'], [])
            self.assertEqual(result['unknownFillTimeSymbols'], [owned['symbol']])
            self.assertEqual(self.calculate([owned], now=at(919, 59))['intents'], [])
            self.assertEqual(len(self.calculate([owned], now=at(920, 1))['intents']), 1)

    def test_pending_or_unknown_sell_never_creates_a_second_sell_generation(self):
        owned = position(fill_time=None, verified=False)
        for phase in ('PREPARED', 'IN_FLIGHT', 'PARTIAL', 'CANCEL_REQUESTED', 'UNKNOWN', 'NEW_UNKNOWN_PHASE'):
            history = {'sell': {'entryId': owned['entryId'], 'side': 'SELL', 'phase': phase}}
            self.assertEqual(self.calculate([owned], now=at(920), history=history)['intents'], [])
        first = self.calculate([owned], now=at(920))['intents'][0]
        history = {'sell': {'entryId': owned['entryId'], 'side': 'SELL', 'phase': 'CANCELLED'}}
        second = self.calculate([owned], now=at(920, 5), history=history)['intents'][0]
        self.assertNotEqual(first['intentId'], second['intentId'])
        self.assertEqual(first['quantity'], second['quantity'])

    def test_odd_remaining_shares_are_reported_without_rounding_selling_or_erasing(self):
        owned = [position(0, quantity=37), position(1, quantity=199)]
        before = deepcopy(owned)
        result = self.calculate(owned, now=at(920))
        self.assertEqual(result['intents'], [])
        self.assertEqual([p['quantity'] for p in result['unresolvedExitPositions']], [37, 199])
        self.assertEqual(owned, before)
        self.assertTrue(all(p['reason'] == 'OWNED_QUANTITY_NOT_100_SHARE_LOT'
                            for p in result['unresolvedExitPositions']))

    def test_invalid_quantities_future_fills_and_duplicate_positions_are_rejected(self):
        for q in (True, -1, 1.5, '100', 1_000_000_001):
            with self.subTest(quantity=q), self.assertRaisesRegex(ValueError, 'POSITION_QUANTITY'):
                self.calculate([position(quantity=q)], now=at(920))
        self.assertEqual(self.calculate([position(quantity=0)], now=at(920))['intents'], [])
        with self.assertRaisesRegex(ValueError, 'FUTURE_POSITION_FILL'):
            self.calculate([position(fill_time=at(575))])
        with self.assertRaisesRegex(ValueError, 'EXIT_POSITION_IDENTITY'):
            self.calculate([position(), position()], now=at(920))

    def test_changed_execution_bytes_cannot_be_loaded_for_eod(self):
        original = bridge.source_loader.load_original_bridge()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'execution.py').write_bytes((original.SOURCE / 'execution.py').read_bytes() + b'\n# changed\n')
            fake = SimpleNamespace(SOURCE=root, CAPITAL_BLOBS=original.CAPITAL_BLOBS)
            with mock.patch.object(bridge.source_loader, 'load_original_bridge', return_value=fake), \
                 self.assertRaisesRegex(ValueError, 'PINNED_SOURCE_CHANGED'):
                self.calculate([position(fill_time=None, verified=False)], now=at(920))


if __name__ == '__main__':
    unittest.main()
