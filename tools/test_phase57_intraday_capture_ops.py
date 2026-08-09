from __future__ import annotations

from datetime import date

from tools.phase57_intraday_capture import rows_from_matrix
from tools.phase57_intraday_capture_ops import (
    PHASE57_P13_SAFETY,
    append_jsonl_deduplicated,
    build_retention_plan,
)


def sample_rows():
    matrix = [
        ["capturedAt","symbol","last","open","high","low","close","volume","bid","ask","bidSize","askSize","depthBid","depthAsk","aggressiveBuyCount","aggressiveSellCount","tradeCount"],
        ["2026-08-09T01:00:00+00:00","7203",3000,2990,3010,2980,3000,120000,2999,3000,500,400,2200,1800,30,20,50],
        ["2026-08-09T01:00:05+00:00","8306.T",1600,1595,1602,1590,1600,90000,1599.5,1600,700,600,2600,2400,40,35,75],
    ]
    return rows_from_matrix(matrix)


def test_dedup_is_idempotent_and_read_only(tmp_path):
    rows = sample_rows()
    first = append_jsonl_deduplicated(rows, tmp_path)
    second = append_jsonl_deduplicated(rows, tmp_path)
    assert first["insertedRows"] == 2
    assert first["duplicateRowsSkipped"] == 0
    assert second["insertedRows"] == 0
    assert second["duplicateRowsSkipped"] == 2
    for key in (
        "executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed",
        "liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed",
    ):
        assert first[key] is False
        assert PHASE57_P13_SAFETY[key] is False


def test_retention_plan_never_deletes_or_moves(tmp_path):
    for session in ("2026-08-09", "2026-07-20", "2026-05-01", "not-a-date"):
        (tmp_path / session).mkdir(parents=True)
    plan = build_retention_plan(tmp_path, as_of=date(2026,8,9), hot_days=7, warm_days=60)
    assert plan["status"] == "RETENTION_PLAN_ONLY"
    assert plan["destructiveActionAllowed"] is False
    assert any("2026-08-09" in path for path in plan["buckets"]["hot"])
    assert any("2026-07-20" in path for path in plan["buckets"]["warm"])
    assert any("2026-05-01" in path for path in plan["buckets"]["cold"])
    assert any("not-a-date" in path for path in plan["buckets"]["invalid"])
