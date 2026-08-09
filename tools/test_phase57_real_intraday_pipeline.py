from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from tools.phase57_real_intraday_pipeline import (
    PHASE57_P16_P18_SAFETY,
    build_read_only_capture_schedule_plan,
    build_real_capture_manifest,
    build_real_intraday_dataset,
)


def _write_rows(root, symbol="7203.T", count=20, step=5):
    base = datetime(2026, 8, 9, 1, 0, tzinfo=timezone.utc)
    path = root / "2026-08-09" / f"{symbol}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(count):
        price = 100.0 + i * 0.05
        rows.append({
            "capturedAt": (base + timedelta(seconds=i * step)).isoformat(),
            "symbol": symbol,
            "last": price,
            "open": 100.0,
            "high": price,
            "low": 99.9,
            "close": price,
            "volume": 1000 + i,
            "bid": price - 0.01,
            "ask": price + 0.01,
            "bidSize": 600,
            "askSize": 400,
            "depthBid": 2500,
            "depthAsk": 1800,
            "aggressiveBuyCount": 30 + i,
            "aggressiveSellCount": 20,
            "tradeCount": 50 + i,
            "sourceMode": "MARKETSPEED_II_RSS_READ_ONLY",
        })
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return base


def test_p16_manifest_audits_only_real_capture(tmp_path):
    _write_rows(tmp_path)
    out = build_real_capture_manifest(tmp_path)
    assert out["phase"] == "57.p16"
    assert out["rowCount"] == 20
    assert out["sessionCount"] == 1
    assert out["symbolCount"] == 1
    assert out["partitions"][0]["coverage"]["bid"] == 1.0
    assert out["syntheticDataUsed"] is False


def test_p17_schedule_is_finite_and_read_only():
    plan = build_read_only_capture_schedule_plan(interval_seconds=5, session_minutes=10, max_ticks_per_session=50)
    assert plan["phase"] == "57.p17"
    assert plan["maxTicksPerSession"] == 50
    assert plan["embeddedInfiniteLoop"] is False
    assert plan["externalSchedulerRequired"] is True
    assert plan["writesExcel"] is False
    assert plan["invokesRssOrderFunctions"] is False


def test_p18_builds_point_in_time_event_rows_from_capture(tmp_path):
    base = _write_rows(tmp_path, count=40, step=5)
    out = build_real_intraday_dataset(
        tmp_path,
        horizon_seconds=60,
        barrier_bps=10,
        require_healthy=True,
        as_of=base + timedelta(seconds=39 * 5),
    )
    assert out["phase"] == "57.p18"
    assert out["status"] == "REAL_INTRADAY_DATASET_READY"
    assert out["rowCount"] > 0
    assert out["futureUsedForFeatures"] is False
    assert out["futureUsedOnlyForLabels"] is True
    assert all(r["featureCutoff"] < r["outcomeAt"] for r in out["rows"])
    assert all(r["sourceMode"] == "MARKETSPEED_II_RSS_READ_ONLY" for r in out["rows"])


def test_all_p16_p18_safety_locks_remain_false(tmp_path):
    _write_rows(tmp_path)
    outputs = [
        build_real_capture_manifest(tmp_path),
        build_read_only_capture_schedule_plan(),
        build_real_intraday_dataset(tmp_path, require_healthy=False, horizon_seconds=60, barrier_bps=10),
    ]
    keys = (
        "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
        "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
    )
    for output in outputs:
        for key in keys:
            assert output[key] is False
            assert PHASE57_P16_P18_SAFETY[key] is False
