"""Corruption tests for the independent data/OOF audit; no estimators execute."""
import copy
import hashlib
import unittest

import numpy as np

from scripts import phase57_exit_gen2_data_audit_r43 as audit


def complete_rows():
    return [[int(m), 100, 100.5, 99.5, 100, 1, 1] for m in audit.STARTS]


class DataAuditCorruptionTest(unittest.TestCase):
    def test_oof_rejects_in_sample_and_terminal_predictions(self):
        scored = np.array([False, True, False])
        good = np.array([[np.nan, np.nan], [.2, .7], [np.nan, np.nan]], dtype=np.float32)
        audit.check_oof({"spec": good}, {"spec"}, scored, 3)
        for row in (0, 2):
            bad = good.copy(); bad[row, 0] = .5
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, "OOF_OUTSIDE_SCORE_FOLD_OR_TERMINAL"):
                audit.check_oof({"spec": bad}, {"spec"}, scored, 3)

    def test_oof_rejects_missing_and_out_of_range_scores(self):
        for value in (np.nan, np.inf, -0.001, 1.001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit.check_oof({"spec": np.array([[value, .7]], dtype=np.float32)}, {"spec"}, np.array([True]), 1)

    def test_oof_rejects_extra_spec_or_wrong_shape(self):
        good = np.array([[.2, .7]], dtype=np.float32)
        with self.assertRaisesRegex(ValueError, "OOF_SPEC_KEYS"):
            audit.check_oof({"spec": good, "extra": good}, {"spec"}, np.array([True]), 1)
        with self.assertRaisesRegex(ValueError, "OOF_SHAPE"):
            audit.check_oof({"spec": good[:, :1]}, {"spec"}, np.array([True]), 1)

    def test_missing_late_window_is_not_a_positive_shortcut(self):
        rows = complete_rows()
        next(r for r in rows if r[0] == 600)[2] = 105
        rows = [r for r in rows if r[0] != 659]
        result = audit.independent_labels(rows, np.array([600]))
        self.assertTrue(np.isnan(result["targets"][0, 0]))
        self.assertEqual(result["targets"][0, 1], 0)
        self.assertEqual(result["reasonCode"][0].tolist(), [4, 0])

    def test_label_mask_or_known_at_corruption_fails(self):
        now = np.array([600, 925])
        expected = audit.independent_labels(complete_rows(), now)
        audit.check_label_arrays(expected, expected, now)
        for name, index, value in (("available", (1, 0), True), ("targets", (1, 0), 0),
                                   ("knownAt", (0, 0), 600), ("horizonBars", (0, 0), 59)):
            bad = copy.deepcopy(expected); bad[name][index] = value
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "LABEL_CONTENT"):
                audit.check_label_arrays(bad, expected, now)

    def test_same_bar_two_events_and_lunch_maturity(self):
        rows = complete_rows()
        next(r for r in rows if r[0] == 750)[2:4] = [101, 99.25]
        result = audit.independent_labels(rows, np.array([690, 925]))
        self.assertEqual(result["targets"][0].tolist(), [1, 1])
        self.assertEqual(result["knownAt"][0].tolist(), [810, 765])
        self.assertTrue(np.isnan(result["targets"][1]).all())

    def test_weighting_balances_sessions_then_entries(self):
        result = audit.expected_weights(np.array([0, 0, 0, 1, 1, 1]), np.array([0, 0, 1, 2, 2, 2]))
        expected = np.array([.75, .75, 1.5, 1, 1, 1], dtype="<f8")
        self.assertEqual(result["weightSha256"], hashlib.sha256(expected.tobytes()).hexdigest())
        self.assertEqual((result["rows"], result["sessions"], result["opportunities"]), (6, 2, 3))


if __name__ == "__main__":
    unittest.main()
