from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from tools.phase57_intraday_capture import IntradayCaptureRow, PHASE57_CAPTURE_SAFETY, rows_from_matrix
from tools.phase57_rss_capture_integration import _matrix_from_sheet, assess_intraday_capture_sufficiency

PHASE57_P13_SAFETY = {
    **PHASE57_CAPTURE_SAFETY,
    "mode": "PHASE57_INTRADAY_CAPTURE_OPS_READ_ONLY",
}


def capture_key(row: IntradayCaptureRow) -> str:
    payload = asdict(row)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_existing_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = payload.get("captureKey")
        if isinstance(key, str) and key:
            keys.add(key)
    return keys


def append_jsonl_deduplicated(
    rows: Iterable[IntradayCaptureRow],
    root: str | Path = "data/intraday",
) -> dict[str, Any]:
    root_path = Path(root)
    grouped: dict[tuple[str, str], list[IntradayCaptureRow]] = {}
    for row in rows:
        session = row.capturedAt[:10]
        grouped.setdefault((session, row.symbol), []).append(row)

    inserted = 0
    duplicates = 0
    partitions: list[str] = []
    for (session, symbol), items in sorted(grouped.items()):
        safe_symbol = symbol.replace("/", "_")
        path = root_path / session / f"{safe_symbol}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = _load_existing_keys(path)
        with path.open("a", encoding="utf-8") as handle:
            for row in items:
                key = capture_key(row)
                if key in existing:
                    duplicates += 1
                    continue
                payload = {
                    **asdict(row),
                    "captureKey": key,
                    "sourceMode": "MARKETSPEED_II_RSS_READ_ONLY",
                    "safety": PHASE57_P13_SAFETY,
                }
                handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
                existing.add(key)
                inserted += 1
        partitions.append(str(path))

    return {
        "phase": "57.p13",
        "status": "READ_ONLY_CAPTURE_DEDUP_COMPLETE",
        "insertedRows": inserted,
        "duplicateRowsSkipped": duplicates,
        "partitions": partitions,
        "executionAllowed": False,
        "brokerWriteAllowed": False,
        "excelOrderWriteAllowed": False,
        "rssOrderFunctionAllowed": False,
        "liveTradingAllowed": False,
        "paperTradingAllowed": False,
        "automaticPromotionAllowed": False,
        "productionUpdateAllowed": False,
        "safety": PHASE57_P13_SAFETY,
    }


def run_read_only_capture_cycle(
    workbook: Any,
    *,
    sheet_name: str = "ArkIntraday",
    root: str | Path = "data/intraday",
    thresholds: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    """Run exactly one local READ-ONLY capture cycle.

    The caller may schedule this function externally. It never writes to Excel and never
    invokes an RSS order function.
    """
    sheet = workbook.Worksheets(sheet_name)
    rows = rows_from_matrix(_matrix_from_sheet(sheet))
    persisted = append_jsonl_deduplicated(rows, root)
    sufficiency = assess_intraday_capture_sufficiency(root, thresholds=thresholds)
    return {
        "phase": "57.p13",
        "status": "READ_ONLY_CAPTURE_CYCLE_COMPLETE",
        "capturedRows": len(rows),
        "persisted": persisted,
        "sufficiency": sufficiency,
        "nextStep": (
            "RUN_PREDECLARED_REAL_REPLAY_OOS"
            if sufficiency.get("status") == "INTRADAY_CAPTURE_SUFFICIENT_FOR_PREDECLARED_OOS"
            else "CONTINUE_READ_ONLY_INTRADAY_CAPTURE"
        ),
        "edgeClaimAllowed": False,
        "executionAllowed": False,
        "brokerWriteAllowed": False,
        "excelOrderWriteAllowed": False,
        "rssOrderFunctionAllowed": False,
        "liveTradingAllowed": False,
        "paperTradingAllowed": False,
        "automaticPromotionAllowed": False,
        "productionUpdateAllowed": False,
        "safety": PHASE57_P13_SAFETY,
    }


def build_retention_plan(
    root: str | Path = "data/intraday",
    *,
    as_of: date | None = None,
    hot_days: int = 7,
    warm_days: int = 60,
) -> dict[str, Any]:
    """Classify local session partitions without deleting or moving any data."""
    today = as_of or datetime.now(timezone.utc).date()
    buckets: dict[str, list[str]] = {"hot": [], "warm": [], "cold": [], "invalid": []}
    root_path = Path(root)
    if root_path.exists():
        for directory in sorted(path for path in root_path.iterdir() if path.is_dir()):
            try:
                session = date.fromisoformat(directory.name)
            except ValueError:
                buckets["invalid"].append(str(directory))
                continue
            age = max(0, (today - session).days)
            if age <= hot_days:
                bucket = "hot"
            elif age <= warm_days:
                bucket = "warm"
            else:
                bucket = "cold"
            buckets[bucket].append(str(directory))

    return {
        "phase": "57.p13",
        "status": "RETENTION_PLAN_ONLY",
        "hotDays": hot_days,
        "warmDays": warm_days,
        "buckets": buckets,
        "destructiveActionAllowed": False,
        "executionAllowed": False,
        "brokerWriteAllowed": False,
        "excelOrderWriteAllowed": False,
        "rssOrderFunctionAllowed": False,
        "liveTradingAllowed": False,
        "paperTradingAllowed": False,
        "automaticPromotionAllowed": False,
        "productionUpdateAllowed": False,
        "safety": PHASE57_P13_SAFETY,
    }
