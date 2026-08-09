from __future__ import annotations

from tools.phase57_rss_capture_integration import (
    PHASE57_P12_SAFETY,
    assess_intraday_capture_sufficiency,
    capture_read_only_workbook_snapshot,
)


HEADERS = [
    "capturedAt","symbol","last","open","high","low","close","volume","bid","ask",
    "bidSize","askSize","depthBid","depthAsk","aggressiveBuyCount","aggressiveSellCount","tradeCount",
]


class DummyUsedRange:
    def __init__(self, values):
        self.Value = values


class DummySheet:
    def __init__(self, values):
        self.UsedRange = DummyUsedRange(values)


class DummySheets:
    def __init__(self, sheet):
        self.sheet = sheet

    def __call__(self, name):
        assert name == "ArkIntraday"
        return self.sheet


class DummyWorkbook:
    def __init__(self, values):
        self.Worksheets = DummySheets(DummySheet(values))


def row(ts, symbol):
    return [ts,symbol,3000,2990,3010,2980,3000,120000,2999,3000,500,400,2200,1800,30,20,50]


def test_capture_reads_excel_snapshot_but_only_writes_local_dataset(tmp_path):
    wb = DummyWorkbook((tuple(HEADERS), tuple(row("2026-08-01T01:00:00+00:00", "7203"))))
    out = capture_read_only_workbook_snapshot(wb, root=tmp_path)
    assert out["status"] == "RSS_READ_ONLY_SNAPSHOT_CAPTURED"
    assert out["capturedRows"] == 1
    assert out["excelOrderWriteAllowed"] is False
    assert out["rssOrderFunctionAllowed"] is False
    assert list(tmp_path.glob("*/*.jsonl"))


def test_sufficiency_monitor_blocks_until_real_capture_thresholds_are_met(tmp_path):
    wb = DummyWorkbook((
        tuple(HEADERS),
        tuple(row("2026-08-01T01:00:00+00:00", "7203")),
        tuple(row("2026-08-02T01:00:00+00:00", "8306")),
        tuple(row("2026-08-03T01:00:00+00:00", "6758")),
    ))
    capture_read_only_workbook_snapshot(wb, root=tmp_path)
    blocked = assess_intraday_capture_sufficiency(tmp_path)
    assert blocked["status"] == "CONTINUE_READ_ONLY_INTRADAY_CAPTURE"
    assert "INSUFFICIENT_INTRADAY_ROWS" in blocked["blockers"]

    ready = assess_intraday_capture_sufficiency(
        tmp_path,
        thresholds={"minRows":3,"minSessions":3,"minSymbols":3,"minMicroCoverage":1.0},
    )
    assert ready["status"] == "INTRADAY_CAPTURE_SUFFICIENT_FOR_PREDECLARED_OOS"
    assert ready["edgeClaimAllowed"] is False
    assert ready["microstructureCoverage"] == 1.0


def test_all_hard_safety_locks_remain_false():
    for key in (
        "executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed",
        "liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed",
    ):
        assert PHASE57_P12_SAFETY[key] is False
