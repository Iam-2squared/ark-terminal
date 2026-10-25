import unittest
from scripts.phase57_state_definition_v02 import direction, structure_from_pivots, phase, breakout

class TestStateDefinitionV02(unittest.TestCase):
    def test_direction(self):
        self.assertEqual(direction([100,101]),"UP")
        self.assertEqual(direction([101,100]),"DOWN")
        self.assertEqual(direction([100,100]),"UNCHANGED")
    def test_up_structure(self):
        p=[{"kind":"H","price":101},{"kind":"L","price":99},{"kind":"H","price":103},{"kind":"L","price":100}]
        self.assertEqual(structure_from_pivots(p,102)["value"],"UP_STRUCTURE")
    def test_down_structure(self):
        p=[{"kind":"H","price":103},{"kind":"L","price":100},{"kind":"H","price":102},{"kind":"L","price":98}]
        self.assertEqual(structure_from_pivots(p,99)["value"],"DOWN_STRUCTURE")
    def test_not_observable(self):
        self.assertEqual(structure_from_pivots([{"kind":"H","price":101}],100)["status"],"NOT_OBSERVABLE")
    def test_correction_recovery(self):
        self.assertIn("CORRECTION",phase("UP_STRUCTURE","DOWN"))
        self.assertIn("RECOVERY",phase("UP_STRUCTURE","UP",recovery=.5))
    def test_restructuring(self):
        self.assertEqual(phase("UP_STRUCTURE","DOWN",invalidated=True),["RESTRUCTURING"])
    def test_wick_and_cross(self):
        self.assertEqual(breakout(99,99.5,101,100),"WICK_TOUCH_UP")
        self.assertEqual(breakout(99,100.5,101,100),"CLOSE_CROSS_UP")

if __name__=="__main__": unittest.main()
