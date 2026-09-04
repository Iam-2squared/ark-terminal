import json
from pathlib import Path

from phase57_msii_prepare_mid_session import prepare


def _raw(path: Path, observed_at: str):
    path.write_text(json.dumps({"meta":{"observedAt":observed_at}}), encoding="utf-8")


def test_mid_session_starts_at_next_bucket_and_skips_earlier_raw(tmp_path):
    raw=tmp_path/"raw"; raw.mkdir()
    _raw(raw/"1030.json","2026-09-04T01:30:00.100Z")
    _raw(raw/"1345.json","2026-09-04T04:45:00.100Z")
    state=tmp_path/"state.json"; lane=tmp_path/"lane.json"
    result=prepare(raw,state,lane,"2026-09-04","2026-09-04T13:49:00+09:00")
    assert result["collectionStartBucketAt"]=="2026-09-04T04:50:00.000Z"
    assert result["stateInitialization"]=="COLD_START"
    assert result["eligibleForMidSessionScore"] is True
    assert result["notEligibleForFullFreshScore"] is True
    assert result["futureOutcomeUsed"] is False
    assert result["processedRaw"]==["1030.json","1345.json"]
    lane_state=json.loads(lane.read_text(encoding="utf-8"))
    assert lane_state["lastDecisionAt"]=="2026-09-04T04:49:59.999Z"
    assert lane_state["sessionQuality"]=="MID_SESSION_CAUSAL_COLD_START"
    for key in ("executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed"):
        assert lane_state["safety"][key] is False
    assert lane_state["safety"]["transmitted"] is False


def test_mid_session_refuses_non_pristine_watchlist_state(tmp_path):
    raw=tmp_path/"raw"; raw.mkdir()
    state=tmp_path/"state.json"; lane=tmp_path/"lane.json"
    state.write_text(json.dumps({"sessionDate":"2026-09-04","lastObservedAt":"x","lastBucketAt":None,"processedBucketCount":1,"processedRaw":[]}),encoding="utf-8")
    try:
        prepare(raw,state,lane,"2026-09-04","2026-09-04T13:49:00+09:00")
    except ValueError as exc:
        assert "non-pristine" in str(exc)
    else:
        raise AssertionError("expected ValueError")
