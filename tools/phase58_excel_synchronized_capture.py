from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase58_excel_microstructure_capture import (
    PHASE58_CAPTURE_SAFETY,
    _find_workbook,
    append_capture,
    capture_once,
    sha256_file,
)

PHASE58_SYNC_SAFETY = {
    **PHASE58_CAPTURE_SAFETY,
    "phase": "58.p9.sync-capture",
    "mode": "MARKETSPEED_II_RSS_READ_ONLY_PLUS_FROZEN_PHASE57_CONTEXT",
    "executionAllowed": False,
    "brokerWriteAllowed": False,
    "excelOrderWriteAllowed": False,
    "rssOrderFunctionAllowed": False,
    "liveTradingAllowed": False,
    "paperTradingAllowed": False,
    "automaticPromotionAllowed": False,
    "productionUpdateAllowed": False,
    "transmitted": False,
    "freshHoldoutConsumed": False,
}

FORBIDDEN_OUTCOME_FIELDS = {
    "futureBars",
    "outcome",
    "outcomes",
    "grossReturnPct",
    "netReturnPct",
    "mfePct",
    "maePct",
    "exitTimestamp",
    "exitReason",
    "barsHeld",
    "hit",
    "realizedReturn",
    "label",
    "target",
}


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_direction(value: Any) -> int | None:
    if value in (1, "UP", "LONG"):
        return 1
    if value in (-1, "DOWN", "SHORT"):
        return -1
    if value in (0, "WAIT", "ABSTAIN", "NONE"):
        return 0
    return None


def _freshness_boundary(snapshot: dict[str, Any], as_of: datetime, capture_time: datetime) -> datetime:
    context = snapshot.get("context") if isinstance(snapshot.get("context"), dict) else {}
    close_raw = context.get("sourceBarCloseAt")
    if close_raw in (None, ""):
        return as_of

    close_at = _parse_iso(close_raw)
    if close_at is None:
        raise RuntimeError("Phase57 snapshot sourceBarCloseAt must be a valid ISO timestamp")
    try:
        duration_minutes = float(context.get("sourceBarDurationMinutes"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Phase57 snapshot sourceBarDurationMinutes must be numeric") from exc
    if duration_minutes != 5.0:
        raise RuntimeError("Phase57 prospective sourceBarDurationMinutes must remain exactly 5")

    expected_seconds = duration_minutes * 60.0
    actual_seconds = (close_at - as_of).total_seconds()
    if abs(actual_seconds - expected_seconds) > 1e-6:
        raise RuntimeError(
            "Phase57 snapshot sourceBarCloseAt does not match asOf + sourceBarDurationMinutes"
        )
    if close_at > capture_time:
        raise RuntimeError("Phase57 snapshot sourceBarCloseAt is in the future")
    return close_at


def read_and_validate_phase57_snapshot(path: Path, captured_at: str, max_age_seconds: float) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    file_sha256 = _sha256_bytes(raw)
    parsed = json.loads(raw.decode("utf-8"))
    snapshot = parsed.get("snapshot") if isinstance(parsed, dict) and isinstance(parsed.get("snapshot"), dict) else parsed
    if not isinstance(snapshot, dict):
        raise RuntimeError("Phase57 snapshot file must contain a JSON object or {snapshot:{...}}")

    forbidden = sorted(FORBIDDEN_OUTCOME_FIELDS.intersection(snapshot.keys()))
    if forbidden:
        raise RuntimeError(f"Phase57 snapshot contains forbidden realized/future outcome fields: {','.join(forbidden)}")

    direction = _normalize_direction(snapshot.get("direction"))
    if direction is None:
        raise RuntimeError("Phase57 snapshot direction must be LONG/SHORT/UP/DOWN/+1/-1 or WAIT/ABSTAIN/0")
    if snapshot.get("frozen") is not True:
        raise RuntimeError("Phase57 snapshot must be explicitly frozen")
    if snapshot.get("futureOutcomeUsed") is not False:
        raise RuntimeError("Phase57 snapshot futureOutcomeUsed must be false")
    if snapshot.get("thresholdSearchAfterCapture") is not False:
        raise RuntimeError("Phase57 snapshot thresholdSearchAfterCapture must be false")
    if snapshot.get("entryRetunedAfterCapture") is not False:
        raise RuntimeError("Phase57 snapshot entryRetunedAfterCapture must be false")

    model_id = snapshot.get("modelId")
    if not isinstance(model_id, str) or not model_id.strip():
        raise RuntimeError("Phase57 snapshot modelId is required")
    artifact_sha256 = snapshot.get("artifactSha256")
    if not isinstance(artifact_sha256, str) or re.fullmatch(r"[0-9a-fA-F]{64}", artifact_sha256) is None:
        raise RuntimeError("Phase57 snapshot artifactSha256 must be 64 hex chars")

    confidence = snapshot.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Phase57 snapshot confidence must be numeric or null") from exc
        if confidence < 0 or confidence > 1:
            raise RuntimeError("Phase57 snapshot confidence must be within [0,1]")

    as_of = _parse_iso(snapshot.get("asOf"))
    capture_time = _parse_iso(captured_at)
    if as_of is None or capture_time is None:
        raise RuntimeError("Phase57 snapshot asOf/capturedAt must be valid ISO timestamps")
    if capture_time < as_of:
        raise RuntimeError("Phase57 snapshot timestamp is in the future")

    freshness_as_of = _freshness_boundary(snapshot, as_of, capture_time)
    age = (capture_time - freshness_as_of).total_seconds()
    if age < 0:
        raise RuntimeError("Phase57 snapshot freshness boundary is in the future")
    if age > max_age_seconds:
        raise RuntimeError(
            f"Phase57 snapshot is stale: ageSeconds={age:.3f} maxAgeSeconds={max_age_seconds:.3f} "
            f"freshnessAsOf={freshness_as_of.isoformat()}"
        )

    canonical = {
        "direction": direction,
        "confidence": confidence,
        "setup": snapshot.get("setup"),
        "context": snapshot.get("context"),
        "asOf": snapshot.get("asOf"),
        "modelId": model_id.strip(),
        "artifactSha256": artifact_sha256.lower(),
        "frozen": True,
        "futureOutcomeUsed": False,
        "thresholdSearchAfterCapture": False,
        "entryRetunedAfterCapture": False,
    }
    return canonical, file_sha256


def synchronized_capture_once(workbook: Any, snapshot_path: Path, max_age_seconds: float) -> dict[str, Any]:
    micro = capture_once(workbook)
    captured_at = str(micro["capturedAt"])
    phase57, snapshot_file_sha256 = read_and_validate_phase57_snapshot(snapshot_path, captured_at, max_age_seconds)
    return {
        **micro,
        "schemaVersion": 2,
        "phase": "58.p9.sync-capture",
        "phase57Snapshot": phase57,
        "phase57SnapshotFileSha256": snapshot_file_sha256,
        "methodology": {
            "phase57DirectionIsFrozenBase": True,
            "phase58MayConfirmDeferOrAbstainOnly": True,
            "phase58MayReverseDirection": False,
            "pointInTimeOnly": True,
            "futureOutcomeUsed": False,
            "historicalDecisionReconstructionAllowed": False,
            "sameCaptureBoundary": True,
            "snapshotFreshnessUsesCompletedSourceBarCloseWhenPresent": True,
            "freshHoldoutConsumed": False,
        },
        "safety": PHASE58_SYNC_SAFETY,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prospective READ ONLY Phase57 + MARKETSPEED II RSS synchronized capture")
    parser.add_argument("--phase57-snapshot-file", required=True)
    parser.add_argument("--workbook", default=None)
    parser.add_argument("--output", default="data/phase58/phase57-microstructure-sync-live.jsonl")
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--samples", type=int, default=120)
    parser.add_argument("--phase57-max-age-seconds", type=float, default=300.0)
    args = parser.parse_args()

    if args.samples < 1:
        raise SystemExit("--samples must be >= 1")
    if args.interval_seconds < 0.2:
        raise SystemExit("--interval-seconds must be >= 0.2")
    if args.phase57_max_age_seconds <= 0:
        raise SystemExit("--phase57-max-age-seconds must be > 0")

    snapshot_path = Path(args.phase57_snapshot_file)
    if not snapshot_path.exists():
        raise SystemExit(f"Phase57 snapshot file not found: {snapshot_path}")

    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise SystemExit("pywin32 is required: py -m pip install -r tools/requirements-rss.txt") from exc

    excel = win32com.client.GetActiveObject("Excel.Application")
    workbook = _find_workbook(excel, args.workbook)
    output = Path(args.output)

    print(json.dumps({
        "status": "PHASE58_PROSPECTIVE_SYNC_CAPTURE_START",
        "workbook": workbook.Name,
        "phase57SnapshotFile": str(snapshot_path),
        "output": str(output),
        "samples": args.samples,
        "intervalSeconds": args.interval_seconds,
        "phase57MaxAgeSeconds": args.phase57_max_age_seconds,
        "safety": PHASE58_SYNC_SAFETY,
    }, ensure_ascii=False))

    captured = 0
    for index in range(args.samples):
        payload = synchronized_capture_once(workbook, snapshot_path, args.phase57_max_age_seconds)
        append_capture(output, payload)
        captured += 1
        if index + 1 < args.samples:
            time.sleep(args.interval_seconds)

    digest = sha256_file(output)
    print(json.dumps({
        "status": "PHASE58_PROSPECTIVE_SYNC_CAPTURE_COMPLETE",
        "capturedSamples": captured,
        "output": str(output),
        "sha256": digest,
        "safety": PHASE58_SYNC_SAFETY,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
