#!/usr/bin/env python3
"""Phase57 All-Material Entry evaluator extension v1.

Evaluator-only extension of the frozen State-Conditioned Signal Entry v1
measurement contract.  It does not create Entry decisions and never exports
future evaluator fields into a decision payload.
"""
from __future__ import annotations

import argparse
import collections
from pathlib import Path

from scripts import phase57_state_conditioned_signal_entry_v1 as base


LEVELS = (1, 2, 3, 4, 5)
CANONICAL_LEVELS = tuple(base.LEVELS)
POSITION_THRESHOLDS = (0.10, 0.15, 0.25, 0.50)
SAFETY = {key: False for key in base.SAFETY_KEYS}


def _id(row):
    return row["opportunity"]


def _bps_distribution(values_pct):
    return base.distribution(
        None if value is None else float(value) * 100.0
        for value in values_pct
    )


def _concentration(records, field):
    present = [row.get(field) for row in records if row.get(field) not in (None, "")]
    counts = collections.Counter(present)
    total = len(present)
    top = [
        {
            field: key,
            "count": count,
            "sharePctOfPresent": 100.0 * count / total if total else None,
        }
        for key, count in counts.most_common(20)
    ]
    return {
        "field": field,
        "population": len(records),
        "present": total,
        "missing": len(records) - total,
        "unique": len(counts),
        "top20": top,
    }


def _time_bucket(entry_minute):
    if not entry_minute:
        return None
    entry_minute = str(entry_minute)
    if "T" in entry_minute:
        clock = entry_minute.split("T", 1)[1]
    else:
        clock = entry_minute
    return clock[:5] if len(clock) >= 5 else clock


def capture_extended(opportunities, records):
    """Extend canonical Capture to +4 without changing +1/+2/+3/+5 semantics."""
    out = {}
    for level in LEVELS:
        winners = {
            row["opportunity"]
            for row in opportunities
            if row["selectorOutcome"]["mfeEnd"] is not None
            and row["selectorOutcome"]["mfeEnd"] >= level
        }
        counts = collections.Counter()
        seen = set()
        for row in records:
            opportunity = row["opportunity"]
            if opportunity not in winners:
                continue
            if opportunity in seen:
                raise AssertionError(("DUPLICATE_RECORD", opportunity))
            seen.add(opportunity)
            if not row["entryId"]:
                counts["noEntry"] += 1
            elif row["labels"]["mfeEnd"] is None:
                counts["unknownEntered"] += 1
            elif row["labels"]["mfeEnd"] >= level:
                counts["captured"] += 1
            else:
                counts["belowThreshold"] += 1
        denominator = len(winners)
        if seen != winners:
            missing = sorted(winners - seen)[:10]
            raise AssertionError(("MISSING_WINNER_RECORDS", level, missing))
        assert sum(counts.values()) == denominator
        out[str(level)] = {
            "selectorWinnerDenominator": denominator,
            "captured": counts["captured"],
            "missed": denominator - counts["captured"],
            "ratePct": 100.0 * counts["captured"] / denominator if denominator else None,
            "noEntry": counts["noEntry"],
            "unknownEntered": counts["unknownEntered"],
            "belowThreshold": counts["belowThreshold"],
        }

    canonical = base.capture(opportunities, records)
    for level in CANONICAL_LEVELS:
        key = str(level)
        if out[key] != canonical[key]:
            raise AssertionError(("CANONICAL_CAPTURE_PARITY", key, out[key], canonical[key]))
    return out


def policy_panel(opportunities, records):
    fills = [row for row in records if row["entryId"]]
    positions = [
        row["quality"].get("entryPosition")
        for row in fills
        if row["quality"].get("entryPosition") is not None
    ]
    position_n = len(positions)
    threshold_rates = {}
    for threshold in POSITION_THRESHOLDS:
        count = sum(value <= threshold for value in positions)
        threshold_rates[f"le{int(threshold * 100)}Pct"] = {
            "count": count,
            "denominator": position_n,
            "ratePct": 100.0 * count / position_n if position_n else None,
        }

    low_to_entry = [row["quality"].get("lowToEntryDistancePct") for row in fills]
    remaining_upside = [
        row["quality"].get("entryToLaterHighRemainingUpsidePct")
        for row in fills
    ]

    horizons = {}
    for horizon in ("30", "60"):
        panels = [
            row["labels"].get(horizon)
            for row in fills
            if row["labels"].get(horizon) is not None
        ]
        horizons[horizon] = {
            "validN": len(panels),
            "coverage": dict(collections.Counter(panel.get("status") for panel in panels)),
            "MFE": base.distribution(panel.get("MFE") for panel in panels),
            "MAE": base.distribution(panel.get("MAE") for panel in panels),
            "returnNet": base.distribution(panel.get("returnNet") for panel in panels),
        }

    time_counts = collections.Counter(
        bucket for bucket in (_time_bucket(row.get("entryMinute")) for row in records)
        if bucket is not None
    )

    sector_present = any("sector" in row and row.get("sector") not in (None, "") for row in records)
    return {
        "population": len(records),
        "fills": len(fills),
        "noEntry": len(records) - len(fills),
        "fillRatePct": 100.0 * len(fills) / len(records) if records else None,
        "entryPosition": base.distribution(positions),
        "entryPositionThresholds": threshold_rates,
        "lowToEntryDistancePct": base.distribution(low_to_entry),
        "lowToEntryDistanceBps": _bps_distribution(low_to_entry),
        "entryToLaterHighRemainingUpsidePct": base.distribution(remaining_upside),
        "entryToLaterHighRemainingUpsideBps": _bps_distribution(remaining_upside),
        "capture": capture_extended(opportunities, records),
        "horizons": horizons,
        "concentration": {
            "session": _concentration(records, "session"),
            "symbol": _concentration(records, "symbol"),
            "entryClockMinute": {
                "population": len(records),
                "present": sum(time_counts.values()),
                "missing": len(records) - sum(time_counts.values()),
                "unique": len(time_counts),
                "top20": [
                    {
                        "entryClockMinute": key,
                        "count": count,
                        "sharePctOfPresent": 100.0 * count / sum(time_counts.values())
                        if time_counts else None,
                    }
                    for key, count in time_counts.most_common(20)
                ],
            },
            "sector": _concentration(records, "sector")
            if sector_present
            else {
                "status": "UNAVAILABLE_IN_RECORD_SCHEMA",
                "population": len(records),
                "present": 0,
                "missing": len(records),
            },
        },
    }


def _subset(opportunities, records, ids):
    opp = [row for row in opportunities if row["opportunity"] in ids]
    rec = [row for row in records if row["opportunity"] in ids]
    assert len(opp) == len(ids)
    assert len(rec) == len(ids)
    return opp, rec


def upside_threshold_panels(opportunities, records):
    panels = {}
    extended = capture_extended(opportunities, records)
    for level in LEVELS:
        ids = {
            row["opportunity"]
            for row in opportunities
            if row["selectorOutcome"]["mfeEnd"] is not None
            and row["selectorOutcome"]["mfeEnd"] >= level
        }
        opp, rec = _subset(opportunities, records, ids)
        panels[str(level)] = {
            "selectorWinnerDefinition": f"selectorOutcome.mfeEnd >= {level}",
            "denominator": len(ids),
            "metrics": policy_panel(opp, rec),
            "captureAtSameThreshold": extended[str(level)],
        }
    return panels


def future_mfe_bucket_panels(opportunities, records):
    specs = (
        ("lt1", lambda x: x < 1, "<1%"),
        ("1to2", lambda x: 1 <= x < 2, "[1%,2%)"),
        ("2to3", lambda x: 2 <= x < 3, "[2%,3%)"),
        ("3to4", lambda x: 3 <= x < 4, "[3%,4%)"),
        ("4to5", lambda x: 4 <= x < 5, "[4%,5%)"),
        ("ge5", lambda x: x >= 5, ">=5%"),
    )
    panels = {}
    observed_ids = {
        row["opportunity"]
        for row in opportunities
        if row["selectorOutcome"]["mfeEnd"] is not None
    }
    assigned = set()
    for key, predicate, label in specs:
        ids = {
            row["opportunity"]
            for row in opportunities
            if row["selectorOutcome"]["mfeEnd"] is not None
            and predicate(row["selectorOutcome"]["mfeEnd"])
        }
        if assigned & ids:
            raise AssertionError(("OVERLAPPING_MFE_BUCKET", key))
        assigned |= ids
        opp, rec = _subset(opportunities, records, ids)
        panels[key] = {
            "futureEvaluatorOnly": True,
            "selectorMfeEndBucket": label,
            "denominator": len(ids),
            "metrics": policy_panel(opp, rec),
        }
    if assigned != observed_ids:
        raise AssertionError(("MFE_BUCKET_COVERAGE", len(assigned), len(observed_ids)))
    panels["missing"] = {
        "denominator": len(opportunities) - len(observed_ids),
        "futureEvaluatorOnly": True,
    }
    return panels


def _assert_population(opportunities, records):
    opportunity_ids = [_id(row) for row in opportunities]
    record_ids = [_id(row) for row in records]
    if len(opportunity_ids) != len(set(opportunity_ids)):
        raise AssertionError("DUPLICATE_OPPORTUNITY_IDS")
    if len(record_ids) != len(set(record_ids)):
        raise AssertionError("DUPLICATE_RECORD_IDS")
    if set(opportunity_ids) != set(record_ids):
        raise AssertionError(
            ("OPPORTUNITY_RECORD_ID_MISMATCH",
             len(set(opportunity_ids) - set(record_ids)),
             len(set(record_ids) - set(opportunity_ids)))
        )


def evaluate(opportunities, records, policy_name, baseline_records=None, baseline_name=None):
    _assert_population(opportunities, records)
    records_by_id = {_id(row): row for row in records}
    records = [records_by_id[_id(row)] for row in opportunities]

    base_summary = base.policy_summary(opportunities, records)
    extended_capture = capture_extended(opportunities, records)
    panel = policy_panel(opportunities, records)

    by_state = {}
    states = sorted({row.get("initialState", "UNKNOWN") for row in records})
    for state in states:
        ids = {_id(row) for row in records if row.get("initialState", "UNKNOWN") == state}
        opp, rec = _subset(opportunities, records, ids)
        by_state[state] = policy_panel(opp, rec)

    result = {
        "schemaVersion": 1,
        "name": "PHASE57_ALL_MATERIAL_ENTRY_EVALUATOR_V1",
        "policyName": policy_name,
        "evaluatorOnly": True,
        "decisionOutputsCreated": 0,
        "futureEvaluatorUsedForDecision": False,
        "population": len(records),
        "canonicalCaptureLevels": list(CANONICAL_LEVELS),
        "extendedCaptureLevels": list(LEVELS),
        "canonicalCaptureParity": {
            str(level): extended_capture[str(level)] == base_summary["capture"][str(level)]
            for level in CANONICAL_LEVELS
        },
        "overall": panel,
        "byState": by_state,
        "upsideThresholdPanels": upside_threshold_panels(opportunities, records),
        "futureSelectorMfeBuckets": future_mfe_bucket_panels(opportunities, records),
        "safety": SAFETY,
    }
    assert all(result["canonicalCaptureParity"].values())
    assert all(value is False for value in result["safety"].values())

    if baseline_records is not None:
        _assert_population(opportunities, baseline_records)
        baseline_by_id = {_id(row): row for row in baseline_records}
        baseline_records = [baseline_by_id[_id(row)] for row in opportunities]
        baseline_summary = base.policy_summary(opportunities, baseline_records)
        paired, _ = base.paired_summary(
            baseline_records, records, baseline_summary, base_summary
        )
        result["baselineComparison"] = {
            "baselineName": baseline_name or "baseline",
            "commonCasePaired": paired,
            "baselineOverall": policy_panel(opportunities, baseline_records),
        }
    return result


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--opportunities", required=True)
    parser.add_argument("--records", required=True)
    parser.add_argument("--policy-name", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--baseline-records")
    parser.add_argument("--baseline-name")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    opportunities = base.read_json(Path(args.opportunities))
    records = base.read_json(Path(args.records))
    baseline_records = (
        base.read_json(Path(args.baseline_records)) if args.baseline_records else None
    )
    result = evaluate(
        opportunities,
        records,
        args.policy_name,
        baseline_records=baseline_records,
        baseline_name=args.baseline_name,
    )
    base.write_json(Path(args.output), result)


if __name__ == "__main__":
    main()
