from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tools.phase58_prospective_session_runner import (
    MIN_MICROSTRUCTURE_SAMPLES_PER_CYCLE,
    SAFETY,
    build_cycle_commands,
    freshness_adjusted_samples,
)


def test_build_cycle_commands_keeps_read_only_refresh_order():
    commands = build_cycle_commands(
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
    )
    assert len(commands) == 3
    assert commands[0][:2] == ["python", "tools/phase58_excel_5m_chart_export.py"]
    assert commands[1][:2] == ["node", "tools/phase58_phase57_prospective_snapshot.mjs"]
    assert commands[2][:2] == ["python", "tools/phase58_excel_synchronized_capture.py"]
    assert "--reusable-target" not in commands[1]
    assert commands[2][commands[2].index("--samples") + 1] == "110"


def test_reusable_target_flag_is_explicit_and_does_not_change_training_history():
    commands = build_cycle_commands(
        python_exe="py",
        node_exe="node",
        symbol="285A.T",
        sheet="Ark5mLive",
        history_pack="history.json",
        current_prefix="prefix.json",
        snapshot="snapshot.json",
        output="sync.jsonl",
        interval_seconds=2.0,
        samples_per_cycle=50,
        phase57_max_age_seconds=300.0,
        reusable_target=True,
        workbook="Ark Terminal.xlsx",
    )
    assert "--reusable-target" in commands[1]
    assert commands[1][commands[1].index("--history-pack") + 1] == "history.json"
    assert commands[0][-2:] == ["--workbook", "Ark Terminal.xlsx"]
    assert commands[2][-2:] == ["--workbook", "Ark Terminal.xlsx"]


def _snapshot_file(tmp_path: Path) -> Path:
    path = tmp_path / "snapshot.json"
    path.write_text(
        json.dumps(
            {
                "snapshot": {
                    "asOf": "2026-08-18T00:30:00.000Z",
                    "context": {
                        "sourceBarDurationMinutes": 5,
                        "sourceBarCloseAt": "2026-08-18T00:35:00.000Z",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def test_freshness_budget_shrinks_capture_instead_of_expiring_mid_cycle(tmp_path: Path):
    result = freshness_adjusted_samples(
        snapshot_path=_snapshot_file(tmp_path),
        requested_samples=110,
        interval_seconds=2.0,
        max_age_seconds=300.0,
        now=datetime(2026, 8, 18, 0, 36, 32, 169000, tzinfo=timezone.utc),
    )
    assert result["actualSamples"] == 94
    assert result["adjusted"] is True
    assert result["captureSpanSeconds"] == 186.0
    assert result["actualSamples"] >= MIN_MICROSTRUCTURE_SAMPLES_PER_CYCLE


def test_freshness_budget_keeps_requested_samples_when_room_is_available(tmp_path: Path):
    result = freshness_adjusted_samples(
        snapshot_path=_snapshot_file(tmp_path),
        requested_samples=110,
        interval_seconds=2.0,
        max_age_seconds=300.0,
        now=datetime(2026, 8, 18, 0, 35, 10, tzinfo=timezone.utc),
    )
    assert result["actualSamples"] == 110
    assert result["adjusted"] is False


def test_freshness_budget_exposes_when_too_few_samples_remain(tmp_path: Path):
    result = freshness_adjusted_samples(
        snapshot_path=_snapshot_file(tmp_path),
        requested_samples=110,
        interval_seconds=2.0,
        max_age_seconds=300.0,
        now=datetime(2026, 8, 18, 0, 39, 30, tzinfo=timezone.utc),
    )
    assert result["actualSamples"] == 6
    assert result["actualSamples"] < MIN_MICROSTRUCTURE_SAMPLES_PER_CYCLE


def test_all_execution_and_write_flags_remain_false():
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
        assert SAFETY[key] is False
