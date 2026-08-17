from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase58_excel_5m_chart_export import (
    _complete_ohlcv_or_none,
    _find_workbook,
    _iso_timestamp,
    _matrix,
    _parse_date,
    _parse_time,
    _session_date_from_iso,
    _text,
    _validate_5m_timestamp_grid,
    _validate_populated_timeframe_cell,
    find_rss_chart_header,
)

UTC = timezone.utc
FROZEN_P24_COMBINED_UNIVERSE = ("7203.T", "6758.T", "9984.T", "8306.T", "8035.T")
MIN_BARS_PER_HISTORICAL_SESSION = 30

PHASE58_P14_SAFETY = {
    "phase": "58.p14.rsschart-history-pack",
    "mode": "MARKETSPEED_II_RSS_RSSCHART_MULTI_SYMBOL_READ_ONLY",
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


def _parse_all_rows(
    values: Any,
    *,
    symbol: str,
    captured_at: str,
) -> tuple[list[dict[str, Any]], int, int, int]:
    matrix = _matrix(values)
    header_row, columns = find_rss_chart_header(matrix)
    captured = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    if captured.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware")
    captured = captured.astimezone(UTC)
    rows: list[dict[str, Any]] = []
    skipped_unpopulated = 0
    explicit_5m_count = 0
    missing_timeframe_metadata_count = 0

    for excel_row_number, raw in enumerate(matrix[header_row + 1 :], start=header_row + 2):
        if not raw or all(_text(cell) == "" for cell in raw):
            continue
        try:
            day_value = raw[columns["日付"]]
            time_value = raw[columns["時刻"]]
        except IndexError as exc:
            raise ValueError(f"{symbol}: Excel row {excel_row_number}: row shorter than detected header") from exc
        if _text(day_value) == "" or _text(time_value) == "":
            continue

        try:
            ohlcv = _complete_ohlcv_or_none(raw, columns)
        except ValueError as exc:
            raise ValueError(f"{symbol}: Excel row {excel_row_number}: {exc}") from exc
        if ohlcv is None:
            skipped_unpopulated += 1
            continue

        has_explicit_5m = _validate_populated_timeframe_cell(
            raw,
            columns,
            error_prefix=f"{symbol}: Excel row {excel_row_number}: RssChart ",
        )
        if has_explicit_5m:
            explicit_5m_count += 1
        else:
            missing_timeframe_metadata_count += 1

        open_, high, low, close, volume = ohlcv
        try:
            timestamp = _iso_timestamp(_parse_date(day_value), _parse_time(time_value))
        except ValueError as exc:
            raise ValueError(f"{symbol}: Excel row {excel_row_number}: {exc}") from exc
        instant = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if instant > captured:
            raise ValueError(f"{symbol}: Excel row {excel_row_number}: RssChart timestamp is in the future: {timestamp}")
        if min(open_, high, low, close) <= 0:
            raise ValueError(f"{symbol}: Excel row {excel_row_number}: OHLC must be positive")
        if high < low or high < max(open_, close) or low > min(open_, close):
            raise ValueError(f"{symbol}: Excel row {excel_row_number}: invalid OHLC relationship")
        if volume < 0:
            raise ValueError(f"{symbol}: Excel row {excel_row_number}: volume must be non-negative")
        rows.append({
            "timestamp": timestamp,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })

    if not rows:
        raise ValueError(f"{symbol}: no RssChart OHLCV rows")
    rows.sort(key=lambda row: row["timestamp"])
    timestamps = [row["timestamp"] for row in rows]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError(f"{symbol}: duplicate RssChart timestamps")
    _validate_5m_timestamp_grid(rows, error_prefix=f"{symbol}: RssChart: ")
    return rows, skipped_unpopulated, explicit_5m_count, missing_timeframe_metadata_count


def build_history_pack_from_matrices(
    matrices_by_symbol: dict[str, Any],
    *,
    captured_at: str,
    as_of_session_date: str,
    expected_universe: tuple[str, ...] = FROZEN_P24_COMBINED_UNIVERSE,
    min_bars_per_session: int = MIN_BARS_PER_HISTORICAL_SESSION,
) -> dict[str, Any]:
    if not isinstance(as_of_session_date, str) or len(as_of_session_date) != 10:
        raise ValueError("as_of_session_date must be YYYY-MM-DD")
    expected = set(expected_universe)
    actual = set(matrices_by_symbol)
    if actual != expected:
        raise ValueError(f"frozen universe mismatch: expected={sorted(expected)} actual={sorted(actual)}")
    if min_bars_per_session < 1:
        raise ValueError("min_bars_per_session must be positive")

    sessions: list[dict[str, Any]] = []
    per_symbol: dict[str, Any] = {}
    dropped_current_or_future = 0
    dropped_short_sessions = 0
    skipped_unpopulated_total = 0
    explicit_5m_total = 0
    missing_timeframe_metadata_total = 0

    for symbol in expected_universe:
        rows, skipped_unpopulated, explicit_5m_count, missing_timeframe_metadata_count = _parse_all_rows(
            matrices_by_symbol[symbol], symbol=symbol, captured_at=captured_at
        )
        skipped_unpopulated_total += skipped_unpopulated
        explicit_5m_total += explicit_5m_count
        missing_timeframe_metadata_total += missing_timeframe_metadata_count
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            session_date = _session_date_from_iso(row["timestamp"])
            if session_date >= as_of_session_date:
                dropped_current_or_future += 1
                continue
            grouped[session_date].append(row)

        accepted_dates: list[str] = []
        accepted_bar_count = 0
        for session_date in sorted(grouped):
            bars = grouped[session_date]
            if len(bars) < min_bars_per_session:
                dropped_short_sessions += 1
                continue
            accepted_dates.append(session_date)
            accepted_bar_count += len(bars)
            sessions.append({
                "symbol": symbol,
                "sessionDate": session_date,
                "bars5m": bars,
                "source": "MARKETSPEED_II_RSS_RssChart",
                "timeframe": "5M",
                "fullyPriorToAsOfSession": True,
            })
        if not accepted_dates:
            raise ValueError(f"{symbol}: no eligible completed historical sessions before {as_of_session_date}")
        per_symbol[symbol] = {
            "sourceRowCount": len(rows),
            "skippedUnpopulatedOhlcvRowCount": skipped_unpopulated,
            "explicit5mTimeframeCellCount": explicit_5m_count,
            "missingTimeframeMetadataCount": missing_timeframe_metadata_count,
            "acceptedSessionCount": len(accepted_dates),
            "acceptedBarCount": accepted_bar_count,
            "firstAcceptedSession": accepted_dates[0],
            "lastAcceptedSession": accepted_dates[-1],
        }

    sessions.sort(key=lambda row: (row["sessionDate"], row["symbol"]))
    return {
        "schemaVersion": 1,
        "phase": "58.p14.rsschart-history-pack",
        "status": "PHASE58_FROZEN_UNIVERSE_5M_HISTORY_PACK_READY",
        "capturedAt": captured_at,
        "asOfSessionDate": as_of_session_date,
        "frozenUniverse": list(expected_universe),
        "minBarsPerHistoricalSession": min_bars_per_session,
        "sessionCount": len(sessions),
        "perSymbol": per_symbol,
        "skippedUnpopulatedOhlcvRowCount": skipped_unpopulated_total,
        "explicit5mTimeframeCellCount": explicit_5m_total,
        "missingTimeframeMetadataCount": missing_timeframe_metadata_total,
        "droppedCurrentOrFutureRowCount": dropped_current_or_future,
        "droppedShortSessionCount": dropped_short_sessions,
        "sessions": sessions,
        "methodology": {
            "source": "MARKETSPEED_II_RSS_RssChart",
            "timeframe": "5M",
            "excelReadOnly": True,
            "fullyUnpopulatedOhlcvRowsSkipped": True,
            "zeroVolumeNoPricePlaceholderRowsSkipped": True,
            "dashOnlyDisplayPlaceholdersTreatedAsMissing": True,
            "blankOrPlaceholderTimeframeMetadataAllowedWithGridProof": True,
            "explicitNon5mTimeframeRejected": True,
            "timestampGridValidatedAs5m": True,
            "partiallyPopulatedOhlcvRowsRejected": True,
            "currentSessionExcludedFromTrainingHistory": True,
            "onlySessionsStrictlyBeforeAsOfSession": True,
            "frozenP24CombinedUniverseRequired": True,
            "sameSessionRowsOnly": True,
            "outcomesNotReadFromExcel": True,
            "freshHoldoutConsumed": False,
        },
        "safety": PHASE58_P14_SAFETY,
    }


def _parse_sheet_map(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"--sheet-map must be SYMBOL=SHEET, got {value!r}")
        symbol, sheet = value.split("=", 1)
        symbol, sheet = symbol.strip(), sheet.strip()
        if not symbol or not sheet or symbol in result:
            raise ValueError(f"invalid or duplicate --sheet-map: {value!r}")
        result[symbol] = sheet
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="READ ONLY multi-symbol MARKETSPEED II RSS RssChart 5M history pack builder")
    parser.add_argument("--current-prefix", required=True, help="P12 current RssChart prefix JSON; its sessionDate becomes the strict history cutoff")
    parser.add_argument("--sheet-map", action="append", default=[], help="repeat SYMBOL=SHEET for each frozen-universe symbol")
    parser.add_argument("--workbook", default=None)
    parser.add_argument("--output", default="data/phase58/phase57-p21-history-sessions.json")
    args = parser.parse_args()

    prefix = json.loads(Path(args.current_prefix).read_text(encoding="utf-8"))
    as_of_session_date = str(prefix.get("sessionDate") or "")
    if prefix.get("latestBarClosed") is not True:
        raise SystemExit("current prefix is not completed-bar safe")
    sheet_map = _parse_sheet_map(args.sheet_map)
    if set(sheet_map) != set(FROZEN_P24_COMBINED_UNIVERSE):
        raise SystemExit(
            "sheet map must contain exactly frozen P24 combined universe: "
            + ",".join(FROZEN_P24_COMBINED_UNIVERSE)
        )

    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise SystemExit("pywin32 is required: py -m pip install -r tools/requirements-rss.txt") from exc

    excel = win32com.client.GetActiveObject("Excel.Application")
    workbook = _find_workbook(excel, args.workbook)
    matrices: dict[str, Any] = {}
    for symbol in FROZEN_P24_COMBINED_UNIVERSE:
        try:
            sheet = workbook.Worksheets(sheet_map[symbol])
        except Exception as exc:  # pragma: no cover - COM-specific
            raise SystemExit(f"worksheet not found for {symbol}: {sheet_map[symbol]}") from exc
        matrices[symbol] = sheet.UsedRange.Value

    captured_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = build_history_pack_from_matrices(
        matrices,
        captured_at=captured_at,
        as_of_session_date=as_of_session_date,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "output": str(output),
        "sha256": _sha256(output),
        "asOfSessionDate": payload["asOfSessionDate"],
        "sessionCount": payload["sessionCount"],
        "skippedUnpopulatedOhlcvRowCount": payload["skippedUnpopulatedOhlcvRowCount"],
        "explicit5mTimeframeCellCount": payload["explicit5mTimeframeCellCount"],
        "missingTimeframeMetadataCount": payload["missingTimeframeMetadataCount"],
        "perSymbol": payload["perSymbol"],
        "safety": PHASE58_P14_SAFETY,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
