import json
from pathlib import Path

import pytest

from phase57_msii_prepare_partial_smoke import prepare_partial_smoke


def write_raw(path: Path, observed_at: str):
    path.write_text(json.dumps({"meta": {"observedAt": observed_at}, "entries": []}), encoding="utf-8")


def test_partial_smoke_bootstrap_starts_from_first_available_bucket_and_marks_ineligible(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    write_raw(raw_dir / "20260904T013000Z.json", "2026-09-04T01:30:00.834Z")
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({
        "schemaVersion": 2,
        "sessionDate": "2026-09-04",
        "lastObservedAt": None,
        "lastBucketAt": None,
        "processedBucketCount": 0,
        "priorV2Selections": [],
        "recentV1Selections": [],
        "processedRaw": [],
    }), encoding="utf-8")

    state = prepare_partial_smoke(raw_dir, state_file, "2026-09-04")

    assert state["partialStartBucketAt"] == "2026-09-04T01:30:00.000Z"
    assert state["processedBucketCount"] == 17
    assert state["missingOpeningBucketCount"] == 17
    assert state["sessionEligibility"] == "PARTIAL_SMOKE"
    assert state["notEligibleForProspectiveScore"] is True
    assert state["futureOutcomeUsed"] is False
    assert state["safety"]["executionAllowed"] is False
    assert state["safety"]["brokerWriteAllowed"] is False
    assert state["safety"]["excelOrderWriteAllowed"] is False
    assert state["safety"]["rssOrderFunctionAllowed"] is False
    assert state["safety"]["liveTradingAllowed"] is False
    assert state["safety"]["paperTradingAllowed"] is False
    assert state["safety"]["automaticPromotionAllowed"] is False
    assert state["safety"]["productionUpdateAllowed"] is False
    assert state["safety"]["transmitted"] is False
    assert state["safety"]["excelMarketDataQueryWriteAllowed"] is True


def test_partial_smoke_refuses_non_pristine_state(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    write_raw(raw_dir / "20260904T013000Z.json", "2026-09-04T01:30:00.834Z")
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({
        "schemaVersion": 2,
        "sessionDate": "2026-09-04",
        "lastObservedAt": "2026-09-04T01:30:00.834Z",
        "lastBucketAt": "2026-09-04T01:30:00.000Z",
        "processedBucketCount": 18,
        "processedRaw": ["20260904T013000Z.json"],
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="non-pristine"):
        prepare_partial_smoke(raw_dir, state_file, "2026-09-04")


def test_partial_smoke_refuses_normal_full_fresh_start(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    write_raw(raw_dir / "0905.json", "2026-09-04T00:05:00.100Z")
    state_file = tmp_path / "state.json"

    with pytest.raises(ValueError, match="unnecessary"):
        prepare_partial_smoke(raw_dir, state_file, "2026-09-04")
