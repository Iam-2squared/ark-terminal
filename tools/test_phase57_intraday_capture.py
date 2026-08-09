from __future__ import annotations

import json

from tools.phase57_intraday_capture import (
    PHASE57_CAPTURE_SAFETY,
    append_jsonl,
    capture_manifest,
    rows_from_matrix,
)


def sample_matrix():
    return [
        ["capturedAt","symbol","last","open","high","low","close","volume","bid","ask","bidSize","askSize","depthBid","depthAsk","aggressiveBuyCount","aggressiveSellCount","tradeCount"],
        ["2026-08-09T01:00:00+00:00","7203",3000,2990,3010,2980,3000,120000,2999,3000,500,400,2200,1800,30,20,50],
        ["2026-08-09T01:00:05+00:00","8306.T",1600,1595,1602,1590,1600,90000,1599.5,1600,700,600,2600,2400,40,35,75],
    ]


def test_rows_from_matrix_normalizes_symbols_and_numbers():
    rows = rows_from_matrix(sample_matrix())
    assert len(rows) == 2
    assert rows[0].symbol == "7203.T"
    assert rows[0].bid == 2999.0
    assert rows[1].symbol == "8306.T"


def test_append_jsonl_is_local_research_storage_only(tmp_path):
    rows = rows_from_matrix(sample_matrix())
    paths = append_jsonl(rows, tmp_path)
    assert len(paths) == 2
    payload = json.loads(paths[0].read_text(encoding="utf-8").splitlines()[0])
    assert payload["sourceMode"] == "MARKETSPEED_II_RSS_READ_ONLY"
    assert payload["safety"]["executionAllowed"] is False
    assert payload["safety"]["rssOrderFunctionAllowed"] is False


def test_manifest_requires_no_execution_permissions():
    manifest = capture_manifest(rows_from_matrix(sample_matrix()))
    assert manifest["status"] == "READ_ONLY_INTRADAY_CAPTURE_READY"
    assert manifest["microstructureCoverage"] == 1.0
    for key in (
        "executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed",
        "liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed",
    ):
        assert manifest[key] is False
        assert PHASE57_CAPTURE_SAFETY[key] is False
