from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

ACCOUNT_SHEET_NAME = "ArkAccount"
POSITIONS_SHEET_NAME = "ArkPositions"
PROVIDER_NAME = "MARKETSPEED II RSS / Excel"
MAX_POSITION_ROWS = 500

ACCOUNT_CELLS = {
    "cash": "B2",
    "buyingPower": "B3",
    "marketValue": "B4",
    "equity": "B5",
    "realizedPnl": "B6",
    "unrealizedPnl": "B7",
    "currency": "B8",
    "updatedAt": "B9",
    "accountType": "B10",
}

POSITION_COLUMNS = {
    "symbol": "A",
    "name": "B",
    "quantity": "C",
    "availableQuantity": "D",
    "averagePrice": "E",
    "marketPrice": "F",
    "marketValue": "G",
    "unrealizedPnl": "H",
    "unrealizedPnlPercent": "I",
    "currency": "J",
    "accountType": "K",
    "updatedAt": "L",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number(value: Any, *, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default

    if isinstance(value, bool):
        return default

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return default

    negative = text.startswith("(") and text.endswith(")")
    cleaned = (
        text.replace(",", "")
        .replace("¥", "")
        .replace("￥", "")
        .replace("円", "")
        .replace("%", "")
        .strip("() ")
    )

    try:
        result = float(cleaned)
    except (TypeError, ValueError):
        return default

    return -result if negative else result


def _iso_datetime(value: Any, fallback: str) -> str:
    if value is None or value == "":
        return fallback

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    if isinstance(value, date):
        return datetime(
            value.year,
            value.month,
            value.day,
            tzinfo=timezone.utc,
        ).isoformat()

    return str(value).strip() or fallback


def _sheet(workbook: Any, name: str) -> Any:
    try:
        return workbook.Worksheets(name)
    except Exception as exc:
        raise RuntimeError(
            f"Excelに{name}シートが見つかりません。"
        ) from exc


def _cell(sheet: Any, address: str) -> Any:
    try:
        return sheet.Range(address).Value
    except Exception as exc:
        raise RuntimeError(
            f"Excelセル {address} を読み取れません。"
        ) from exc


def normalize_symbol(value: Any) -> str:
    symbol = str(value or "").strip().upper()
    if symbol.isdigit():
        return f"{symbol}.T"
    return symbol


def read_account(workbook: Any, *, now: str | None = None) -> dict[str, Any]:
    synchronized_at = now or utc_now_iso()
    sheet = _sheet(workbook, ACCOUNT_SHEET_NAME)

    values = {
        key: _cell(sheet, address)
        for key, address in ACCOUNT_CELLS.items()
    }

    cash = _number(values["cash"], default=0.0) or 0.0
    buying_power = _number(values["buyingPower"], default=cash)
    market_value = _number(values["marketValue"], default=0.0) or 0.0
    equity = _number(values["equity"], default=cash + market_value)

    has_account_data = any(
        values[key] not in (None, "")
        for key in (
            "cash",
            "buyingPower",
            "marketValue",
            "equity",
        )
    )

    if not has_account_data:
        raise RuntimeError(
            "ArkAccountシートに口座データがありません。"
        )

    return {
        "accountId": None,
        "provider": PROVIDER_NAME,
        "accountType": _text(values["accountType"]),
        "currency": (_text(values["currency"]) or "JPY").upper(),
        "cash": cash,
        "buyingPower": buying_power if buying_power is not None else cash,
        "marketValue": market_value,
        "equity": equity if equity is not None else cash + market_value,
        "realizedPnl": _number(values["realizedPnl"], default=0.0) or 0.0,
        "unrealizedPnl": _number(values["unrealizedPnl"], default=0.0) or 0.0,
        "updatedAt": _iso_datetime(values["updatedAt"], synchronized_at),
        "readOnly": True,
    }


def read_positions(
    workbook: Any,
    *,
    now: str | None = None,
    max_rows: int = MAX_POSITION_ROWS,
) -> list[dict[str, Any]]:
    synchronized_at = now or utc_now_iso()
    sheet = _sheet(workbook, POSITIONS_SHEET_NAME)
    positions: list[dict[str, Any]] = []

    for row in range(2, max_rows + 2):
        symbol = normalize_symbol(
            _cell(sheet, f"{POSITION_COLUMNS['symbol']}{row}")
        )

        if not symbol:
            break

        quantity = _number(
            _cell(sheet, f"{POSITION_COLUMNS['quantity']}{row}"),
            default=0.0,
        ) or 0.0

        if quantity == 0:
            continue

        average_price = _number(
            _cell(sheet, f"{POSITION_COLUMNS['averagePrice']}{row}")
        )
        market_price = _number(
            _cell(sheet, f"{POSITION_COLUMNS['marketPrice']}{row}")
        )
        market_value = _number(
            _cell(sheet, f"{POSITION_COLUMNS['marketValue']}{row}")
        )
        unrealized_pnl = _number(
            _cell(sheet, f"{POSITION_COLUMNS['unrealizedPnl']}{row}")
        )

        if market_value is None and market_price is not None:
            market_value = market_price * quantity

        if (
            unrealized_pnl is None
            and market_price is not None
            and average_price is not None
        ):
            unrealized_pnl = (market_price - average_price) * quantity

        available_quantity = _number(
            _cell(sheet, f"{POSITION_COLUMNS['availableQuantity']}{row}"),
            default=quantity,
        )

        updated_at_value = _cell(
            sheet,
            f"{POSITION_COLUMNS['updatedAt']}{row}",
        )

        positions.append(
            {
                "symbol": symbol,
                "name": _text(
                    _cell(sheet, f"{POSITION_COLUMNS['name']}{row}")
                ),
                "quantity": quantity,
                "availableQuantity": (
                    available_quantity
                    if available_quantity is not None
                    else quantity
                ),
                "averagePrice": average_price,
                "marketPrice": market_price,
                "marketValue": market_value,
                "unrealizedPnl": unrealized_pnl,
                "unrealizedPnlPercent": _number(
                    _cell(
                        sheet,
                        f"{POSITION_COLUMNS['unrealizedPnlPercent']}{row}",
                    )
                ),
                "currency": (
                    _text(
                        _cell(sheet, f"{POSITION_COLUMNS['currency']}{row}")
                    )
                    or "JPY"
                ).upper(),
                "accountType": _text(
                    _cell(sheet, f"{POSITION_COLUMNS['accountType']}{row}")
                ),
                "updatedAt": _iso_datetime(
                    updated_at_value,
                    synchronized_at,
                ),
                "readOnly": True,
            }
        )

    return positions


def read_broker_snapshot(
    workbook: Any,
    *,
    now: str | None = None,
) -> dict[str, Any]:
    synchronized_at = now or utc_now_iso()
    account = read_account(workbook, now=synchronized_at)
    positions = read_positions(workbook, now=synchronized_at)

    return {
        "connection": {
            "connected": True,
            "authenticated": True,
            "provider": PROVIDER_NAME,
            "accountId": None,
            "connectedAt": synchronized_at,
            "lastSyncAt": synchronized_at,
            "message": "Excel経由で実口座データを読み取り中です。",
            "readOnly": True,
        },
        "account": account,
        "positions": positions,
        "orders": [],
        "readOnly": True,
        "synchronized": True,
        "synchronizedAt": synchronized_at,
        "source": PROVIDER_NAME,
    }
