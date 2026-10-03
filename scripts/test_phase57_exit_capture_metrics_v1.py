"""Synthetic tests only; no current cohort outcomes are loaded."""
from dataclasses import replace
import unittest
from scripts.phase57_exit_capture_metrics_v1 import OrderedGeometry, PostEntryHigh, evaluate_capture, opportunity_bucket

G = OrderedGeometry(1000.,1050.,575,600,925,'SYNTHETIC_ORDERED_LOW_LATER_HIGH','COMPLETE')


def evaluate(**changes):
    args=dict(entry_price=1000.,entry_minute=570,exit_price=1040.,exit_minute=610,
              cost_pp=0.,geometry=G)
    args.update(changes)
    return evaluate_capture(**args)


class CaptureTests(unittest.TestCase):
    def test_six_buckets_are_half_open(self):
        for x,name in [(0.9,'<1%'),(1.,'1-2%'),(2.,'2-3%'),(3.,'3-4%'),(4.,'4-5%'),(5.,'>=5%'),(9.,'>=5%')]:
            self.assertEqual(opportunity_bucket(x),name)
        self.assertEqual(opportunity_bucket(None),'UNAVAILABLE')
        self.assertEqual(opportunity_bucket(0.),'NON_POSITIVE_RANGE')
        self.assertEqual(opportunity_bucket(-1.),'NON_POSITIVE_RANGE')

    def test_example_5pct_available_4pct_taken_80pct(self):
        r=evaluate()
        self.assertAlmostEqual(r['opportunityRangePct'],5.)
        self.assertEqual(r['bucket'],'>=5%')
        self.assertAlmostEqual(r['entryToSameOrderedHighPct'],5.)
        self.assertAlmostEqual(r['entryToExitGrossPct'],4.)
        self.assertAlmostEqual(r['sameHighUpsideCapturePct'],80.)
        self.assertAlmostEqual(r['wholeOpportunityCapturePct'],80.)

    def test_whole_opportunity_differs_from_remaining_upside(self):
        r=evaluate(entry_price=1020.)
        self.assertAlmostEqual(r['wholeOpportunityCapturePct'],40.)
        self.assertAlmostEqual(r['sameHighUpsideCapturePct'],2000/30)
        self.assertAlmostEqual(r['entryPositionPct'],40.)

    def test_negative_capture_not_clamped(self):
        r=evaluate(exit_price=990.)
        self.assertEqual(r['wholeOpportunityCapturePct'],-20.)
        self.assertEqual(r['sameHighUpsideCapturePct'],-20.)

    def test_over_100_not_clamped_or_replaced_with_best_high(self):
        r=evaluate(exit_price=1060.)
        self.assertEqual(r['sameHighUpsideCapturePct'],120.)
        self.assertEqual(r['wholeOpportunityCapturePct'],120.)
        self.assertEqual(r['sameHighEvaluatorGapPp'],-1.)

    def test_cost_is_explicit_and_separate(self):
        r=evaluate(cost_pp=.07)
        self.assertAlmostEqual(r['entryToExitNetPct'],3.93)
        self.assertEqual(r['sameHighUpsideCapturePct'],80.)
        for cost in (None,-.1,True,float('nan')):
            with self.subTest(cost=cost),self.assertRaises(ValueError):evaluate(cost_pp=cost)

    def test_no_entry_does_not_become_zero_return(self):
        r=evaluate(entry_price=None,entry_minute=None,exit_price=None,exit_minute=None)
        self.assertEqual(r['bucket'],'>=5%')
        self.assertEqual(r['captureStatus'],'NO_ENTRY')
        self.assertIsNone(r['entryToExitNetPct'])

    def test_unresolved_exit_keeps_available_upside_but_no_capture(self):
        r=evaluate(exit_price=None,exit_minute=None)
        self.assertEqual(r['captureStatus'],'UNRESOLVED_EXIT')
        self.assertEqual(r['entryToSameOrderedHighPct'],5.)
        self.assertIsNone(r['sameHighUpsideCapturePct'])
        self.assertIsNone(r['entryToExitNetPct'])

    def test_partial_geometry_is_observed_not_certified_bucket(self):
        r=evaluate(geometry=replace(G,coverage_status='PARTIAL'))
        self.assertEqual(r['observedBucket'],'>=5%')
        self.assertEqual(r['bucket'],'UNAVAILABLE')
        self.assertIsNone(r['sameHighUpsideCapturePct'])
        self.assertEqual(r['entryToExitGrossPct'],4.)

    def test_missing_geometry_does_not_erase_valid_return(self):
        r=evaluate(geometry=None)
        self.assertEqual(r['entryToExitGrossPct'],4.)
        self.assertIsNone(r['wholeOpportunityCapturePct'])

    def test_high_at_or_before_entry_not_remaining_upside(self):
        r=evaluate(entry_minute=600,exit_minute=610)
        self.assertEqual(r['captureStatus'],'ORDERED_HIGH_NOT_STRICTLY_AFTER_ENTRY')
        self.assertIsNone(r['entryToSameOrderedHighPct'])

    def test_no_positive_upside_not_divided_or_epsilon_filled(self):
        r=evaluate(entry_price=1050.)
        self.assertEqual(r['captureStatus'],'NON_POSITIVE_AVAILABLE_UPSIDE')
        self.assertIsNone(r['sameHighUpsideCapturePct'])
        self.assertIsNotNone(r['wholeOpportunityCapturePct'])

    def test_future_high_gap_not_owned_giveback(self):
        r=evaluate(exit_minute=590,owned_peak=1045.,owned_peak_confirmed_at=589,owned_path_complete=True)
        self.assertTrue(r['sameHighAfterExit'])
        self.assertEqual(r['sameHighEvaluatorGapPp'],1.)
        self.assertEqual(r['ownedPeakGivebackPp'],.5)

    def test_endpoint_stamped_auction_high_is_known_at_terminal_exit(self):
        g=OrderedGeometry(1000.,1050.,920,930,930,'SYNTHETIC_ENDPOINT_AUCTION','COMPLETE',930)
        r=evaluate(geometry=g,exit_price=1050.,exit_minute=930)
        self.assertFalse(r['sameHighAfterExit'])
        self.assertEqual(r['geometryHighKnownAt'],930)
        with self.assertRaises(ValueError):
            evaluate(geometry=replace(g,high_known_at=None),exit_price=1050.,exit_minute=930)

    def test_exit_bar_high_cannot_be_credited_as_owned(self):
        with self.assertRaises(ValueError):evaluate(owned_peak=1050.,owned_peak_confirmed_at=611,owned_path_complete=True)

    def test_partial_owned_path_does_not_certify_giveback(self):
        self.assertIsNone(evaluate(owned_peak=1050.,owned_peak_confirmed_at=601)['ownedPeakGivebackPp'])

    def test_exit_reference_new_high_has_zero_owned_giveback(self):
        r=evaluate(exit_price=1060.,owned_peak=1050.,owned_peak_confirmed_at=601,owned_path_complete=True)
        self.assertEqual(r['ownedPeakGivebackPp'],0.)

    def test_order_and_horizon_errors_not_hidden(self):
        with self.assertRaises(ValueError):evaluate(geometry=replace(G,low_bar_start=600))
        with self.assertRaises(ValueError):evaluate(exit_minute=570)
        r=evaluate(exit_minute=930)
        self.assertEqual(r['captureStatus'],'OUTSIDE_COMMON_EVALUATION_HORIZON')
        self.assertIsNone(r['wholeOpportunityCapturePct'])
        self.assertEqual(r['entryToExitGrossPct'],4.)

    def test_zero_range_is_explicit(self):
        r=evaluate(geometry=replace(G,high=1000.))
        self.assertEqual(r['bucket'],'NON_POSITIVE_RANGE')
        self.assertIsNone(r['entryPositionPct'])

    def test_invalid_price_and_nan_are_rejected(self):
        for p in (0, -1, True, float('inf'), float('nan')):
            with self.subTest(price=p),self.assertRaises(ValueError):evaluate(entry_price=p)


    def test_post_entry_best_high_separate_from_ordered_high(self):
        h=PostEntryHigh(1060.,590,925,'SYNTHETIC_POST_ENTRY_HIGH','COMPLETE')
        r=evaluate(post_entry_high=h)
        self.assertEqual(r['sameHighUpsideCapturePct'],80.)
        self.assertAlmostEqual(r['postEntryUpsideCapturePct'],200/3)
        self.assertEqual(r['entryToPostEntryHighPct'],6.)
        self.assertIsNone(r['ownedPeakGivebackPp'])

    def test_post_entry_high_survives_missing_ordered_geometry(self):
        h=PostEntryHigh(1050.,600,925,'SYNTHETIC_POST_ENTRY_HIGH','COMPLETE')
        r=evaluate(post_entry_high=h,geometry=None)
        self.assertEqual(r['postEntryUpsideCapturePct'],80.)
        self.assertEqual(r['bucket'],'UNAVAILABLE')

    def test_post_entry_high_must_be_later_and_complete(self):
        h=PostEntryHigh(1050.,570,925,'SYNTHETIC_POST_ENTRY_HIGH','COMPLETE')
        r=evaluate(post_entry_high=h)
        self.assertIsNone(r['postEntryUpsideCapturePct'])
        self.assertEqual(r['postEntryCaptureStatus'],'HIGH_NOT_STRICTLY_AFTER_ENTRY')
        r=evaluate(post_entry_high=replace(h,high_bar_start=600,coverage_status='PARTIAL'))
        self.assertIsNone(r['postEntryUpsideCapturePct'])

    def test_horizons_must_match_when_both_are_supplied(self):
        h=PostEntryHigh(1050.,600,900,'SYNTHETIC_POST_ENTRY_HIGH','COMPLETE')
        with self.assertRaises(ValueError):evaluate(post_entry_high=h)

    def test_unresolved_exit_does_not_create_postentry_capture(self):
        h=PostEntryHigh(1050.,600,925,'SYNTHETIC_POST_ENTRY_HIGH','COMPLETE')
        r=evaluate(post_entry_high=h,exit_price=None,exit_minute=None)
        self.assertIsNone(r['postEntryUpsideCapturePct'])
        self.assertEqual(r['postEntryCaptureStatus'],'UNRESOLVED_EXIT')


if __name__ == '__main__':unittest.main()
