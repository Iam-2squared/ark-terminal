from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any

from tools.phase57_intraday_capture import PHASE57_CAPTURE_SAFETY
from tools.phase57_intraday_capture_health import assess_capture_health

PHASE57_P16_P18_SAFETY = {
    **PHASE57_CAPTURE_SAFETY,
    "mode": "PHASE57_P16_P18_REAL_INTRADAY_RESEARCH_READ_ONLY",
}


def _parse_ts(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load(root: str | Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    base = Path(root)
    if not base.exists():
        return out
    for path in sorted(base.glob("*/*.jsonl")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("sourceMode") == "MARKETSPEED_II_RSS_READ_ONLY":
                out.append(row)
    return out


def build_real_capture_manifest(root: str | Path = "data/intraday") -> dict[str, Any]:
    """P16: audit actual captured sessions/symbols/coverage without inventing data."""
    rows = _load(root)
    sessions: dict[str, dict[str, Any]] = {}
    fields = ("bid", "ask", "bidSize", "askSize", "depthBid", "depthAsk", "aggressiveBuyCount", "aggressiveSellCount", "tradeCount")
    for row in rows:
        ts = _parse_ts(row.get("capturedAt"))
        if ts is None:
            continue
        session = ts.date().isoformat()
        symbol = str(row.get("symbol") or "UNKNOWN")
        key = f"{session}:{symbol}"
        item = sessions.setdefault(key, {"sessionDate": session, "symbol": symbol, "rows": 0, "first": ts, "last": ts, "fieldPresent": defaultdict(int)})
        item["rows"] += 1
        item["first"] = min(item["first"], ts)
        item["last"] = max(item["last"], ts)
        for field in fields:
            if row.get(field) not in (None, ""):
                item["fieldPresent"][field] += 1

    normalized = []
    for item in sessions.values():
        n = item["rows"] or 1
        normalized.append({
            "sessionDate": item["sessionDate"],
            "symbol": item["symbol"],
            "rows": item["rows"],
            "firstCapturedAt": item["first"].isoformat(),
            "lastCapturedAt": item["last"].isoformat(),
            "coverage": {field: item["fieldPresent"][field] / n for field in fields},
        })
    normalized.sort(key=lambda x: (x["sessionDate"], x["symbol"]))
    unique_sessions = sorted({x["sessionDate"] for x in normalized})
    unique_symbols = sorted({x["symbol"] for x in normalized})
    return {
        "phase": "57.p16",
        "status": "REAL_CAPTURE_AUDIT_READY" if rows else "REAL_CAPTURE_AUDIT_EMPTY",
        "rowCount": len(rows),
        "sessionCount": len(unique_sessions),
        "symbolCount": len(unique_symbols),
        "sessions": unique_sessions,
        "symbols": unique_symbols,
        "partitions": normalized,
        "syntheticDataUsed": False,
        "edgeClaimAllowed": False,
        **{k: False for k in ("executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed")},
        "safety": PHASE57_P16_P18_SAFETY,
    }


def build_read_only_capture_schedule_plan(*, interval_seconds: int = 5, session_minutes: int = 330, max_ticks_per_session: int | None = None) -> dict[str, Any]:
    """P17: produce a finite capture plan. This does not start a daemon or write to Excel."""
    interval = max(1, int(interval_seconds))
    natural = max(1, (max(1, int(session_minutes)) * 60) // interval)
    ticks = min(natural, int(max_ticks_per_session)) if max_ticks_per_session is not None else natural
    return {
        "phase": "57.p17",
        "status": "READ_ONLY_CAPTURE_SCHEDULE_PLANNED",
        "intervalSeconds": interval,
        "sessionMinutes": int(session_minutes),
        "maxTicksPerSession": ticks,
        "embeddedInfiniteLoop": False,
        "externalSchedulerRequired": True,
        "writesExcel": False,
        "invokesRssOrderFunctions": False,
        **{k: False for k in ("executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed")},
        "safety": PHASE57_P16_P18_SAFETY,
    }


def _num(row: dict[str, Any], key: str) -> float | None:
    try:
        value = row.get(key)
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def build_real_intraday_dataset(
    root: str | Path = "data/intraday",
    *,
    horizon_seconds: int = 60,
    barrier_bps: float = 20.0,
    require_healthy: bool = True,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """P18: build point-in-time feature rows plus event-barrier labels from real capture only.

    Features use the current snapshot only. Future snapshots are consulted solely for label/outcomeAt.
    Ambiguous same-snapshot barrier hits and timeouts are not forced into a label.
    """
    rows = _load(root)
    health = assess_capture_health(root, as_of=as_of) if require_healthy else None
    if require_healthy and health and health.get("status") != "INTRADAY_CAPTURE_HEALTHY":
        return {
            "phase": "57.p18", "status": "REAL_INTRADAY_DATASET_BLOCKED_BY_HEALTH", "rowCount": 0,
            "health": health, "rows": [], "syntheticDataUsed": False, "edgeClaimAllowed": False,
            **{k: False for k in ("executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed")},
            "safety": PHASE57_P16_P18_SAFETY,
        }

    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        ts = _parse_ts(row.get("capturedAt"))
        last = _num(row, "last")
        if ts is None or last is None or last <= 0:
            continue
        x = dict(row)
        x["_ts"] = ts
        by_symbol[str(row.get("symbol") or "UNKNOWN")].append(x)

    dataset: list[dict[str, Any]] = []
    horizon = timedelta(seconds=max(1, int(horizon_seconds)))
    barrier = max(0.1, float(barrier_bps)) / 10000.0

    for symbol, items in by_symbol.items():
        items.sort(key=lambda r: r["_ts"])
        for i, current in enumerate(items):
            t0 = current["_ts"]
            p0 = _num(current, "last")
            if p0 is None:
                continue
            future = [r for r in items[i + 1:] if t0 < r["_ts"] <= t0 + horizon]
            if not future:
                continue
            label = None
            outcome_at = None
            upper, lower = p0 * (1 + barrier), p0 * (1 - barrier)
            for f in future:
                p = _num(f, "last")
                if p is None:
                    continue
                if p >= upper:
                    label, outcome_at = 1, f["_ts"]
                    break
                if p <= lower:
                    label, outcome_at = 0, f["_ts"]
                    break
            if label is None:
                continue

            bid, ask = _num(current, "bid"), _num(current, "ask")
            bid_size, ask_size = _num(current, "bidSize"), _num(current, "askSize")
            depth_bid, depth_ask = _num(current, "depthBid"), _num(current, "depthAsk")
            ab, ass = _num(current, "aggressiveBuyCount"), _num(current, "aggressiveSellCount")
            spread_bps = ((ask - bid) / p0 * 10000.0) if bid is not None and ask is not None else None
            book_imb = ((bid_size - ask_size) / (bid_size + ask_size)) if bid_size is not None and ask_size is not None and (bid_size + ask_size) else None
            depth_imb = ((depth_bid - depth_ask) / (depth_bid + depth_ask)) if depth_bid is not None and depth_ask is not None and (depth_bid + depth_ask) else None
            aggr_buy_ratio = (ab / (ab + ass)) if ab is not None and ass is not None and (ab + ass) else None
            dataset.append({
                "symbol": symbol,
                "sessionDate": t0.date().isoformat(),
                "featureCutoff": t0.isoformat(),
                "outcomeAt": outcome_at.isoformat() if outcome_at else None,
                "pointInTimeValid": bool(outcome_at and t0 < outcome_at),
                "label": label,
                "barrierBps": barrier_bps,
                "horizonSeconds": horizon_seconds,
                "features": {
                    "last": p0,
                    "returnFromOpen": ((p0 / _num(current, "open")) - 1) if _num(current, "open") not in (None, 0) else None,
                    "spreadBps": spread_bps,
                    "bookImbalance": book_imb,
                    "depthImbalance": depth_imb,
                    "aggressiveBuyRatio": aggr_buy_ratio,
                    "tradeCount": _num(current, "tradeCount"),
                    "volume": _num(current, "volume"),
                },
                "sourceMode": "MARKETSPEED_II_RSS_READ_ONLY",
            })

    durations = [(_parse_ts(r["outcomeAt"]) - _parse_ts(r["featureCutoff"])).total_seconds() for r in dataset if _parse_ts(r["outcomeAt"]) and _parse_ts(r["featureCutoff"])]
    return {
        "phase": "57.p18",
        "status": "REAL_INTRADAY_DATASET_READY" if dataset else "REAL_INTRADAY_DATASET_EMPTY",
        "rowCount": len(dataset),
        "symbolCount": len({r["symbol"] for r in dataset}),
        "sessionCount": len({r["sessionDate"] for r in dataset}),
        "medianOutcomeSeconds": median(durations) if durations else None,
        "rows": dataset,
        "syntheticDataUsed": False,
        "futureUsedForFeatures": False,
        "futureUsedOnlyForLabels": True,
        "edgeClaimAllowed": False,
        **{k: False for k in ("executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed")},
        "safety": PHASE57_P16_P18_SAFETY,
    }
