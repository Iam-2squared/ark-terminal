#!/usr/bin/env python3
"""Phase57 All-Material Entry cohort-native feature coverage audit.

This is a Development-only inventory/audit. It does not read Entry performance
metrics, fit a model, create predictions, choose thresholds, or change decisions.

It proves exact 2,155 cohort identity and measures causal feature availability
for the already-committed Entry Pattern v2 substrate, frozen six-signal census,
and State-v3 checkpoints. Missing values remain missing; no future fill/backfill
is performed.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PATTERN = ROOT / "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate"
TIMING = ROOT / "docs/evidence/phase57-entry-timing-signal-census-v1/measurement"
STATE = ROOT / "docs/evidence/phase57-state-v3-9pattern-entry-v1/measurement"

SAFETY = {
    "executionAllowed": False,
    "brokerWriteAllowed": False,
    "excelOrderWriteAllowed": False,
    "rssOrderFunctionAllowed": False,
    "liveTradingAllowed": False,
    "paperTradingAllowed": False,
    "automaticPromotionAllowed": False,
    "productionUpdateAllowed": False,
    "transmitted": False,
}
SIGNAL_FAMILIES = (
    "CONTINUATION", "BREAKOUT", "COMPRESSION_EXPANSION",
    "HIGHER_LOW", "LOWER_WICK", "RECLAIM",
)
STATE_LABELS = (
    "RISE_STOP", "RISE", "SHARP_RISE", "PULLBACK", "RANGE",
    "REBOUND", "SHARP_DROP", "DROP", "DROP_STOP",
)


def read_json(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def active_ordinal(minute: int) -> int:
    if 540 <= minute <= 690:
        return minute - 540
    if 750 <= minute <= 930:
        return 150 + minute - 750
    raise ValueError(f"OUTSIDE_ACTIVE_SESSION:{minute}")


def active_elapsed(start: int, end: int) -> int:
    return active_ordinal(end) - active_ordinal(start)


def pct(n: int, d: int):
    return 100.0 * n / d if d else None


def summary(values):
    xs = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not xs:
        return {"n": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "n": len(xs),
        "min": min(xs),
        "median": statistics.median(xs),
        "mean": statistics.fmean(xs),
        "max": max(xs),
    }


def load_matrix(path: Path):
    with gzip.open(path, "rb") as fh:
        return np.load(fh, allow_pickle=False)


def cohort_ids():
    cohort = read_json(TIMING / "opportunity-records.json.gz")
    assert len(cohort) == 2155
    ids = [row["opportunity"] for row in cohort]
    assert len(ids) == len(set(ids)) == 2155
    sessions = sorted({row["session"] for row in cohort})
    assert len(sessions) == 59
    return cohort, set(ids), set(sessions)


def build_pattern_coverage(ids, sessions):
    p0 = read_json(PATTERN / "p0-audit.json")
    assert p0["status"] == "PASS"
    assert p0["all144"] is True
    assert p0["previousCausal"] is True
    assert p0["todayPrefixCausal"] is True
    assert p0["featureNoWHO"] is True
    assert p0["holdoutOpened"] == 0
    assert all(v is False for v in p0["safety"].values())

    names = read_json(PATTERN / "names.json")
    assert len(names) == len(set(names))
    opps = [row for row in read_json(PATTERN / "opportunities.json.gz")
            if row["session"] in sessions]
    pids = {row["id"] for row in opps}
    assert len(opps) == 2155
    assert pids == ids

    rows = [row for row in read_json(PATTERN / "rows.json.gz")
            if row["session"] in sessions]
    by_session = collections.defaultdict(list)
    for row in rows:
        by_session[row["session"]].append(row)

    decision_rows = []
    finite_counts = np.zeros(len(names), dtype=np.int64)
    t0_counts = np.zeros(len(names), dtype=np.int64)
    decision_n = 0
    t0_n = 0
    row_meta = collections.Counter()
    opportunity_decision_counts = collections.Counter()

    for day in sorted(sessions):
        day_rows = by_session[day]
        matrix = load_matrix(PATTERN / f"{day}.npy.gz")
        assert matrix.shape == (len(day_rows), len(names)), (day, matrix.shape, len(day_rows), len(names))
        for local_i, row in enumerate(day_rows):
            assert row["opportunity"] in ids
            # R1 sequential policy uses T0 through T+30 active-minute checkpoints.
            if not row.get("eligible1") or int(row["delay"]) > 30:
                continue
            values = matrix[local_i]
            finite = np.isfinite(values)
            finite_counts += finite
            decision_n += 1
            opportunity_decision_counts[row["opportunity"]] += 1
            if int(row["delay"]) == 0:
                t0_counts += finite
                t0_n += 1
            row_meta[("quoteAvailable", bool(row.get("quoteAvailable")))] += 1
            row_meta[("previousCoverage", str(row.get("previousCoverage")))] += 1
            row_meta[("todayCoverage", str(row.get("todayCoverage")))] += 1
            decision_rows.append({
                "opportunity": row["opportunity"],
                "session": row["session"],
                "minute": int(row["minute"]),
                "delay": int(row["delay"]),
            })

    assert len(opportunity_decision_counts) == 2155
    assert min(opportunity_decision_counts.values()) >= 1
    assert t0_n == 2155

    columns = {}
    groups = collections.defaultdict(list)
    for i, name in enumerate(names):
        available = int(finite_counts[i])
        t0_available = int(t0_counts[i])
        col = {
            "available": available,
            "missing": decision_n - available,
            "coveragePct": pct(available, decision_n),
            "t0Available": t0_available,
            "t0Missing": t0_n - t0_available,
            "t0CoveragePct": pct(t0_available, t0_n),
            "missingSemantics": "RAW_NAN_PRESERVED__NO_FUTURE_FILL__TRAIN_FOLD_ONLY_IMPUTATION_IF_MODEL_ADMITTED",
        }
        columns[name] = col
        groups[name.split("/", 1)[0]].append(col)

    group_summary = {}
    for group, cols in sorted(groups.items()):
        cov = [c["coveragePct"] for c in cols]
        t0cov = [c["t0CoveragePct"] for c in cols]
        group_summary[group] = {
            "columns": len(cols),
            "coveragePct": summary(cov),
            "t0CoveragePct": summary(t0cov),
            "fullCoverageColumns": sum(c == 100.0 for c in cov),
            "ge95CoverageColumns": sum(c >= 95.0 for c in cov),
            "ge80CoverageColumns": sum(c >= 80.0 for c in cov),
        }

    return {
        "source": "phase57-entry-pattern-v2/ci-result/substrate",
        "p0Audit": {
            "status": p0["status"],
            "all144": p0["all144"],
            "previousCausal": p0["previousCausal"],
            "todayPrefixCausal": p0["todayPrefixCausal"],
            "featureNoWHO": p0["featureNoWHO"],
            "holdoutOpened": p0["holdoutOpened"],
        },
        "population": len(opps),
        "sessions": len(sessions),
        "decisionRows": decision_n,
        "t0Rows": t0_n,
        "featureColumns": len(names),
        "opportunityDecisionRows": summary(opportunity_decision_counts.values()),
        "rowAvailability": {
            f"{k[0]}={k[1]}": v for k, v in sorted(row_meta.items(), key=lambda z: str(z[0]))
        },
        "columns": columns,
        "groups": group_summary,
        "decisionRowsKey": decision_rows,
        "sourceHashes": {
            "manifest": sha256(PATTERN / "manifest.json"),
            "names": sha256(PATTERN / "names.json"),
            "rows": sha256(PATTERN / "rows.json.gz"),
            "opportunities": sha256(PATTERN / "opportunities.json.gz"),
            "p0Audit": sha256(PATTERN / "p0-audit.json"),
        },
    }


def build_signal_coverage(ids, sessions, decision_rows):
    rows_by_key = {}
    source_files = []
    for day in sorted(sessions):
        path = TIMING / "minute-census" / f"{day}.json.gz"
        assert path.exists(), path
        source_files.append((day, sha256(path)))
        for row in read_json(path):
            oid = row["opportunity"]
            assert oid in ids
            key = (oid, int(row["minute"]))
            assert key not in rows_by_key
            rows_by_key[key] = row

    exact = 0
    fam = {name: collections.Counter() for name in SIGNAL_FAMILIES}
    closed_bar_violations = 0
    future_pivot_violations = 0
    for base in decision_rows:
        key = (base["opportunity"], base["minute"])
        row = rows_by_key.get(key)
        if row is None:
            continue
        exact += 1
        through = row.get("computedThroughBarStart")
        if through is not None and int(through) >= base["minute"]:
            closed_bar_violations += 1
        for name in SIGNAL_FAMILIES:
            sig = row["signals"][name]
            trigger = sig.get("trigger")
            fam[name]["available"] += trigger is not None
            fam[name]["true"] += trigger is True
            fam[name]["false"] += trigger is False
            fam[name]["unknown"] += trigger is None
            pivot = sig.get("pivot")
            if pivot and not (pivot["lowBarStart"] < pivot["confirmedAt"] <= base["minute"]):
                future_pivot_violations += 1

    assert closed_bar_violations == 0
    assert future_pivot_violations == 0
    out_fam = {}
    for name, c in fam.items():
        out_fam[name] = {
            **dict(c),
            "coveragePct": pct(c["available"], exact),
            "missingSemantics": "TRISTATE_UNKNOWN_PRESERVED__NO_FUTURE_INFERENCE",
        }
    return {
        "source": "phase57-entry-timing-signal-census-v1/measurement/minute-census",
        "sourceRows": len(rows_by_key),
        "decisionRows": len(decision_rows),
        "exactJoinRows": exact,
        "exactJoinCoveragePct": pct(exact, len(decision_rows)),
        "closedBarViolations": closed_bar_violations,
        "futurePivotViolations": future_pivot_violations,
        "families": out_fam,
        "sourceHashes": {
            "manifest": sha256(TIMING / "manifest.json"),
            "cohort": sha256(TIMING / "cohort.json"),
            "minuteCensusAggregate": hashlib.sha256(
                "\n".join(f"{day}:{digest}" for day, digest in source_files).encode()
            ).hexdigest(),
        },
    }


def build_state_coverage(ids, decision_rows):
    rows = read_json(STATE / "state-checkpoints.json.gz")
    by_opp = collections.defaultdict(list)
    for row in rows:
        oid = row["opportunity"]
        assert oid in ids
        minute = int(row.get("asOf", row.get("minute")))
        by_opp[oid].append((minute, row))
    assert len(by_opp) == 2155
    for oid in by_opp:
        by_opp[oid].sort(key=lambda x: x[0])

    exact = 0
    asof = 0
    valid = 0
    invalid = 0
    stale = []
    state_counts = collections.Counter()
    future_violations = 0
    transitions_available = 0
    dwell_available = 0
    churn_available = 0

    for base in decision_rows:
        checks = by_opp[base["opportunity"]]
        eligible = [(minute, row) for minute, row in checks if minute <= base["minute"]]
        if not eligible:
            continue
        minute, row = eligible[-1]
        asof += 1
        exact += minute == base["minute"]
        stale.append(active_elapsed(minute, base["minute"]))
        if row.get("maxSourceBarStart") is not None and int(row["maxSourceBarStart"]) >= base["minute"]:
            future_violations += 1
        state = row.get("state")
        if state in STATE_LABELS and row.get("dataQuality") != "INVALID":
            valid += 1
            state_counts[state] += 1
        else:
            invalid += 1

        history = [(m, r) for m, r in checks if m <= base["minute"]]
        if history:
            dwell_available += 1
            transitions_available += 1
            churn_available += 1

    assert future_violations == 0
    return {
        "source": "phase57-state-v3-9pattern-entry-v1/measurement/state-checkpoints.json.gz",
        "sourceRows": len(rows),
        "decisionRows": len(decision_rows),
        "exactCheckpointRows": exact,
        "exactCheckpointCoveragePct": pct(exact, len(decision_rows)),
        "asOfJoinRows": asof,
        "asOfJoinCoveragePct": pct(asof, len(decision_rows)),
        "validStateRows": valid,
        "validStateCoveragePct": pct(valid, len(decision_rows)),
        "invalidStateRows": invalid,
        "asOfStalenessActiveMinutes": summary(stale),
        "stateCounts": dict(sorted(state_counts.items())),
        "derivedCausalCoverage": {
            "currentStateAsOf": asof,
            "priorState": transitions_available,
            "transitionCount": transitions_available,
            "dwell": dwell_available,
            "churn": churn_available,
        },
        "futureBarViolations": future_violations,
        "missingSemantics": "LAST_KNOWN_FROZEN_STATE_CHECKPOINT_CARRY_FORWARD_ONLY__NEVER_FUTURE_STATE",
        "sourceHashes": {
            "manifest": sha256(STATE / "manifest.json"),
            "stateCheckpoints": sha256(STATE / "state-checkpoints.json.gz"),
            "causalityAudit": sha256(STATE / "causality-audit.json"),
        },
    }


def run():
    cohort, ids, sessions = cohort_ids()
    pattern = build_pattern_coverage(ids, sessions)
    signal = build_signal_coverage(ids, sessions, pattern.pop("decisionRowsKey"))
    # Re-create compact keys without re-reading matrices.
    rows = [row for row in read_json(PATTERN / "rows.json.gz")
            if row["session"] in sessions and row.get("eligible1") and int(row["delay"]) <= 30]
    decision_rows = [{
        "opportunity": row["opportunity"],
        "session": row["session"],
        "minute": int(row["minute"]),
        "delay": int(row["delay"]),
    } for row in rows]
    state = build_state_coverage(ids, decision_rows)

    cohort_ids_hash = hashlib.sha256(
        "\n".join(sorted(ids)).encode()
    ).hexdigest()
    result = {
        "id": "PHASE57_ALL_MATERIAL_COHORT_NATIVE_FEATURE_COVERAGE_V1",
        "scope": "Development-only causal coverage/missingness audit; zero performance metrics read",
        "cohort": {
            "population": len(cohort),
            "sessions": len(sessions),
            "firstSession": min(sessions),
            "lastSession": max(sessions),
            "opportunityIdsSHA256": cohort_ids_hash,
            "timingCensusPinnedOpportunityIdsSHA256": read_json(TIMING / "cohort.json")["opportunityIdsSHA256"],
        },
        "patternSubstrate": pattern,
        "sixSignals": signal,
        "stateV3": state,
        "integrity": {
            "patternPopulationExact2155": pattern["population"] == 2155,
            "t0RowsExact2155": pattern["t0Rows"] == 2155,
            "signalExactJoinComplete": signal["exactJoinRows"] == pattern["decisionRows"],
            "stateAsOfJoinComplete": state["asOfJoinRows"] == pattern["decisionRows"],
            "futureBarViolations": signal["closedBarViolations"] + signal["futurePivotViolations"] + state["futureBarViolations"],
            "performanceMetricsRead": 0,
            "modelFits": 0,
            "modelPredictions": 0,
            "providerRequests": 0,
            "protectedDataOpened": 0,
        },
        "conditionalFamilyDispositionInputs": {
            "volumeTurnover": {
                "sourceProof": "PATTERN_P0_PREFIX_CAUSAL",
                "columns": [n for n in pattern["columns"] if any(tok in n.lower() for tok in ("volume", "/value", "/va", "/vo"))],
                "automaticAdmission": False,
            },
            "marketContext": {"availableInAuditedSources": False, "automaticAdmission": False},
            "sectorContext": {"availableInAuditedSources": False, "automaticAdmission": False},
            "liquidityTradabilityTick": {"availableInAuditedSources": False, "automaticAdmission": False},
            "pointInTimeSymbolProfile": {"availableInAuditedSources": False, "automaticAdmission": False},
            "dictionaryDescriptors": {"availableInAuditedSources": False, "automaticAdmission": False},
        },
        "missingPolicy": {
            "decisionTime": "missing remains missing",
            "futureBackfill": False,
            "interpolationFromFuture": False,
            "modelPreprocessing": "fit imputer/scaler on train fold only; missing indicators allowed",
        },
        "safety": SAFETY,
    }
    assert all(result["integrity"][k] for k in (
        "patternPopulationExact2155", "t0RowsExact2155",
        "signalExactJoinComplete", "stateAsOfJoinComplete",
    ))
    assert result["integrity"]["futureBarViolations"] == 0
    assert all(v is False for v in SAFETY.values())
    return result


def self_test():
    assert active_elapsed(689, 690) == 1
    assert active_elapsed(690, 750) == 0
    assert active_elapsed(750, 755) == 5
    assert pct(1, 4) == 25.0
    assert pct(0, 0) is None
    print(json.dumps({"status": "PASS", "tests": 5}, sort_keys=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.output:
        raise SystemExit("--output required")
    result = run()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "population": result["cohort"]["population"],
        "decisionRows": result["patternSubstrate"]["decisionRows"],
        "features": result["patternSubstrate"]["featureColumns"],
        "signalJoinPct": result["sixSignals"]["exactJoinCoveragePct"],
        "stateAsOfJoinPct": result["stateV3"]["asOfJoinCoveragePct"],
        "performanceMetricsRead": 0,
        "modelFits": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
