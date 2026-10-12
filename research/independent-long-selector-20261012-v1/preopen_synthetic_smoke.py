"""Actual estimator exercise on explicitly artificial data, NOT market research.

The only printed result is engineering test status and operation counts; synthetic
profit, hit-rate or equity values are never presented as Ark market performance.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from preopen_selector import (CONTRACT, LABEL, PreopenConfig, PreopenError, digest,
    evaluate_open_high, make_watchlist, row_key, summarize_open_high)
from preopen_model import HEADS, train_preopen_model, save_private_model


def artificial_population(session):
    config = PreopenConfig()
    rows, labels = [], {}
    for i in range(140):
        code = f"{1000+i}0"
        u = i % 7
        downside = (i // 7) % 7
        close_negative = i % 2 == 0
        features = {"preopen_synthetic_rise":float(u),
                    "preopen_synthetic_risk":float(downside),
                    "preopen_synthetic_cycle":float(i % 11),
                    "preopen_unavailable_source":None}
        r = {"schema":"ARK_PREOPEN_FEATURE_ROW_V1", "contract":CONTRACT,
             "configHash":config.sha,"session":session,"symbol":code,
             "cutoff":config.at(session).isoformat(),"assetType":"JPX_CASH_EQUITY",
             "universeHash":"artificial-universe","sourceManifestSha256":"artificial-source-only",
             "features":features,"featureHash":digest(features),"sampleKind":"SYNTHETIC"}
        # Every teacher is produced by the actual exact-rational evaluator.
        close = 100-min(downside,1) if close_negative else 100+min(u,1)
        raw = {"labelId":LABEL,"session":session,"symbol":code,"market":"T",
               "priceBasis":"RAW_JPX_CASH","traded":True,"completeSession":True,
               "officialFirstTradeOpen":True,"open":100,"high":100+u,
               "low":100-downside,"close":close}
        w = make_watchlist([r],{row_key(r):0.0})
        labels[row_key(r)] = evaluate_open_high(w,{row_key(r):raw})[0]
        rows.append(r)
    return rows, labels


def main():
    fit, fy = artificial_population("2000-01-04")
    cal, cy = artificial_population("2000-01-05")
    report, ry = artificial_population("2000-01-06")
    plan = {"contract":CONTRACT,"mode":"SYNTHETIC","splits":{
        "fit":["2000-01-04"],"calibration":["2000-01-05"],"report":["2000-01-06"]}}
    model = train_preopen_model(fit,fy,cal,cy,plan)
    assert model.receipt["marketFits"] == 0
    assert model.receipt["syntheticFits"] == 10
    assert model.receipt["calibrationFits"] == 10
    assert model.receipt["usedFeatureN"] == 3
    assert model.receipt["registeredFeatureN"] == 4
    assert model.receipt["reportConsumedByFit"] is False
    assert "signed_high_negative" not in model.models
    assert "close_negative" in model.models
    one = model.watchlist(report)
    two = model.watchlist(copy.deepcopy(report))
    assert one == two
    assert one["selectedN"] == 15
    assert len({x["symbol"] for x in one["items"]}) == 15
    assert one["entryAllowed"] is False and one["executionAllowed"] is False
    scores_before = model.score(report)
    modified_report_outcomes = copy.deepcopy(ry)
    for y in modified_report_outcomes.values():
        y["openHighPct"] += 1000
    assert model.score(report) == scores_before
    try:
        model.score(fit)
    except PreopenError as exc:
        assert "IN_FIT_OR_CALIBRATION" in str(exc)
    else:
        raise AssertionError("IN_FIT_REPORT_NOT_REJECTED")
    with TemporaryDirectory() as d:
        receipt = save_private_model(model,Path(d)/"artificial-only")
        assert len(receipt["modelFileSha256"]) == 64
        assert receipt["marketFits"] == 0
    print(json.dumps({"status":"PREOPEN_ESTIMATOR_SYNTHETIC_E2E_PASS",
        "syntheticHeadFits":10,"syntheticCalibrationFits":10,
        "marketFits":0,"marketOutcomeRows":0,"newProviderRequests":0,
        "reportLabelsUsedForFit":False,"watchlistCount":15,
        "tests":"class-support, split, missing features, repeated-score, future-label independence, artifact save",
        "productionReady":False},sort_keys=True))


if __name__ == "__main__":
    main()
