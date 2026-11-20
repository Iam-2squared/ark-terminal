"""Chart50 boundary/parity tests; native original math, synthetic cash only."""
from copy import deepcopy
from decimal import Decimal
import random
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import no11_capital_v5_batch_capacity as wide
import no11_capital_v5_crlf_safe_synthetic as native


def request(n=47, *, occupancy=0, cash='1000000', minute=600):
    rows = [{'entry_id': 'candidate-%03d' % i, 'brokerSymbol': '%04d.T' % (1000 + i),
             'ML': 2.0, 'capital_score': 2.0, 'rank': 'S', 'block': '8',
             'raw_reference': str(100 + i)} for i in range(n)]
    exposure = Decimal('100000') * occupancy
    return {'schemaId': 'ARK_NO11_FROZEN_V5_SYNTHETIC_BRIDGE_V1',
            'evidenceMode': 'SYNTHETIC_OFFLINE_ONLY',
            'strategyFreezeCommit': '10c94c92c4bd2a59a22744667fd0210252602df4',
            'capitalAuthorityCommit': '710656491be06235901b45c50a8b5cbd714ba4eb',
            'afterFirstLegalSellFill': False, 'pendingBrokerOrders': False,
            'sessionVerified': False, 'productionReady': False, 'orderTransmission': False,
            'minute': minute, 'externalSymbols': [],
            'arkManagedSymbols': ['%04d.T' % (9000 + i) for i in range(occupancy)],
            'existingBands': ['B'] * occupancy,
            'arkCapitalInputs': {'cash': cash, 'equity': str(Decimal(cash) + exposure),
                                 'exposure': str(exposure)},
            'preorderedCandidates': rows,
            'syntheticTrainingTables': {'8': {
                'minute_counts': {str(minute): [0, 0, 0]},
                'minute_bucket': {str(minute): 'SYNTHETIC'},
                'training_session_N': 10, 'B_median': 1.1, 'B_p75': 1.2}}}


def native_reference(value):
    """Full-list gate oracle calls the pinned original gate, never a copied rule.

    Once the admitted list is known, the original bridge can allocate that
    <=3-row set in a single call. Rejection reasons come from the actual gate.
    """
    native.run_request(dict(value, preorderedCandidates=[]))
    module = native.load_original_bridge()
    saved = module.git_blob_sha
    module.git_blob_sha = lambda raw: saved(raw.replace(b'\r\n', b'\n'))
    _, slots = module.load_frozen()
    chosen, rejected = [], []
    for row in value['preorderedCandidates']:
        count = len(value['arkManagedSymbols']) + len(chosen)
        if count >= 3:
            admitted, reason = False, 'MAX_POSITION_CAP'
        else:
            admitted, reason, _ = slots.gate(row, count, value['minute'],
                                           value['syntheticTrainingTables'][str(row['block'])])
        if admitted:
            chosen.append(row)
        else:
            rejected.append({'entry_id': row['entry_id'], 'reason': reason})
    out = native.run_request(dict(value, preorderedCandidates=chosen))
    out['rejected'] = rejected
    return out


class NativeBatchCapacity(unittest.TestCase):
    def test_existing_zero_to_twenty_path_is_exactly_unchanged(self):
        for n in (0, 1, 3, 19, 20):
            with self.subTest(n=n):
                value = request(n)
                self.assertEqual(wide.run_request(value), native.run_request(value))

    def test_original_bridge_still_rejects_twenty_one_without_being_edited(self):
        with self.assertRaisesRegex(Exception, 'CANDIDATE_BATCH_INVALID'):
            native.run_request(request(21))

    def test_twenty_one_47_and_fifty_match_original_gate_and_allocation(self):
        for n in (21, 47, 50):
            with self.subTest(n=n):
                value = request(n)
                out = wide.run_request(value)
                self.assertEqual(out, native_reference(value))
                self.assertEqual(out['admittedCount'], 3)
                self.assertEqual(len(out['rejected']), n - 3)
                self.assertLessEqual(out['fundedCount'], 3)
                self.assertLessEqual(Decimal(out['allocatedDebitJpy']), Decimal('1000000'))
                self.assertFalse(out['transmitted'])

    def test_fifty_one_is_rejected_without_any_native_pass(self):
        with mock.patch.object(native, 'run_request') as run:
            with self.assertRaisesRegex(ValueError, 'CAPACITY_EXCEEDED'):
                wide.run_request(request(51))
            run.assert_not_called()

    def test_all_passes_use_original_20_bound_and_same_initial_cash(self):
        value = request(50)
        real = native.run_request
        with mock.patch.object(native, 'run_request', wraps=real) as run:
            out = wide.run_request(value)
        self.assertEqual(run.call_count, 3)
        self.assertEqual([len(c.args[0]['preorderedCandidates']) for c in run.call_args_list], [20, 20, 16])
        for call in run.call_args_list:
            self.assertEqual(call.args[0]['arkCapitalInputs'], value['arkCapitalInputs'])
            self.assertFalse(call.args[0]['sessionVerified'])
        self.assertEqual(out, native_reference(value))

    def test_order_and_original_objects_are_not_mutated(self):
        value = request(47)
        value['preorderedCandidates'].reverse()
        before = deepcopy(value)
        out = wide.run_request(value)
        self.assertEqual(value, before)
        self.assertEqual([r['entry_id'] for r in out['allocations']],
                         [r['entry_id'] for r in value['preorderedCandidates'][:3]])

    def test_reserve_gate_rejections_do_not_discard_later_eligible_row(self):
        value = request(47)
        for row in value['preorderedCandidates']:
            row.update(rank='B', ML=1.0, capital_score=1.0)
        value['preorderedCandidates'][-1].update(rank='A', ML=1.5, capital_score=1.5)
        out = wide.run_request(value)
        self.assertEqual(out, native_reference(value))
        self.assertEqual(out['admittedCount'], 2)
        self.assertEqual(out['allocations'][-1]['entry_id'], 'candidate-046')

    def test_zero_lot_admissions_are_not_replaced_by_later_affordable_names(self):
        value = request(47)
        for row in value['preorderedCandidates'][:3]:
            row['raw_reference'] = '10000000'
        out = wide.run_request(value)
        self.assertEqual(out, native_reference(value))
        self.assertEqual(out['admittedCount'], 3)
        self.assertEqual(out['fundedCount'], 0)
        self.assertTrue(all(r['quantity'] == 0 for r in out['allocations']))

    def test_existing_managed_positions_consume_the_same_max3_slots(self):
        for count in (1, 2, 3):
            with self.subTest(occupancy=count):
                value = request(47, occupancy=count)
                out = wide.run_request(value)
                self.assertEqual(out, native_reference(value))
                self.assertEqual(out['admittedCount'], 3 - count)
                self.assertLessEqual(out['fundedCount'] + count, 3)

    def test_zero_cash_never_funds_any_of_47_candidates(self):
        out = wide.run_request(request(47, cash='0'))
        self.assertEqual(out['fundedCount'], 0)
        self.assertEqual(Decimal(out['allocatedDebitJpy']), 0)

    def test_cross_window_duplicate_candidate_id_is_rejected(self):
        value = request(47)
        value['preorderedCandidates'][-1]['entry_id'] = value['preorderedCandidates'][0]['entry_id']
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_OR_INVALID_ENTRY_ID'):
            wide.run_request(value)

    def test_cross_window_normalized_duplicate_symbol_is_rejected(self):
        value = request(47)
        value['preorderedCandidates'][-1]['brokerSymbol'] = ' 1000 '
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_SYMBOL'):
            wide.run_request(value)

    def test_invalid_last_row_is_validated_even_when_first_three_fill_capacity(self):
        for key, bad in [('raw_reference', '-1'), ('ML', float('nan')), ('rank', 'X'), ('block', 'missing')]:
            with self.subTest(key=key):
                value = request(47)
                value['preorderedCandidates'][-1][key] = bad
                with self.assertRaises(Exception):
                    wide.run_request(value)

    def test_personal_or_managed_symbol_in_tail_still_rejects_entire_request(self):
        for key in ('externalSymbols', 'arkManagedSymbols'):
            with self.subTest(key=key):
                value = request(47, occupancy=1 if key == 'arkManagedSymbols' else 0)
                value['preorderedCandidates'][-1]['brokerSymbol'] = '9000.T'
                if key == 'externalSymbols':
                    value[key] = ['9000.T']
                with self.assertRaises(Exception):
                    wide.run_request(value)

    def test_existing_synthetic_source_and_buy_halt_restrictions_unchanged(self):
        for key, bad in [('evidenceMode', 'LIVE'), ('afterFirstLegalSellFill', True),
                         ('pendingBrokerOrders', True), ('sessionVerified', True)]:
            with self.subTest(key=key):
                with self.assertRaises(Exception):
                    wide.run_request(dict(request(47), **{key: bad}))

    def test_native_source_identity_failure_is_not_suppressed(self):
        with mock.patch.object(native, 'load_original_bridge', side_effect=RuntimeError('NO11_V5_ORIGINAL_BRIDGE_BLOB_CHANGED')):
            with self.assertRaisesRegex(RuntimeError, 'ORIGINAL_BRIDGE_BLOB_CHANGED'):
                wide.run_request(request(47))

    def test_seeded_47_way_ranks_prices_cash_and_occupancy_match_native_math(self):
        rng = random.Random(20261026)
        for iteration in range(60):
            minute = rng.choice((570, 600, 840, 870, 919))
            value = request(rng.choice((21, 47, 50)), occupancy=rng.randrange(4),
                            cash=str(rng.choice((0, 10000, 1000000, 3000000))), minute=minute)
            table = value['syntheticTrainingTables']['8']
            table['minute_counts'][str(minute)] = rng.choice(([0, 0, 0], [4, 1, 6], [6, 3, 10]))
            for row in value['preorderedCandidates']:
                score = rng.choice((1.0, 1.1, 1.25, 1.5, 2.0, 2.5))
                row.update(ML=score, capital_score=score,
                           rank='S' if score >= 2 else 'A' if score >= 1.5 else 'B',
                           raw_reference=str(rng.choice(('9.1', '100.03', '1200', '10000000'))))
            with self.subTest(case=iteration):
                self.assertEqual(wide.run_request(value), native_reference(value))


if __name__ == '__main__':
    unittest.main()
