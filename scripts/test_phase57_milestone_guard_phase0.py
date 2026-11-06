"""Focused zero-fit contract checks; no Guard candidate is instantiated."""
import json
import unittest

from scripts import phase57_milestone_guard_phase0 as mg


class MilestonePhase0Test(unittest.TestCase):
    def test_floor_mapping_matches_precommit(self):
        frozen=json.loads((mg.EVIDENCE/'CYCLE_PRECOMMIT.json').read_text())
        self.assertEqual(frozen['milestones']['highestToFloorPct'],
                         {str(k):v for k,v in mg.FLOORS.items()})
        self.assertEqual(frozen['milestones']['confirmation'],2)
        self.assertFalse(any(frozen['safety'].values()))

    def test_same_bar_is_unknown(self):
        # +1 and +2 touch alongside a breach of floor 0 in one bar.
        rows=[(541,(100,102.1,99.9,101))]
        reached={1:mg.reached_at(rows,100,1)}
        self.assertEqual(mg.passage(rows,100,reached,1,2,0)['status'],
                         'AMBIGUOUS_SAME_BAR')

    def test_two_closed_breaches_are_recorded(self):
        rows=[(541,(100,101.1,100.0,100.5)),
              (542,(100.5,100.6,99.8,99.9)),
              (543,(99.9,100.0,99.4,99.6))]
        reached={1:mg.reached_at(rows,100,1)}
        found=mg.passage(rows,100,reached,1,2,0)
        self.assertEqual(found['status'],'FLOOR_FIRST')
        self.assertTrue(found['twoCheckpointUnrecovered'])

    def test_missing_bar_cannot_certify_first_passage(self):
        rows=[(541,None),(542,(100,102.2,100,102))]
        reached={1:mg.reached_at(rows,100,1)}
        self.assertEqual(reached[1][0],'MISSING_PRIOR')
        self.assertEqual(mg.passage(rows,100,reached,1,2,0)['status'],
                         'MISSING_PRIOR')

    def test_auc_handles_ties_and_single_class(self):
        self.assertAlmostEqual(mg.roc([0,1,0,1],[.1,.2,.2,.3]),.875)
        self.assertIsNone(mg.roc([1,1],[.2,.3]))


if __name__=='__main__':unittest.main()
