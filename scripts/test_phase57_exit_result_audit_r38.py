import copy
import unittest
import numpy as np
from scripts import phase57_exit_result_audit_r38 as audit


class ResultAuditTests(unittest.TestCase):
    def row(self, exit_minute=543, kind='MODEL_EXIT'):
        return {'entryArm':'IMMEDIATE','entryId':'2025-07-03|11110|540',
            'session':'2025-07-03','entryMinute':540,'entryPrice':100.,
            'exitKind':kind,'exitMinute':exit_minute,'exitPrice':102.,
            'exitStatus':'RESOLVED','metrics':{'ownedPeakGivebackPp':None},
            'netReturnPctBySellCost':{'0.05':1.95}}

    def path(self):
        return [[540,100,101,99,100,1,1],[541,100,105,99,101,1,1],
                [542,101,104,100,103,1,1],[543,102,999,1,102,1,1]]

    def test_reproduce_numpy_scalar_defect_without_changing_frozen_runner(self):
        self.assertFalse(audit.frozen.finite(np.float32(105)))
        self.assertTrue(audit.frozen.finite(float(np.float32(105))))

    def test_repair_only_owned_field_and_exclude_exit_candle(self):
        row=self.row(); before=copy.deepcopy(row)
        result=audit.corrected_row(row,self.path())
        self.assertEqual(result['metrics']['ownedPeakGivebackPp'],3.)
        self.assertEqual(row,before)
        result['metrics']['ownedPeakGivebackPp']=None
        self.assertEqual(row,result)

    def test_missing_prefix_not_certified(self):
        self.assertIsNone(audit.corrected_row(self.row(),self.path()[1:])['metrics']['ownedPeakGivebackPp'])

    def test_suffix_mutation_invariance(self):
        a=self.path(); b=copy.deepcopy(a); b[-1][2]=1e8
        self.assertEqual(audit.corrected_row(self.row(),a),audit.corrected_row(self.row(),b))

    def test_lunch_and_terminal_inverse(self):
        self.assertEqual(audit.decision_now(self.row(750)),690)
        self.assertEqual(audit.decision_now(self.row(930,'FORCED_TERMINAL')),925)

    def test_unresolved_has_no_metric(self):
        row=self.row(); row.update(exitStatus='UNRESOLVED_TERMINAL_EXIT',exitMinute=None,exitKind=None,exitPrice=None)
        self.assertEqual(audit.corrected_row(row,[]),row)


if __name__ == '__main__':
    unittest.main()
