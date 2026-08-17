from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

JST = timezone(timedelta(hours=9))
SAFETY = {
    "phase": "58.p8.dataset-quality",
    "mode": "MARKETSPEED_II_RSS_READ_ONLY",
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


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _parse_iso(value: str) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError("capturedAt must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _time_seconds(value: Any) -> int | None:
    text = str(value or "").strip()
    parts = text.split(":")
    if len(parts) != 3:
        return None
    try:
        hh, mm = int(parts[0]), int(parts[1])
        sec = float(parts[2])
    except ValueError:
        return None
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= sec < 60):
        return None
    return int(hh * 3600 + mm * 60 + sec)


def _market_signature(row: dict[str, Any]) -> str:
    market = row.get("market") or {}
    keys = ["bestAsk", "bestBid", "bestAskSize", "bestBidSize"]
    keys += [f"askSize{i}" for i in range(1, 11)] + [f"bidSize{i}" for i in range(1, 11)]
    payload = {k: market.get(k) for k in keys}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _quote_signature(row: dict[str, Any]) -> str:
    market = row.get("market") or {}
    payload = {k: market.get(k) for k in ("bestAsk", "bestBid", "bestAskSize", "bestBidSize")}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _tick_signature(row: dict[str, Any]) -> str:
    ticks = row.get("ticks") or []
    payload = [(t.get("time"), t.get("price"), t.get("volume")) for t in ticks]
    return json.dumps(payload, separators=(",", ":"))


def validate(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    rows: list[dict[str, Any]] = []
    malformed = 0
    for line in raw.decode("utf-8", errors="strict").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(payload, dict):
            rows.append(payload)
        else:
            malformed += 1

    blockers: list[str] = []
    warnings: list[str] = []
    if malformed:
        blockers.append("MALFORMED_JSONL_ROWS")
    if len(rows) < 100:
        blockers.append("INSUFFICIENT_CAPTURE_ROWS")

    captured: list[datetime] = []
    invalid_capture_ts = 0
    source_mismatch = 0
    safety_violation = 0
    crossed = 0
    missing_quote = 0
    missing_depth = 0
    tick_order_mismatch = 0
    tick_session_mismatch_rows = 0
    tick_empty_rows = 0
    stale_tick_rows = 0
    newest_tick_ages: list[float] = []

    for row in rows:
        try:
            cap = _parse_iso(row.get("capturedAt", ""))
            captured.append(cap)
        except Exception:
            invalid_capture_ts += 1
            continue

        if row.get("sourceMode") != "MARKETSPEED_II_RSS_READ_ONLY":
            source_mismatch += 1
        safety = row.get("safety") or {}
        forbidden_true = [
            "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
            "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
            "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted",
        ]
        if any(bool(safety.get(k)) for k in forbidden_true):
            safety_violation += 1

        market = row.get("market") or {}
        bid, ask = market.get("bestBid"), market.get("bestAsk")
        if not (_finite(bid) and _finite(ask) and float(bid) > 0 and float(ask) > 0):
            missing_quote += 1
        elif float(ask) < float(bid):
            crossed += 1

        depth_ok = all(
            _finite(market.get(f"ask{i}")) and _finite(market.get(f"bid{i}"))
            and _finite(market.get(f"askSize{i}")) and _finite(market.get(f"bidSize{i}"))
            for i in range(1, 11)
        )
        if not depth_ok:
            missing_depth += 1

        ticks = row.get("ticks") or []
        if not ticks:
            tick_empty_rows += 1
            continue
        if row.get("tickOrder") != "DESC":
            tick_order_mismatch += 1

        times = [_time_seconds(t.get("time")) for t in ticks]
        valid_times = [t for t in times if t is not None]
        if len(valid_times) != len(ticks):
            tick_order_mismatch += 1
        elif any(valid_times[i] < valid_times[i + 1] for i in range(len(valid_times) - 1)):
            tick_order_mismatch += 1

        local = cap.astimezone(JST)
        capture_sec = local.hour * 3600 + local.minute * 60 + local.second
        newest = valid_times[0] if valid_times else None
        if newest is not None:
            # During the active daytime session, a newest tick materially later than capturedAt
            # cannot belong to the same session because RssTickList exposes time-of-day only.
            if 9 * 3600 <= capture_sec <= 15 * 3600 + 30 * 60 and newest > capture_sec + 5:
                tick_session_mismatch_rows += 1
            else:
                age = capture_sec - newest
                if age < 0:
                    age += 24 * 3600
                newest_tick_ages.append(float(age))
                if age > 30:
                    stale_tick_rows += 1

    if invalid_capture_ts:
        blockers.append("INVALID_CAPTURE_TIMESTAMPS")
    if source_mismatch:
        blockers.append("NON_RSS_READ_ONLY_SOURCE_ROWS")
    if safety_violation:
        blockers.append("SAFETY_FLAG_VIOLATION")
    if crossed:
        blockers.append("CROSSED_QUOTES")
    if missing_quote:
        blockers.append("MISSING_BEST_QUOTES")
    if missing_depth:
        blockers.append("INCOMPLETE_10_LEVEL_DEPTH")
    if tick_empty_rows:
        blockers.append("EMPTY_TICK_WINDOWS")
    if tick_order_mismatch:
        blockers.append("TICK_ORDER_OR_TIME_FORMAT_MISMATCH")
    if tick_session_mismatch_rows:
        blockers.append("TICK_SESSION_MISMATCH_OR_STALE_PREVIOUS_SESSION_WINDOW")

    intervals: list[float] = []
    if len(captured) >= 2:
        for a, b in zip(captured, captured[1:]):
            intervals.append((b - a).total_seconds())
        if any(x <= 0 for x in intervals):
            blockers.append("NON_MONOTONIC_CAPTURE_TIMESTAMPS")

    market_sigs = [_market_signature(r) for r in rows]
    quote_sigs = [_quote_signature(r) for r in rows]
    tick_sigs = [_tick_signature(r) for r in rows]
    market_changes = sum(a != b for a, b in zip(market_sigs, market_sigs[1:]))
    quote_changes = sum(a != b for a, b in zip(quote_sigs, quote_sigs[1:]))
    tick_changes = sum(a != b for a, b in zip(tick_sigs, tick_sigs[1:]))
    transitions = max(0, len(rows) - 1)

    unique_market = len(set(market_sigs)) if market_sigs else 0
    unique_ticks = len(set(tick_sigs)) if tick_sigs else 0
    duplicate_market_ratio = 1 - (unique_market / len(market_sigs)) if market_sigs else 1.0

    if transitions and market_changes == 0:
        blockers.append("STATIC_MARKET_CAPTURE")
    if transitions and market_changes / transitions < 0.10:
        warnings.append("LOW_MARKET_CHANGE_RATE")
    if transitions and tick_changes == 0:
        warnings.append("STATIC_TICK_WINDOW")
    if stale_tick_rows:
        warnings.append("STALE_NEWEST_TICK_ROWS")

    status = "PHASE58_DATASET_QUALITY_READY" if not blockers else "PHASE58_DATASET_QUALITY_BLOCKED"
    return {
        "phase": "58.p8.dataset-quality",
        "status": status,
        "complete": not blockers,
        "path": str(path),
        "sha256": sha256,
        "rowCount": len(rows),
        "malformedRows": malformed,
        "capture": {
            "start": captured[0].isoformat() if captured else None,
            "end": captured[-1].isoformat() if captured else None,
            "durationSeconds": (captured[-1] - captured[0]).total_seconds() if len(captured) >= 2 else 0,
            "intervalMeanSeconds": mean(intervals) if intervals else None,
            "intervalMedianSeconds": median(intervals) if intervals else None,
            "intervalMinSeconds": min(intervals) if intervals else None,
            "intervalMaxSeconds": max(intervals) if intervals else None,
        },
        "market": {
            "uniqueSnapshots": unique_market,
            "duplicateSnapshotRatio": duplicate_market_ratio,
            "marketChangeTransitions": market_changes,
            "marketChangeRate": market_changes / transitions if transitions else 0,
            "topQuoteChangeTransitions": quote_changes,
            "topQuoteChangeRate": quote_changes / transitions if transitions else 0,
            "crossedQuoteRows": crossed,
            "missingQuoteRows": missing_quote,
            "incompleteDepthRows": missing_depth,
        },
        "ticks": {
            "uniqueWindows": unique_ticks,
            "tickWindowChangeTransitions": tick_changes,
            "tickWindowChangeRate": tick_changes / transitions if transitions else 0,
            "emptyTickRows": tick_empty_rows,
            "tickOrderMismatchRows": tick_order_mismatch,
            "tickSessionMismatchRows": tick_session_mismatch_rows,
            "staleNewestTickRows": stale_tick_rows,
            "newestTickAgeMedianSeconds": median(newest_tick_ages) if newest_tick_ages else None,
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "safety": SAFETY,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate byte-pinned Phase58 MARKETSPEED II RSS JSONL data fail-closed.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    result = validate(args.path)
    if args.expected_sha256 and result["sha256"] != args.expected_sha256:
        result["blockers"] = sorted(set([*result["blockers"], "DATASET_SHA256_MISMATCH"]))
        result["status"] = "PHASE58_DATASET_QUALITY_BLOCKED"
        result["complete"] = False

    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
