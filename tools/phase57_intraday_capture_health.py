from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.phase57_intraday_capture import PHASE57_CAPTURE_SAFETY

PHASE57_P14_SAFETY = {
    **PHASE57_CAPTURE_SAFETY,
    "mode": "PHASE57_INTRADAY_CAPTURE_HEALTH_READ_ONLY",
}


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_records(root: str | Path) -> list[dict[str, Any]]:
    root_path = Path(root)
    records: list[dict[str, Any]] = []
    if not root_path.exists():
        return records
    for path in sorted(root_path.glob("*/*.jsonl")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("sourceMode") == "MARKETSPEED_II_RSS_READ_ONLY":
                records.append(payload)
    return records


def assess_capture_health(
    root: str | Path = "data/intraday",
    *,
    as_of: datetime | None = None,
    expected_interval_seconds: int = 5,
    stale_after_seconds: int = 30,
    max_gap_multiplier: float = 3.0,
) -> dict[str, Any]:
    now = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    records = _load_records(root)
    by_symbol: dict[str, list[datetime]] = {}
    invalid_timestamp_rows = 0
    for record in records:
        ts = _parse_ts(record.get("capturedAt"))
        if ts is None:
            invalid_timestamp_rows += 1
            continue
        symbol = str(record.get("symbol") or "UNKNOWN")
        by_symbol.setdefault(symbol, []).append(ts)

    symbol_health: dict[str, Any] = {}
    stale_symbols: list[str] = []
    gapped_symbols: list[str] = []
    max_allowed_gap = expected_interval_seconds * max_gap_multiplier

    for symbol, timestamps in sorted(by_symbol.items()):
        ordered = sorted(set(timestamps))
        gaps = [
            (ordered[i] - ordered[i - 1]).total_seconds()
            for i in range(1, len(ordered))
        ]
        large_gaps = [gap for gap in gaps if gap > max_allowed_gap]
        latest = ordered[-1]
        age_seconds = max(0.0, (now - latest).total_seconds())
        stale = age_seconds > stale_after_seconds
        gapped = bool(large_gaps)
        if stale:
            stale_symbols.append(symbol)
        if gapped:
            gapped_symbols.append(symbol)
        symbol_health[symbol] = {
            "samples": len(ordered),
            "latestCapturedAt": latest.isoformat(),
            "ageSeconds": age_seconds,
            "stale": stale,
            "gapCount": len(large_gaps),
            "largestGapSeconds": max(gaps) if gaps else 0.0,
            "gapped": gapped,
        }

    blockers: list[str] = []
    if not records:
        blockers.append("NO_INTRADAY_CAPTURE_DATA")
    if stale_symbols:
        blockers.append("STALE_INTRADAY_CAPTURE")
    if gapped_symbols:
        blockers.append("INTRADAY_CAPTURE_GAPS_DETECTED")
    if invalid_timestamp_rows:
        blockers.append("INVALID_CAPTURE_TIMESTAMPS")

    return {
        "phase": "57.p14",
        "status": "INTRADAY_CAPTURE_HEALTHY" if not blockers else "INTRADAY_CAPTURE_HEALTH_BLOCKED",
        "recordCount": len(records),
        "symbolCount": len(by_symbol),
        "staleSymbols": stale_symbols,
        "gappedSymbols": gapped_symbols,
        "invalidTimestampRows": invalid_timestamp_rows,
        "config": {
            "expectedIntervalSeconds": expected_interval_seconds,
            "staleAfterSeconds": stale_after_seconds,
            "maxGapMultiplier": max_gap_multiplier,
            "maxAllowedGapSeconds": max_allowed_gap,
        },
        "symbols": symbol_health,
        "blockers": blockers,
        "nextStep": "CONTINUE_READ_ONLY_INTRADAY_CAPTURE" if blockers else "CONTINUE_DATA_SUFFICIENCY_ACCUMULATION",
        "edgeClaimAllowed": False,
        "executionAllowed": False,
        "brokerWriteAllowed": False,
        "excelOrderWriteAllowed": False,
        "rssOrderFunctionAllowed": False,
        "liveTradingAllowed": False,
        "paperTradingAllowed": False,
        "automaticPromotionAllowed": False,
        "productionUpdateAllowed": False,
        "safety": PHASE57_P14_SAFETY,
    }
