"""Zero-fit tests for evaluator-only paired reporting and certified nulls."""
import unittest
from decimal import Decimal
from scripts import phase57_exit_continuation_r52_cycle2_report as report

class Cycle2ReportTests(unittest.TestCase):
    def test_identical_quantity_exit_capture_and_bucket(self):
        baseline={'funded':{'ENTRY':{'quantity':100,'notionalJpy':'10000',
            'effectiveEntryPrice':'100','entryMinute':570}}}
        row={'entryId':'ENTRY','controlPnlJpy':'-5',
            'candidatePnlJpy':'994.5','controlExitMinute':580,'newExitMinute':600,
            'evaluatorOnlyUpsidePct':20.0}
        paired=report.paired_rows([row],baseline)
        self.assertEqual(paired['candidate'][0]['bucket'],'>=10%')
        self.assertEqual(paired['candidate'][0]['pnlJpy'],Decimal('994.5'))
        self.assertAlmostEqual(paired['candidate'][0]['capturePct'],50)
        self.assertEqual(paired['candidate'][0]['holdingWallMinutes'],30)
        self.assertEqual(paired['control'][0]['holdingWallMinutes'],10)

    def test_unresolved_is_null_and_does_not_create_profit(self):
        baseline={'funded':{'ENTRY':{'quantity':100,'notionalJpy':'10000',
            'effectiveEntryPrice':'100','entryMinute':570}}}
        row={'entryId':'ENTRY','controlPnlJpy':None,'candidatePnlJpy':None,
            'controlExitMinute':None,'newExitMinute':None,'evaluatorOnlyUpsidePct':None}
        paired=report.paired_rows([row],baseline)
        s=report.layer_a_groups(paired['candidate'])
        self.assertEqual(s['All baseline funded']['unresolved'],1)
        self.assertIsNone(s['All baseline funded']['meanNetPct'])
        self.assertEqual(s['All baseline funded']['pnlJpy'],'0')
        self.assertEqual(s['UNKNOWN/CENSORED']['n'],1)

if __name__=='__main__':unittest.main()
