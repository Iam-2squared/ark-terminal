"""Zero-cohort-safe runner for the frozen nine-State evaluator anatomy.

V1 correctly computes populated cohorts but the inherited paired-summary helper
subtracts ``None`` fill rates for the deliberately empty RISE_STOP T0 cohort.
This wrapper changes only that zero-population reporting edge case.  All populated
cohorts and evaluator definitions are delegated byte-for-byte to v1.
"""
from __future__ import annotations

from scripts import phase57_nine_state_anatomy_v1 as v1


def zero_pair():
    empty = {"count": 0, "mean": None, "median": None, "p25": None,
             "p5": None, "p75": None, "p90": None, "p95": None}
    return {
        "population": 0,
        "pairStatus": {},
        "fillRateDeltaPp": None,
        "fillDelta": 0,
        "entryPositionDelta": dict(empty),
        "lowToEntryDistanceDeltaPct": dict(empty),
        "priceImprovementPct": dict(empty),
        "delayDelta": dict(empty),
        "remainingUpsideDeltaPct": dict(empty),
        "MFE30DeltaPp": dict(empty),
        "MAE30DeltaPp": dict(empty),
        "MFE60DeltaPp": dict(empty),
        "MAE60DeltaPp": dict(empty),
        "captureDeltaPp": {},
        "sessionEqualPriceBootstrap": None,
        "status": "NO_T0_OBSERVATIONS",
    }


_original = v1.paired_compact


def paired_compact_zero_safe(base_rows, candidate_rows, base_summary, candidate_summary):
    if not base_rows and not candidate_rows:
        return zero_pair()
    return _original(base_rows, candidate_rows, base_summary, candidate_summary)


v1.paired_compact = paired_compact_zero_safe


def main():
    v1.main()


if __name__ == "__main__":
    main()
