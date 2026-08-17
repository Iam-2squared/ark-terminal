from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASE58_CAPTURE_SAFETY = {
    "phase": "58.p8.capture",
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


def _scalar(value: Any) -> Any:
    if value in (None, ""):
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def _excel_time(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%H:%M:%S.%f")[:-3]
        except Exception:
            pass
    if isinstance(value, (int, float)):
        fraction = float(value) % 1.0
        total_ms = round(fraction * 86_400_000)
        hh = (total_ms // 3_600_000) % 24
        mm = (total_ms % 3_600_000) // 60_000
        ss = (total_ms % 60_000) // 1000
        ms = total_ms % 1000
        return f"{hh:02d}:{mm:02d}:{ss:02d}.{ms:03d}"
    text = str(value).strip()
    return text or None


def _row_dict(headers: list[Any], values: list[Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for index, header in enumerate(headers):
        key = str(header or "").strip()
        if key:
            out[key] = _scalar(values[index] if index < len(values) else None)
    return out


def _used_matrix(sheet: Any) -> list[list[Any]]:
    values = sheet.UsedRange.Value
    if values is None:
        return []
    if not isinstance(values, (tuple, list)):
        return [[values]]
    rows = list(values)
    if rows and not isinstance(rows[0], (tuple, list)):
        return [list(rows)]
    return [list(row) for row in rows]


def _find_workbook(excel: Any, workbook_name: str | None) -> Any:
    if workbook_name:
        for workbook in excel.Workbooks:
            if str(workbook.Name).lower() == workbook_name.lower():
                return workbook
        raise RuntimeError(f"Excel workbook not found: {workbook_name}")
    for workbook in excel.Workbooks:
        names = {str(workbook.Worksheets(i).Name) for i in range(1, workbook.Worksheets.Count + 1)}
        if {"ArkMarket", "ArkTicks"}.issubset(names):
            return workbook
    raise RuntimeError("No open workbook contains both ArkMarket and ArkTicks sheets")


def read_market_sheet(workbook: Any) -> dict[str, Any]:
    matrix = _used_matrix(workbook.Worksheets("ArkMarket"))
    if len(matrix) < 2:
        raise RuntimeError("ArkMarket must contain headers in row 1 and RSS values in row 2")
    row = _row_dict(matrix[0], matrix[1])
    required = ["symbol", "bestAsk", "bestBid", "bestAskSize", "bestBidSize", "bestAskTime", "bestBidTime"]
    missing = [key for key in required if row.get(key) in (None, "")]
    if missing:
        raise RuntimeError(f"ArkMarket missing RSS values: {','.join(missing)}")
    return row


def _tick_header_indices(row: list[Any]) -> dict[str, int] | None:
    headers = [str(value or "").strip() for value in row]
    aliases = {
        "time": {"時刻", "time", "timestamp"},
        "volume": {"出来高", "volume", "size"},
        "price": {"約定値", "price", "executionPrice"},
    }
    indices: dict[str, int] = {}
    for canonical, names in aliases.items():
        for index, header in enumerate(headers):
            if header in names:
                indices[canonical] = index
                break
    return indices if set(indices) == {"time", "volume", "price"} else None


def read_tick_sheet(workbook: Any, max_rows: int = 300) -> list[dict[str, Any]]:
    matrix = _used_matrix(workbook.Worksheets("ArkTicks"))
    if len(matrix) < 2:
        return []

    # MARKETSPEED II GUI registration can place the RssTickList formula in A2
    # and spill a second header row (e.g. row 3) before the live tick rows.
    # Locate the last valid header row near the top instead of assuming row 1.
    header_row_index: int | None = None
    indices: dict[str, int] | None = None
    for row_index, row in enumerate(matrix[:10]):
        candidate = _tick_header_indices(row)
        if candidate is not None:
            header_row_index = row_index
            indices = candidate
    if header_row_index is None or indices is None:
        raise RuntimeError("ArkTicks must contain a 時刻 / 出来高 / 約定値 header row in the first 10 rows")

    ticks: list[dict[str, Any]] = []
    start = header_row_index + 1
    for row in matrix[start : start + max_rows]:
        raw_time = row[indices["time"]] if indices["time"] < len(row) else None
        raw_volume = row[indices["volume"]] if indices["volume"] < len(row) else None
        raw_price = row[indices["price"]] if indices["price"] < len(row) else None
        if raw_time in (None, "") and raw_volume in (None, "") and raw_price in (None, ""):
            continue
        ticks.append({"time": _excel_time(raw_time), "volume": _scalar(raw_volume), "price": _scalar(raw_price)})
    return ticks


def capture_once(workbook: Any) -> dict[str, Any]:
    captured_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    market = read_market_sheet(workbook)
    ticks = read_tick_sheet(workbook)
    asks = []
    bids = []
    for level in range(1, 11):
        asks.append({"level": level, "price": market.get(f"ask{level}"), "size": market.get(f"askSize{level}")})
        bids.append({"level": level, "price": market.get(f"bid{level}"), "size": market.get(f"bidSize{level}")})
    payload = {
        "schemaVersion": 1,
        "phase": "58.p8.capture",
        "sourceMode": "MARKETSPEED_II_RSS_READ_ONLY",
        "capturedAt": captured_at,
        "symbol": str(market.get("symbol")),
        "tickOrder": "DESC",
        "market": market,
        "orderBook": {"asks": asks, "bids": bids},
        "ticks": ticks,
        "safety": PHASE58_CAPTURE_SAFETY,
    }
    return payload


def append_capture(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only MARKETSPEED II RSS Excel microstructure capture for Phase58 P8")
    parser.add_argument("--workbook", default=None, help="Optional open workbook name; otherwise auto-detect ArkMarket + ArkTicks")
    parser.add_argument("--output", default="data/phase58/microstructure-live.jsonl")
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--samples", type=int, default=120)
    args = parser.parse_args()
    if args.samples < 1:
        raise SystemExit("--samples must be >= 1")
    if args.interval_seconds < 0.2:
        raise SystemExit("--interval-seconds must be >= 0.2")

    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise SystemExit("pywin32 is required: python -m pip install -r tools/requirements-rss.txt") from exc

    excel = win32com.client.GetActiveObject("Excel.Application")
    workbook = _find_workbook(excel, args.workbook)
    output = Path(args.output)
    print(json.dumps({"status": "PHASE58_READ_ONLY_CAPTURE_START", "workbook": workbook.Name, "output": str(output), "samples": args.samples, "intervalSeconds": args.interval_seconds, "safety": PHASE58_CAPTURE_SAFETY}, ensure_ascii=False))
    captured = 0
    for index in range(args.samples):
        payload = capture_once(workbook)
        append_capture(output, payload)
        captured += 1
        if index + 1 < args.samples:
            time.sleep(args.interval_seconds)
    digest = sha256_file(output)
    print(json.dumps({"status": "PHASE58_READ_ONLY_CAPTURE_COMPLETE", "capturedSamples": captured, "output": str(output), "sha256": digest, "safety": PHASE58_CAPTURE_SAFETY}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())