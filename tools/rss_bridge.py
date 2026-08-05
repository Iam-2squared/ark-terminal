from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

try:
    import pythoncom
    import win32com.client as win32_client
except ImportError:  # CI and non-Windows environments
    pythoncom = None
    win32_client = None

app = FastAPI(title="Ark Terminal RSS Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

READ_ONLY_SAFETY = {
    "mode": "read_only",
    "order_creation": False,
    "order_transmission": False,
    "order_cancellation": False,
}

# One symbol per row. Column A is the current price and B-I are optional RSS fields.
SYMBOL_CELLS: dict[str, str] = {
    "4755.T": "A1",
    "9432.T": "A2",
    "7203.T": "A3",
    "9984.T": "A4",
}
FIELD_COLUMNS = {
    "price": "A",
    "open": "B",
    "high": "C",
    "low": "D",
    "volume": "E",
    "bid": "F",
    "ask": "G",
    "previous_close": "H",
    "vwap": "I",
}

WATCHLIST: dict[str, dict[str, Any]] = {}
WATCHLIST_LOCK = Lock()


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    updated_at: str


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    price: float
    open: float | None
    high: float | None
    low: float | None
    volume: float | None
    bid: float | None
    ask: float | None
    previous_close: float | None
    vwap: float | None
    updated_at: str


def normalize_symbol(symbol: str) -> str:
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        raise ValueError("銘柄コードが必要です。")
    if "." not in normalized and normalized.isdigit():
        normalized = f"{normalized}.T"
    return normalized


def require_windows_com() -> None:
    if pythoncom is None or win32_client is None:
        raise RuntimeError("MARKETSPEED II RSS BridgeはWindows環境でのみ利用できます。")


def read_sheet_snapshot() -> tuple[Any, Any]:
    require_windows_com()
    pythoncom.CoInitialize()
    try:
        excel = win32_client.GetActiveObject("Excel.Application")
        workbook = excel.ActiveWorkbook
        if workbook is None:
            raise RuntimeError("Excelでブックが開かれていません。")
        return excel, workbook.Worksheets("Sheet1")
    except RuntimeError:
        pythoncom.CoUninitialize()
        raise
    except Exception as exc:
        pythoncom.CoUninitialize()
        raise RuntimeError("ExcelまたはMARKETSPEED II RSSに接続できません。") from exc


def release_com() -> None:
    if pythoncom is not None:
        pythoncom.CoUninitialize()


def _row_for_symbol(symbol: str) -> int:
    cell = SYMBOL_CELLS.get(symbol)
    if cell is None:
        raise KeyError(symbol)
    return int("".join(ch for ch in cell if ch.isdigit()))


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_market_snapshots(symbols: list[str]) -> list[MarketSnapshot]:
    normalized = [normalize_symbol(symbol) for symbol in symbols]
    unknown = [symbol for symbol in normalized if symbol not in SYMBOL_CELLS]
    if unknown:
        raise KeyError(",".join(unknown))

    _, sheet = read_sheet_snapshot()
    try:
        now = datetime.now(timezone.utc).isoformat()
        snapshots: list[MarketSnapshot] = []
        for symbol in normalized:
            row = _row_for_symbol(symbol)
            values = {
                field: _optional_float(sheet.Range(f"{column}{row}").Value)
                for field, column in FIELD_COLUMNS.items()
            }
            if values["price"] is None:
                continue
            snapshots.append(MarketSnapshot(symbol=symbol, updated_at=now, **values))
        return snapshots
    finally:
        release_com()


def read_price_from_excel(symbol: str) -> float:
    snapshots = read_market_snapshots([symbol])
    if not snapshots:
        raise RuntimeError("価格を取得できません。")
    return snapshots[0].price


def read_quotes(symbols: list[str]) -> list[Quote]:
    return [Quote(item.symbol, item.price, item.updated_at) for item in read_market_snapshots(symbols)]


def quote_payload(quote: Quote) -> dict[str, Any]:
    return {
        "symbol": quote.symbol,
        "price": quote.price,
        "updated_at": quote.updated_at,
        "source": "MARKETSPEED II RSS",
        "read_only": True,
        "order_transmission": False,
    }


def snapshot_payload(snapshot: MarketSnapshot) -> dict[str, Any]:
    payload = asdict(snapshot)
    payload.update({"source": "MARKETSPEED II RSS", **READ_ONLY_SAFETY})
    if snapshot.previous_close:
        payload["change"] = snapshot.price - snapshot.previous_close
        payload["change_percent"] = (snapshot.price / snapshot.previous_close - 1) * 100
    else:
        payload["change"] = None
        payload["change_percent"] = None
    payload["spread"] = (
        snapshot.ask - snapshot.bid
        if snapshot.ask is not None and snapshot.bid is not None
        else None
    )
    return payload


def realtime_ai_payload(snapshot: MarketSnapshot) -> dict[str, Any]:
    score = 50
    reasons: list[str] = []
    risks: list[str] = []
    change_percent = None
    if snapshot.previous_close:
        change_percent = (snapshot.price / snapshot.previous_close - 1) * 100
        score += max(-20, min(20, round(change_percent * 4)))
        reasons.append(f"前日比 {change_percent:+.2f}%")
    if snapshot.vwap:
        if snapshot.price >= snapshot.vwap:
            score += 8
            reasons.append("現在値がVWAP以上")
        else:
            score -= 8
            risks.append("現在値がVWAP未満")
    if snapshot.bid is not None and snapshot.ask is not None:
        spread_rate = (snapshot.ask - snapshot.bid) / snapshot.price * 100
        if spread_rate > 1:
            score -= 10
            risks.append("スプレッドが広い")
    else:
        risks.append("気配値データ未設定")
    if snapshot.volume is None:
        risks.append("出来高データ未設定")

    score = max(0, min(100, score))
    stance = "positive" if score >= 65 else "negative" if score <= 35 else "neutral"
    return {
        "symbol": snapshot.symbol,
        "score": score,
        "stance": stance,
        "reasons": reasons,
        "risks": risks,
        "change_percent": change_percent,
        "decision_support_only": True,
        "automatic_order": False,
        "updated_at": snapshot.updated_at,
        **READ_ONLY_SAFETY,
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        **READ_ONLY_SAFETY,
        "registered_symbols": sorted(SYMBOL_CELLS.keys()),
        "phase": 18,
        "parts": list(range(1, 11)),
    }


@app.get("/symbols")
def symbols() -> dict[str, Any]:
    return {"symbols": sorted(SYMBOL_CELLS), "count": len(SYMBOL_CELLS), **READ_ONLY_SAFETY}


@app.get("/price/{symbol}")
def get_price(symbol: str) -> dict[str, object]:
    normalized = normalize_symbol(symbol)
    try:
        value = read_price_from_excel(normalized)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="未登録の銘柄です。") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return quote_payload(Quote(normalized, value, datetime.now(timezone.utc).isoformat()))


@app.get("/prices")
def get_prices(symbols: str = Query(..., description="Comma-separated symbols")) -> dict[str, Any]:
    requested = [item for item in symbols.split(",") if item.strip()]
    try:
        quotes = read_quotes(requested)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"未登録の銘柄です: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"quotes": [quote_payload(q) for q in quotes], "count": len(quotes), **READ_ONLY_SAFETY}


@app.get("/discovery/realtime")
def discovery_realtime(limit: int = Query(20, ge=1, le=200)) -> dict[str, Any]:
    try:
        quotes = read_quotes(list(SYMBOL_CELLS))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    ranked = sorted(quotes, key=lambda quote: quote.price, reverse=True)[:limit]
    return {"items": [{**quote_payload(q), "rank": i + 1, "realtime": True} for i, q in enumerate(ranked)], "count": len(ranked), **READ_ONLY_SAFETY}


@app.get("/prediction/{symbol}")
def prediction_context(symbol: str) -> dict[str, Any]:
    normalized = normalize_symbol(symbol)
    try:
        price = read_price_from_excel(normalized)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="未登録の銘柄です。") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"symbol": normalized, "realtime_price": price, "data_source": "MARKETSPEED II RSS", "prediction_ready": True, "ai_analysis_ready": True, "timestamp": datetime.now(timezone.utc).isoformat(), **READ_ONLY_SAFETY}


@app.get("/portfolio/realtime")
def portfolio_realtime(symbols: str = Query(..., description="Comma-separated symbols")) -> dict[str, Any]:
    requested = [item for item in symbols.split(",") if item.strip()]
    try:
        quotes = read_quotes(requested)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"未登録の銘柄です: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"positions": [quote_payload(q) for q in quotes], "count": len(quotes), "valuation_source": "MARKETSPEED II RSS", **READ_ONLY_SAFETY}


@app.get("/watchlist")
def get_watchlist() -> dict[str, Any]:
    with WATCHLIST_LOCK:
        items = list(WATCHLIST.values())
    return {"items": items, "count": len(items), **READ_ONLY_SAFETY}


@app.post("/watchlist/{symbol}")
def add_watchlist(symbol: str, target_price: float | None = None) -> dict[str, Any]:
    normalized = normalize_symbol(symbol)
    if normalized not in SYMBOL_CELLS:
        raise HTTPException(status_code=404, detail="未登録の銘柄です。")
    with WATCHLIST_LOCK:
        WATCHLIST[normalized] = {"symbol": normalized, "target_price": target_price, "active": True, "created_at": datetime.now(timezone.utc).isoformat()}
        item = dict(WATCHLIST[normalized])
    return {"item": item, **READ_ONLY_SAFETY}


@app.delete("/watchlist/{symbol}")
def remove_watchlist(symbol: str) -> dict[str, Any]:
    normalized = normalize_symbol(symbol)
    with WATCHLIST_LOCK:
        removed = WATCHLIST.pop(normalized, None)
    return {"removed": removed is not None, "symbol": normalized, **READ_ONLY_SAFETY}


@app.get("/watchlist/check")
def check_watchlist() -> dict[str, Any]:
    with WATCHLIST_LOCK:
        items = [dict(item) for item in WATCHLIST.values() if item.get("active")]
    if not items:
        return {"alerts": [], "count": 0, **READ_ONLY_SAFETY}
    try:
        quotes = {q.symbol: q for q in read_quotes([item["symbol"] for item in items])}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    alerts = []
    for item in items:
        quote, target = quotes.get(item["symbol"]), item.get("target_price")
        if quote is not None and target is not None and quote.price >= float(target):
            alerts.append({"symbol": quote.symbol, "price": quote.price, "target_price": float(target), "triggered": True, "updated_at": quote.updated_at})
    return {"alerts": alerts, "count": len(alerts), **READ_ONLY_SAFETY}


# Phase18 Part6: realtime market monitoring.
@app.get("/monitor/realtime")
def monitor_realtime(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    try:
        snapshots = read_market_snapshots(list(SYMBOL_CELLS)[:limit])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    items = [snapshot_payload(item) for item in snapshots]
    alerts = [item for item in items if item["change_percent"] is not None and abs(item["change_percent"]) >= 3]
    return {"items": items, "alerts": alerts, "count": len(items), **READ_ONLY_SAFETY}


# Phase18 Part7: best bid/ask view. This intentionally does not place or modify orders.
@app.get("/orderbook/{symbol}")
def orderbook(symbol: str) -> dict[str, Any]:
    normalized = normalize_symbol(symbol)
    try:
        snapshot = read_market_snapshots([normalized])[0]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="未登録の銘柄です。") from exc
    except (RuntimeError, IndexError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"symbol": normalized, "best_bid": snapshot.bid, "best_ask": snapshot.ask, "spread": snapshot.ask - snapshot.bid if snapshot.ask is not None and snapshot.bid is not None else None, "available": snapshot.bid is not None and snapshot.ask is not None, "depth": "best_only", **READ_ONLY_SAFETY}


# Phase18 Part8: unified price, OHLC, volume, quote and VWAP snapshot.
@app.get("/market/{symbol}")
def market_snapshot(symbol: str) -> dict[str, Any]:
    normalized = normalize_symbol(symbol)
    try:
        snapshots = read_market_snapshots([normalized])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="未登録の銘柄です。") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not snapshots:
        raise HTTPException(status_code=503, detail="市場データを取得できません。")
    return snapshot_payload(snapshots[0])


# Phase18 Part9: explainable realtime decision support; never an execution instruction.
@app.get("/ai/realtime/{symbol}")
def realtime_ai(symbol: str) -> dict[str, Any]:
    normalized = normalize_symbol(symbol)
    try:
        snapshots = read_market_snapshots([normalized])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="未登録の銘柄です。") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not snapshots:
        raise HTTPException(status_code=503, detail="AI分析用データを取得できません。")
    return realtime_ai_payload(snapshots[0])


# Phase18 Part10: integration completion and capability declaration.
@app.get("/phase18/status")
def phase18_status() -> dict[str, Any]:
    return {
        "phase": 18,
        "completed_parts": list(range(1, 11)),
        "completion_percent": 100,
        "capabilities": ["batch_quotes", "discovery", "prediction_context", "portfolio", "watchlist", "realtime_monitor", "best_bid_ask", "ohlcv_volume_vwap", "realtime_ai", "integration_status"],
        "excel_columns": FIELD_COLUMNS,
        "note": "B-I列は任意のRSS項目。未設定項目はnullで返します。",
        **READ_ONLY_SAFETY,
    }
