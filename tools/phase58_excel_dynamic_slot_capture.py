from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase58_excel_microstructure_capture import _excel_time, _find_workbook, _scalar, _tick_header_indices, _used_matrix
from phase58_excel_dynamic_slot_setup import (
    ALLOWED_RSS_FUNCTIONS,
    FORBIDDEN_FORMULA_TOKENS,
    MARKET_FIELDS,
    SHEET_CONTROL,
    SHEET_MARKET,
    SHEET_TICKS,
)

SAFETY = {
    "phase": "58.p32.dynamic-slot-capture",
    "mode": "MARKETSPEED_II_RSS_DYNAMIC_MARKET_DATA_QUERY_ONLY",
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

ATTESTED_SIZE_UNIT = "SHARES"


def attest_size_units(market_size_unit: Any, tick_size_unit: Any) -> tuple[str, str]:
    """Require an explicit operator attestation; never infer MarketSpeed quantity units."""
    market = str(market_size_unit or "").strip().upper()
    ticks = str(tick_size_unit or "").strip().upper()
    if not market or not ticks:
        raise ValueError("explicit --market-size-unit and --tick-size-unit attestations are required")
    if market != ATTESTED_SIZE_UNIT or ticks != ATTESTED_SIZE_UNIT:
        raise ValueError("MarketSpeed quantity units must be explicitly attested as SHARES")
    return market, ticks


def normalize_symbol(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    if raw.endswith(".T"):
        return raw
    if raw.replace(".0", "").isdigit():
        return f"{int(float(raw))}.T"
    return raw


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


def formula_surface_attestation(workbook: Any) -> dict[str, Any]:
    """Hash the verified formula surface so capture rows can prove the workbook read path."""
    normalized: list[dict[str, Any]] = []
    for index in range(1, int(workbook.Worksheets.Count) + 1):
        sheet = workbook.Worksheets(index)
        rows = _formula_values(sheet)
        normalized.append({"sheet": str(sheet.Name), "formulaGrid": rows})
    canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return {
        "algorithm": "SHA256",
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "sheetNames": [row["sheet"] for row in normalized],
        "allowedRssFunctions": list(ALLOWED_RSS_FUNCTIONS),
        "verifiedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }


def assert_dynamic_workbook_formula_surface(workbook: Any) -> None:
    for index in range(1, int(workbook.Worksheets.Count) + 1):
        sheet = workbook.Worksheets(index)
        for row in _formula_values(sheet):
            for value in row:
                text = str(value or "").upper().replace(" ", "")
                forbidden = next((token for token in FORBIDDEN_FORMULA_TOKENS if token in text), None)
                if forbidden:
                    raise RuntimeError(f"forbidden RSS order-capable formula in {sheet.Name}: {forbidden}")
                if "RSS" in text and not any(name in text for name in ALLOWED_RSS_FUNCTIONS):
                    raise RuntimeError(f"unapproved RSS function in {sheet.Name}: {value}")


def _normalized_unique_symbols(values: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        symbol = normalize_symbol(raw)
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        out.append(symbol)
    return out


def validate_watchlist(payload: Any, slot_count: int) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("complete") is not True:
        raise ValueError("dynamic watchlist must be complete")
    if payload.get("status") != "PHASE57_MSII_DYNAMIC_WATCHLIST_READY":
        raise ValueError("unexpected dynamic watchlist status")
    if payload.get("futureOutcomeUsed") is not False:
        raise ValueError("dynamic watchlist futureOutcomeUsed must be false")

    symbols = _normalized_unique_symbols(payload.get("assignedSymbols"))
    v1_symbols = _normalized_unique_symbols(payload.get("currentV1Symbols"))
    v2_symbols = _normalized_unique_symbols(payload.get("currentV2Symbols"))
    pinned_symbols = _normalized_unique_symbols(payload.get("pinnedSymbols"))

    if len(symbols) > slot_count:
        raise ValueError("dynamic watchlist exceeds workbook slot capacity")
    if not 20 <= len(v1_symbols) <= 50:
        raise ValueError("dynamic watchlist V1 selection outside frozen readiness range")
    if not 15 <= len(v2_symbols) <= 30:
        raise ValueError("dynamic watchlist V2 selection outside frozen readiness range")
    if not set(v2_symbols).issubset(set(v1_symbols)):
        raise ValueError("dynamic watchlist V2 must remain inside the frozen V1 base universe")
    hard_required = set(v1_symbols) | set(pinned_symbols)
    if not hard_required.issubset(set(symbols)):
        raise ValueError("dynamic watchlist assignedSymbols dropped a hard-required V1 or Lane M inventory symbol")

    out = dict(payload)
    out["assignedSymbols"] = symbols
    out["currentV1Symbols"] = v1_symbols
    out["currentV2Symbols"] = v2_symbols
    out["pinnedSymbols"] = pinned_symbols
    return out


def plan_slot_assignments(current_symbols: list[str], desired_symbols: list[str], slot_count: int) -> list[str]:
    if len(current_symbols) != slot_count:
        raise ValueError("current slot vector length mismatch")
    desired = []
    seen = set()
    for raw in desired_symbols:
        symbol = normalize_symbol(raw)
        if symbol and symbol not in seen:
            desired.append(symbol)
            seen.add(symbol)
    if len(desired) > slot_count:
        raise ValueError("desired symbols exceed slot capacity")
    desired_set = set(desired)
    next_slots = [normalize_symbol(value) if normalize_symbol(value) in desired_set else "" for value in current_symbols]
    already = {symbol for symbol in next_slots if symbol}
    pending = [symbol for symbol in desired if symbol not in already]
    empty_indices = [index for index, symbol in enumerate(next_slots) if not symbol]
    for index, symbol in zip(empty_indices, pending):
        next_slots[index] = symbol
    if {symbol for symbol in next_slots if symbol} != desired_set:
        raise RuntimeError("slot assignment failed to cover desired symbols")
    return next_slots


def read_control_symbols(control_sheet: Any, slot_count: int) -> list[str]:
    values = control_sheet.Range(f"B2:B{slot_count + 1}").Value
    if slot_count == 1 and not isinstance(values, (tuple, list)):
        return [normalize_symbol(values)]
    return [normalize_symbol(row[0] if isinstance(row, (tuple, list)) else row) for row in values]


def apply_watchlist(workbook: Any, watchlist: dict[str, Any], *, slot_count: int, generation: int) -> tuple[list[str], bool]:
    control = workbook.Worksheets(SHEET_CONTROL)
    current = read_control_symbols(control, slot_count)
    desired = list(watchlist["assignedSymbols"])
    planned = plan_slot_assignments(current, desired, slot_count)
    changed = planned != current
    if not changed:
        return planned, False
    assigned_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    watchlist_as_of = str(watchlist.get("observedAt") or "")
    symbols_matrix = tuple((symbol.replace(".T", ""),) if symbol else ("",) for symbol in planned)
    control.Range(f"B2:B{slot_count + 1}").Value = symbols_matrix
    control.Range(f"C2:C{slot_count + 1}").Value = tuple((assigned_at if symbol else "",) for symbol in planned)
    control.Range(f"D2:D{slot_count + 1}").Value = tuple((watchlist_as_of if symbol else "",) for symbol in planned)
    control.Range(f"E2:E{slot_count + 1}").Value = tuple((generation if symbol else "",) for symbol in planned)
    control.Range(f"F2:F{slot_count + 1}").Value = tuple(("ACTIVE" if symbol else "EMPTY",) for symbol in planned)
    workbook.Application.CalculateFull()
    return planned, True


def _row_dict(headers: list[Any], values: list[Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for index, header in enumerate(headers):
        key = str(header or "").strip()
        if key:
            out[key] = _scalar(values[index] if index < len(values) else None)
    return out


def _extract_ticks(tick_matrix: list[list[Any]], start_col_zero: int, max_rows: int) -> list[dict[str, Any]]:
    block = []
    for row in tick_matrix[: max_rows + 12]:
        block.append([row[start_col_zero + offset] if start_col_zero + offset < len(row) else None for offset in range(3)])
    header_index = None
    indices = None
    for row_index, row in enumerate(block[:10]):
        candidate = _tick_header_indices(row)
        if candidate is not None:
            header_index = row_index
            indices = candidate
    if header_index is None or indices is None:
        return []
    ticks: list[dict[str, Any]] = []
    for row in block[header_index + 1 : header_index + 1 + max_rows]:
        raw_time = row[indices["time"]] if indices["time"] < len(row) else None
        raw_volume = row[indices["volume"]] if indices["volume"] < len(row) else None
        raw_price = row[indices["price"]] if indices["price"] < len(row) else None
        if raw_time in (None, "") and raw_volume in (None, "") and raw_price in (None, ""):
            continue
        ticks.append({"time": _excel_time(raw_time), "volume": _scalar(raw_volume), "price": _scalar(raw_price)})
    return ticks


def heartbeat_row(*, watchlist_as_of: str | None = None, market_size_unit: Any, tick_size_unit: Any, formula_attestation: dict[str, Any]) -> dict[str, Any]:
    market_unit, tick_unit = attest_size_units(market_size_unit, tick_size_unit)
    return {
        "schemaVersion": 2,
        "phase": "58.p32.dynamic-slot-capture",
        "recordType": "SESSION_HEARTBEAT",
        "sourceMode": "MARKETSPEED_II_RSS_READ_ONLY",
        "capturedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "symbol": None,
        "watchlistAsOf": watchlist_as_of,
        "sourceFunctions": ["RssMarket", "RssTickList"],
        "marketSizeUnit": market_unit,
        "tickSizeUnit": tick_unit,
        "sizeUnitAttestation": {
            "explicit": True,
            "inferred": False,
            "operatorProvided": True,
        },
        "formulaSurfaceAttestation": formula_attestation,
        "methodology": {
            "dynamicSlotMode": True,
            "excelFormulaWritePerformed": False,
            "symbolSwitchWritePerformed": False,
            "symbolSwitchScope": "MARKET_DATA_QUERY_ONLY",
            "excelOrderWritePerformed": False,
            "pointInTimeOnly": True,
            "futureOutcomeUsed": False,
        },
        "safety": SAFETY,
    }


def capture_batch(
    workbook: Any,
    assignments: list[str],
    watchlist: dict[str, Any],
    *,
    tick_rows: int,
    generation: int,
    market_size_unit: Any,
    tick_size_unit: Any,
    formula_attestation: dict[str, Any],
) -> list[dict[str, Any]]:
    market_unit, tick_unit = attest_size_units(market_size_unit, tick_size_unit)
    captured_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    market_matrix = _used_matrix(workbook.Worksheets(SHEET_MARKET))
    tick_matrix = _used_matrix(workbook.Worksheets(SHEET_TICKS))
    if not market_matrix:
        raise RuntimeError("ArkMarket is empty")
    headers = list(market_matrix[0])
    rows: list[dict[str, Any]] = []
    for slot_index, symbol in enumerate(assignments):
        if not symbol:
            continue
        row_index = slot_index + 1
        market_row = _row_dict(headers, list(market_matrix[row_index]) if row_index < len(market_matrix) else [])
        observed = normalize_symbol(market_row.get("observedSymbol"))
        ready = observed == normalize_symbol(symbol)
        market = market_row if ready else {
            "slotId": f"SLOT{slot_index + 1:03d}",
            "symbol": symbol,
            "observedSymbol": observed or None,
            "bestAsk": None,
            "bestBid": None,
            "bestAskSize": None,
            "bestBidSize": None,
            "bestAskTime": None,
            "bestBidTime": None,
        }
        ticks = _extract_ticks(tick_matrix, slot_index * 4, tick_rows) if ready else []
        rows.append({
            "schemaVersion": 2,
            "phase": "58.p32.dynamic-slot-capture",
            "recordType": "MARKET_OBSERVATION",
            "sourceMode": "MARKETSPEED_II_RSS_READ_ONLY",
            "capturedAt": captured_at,
            "symbol": normalize_symbol(symbol),
            "slotId": f"SLOT{slot_index + 1:03d}",
            "assignmentGeneration": generation,
            "watchlistAsOf": watchlist.get("observedAt"),
            "slotReady": ready,
            "blockers": [] if ready else ["RSS_SYMBOL_NOT_SETTLED"],
            "tickOrder": "DESC",
            "market": market,
            "orderBook": {
                "asks": [{"level": level, "price": market.get(f"ask{level}"), "size": market.get(f"askSize{level}")} for level in range(1, 11)],
                "bids": [{"level": level, "price": market.get(f"bid{level}"), "size": market.get(f"bidSize{level}")} for level in range(1, 11)],
            },
            "ticks": ticks,
            "sourceFunctions": ["RssMarket", "RssTickList"],
            "marketSizeUnit": market_unit,
            "tickSizeUnit": tick_unit,
            "sizeUnitAttestation": {
                "explicit": True,
                "inferred": False,
                "operatorProvided": True,
            },
            "formulaSurfaceAttestation": formula_attestation,
            "methodology": {
                "dynamicSlotMode": True,
                "excelFormulaWritePerformed": False,
                "symbolSwitchWritePerformed": True,
                "symbolSwitchScope": "MARKET_DATA_QUERY_ONLY",
                "symbolSwitchCellOnly": True,
                "excelOrderWritePerformed": False,
                "pointInTimeOnly": True,
                "futureOutcomeUsed": False,
            },
            "safety": SAFETY,
        })
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
    parser = argparse.ArgumentParser(description="Dynamic MarketSpeed II Excel slot capture; writes only market-data query symbol cells")
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--watchlist", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--market-size-unit", required=True, help="Explicit operator attestation; only SHARES is accepted")
    parser.add_argument("--tick-size-unit", required=True, help="Explicit operator attestation; only SHARES is accepted")
    parser.add_argument("--slots", type=int, default=80)
    parser.add_argument("--tick-rows", type=int, default=100)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--samples", type=int, default=30000)
    parser.add_argument("--settle-seconds", type=float, default=0.75)
    args = parser.parse_args()
    if args.slots < 50:
        raise SystemExit("--slots must be >= 50")
    if args.tick_rows < 20:
        raise SystemExit("--tick-rows must be >= 20")
    if args.interval_seconds < 0.2:
        raise SystemExit("--interval-seconds must be >= 0.2")
    if args.samples < 1:
        raise SystemExit("--samples must be >= 1")
    if args.settle_seconds < 0:
        raise SystemExit("--settle-seconds must be >= 0")
    market_size_unit, tick_size_unit = attest_size_units(args.market_size_unit, args.tick_size_unit)

    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise SystemExit("pywin32 is required: py -m pip install -r tools/requirements-rss.txt") from exc
    excel = win32com.client.GetActiveObject("Excel.Application")
    workbook = _find_workbook(excel, args.workbook)
    assert_dynamic_workbook_formula_surface(workbook)
    for sheet_name in (SHEET_CONTROL, SHEET_MARKET, SHEET_TICKS):
        workbook.Worksheets(sheet_name)
    formula_attestation = formula_surface_attestation(workbook)

    output = Path(args.output)
    watchlist_file = Path(args.watchlist)
    generation = 0
    assignments = read_control_symbols(workbook.Worksheets(SHEET_CONTROL), args.slots)
    last_watchlist_as_of = None
    last_switch_monotonic = None
    current_watchlist: dict[str, Any] | None = None
    append_rows(output, [heartbeat_row(
        market_size_unit=market_size_unit,
        tick_size_unit=tick_size_unit,
        formula_attestation=formula_attestation,
    )])
    print(json.dumps({
        "status": "PHASE58_MSII_DYNAMIC_SLOT_CAPTURE_START",
        "workbook": workbook.Name,
        "slots": args.slots,
        "tickRows": args.tick_rows,
        "output": str(output),
        "marketSizeUnit": market_size_unit,
        "tickSizeUnit": tick_size_unit,
        "sizeUnitAttestation": {"explicit": True, "inferred": False, "operatorProvided": True},
        "formulaSurfaceAttestation": formula_attestation,
        "safety": SAFETY,
    }, ensure_ascii=False))

    for index in range(args.samples):
        if watchlist_file.exists():
            candidate = validate_watchlist(json.loads(watchlist_file.read_text(encoding="utf-8")), args.slots)
            candidate_as_of = str(candidate.get("observedAt") or "")
            if candidate_as_of and candidate_as_of != last_watchlist_as_of:
                generation += 1
                assignments, changed = apply_watchlist(workbook, candidate, slot_count=args.slots, generation=generation)
                current_watchlist = candidate
                last_watchlist_as_of = candidate_as_of
                if changed:
                    last_switch_monotonic = time.monotonic()
        rows = [heartbeat_row(
            watchlist_as_of=last_watchlist_as_of,
            market_size_unit=market_size_unit,
            tick_size_unit=tick_size_unit,
            formula_attestation=formula_attestation,
        )]
        settled = last_switch_monotonic is None or (time.monotonic() - last_switch_monotonic) >= args.settle_seconds
        if current_watchlist is not None and settled:
            rows.extend(capture_batch(
                workbook,
                assignments,
                current_watchlist,
                tick_rows=args.tick_rows,
                generation=generation,
                market_size_unit=market_size_unit,
                tick_size_unit=tick_size_unit,
                formula_attestation=formula_attestation,
            ))
        append_rows(output, rows)
        if index + 1 < args.samples:
            time.sleep(args.interval_seconds)

    print(json.dumps({"status": "PHASE58_MSII_DYNAMIC_SLOT_CAPTURE_COMPLETE", "rowsSha256": sha256_file(output), "output": str(output), "safety": SAFETY}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
