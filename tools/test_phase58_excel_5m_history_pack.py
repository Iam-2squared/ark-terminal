from __future__ import annotations

import pytest

from phase58_excel_5m_history_pack import (
    FROZEN_P24_COMBINED_UNIVERSE,
    PHASE58_P14_SAFETY,
    build_history_pack_from_matrices,
)


def _matrix(symbol: str, *, include_current: bool = True, short_first: bool = False):
    rows = [["銘柄名称", "市場名称", "足種", "日付", "時刻", "始値", "高値", "安値", "終値", "出来高"]]
    sessions = ["2026/08/13", "2026/08/14"]
    for session_index, day in enumerate(sessions):
        count = 10 if short_first and session_index == 0 else 32
        for index in range(count):
            hour = 9 + (index * 5) // 60
            minute = (index * 5) % 60
            base = 100 + session_index + index * 0.05
            rows.append([symbol, "東証", "5M", day, f"{hour:02d}:{minute:02d}", base, base + 0.5, base - 0.4, base + 0.1, 1000 + index])
    if include_current:
        for index in range(8):
            base = 110 + index * 0.05
            rows.append([symbol, "東証", "5M", "2026/08/17", f"09:{index * 5:02d}", base, base + 0.5, base - 0.4, base + 0.1, 2000 + index])
    return rows


def _matrices(**kwargs):
    return {symbol: _matrix(symbol, **kwargs) for symbol in FROZEN_P24_COMBINED_UNIVERSE}


def test_builds_frozen_universe_history_pack_and_excludes_current_session_rows():
    out = build_history_pack_from_matrices(
        _matrices(),
        captured_at="2026-08-17T01:00:00Z",
        as_of_session_date="2026-08-17",
    )
    assert out["status"] == "PHASE58_FROZEN_UNIVERSE_5M_HISTORY_PACK_READY"
    assert out["frozenUniverse"] == list(FROZEN_P24_COMBINED_UNIVERSE)
    assert out["sessionCount"] == 10
    assert out["droppedCurrentOrFutureRowCount"] == 8 * 5
    assert out["skippedUnpopulatedOhlcvRowCount"] == 0
    assert all(session["sessionDate"] < "2026-08-17" for session in out["sessions"])
    assert set(session["symbol"] for session in out["sessions"]) == set(FROZEN_P24_COMBINED_UNIVERSE)
    assert all(len(session["bars5m"]) == 32 for session in out["sessions"])


def test_skips_fully_unpopulated_timestamped_rows_in_history_sheets():
    matrices = _matrices()
    for symbol in FROZEN_P24_COMBINED_UNIVERSE:
        matrices[symbol].insert(2, [symbol, "東証", "5M", "2026/08/13", "09:02", "", "", "", "", ""])
    out = build_history_pack_from_matrices(
        matrices,
        captured_at="2026-08-17T01:00:00Z",
        as_of_session_date="2026-08-17",
    )
    assert out["sessionCount"] == 10
    assert out["skippedUnpopulatedOhlcvRowCount"] == 5
    assert all(out["perSymbol"][symbol]["skippedUnpopulatedOhlcvRowCount"] == 1 for symbol in FROZEN_P24_COMBINED_UNIVERSE)


def test_skips_zero_volume_no_price_placeholders_in_history_sheets():
    matrices = _matrices()
    for symbol in FROZEN_P24_COMBINED_UNIVERSE:
        matrices[symbol].insert(2, [symbol, "東証", "5M", "2026/08/13", "09:02", "", "", "", "", 0])
    out = build_history_pack_from_matrices(
        matrices,
        captured_at="2026-08-17T01:00:00Z",
        as_of_session_date="2026-08-17",
    )
    assert out["sessionCount"] == 10
    assert out["skippedUnpopulatedOhlcvRowCount"] == 5
    assert all(out["perSymbol"][symbol]["skippedUnpopulatedOhlcvRowCount"] == 1 for symbol in FROZEN_P24_COMBINED_UNIVERSE)


def test_skips_no_price_history_placeholder_before_timeframe_display_marker_validation():
    matrices = _matrices()
    for symbol in FROZEN_P24_COMBINED_UNIVERSE:
        matrices[symbol].insert(2, [symbol, "東証", "--------", "2026/08/13", "09:02", "", "", "", "", 0])
    out = build_history_pack_from_matrices(
        matrices,
        captured_at="2026-08-17T01:00:00Z",
        as_of_session_date="2026-08-17",
    )
    assert out["sessionCount"] == 10
    assert out["skippedUnpopulatedOhlcvRowCount"] == 5
    assert out["methodology"]["timeframeValidatedOnlyForPopulatedBars"] is True


def test_rejects_partially_populated_history_row_fail_closed():
    matrices = _matrices()
    matrices["7203.T"].insert(2, ["7203.T", "東証", "5M", "2026/08/13", "09:02", "", 101, 99, 100.5, 1000])
    with pytest.raises(ValueError, match="partially populated OHLCV row"):
        build_history_pack_from_matrices(
            matrices,
            captured_at="2026-08-17T01:00:00Z",
            as_of_session_date="2026-08-17",
        )


def test_drops_partial_oldest_sessions_below_p24_minimum_bar_count():
    out = build_history_pack_from_matrices(
        _matrices(short_first=True),
        captured_at="2026-08-17T01:00:00Z",
        as_of_session_date="2026-08-17",
    )
    assert out["sessionCount"] == 5
    assert out["droppedShortSessionCount"] == 5
    assert all(session["sessionDate"] == "2026-08-14" for session in out["sessions"])


def test_rejects_missing_or_extra_symbols_in_frozen_combined_universe():
    matrices = _matrices()
    matrices.pop("8035.T")
    with pytest.raises(ValueError, match="frozen universe mismatch"):
        build_history_pack_from_matrices(
            matrices,
            captured_at="2026-08-17T01:00:00Z",
            as_of_session_date="2026-08-17",
        )


def test_rejects_non_5m_rows():
    matrices = _matrices()
    matrices["7203.T"][1][2] = "1M"
    with pytest.raises(ValueError, match="timeframe must be 5M"):
        build_history_pack_from_matrices(
            matrices,
            captured_at="2026-08-17T01:00:00Z",
            as_of_session_date="2026-08-17",
        )


def test_all_write_trading_promotion_and_holdout_flags_remain_false():
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
        assert PHASE58_P14_SAFETY[key] is False, key
