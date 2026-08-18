from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import phase58_excel_5m_chart_export as base


def _explicit_timeframe(row: list[Any], columns: dict[str, int]) -> str | None:
    index = columns.get("足種")
    if index is None or index >= len(row):
        return None
    value = row[index]
    if base._is_rss_display_placeholder(value):
        return None
    return base._text(value)


def collapse_exact_duplicate_timestamp_rows(values: Any) -> tuple[list[list[Any]], int]:
    """Collapse only data-equivalent duplicate populated RssChart timestamps.

    MARKETSPEED II RSS can leave duplicate rows in the spill range after refreshes.
    We may safely collapse a duplicate only when its parsed OHLCV is exactly the same.
    Any conflicting duplicate remains a hard blocker so point-in-time data are never
    guessed, averaged, or selected post hoc.
    """
    matrix = base._matrix(values)
    header_row, columns = base.find_rss_chart_header(matrix)
    cleaned = [list(row) for row in matrix[: header_row + 1]]
    seen: dict[str, tuple[tuple[float, float, float, float, float], str | None, int]] = {}
    collapsed = 0

    for raw_value in matrix[header_row + 1 :]:
        raw = list(raw_value)
        if not raw or all(base._text(cell) == "" for cell in raw):
            cleaned.append(raw)
            continue
        try:
            day_value = raw[columns["日付"]]
            time_value = raw[columns["時刻"]]
        except IndexError:
            cleaned.append(raw)
            continue
        if base._text(day_value) == "" or base._text(time_value) == "":
            cleaned.append(raw)
            continue

        ohlcv = base._complete_ohlcv_or_none(raw, columns)
        if ohlcv is None:
            cleaned.append(raw)
            continue
        timestamp = base._iso_timestamp(base._parse_date(day_value), base._parse_time(time_value))
        timeframe = _explicit_timeframe(raw, columns)
        previous = seen.get(timestamp)
        if previous is None:
            cleaned.append(raw)
            seen[timestamp] = (ohlcv, timeframe, len(cleaned) - 1)
            continue

        previous_ohlcv, previous_timeframe, output_index = previous
        if previous_ohlcv != ohlcv:
            raise ValueError(f"conflicting duplicate RssChart timestamp detected: {timestamp}")
        if previous_timeframe and timeframe and previous_timeframe != timeframe:
            raise ValueError(f"conflicting duplicate RssChart timeframe detected: {timestamp}")

        # Prefer the duplicate carrying explicit timeframe metadata when the first row
        # has none, while keeping the same data-equivalent OHLCV/timestamp evidence.
        if previous_timeframe is None and timeframe is not None:
            cleaned[output_index] = raw
            seen[timestamp] = (ohlcv, timeframe, output_index)
        collapsed += 1

    return cleaned, collapsed


def main() -> int:
    parser = argparse.ArgumentParser(description="READ ONLY exact-duplicate-safe MARKETSPEED II RSS RssChart 5M exporter")
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
    workbook = base._find_workbook(excel, args.workbook)
    try:
        sheet = workbook.Worksheets(args.sheet)
    except Exception as exc:  # pragma: no cover - COM-specific
        raise SystemExit(f"worksheet not found: {args.sheet}") from exc

    used = sheet.UsedRange.Value
    cleaned, collapsed = collapse_exact_duplicate_timestamp_rows(used)
    captured_at = datetime.now(base.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = base.parse_rss_chart_matrix(
        cleaned,
        symbol=args.symbol,
        captured_at=captured_at,
        session_date=args.session_date,
        drop_newest_row_for_closure_safety=True,
    )
    payload["exactDuplicateTimestampRowsCollapsed"] = collapsed
    payload["methodology"] = {
        **payload["methodology"],
        "exactDuplicateTimestampRowsMayCollapseOnlyWhenOhlcvIdentical": True,
        "conflictingDuplicateTimestampRejected": True,
        "duplicateRowsNeverAveragedOrPostHocSelected": True,
    }
    base._write_json(Path(args.output), payload)
    print(json.dumps({
        "status": payload["status"],
        "output": args.output,
        "symbol": payload["symbol"],
        "sessionDate": payload["sessionDate"],
        "closedBarCount": payload["closedBarCount"],
        "exactDuplicateTimestampRowsCollapsed": collapsed,
        "skippedUnpopulatedOhlcvRowCount": payload["skippedUnpopulatedOhlcvRowCount"],
        "explicit5mTimeframeCellCount": payload["explicit5mTimeframeCellCount"],
        "missingTimeframeMetadataCount": payload["missingTimeframeMetadataCount"],
        "droppedNewestTimestamp": payload["droppedNewestTimestamp"],
        "safety": base.PHASE58_5M_EXPORT_SAFETY,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
