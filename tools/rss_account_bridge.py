from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

ACCOUNT_SHEET_NAME = "ArkAccount"
POSITIONS_SHEET_NAME = "ArkPositions"
PROVIDER_NAME = "MARKETSPEED II RSS / Excel"
MAX_POSITION_ROWS = 500
MAX_SCAN_ROWS = 12
MAX_SCAN_COLUMNS = 30

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

NATIVE_POSITION_HEADERS = {
    "symbol": ("銘柄コード",),
    "name": ("銘柄名称", "銘柄名"),
    "accountType": ("口座区分",),
    "quantity": ("保有数量",),
    "orderQuantity": ("発注数量",),
    "averagePrice": ("平均取得価額",),
    "marketPrice": ("時価",),
    "marketValue": ("時価評価額",),
    "unrealizedPnl": ("評価損益額",),
    "unrealizedPnlPercent": ("評価損益率",),
}

NATIVE_REQUIRED_POSITION_FIELDS = {
    "symbol",
    "name",
    "accountType",
    "quantity",
    "averagePrice",
    "marketPrice",
    "marketValue",
    "unrealizedPnl",
    "unrealizedPnlPercent",
}

NATIVE_CAPACITY_HEADERS = {
    "buyingPower": ("現物買付可能額",),
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


def _column_letter(index: int) -> str:
    if index < 1:
        raise ValueError("Excel column index must be 1 or greater.")

    letters = ""
    value = index
    while value:
        value, remainder = divmod(value - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _header_key(value: Any) -> str:
    text = _text(value) or ""
    return (
        text.replace(" ", "")
        .replace("　", "")
        .replace("\r", "")
        .replace("\n", "")
        .strip()
    )


def _canonical_header_fields(
    headers: dict[str, tuple[str, ...]],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for field, aliases in headers.items():
        for alias in aliases:
            result[_header_key(alias)] = field
    return result


def _find_header_row(
    sheet: Any,
    headers: dict[str, tuple[str, ...]],
    *,
    required_fields: set[str],
    max_rows: int = MAX_SCAN_ROWS,
    max_columns: int = MAX_SCAN_COLUMNS,
) -> tuple[int, dict[str, int]] | None:
    aliases = _canonical_header_fields(headers)

    for row in range(1, max_rows + 1):
        field_columns: dict[str, int] = {}
        for column in range(1, max_columns + 1):
            address = f"{_column_letter(column)}{row}"
            key = _header_key(_cell(sheet, address))
            field = aliases.get(key)
            if field and field not in field_columns:
                field_columns[field] = column

        if required_fields.issubset(field_columns):
            return row, field_columns

    return None


def _native_header_value(
    sheet: Any,
    field_columns: dict[str, int],
    field: str,
    row: int,
) -> Any:
    column = field_columns.get(field)
    if column is None:
        return None
    return _cell(sheet, f"{_column_letter(column)}{row}")


def normalize_symbol(value: Any) -> str:
    symbol = str(value or "").strip().upper()
    if symbol.isdigit():
        return f"{symbol}.T"
    return symbol


def _legacy_account_values(sheet: Any) -> dict[str, Any]:
    return {
        key: _cell(sheet, address)
        for key, address in ACCOUNT_CELLS.items()
    }


def _read_legacy_account(
    sheet: Any,
    *,
    synchronized_at: str,
) -> dict[str, Any]:
    values = _legacy_account_values(sheet)

    cash = _number(values["cash"])
    buying_power = _number(values["buyingPower"])
    market_value = _number(values["marketValue"])
    equity = _number(values["equity"])

    has_valid_account_data = any(
        value is not None
        for value in (
            cash,
            buying_power,
            market_value,
            equity,
        )
    )

    if not has_valid_account_data:
        raise RuntimeError(
            "ArkAccountシートに有効な数値の口座データがありません。"
        )

    cash_value = cash if cash is not None else 0.0
    market_value_value = market_value if market_value is not None else 0.0
    buying_power_value = (
        buying_power if buying_power is not None else cash_value
    )
    equity_value = (
        equity
        if equity is not None
        else cash_value + market_value_value
    )

    return {
        "accountId": None,
        "provider": PROVIDER_NAME,
        "accountType": _text(values["accountType"]),
        "currency": (_text(values["currency"]) or "JPY").upper(),
        "cash": cash_value,
        "buyingPower": buying_power_value,
        "marketValue": market_value_value,
        "equity": equity_value,
        "realizedPnl": _number(values["realizedPnl"], default=0.0) or 0.0,
        "unrealizedPnl": _number(values["unrealizedPnl"], default=0.0) or 0.0,
        "updatedAt": _iso_datetime(values["updatedAt"], synchronized_at),
        "availableMetrics": {
            "cash": cash is not None,
            "buyingPower": buying_power is not None,
            "marketValue": market_value is not None,
            "equity": equity is not None,
            "realizedPnl": _number(values["realizedPnl"]) is not None,
            "unrealizedPnl": _number(values["unrealizedPnl"]) is not None,
        },
        "sourceMode": "legacy-normalized-sheet",
        "readOnly": True,
    }


def _sum_defined(
    values: list[float | None],
    *,
    empty_value: float | None = None,
) -> float | None:
    defined = [value for value in values if value is not None]
    if not defined:
        return empty_value
    return float(sum(defined))


def _account_type_from_positions(
    positions: list[dict[str, Any]],
) -> str | None:
    account_types = sorted(
        {
            value
            for value in (
                _text(position.get("accountType"))
                for position in positions
            )
            if value
        }
    )

    if not account_types:
        return None
    if len(account_types) == 1:
        return account_types[0]
    return "複数口座区分"


def _read_native_account(
    sheet: Any,
    positions: list[dict[str, Any]],
    *,
    synchronized_at: str,
) -> dict[str, Any] | None:
    header = _find_header_row(
        sheet,
        NATIVE_CAPACITY_HEADERS,
        required_fields={"buyingPower"},
    )

    if header is None:
        return None

    header_row, field_columns = header
    data_row = header_row + 1
    buying_power = _number(
        _native_header_value(
            sheet,
            field_columns,
            "buyingPower",
            data_row,
        )
    )

    if buying_power is None:
        raise RuntimeError(
            "ArkAccountのRssCapacityList出力に現物買付可能額がありません。"
        )

    market_value = _sum_defined(
        [
            _number(position.get("marketValue"))
            for position in positions
        ],
        empty_value=0.0,
    )
    unrealized_pnl = _sum_defined(
        [
            _number(position.get("unrealizedPnl"))
            for position in positions
        ],
        empty_value=0.0,
    )

    return {
        "accountId": None,
        "provider": PROVIDER_NAME,
        "accountType": _account_type_from_positions(positions),
        "currency": "JPY",
        "cash": None,
        "buyingPower": buying_power,
        "marketValue": market_value,
        "equity": None,
        "realizedPnl": None,
        "unrealizedPnl": unrealized_pnl,
        "updatedAt": synchronized_at,
        "availableMetrics": {
            "cash": False,
            "buyingPower": True,
            "marketValue": True,
            "equity": False,
            "realizedPnl": False,
            "unrealizedPnl": True,
        },
        "sourceMode": "marketspeed-native-rss",
        "readOnly": True,
    }


def read_account(
    workbook: Any,
    *,
    positions: list[dict[str, Any]] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    synchronized_at = now or utc_now_iso()
    sheet = _sheet(workbook, ACCOUNT_SHEET_NAME)
    normalized_positions = positions or []

    native = _read_native_account(
        sheet,
        normalized_positions,
        synchronized_at=synchronized_at,
    )
    if native is not None:
        return native

    return _read_legacy_account(
        sheet,
        synchronized_at=synchronized_at,
    )


def _read_native_positions(
    sheet: Any,
    *,
    synchronized_at: str,
    max_rows: int,
) -> list[dict[str, Any]] | None:
    header = _find_header_row(
        sheet,
        NATIVE_POSITION_HEADERS,
        required_fields=NATIVE_REQUIRED_POSITION_FIELDS,
    )

    if header is None:
        return None

    header_row, field_columns = header
    positions: list[dict[str, Any]] = []

    for row in range(header_row + 1, header_row + max_rows + 1):
        symbol = normalize_symbol(
            _native_header_value(
                sheet,
                field_columns,
                "symbol",
                row,
            )
        )

        if not symbol:
            break

        quantity = _number(
            _native_header_value(
                sheet,
                field_columns,
                "quantity",
                row,
            ),
            default=0.0,
        ) or 0.0

        if quantity == 0:
            continue

        market_value = _number(
            _native_header_value(
                sheet,
                field_columns,
                "marketValue",
                row,
            )
        )
        market_price = _number(
            _native_header_value(
                sheet,
                field_columns,
                "marketPrice",
                row,
            )
        )
        average_price = _number(
            _native_header_value(
                sheet,
                field_columns,
                "averagePrice",
                row,
            )
        )
        unrealized_pnl = _number(
            _native_header_value(
                sheet,
                field_columns,
                "unrealizedPnl",
                row,
            )
        )

        if market_value is None and market_price is not None:
            market_value = market_price * quantity

        if (
            unrealized_pnl is None
            and market_price is not None
            and average_price is not None
        ):
            unrealized_pnl = (market_price - average_price) * quantity

        order_quantity = _number(
            _native_header_value(
                sheet,
                field_columns,
                "orderQuantity",
                row,
            ),
            default=0.0,
        ) or 0.0

        positions.append(
            {
                "symbol": symbol,
                "name": _text(
                    _native_header_value(
                        sheet,
                        field_columns,
                        "name",
                        row,
                    )
                ),
                "quantity": quantity,
                "availableQuantity": quantity,
                "orderQuantity": order_quantity,
                "averagePrice": average_price,
                "marketPrice": market_price,
                "marketValue": market_value,
                "unrealizedPnl": unrealized_pnl,
                "unrealizedPnlPercent": _number(
                    _native_header_value(
                        sheet,
                        field_columns,
                        "unrealizedPnlPercent",
                        row,
                    )
                ),
                "currency": "JPY",
                "accountType": _text(
                    _native_header_value(
                        sheet,
                        field_columns,
                        "accountType",
                        row,
                    )
                ),
                "updatedAt": synchronized_at,
                "sourceMode": "marketspeed-native-rss",
                "readOnly": True,
            }
        )

    return positions


def _read_legacy_positions(
    sheet: Any,
    *,
    synchronized_at: str,
    max_rows: int,
) -> list[dict[str, Any]]:
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
                "sourceMode": "legacy-normalized-sheet",
                "readOnly": True,
            }
        )

    return positions


def read_positions(
    workbook: Any,
    *,
    now: str | None = None,
    max_rows: int = MAX_POSITION_ROWS,
) -> list[dict[str, Any]]:
    synchronized_at = now or utc_now_iso()
    sheet = _sheet(workbook, POSITIONS_SHEET_NAME)

    native = _read_native_positions(
        sheet,
        synchronized_at=synchronized_at,
        max_rows=max_rows,
    )
    if native is not None:
        return native

    return _read_legacy_positions(
        sheet,
        synchronized_at=synchronized_at,
        max_rows=max_rows,
    )


def read_broker_snapshot(
    workbook: Any,
    *,
    now: str | None = None,
) -> dict[str, Any]:
    synchronized_at = now or utc_now_iso()
    positions = read_positions(workbook, now=synchronized_at)
    account = read_account(
        workbook,
        positions=positions,
        now=synchronized_at,
    )
    source_mode = account.get("sourceMode") or "unknown"

    return {
        "connection": {
            "connected": True,
            "authenticated": True,
            "provider": PROVIDER_NAME,
            "accountId": None,
            "connectedAt": synchronized_at,
            "lastSyncAt": synchronized_at,
            "message": (
                "MARKETSPEED II RSSの保有銘柄一覧と現物買付可能額を"
                "読み取り専用で同期しています。"
                if source_mode == "marketspeed-native-rss"
                else "Excel経由で実口座データを読み取り中です。"
            ),
            "readOnly": True,
        },
        "account": account,
        "positions": positions,
        "orders": [],
        "readOnly": True,
        "synchronized": True,
        "synchronizedAt": synchronized_at,
        "source": PROVIDER_NAME,
        "sourceMode": source_mode,
    }
