from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any

from phase58_excel_dynamic_slot_capture import (
    SAFETY as CAPTURE_SAFETY,
    _formula_values,
    assert_dynamic_workbook_formula_surface,
    attest_size_units,
    formula_surface_attestation,
)
from phase58_excel_dynamic_slot_setup import (
    MARKET_FIELDS,
    SHEET_CONTROL,
    SHEET_MARKET,
    SHEET_TICKS,
)
from phase58_excel_microstructure_capture import _find_workbook

FALSE_KEYS = (
    "executionAllowed",
    "brokerWriteAllowed",
    "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed",
    "liveTradingAllowed",
    "paperTradingAllowed",
    "automaticPromotionAllowed",
    "productionUpdateAllowed",
)


def expected_rss_formula_counts(slot_count: int) -> dict[str, int]:
    if not isinstance(slot_count, int) or slot_count < 50:
        raise ValueError("slot_count must be an integer >= 50")
    market_items = sum(1 for _, item in MARKET_FIELDS if item)
    return {
        "RSSMARKET": slot_count * market_items,
        "RSSTICKLIST": slot_count,
    }


def observed_rss_formula_counts(workbook: Any) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for index in range(1, int(workbook.Worksheets.Count) + 1):
        sheet = workbook.Worksheets(index)
        for row in _formula_values(sheet):
            for value in row:
                text = str(value or "").upper().replace(" ", "")
                if "RSSMARKET(" in text:
                    counts["RSSMARKET"] += 1
                if "RSSTICKLIST(" in text:
                    counts["RSSTICKLIST"] += 1
    return dict(counts)


def _range_values(sheet: Any, address: str) -> list[Any]:
    values = sheet.Range(address).Value
    if not isinstance(values, (tuple, list)):
        return [values]
    rows = list(values)
    if rows and isinstance(rows[0], (tuple, list)):
        return [row[0] if row else None for row in rows]
    return rows


def validate_dynamic_workbook_layout(workbook: Any, slot_count: int) -> dict[str, Any]:
    required_sheets = [SHEET_CONTROL, SHEET_MARKET, SHEET_TICKS]
    sheet_names = [str(workbook.Worksheets(index).Name) for index in range(1, int(workbook.Worksheets.Count) + 1)]
    missing = [name for name in required_sheets if name not in sheet_names]
    if missing:
        raise RuntimeError(f"Lane M workbook missing required sheets: {','.join(missing)}")

    control = workbook.Worksheets(SHEET_CONTROL)
    expected_headers = ["slotId", "symbol", "assignedAt", "watchlistAsOf", "generation", "status"]
    headers = list(control.Range("A1:F1").Value[0])
    if [str(value or "").strip() for value in headers] != expected_headers:
        raise RuntimeError("ArkControl header contract mismatch")

    slot_ids = _range_values(control, f"A2:A{slot_count + 1}")
    expected_slot_ids = [f"SLOT{index:03d}" for index in range(1, slot_count + 1)]
    if [str(value or "").strip() for value in slot_ids] != expected_slot_ids:
        raise RuntimeError("ArkControl slot-id contract mismatch")

    assert_dynamic_workbook_formula_surface(workbook)
    observed = observed_rss_formula_counts(workbook)
    expected = expected_rss_formula_counts(slot_count)
    for function_name, expected_count in expected.items():
        if int(observed.get(function_name, 0)) != expected_count:
            raise RuntimeError(
                f"{function_name} formula count mismatch: expected {expected_count}, observed {int(observed.get(function_name, 0))}"
            )

    return {
        "sheetNames": sheet_names,
        "requiredSheets": required_sheets,
        "extraSheets": [name for name in sheet_names if name not in required_sheets],
        "slotCount": slot_count,
        "rssFormulaCounts": observed,
        "expectedRssFormulaCounts": expected,
        "runtimeWritableCells": f"{SHEET_CONTROL}!B2:B{slot_count + 1}",
        "formulaWriteAtRuntime": False,
        "symbolSwitchScope": "MARKET_DATA_QUERY_ONLY",
    }


def assert_safety() -> None:
    for key in FALSE_KEYS:
        if CAPTURE_SAFETY.get(key) is not False:
            raise RuntimeError(f"unsafe Lane M preflight safety flag: {key}")
    if CAPTURE_SAFETY.get("excelMarketDataQueryWriteAllowed") is not True:
        raise RuntimeError("Lane M market-data query write scope must remain explicit")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only preflight for the Phase57 dynamic MarketSpeed II Lane M Windows session"
    )
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--market-size-unit", required=True)
    parser.add_argument("--tick-size-unit", required=True)
    parser.add_argument("--slots", type=int, default=80)
    args = parser.parse_args()

    assert_safety()
    market_unit, tick_unit = attest_size_units(args.market_size_unit, args.tick_size_unit)
    if args.slots < 50:
        raise SystemExit("--slots must be >= 50")

    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise SystemExit("pywin32 is required: py -m pip install -r tools/requirements-rss.txt") from exc

    try:
        excel = win32com.client.GetActiveObject("Excel.Application")
    except Exception as exc:
        raise SystemExit("Excel must already be running with the Lane M workbook open") from exc

    workbook = _find_workbook(excel, args.workbook)
    layout = validate_dynamic_workbook_layout(workbook, args.slots)
    formula_attestation = formula_surface_attestation(workbook)

    result = {
        "status": "PHASE57_MSII_WINDOWS_DYNAMIC_PREFLIGHT_READY",
        "workbook": str(workbook.Name),
        "workbookFullName": str(getattr(workbook, "FullName", workbook.Name)),
        "marketSizeUnit": market_unit,
        "tickSizeUnit": tick_unit,
        "sizeUnitAttestation": {
            "explicit": True,
            "inferred": False,
            "operatorProvided": True,
        },
        "layout": layout,
        "formulaSurfaceAttestation": formula_attestation,
        "marketSpeedConnectivityProven": False,
        "marketSpeedConnectivityNote": "Formula/layout validation is complete; live RSS value readiness must still be proven on the Windows session.",
        "writesPerformed": False,
        "safety": CAPTURE_SAFETY,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
