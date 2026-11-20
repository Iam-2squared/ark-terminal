"""Read-only, predeclared R54 OOF price and cohort diagnostics.

Only the completed, hash-audited score-fold forecasts are read. These
evaluator-only groups never feed the fitted model, EXIT, Entry, or Capital.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
from pathlib import Path

import numpy as np

from scripts import phase57_mh_data_r54 as data
from scripts import phase57_mh_train_r54 as trainer


def time_bin(now: int) -> str:
    return "EARLY" if now < 630 else "MID" if now < 810 else "LATE"


def prefix_bin(rank: int) -> str:
    return "FIRST5" if rank <= 5 else "NEXT10" if rank <= 15 else "LATER"


class DAccumulator:
    def __init__(self):
        self.n = self.wrong = 0
        self.mse = self.zero = self.bias = 0.0

    def add(self, pred, truth):
        self.n += 1
        self.mse += (pred-truth)**2
        self.zero += truth**2
        self.bias += pred-truth
        self.wrong += pred < 0 < truth

    def result(self):
        return summarize(self)


class PriceAccumulator:
    def __init__(self):
        self.n = 0
        self.pred = self.reference = self.abs_error = self.bias = 0.0

    def add(self, pred, reference):
        self.n += 1
        self.pred += pred
        self.reference += reference
        self.abs_error += abs(pred-reference)
        self.bias += pred-reference

    def result(self):
        n = self.n
        return {"n": n, "meanPredictedJpy": self.pred/n,
                "meanReferenceJpy": self.reference/n,
                "maeJpy": self.abs_error/n, "biasJpy": self.bias/n}


def summarize(a):
    if not a.n:
        return {"n": 0, "msePp2": None, "zeroMsePp2": None,
                "biasPp": None, "predictedNegativeTruePositive": None,
                "predictedNegativeTruePositiveRate": None}
    return {"n": a.n, "msePp2": a.mse/a.n,
            "zeroMsePp2": a.zero/a.n, "biasPp": a.bias/a.n,
            "predictedNegativeTruePositive": a.wrong,
            "predictedNegativeTruePositiveRate": a.wrong/a.n}


def diagnostic(source: Path, summary: Path, labels: Path,
               training: Path, out: Path):
    from scripts import phase57_exit_continuation_r52 as r52
    from scripts import phase57_capital_exit_integrated as integrated
    from scripts import phase57_development_integrated_v0 as v0
    if out.exists():
        raise ValueError("APPEND_ONLY_FORECAST_DIAGNOSTIC")
    p = json.loads(trainer.PROTOCOL.read_text())
    if (data.sha(trainer.PROTOCOL) != trainer.PROTOCOL_SHA.read_text().strip() or
        p["cycleId"] != "CYCLE2_CORRECTED_D_TEACHER" or
        data.sha(labels) != p["inputHashes"]["labels"]):
        raise ValueError("CYCLE_OR_CORRECTED_TEACHER_DRIFT")
    audit = json.loads((training / "oof-audit.json").read_text())
    forecast_file = training / "oof-forecasts.npz"
    if (audit["predictionsSha256"] != data.sha(forecast_file) or
        audit["expectedFits"] != 176 or
        audit["sourceIdentitySha256"] != r52.IDENTITY_SHA or
        data.sha(summary / "fold-manifest.json") !=
            p["inputHashes"]["summaryFiles"]["fold-manifest.json"]):
        raise ValueError("UNVERIFIED_FINITE_OOF")
    receipt, arrays, ids, groups = r52.load_checkpoints(source)
    entries = r52.all_frozen_entries()
    raw = r52.projected_raw(entries)
    _, original, _, _ = integrated.load_inputs()
    evaluation = original[4]
    folds = json.loads((summary / "fold-manifest.json").read_text())
    score_fold = {day: f["fold"] for f in folds for day in f["score"]}
    current_state = receipt["categoricalColumns"].index("currentState.state")
    schema = json.loads((trainer.EVIDENCE / "FEATURE_SCHEMA_LOCKED.json").read_text())
    codes = schema["categorical"]["currentState.state"]["sourceCodes"]
    decode = {v: k for k, v in codes.items()}
    rank = {ix: position for seq in groups.values()
            for position, ix in enumerate(seq, 1)}
    with np.load(forecast_file, allow_pickle=False) as z:
        a = z["FULL__A__mean"]
        d = z["FULL__D__mean"]
    with np.load(labels, allow_pickle=False) as z:
        truth_a, truth_d = z["A"], z["D"]
    if (a.shape != truth_a.shape or d.shape != truth_d.shape or
        len(ids) != len(a) or len(ids) != audit["outputRowN"]):
        raise ValueError("OOF_LABEL_ROW_GEOMETRY")
    buckets = collections.defaultdict(DAccumulator)
    price = collections.defaultdict(PriceAccumulator)
    winner = collections.defaultdict(DAccumulator)
    example = {}
    count = collections.Counter()
    eval_days = set(p["sessions"])
    for i, row in enumerate(ids):
        arm, eid, day, now = row["arm"], row["entryId"], row["session"], row["now"]
        if day not in score_fold:
            continue
        short = "IM" if arm == v0.IM else "R1"
        state = decode.get(int(arrays["categorical"][i, current_state]), "UNKNOWN")
        tbin, prefix = time_bin(now), prefix_bin(rank[i])
        now_price = None
        if (arm, eid) in entries:
            path = raw[entries[(arm, eid)]["opportunity"]]
            now_price = data._price(path.get(now-1), 4)
        for j, h in enumerate(data.HORIZONS):
            horizon = str(h)
            if math.isfinite(float(a[i, j])) and math.isfinite(float(truth_a[i, j])):
                if now_price is not None:
                    predicted = now_price*(1+float(a[i, j])/100)
                    observed = now_price*(1+float(truth_a[i, j])/100)
                    price[(short, horizon)].add(predicted, observed)
                    if day in eval_days and short not in example:
                        example[short] = {"entryId": eid, "session": day,
                                          "checkpointMinute": now,
                                          "freshNowPriceJpy": now_price, "horizons": {}}
                    if example.get(short, {}).get("entryId") == eid and \
                       example.get(short, {}).get("checkpointMinute") == now:
                        example[short]["horizons"][horizon] = {
                            "predictedPriceJpy": predicted, "exactReferencePriceJpy": observed}
            if h == 0 or not (math.isfinite(float(d[i, j])) and
                              math.isfinite(float(truth_d[i, j]))):
                continue
            pred, truth = float(d[i, j]), float(truth_d[i, j])
            count[(short, horizon)] += 1
            for group, key in (("state", state), ("time", tbin), ("prefix", prefix)):
                buckets[(short, horizon, group, key)].add(pred, truth)
            if day in eval_days:
                upside = evaluation[arm][eid]["postUpsidePct"]
                if upside is not None and upside >= 5:
                    winner[(short, horizon)].add(pred, truth)
    payload = {
        "schema": "phase57-r54-cycle2-readonly-forecast-strata-v1",
        "cycleId": p["cycleId"], "protocolSha256": data.sha(trainer.PROTOCOL),
        "teacherSha256": data.sha(labels), "oofSha256": data.sha(forecast_file),
        "scope": "SCORED_OOF_ONLY; DIAGNOSTIC_NEVER_RUNTIME",
        "definitions": {"time": "EARLY now<10:30; MID 10:30<=now<13:30; LATE later",
                        "prefix": "per Entry checkpoint rank FIRST5, NEXT10, LATER",
                        "winner": "evaluator postEntryUpsidePct>=5 in 24 Development sessions",
                        "price": "fresh NOW reference times (1 + A mean forecast pct/100)"},
        "forecastPriceExample": example,
        "priceByArmHorizon": {f"{arm}|{h}": rows.result()
            for (arm, h), rows in sorted(price.items())},
        "dByStratum": {"|".join(k): v.result() for k, v in sorted(buckets.items())},
        "winnerD": {"|".join(k): v.result() for k, v in sorted(winner.items())},
        "dScoredRows": {"|".join(k): v for k, v in sorted(count.items())},
        "newEstimatorFits": 0, "newIntegratedReplays": 0,
        "safety": p["safety"]}
    out.write_bytes(data.canonical(payload))
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in ("source", "summary", "labels", "training", "out"):
        parser.add_argument("--"+key, type=Path, required=True)
    args = parser.parse_args()
    result = diagnostic(args.source, args.summary, args.labels,
                        args.training, args.out)
    print(data.canonical({"status": "PASS", "sections": list(result),
                          "newEstimatorFits": 0, "newIntegratedReplays": 0}).decode())
