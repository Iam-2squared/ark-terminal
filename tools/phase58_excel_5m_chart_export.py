from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from phase58_excel_microstructure_capture import _find_workbook

# Japan Standard Time is UTC+09:00 for the modern market-data period covered here.
# A fixed offset avoids Python's optional tzdata dependency on Windows.
JST = timezone(timedelta(hours=9), name="JST")
UTC = timezone.utc

PHASE58_5M_EXPORT_SAFETY = {
    "phase": "58.p12.rsschart-5m-export",
    "mode": "MARKETSPEED_II_RSS_RSSCHART_READ_ONLY",
    "researchOnly": True,
    "executionAllowed": False,
    "brokerWriteAllowed": False,
    "excelOrderWriteAllowed": False,
    "rssOrderFunctionAllowed": False,
    "liveTradingAllowed": False,
    "paperTradingAllowed": False,
    "automaticPromotionAllowed": False,
    "productionUpdateAllowed": False,
    "overnightHoldingAllowed": False,
    "transmitted": False,
    "freshHoldoutConsumed": False,
}

REQUIRED_HEADERS = ("日付", "時刻", "始値", "高値", "安値", "終値", "出来高")
OPTIONAL_HEADERS = ("銘柄名称", "市場名称", "足種")
OHLCV_HEADERS = ("始値", "高値", "安値", "終値", "出来高")


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _finite(value: Any) -> bool:
    if value is None or value == "":
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _matrix(values: Any) -> list[list[Any]]:
    if values is None:
        return []
    if isinstance(values, tuple):
        rows = list(values)
    elif isinstance(values, list):
        rows = values
    else:
        return [[values]]
    out: list[list[Any]] = []
    for row in rows:
        if isinstance(row, tuple):
            out.append(list(row))
        elif isinstance(row, list):
            out.append(row)
        else:
            out.append([row])
    return out


def find_rss_chart_header(matrix: list[list[Any]], max_rows: int = 25) -> tuple[int, dict[str, int]]:
    for row_index, row in enumerate(matrix[:max_rows]):
        mapping = {_text(value): index for index, value in enumerate(row) if _text(value)}
        if all(header in mapping for header in REQUIRED_HEADERS):
            return row_index, {
                header: mapping[header]
                for header in (*REQUIRED_HEADERS, *OPTIONAL_HEADERS)
                if header in mapping
            }
    raise ValueError("RssChart header row not found; required headers: " + ",".join(REQUIRED_HEADERS))


def _excel_serial_to_date(value: float) -> date:
    return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if _finite(value) and not isinstance(value, str):
        return _excel_serial_to_date(float(value))
    text = _text(value)
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"invalid RssChart date: {value!r}")


def _parse_time(value: Any) -> time:
    if isinstance(value, datetime):
        return value.time().replace(tzinfo=None)
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    if _finite(value) and not isinstance(value, str):
        fraction = float(value) % 1.0
        total_seconds = int(round(fraction * 86400)) % 86400
        return time(total_seconds // 3600, (total_seconds % 3600) // 60, total_seconds % 60)
    text = _text(value)
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            pass
    raise ValueError(f"invalid RssChart time: {value!r}")


def _iso_timestamp(day: date, clock: time) -> str:
    local = datetime.combine(day, clock, tzinfo=JST)
    return local.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _session_date_from_iso(timestamp: str) -> str:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(JST).date().isoformat()


def _numeric(value: Any, field: str) -> float:
    if not _finite(value):
        raise ValueError(f"RssChart {field} must be finite: {value!r}")
    return float(value)


def _complete_ohlcv_or_none(raw: list[Any], columns: dict[str, int]) -> tuple[float, float, float, float, float] | None:
    """Return a complete OHLCV tuple, skip unpopulated RSS rows, fail on ambiguous partial rows.

    MARKETSPEED II RssChart can expose timestamped/preallocated grid rows where all
    four OHLC cells are blank while 出来高 is either blank or numeric zero. Those
    rows contain no price bar and are safe to ignore. If any OHLC value is present,
    all OHLCV fields must be present and finite. A positive/non-zero volume with all
    OHLC blank is also rejected fail-closed rather than silently discarded.
    """
    try:
        values = [raw[columns[header]] for header in OHLCV_HEADERS]
    except IndexError as exc:
        raise ValueError("RssChart row shorter than detected OHLCV columns") from exc

    ohlc_values = values[:4]
    volume_value = values[4]
    ohlc_blank = [_text(value) == "" for value in ohlc_values]
    volume_blank = _text(volume_value) == ""
    volume_zero = _finite(volume_value) and float(volume_value) == 0.0

    if all(ohlc_blank) and (volume_blank or volume_zero):
        return None

    blank = [*ohlc_blank, volume_blank]
    if any(blank):
        missing = [header for header, is_blank in zip(OHLCV_HEADERS, blank) if is_blank]
        raise ValueError("RssChart partially populated OHLCV row; missing: " + ",".join(missing))

    return tuple(_numeric(value, header) for value, header in zip(values, OHLCV_HEADERS))  # type: ignore[return-value]


def parse_rss_chart_matrix(
    values: Any,
    *,
    symbol: str,
    captured_at: str,
    session_date: str | None = None,
    drop_newest_row_for_closure_safety: bool = True,
) -> dict[str, Any]:
    matrix = _matrix(values)
    header_row, columns = find_rss_chart_header(matrix)
    symbol = _text(symbol)
    if not symbol:
        raise ValueError("symbol is required")

    captured = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    if captured.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware ISO timestamp")
    captured = captured.astimezone(UTC)

    rows: list[dict[str, Any]] = []
    skipped_unpopulated = 0
    for raw in matrix[header_row + 1 :]:
        if not raw or all(_text(cell) == "" for cell in raw):
            continue
        try:
            day_value = raw[columns["日付"]]
            time_value = raw[columns["時刻"]]
        except IndexError as exc:
            raise ValueError("RssChart row shorter than detected header") from exc
        if _text(day_value) == "" or _text(time_value) == "":
            continue

        if "足種" in columns:
            tf = _text(raw[columns["足種"]]) if columns["足種"] < len(raw) else ""
            if tf and tf != "5M":
                raise ValueError(f"RssChart timeframe must be 5M, got {tf!r}")

        ohlcv = _complete_ohlcv_or_none(raw, columns)
        if ohlcv is None:
            skipped_unpopulated += 1
            continue
        open_, high, low, close, volume = ohlcv

        day = _parse_date(day_value)
        clock = _parse_time(time_value)
        timestamp = _iso_timestamp(day, clock)
        if datetime.fromisoformat(timestamp.replace("Z", "+00:00")) > captured:
            raise ValueError(f"RssChart timestamp is in the future relative to capture: {timestamp}")
        if min(open_, high, low, close) <= 0:
            raise ValueError("RssChart OHLC values must be positive")
        if high < low or high < max(open_, close) or low > min(open_, close):
            raise ValueError("RssChart OHLC relationship is invalid")
        if volume < 0:
            raise ValueError("RssChart volume must be non-negative")

        rows.append({
            "timestamp": timestamp,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })

    if not rows:
        raise ValueError("RssChart produced no OHLCV rows")
    rows.sort(key=lambda row: row["timestamp"])
    timestamps = [row["timestamp"] for row in rows]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("duplicate RssChart timestamps detected")

    target_session = session_date or _session_date_from_iso(rows[-1]["timestamp"])
    if not isinstance(target_session, str) or len(target_session) != 10:
        raise ValueError("session_date must be YYYY-MM-DD")
    same_session = [row for row in rows if _session_date_from_iso(row["timestamp"]) == target_session]
    if not same_session:
        raise ValueError(f"no RssChart rows found for JST session {target_session}")

    dropped_newest = None
    closed_rows = same_session
    if drop_newest_row_for_closure_safety:
        if len(same_session) < 2:
            raise ValueError("need at least two same-session RssChart rows before conservative newest-row drop")
        dropped_newest = same_session[-1]["timestamp"]
        closed_rows = same_session[:-1]
    if len(closed_rows) < 6:
        raise ValueError("need at least six completed same-session 5m bars for Phase57 P21 features")

    return {
        "schemaVersion": 1,
        "phase": "58.p12.rsschart-5m-export",
        "status": "PHASE58_RSSCHART_5M_PREFIX_READY",
        "symbol": symbol,
        "sessionDate": target_session,
        "capturedAt": captured.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "latestBarClosed": True,
        "bars5m": closed_rows,
        "sourceBarCount": len(rows),
        "sameSessionSourceBarCount": len(same_session),
        "closedBarCount": len(closed_rows),
        "skippedUnpopulatedOhlcvRowCount": skipped_unpopulated,
        "droppedNewestTimestamp": dropped_newest,
        "methodology": {
            "source": "MARKETSPEED_II_RSS_RssChart",
            "timeframe": "5M",
            "headerDetectedByLabels": True,
            "fullyUnpopulatedOhlcvRowsSkipped": True,
            "zeroVolumeNoPricePlaceholderRowsSkipped": True,
            "partiallyPopulatedOhlcvRowsRejected": True,
            "newestVisibleRowDroppedForClosureSafety": bool(drop_newest_row_for_closure_safety),
            "currentOrFutureOutcomeUsed": False,
            "sameSessionOnly": True,
            "excelReadOnly": True,
            "freshHoldoutConsumed": False,
        },
        "safety": PHASE58_5M_EXPORT_SAFETY,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="READ ONLY MARKETSPEED II RSS RssChart 5M exporter for Phase57 prospective features")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--workbook", default=None)
    parser.add_argument("--sheet", default="ArkIntraday")
    parser.add_argument("--session-date", default=None)
    parser.add_argument("--output", default="data/phase58/phase57-live-5m-prefix.json")
    args = parser.parse_args()

    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise SystemExit("pywin32 is required: py -m pip install -r tools/requirements-rss.txt") from exc

    excel = win32com.client.GetActiveObject("Excel.Application")
    workbook = _find_workbook(excel, args.workbook)
    try:
        sheet = workbook.Worksheets(args.sheet)
    except Exception as exc:  # pragma: no cover - COM-specific
        raise SystemExit(f"worksheet not found: {args.sheet}") from exc

    used = sheet.UsedRange.Value
    captured_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = parse_rss_chart_matrix(
        used,
        symbol=args.symbol,
        captured_at=captured_at,
        session_date=args.session_date,
        drop_newest_row_for_closure_safety=True,
    )
    _write_json(Path(args.output), payload)
    print(json.dumps({
        "status": payload["status"],
        "output": args.output,
        "symbol": payload["symbol"],
        "sessionDate": payload["sessionDate"],
        "closedBarCount": payload["closedBarCount"],
        "skippedUnpopulatedOhlcvRowCount": payload["skippedUnpopulatedOhlcvRowCount"],
        "droppedNewestTimestamp": payload["droppedNewestTimestamp"],
        "safety": PHASE58_5M_EXPORT_SAFETY,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
