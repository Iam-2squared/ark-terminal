"""Audit saved raw-Selector Direct Entry evidence without fitting or outcomes replay."""
import argparse
import json
import math
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts import phase57_raw_selector_direct_entry_window as study


def audit(saved, output):
    saved = Path(saved)
    p = study.protocol()
    manifest = study.read(saved / "manifest.json")
    for name, digest in manifest["outputs"].items():
        assert study.sha(saved / name) == digest, name
    assert manifest["codeSHA256"] == study.sha(study.__file__)
    assert manifest["fitCalls"] == manifest["validationEvaluations"] == 1
    assert manifest["developmentTestEvaluations"] == 0 and manifest["freshOOSOpened"] is False
    assert manifest["safety"] == study.SAFETY

    result = study.read(saved / "summary.json")
    model = study.Model(study.read(saved / "model.json"))
    labels = study.read(saved / "training-labels.json.gz")
    assert labels and {row["session"] for row in labels} <= set(p["split"]["TRAIN"])
    assert not ({row["session"] for row in labels} & set(p["split"]["VALIDATION"] + p["split"]["DEVELOPMENT_TEST"]))
    y = np.asarray([row["targets"] for row in labels])
    weights = np.asarray([row["weight"] for row in labels])
    root = np.asarray(model.artifact["tree"]["value"][0]).reshape(-1)
    assert np.allclose(np.average(y, axis=0, weights=weights), root, rtol=0, atol=1e-12)
    assert np.isfinite(model.predict_many([row["features"] for row in labels])).all()

    pit = {row["id"]: row for row in study.read(saved / "validation-pit-states.json.gz")}
    ledger = study.read(saved / "validation-ledger.json.gz")
    assert len(ledger) == len(pit) == p["episodes"]["expectedByPartition"]["VALIDATION"]
    assert {row["session"] for row in ledger} <= set(p["split"]["VALIDATION"])
    assert not ({row["session"] for row in ledger} & set(p["split"]["DEVELOPMENT_TEST"]))
    for row in ledger:
        states = {state["delay"]: state for state in pit[row["id"]]["states"]}
        for transition in row["decision"]["transitions"]:
            state = states[transition["delay"]]
            scores = model.predict(state["features"])
            saved_scores = [transition["scores"][name] for name in p["architecture"]["outputs"]]
            assert all(abs(a - b) <= 1e-14 for a, b in zip(scores, saved_scores))
            assert state["selectorRank"] == transition["selectorRank"]
            assert state["selectorScore"] == transition["selectorScore"]
            assert state["selectorSnapshotTimestamp"] == transition["selectorSnapshotTimestamp"]
        assert sum(step["action"] == "BUY_NOW" for step in row["decision"]["transitions"]) <= 1
        assert all(step["action"] in ("WATCH", "BUY_NOW") for step in row["decision"]["transitions"])

    recomputed = study.summary(ledger)
    assert recomputed == result["classification"]["summary"]
    assert result["status"] == "FIRST_RAW_SELECTOR_DIRECT_ENTRY_MEASUREMENT_COMPLETE_HARD_FAIL"
    assert result["classification"]["verdict"] == "HARD_FAIL"
    assert result["classification"]["summary"]["watchEpisodes"] == 0
    assert result["classification"]["summary"]["delayedEntries"] == 0
    assert result["developmentTestOpened"] is False and result["freshOOSOpened"] is False
    assert result["providerRequests"] == 0 and result["candidateFreeze"] is False
    assert all(value == 0 for value in result["noRescue"].values())
    assert result["safety"] == study.SAFETY

    payload = {
        "status": "PASS", "researchStatus": result["status"],
        "savedModelReplayRows": len(labels), "savedValidationDecisionsVerified": len(ledger),
        "fitCallsInAudit": 0, "outcomeRemeasurementsInAudit": 0,
        "developmentTestOpened": False, "freshOOSOpened": False,
        "scoreRankFixedInsideWindow": True, "inventedFiveMinuteSelectorValues": 0,
        "modelSHA256": study.sha(saved / "model.json"), "manifestSHA256": study.sha(saved / "manifest.json"),
        "safety": study.SAFETY,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saved", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    with patch.object(study.Model, "fit_once", side_effect=AssertionError("AUDIT_MUST_NOT_FIT")):
        audit(args.saved, args.out)
