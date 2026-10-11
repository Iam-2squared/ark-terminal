"""Offline-only tests: no Excel, RSS, broker, or real order functions."""
import copy
import importlib.util
import pathlib
import unittest
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('v5_shadow', ROOT / 'tools' / 'no11_capital_v5_shadow.py')
shadow_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(shadow_module)


def sample():
    return {
        'schemaId': 'ARK_NO11_FROZEN_V5_SYNTHETIC_BRIDGE_V1',
        'evidenceMode': 'SYNTHETIC_OFFLINE_ONLY',
        'strategyFreezeCommit': shadow_module.FROZEN_NO11,
        'capitalAuthorityCommit': shadow_module.CAPITAL_AUTHORITY,
        'afterFirstLegalSellFill': False,
        'pendingBrokerOrders': False,
        'sessionVerified': False,
        'arkCapitalInputs': {'cash': 700000, 'equity': 700000, 'exposure': 0},
        'externalSymbols': ['408A.T'],
        'arkManagedSymbols': [],
        'existingBands': [],
        'minute': 600,
        'preorderedCandidates': [
            {'entry_id': 'synthetic-S', 'brokerSymbol': '6758.T', 'rank': 'S',
             'ML': 2.5, 'capital_score': 2.2, 'raw_reference': '1000', 'block': '1'}
        ],
        'syntheticTrainingTables': {'1': {
            'minute_counts': {'600': [1, 0, 2], '840': [1, 0, 2], '870': [1, 0, 2]},
            'training_session_N': 10, 'B_median': 1.3, 'B_p75': 1.4,
            'minute_bucket': {'600': 'unit', '840': 'unit', '870': 'unit'}
        }}
    }


class CapitalV5OfflineBridgeTests(unittest.TestCase):
    def test_authority_sources_are_byte_exact_and_cost_is_frozen(self):
        for filename, expected in shadow_module.CAPITAL_BLOBS.items():
            with self.subTest(filename=filename):
                data = (shadow_module.SOURCE / filename).read_bytes()
                self.assertEqual(shadow_module.git_blob_sha(data), expected)
        original, _ = shadow_module.load_frozen()
        self.assertEqual(str(original.BUY), '1.0005')

    def test_cash_uses_full_broker_buying_power_and_zero_personal_equity(self):
        r = shadow_module.shadow(sample())
        self.assertEqual(r['status'], 'SYNTHETIC_SHADOW_ONLY')
        self.assertEqual(r['inputCashJpy'], '700000')
        self.assertEqual(r['inputEquityJpy'], '700000')
        self.assertEqual(r['arkExposureJpy'], '0')
        self.assertEqual(r['allocatedDebitJpy'], '300150.0000')
        self.assertEqual(r['remainingBuyingPowerJpy'], '399850.0000')
        self.assertEqual(r['allocations'][0]['quantity'], 300)
        self.assertEqual(r['allocations'][0]['band'], 'S')
        self.assertEqual(Decimal(r['allocations'][0]['batchBudgetJpy']), Decimal('476000.00'))
        self.assertFalse(r['personalStockDoubleDeducted'])
        self.assertFalse(r['orderAllowed'])
        self.assertFalse(r['productionReady'])
        self.assertFalse(r['transmitted'])

    def test_personal_symbol_buy_blocked_even_if_cash_available(self):
        p = sample()
        p['preorderedCandidates'][0]['brokerSymbol'] = '408A.T'
        with self.assertRaisesRegex(shadow_module.Blocked, 'PERSONAL_SYMBOL_BUY_PROHIBITED'):
            shadow_module.shadow(p)

    def test_existing_ark_valuation_is_only_exposure(self):
        p = sample()
        p['arkCapitalInputs'] = {'cash': 700000, 'equity': 850000, 'exposure': 150000}
        p['arkManagedSymbols'] = ['7203.T']
        p['existingBands'] = ['A']
        r = shadow_module.shadow(p)
        self.assertEqual(r['arkExposureJpy'], '150000')
        self.assertEqual(r['inputEquityJpy'], '850000')
        self.assertEqual(len(p['arkManagedSymbols']), 1)
        self.assertTrue(all(a['quantity'] % 100 == 0 for a in r['allocations']))
        self.assertLessEqual(Decimal(r['allocatedDebitJpy']), Decimal('700000'))

    def test_frozen_slot2_B_reserve_retained(self):
        p = sample()
        p['preorderedCandidates'].append({'entry_id': 'synthetic-B',
            'brokerSymbol': '9999.T', 'rank': 'B', 'ML': 1.2,
            'capital_score': 1.2, 'raw_reference': '500', 'block': '1'})
        r = shadow_module.shadow(p)
        self.assertEqual(r['admittedCount'], 1)
        self.assertEqual(r['rejected'][0]['reason'], 'SLOT2_RESERVE_FOR_FUTURE_QUALITY')
        self.assertEqual(r['rejected'][0]['entry_id'], 'synthetic-B')

    def test_max3_uses_managed_positions_not_personal_stock(self):
        p = sample()
        p['arkManagedSymbols'] = ['7203.T', '9432.T']
        p['existingBands'] = ['S', 'A']
        p['arkCapitalInputs'] = {'cash': 700000, 'equity': 900000, 'exposure': 200000}
        p['preorderedCandidates'].append({'entry_id': 'synthetic-A',
            'brokerSymbol': '9999.T', 'rank': 'A', 'ML': 1.7,
            'capital_score': 1.6, 'raw_reference': '500', 'block': '1'})
        r = shadow_module.shadow(p)
        self.assertEqual(r['admittedCount'], 1)
        self.assertEqual(r['rejected'][0]['reason'], 'MAX_POSITION_CAP')
        self.assertLessEqual(r['fundedCount']+len(p['arkManagedSymbols']), 3)

    def test_frozen_buy_cost_blocks_unauthorized_cash_borrowing(self):
        p = sample()
        p['arkCapitalInputs'] = {'cash': 99999, 'equity': 99999, 'exposure': 0}
        p['preorderedCandidates'][0]['raw_reference'] = '1000'
        r = shadow_module.shadow(p)
        self.assertEqual(r['fundedCount'], 0)
        self.assertEqual(r['allocatedDebitJpy'], '0.0000')

    def test_after_first_legal_sell_fill_halts_same_day_buy(self):
        p = sample(); p['afterFirstLegalSellFill'] = True
        with self.assertRaisesRegex(shadow_module.Blocked, 'AFTER_FIRST_SELL_FILL_NO_NEW_BUY'):
            shadow_module.shadow(p)

    def test_pending_broker_order_blocks_funding(self):
        p = sample(); p['pendingBrokerOrders'] = True
        with self.assertRaisesRegex(shadow_module.Blocked, 'PENDING_ORDERS_BLOCK_FUNDING'):
            shadow_module.shadow(p)

    def test_reject_live_or_fake_timestamp_certification(self):
        p = sample(); p['evidenceMode'] = 'LIVE_ATTESTED'
        with self.assertRaisesRegex(shadow_module.Blocked, 'LIVE_DECISION_SOURCE_NOT_CERTIFIED'):
            shadow_module.shadow(p)
        p = sample(); p['sessionVerified'] = True
        with self.assertRaisesRegex(shadow_module.Blocked, 'SESSION_CERTIFICATION_NOT_ALLOWED_IN_SYNTHETIC'):
            shadow_module.shadow(p)

    def test_input_equity_must_equal_cash_plus_ark_exposure(self):
        p = sample(); p['arkCapitalInputs']['equity'] = 1000000
        with self.assertRaisesRegex(shadow_module.Blocked, 'ARK_EQUITY_CASH_EXPOSURE_MISMATCH'):
            shadow_module.shadow(p)

    def test_nan_negative_and_bool_price_or_score_block(self):
        for invalid in ('NaN', '-1', '', 'Infinity', True, None):
            with self.subTest(invalid=invalid):
                p = sample(); p['preorderedCandidates'][0]['raw_reference'] = invalid
                with self.assertRaises(shadow_module.Blocked):
                    shadow_module.shadow(p)
        p = sample(); p['preorderedCandidates'][0]['capital_score'] = float('nan')
        with self.assertRaises(shadow_module.Blocked):
            shadow_module.shadow(p)

    def test_same_personal_ark_symbol_fails_even_without_candidate(self):
        p = sample(); p['arkManagedSymbols'] = ['408A.T']; p['existingBands'] = ['A']
        p['arkCapitalInputs'] = {'cash': 700000, 'equity': 850000, 'exposure': 150000}
        with self.assertRaisesRegex(shadow_module.Blocked, 'PERSONAL_AND_ARK_OVERLAP'):
            shadow_module.shadow(p)

    def test_duplicate_candidate_symbol_or_id_is_not_accepted(self):
        p = sample(); x = copy.deepcopy(p['preorderedCandidates'][0]);x['entry_id'] = 'another'
        p['preorderedCandidates'].append(x)
        with self.assertRaisesRegex(shadow_module.Blocked, 'DUPLICATE_CANDIDATE_SYMBOL'):
            shadow_module.shadow(p)

    def test_explicit_existing_band_is_required(self):
        p = sample(); p['arkManagedSymbols']=['7203.T'];p['existingBands']=[]
        p['arkCapitalInputs']={'cash':700000,'equity':850000,'exposure':150000}
        with self.assertRaisesRegex(shadow_module.Blocked, 'FROZEN_EXISTING_BAND_ATTESTATION_MISSING'):
            shadow_module.shadow(p)

    def test_empty_batch_remains_zero_and_no_forced_backfill(self):
        p = sample(); p['preorderedCandidates'] = []
        r = shadow_module.shadow(p)
        self.assertEqual(r['allocatedDebitJpy'], '0')
        self.assertEqual(r['fundedCount'], 0)


if __name__ == '__main__':
    unittest.main()
