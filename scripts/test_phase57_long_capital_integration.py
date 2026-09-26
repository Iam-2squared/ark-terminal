import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from scripts.phase57_long_capital_integration import (
    CONTRACT, EXIT_BASE, PATHS, PREDICTIONS, calendar, causal_envelopes, digest,
    iso, minute_stamp, module, replay, run, stamp, weights,
)


DATE = '2024-09-17'


def event(symbol='10000', minute=570, price=100, closes=None, date=DATE):
    if closes is None:
        closes = [0]*12
    t = minute_stamp(date, minute)
    slots = [m for m in calendar(date) if m > minute]
    bars = [{'slot': i+1, 'end': iso(minute_stamp(date, m)), 'minutes': m-minute,
             'missing': c is None, **({'c': c} if c is not None else {})}
            for i, (m, c) in enumerate(zip(slots, closes))]
    return {'selectorEventId': f'{date}|{minute}|{symbol}', 'symbolSessionId': f'{date}|{symbol}',
            'sessionDate': date, 'symbol': symbol, 'decisionTimestamp': iso(t),
            'decisionPrice': price, 'direction': 'LONG', 'expectedBars': len(slots), 'future': bars}


def evaluate(events, arm='EQUAL_MAX3', mode='LONG', **changes):
    c = json.loads(CONTRACT.read_text()) | changes
    env = [{'eventId': e['selectorEventId'], 'timestamp': e['decisionTimestamp'],
            'symbol': e['symbol'], 'score': 2+i/100} for i, e in enumerate(events)]
    ws = weights(env)
    return replay(events, sorted(set(e['sessionDate'] for e in events)), arm, ws.get(arm, {}), c, mode)


class LedgerTests(unittest.TestCase):
    def test_cost_once_cash_and_lots(self):
        r = evaluate([event(closes=[1, 2, 1, 0])])
        t = r['closedTrades'][0]
        self.assertEqual(t['quantity'], 3300)
        self.assertAlmostEqual(t['pnlJpy'], -165)
        self.assertAlmostEqual(r['finalEquityJpy'], 999835)
        self.assertAlmostEqual(r['realizedLedgerPnlJpy'], -165)
        self.assertAlmostEqual(r['capital']['feesJpy'], 165)
        self.assertLess(r['ledgerAudit']['maxCashBalanceErrorJpy'], 1e-6)

    def test_missing_is_locked_unknown_not_zero_or_future_substitute(self):
        a = event(closes=[1, None, 999, 0, -1])
        b = event('20000', minute=600)
        r = evaluate([a, b])
        self.assertIsNone(r['finalEquityJpy'])
        self.assertIsNone(r['maxDrawdownPct'])
        self.assertEqual(r['trade']['closed'], 0)
        self.assertEqual(r['trade']['unresolved'], 1)
        self.assertEqual(r['trade']['rejectionReasons']['CURRENT_EQUITY_UNKNOWN'], 1)
        self.assertEqual(r['lockedPurchaseNotionalJpy'], 330000)
        self.assertAlmostEqual(r['cashBalanceJpy'], 669917.5)

    def test_missing_after_exit_does_not_rewrite_exit(self):
        a = event(closes=[3, 2, 1, None, -99])
        r = evaluate([a])
        self.assertEqual(r['trade']['closed'], 1)
        self.assertEqual(r['trade']['unresolved'], 0)
        self.assertIsNotNone(r['finalEquityJpy'])

    def test_bar5_reclaim_and_failure_unchanged(self):
        r = evaluate([event(closes=[-1, -2, -3, -4, -5, 100])])
        self.assertEqual(r['closedTrades'][0]['exitReason'], 'BAR5_NO_RECLAIM')
        self.assertAlmostEqual(r['closedTrades'][0]['netPct'], -5.05)
        r = evaluate([event(closes=[-1, -2, -3, -4, 0, 2, 1, 0])])
        self.assertEqual(r['closedTrades'][0]['holdingBars'], 8)

    def test_no_remaining_bar_is_causal_rejection(self):
        r = evaluate([event(minute=900)])
        self.assertEqual(r['trade']['accepted'], 0)
        self.assertEqual(r['trade']['rejectionReasons'], {'NO_REMAINING_REGULAR_BAR': 1})
        self.assertEqual(r['finalEquityJpy'], 1000000)

    def test_exit_before_same_time_entry_recycles_cash(self):
        a = event('10000', closes=[1, 0, -1])
        b = event('20000', minute=585, closes=[1, 0, -1])
        r = evaluate([a, b], maximumConcurrentPositions=1)
        self.assertEqual(r['trade']['accepted'], 2)
        self.assertEqual(r['capital']['sameTimestampRecyclingEntries'], 1)
        self.assertTrue(r['decisions'][1]['sameTimestampCashRecycling'])

    def test_lot_and_cash_reasons_distinct(self):
        r = evaluate([event(price=4000)])
        self.assertEqual(r['trade']['rejectionReasons'], {'TARGET_BELOW_LOT': 1})
        r = evaluate([event(price=11000)], arm='ONE_LOT_REFERENCE')
        self.assertEqual(r['trade']['rejectionReasons'], {'INSUFFICIENT_CASH': 1})

    def test_concurrency_and_symbol_order(self):
        es = [event('20000'), event('10000')]
        r = evaluate(es, maximumConcurrentPositions=1)
        self.assertEqual(r['decisions'][0]['symbol'], '10000')
        self.assertEqual(r['trade']['accepted'], 1)
        self.assertEqual(r['trade']['rejectionReasons']['MAX_CONCURRENT_POSITIONS'], 1)

    def test_short_and_duplicate_identity_rejected(self):
        a = event()
        a['direction'] = 'SHORT'
        with self.assertRaises(ValueError):
            evaluate([a])
        a = event()
        with self.assertRaises(ValueError):
            evaluate([a, a])

    def test_future_changes_do_not_change_entry_sizing(self):
        a = event(closes=[1]*12)
        b = copy.deepcopy(a)
        b['future'][1]['c'] = -90
        x, y = evaluate([a]), evaluate([b])
        self.assertEqual(x['decisions'], y['decisions'])

    def test_rank_and_equal_reuse_with_no_outcome_fields(self):
        env = [{'eventId': 'a', 'timestamp': DATE+'T09:30:00+09:00', 'symbol': '1', 'score': 2},
               {'eventId': 'b', 'timestamp': DATE+'T09:30:00+09:00', 'symbol': '2', 'score': 3}]
        w = weights(env)
        self.assertEqual(w['EQUAL_MAX3'], {'b': .5, 'a': .5})
        self.assertEqual(w['LONG_RANK_MAX3'], {'b': 2/3, 'a': 1/3})
        env[0]['futureReturn'] = 99
        with self.assertRaises(Exception):
            weights(env)

    def test_unresolved_position_never_releases_next_day(self):
        a = event(closes=[None])
        b = event('20000', date='2024-09-18')
        r = evaluate([a, b])
        self.assertEqual(r['trade']['accepted'], 1)
        self.assertEqual(r['trade']['unresolved'], 1)
        self.assertIsNone(r['sessions'][-1]['equityJpy'])

    def test_mtm_drawdown_uses_open_position_marks(self):
        r = evaluate([event(closes=[-20, 0]+[0]*10)])
        self.assertGreater(r['maxDrawdownJpy'], 65000)
        self.assertAlmostEqual(r['finalEquityJpy'], 999835)

    def test_full_session_time_includes_idle_not_overnight_or_lunch(self):
        r = evaluate([event()])
        self.assertEqual(r['capital']['tradingMinutes'], 300)
        self.assertLess(r['capital']['averageUtilization'], .1)

    def test_event_input_order_invariance_and_timezone_normalization(self):
        es = [event('10000'), event('20000')]
        a = evaluate(es)
        b = evaluate(list(reversed(es)))
        self.assertEqual(a, b)
        es[0]['future'][0]['end'] = '2024-09-17T00:35:00Z'
        self.assertEqual(evaluate(es), a)

    def test_unrealized_gain_never_becomes_spendable_cash(self):
        es = [event(str(10000+i)) for i in range(4)]
        r = evaluate(es)
        self.assertGreaterEqual(min(row['cashJpy'] for row in r['equityCurve']), 0)
        for row in r['decisions']:
            if row['status'] == 'ACCEPTED':
                self.assertLessEqual(row['notionalJpy']+row['feeJpy'], row['cashBeforeJpy']+1e-7)


class EvidenceTests(unittest.TestCase):
    def test_publication_manifest_hashes(self):
        base = Path('docs/evidence/phase57-long-capital-integration-v1')
        if not (base/'manifest.json').exists():
            self.skipTest('before publication')
        manifest = json.loads((base/'manifest.json').read_text())
        import hashlib
        self.assertEqual(hashlib.sha256(gzip.decompress((base/'measurement.json.gz').read_bytes())).hexdigest(), manifest['rawMeasurementSHA256'])
        for path, sha in manifest['artifacts'].items():
            self.assertEqual(digest(base/path), sha, path)
        for path, sha in {**manifest['codePins'], **manifest['upstreamPins']}.items():
            self.assertEqual(digest(path), sha, path)
        self.assertFalse(manifest['allocationFinalSelected'])
        self.assertFalse(manifest['primary277FinalEquityKnown'])

    def test_frozen277_selected_reference_reproduction(self):
        events = json.loads(gzip.decompress(PATHS.read_bytes()))['events']
        old = json.loads((EXIT_BASE/'measurement.json').read_text())
        ids = set(old['pairedIdentities'])
        paired = [e for e in events if e['selectorEventId'] in ids]
        c = json.loads(CONTRACT.read_text())
        result = replay(paired, json.loads(Path('docs/evidence/phase57-long-exit-v345-paired/contract.json').read_text())['sessionList'],
                        'ONE_LOT_REFERENCE', {}, c)
        runtime = module('predict/long-only/phase57_long_exit_continuation_v1.py', 'reference_test')
        by_id = {e['selectorEventId']: e for e in paired}
        self.assertEqual(result['trade']['closed'], 173)
        for trade in result['closedTrades']:
            expected = runtime.replay(by_id[trade['eventId']], 'BAR5_TWO_LOWER_CLOSES')
            self.assertEqual(stamp(trade['exitTimestamp']), stamp(expected['exitTimestamp']))
            self.assertAlmostEqual(trade['netPct'], expected['netPct'], places=10)
        self.assertAlmostEqual(sum(t['netPct'] for t in result['closedTrades']),
                               old['metrics']['BAR5_TWO_LOWER_CLOSES']['netSumPctPoints'], places=8)

    def test_allocation_source_hashes_unchanged(self):
        # These two source files were imported verbatim from the latest Allocation lineage.
        import subprocess
        result = subprocess.run(['git', 'hash-object', 'scripts/lib/phase57-capital-allocation-v3-entrytime.mjs'], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), '39b02cc630d92f0b8530fde2a88be42e9740a5f0')

    def test_reproducible_run_and_277_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(Path(tmp)/'evidence')
            for r in result['reports']['FULL277'].values():
                self.assertEqual(len(r['decisions']), 277)
                self.assertEqual(r['trade']['accepted'], r['trade']['closed']+r['trade']['unresolved'])
                self.assertIsNone(r['finalEquityJpy'])
            self.assertFalse(result['allocationDevelopmentFinalSelected'])
            self.assertTrue(all(v is False for v in result['safety'].values()))
            saved = Path('docs/evidence/phase57-long-capital-integration-v1/measurement.json.gz')
            if saved.exists():
                self.assertEqual(gzip.decompress(saved.read_bytes()), (Path(tmp)/'evidence/measurement.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
