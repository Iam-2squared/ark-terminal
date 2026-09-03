from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase58_excel_microstructure_capture import (
    _excel_time,
    _find_workbook,
    _row_dict,
    _scalar,
    _tick_header_indices,
    _used_matrix,
)

SAFETY = {
    "phase": "58.p31.multi-symbol-capture",
    "mode": "MARKETSPEED_II_RSS_READ_ONLY_PRECONFIGURED_MULTISYMBOL",
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

FORBIDDEN_FORMULA_TOKENS = (
    "RSSSTOCKORDER",
    "RSSMARGINOPENORDER",
    "RSSMARGINCLOSEORDER",
    "RSSMODIFYORDER",
    "RSSCANCELORDER",
    "RSSFUTUREORDER",
    "RSSOPTIONORDER",
    "RSSFOP",
)
_SYMBOL = re.compile(r"^(?:\d{4,5})(?:\.T)?$", re.IGNORECASE)


def normalize_symbol(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if not _SYMBOL.fullmatch(raw):
        raise ValueError(f"invalid JPX symbol: {value}")
    return raw if raw.endswith(".T") else f"{raw}.T"


def validate_registry(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
        raise ValueError("registry schemaVersion must be 1")
    rows = payload.get("symbols")
    if not isinstance(rows, list) or not rows:
        raise ValueError("registry symbols[] is required")
    normalized: list[dict[str, str]] = []
    seen_symbols: set[str] = set()
    seen_sheets: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"registry symbols[{index}] must be an object")
        symbol = normalize_symbol(row.get("symbol"))
        market_sheet = str(row.get("marketSheet") or "").strip()
        tick_sheet = str(row.get("tickSheet") or "").strip()
        if not market_sheet or not tick_sheet:
            raise ValueError(f"registry {symbol} requires marketSheet and tickSheet")
        if market_sheet == tick_sheet:
            raise ValueError(f"registry {symbol} marketSheet and tickSheet must differ")
        if symbol in seen_symbols:
            raise ValueError(f"duplicate registry symbol: {symbol}")
        for sheet in (market_sheet, tick_sheet):
            if sheet in seen_sheets:
                raise ValueError(f"sheet reused across symbols: {sheet}")
            seen_sheets.add(sheet)
        seen_symbols.add(symbol)
        normalized.append({"symbol": symbol, "marketSheet": market_sheet, "tickSheet": tick_sheet})
    return {
        "schemaVersion": 1,
        "workbook": str(payload.get("workbook") or "").strip() or None,
        "symbols": normalized,
    }


def _formula_values(sheet: Any) -> list[list[Any]]:
    values = sheet.UsedRange.Formula
    if values is None:
        return []
    if not isinstance(values, (tuple, list)):
        return [[values]]
    rows = list(values)
    if rows and not isinstance(rows[0], (tuple, list)):
        return [list(rows)]
    return [list(row) for row in rows]


def assert_read_only_formula_surface(sheet: Any, label: str) -> None:
    for row in _formula_values(sheet):
        for value in row:
            text = str(value or "").upper().replace(" ", "")
            forbidden = next((token for token in FORBIDDEN_FORMULA_TOKENS if token in text), None)
            if forbidden:
                raise RuntimeError(f"forbidden RSS order-capable formula in {label}: {forbidden}")


def read_market_sheet_named(workbook: Any, sheet_name: str, expected_symbol: str) -> dict[str, Any]:
    sheet = workbook.Worksheets(sheet_name)
    assert_read_only_formula_surface(sheet, sheet_name)
    matrix = _used_matrix(sheet)
    if len(matrix) < 2:
        raise RuntimeError(f"{sheet_name} must contain headers in row 1 and RSS values in row 2")
    row = _row_dict(matrix[0], matrix[1])
    required = ["symbol", "bestAsk", "bestBid", "bestAskSize", "bestBidSize", "bestAskTime", "bestBidTime"]
    missing = [key for key in required if row.get(key) in (None, "")]
    if missing:
        raise RuntimeError(f"{sheet_name} missing RSS values: {','.join(missing)}")
    observed_symbol = normalize_symbol(row.get("symbol"))
    if observed_symbol != expected_symbol:
        raise RuntimeError(f"{sheet_name} symbol mismatch: expected {expected_symbol}, observed {observed_symbol}")
    return row


def read_tick_sheet_named(workbook: Any, sheet_name: str, max_rows: int = 300) -> list[dict[str, Any]]:
    sheet = workbook.Worksheets(sheet_name)
    assert_read_only_formula_surface(sheet, sheet_name)
    matrix = _used_matrix(sheet)
    if len(matrix) < 2:
        return []
    header_row_index: int | None = None
    indices: dict[str, int] | None = None
    for row_index, row in enumerate(matrix[:10]):
        candidate = _tick_header_indices(row)
        if candidate is not None:
            header_row_index = row_index
            indices = candidate
    if header_row_index is None or indices is None:
        raise RuntimeError(f"{sheet_name} must contain a 時刻 / 出来高 / 約定値 header row in the first 10 rows")
    ticks: list[dict[str, Any]] = []
    for row in matrix[header_row_index + 1 : header_row_index + 1 + max_rows]:
        raw_time = row[indices["time"]] if indices["time"] < len(row) else None
        raw_volume = row[indices["volume"]] if indices["volume"] < len(row) else None
        raw_price = row[indices["price"]] if indices["price"] < len(row) else None
        if raw_time in (None, "") and raw_volume in (None, "") and raw_price in (None, ""):
            continue
        ticks.append({"time": _excel_time(raw_time), "volume": _scalar(raw_volume), "price": _scalar(raw_price)})
    return ticks


def capture_symbol(workbook: Any, mapping: dict[str, str], *, batch_id: str) -> dict[str, Any]:
    captured_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    symbol = mapping["symbol"]
    market = read_market_sheet_named(workbook, mapping["marketSheet"], symbol)
    ticks = read_tick_sheet_named(workbook, mapping["tickSheet"])
    asks = [{"level": level, "price": market.get(f"ask{level}"), "size": market.get(f"askSize{level}")} for level in range(1, 11)]
    bids = [{"level": level, "price": market.get(f"bid{level}"), "size": market.get(f"bidSize{level}")} for level in range(1, 11)]
    return {
        "schemaVersion": 1,
        "phase": "58.p31.multi-symbol-capture",
        "sourceMode": "MARKETSPEED_II_RSS_READ_ONLY",
        "batchId": batch_id,
        "capturedAt": captured_at,
        "symbol": symbol,
        "tickOrder": "DESC",
        "market": market,
        "orderBook": {"asks": asks, "bids": bids},
        "ticks": ticks,
        "sourceFunctions": ["RssMarket", "RssTickList"],
        "marketSizeUnit": "SHARES",
        "tickSizeUnit": "SHARES",
        "methodology": {
            "preconfiguredSheetsOnly": True,
            "excelFormulaWritePerformed": False,
            "symbolSwitchWritePerformed": False,
            "pointInTimeOnly": True,
            "futureOutcomeUsed": False,
        },
        "safety": SAFETY,
    }


def capture_batch(workbook: Any, registry: dict[str, Any], *, max_skew_ms: float) -> list[dict[str, Any]]:
    start = datetime.now(timezone.utc)
    batch_id = f"MSII_MULTI|{start.isoformat(timespec='milliseconds')}"
    rows = [capture_symbol(workbook, mapping, batch_id=batch_id) for mapping in registry["symbols"]]
    end = datetime.now(timezone.utc)
    skew_ms = (end - start).total_seconds() * 1000.0
    if skew_ms > max_skew_ms:
        raise RuntimeError(f"multi-symbol capture batch exceeded max skew: {skew_ms:.3f}ms > {max_skew_ms:.3f}ms")
    for row in rows:
        row["batchStartedAt"] = start.isoformat(timespec="milliseconds")
        row["batchCompletedAt"] = end.isoformat(timespec="milliseconds")
        row["batchSkewMs"] = skew_ms
    return rows


def append_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="READ ONLY preconfigured multi-symbol MarketSpeed II RSS capture")
    parser.add_argument("--registry", required=True)
    parser.add_argument("--workbook", default=None)
    parser.add_argument("--output", default="data/phase58/msii-multisymbol-live.jsonl")
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--samples", type=int, default=120)
    parser.add_argument("--max-batch-skew-ms", type=float, default=5000.0)
    args = parser.parse_args()
    if args.samples < 1:
        raise SystemExit("--samples must be >= 1")
    if args.interval_seconds < 0.2:
        raise SystemExit("--interval-seconds must be >= 0.2")
    if args.max_batch_skew_ms <= 0:
        raise SystemExit("--max-batch-skew-ms must be > 0")
    registry = validate_registry(json.loads(Path(args.registry).read_text(encoding="utf-8")))

    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise SystemExit("pywin32 is required: py -m pip install -r tools/requirements-rss.txt") from exc
    excel = win32com.client.GetActiveObject("Excel.Application")
    workbook = _find_workbook(excel, args.workbook or registry.get("workbook"))
    output = Path(args.output)
    print(json.dumps({
        "status": "PHASE58_MSII_MULTISYMBOL_CAPTURE_START",
        "workbook": workbook.Name,
        "symbolCount": len(registry["symbols"]),
        "samples": args.samples,
        "intervalSeconds": args.interval_seconds,
        "maxBatchSkewMs": args.max_batch_skew_ms,
        "output": str(output),
        "safety": SAFETY,
    }, ensure_ascii=False))
    rows_written = 0
    for index in range(args.samples):
        rows = capture_batch(workbook, registry, max_skew_ms=args.max_batch_skew_ms)
        append_rows(output, rows)
        rows_written += len(rows)
        if index + 1 < args.samples:
            time.sleep(args.interval_seconds)
    print(json.dumps({
        "status": "PHASE58_MSII_MULTISYMBOL_CAPTURE_COMPLETE",
        "rowsWritten": rows_written,
        "sha256": sha256_file(output),
        "output": str(output),
        "safety": SAFETY,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
