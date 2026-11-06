import unittest

from scripts.phase57_entry_unknown_coverage_diagnostic import (
    causal_trajectory,
    phase_age_bucket,
    unknown_reason,
)


def row(delay, minute, value5, *, new_closed=True, through=None):
    return {
        "opportunity": "SYNTH",
        "delay": delay,
        "minute": minute,
        "computedThroughBarStart": through if through is not None else minute - 1,
        "newClosedBarObserved": new_closed,
        "context": {
            "returnPct": {"1": None, "3": None, "5": value5, "10": None},
            "previousDayAvailable": True,
        },
    }


class UnknownCoverageDiagnosticTests(unittest.TestCase):
    def test_unknown_reason_phase_history(self):
        self.assertEqual(
            unknown_reason(row(0, 544, None)),
            "INSUFFICIENT_PHASE_HISTORY_FOR_RETURN5",
        )
        self.assertEqual(
            unknown_reason(row(0, 754, None)),
            "INSUFFICIENT_PHASE_HISTORY_FOR_RETURN5",
        )

    def test_unknown_reason_no_new_closed_bar(self):
        self.assertEqual(
            unknown_reason(row(0, 600, None, new_closed=False, through=598)),
            "NO_NEW_CLOSED_BAR_AT_ASOF",
        )

    def test_unknown_reason_contiguous_window_unavailable(self):
        self.assertEqual(
            unknown_reason(row(0, 600, None, new_closed=True)),
            "STRICT_CONTIGUOUS_WINDOW_UNAVAILABLE",
        )

    def test_rejects_defined_row_as_unknown(self):
        with self.assertRaisesRegex(ValueError, "ROW_NOT_UNKNOWN"):
            unknown_reason(row(0, 600, 0.1))

    def test_causal_trajectory_first_defined_and_offsets(self):
        rows = [
            row(0, 600, None),
            row(1, 601, None),
            row(2, 602, 0.2),
            row(3, 603, -0.1),
            row(5, 605, 0.0),
            row(10, 610, 0.4),
        ]
        out = causal_trajectory(rows)
        self.assertEqual(out["firstDefinedDelay"], 2)
        self.assertEqual(out["firstDefinedState"], "UP")
        self.assertEqual(out["exactOffsets"]["1"]["state"], "UNKNOWN")
        self.assertEqual(out["exactOffsets"]["2"]["state"], "UP")
        self.assertEqual(out["exactOffsets"]["3"]["state"], "DOWN")
        self.assertEqual(out["exactOffsets"]["5"]["state"], "NEUTRAL")
        self.assertEqual(out["exactOffsets"]["10"]["state"], "UP")
        self.assertEqual(
            out["transitionSignatureThroughT10"],
            "UNKNOWN>UP>DOWN>NEUTRAL>UP",
        )

    def test_missing_offset_is_preserved_not_imputed(self):
        rows = [row(0, 600, None), row(2, 602, 0.2)]
        out = causal_trajectory(rows)
        self.assertFalse(out["exactOffsets"]["1"]["checkpointPresent"])
        self.assertEqual(out["exactOffsets"]["1"]["state"], "NO_CHECKPOINT")

    def test_phase_age_bucket_respects_lunch_boundary(self):
        self.assertEqual(phase_age_bucket(540), "PHASE_AGE_0_5")
        self.assertEqual(phase_age_bucket(750), "PHASE_AGE_0_5")
        self.assertEqual(phase_age_bucket(756), "PHASE_AGE_6_10")
        self.assertEqual(phase_age_bucket(781), "PHASE_AGE_31_60")


if __name__ == "__main__":
    unittest.main()
