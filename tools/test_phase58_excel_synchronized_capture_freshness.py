from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from phase58_excel_synchronized_capture import read_and_validate_phase57_snapshot  # noqa: E402


def _payload(*, with_close: bool = True, close_at: str = "2026-08-18T00:35:00.000Z") -> dict:
    context = {"selectedHorizonBars": 24}
    if with_close:
        context.update(
            {
                "sourceBarTimestamp": "2026-08-18T00:30:00.000Z",
                "sourceBarDurationMinutes": 5,
                "sourceBarCloseAt": close_at,
            }
        )
    return {
        "snapshot": {
            "direction": 1,
            "confidence": 0.56,
            "setup": "VOLATILITY",
            "context": context,
            "asOf": "2026-08-18T00:30:00.000Z",
            "modelId": "phase57-p21-prospective-rf-h24",
            "artifactSha256": "a" * 64,
            "frozen": True,
            "futureOutcomeUsed": False,
            "thresholdSearchAfterCapture": False,
            "entryRetunedAfterCapture": False,
        }
    }


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_completed_5m_bar_close_is_used_for_age(tmp_path: Path) -> None:
    path = _write(tmp_path, _payload())
    snapshot, digest = read_and_validate_phase57_snapshot(
        path,
        "2026-08-18T00:36:32.169Z",
        300.0,
    )
    assert snapshot["direction"] == 1
    assert snapshot["context"]["sourceBarCloseAt"] == "2026-08-18T00:35:00.000Z"
    assert len(digest) == 64


def test_legacy_snapshot_without_close_metadata_remains_strict(tmp_path: Path) -> None:
    path = _write(tmp_path, _payload(with_close=False))
    with pytest.raises(RuntimeError, match="Phase57 snapshot is stale"):
        read_and_validate_phase57_snapshot(path, "2026-08-18T00:36:32.169Z", 300.0)


def test_inconsistent_close_metadata_fails_closed(tmp_path: Path) -> None:
    path = _write(tmp_path, _payload(close_at="2026-08-18T00:36:00.000Z"))
    with pytest.raises(RuntimeError, match="sourceBarCloseAt does not match"):
        read_and_validate_phase57_snapshot(path, "2026-08-18T00:36:32.169Z", 300.0)
