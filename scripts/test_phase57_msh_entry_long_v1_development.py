"""Synthetic-only evaluation regression; importing the runner performs no fit."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest

import numpy as np

spec = importlib.util.spec_from_file_location('entry_development', Path(__file__).with_name('run_phase57_msh_entry_long_v1_development.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def row(day='2024-01-01', symbol='A', minute=570, klass=4, score=2.0, price=100):
    stamp = datetime.fromisoformat(day).replace(tzinfo=timezone(timedelta(hours=9))) + timedelta(minutes=minute)
    end = stamp + timedelta(minutes=30)
    identifier = f'{day}|{stamp.isoformat()}|{symbol}'
    return {'selectorEventId': identifier, 'symbolSessionId': f'{day}|{symbol}',
            'sessionDate': day, 'symbol': symbol, 'decisionTimestamp': stamp.isoformat(),
            'ridgeRank': 1, 'ridgeScore': 10 + klass, 'decisionPrice': price,
            'expectedLevel': score, 'fold': 1,
            'label': {'labelable': True, 'ordinalClass': klass, 'closeOrdinalClass': max(0, klass-1),
                      'highReturnPct': [0.5, 1.5, 2.5, 4, 6][klass], 'windowEndTimestamp': end.isoformat()},
            'transfer': {'selectorMfePct': 8, 'selectorMaePct': -2,
                         **{f'selectorOpportunity{t}': 1 for t in mod.LEVELS}}}


class DevelopmentEvaluationTests(unittest.TestCase):
    def test_replay_only_first_enter_after_skip(self):
        a = row(score=0.9)
        b = row(minute=600, score=2.1)
        c = row(minute=630, score=3.5)
        entries, actions = mod.replay([c, a, b], 2)
        self.assertEqual([r['selectorEventId'] for r in entries], [b['selectorEventId']])
        self.assertEqual([r['action'] for r in actions], ['SKIP_THIS_DECISION', 'ENTER', 'SKIP_THIS_DECISION'])
        self.assertEqual(actions[-1]['reason'], 'ALREADY_ENTERED')

    def test_threshold_equality_and_candidates_independent(self):
        a = row(score=2)
        self.assertEqual(len(mod.replay([a], 2)[0]), 1)
        self.assertEqual(len(mod.replay([a], 3)[0]), 0)
        self.assertEqual(len(mod.replay([a], 1)[0]), 1)

    def test_horizons_not_mixed(self):
        a = row(klass=1)
        result = mod.evaluate([a], [a], 1, {a['symbolSessionId']: a})
        self.assertEqual(result['high30']['3']['hitN'], 0)
        self.assertEqual(result['close30']['1']['hitN'], 0)
        self.assertEqual(result['session']['3']['hitN'], 1)
        self.assertEqual(result['strict30mMfePct']['mean'], 1.5)
        self.assertEqual(result['strict30mTrueMaePct']['n'], 0)
        self.assertEqual(result['sessionTrueMaePct']['mean'], -2)

    def test_later_entry_not_original_window_retention(self):
        a, b = row(score=0), row(minute=600, score=2, klass=0, price=104)
        result = mod.evaluate([a, b], [b], 1, {a['symbolSessionId']: a})
        self.assertEqual(result['high30']['5']['admissionPreservationPct'], 100)
        self.assertEqual(result['high30']['5']['timelyAdmissionPreservationPct'], 0)
        self.assertEqual(result['high30']['5']['remainingPreservationPct'], 0)
        self.assertEqual(result['firstEligibleLatencyMinutes']['mean'], 30)
        self.assertAlmostEqual(result['firstEligibleConsumedReturnBps']['mean'], 400)

    def test_original_vs_eligible_latency_separated(self):
        a, b = row(), row(minute=630, price=95)
        result = mod.evaluate([b], [b], 1, {a['symbolSessionId']: a})
        self.assertEqual(result['firstEligibleLatencyMinutes']['mean'], 0)
        self.assertEqual(result['firstOriginalLatencyMinutes']['mean'], 60)

    def test_no_entries_null_precision_and_zero_coverage(self):
        a = row()
        result = mod.evaluate([a], [], 1, {a['symbolSessionId']: a})
        self.assertIsNone(result['high30']['3']['precisionPct'])
        self.assertEqual(result['high30']['3']['admissionPreservationPct'], 0)
        self.assertEqual(result['frozenBalanceMetric'], 0)

    def test_current_unmatched_not_negative_or_new_pass(self):
        a, b = row(), row(minute=600)
        current = {a['symbolSessionId']: {'symbolSessionId': a['symbolSessionId'],
            'firstPassTimestamp': a['decisionTimestamp'], 'firstPassPrice': 100,
            'entryOutcome': {f'opportunity{t}': 1 for t in mod.LEVELS}}}
        result = mod.current_baseline([a, b], current, {a['symbolSessionId']: a}, 1)
        self.assertEqual(result['strict30mExactEventMatchedPassCount'], 1)
        current[a['symbolSessionId']]['firstPassTimestamp'] = a['decisionTimestamp'].replace('09:30', '09:35')
        result = mod.current_baseline([a, b], current, {a['symbolSessionId']: a}, 1)
        self.assertEqual(result['actualFirstPassCount'], 1)
        self.assertEqual(result['strict30mUnmatchedPassCount'], 1)
        self.assertIsNone(result['strict30mExactEventSubsetOnly']['high30']['1']['precisionPct'])

    def test_event_and_symbol_session_denominators(self):
        a, b, c = row(), row(minute=600), row(symbol='B')
        entries, _ = mod.replay([a, b, c], 1)
        self.assertEqual(len(entries), 2)
        self.assertEqual(mod.event_metrics([a, b, c], [a, b, c])['qualifiedEventN'], 3)

    def test_duplicate_entry_rejected(self):
        a = row()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            mod.evaluate([a], [a, a], 1, {a['symbolSessionId']: a})

    def fixture(self):
        dates = [(datetime(2024, 1, 1) + timedelta(days=d)).date().isoformat() for d in range(76)]
        rows = [row(day=day, symbol=str(k), klass=k) for day in dates for k in range(5)]
        for r in rows:
            r['ridgeRank'] = 5 - int(r['symbol'])
        return dates, rows

    def test_prefix_scaler_not_eval_and_no_symbol_session_leakage(self):
        dates, rows = self.fixture()
        for r in rows:
            if r['sessionDate'] in dates[16:]:
                r['ridgeScore'] += 1000
        folds = mod.prepare_folds(rows, dates)
        first = folds[0][2]
        self.assertEqual(first['trainRows'], 80)
        self.assertEqual(first['evalRows'], 75)
        self.assertEqual(first['scaler']['mean'][0], 12)
        self.assertTrue(all(first['preFitChecks'].values()))

    def test_missing_training_class_fails_all_preflight(self):
        dates, rows = self.fixture()
        rows = [r for r in rows if not (r['sessionDate'] in dates[:16] and r['label']['ordinalClass'] == 3)]
        with self.assertRaisesRegex(ValueError, 'allFiveTrainingClasses'):
            mod.prepare_folds(rows, dates)

    def test_unlabelable_never_negative(self):
        dates, rows = self.fixture()
        rows[0]['label']['labelable'] = False
        rows[0]['label']['ordinalClass'] = None
        folds = mod.prepare_folds(rows, dates)
        self.assertEqual(folds[0][2]['trainRows'], 79)
        self.assertEqual(folds[0][2]['trainClassCounts'][0], 15)


if __name__ == '__main__':
    unittest.main()
