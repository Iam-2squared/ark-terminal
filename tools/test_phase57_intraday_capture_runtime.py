from __future__ import annotations

from datetime import datetime, timezone

from tools.phase57_intraday_capture_runtime import (
    PHASE57_P15_SAFETY,
    run_bounded_read_only_runtime,
)


class _Sheet:
    UsedRange = type("UsedRange", (), {
        "Value": (
            ("capturedAt","symbol","last","open","high","low","close","volume","bid","ask","bidSize","askSize","depthBid","depthAsk","aggressiveBuyCount","aggressiveSellCount","tradeCount"),
            ("2026-08-09T02:00:00+00:00","7203",3000,2990,3010,2980,3000,120000,2999,3000,500,400,2200,1800,30,20,50),
        )
    })()


class _Workbook:
    def Worksheets(self, name):
        assert name == "ArkIntraday"
        return _Sheet()


def test_bounded_runtime_never_enables_trading(tmp_path):
    out = run_bounded_read_only_runtime(
        _Workbook(),
        iterations=2,
        root=tmp_path,
        now=datetime(2026,8,9,2,0,5,tzinfo=timezone.utc),
        capture_thresholds={"minRows":1,"minSessions":1,"minSymbols":1,"minMicroCoverage":0.5},
        expected_interval_seconds=5,
        stale_after_seconds=30,
        max_gap_multiplier=3,
    )
    assert out["iterationsCompleted"] == 2
    assert out["continuousLoopAllowed"] is False
    for key in (
        "executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed",
        "liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed",
    ):
        assert out[key] is False
        assert PHASE57_P15_SAFETY[key] is False


def test_runtime_is_explicitly_bounded(tmp_path):
    out = run_bounded_read_only_runtime(_Workbook(), iterations=0, root=tmp_path)
    assert out["iterationsCompleted"] == 0
    assert out["status"] == "BOUNDED_READ_ONLY_RUNTIME_COMPLETE"
