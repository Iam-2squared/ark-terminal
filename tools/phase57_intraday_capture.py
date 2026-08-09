from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PHASE57_CAPTURE_SAFETY = {
    "mode": "PHASE57_INTRADAY_CAPTURE_READ_ONLY",
    "executionAllowed": False,
    "brokerWriteAllowed": False,
    "excelOrderWriteAllowed": False,
    "rssOrderFunctionAllowed": False,
    "liveTradingAllowed": False,
    "paperTradingAllowed": False,
    "automaticPromotionAllowed": False,
    "productionUpdateAllowed": False,
}

REQUIRED_COLUMNS = (
    "capturedAt", "symbol", "last", "open", "high", "low", "close", "volume",
    "bid", "ask", "bidSize", "askSize", "depthBid", "depthAsk",
    "aggressiveBuyCount", "aggressiveSellCount", "tradeCount",
)

@dataclass(frozen=True)
class IntradayCaptureRow:
    capturedAt: str
    symbol: str
    last: float | None
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    bid: float | None
    ask: float | None
    bidSize: float | None
    askSize: float | None
    depthBid: float | None
    depthAsk: float | None
    aggressiveBuyCount: float | None
    aggressiveSellCount: float | None
    tradeCount: float | None


def _num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_capture_row(raw: dict[str, Any]) -> IntradayCaptureRow:
    symbol = str(raw.get("symbol") or "").strip().upper()
    if symbol.isdigit():
        symbol = f"{symbol}.T"
    if not symbol:
        raise ValueError("symbol is required")
    captured_at = str(raw.get("capturedAt") or "").strip()
    if not captured_at:
        captured_at = datetime.now(timezone.utc).isoformat()
    return IntradayCaptureRow(
        capturedAt=captured_at,
        symbol=symbol,
        last=_num(raw.get("last")),
        open=_num(raw.get("open")),
        high=_num(raw.get("high")),
        low=_num(raw.get("low")),
        close=_num(raw.get("close")),
        volume=_num(raw.get("volume")),
        bid=_num(raw.get("bid")),
        ask=_num(raw.get("ask")),
        bidSize=_num(raw.get("bidSize")),
        askSize=_num(raw.get("askSize")),
        depthBid=_num(raw.get("depthBid")),
        depthAsk=_num(raw.get("depthAsk")),
        aggressiveBuyCount=_num(raw.get("aggressiveBuyCount")),
        aggressiveSellCount=_num(raw.get("aggressiveSellCount")),
        tradeCount=_num(raw.get("tradeCount")),
    )


def rows_from_matrix(matrix: Iterable[Iterable[Any]]) -> list[IntradayCaptureRow]:
    rows = [list(row) for row in matrix]
    if not rows:
        return []
    headers = [str(x or "").strip() for x in rows[0]]
    index = {name: i for i, name in enumerate(headers) if name}
    missing = [name for name in REQUIRED_COLUMNS if name not in index]
    if missing:
        raise ValueError(f"missing intraday columns: {','.join(missing)}")
    out: list[IntradayCaptureRow] = []
    for values in rows[1:]:
        if not any(v not in (None, "") for v in values):
            continue
        raw = {name: values[i] if i < len(values) else None for name, i in index.items()}
        out.append(normalize_capture_row(raw))
    return out


def append_jsonl(rows: Iterable[IntradayCaptureRow], root: str | Path = "data/intraday") -> list[Path]:
    root_path = Path(root)
    written: list[Path] = []
    grouped: dict[tuple[str, str], list[IntradayCaptureRow]] = {}
    for row in rows:
        session = row.capturedAt[:10]
        grouped.setdefault((session, row.symbol), []).append(row)
    for (session, symbol), items in grouped.items():
        safe_symbol = symbol.replace("/", "_")
        path = root_path / session / f"{safe_symbol}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for item in items:
                payload = {**asdict(item), "sourceMode": "MARKETSPEED_II_RSS_READ_ONLY", "safety": PHASE57_CAPTURE_SAFETY}
                f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
        written.append(path)
    return written


def capture_manifest(rows: Iterable[IntradayCaptureRow]) -> dict[str, Any]:
    items = list(rows)
    symbols = sorted({r.symbol for r in items})
    sessions = sorted({r.capturedAt[:10] for r in items})
    micro = [r for r in items if None not in (r.bid, r.ask, r.bidSize, r.askSize)]
    return {
        "phase": "57.p11",
        "status": "READ_ONLY_INTRADAY_CAPTURE_READY" if items else "NO_INTRADAY_ROWS",
        "rowCount": len(items),
        "symbols": symbols,
        "sessions": sessions,
        "microstructureCoverage": len(micro) / len(items) if items else 0.0,
        "executionAllowed": False,
        "brokerWriteAllowed": False,
        "excelOrderWriteAllowed": False,
        "rssOrderFunctionAllowed": False,
        "liveTradingAllowed": False,
        "paperTradingAllowed": False,
        "automaticPromotionAllowed": False,
        "productionUpdateAllowed": False,
        "safety": PHASE57_CAPTURE_SAFETY,
    }
