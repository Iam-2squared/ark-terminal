from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SHEET_CONTROL = "ArkControl"
SHEET_MARKET = "ArkMarket"
SHEET_TICKS = "ArkTicks"
DEFAULT_SLOTS = 80
DEFAULT_TICK_ROWS = 100

SAFETY = {
    "phase": "58.p32.dynamic-slot-setup",
    "mode": "MARKETSPEED_II_MARKET_DATA_QUERY_SETUP_ONLY",
    "executionAllowed": False,
    "brokerWriteAllowed": False,
    "excelOrderWriteAllowed": False,
    "excelMarketDataQueryWriteAllowed": True,
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
ALLOWED_RSS_FUNCTIONS = ("RSSMARKET", "RSSTICKLIST")

MARKET_FIELDS: list[tuple[str, str | None]] = [
    ("slotId", None),
    ("symbol", None),
    ("observedSymbol", "銘柄コード"),
    ("bestAsk", "最良売気配値"),
    ("bestBid", "最良買気配値"),
    ("bestAskSize", "最良売気配数量"),
    ("bestBidSize", "最良買気配数量"),
    ("bestAskTime", "最良売気配詳細時刻"),
    ("bestBidTime", "最良買気配詳細時刻"),
]
for level in range(1, 11):
    MARKET_FIELDS.extend([
        (f"ask{level}", f"最良売気配値{level}"),
        (f"askSize{level}", f"最良売気配数量{level}"),
    ])
for level in range(1, 11):
    MARKET_FIELDS.extend([
        (f"bid{level}", f"最良買気配値{level}"),
        (f"bidSize{level}", f"最良買気配数量{level}"),
    ])


def market_formula(control_row: int, item: str) -> str:
    return f'=IF({SHEET_CONTROL}!$B${control_row}="","",RssMarket({SHEET_CONTROL}!$B${control_row},"{item}"))'


def tick_formula(control_row: int, display_rows: int) -> str:
    if display_rows < 1:
        raise ValueError("display_rows must be >= 1")
    return f'=IF({SHEET_CONTROL}!$B${control_row}="","",RssTickList(,{SHEET_CONTROL}!$B${control_row},{display_rows}))'


def assert_formula_is_market_data_only(formula: str) -> None:
    text = str(formula or "").upper().replace(" ", "")
    forbidden = next((token for token in FORBIDDEN_FORMULA_TOKENS if token in text), None)
    if forbidden:
        raise ValueError(f"forbidden RSS order formula: {forbidden}")
    if "RSS" in text and not any(name in text for name in ALLOWED_RSS_FUNCTIONS):
        raise ValueError(f"unapproved RSS function in dynamic workbook formula: {formula}")


def build_workbook_manifest(*, workbook_path: str, slot_count: int, tick_rows: int) -> dict[str, Any]:
    if not isinstance(slot_count, int) or slot_count < 50:
        raise ValueError("slot_count must be an integer >= 50")
    if not isinstance(tick_rows, int) or tick_rows < 20:
        raise ValueError("tick_rows must be an integer >= 20")
    formulas = []
    for slot in range(slot_count):
        control_row = slot + 2
        formulas.extend(market_formula(control_row, item) for _, item in MARKET_FIELDS if item)
        formulas.append(tick_formula(control_row, tick_rows))
    for formula in formulas:
        assert_formula_is_market_data_only(formula)
    return {
        "schemaVersion": 1,
        "phase": "58.p32.dynamic-slot-setup",
        "workbook": str(Path(workbook_path)),
        "slotCount": slot_count,
        "tickRowsPerSlot": tick_rows,
        "sheets": [SHEET_CONTROL, SHEET_MARKET, SHEET_TICKS],
        "runtimeWritableCells": f"{SHEET_CONTROL}!B2:B{slot_count + 1}",
        "formulaWriteAtRuntime": False,
        "symbolSwitchAtRuntime": True,
        "symbolSwitchScope": "MARKET_DATA_QUERY_ONLY",
        "allowedRssFunctions": list(ALLOWED_RSS_FUNCTIONS),
        "forbiddenOrderFunctions": list(FORBIDDEN_FORMULA_TOKENS),
        "safety": SAFETY,
    }


def _set_formula(cell: Any, formula: str) -> None:
    assert_formula_is_market_data_only(formula)
    try:
        cell.Formula2 = formula
    except Exception:
        cell.Formula = formula


def _delete_extra_sheets(workbook: Any) -> None:
    workbook.Application.DisplayAlerts = False
    while workbook.Worksheets.Count > 1:
        workbook.Worksheets(workbook.Worksheets.Count).Delete()


def setup_workbook(excel: Any, workbook_path: Path, *, slot_count: int, tick_rows: int, overwrite: bool) -> dict[str, Any]:
    manifest = build_workbook_manifest(workbook_path=str(workbook_path), slot_count=slot_count, tick_rows=tick_rows)
    if workbook_path.exists():
        if not overwrite:
            raise FileExistsError(f"workbook already exists: {workbook_path}; pass --overwrite for a fresh Lane M workbook")
        workbook_path.unlink()
    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = excel.Workbooks.Add()
    _delete_extra_sheets(workbook)
    control = workbook.Worksheets(1)
    control.Name = SHEET_CONTROL
    market = workbook.Worksheets.Add(After=control)
    market.Name = SHEET_MARKET
    ticks = workbook.Worksheets.Add(After=market)
    ticks.Name = SHEET_TICKS

    control_headers = ["slotId", "symbol", "assignedAt", "watchlistAsOf", "generation", "status"]
    for col, header in enumerate(control_headers, 1):
        control.Cells(1, col).Value = header
    for slot in range(slot_count):
        row = slot + 2
        control.Cells(row, 1).Value = f"SLOT{slot + 1:03d}"
        control.Cells(row, 6).Value = "EMPTY"

    for col, (header, _) in enumerate(MARKET_FIELDS, 1):
        market.Cells(1, col).Value = header
    for slot in range(slot_count):
        row = slot + 2
        control_row = row
        market.Cells(row, 1).Value = f"SLOT{slot + 1:03d}"
        _set_formula(market.Cells(row, 2), f'=IF({SHEET_CONTROL}!$B${control_row}="","",{SHEET_CONTROL}!$B${control_row})')
        for col, (_, item) in enumerate(MARKET_FIELDS[2:], 3):
            if item:
                _set_formula(market.Cells(row, col), market_formula(control_row, item))

    block_width = 4
    for slot in range(slot_count):
        start_col = slot * block_width + 1
        ticks.Cells(1, start_col).Value = f"SLOT{slot + 1:03d}"
        ticks.Cells(1, start_col + 1).Value = "symbol"
        _set_formula(ticks.Cells(1, start_col + 2), f'=IF({SHEET_CONTROL}!$B${slot + 2}="","",{SHEET_CONTROL}!$B${slot + 2})')
        _set_formula(ticks.Cells(2, start_col), tick_formula(slot + 2, tick_rows))

    control.Columns("A:F").ColumnWidth = 20
    market.Rows(1).Font.Bold = True
    control.Rows(1).Font.Bold = True
    ticks.Rows(1).Font.Bold = True
    workbook.SaveAs(str(workbook_path.resolve()), FileFormat=51)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a fresh dynamic-slot MarketSpeed II Lane M workbook")
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--slots", type=int, default=DEFAULT_SLOTS)
    parser.add_argument("--tick-rows", type=int, default=DEFAULT_TICK_ROWS)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args()

    manifest = build_workbook_manifest(workbook_path=args.workbook, slot_count=args.slots, tick_rows=args.tick_rows)
    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise SystemExit("pywin32 is required: py -m pip install -r tools/requirements-rss.txt") from exc
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = True
    try:
        manifest = setup_workbook(excel, Path(args.workbook), slot_count=args.slots, tick_rows=args.tick_rows, overwrite=args.overwrite)
        if args.manifest:
            output = Path(args.manifest)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PHASE58_MSII_DYNAMIC_WORKBOOK_READY", **manifest}, ensure_ascii=False))
    except Exception:
        excel.Quit()
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
