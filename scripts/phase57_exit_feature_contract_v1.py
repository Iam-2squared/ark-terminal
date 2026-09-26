"""R23 EXIT-NOW feature admission contract; no model fit or outcome access.

Pattern-v2's canonical producer is reused only with a strict closed prefix.  The
30 prior-daily-dependent columns are deliberately emitted as None and removed
from the decision payload until an exact prior-daily lineage is separately
frozen.  This module never reads the evaluator path or an EXIT outcome.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAMES = ROOT / "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/names.json"
PATTERN_OPPORTUNITIES = ROOT / "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/opportunities.json.gz"
COHORT = ROOT / "docs/evidence/phase57-entry-timing-signal-census-v1/protocol.json"

PINS = {
    str(NAMES.relative_to(ROOT)): "efcbcaf4c4024679dc5f6e7881dcccc7c0186361b6bd469b7d3a5e6a5421e8eb",
    str(PATTERN_OPPORTUNITIES.relative_to(ROOT)): "1138960e489c3403e49f502a7ff7ab1fa1e9ef205910d2d018f2bb938df813ea",
    str(COHORT.relative_to(ROOT)): "6b02b3088dd8ea7f8ce53112bc276df442bae3ce0716b8139c92733be4de2994",
}

CURATED_FAMILIES = frozenset({
    "AVAIL", "CLOCK", "SEL", "TODAY", "PREV",
    "LOCAL1", "LOCAL3", "LOCAL5", "LOCAL10", "LOCAL15", "LOCAL30",
    "ACCEL1", "ACCEL3", "ACCEL5", "ACCEL10",
    "RVOL1", "RVOL3", "RVOL5", "RVOL10", "STRUCT", "SIGNAL",
})

STATE_FEATURES = (
    "entryState", "currentState", "entryToCurrentState",
    "stateDataQuality", "stateReason", "stateConfidence",
    "stateDwellObservedActiveMinutes", "stateChanges3", "stateChanges5",
    "stateChanges10", "stateKnown3", "stateKnown5", "stateKnown10",
)

SIGNAL_FAMILIES = (
    "CONTINUATION", "BREAKOUT", "COMPRESSION_EXPANSION",
    "HIGHER_LOW", "LOWER_WICK", "RECLAIM",
)

POSITION_FEATURES = (
    "clockMinutesHeld", "activeMinutesHeld", "observedOwnedBars",
    "missingOwnedBars", "fullOwnedPrefix", "freshClosedPrice",
    "lastObservedClose", "lastObservedClosedAt", "currentReturnPct",
    "observedRunningHigh", "observedRunningLow", "observedMfePct",
    "observedMaePct", "completePrefixMfePct", "completePrefixMaePct",
    "observedPeakGivebackPp", "peakConfirmedAt",
    "activeMinutesSincePeakConfirmation",
)

EVALUATOR_ONLY = (
    "orderedOpportunityLow", "orderedStrictlyLaterHigh",
    "postEntryBestHigh", "futureMFE", "futureMAE", "futureState",
    "futurePivot", "finalPnL", "oracleExit", "actualExitOutcome",
    "upmoveCaptureRatio", "highToExitEvaluatorGap",
    "ownedPeakToFinalExitGiveback",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def _blocked(name: str) -> bool:
    return name.startswith("RECENT/") or name.startswith(("SIGNAL/PDH", "SIGNAL/PDL"))


def pattern_rows() -> list[dict]:
    _require(_sha(NAMES) == PINS[str(NAMES.relative_to(ROOT))], "PATTERN_NAMES_SHA")
    names = _read(NAMES)
    _require(names == sorted(names) and len(names) == len(set(names)) == 476,
             "PATTERN_REGISTRY_NOT_EXACT_476")
    rows = []
    for name in names:
        family = name.split("/", 1)[0]
        blocked = _blocked(name)
        if blocked:
            status = "BLOCKED"
            source = "PRIOR_DAILY_CONTEXT_NOT_PINNED_FOR_EXIT_NOW"
            known_at = "UNPROVEN_FOR_EXACT_EXIT_NOW_JOIN"
        elif family == "SEL":
            status = "MODEL_ADMITTED"
            source = "FROZEN_SELECTOR_ORIGIN_ALLOWLIST"
            known_at = "SELECTOR_DECISION_AT_OR_BEFORE_ENTRY_AND_NOW"
        elif family in {"PREV", "RVOL1", "RVOL3", "RVOL5", "RVOL10"}:
            status = "MODEL_ADMITTED"
            source = "CANONICAL_PATTERN_V2_PREVIOUS_SESSION_PREFIX"
            known_at = "PREVIOUS_SESSION_END_BEFORE_CURRENT_SESSION"
        else:
            status = "MODEL_ADMITTED"
            source = "CANONICAL_PATTERN_V2_CLOSED_PREFIX"
            known_at = "BAR_END_PROXY_AND_INPUT_KNOWN_AT_NOT_AFTER_NOW"
        curated = status == "MODEL_ADMITTED" and family in CURATED_FAMILIES
        rows.append({
            "feature": name,
            "family": family,
            "producer": "scripts/phase57_entry_pattern_v2.py::features",
            "source": source,
            "knownAt": known_at,
            "closedBarRequired": family != "SEL",
            "futureSuffixDependency": False,
            "missingSemantics": "NULL_PLUS_EXPLICIT_AVAILABILITY_NEVER_IMPUTED_FROM_FUTURE",
            "status": status,
            "selectedInFiniteSearch": curated,
        })
    _require(Counter(r["status"] for r in rows) == {"MODEL_ADMITTED": 446, "BLOCKED": 30},
             "PATTERN_ADMISSION_COUNTS")
    _require(sum(r["selectedInFiniteSearch"] for r in rows) == 187,
             "CURATED_PATTERN_NOT_187")
    return rows


def selector_context_audit() -> dict:
    """Verify exact cohort join while projecting only the three frozen fields."""
    for path in (PATTERN_OPPORTUNITIES, COHORT):
        _require(_sha(path) == PINS[str(path.relative_to(ROOT))], "PIN_MISMATCH:" + str(path))
    cohort = _read(COHORT)["opportunityIds"]
    allowed = set(cohort)
    _require(len(cohort) == len(allowed) == 2155, "COHORT_NOT_2155")
    selected = {}
    for row in _read(PATTERN_OPPORTUNITIES):
        oid = row["id"]
        if oid not in allowed:
            continue
        origin = row["origin"]
        projected = {key: origin[key] for key in
                     ("decisionPrice", "decisionTimestamp", "savedV1Score", "newEligibleRank")}
        _require(all(isinstance(projected[k], (int, float)) and
                     not isinstance(projected[k], bool) and math.isfinite(projected[k])
                     for k in ("decisionPrice", "savedV1Score", "newEligibleRank")),
                 "SELECTOR_CONTEXT_VALUE:" + oid)
        selected[oid] = projected
    _require(set(selected) == allowed and len(selected) == 2155, "SELECTOR_CONTEXT_JOIN")
    encoded = json.dumps({k: selected[k] for k in sorted(selected)},
                         sort_keys=True, separators=(",", ":")).encode()
    return {
        "cohort": len(selected),
        "missing": 0,
        "projectedFields": ["decisionPrice", "decisionTimestamp", "savedV1Score", "newEligibleRank"],
        "sanitizedProjectionSHA256": hashlib.sha256(encoded).hexdigest(),
        "sourceRowsRead": 5375,
        "outcomeFieldsProjected": 0,
    }


def _rows(values) -> list[list[float]]:
    out = []
    for value in values:
        row = value.row() if hasattr(value, "row") else list(value)
        _require(len(row) == 7, "PATTERN_ROW_WIDTH")
        out.append(row)
    return out


def pattern_now(*, day: str, now: int, selector_minute: int, selector_origin: dict,
                today_prefix, previous_prefix) -> dict:
    """Recompute all canonical names, then expose only audited decision columns.

    Callers must pass the already closed R20 prefix.  Any future row is rejected,
    rather than sliced here.  Prior-daily inputs are intentionally absent.
    """
    import numpy as np
    from scripts.phase57_entry_pattern_v2 import features

    registry = [r["feature"] for r in pattern_rows()]
    today = _rows(today_prefix)
    previous = _rows(previous_prefix)
    _require(all(int(r[0]) == r[0] and r[0] + 1 <= now for r in today),
             "PATTERN_TODAY_NOT_CLOSED_AT_NOW")
    _require(all(int(r[0]) == r[0] for r in previous), "PATTERN_PREVIOUS_TIME")
    _require(isinstance(selector_minute, int) and selector_minute < now,
             "SELECTOR_MINUTE_NOT_PAST")
    for key in ("decisionPrice", "savedV1Score", "newEligibleRank"):
        _require(key in selector_origin, "SELECTOR_ORIGIN_MISSING:" + key)
    recent = {name.split("/", 1)[1]: None for name in registry if name.startswith("RECENT/")}
    values, quote = features(
        day, now, selector_minute, selector_origin,
        np.asarray(today, dtype=float).reshape(-1, 7),
        np.asarray(previous, dtype=float).reshape(-1, 7),
        None, recent,
    )
    _require(sorted(values) == registry, "PATTERN_PRODUCER_REGISTRY_DRIFT")
    admitted = {r["feature"] for r in pattern_rows() if r["status"] == "MODEL_ADMITTED"}
    curated = {r["feature"] for r in pattern_rows() if r["selectedInFiniteSearch"]}
    _require(all(values[name] is None for name in registry if _blocked(name)),
             "BLOCKED_PRIOR_DAILY_VALUE_LEAK")
    return {
        "quoteAvailable": bool(quote),
        "admitted": {name: values[name] for name in sorted(admitted)},
        "curated": {name: values[name] for name in sorted(curated)},
        "blocked": {name: None for name in registry if _blocked(name)},
    }


def contract() -> dict:
    rows = pattern_rows()
    return {
        "schemaVersion": "phase57-exit-feature-availability-causality-r23",
        "patternRegistry": {
            "columns": len(rows),
            "registrySHA256": PINS[str(NAMES.relative_to(ROOT))],
            "statusCounts": dict(sorted(Counter(r["status"] for r in rows).items())),
            "familyCounts": dict(sorted(Counter(r["family"] for r in rows).items())),
            "finiteSearchCuratedColumns": sum(r["selectedInFiniteSearch"] for r in rows),
            "rows": rows,
        },
        "stateV3": {
            "states": ["RISE", "SHARP_RISE", "REBOUND", "DROP", "PULLBACK",
                       "RANGE", "SHARP_DROP", "DROP_STOP", "RISE_STOP"],
            "features": list(STATE_FEATURES),
            "status": "MODEL_ADMITTED_WITH_QUALITY_AND_MISSINGNESS",
            "rule": "DROP_OR_NEGATIVE_RETURN_ALONE_MUST_NOT_FORCE_EXIT",
        },
        "timingSignals": {
            "families": list(SIGNAL_FAMILIES),
            "history": ["currentTriState", "trueFalseUnknownCounts3_5_10",
                        "observedTrueToFalse", "persistence", "agreement"],
            "status": "MODEL_ADMITTED_TRI_STATE_UNKNOWN_NOT_FALSE",
        },
        "entryToNow": {
            "features": list(POSITION_FEATURES),
            "status": "MODEL_ADMITTED_CAUSAL_OBSERVED_PREFIX",
            "rule": "INCOMPLETE_PATH_EXTREMA_REQUIRE_COMPLETENESS_FLAG",
        },
        "evaluatorOnly": [{"feature": name, "status": "EVALUATOR_ONLY"}
                          for name in EVALUATOR_ONLY],
        "selectorContext": selector_context_audit(),
        "modelInputSets": {
            "CORE": "R20_STATE_SIGNAL_ENTRY_TO_NOW_PLUS_QUALITY_MISSINGNESS",
            "CORE_PLUS_CURATED_PATTERN": "CORE_PLUS_EXACT_187_SELECTED_PATTERN_COLUMNS",
            "all476Forbidden": True,
        },
        "providerRequests": 0,
        "modelFits": 0,
        "candidatePoliciesEvaluated": 0,
    }


if __name__ == "__main__":
    print(json.dumps(contract(), sort_keys=True, separators=(",", ":")))
