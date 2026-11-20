import unittest
import numpy as np

from scripts.phase57_prr_rank import low, route, percentile, bucket, SAFETY


class PreroutingContract(unittest.TestCase):
    def test_strict_train_median_and_tie(self):
        self.assertTrue(low(-.001, 0.))
        self.assertFalse(low(0., 0.))
        self.assertFalse(low(.001, 0.))

    def test_conjunction_and_disagreement(self):
        self.assertEqual(route(True, True), "DEFENSIVE_ELIGIBLE")
        for a, b in ((False, False), (True, False), (False, True)):
            self.assertEqual(route(a, b), "CONTROL_DEFAULT")

    def test_percentile_training_reference(self):
        train = np.array([-2., -1., 0., 1.])
        self.assertEqual(percentile(-.5, train), .5)
        self.assertEqual(percentile(-2., train), 0.)
        self.assertEqual(percentile(3., train), 1.)

    def test_evaluator_buckets_only(self):
        self.assertEqual([bucket(v) for v in (0., 1., 3., 5., 10.)],
                         ["<1", "1-3", "3-5", "5-10", ">=10"])

    def test_safety_nine_false(self):
        self.assertEqual(len(SAFETY), 9)
        self.assertFalse(any(SAFETY.values()))


if __name__ == "__main__":
    unittest.main()
