import ast
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import phase57_exit_gen2_report_r43 as report


def row(oid, net=1., headroom=2., resolved=True, capture=50.):
    return {'opportunity': '2025-07-03|' + oid, 'session': '2025-07-03',
        'exitStatus': 'RESOLVED' if resolved else 'UNRESOLVED_TERMINAL_EXIT',
        'exitKind': 'MODEL_EXIT' if resolved else None,
        'missingOrdinaryReferences': 0, 'activeMinutesHeld': 5 if resolved else None,
        'wallMinutesHeld': 5 if resolved else None, 'earlyExitOpportunityCostPp': 1 if resolved else None,
        'netReturnPctBySellCost': {'0.05': net if resolved else None, '0.10': net-.05 if resolved else None, '0.20': net-.15 if resolved else None},
        'metrics': {'bucket': '>=5%', 'entryToExitGrossPct': net+.05 if resolved else None,
            'entryToPostEntryHighPct': headroom, 'entryToSameOrderedHighPct': headroom,
            'postEntryUpsideCapturePct': capture, 'ownedPeakGivebackPp': None}}


class ReportTests(unittest.TestCase):
    def test_audit_failure_prevents_file_reads(self):
        with patch.object(report, 'read_json', side_effect=AssertionError('READ_FORBIDDEN')):
            with self.assertRaisesRegex(ValueError, 'AUDIT_PASS_REQUIRED'):
                report.build_report(Path('/missing'), {}, Path('/missing'), Path('/missing-out'))

    def test_unresolved_paired_rows_are_excluded_even_when_metric_populated(self):
        a = [row('A', capture=5), row('B', capture=20)]
        b = [row('A', resolved=False, capture=10), row('B', capture=30)]
        result = report.strict_pairs(a, b)
        self.assertEqual(result['bothResolvedN'], 1)
        self.assertEqual(result['censoredExcludedN'], 1)
        self.assertEqual(result['metrics']['postEntryUpsideCapturePct']['deltaLeftMinusRight']['mean'], -10)

    def test_metric_missingness_is_independent_per_metric(self):
        a, b = [row('A')], [row('A')]
        a[0]['metrics']['postEntryUpsideCapturePct'] = None
        result = report.strict_pairs(a, b)
        self.assertEqual(result['metrics']['netReturnPct']['eligibleN'], 1)
        self.assertEqual(result['metrics']['postEntryUpsideCapturePct']['eligibleN'], 0)
        self.assertEqual(result['metrics']['postEntryUpsideCapturePct']['metricMissingOnEitherSideN'], 1)

    def test_ratio_of_sums_is_not_mean_of_ratios(self):
        a, b = row('A', net=.95, headroom=1), row('B', net=.95, headroom=9)
        result = report.ratio_of_sums([a, b])
        self.assertEqual(result['ratioOfSumsCapturePct'], 20)
        self.assertFalse(result['usedByFormalGate'])

    def test_ratio_population_requires_identical_ids_positive_headroom_both_sides(self):
        left = [row('A', headroom=2), row('B', headroom=3), row('C', headroom=5)]
        right = [row('A', headroom=4), row('B', headroom=0), row('D', headroom=8)]
        result = report.paired_ratio_of_sums(left, right)
        self.assertEqual(result['left']['matchedIds'], ['2025-07-03|A'])
        self.assertEqual(result['left']['matchedIds'], result['right']['matchedIds'])
        self.assertEqual(result['bothResolvedPositiveHeadroomMatchedIdN'], 1)

    def test_same_ordered_high_uses_its_own_positive_headroom_mask(self):
        a, b = row('A', net=.95, headroom=2), row('B', net=.95, headroom=2)
        a['metrics']['entryToSameOrderedHighPct'] = 4
        b['metrics']['entryToSameOrderedHighPct'] = -1
        result = report.paired_ratio_of_sums([a, b], [copy.deepcopy(a), copy.deepcopy(b)], 'entryToSameOrderedHighPct')
        self.assertEqual(result['left']['eligibleN'], 1)
        self.assertEqual(result['left']['ratioOfSumsCapturePct'], 25)
        self.assertEqual(result['left']['denominatorMetric'], 'entryToSameOrderedHighPct')

    def test_nonpositive_headroom_does_not_become_zero_capture(self):
        result = report.ratio_of_sums([row('A', headroom=0), row('B', headroom=-1)])
        self.assertIsNone(result['ratioOfSumsCapturePct'])
        self.assertEqual(result['eligibleN'], 0)

    def test_bucket_anatomy_preserves_unavailable_cases(self):
        for value in (None, 'UNAVAILABLE', 'NON_POSITIVE_RANGE'):
            a = row('A'); a['metrics']['bucket'] = value
            self.assertEqual(report.bucket(a), 'NOT_EVALUABLE')

    def test_group_counts_noentry_censored_and_missing_reference(self):
        a, b = row('A'), row('B', resolved=False)
        a['missingOrdinaryReferences'] = 2
        result = report.group_report([a, b], {'populationN': 5})
        self.assertEqual((result['noEntryN'], result['resolvedN'], result['censoredN']), (3, 1, 1))
        self.assertEqual((result['missingReferenceCaseN'], result['missingReferenceAttemptN']), (1, 2))
        self.assertEqual(result['metricEligibility']['ownedPeakGivebackPp']['resolvedMetricMissingN'], 1)

    def test_duplicate_pair_ids_fail(self):
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_OPPORTUNITY'):
            report.strict_pairs([row('A'), row('A')], [row('A')])

    def test_supplemental_functions_do_not_mutate_ledgers(self):
        rows = [row('A'), row('B', resolved=False)]; before = copy.deepcopy(rows)
        report.group_report(rows); report.strict_pairs(rows, copy.deepcopy(rows)); report.ratio_of_sums(rows)
        self.assertEqual(rows, before)

    def test_csv_keeps_exact_numeric_columns(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'report.csv'
            report.write_csv(path, [{'candidateId': 'X', 'metric': {'mean': 1.25, 'n': 2}}])
            text = path.read_text(encoding='utf-8-sig')
            self.assertIn('metric.mean', text); self.assertIn('1.25', text)

    def test_no_training_replay_or_order_call(self):
        tree = ast.parse(Path(report.__file__).read_text())
        called = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertFalse(called & {'fit', 'fit_transform', 'replay_candidate', 'fit_predictions', 'intent', 'place_order'})


if __name__ == '__main__': unittest.main()
