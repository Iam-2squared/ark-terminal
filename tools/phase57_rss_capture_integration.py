from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.phase57_intraday_capture import (
    PHASE57_CAPTURE_SAFETY,
    append_jsonl,
    capture_manifest,
    rows_from_matrix,
)

PHASE57_P12_SAFETY = {
    **PHASE57_CAPTURE_SAFETY,
    "mode": "PHASE57_RSS_CAPTURE_INTEGRATION_READ_ONLY",
}

DEFAULT_THRESHOLDS = {
    "minRows": 1000,
    "minSessions": 20,
    "minSymbols": 3,
    "minMicroCoverage": 0.80,
}

MICRO_FIELDS = (
    "bid", "ask", "bidSize", "askSize", "depthBid", "depthAsk",
    "aggressiveBuyCount", "aggressiveSellCount", "tradeCount",
)


def _matrix_from_sheet(sheet: Any) -> list[list[Any]]:
    values = sheet.UsedRange.Value
    if values is None:
        return []
    if not isinstance(values, (tuple, list)):
        return [[values]]
    rows = list(values)
    if rows and not isinstance(rows[0], (tuple, list)):
        return [list(rows)]
    return [list(row) for row in rows]


def capture_read_only_workbook_snapshot(
    workbook: Any,
    *,
    sheet_name: str = "ArkIntraday",
    root: str | Path = "data/intraday",
) -> dict[str, Any]:
    """Read one Excel RSS sheet snapshot and persist it locally.

    This function never writes to Excel and never calls any RSS order function.
    """
    sheet = workbook.Worksheets(sheet_name)
    rows = rows_from_matrix(_matrix_from_sheet(sheet))
    written = append_jsonl(rows, root)
    manifest = capture_manifest(rows)
    return {
        "phase": "57.p12",
        "status": "RSS_READ_ONLY_SNAPSHOT_CAPTURED" if rows else "NO_RSS_INTRADAY_ROWS",
        "capturedRows": len(rows),
        "writtenPartitions": [str(path) for path in written],
        "captureManifest": manifest,
        "executionAllowed": False,
        "brokerWriteAllowed": False,
        "excelOrderWriteAllowed": False,
        "rssOrderFunctionAllowed": False,
        "liveTradingAllowed": False,
        "paperTradingAllowed": False,
        "automaticPromotionAllowed": False,
        "productionUpdateAllowed": False,
        "safety": PHASE57_P12_SAFETY,
    }


def assess_intraday_capture_sufficiency(
    root: str | Path = "data/intraday",
    *,
    thresholds: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    cfg = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    root_path = Path(root)
    records: list[dict[str, Any]] = []
    for path in sorted(root_path.glob("*/*.jsonl")) if root_path.exists() else []:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("sourceMode") != "MARKETSPEED_II_RSS_READ_ONLY":
                continue
            records.append(payload)

    sessions = sorted({str(r.get("capturedAt", ""))[:10] for r in records if r.get("capturedAt")})
    symbols = sorted({str(r.get("symbol")) for r in records if r.get("symbol")})
    micro_complete = sum(
        1 for r in records
        if all(r.get(field) is not None for field in MICRO_FIELDS)
    )
    coverage = micro_complete / len(records) if records else 0.0

    blockers: list[str] = []
    if len(records) < int(cfg["minRows"]):
        blockers.append("INSUFFICIENT_INTRADAY_ROWS")
    if len(sessions) < int(cfg["minSessions"]):
        blockers.append("INSUFFICIENT_INTRADAY_SESSIONS")
    if len(symbols) < int(cfg["minSymbols"]):
        blockers.append("INSUFFICIENT_INTRADAY_SYMBOLS")
    if coverage < float(cfg["minMicroCoverage"]):
        blockers.append("INSUFFICIENT_MICROSTRUCTURE_COVERAGE")

    return {
        "phase": "57.p12",
        "status": "INTRADAY_CAPTURE_SUFFICIENT_FOR_PREDECLARED_OOS" if not blockers else "CONTINUE_READ_ONLY_INTRADAY_CAPTURE",
        "rowCount": len(records),
        "sessionCount": len(sessions),
        "symbolCount": len(symbols),
        "symbols": symbols,
        "sessions": sessions,
        "microstructureCoverage": coverage,
        "thresholds": cfg,
        "blockers": blockers,
        "edgeClaimAllowed": False,
        "executionAllowed": False,
        "brokerWriteAllowed": False,
        "excelOrderWriteAllowed": False,
        "rssOrderFunctionAllowed": False,
        "liveTradingAllowed": False,
        "paperTradingAllowed": False,
        "automaticPromotionAllowed": False,
        "productionUpdateAllowed": False,
        "safety": PHASE57_P12_SAFETY,
    }
