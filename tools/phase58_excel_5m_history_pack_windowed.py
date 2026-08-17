from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase58_excel_5m_chart_export import _find_workbook
from phase58_excel_5m_history_pack import (
    FROZEN_P24_COMBINED_UNIVERSE,
    PHASE58_P14_SAFETY,
    build_history_pack_from_matrices,
)

UTC = timezone.utc
RSSCHART_MAX_DISPLAY_COUNT = 3000
RSSCHART_HEADER_ROW = 2
RSSCHART_FIRST_COLUMN = "A"
RSSCHART_LAST_COLUMN = "J"
RSSCHART_LAST_ROW = RSSCHART_HEADER_ROW + RSSCHART_MAX_DISPLAY_COUNT
RSSCHART_READ_RANGE = f"{RSSCHART_FIRST_COLUMN}1:{RSSCHART_LAST_COLUMN}{RSSCHART_LAST_ROW}"


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


def _read_rsschart_display_window(sheet: Any) -> Any:
    """Read the full configured RssChart display window without trusting UsedRange.

    MARKETSPEED II RSS can render dynamic RssChart values beyond Excel's stale
    UsedRange boundary. The workbook is configured with header row A2:J2 and a
    maximum display count of 3000, so A1:J3002 covers formula/status, headers, and
    every possible data row while remaining READ ONLY.
    """
    return sheet.Range(RSSCHART_READ_RANGE).Value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="READ ONLY full-window MARKETSPEED II RSS RssChart 5M history pack builder"
    )
    parser.add_argument(
        "--current-prefix",
        required=True,
        help="P12 current RssChart prefix JSON; its sessionDate becomes the strict history cutoff",
    )
    parser.add_argument(
        "--sheet-map",
        action="append",
        default=[],
        help="repeat SYMBOL=SHEET for each frozen-universe symbol",
    )
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
        matrices[symbol] = _read_rsschart_display_window(sheet)

    captured_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = build_history_pack_from_matrices(
        matrices,
        captured_at=captured_at,
        as_of_session_date=as_of_session_date,
    )
    payload.setdefault("methodology", {})["excelRangeReadMode"] = "FIXED_RSSCHART_3000_WINDOW"
    payload["methodology"]["excelReadRange"] = RSSCHART_READ_RANGE
    payload["methodology"]["excelUsedRangeTrusted"] = False

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "output": str(output),
        "sha256": _sha256(output),
        "asOfSessionDate": payload["asOfSessionDate"],
        "sessionCount": payload["sessionCount"],
        "excelReadRange": RSSCHART_READ_RANGE,
        "skippedUnpopulatedOhlcvRowCount": payload["skippedUnpopulatedOhlcvRowCount"],
        "explicit5mTimeframeCellCount": payload["explicit5mTimeframeCellCount"],
        "missingTimeframeMetadataCount": payload["missingTimeframeMetadataCount"],
        "perSymbol": payload["perSymbol"],
        "safety": PHASE58_P14_SAFETY,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
