from __future__ import annotations

import pytest

from phase58_excel_5m_chart_export import PHASE58_5M_EXPORT_SAFETY, parse_rss_chart_matrix


def _matrix(timeframe: str = "5M"):
    rows = [["meta"], ["銘柄名称", "市場名称", "足種", "日付", "時刻", "始値", "高値", "安値", "終値", "出来高"]]
    for index in range(8):
        rows.append([
            "トヨタ自動車",
            "東証",
            timeframe,
            "2026/08/17",
            f"09:{index * 5:02d}",
            100 + index,
            101 + index,
            99 + index,
            100.5 + index,
            1000 + index * 100,
        ])
    return rows


def test_parses_rsschart_headers_and_drops_newest_visible_row_for_closure_safety():
    out = parse_rss_chart_matrix(
        _matrix(),
        symbol="7203.T",
        captured_at="2026-08-17T01:00:00Z",
        session_date="2026-08-17",
    )
    assert out["status"] == "PHASE58_RSSCHART_5M_PREFIX_READY"
    assert out["latestBarClosed"] is True
    assert out["sameSessionSourceBarCount"] == 8
    assert out["closedBarCount"] == 7
    assert out["skippedUnpopulatedOhlcvRowCount"] == 0
    assert out["bars5m"][-1]["timestamp"] == "2026-08-17T00:30:00Z"
    assert out["droppedNewestTimestamp"] == "2026-08-17T00:35:00Z"
    assert out["methodology"]["newestVisibleRowDroppedForClosureSafety"] is True


def test_filters_older_sessions_before_conservative_newest_row_drop():
    values = _matrix()
    values.insert(2, ["トヨタ自動車", "東証", "5M", "2026/08/14", "15:25", 90, 91, 89, 90.5, 500])
    out = parse_rss_chart_matrix(
        values,
        symbol="7203.T",
        captured_at="2026-08-17T01:00:00Z",
        session_date="2026-08-17",
    )
    assert out["sourceBarCount"] == 9
    assert out["sameSessionSourceBarCount"] == 8
    assert all(row["timestamp"].startswith("2026-08-17T") for row in out["bars5m"])


def test_skips_timestamped_rows_when_all_ohlcv_cells_are_unpopulated():
    values = _matrix()
    values.insert(3, ["トヨタ自動車", "東証", "5M", "2026/08/17", "09:02", "", "", "", "", ""])
    out = parse_rss_chart_matrix(
        values,
        symbol="7203.T",
        captured_at="2026-08-17T01:00:00Z",
        session_date="2026-08-17",
    )
    assert out["sourceBarCount"] == 8
    assert out["skippedUnpopulatedOhlcvRowCount"] == 1
    assert out["methodology"]["fullyUnpopulatedOhlcvRowsSkipped"] is True


def test_rejects_partially_populated_ohlcv_rows_fail_closed():
    values = _matrix()
    values.insert(3, ["トヨタ自動車", "東証", "5M", "2026/08/17", "09:02", "", 101, 99, 100.5, 1000])
    with pytest.raises(ValueError, match="partially populated OHLCV row"):
        parse_rss_chart_matrix(
            values,
            symbol="7203.T",
            captured_at="2026-08-17T01:00:00Z",
            session_date="2026-08-17",
        )


def test_rejects_non_5m_chart_rows():
    with pytest.raises(ValueError, match="timeframe must be 5M"):
        parse_rss_chart_matrix(
            _matrix("1M"),
            symbol="7203.T",
            captured_at="2026-08-17T01:00:00Z",
            session_date="2026-08-17",
        )


def test_rejects_duplicate_timestamps():
    values = _matrix()
    values.append(values[-1].copy())
    with pytest.raises(ValueError, match="duplicate RssChart timestamps"):
        parse_rss_chart_matrix(
            values,
            symbol="7203.T",
            captured_at="2026-08-17T01:00:00Z",
            session_date="2026-08-17",
        )


def test_accepts_excel_numeric_date_and_time_values():
    values = [["日付", "時刻", "始値", "高値", "安値", "終値", "出来高", "足種"]]
    for index in range(8):
        values.append([46251, (9 * 60 + index * 5) / 1440, 100, 101, 99, 100.5, 1000, "5M"])
    out = parse_rss_chart_matrix(
        values,
        symbol="7203.T",
        captured_at="2026-08-17T01:00:00Z",
        session_date="2026-08-17",
    )
    assert out["closedBarCount"] == 7
    assert out["bars5m"][0]["timestamp"] == "2026-08-17T00:00:00Z"


def test_all_write_trading_and_promotion_flags_remain_false():
    for key in (
        "executionAllowed",
        "brokerWriteAllowed",
        "excelOrderWriteAllowed",
        "rssOrderFunctionAllowed",
        "liveTradingAllowed",
        "paperTradingAllowed",
        "automaticPromotionAllowed",
        "productionUpdateAllowed",
        "overnightHoldingAllowed",
        "transmitted",
        "freshHoldoutConsumed",
    ):
        assert PHASE58_5M_EXPORT_SAFETY[key] is False, key
