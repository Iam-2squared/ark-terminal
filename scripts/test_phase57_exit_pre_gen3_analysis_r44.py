import unittest
import numpy as np
from scripts.phase57_exit_pre_gen3_analysis_r44 import overlap,path_class
class Diagnostics(unittest.TestCase):
 def test_overlap_missing_is_not_false(self):
  r=overlap(np.array([0,0,1,1,np.nan]),np.array([0,1,0,1,1]));self.assertEqual(r['bothAvailableN'],4);self.assertTrue(all(v['n']==1 for v in r['cells'].values()))
 def test_empty_overlap(self):self.assertEqual(overlap(np.array([np.nan]),np.array([0]))['cells']['C0F0']['fraction'],None)
 def test_groups_are_evaluator_only(self):
  r={'exitStatus':'RESOLVED','metrics':{'bucket':'>=5%','postEntryUpsideCapturePct':60,'postEntryHighEvaluatorGapPp':3,'postEntryHighKnownAt':600},'netReturnPctBySellCost':{'0.05':3},'activeMinutesHeld':40,'exitMinute':650}
  self.assertEqual(path_class(r),'A_RETAINED_WINNER')
  r['metrics']['postEntryUpsideCapturePct']=20;self.assertEqual(path_class(r),'B_GIVEBACK_WINNER')
  r['exitStatus']='UNRESOLVED_TERMINAL_EXIT';self.assertEqual(path_class(r),'CENSORED')
