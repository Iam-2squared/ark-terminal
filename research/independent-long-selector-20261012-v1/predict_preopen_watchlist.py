"""Label-free private predict/export CLI. No RSS or broker transmission."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from preopen_io import private_path, write_json, utc_now, SAFE_FLAGS
from preopen_model import load_private_model
from preopen_selector import PreopenConfig, PreopenError, digest, JST
from run_preopen_selector import load_feature_input


def export_watchlist(rows, model, *, session, previous_session, generated_at=None,
                     historical=False, live_profile=None):
    config = PreopenConfig()
    config.at(session)
    now = datetime.now(JST)
    if not historical and (session != now.date().isoformat() or now > config.at(session)):
        raise PreopenError("LIVE_EXPORT_WRONG_SESSION_OR_AFTER_CUTOFF")
    if previous_session >= session:
        raise PreopenError("PREVIOUS_SESSION_MUST_PRECEDE_TARGET")
    if not historical and (live_profile or {}).get("refreshVerified") is not True:
        raise PreopenError("LIVE_REFRESH_PROFILE_NOT_VERIFIED")
    for row in rows:
        if row["session"] != session or row.get("sourceLatestSession") != previous_session:
            raise PreopenError("STALE_CACHE_OR_MIXED_SESSION")
        missing_required = row.get("missingRequiredSources", [])
        if missing_required:
            raise PreopenError("REQUIRED_SOURCE_MISSING")
        if not historical and row.get("liveRefreshReady") is not True:
            raise PreopenError("ROW_LIVE_REFRESH_NOT_VERIFIED")
    if not rows:
        # Empty eligible universe is represented explicitly. It does not imply
        # a calibrated quality-gate rejection of otherwise eligible candidates.
        watch = {"schema":"ARK_PREOPEN_NO_CANDIDATE_RECEIPT_V1",
                 "contract":model.receipt["contract"],"session":session,
                 "cutoff":config.at(session).isoformat(),"items":[],
                 "selectedN":0,"eligibleN":0,"reason":"EMPTY_ADMITTED_ELIGIBLE_UNIVERSE",
                 "sourceLatestSession":previous_session, **SAFE_FLAGS}
        watch["watchlistHash"] = digest(watch)
    else:
        watch = model.watchlist(rows)
    receipt = {
        "schema_version":"ARK_RSS_PREOPEN_HANDOFF_V1",
        "selector_id":"ARK_PREOPEN_OPEN_HIGH_V1_20261012",
        "feature_schema_hash":model.receipt["featureSchemaHash"],
        "session":session,"cutoff":config.at(session).isoformat(),
        "generated_at":generated_at or utc_now(),
        "source_latest_session":previous_session,
        "source_manifest_hash":rows[0]["sourceManifestSha256"] if rows else None,
        "universe_hash":rows[0]["universeHash"] if rows else None,
        "watchlist_hash":watch["watchlistHash"],
        "symbols":watch["items"], "data_quality": "ADMITTED_HISTORICAL" if historical else "REFRESH_VERIFIED",
        "missing_reasons":{r["symbol"]:r.get("missingReasons",{}) for r in rows
                           if r.get("missingReasons")},
        "live_feature_profile":live_profile or {"refreshVerified":False},
        "intended_use":"WATCHLIST_ONLY","historicalResearchOnly":historical,
        "rankScoreIsExpectedReturn":False, **SAFE_FLAGS}
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--request", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    req = json.loads(Path(a.request).read_text())
    if set(req).intersection({"labels","report_labels","outcomes"}):
        raise PreopenError("LABEL_INPUT_FORBIDDEN_IN_PREDICT_CLI")
    root = Path(req["privateRoot"]).resolve()
    from preopen_io import verify_entry
    from preopen_session_admission import exchange_sessions
    import csv
    import gzip
    with gzip.open(verify_entry(req["calendar"],root),"rt",newline="") as stream:
        sessions=exchange_sessions(list(csv.DictReader(stream)))
    if req["session"] not in sessions:
        raise PreopenError("PREDICT_TARGET_IS_NOT_EXCHANGE_SESSION")
    ix=sessions.index(req["session"])
    if not ix or sessions[ix-1] != req["exchangePreviousSession"]:
        raise PreopenError("PREDICT_PREVIOUS_EXCHANGE_SESSION_MISMATCH")
    model = load_private_model(private_path(req["trustedModelDirectory"],root),
        private_root=root,expected_model_sha256=req["modelSha256"],
        expected_schema_sha256=req["featureSchemaHash"])
    if model.receipt["mode"] == "AUTHORIZED_DEVELOPMENT":
        from preopen_io import verify_entry
        from preopen_reuse_authorization import validate_reuse_authorization
        evidence=json.loads(verify_entry(req["currentReuseEvidence"],root).read_text())
        validate_reuse_authorization(evidence, work_id=req.get("reuseWorkId"))
    rows = load_feature_input(req["features"],root)
    out = export_watchlist(rows,model,session=req["session"],
        previous_session=req["exchangePreviousSession"],
        historical=req.get("historicalResearchOnly",False),
        live_profile=req.get("liveFeatureProfile"))
    out["model_hash"] = req["modelSha256"]
    out["export_hash"] = digest(out)
    write_json(private_path(a.output,root),out)
    print(json.dumps({"status":"PRIVATE_WATCHLIST_ONLY_EXPORTED",
                      "selectedN":len(out["symbols"]),"transmitted":False,
                      "productionReady":False},sort_keys=True))


if __name__ == "__main__":
    main()
