from __future__ import annotations

import unittest

import phase58_excel_5m_chart_export_stable as stable
import phase58_prospective_session_runner_p30 as p30
import phase58_prospective_session_runner as p17


HEADERS = ["銘柄名称", "市場名称", "足種", "日付", "時刻", "始値", "高値", "安値", "終値", "出来高"]


def bar(clock: str, *, close: float = 100.5, timeframe: str = "5M") -> list[object]:
    return ["トヨタ", "東証", timeframe, "2026/08/18", clock, 100.0, 101.0, 99.5, close, 10000.0]


class StableRssChartDuplicateTests(unittest.TestCase):
    def test_exact_duplicate_timestamp_is_collapsed_once(self) -> None:
        matrix = [HEADERS, bar("13:35:00"), bar("13:35:00"), bar("13:40:00")]
        cleaned, collapsed = stable.collapse_exact_duplicate_timestamp_rows(matrix)
        self.assertEqual(collapsed, 1)
        self.assertEqual(len(cleaned), 3)

    def test_conflicting_duplicate_timestamp_fails_closed(self) -> None:
        matrix = [HEADERS, bar("13:35:00", close=100.5), bar("13:35:00", close=100.7)]
        with self.assertRaisesRegex(ValueError, "conflicting duplicate RssChart timestamp"):
            stable.collapse_exact_duplicate_timestamp_rows(matrix)

    def test_explicit_5m_metadata_is_preferred_over_blank_duplicate(self) -> None:
        matrix = [HEADERS, bar("13:35:00", timeframe=""), bar("13:35:00", timeframe="5M")]
        cleaned, collapsed = stable.collapse_exact_duplicate_timestamp_rows(matrix)
        self.assertEqual(collapsed, 1)
        self.assertEqual(cleaned[1][2], "5M")

    def test_p30_runner_changes_only_exporter_command(self) -> None:
        kwargs = dict(
            python_exe="python",
            node_exe="node",
            symbol="7203.T",
            sheet="Ark5m7203",
            history_pack="history.json",
            current_prefix="prefix.json",
            snapshot="snapshot.json",
            output="sync.jsonl",
            interval_seconds=2.0,
            samples_per_cycle=110,
            phase57_max_age_seconds=300.0,
            reusable_target=False,
            workbook=None,
        )
        original = p17.build_cycle_commands(**kwargs)
        routed = p30.build_cycle_commands_p30(**kwargs)
        self.assertEqual(routed[0][1], "tools/phase58_excel_5m_chart_export_stable.py")
        self.assertEqual(routed[0][0], original[0][0])
        self.assertEqual(routed[0][2:], original[0][2:])
        self.assertEqual(routed[1:], original[1:])
        for key in (
            "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
            "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
            "overnightHoldingAllowed", "transmitted", "freshHoldoutConsumed",
        ):
            self.assertFalse(p17.SAFETY[key], key)


if __name__ == "__main__":
    unittest.main()
