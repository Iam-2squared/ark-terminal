"""R25 finite NEW EXIT dataset/cache builder; no estimator fit or candidate score.

Consumes the frozen R20 observation substrate and pinned Development raw paths.
Future prices are projected only into training-label fields; decision feature
payloads are strict allowlists.  Pattern features, when requested, are
recomputed from the closed NOW prefix with the already-frozen Pattern-v2
producer.  No protected partition, provider request, policy replay or winner
selection occurs here.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from scripts import phase57_exit_checkpoints_v1 as r20
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_exit_feature_contract_v1 as features
from scripts import phase57_exit_fit_contract_r33 as r33
from scripts import phase57_exit_research_protocol_v1 as r25
from scripts import phase57_chart_entry as chart_entry

ROOT = Path(__file__).resolve().parents[1]
RAW_PATHS = ROOT / "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz"
PATTERN_OPPORTUNITIES = ROOT / "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/opportunities.json.gz"
RAW_PATHS_SHA256 = "37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b"
PATTERN_OPPORTUNITIES_SHA256 = "1138960e489c3403e49f502a7ff7ab1fa1e9ef205910d2d018f2bb938df813ea"
HEADS = ("hold5", "hold15", "holdTerminal")
SIGNALS = r33.SIGNALS

SAFETY = dict.fromkeys((
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
    "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted"), False)


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def exact_open(rows, minute: int):
    exact = [r for r in rows if len(r) == 7 and r[0] == minute]
    require(len(exact) <= 1, "DUPLICATE_EXACT_REFERENCE")
    if not exact:
        return None
    value = exact[0][1]
    return float(value) if execution.finite_price(value) else None


def label_references(day: str, now: int, today_rows) -> dict:
    """Training-label references only, never decision features."""
    now_ref = execution.ordinary_execution_reference(day, now, today_rows)
    exit_price = now_ref["price"] if now_ref["status"] == "RESOLVED_NEXT_SCHEDULED_OPEN" else None
    starts = list(execution.continuous_minutes(day))
    start = now_ref["referenceStart"]
    result = {"exitNow": exit_price, "hold5": None, "hold15": None, "holdTerminal": None}
    if exit_price is None or start is None:
        return result
    require(start in starts, "EXIT_START_NOT_SCHEDULED")
    index = starts.index(start)
    for name, horizon in (("hold5", 5), ("hold15", 15)):
        target = index + horizon
        if target < len(starts):
            result[name] = exact_open(today_rows, starts[target])
    terminal = execution.terminal_execution_reference(today_rows)
    if terminal["status"] == "RESOLVED_TERMINAL_AUCTION":
        result["holdTerminal"] = terminal["price"]
    return result


def labels_from_references(refs: dict) -> dict:
    base = refs["exitNow"]
    out = {}
    for name in HEADS:
        target = refs[name]
        out[name] = (100.0 * (target / base - 1.0)
                     if execution.finite_price(base) and execution.finite_price(target)
                     else None)
    return out


def _cat(value) -> str:
    if value is None:
        return "UNKNOWN"
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    if isinstance(value, (list, tuple, dict)):
        return canonical(value)
    return str(value)


def _num(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None


def core_features(row: dict) -> tuple[dict, dict]:
    """Exact R33 CORE projection. Extra checkpoint/evaluator fields are ignored."""
    entry_state = row.get("entryState") or {}
    current_state = (row.get("recognition") or {}).get("state") or {}
    recognition_signals = (row.get("recognition") or {}).get("signals") or {}
    history = row.get("history") or {}
    position = row.get("position") or {}

    cats = {
        "entryState.state": _cat(entry_state.get("state")),
        "entryState.dataQuality": _cat(entry_state.get("dataQuality")),
        "entryState.confidence": _cat(entry_state.get("confidence")),
        "currentState.state": _cat(current_state.get("state")),
        "currentState.dataQuality": _cat(current_state.get("dataQuality")),
        "currentState.confidence": _cat(current_state.get("confidence")),
        "entryToCurrentState": _cat(row.get("entryToCurrentState")),
        "entryState.reasonCodesSorted": _cat(sorted(entry_state.get("reasonCodes") or [])),
        "currentState.reasonCodesSorted": _cat(sorted(current_state.get("reasonCodes") or [])),
    }
    disappeared = history.get("bullishStateDisappeared") or {}
    for signal in SIGNALS:
        state = (recognition_signals.get(signal) or {}).get("state")
        cats[f"signal.{signal}.currentTriState"] = _cat(state)
        cats[f"signal.{signal}.observedTrueToFalseTriState"] = _cat(disappeared.get(signal))

    nums = {"stateDwellObservedActiveMinutes": _num(row.get("stateDwellObservedActiveMinutes"))}
    for window in (3, 5, 10):
        h = history.get(str(window)) or {}
        for key in ("stateChanges", "stateKnown", "stateKnownAdjacentPairs"):
            nums[f"history.{window}.{key}"] = _num(h.get(key))
        sh = h.get("signals") or {}
        for signal in SIGNALS:
            counts = sh.get(signal) or {}
            for key in ("true", "false", "unknown"):
                nums[f"history.{window}.signal.{signal}.{key}"] = _num(counts.get(key))
    nums["history.stateRunObservedSamplesCapped10"] = _num(history.get("stateRunObservedSamplesCapped10"))
    for key in (
        "clockMinutesHeld", "activeMinutesHeld", "observedOwnedBars", "missingOwnedBars",
        "fullOwnedPrefix", "freshClosedPrice", "lastObservedClose", "lastObservedClosedAt",
        "currentReturnPct", "observedRunningHigh", "observedRunningLow", "observedMfePct",
        "observedMaePct", "completePrefixMfePct", "completePrefixMaePct",
        "observedPeakGivebackPp", "peakConfirmedAt", "activeMinutesSincePeakConfirmation",
    ):
        nums[f"position.{key}"] = _num(position.get(key))

    expected_cat = set(r33.contract()["coreEncoding"]["categorical"])
    expected_num = set(r33.contract()["coreEncoding"]["numeric"])
    require(set(cats) == expected_cat, "R33_CORE_CATEGORICAL_DRIFT")
    require(set(nums) == expected_num, "R33_CORE_NUMERIC_DRIFT")
    return cats, nums


def selector_origins(allowed: set[str]) -> dict:
    require(sha(PATTERN_OPPORTUNITIES) == PATTERN_OPPORTUNITIES_SHA256,
            "PATTERN_OPPORTUNITIES_SHA")
    out = {}
    for row in read(PATTERN_OPPORTUNITIES):
        oid = row["id"]
        if oid not in allowed:
            continue
        origin = row["origin"]
        minute = chart_entry.minute(origin["decisionTimestamp"])
        out[oid] = {
            "selectorMinute": int(minute),
            "origin": {key: origin[key] for key in
                       ("decisionPrice", "decisionTimestamp", "savedV1Score", "newEligibleRank")},
        }
    require(set(out) == allowed, "SELECTOR_ORIGIN_COHORT_MISMATCH")
    return out


def verify_r20(root: Path) -> dict:
    coverage = read(root / "coverage.json")
    require(coverage["populationPerEntry"] == 2155, "R20_POPULATION")
    require(coverage["modelFits"] == coverage["candidatePoliciesEvaluated"] == 0,
            "R20_NOT_OBSERVATION_ONLY")
    require(all(v is False for v in coverage["safety"].values()), "R20_SAFETY")
    manifest = read(root / "manifest.json")
    for rel, expected in manifest.items():
        path = root / rel
        require(path.is_file() and sha(path) == expected, "R20_MANIFEST:" + rel)
    return coverage


def checkpoint_rows(root: Path, session: str):
    path = root / "checkpoints" / f"{session}.jsonl.gz"
    require(path.is_file(), "R20_SESSION_MISSING:" + session)
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            require(row["entry"]["session"] == session, "R20_SESSION_ROW_MISMATCH")
            require(row["entryPolicy"] in r33.ARMS, "R20_ARM")
            require(row["inputMaxKnownAt"] is None or row["inputMaxKnownAt"] <= row["now"],
                    "R20_KNOWLEDGE_LEAK")
            yield row


def pattern_features(oid: str, row: dict, raw: dict, origin: dict) -> dict:
    day, now = row["entry"]["session"], int(row["now"])
    path = raw[oid]
    previous_day = path["previousSession"]
    previous = r20.closed_prefix(previous_day, 1440, path["previous"]) if previous_day else ()
    today = r20.closed_prefix(day, now, path["today"])
    result = features.pattern_now(
        day=day, now=now, selector_minute=origin["selectorMinute"],
        selector_origin=origin["origin"], today_prefix=today, previous_prefix=previous)
    curated = result["curated"]
    require(len(curated) == 187, "CURATED_PATTERN_NOT_187")
    return {key: _num(value) for key, value in curated.items()}


def build_session(r20_root: Path, session: str, raw: dict, origins: dict,
                  include_pattern: bool) -> list[dict]:
    rows = []
    for row in checkpoint_rows(r20_root, session):
        oid = row["entry"]["opportunity"]
        cats, nums = core_features(row)
        refs = label_references(session, int(row["now"]), raw[oid]["today"])
        record = {
            "schemaVersion": "phase57-r25-fit-row-v1",
            "session": session,
            "opportunity": oid,
            "entryArm": row["entryPolicy"],
            "now": int(row["now"]),
            "entryMinute": int(row["entry"]["entryMinute"]),
            "entryPrice": float(row["entry"]["price"]),
            "freshCurrentObservation": bool((row.get("position") or {}).get("freshClosedPrice")),
            "coreCategorical": cats,
            "coreNumeric": nums,
            "labels": labels_from_references(refs),
        }
        if include_pattern:
            record["curatedPatternNumeric"] = pattern_features(oid, row, raw, origins[oid])
        rows.append(record)
    rows.sort(key=lambda x: (x["entryArm"], x["opportunity"], x["now"]))
    require(len({(r["entryArm"], r["opportunity"], r["now"]) for r in rows}) == len(rows),
            "DUPLICATE_R25_ROW_ID")
    return rows


def write_gzip_jsonl(path: Path, rows: list[dict]) -> None:
    require(not path.exists(), "APPEND_ONLY_OUTPUT_EXISTS")
    with path.open("xb") as bf, gzip.GzipFile(fileobj=bf, filename="", mode="wb", mtime=0) as gz:
        for row in rows:
            gz.write((canonical(row) + "\n").encode())


def run(r20_root: Path, out: Path, sessions: list[str], include_pattern: bool) -> dict:
    contract = r33.contract()
    require(contract["exposureAtFreeze"]["modelFits"] == 0, "R33_ALREADY_FIT")
    verify_r20(r20_root)
    require(sha(RAW_PATHS) == RAW_PATHS_SHA256, "RAW_PATHS_SHA")
    allowed = set(r25.development_sessions())
    require(set(sessions) <= allowed and sessions, "SESSION_SCOPE")
    raw = r20.read_allowlisted_paths(RAW_PATHS, allowed)
    origins = selector_origins(allowed) if include_pattern else {}
    out.mkdir(parents=True, exist_ok=False)
    counts = {arm: 0 for arm in r33.ARMS}
    label_counts = {head: {"known": 0, "missing": 0} for head in HEADS}
    files = {}
    for session in sessions:
        rows = build_session(r20_root, session, raw, origins, include_pattern)
        path = out / f"{session}.jsonl.gz"
        write_gzip_jsonl(path, rows)
        files[path.name] = sha(path)
        for row in rows:
            counts[row["entryArm"]] += 1
            for head, value in row["labels"].items():
                label_counts[head]["known" if value is not None else "missing"] += 1
        print(canonical({"session": session, "rows": len(rows), "includePattern": include_pattern}), flush=True)
    receipt = {
        "schemaVersion": "phase57-r25-dataset-cache-receipt-v1",
        "status": "DATASET_CACHE_ONLY_NO_MODEL_FIT_NO_POLICY_PERFORMANCE",
        "sessions": sessions,
        "includePattern": include_pattern,
        "rowsByArm": counts,
        "labelAvailability": label_counts,
        "files": files,
        "r20Source": r33.R20,
        "rawPathsSHA256": RAW_PATHS_SHA256,
        "modelFits": 0,
        "candidatePoliciesEvaluated": 0,
        "candidatePerformanceInspected": False,
        "providerRequests": 0,
        "protectedPartitionsOpened": 0,
        "safety": SAFETY,
    }
    (out / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    return receipt


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--r20-root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--sessions", default="")
    p.add_argument("--include-pattern", action="store_true")
    args = p.parse_args()
    sessions = [x for x in args.sessions.split(",") if x] or r25.development_sessions()
    print(canonical(run(args.r20_root, args.out, sessions, args.include_pattern)))


if __name__ == "__main__":
    main()
