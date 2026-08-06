from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from tools.rss_account_bridge import (
    PROVIDER_NAME as ACCOUNT_PROVIDER_NAME,
    read_broker_snapshot,
)
from tools.run_phase28_excel_preview import run_excel_preview

try:
    import pythoncom
    import win32com.client as win32_client
except ImportError:  # CI and non-Windows environments
    pythoncom = None
    win32_client = None

app = FastAPI(title="Ark Terminal RSS Bridge")

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://ark-terminal.vercel.app",
]

extra_origins = [
    origin.strip()
    for origin in os.getenv("ARK_RSS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

ALLOWED_ORIGINS = list(dict.fromkeys(DEFAULT_ALLOWED_ORIGINS + extra_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Accept", "Content-Type", "X-Ark-Read-Only"],
)

PRIVATE_NETWORK_ALLOWED_HEADERS = {
    "accept",
    "content-type",
    "x-ark-read-only",
}


@app.middleware("http")
async def allow_restricted_private_network_access(
    request: Request,
    call_next,
):
    origin = request.headers.get("origin")
    private_network_requested = (
        request.headers.get("access-control-request-private-network", "").lower()
        == "true"
    )

    is_broker_preflight = (
        request.method == "OPTIONS"
        and request.url.path.startswith("/broker/")
        and private_network_requested
    )

    if is_broker_preflight:
        requested_method = request.headers.get(
            "access-control-request-method",
            "",
        ).upper()
        requested_headers = {
            item.strip().lower()
            for item in request.headers.get(
                "access-control-request-headers",
                "",
            ).split(",")
            if item.strip()
        }

        allowed = (
            origin in ALLOWED_ORIGINS
            and requested_method == "GET"
            and requested_headers.issubset(
                PRIVATE_NETWORK_ALLOWED_HEADERS,
            )
        )

        if not allowed:
            return Response(
                content="Private network request denied",
                status_code=400,
                media_type="text/plain",
            )

        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": (
                    "Accept, Content-Type, X-Ark-Read-Only"
                ),
                "Access-Control-Allow-Private-Network": "true",
                "Access-Control-Max-Age": "600",
                "Vary": "Origin",
            },
        )

    response = await call_next(request)

    if origin in ALLOWED_ORIGINS and private_network_requested:
        response.headers["Access-Control-Allow-Private-Network"] = "true"

    return response


READ_ONLY_SAFETY = {
    "mode": "read_only",
    "order_creation": False,
    "order_transmission": False,
    "order_cancellation": False,
}

SYMBOL_CELLS: dict[str, str] = {
    "4755.T": "A1",
    "9432.T": "A2",
    "7203.T": "A3",
    "9984.T": "A4",
}

WATCHLIST: dict[str, dict[str, Any]] = {}
WATCHLIST_LOCK = Lock()


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
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
        raise RuntimeError(
            "MARKETSPEED II RSS BridgeはWindows環境でのみ利用できます。"
        )


def read_workbook_snapshot() -> tuple[Any, Any]:
    require_windows_com()
    pythoncom.CoInitialize()
    try:
        excel = win32_client.GetActiveObject("Excel.Application")
        workbook = excel.ActiveWorkbook
        if workbook is None:
            raise RuntimeError("Excelでブックが開かれていません。")
        return excel, workbook
    except RuntimeError:
        pythoncom.CoUninitialize()
        raise
    except Exception as exc:
        pythoncom.CoUninitialize()
        raise RuntimeError(
            "ExcelまたはMARKETSPEED II RSSに接続できません。"
        ) from exc


def read_sheet_snapshot() -> tuple[Any, Any]:
    excel, workbook = read_workbook_snapshot()
    try:
        return excel, workbook.Worksheets("Sheet1")
    except Exception as exc:
        release_com()
        raise RuntimeError(
            "ExcelにSheet1シートが見つかりません。"
        ) from exc


def release_com() -> None:
    if pythoncom is not None:
        pythoncom.CoUninitialize()


def read_price_from_excel(symbol: str) -> float:
    normalized = normalize_symbol(symbol)
    cell = SYMBOL_CELLS.get(normalized)
    if cell is None:
        raise KeyError(normalized)

    _, sheet = read_sheet_snapshot()
    try:
        value = sheet.Range(cell).Value
        if value is None:
            raise RuntimeError("価格を取得できません。")
        return float(value)
    finally:
        release_com()


def read_quotes(symbols: list[str]) -> list[Quote]:
    normalized_symbols = [normalize_symbol(symbol) for symbol in symbols]
    unknown = [symbol for symbol in normalized_symbols if symbol not in SYMBOL_CELLS]
    if unknown:
        raise KeyError(",".join(unknown))

    _, sheet = read_sheet_snapshot()
    try:
        now = datetime.now(timezone.utc).isoformat()
        quotes: list[Quote] = []
        for symbol in normalized_symbols:
            value = sheet.Range(SYMBOL_CELLS[symbol]).Value
            if value is None:
                continue
            quotes.append(Quote(symbol=symbol, price=float(value), updated_at=now))
        return quotes
    finally:
        release_com()


def read_account_snapshot_from_excel() -> dict[str, Any]:
    _, workbook = read_workbook_snapshot()
    try:
        return read_broker_snapshot(workbook)
    finally:
        release_com()


def quote_payload(quote: Quote) -> dict[str, Any]:
    return {
        "symbol": quote.symbol,
        "price": quote.price,
        "updated_at": quote.updated_at,
        "source": "MARKETSPEED II RSS",
        "read_only": True,
        "order_transmission": False,
    }


def disconnected_account_payload(message: str) -> dict[str, Any]:
    return {
        "connected": False,
        "authenticated": False,
        "provider": ACCOUNT_PROVIDER_NAME,
        "accountId": None,
        "connectedAt": None,
        "lastSyncAt": None,
        "message": message,
        "readOnly": True,
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        **READ_ONLY_SAFETY,
        "registered_symbols": sorted(SYMBOL_CELLS.keys()),
        "phase": 19,
        "parts": [1, 2, 3, 4, 5, 6],
        "market_data_phase": 18,
        "account_bridge": True,
        "phase28_5_excel_preview": True,
        "allowed_origins": ALLOWED_ORIGINS,
    }


@app.post("/dry-run/order-preview")
def dry_run_order_preview(
    symbol: str = Query("7203.T"),
    quantity: int = Query(100, ge=1),
    limit_price: float = Query(1.0, gt=0),
) -> dict[str, Any]:
    try:
        return run_excel_preview(symbol, quantity, limit_price)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/symbols")
def symbols() -> dict[str, Any]:
    return {
        "symbols": sorted(SYMBOL_CELLS.keys()),
        "count": len(SYMBOL_CELLS),
        **READ_ONLY_SAFETY,
    }


@app.get("/price/{symbol}")
def get_price(symbol: str) -> dict[str, object]:
    normalized = normalize_symbol(symbol)
    try:
        value = read_price_from_excel(normalized)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="未登録の銘柄です。") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    quote = Quote(
        symbol=normalized,
        price=value,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    return quote_payload(quote)


@app.get("/prices")
def get_prices(symbols: str = Query(..., description="Comma-separated symbols")) -> dict[str, Any]:
    requested = [item for item in symbols.split(",") if item.strip()]
    try:
        quotes = read_quotes(requested)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"未登録の銘柄です: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "quotes": [quote_payload(quote) for quote in quotes],
        "count": len(quotes),
        **READ_ONLY_SAFETY,
    }


@app.get("/discovery/realtime")
def discovery_realtime(limit: int = Query(20, ge=1, le=200)) -> dict[str, Any]:
    try:
        quotes = read_quotes(list(SYMBOL_CELLS.keys()))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    ranked = sorted(quotes, key=lambda quote: quote.price, reverse=True)[:limit]
    return {
        "items": [
            {
                **quote_payload(quote),
                "rank": index + 1,
                "realtime": True,
            }
            for index, quote in enumerate(ranked)
        ],
        "count": len(ranked),
        **READ_ONLY_SAFETY,
    }


@app.get("/prediction/{symbol}")
def prediction_context(symbol: str) -> dict[str, Any]:
    normalized = normalize_symbol(symbol)
    try:
        price = read_price_from_excel(normalized)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="未登録の銘柄です。") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "symbol": normalized,
        "realtime_price": price,
        "data_source": "MARKETSPEED II RSS",
        "prediction_ready": True,
        "ai_analysis_ready": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **READ_ONLY_SAFETY,
    }


@app.get("/portfolio/realtime")
def portfolio_realtime(symbols: str = Query(..., description="Comma-separated symbols")) -> dict[str, Any]:
    requested = [item for item in symbols.split(",") if item.strip()]
    try:
        quotes = read_quotes(requested)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"未登録の銘柄です: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "positions": [quote_payload(quote) for quote in quotes],
        "count": len(quotes),
        "valuation_source": "MARKETSPEED II RSS",
        **READ_ONLY_SAFETY,
    }


@app.get("/broker/connection")
def broker_connection() -> dict[str, Any]:
    try:
        snapshot = read_account_snapshot_from_excel()
    except RuntimeError as exc:
        return disconnected_account_payload(str(exc))

    return snapshot["connection"]


@app.get("/broker/account")
def broker_account() -> dict[str, Any]:
    try:
        snapshot = read_account_snapshot_from_excel()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "account": snapshot["account"],
        "readOnly": True,
    }


@app.get("/broker/positions")
def broker_positions() -> dict[str, Any]:
    try:
        snapshot = read_account_snapshot_from_excel()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "positions": snapshot["positions"],
        "count": len(snapshot["positions"]),
        "readOnly": True,
    }


@app.get("/broker/snapshot")
def broker_snapshot() -> dict[str, Any]:
    try:
        return read_account_snapshot_from_excel()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
        WATCHLIST[normalized] = {
            "symbol": normalized,
            "target_price": target_price,
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
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
        quotes = {quote.symbol: quote for quote in read_quotes([item["symbol"] for item in items])}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    alerts: list[dict[str, Any]] = []
    for item in items:
        quote = quotes.get(item["symbol"])
        target = item.get("target_price")
        if quote is None or target is None:
            continue
        if quote.price >= float(target):
            alerts.append({
                "symbol": quote.symbol,
                "price": quote.price,
                "target_price": float(target),
                "triggered": True,
                "updated_at": quote.updated_at,
            })

    return {"alerts": alerts, "count": len(alerts), **READ_ONLY_SAFETY}
