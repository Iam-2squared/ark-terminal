from __future__ import annotations

import json
from datetime import datetime, timezone

from tools.phase57_intraday_capture_health import assess_capture_health, PHASE57_P14_SAFETY


def _write(root, session, symbol, rows):
    path = root / session / f"{symbol}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = {
                "symbol": symbol,
                "sourceMode": "MARKETSPEED_II_RSS_READ_ONLY",
                **row,
            }
            handle.write(json.dumps(payload) + "\n")


def test_healthy_capture_has_no_blockers(tmp_path):
    _write(tmp_path, "2026-08-09", "7203.T", [
        {"capturedAt": "2026-08-09T02:00:00+00:00"},
        {"capturedAt": "2026-08-09T02:00:05+00:00"},
        {"capturedAt": "2026-08-09T02:00:10+00:00"},
    ])
    out = assess_capture_health(
        tmp_path,
        as_of=datetime(2026, 8, 9, 2, 0, 20, tzinfo=timezone.utc),
        expected_interval_seconds=5,
        stale_after_seconds=30,
        max_gap_multiplier=3,
    )
    assert out["status"] == "INTRADAY_CAPTURE_HEALTHY"
    assert out["blockers"] == []
    assert out["symbols"]["7203.T"]["stale"] is False
    assert out["symbols"]["7203.T"]["gapped"] is False


def test_stale_and_gap_conditions_block_health(tmp_path):
    _write(tmp_path, "2026-08-09", "8306.T", [
        {"capturedAt": "2026-08-09T01:59:00+00:00"},
        {"capturedAt": "2026-08-09T01:59:40+00:00"},
    ])
    out = assess_capture_health(
        tmp_path,
        as_of=datetime(2026, 8, 9, 2, 1, 0, tzinfo=timezone.utc),
        expected_interval_seconds=5,
        stale_after_seconds=30,
        max_gap_multiplier=3,
    )
    assert out["status"] == "INTRADAY_CAPTURE_HEALTH_BLOCKED"
    assert "STALE_INTRADAY_CAPTURE" in out["blockers"]
    assert "INTRADAY_CAPTURE_GAPS_DETECTED" in out["blockers"]
    assert "8306.T" in out["staleSymbols"]
    assert "8306.T" in out["gappedSymbols"]


def test_safety_locks_remain_false(tmp_path):
    out = assess_capture_health(tmp_path)
    for key in (
        "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
        "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
    ):
        assert out[key] is False
        assert PHASE57_P14_SAFETY[key] is False
