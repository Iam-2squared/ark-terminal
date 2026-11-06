"""Precommitted zero-fit EXIT policy using archived temporal R52 B predictions.

Only causal state and saved OOF predictions enter decisions. Historical prices
are resolved after SELL_INTENT by the unchanged R24 execution adapter.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path

import numpy as np

from scripts import phase57_exit_continuation_r52 as r52
from scripts import phase57_exit_continuation_r52_cycle2_report as report52
from scripts import phase57_exit_continuation_r52_independent_audit as audit52
from scripts import phase57_exit_winner_lifecycle_r50 as r50
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_capital_exit_integrated as integrated
from scripts import phase57_capital_v3 as v3
from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_development_integrated_v1 as v1


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/phase57-exit-persistent-value-r53"
PRECOMMIT = EVIDENCE / "PRECOMMIT.json"
NAME = "R53_PERSISTENT_PREFIX_VALUE"
PREDICTOR = "R52_PREFIX_PATTERN_VALUE"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract():
    p = json.loads(PRECOMMIT.read_text())
    v0.require(sha(PRECOMMIT) == (EVIDENCE / "PRECOMMIT.sha256").read_text().strip(),
               "R53_PRECOMMIT_CHANGED")
    v0.require(p["status"] == "FROZEN_BEFORE_NEW_EXIT_POLICY_PERFORMANCE"
               and p["candidates"] == [NAME] and p["finiteBudget"]["newFits"] == 0
               and p["safety"] == v0.SAFETY and not any(v0.SAFETY.values()),
               "R53_FINITE_CONTRACT")
    r52.protocol()
    v0.require(sha(r52.PRECOMMIT) == p["originalPins"]["r52ProtocolSha256"]
               and sha(EVIDENCE / "READINESS_AUDIT.json") == p["readinessAuditSha256"],
               "R53_R52_OR_READINESS_SOURCE_CHANGED")
    return p


def frozen_predictions(path, n, p):
    v0.require(sha(path) == p["predictionSource"]["sha256"], "R53_SAVED_PREDICTION_PIN")
    with np.load(path, allow_pickle=False) as source:
        v0.require(set(source.files) == set(r52.CANDIDATES), "R53_PREDICTION_SET")
        values = source[PREDICTOR].copy()
    v0.require(len(values) == n and values.dtype == np.float32,
               "R53_PREDICTION_ROW_IDENTITY")
    return values


def action(frozen_r50, fresh, current_return, prediction, previous, p):
    """R50-A has its original priority; no future execution price enters here."""
    if frozen_r50["action"] == "FORCE_TERMINAL":
        return "FORCE_TERMINAL", "FROZEN_R50_TERMINAL", 0
    if frozen_r50["action"] == "EXIT_INTENT":
        return "SELL_INTENT", "FROZEN_R50_HARVEST", 0
    if (not fresh or current_return is None or
            not math.isfinite(current_return) or
            prediction is None or not math.isfinite(prediction)):
        return "HOLD", "MISSING_NOW_RESET", 0
    if prediction >= p["runtime"]["modelThresholdPp"]:
        return "HOLD", "PREDICTED_CONTINUATION_RESET", 0
    consecutive = previous + 1
    if consecutive < p["runtime"]["confirmations"]:
        return "HOLD", "NEGATIVE_VALUE_CONFIRMATION_PENDING", consecutive
    return "SELL_INTENT", "CONFIRMED_NEGATIVE_VALUE", consecutive


def calendar(p, receipt, arrays, identities, groups, entries, raw, predictions, source_r50):
    """Build one exit for every frozen Entry; do not restrict to formerly funded IDs."""
    cols = receipt["numericColumns"]
    ret_col = cols.index("facts.currentReturnPct")
    chosen = set(p["sessions"])
    out = {arm: {} for arm in v0.ARMS}
    traces = []
    support = collections.Counter()
    for (arm, eid), seq in groups.items():
        entry = entries[arm, eid]
        day = entry["session"]
        if day not in chosen:
            continue
        path = raw[entry["opportunity"]]
        observed = [path[t] for t in sorted(path)]
        terminal = execution.terminal_execution_reference(observed)
        state = r50.initial_state()
        streak = 0
        first_r50 = None
        selected = None
        missing = []
        for idx in seq:
            now = identities[idx]["now"]
            fact = r52.fact(arrays, cols, idx, now)
            d = r50.intent(fact, state, "R50_A_LIFECYCLE", terminal=now == 925)
            state = d["state"]
            raw_prediction = float(predictions[idx])
            prediction = raw_prediction if math.isfinite(raw_prediction) else None
            raw_return = float(arrays["numeric"][idx, ret_col])
            current_return = raw_return if math.isfinite(raw_return) else None
            decision, reason, next_streak = action(
                d, fact["fresh"], current_return, prediction, streak, p)
            streak = next_streak
            support[reason] += 1
            # The lookup happens only after an EXIT_INTENT is issued.
            if decision == "SELL_INTENT":
                ref = execution.ordinary_execution_reference(day, now, observed)
                if d["action"] == "EXIT_INTENT" and first_r50 is None:
                    first_r50 = (ref["referenceStart"], ref["price"]) if (
                        ref["status"] == "RESOLVED_NEXT_SCHEDULED_OPEN") else None
                if ref["status"] == "RESOLVED_NEXT_SCHEDULED_OPEN":
                    selected = {
                        "session": day, "entryId": eid, "decisionNow": now,
                        "exitMinute": ref["referenceStart"], "exitPrice": ref["price"],
                        "exitKind": "MODEL_EXIT", "reason": reason,
                        "predictedAdvantagePp": prediction}
                    break
                missing.append({"decisionNow": now, "status": ref["status"],
                                "reason": reason})
                if reason == "CONFIRMED_NEGATIVE_VALUE":
                    streak = 0
            elif decision == "FORCE_TERMINAL":
                selected = {
                    "session": day, "entryId": eid, "decisionNow": now,
                    "exitMinute": 930 if terminal["price"] is not None else None,
                    "exitPrice": terminal["price"], "exitKind": "FORCED_TERMINAL",
                    "reason": reason, "predictedAdvantagePp": None}
                break
        v0.require(selected is not None, "R53_MISSING_TERMINAL_CHECKPOINT")
        out[arm][eid] = selected
        traces.append({**selected, "arm": arm,
                       "missingOrdinaryReferences": missing,
                       "firstR50ExitThroughNewHeldPrefix": first_r50})
    for arm in v0.ARMS:
        v0.require(set(out[arm]) == set(source_r50[arm]), "R53_FROZEN_ENTRY_SCOPE")
    return out, traces, dict(support)


def read_inputs(source, prediction_path):
    p = contract()
    receipt, arrays, identities, groups = r52.load_checkpoints(source)
    entries = r52.all_frozen_entries()
    v0.require(set(groups) == set(entries), "R53_GROUP_SCOPE")
    raw = r52.projected_raw(entries)
    predictions = frozen_predictions(prediction_path, len(identities), p)
    expected = [i for i, x in enumerate(identities)
                if x["session"] in p["sessions"] and x["now"] != 925]
    v0.require(len(expected) == p["predictionSource"]["evaluationWindowScoredRows"]
               and np.all(np.isfinite(predictions[expected])), "R53_OOF_GAPS")
    return p, receipt, arrays, identities, groups, entries, raw, predictions


def preflight(source, prediction_path):
    p, receipt, arrays, identities, groups, entries, raw, predictions = read_inputs(
        source, prediction_path)
    v0.require(all(x["now"] == 925 or math.isfinite(float(predictions[i]))
                   for i, x in enumerate(identities) if x["session"] in p["sessions"]),
               "R53_PREDICTION_SUFFIX")
    return {"stage": "ZERO_FIT_INPUT_CHECK", "protocolSha256": sha(PRECOMMIT),
            "sourceFeaturesSha256": r52.FEATURE_SHA,
            "sourceRowIdentitiesSha256": r52.IDENTITY_SHA,
            "savedPredictionSha256": sha(prediction_path),
            "rows": len(identities), "frozenEntryGroups": len(groups),
            "windowEntryGroups": sum(entries[k]["session"] in p["sessions"] for k in groups),
            "newFits": 0, "newPolicyReplays": 0,
            "providerRequests": 0, "protectedOpened": 0, "safety": v0.SAFETY}


def paired_performance(rows, baseline):
    paired = report52.paired_rows(rows, baseline)
    return {kind: report52.layer_a_groups(sub) for kind, sub in paired.items()}


def gate(p, report, paired):
    card = report["IM"][NAME]
    portfolio = card["portfolio"]
    quality = card["quality"]
    g = p["gate"]
    groups = paired["IM"]["candidate"]
    baseline_ge5 = groups[">=5%"]
    daily = card["dailySummary"]["validSessions"]
    supplemental = report["IM"][NAME]["supplemental"]
    checks = {
        "certified24Eod": daily == g["full24IMCertifiedEod"],
        "positiveEquity": portfolio["finalEquityJpy"] is not None and
            Decimal(portfolio["finalEquityJpy"]) > Decimal(g["finalEquityMustExceedJpy"][0]),
        "improvedVsR50": portfolio["finalEquityJpy"] is not None and
            Decimal(portfolio["finalEquityJpy"]) > Decimal(g["finalEquityMustExceedJpy"][1]),
        "pairedWinnerGe5Mean": baseline_ge5["meanNetPct"] is not None and
            baseline_ge5["meanNetPct"] >= g["pairedOld79Ge5MeanNetPctMin"],
        "pairedWinnerGe10Mean": groups[">=10%"]["meanNetPct"] is not None and
            groups[">=10%"]["meanNetPct"] >= g["pairedOld79Ge10MeanNetPctMin"],
        "pairedWinnerGe5Pnl": Decimal(baseline_ge5["pnlJpy"]) >=
            Decimal(g["pairedOld79Ge5ConfirmedPnlJpyMin"]),
        "pairedThreeToFive": groups["3–5%"]["meanNetPct"] is not None and
            groups["3–5%"]["meanNetPct"] >= g["pairedThreeToFiveMeanNetPctMin"],
        "pairedBelowOne": groups["<1%"]["meanNetPct"] is not None and
            groups["<1%"]["meanNetPct"] >= g["pairedBelowOneMeanNetPctMin"],
        "combinedGe5": quality["Combined"]["ge5"] >= g["combinedFundedGe5Min"],
        "combinedGe10": quality["Combined"]["ge10"] >= g["combinedFundedGe10Min"],
        "ge5Reach": card["upside"]["reach"] >= g["ge5ReachMin"],
        "replacementN": quality["Replacement"]["n"] >= g["replacementFundedMin"],
        "replacementGe5": quality["Replacement"]["ge5"] >= g["replacementFundedGe5Min"],
        "replacementMedian": quality["Replacement"]["medianUpsidePct"] is not None and
            quality["Replacement"]["medianUpsidePct"] >= g["replacementMedianUpsidePctMin"],
        "concentration": supplemental["topSessionNotionalShare"] is not None and
            supplemental["topSessionNotionalShare"] <= g["topSessionFundedNotionalShareMax"],
    }
    return {
        "selection": "SELECT_DEVELOPMENT_ONLY" if all(checks.values()) else "NO_SELECTION_STOP",
        "checks": checks, "fitCount": 0,
        "utilizationTarget": "UNVERIFIED" if supplemental["validMarkCoverage"] <
                g["user80PercentTargetSeparate"]["markCoverageForAttainmentMin"] else
            ("ATTAINED" if card["turnover"]["timeWeightedUtilizationValidOnly"] >= .8
             else "UNMET"),
        "fullPeriodMeasurement": "CERTIFIED" if daily == 24 else "MEASUREMENT_BLOCKED",
        "productionReady": False, "safety": v0.SAFETY}


def finite(source, prediction_path, out):
    p, receipt, arrays, identities, groups, entries, raw, predictions = read_inputs(
        source, prediction_path)
    _, data, score, source_r50 = integrated.load_inputs()
    original_control = {arm: r52.archive_control(arm) for arm in v0.ARMS}
    # Zero-fit, no performance: independently reconstruct frozen R50-A.
    _, _, reconstructed = r52.build_labels(receipt, arrays, identities, groups, entries, raw)
    for arm in v0.ARMS:
        for eid, saved in source_r50[arm].items():
            got = reconstructed[arm][eid]
            v0.require((got is None and saved["exitPrice"] is None) or
                       (got is not None and got[0] == saved["exitMinute"] and
                        float(got[1]) == float(saved["exitPrice"])),
                       "R53_R50_RECONSTRUCTION:" + eid)
    exits, trace, support = calendar(
        p, receipt, arrays, identities, groups, entries, raw, predictions, source_r50)
    _, _, cohort, intents, evaluation, _, joined_raw, _, _, labels = data
    replays = {}
    result = {"IM": {}, "R1": {}}
    paired = {}
    ranked = {}
    for arm in v0.ARMS:
        short = "IM" if arm == v0.IM else "R1"
        subset = {**cohort, "sessions": p["sessions"]}
        eligible = [i for i in intents[arm] if i["timestamp"][:10] in p["sessions"]]
        ranked[arm] = v3.ranked_intents(eligible, score[arm])
        control = integrated.replay(arm, 3, subset, ranked[arm], joined_raw, source_r50[arm])
        v0.require(v0.canonical(control) == v0.canonical(original_control[arm]),
                   "R53_CONTROL_ARCHIVE_CHANGED")
        first = integrated.replay(arm, 3, subset, ranked[arm], joined_raw, exits[arm])
        second = integrated.replay(arm, 3, subset, ranked[arm], joined_raw, exits[arm])
        v0.require(v0.canonical(first) == v0.canonical(second),
                   "R53_SAVED_PREDICTION_REPLAY_NONDETERMINISTIC")
        for name, ledger in (("R50_A_CONTROL", control), (NAME, first)):
            replays[arm, name] = ledger
            x = r52.score(ledger, ranked[arm], evaluation[arm], labels[arm],
                          data[0]["split"]["folds"], p["sessions"])
            x["supplemental"] = audit52.supplemental(ledger, evaluation[arm], p["sessions"])
            result[short][name] = x
        result[short][NAME]["currencyAttributionVsControl"] = r52.pnl_delta(control, first)
        paired[short] = paired_performance(r52.layer_a(control, exits[arm], evaluation[arm]),
                                           control)
    decision = gate(p, result, paired)
    out.mkdir(parents=True, exist_ok=False)
    for (arm, name), ledger in replays.items():
        short = "IM" if arm == v0.IM else "R1"
        prefix = short + "_" + name
        (out / (prefix + "_ledger.json.gz")).write_bytes(
            gzip.compress(v0.canonical(ledger), mtime=0))
        curve = v1.curve(ledger)
        (out / (prefix + "_equity.json")).write_bytes(v0.canonical(curve))
        for filename, keys, rows in (
                (prefix + "_equity.csv",
                 ("timestamp", "equityJpy", "cashJpy", "grossExposureJpy",
                  "utilization", "drawdownPct", "equityValid"), curve),
                (prefix + "_daily.csv",
                 ("session", "cashJpy", "equityJpy", "certified", "dailyReturn"),
                 result[short][name]["daily"])):
            with (out / filename).open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=keys)
                writer.writeheader()
                writer.writerows(rows)
        (out / (prefix + "_buckets.json")).write_bytes(
            v0.canonical(result[short][name]["buckets"]))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for arm in v0.ARMS:
        short = "IM" if arm == v0.IM else "R1"
        fig, ax = plt.subplots(figsize=(11, 4))
        for name in ("R50_A_CONTROL", NAME):
            points = v1.curve(replays[arm, name])
            times = [dt.datetime.fromisoformat(x["timestamp"]) for x in points]
            values = [float(x["equityJpy"]) if x["equityJpy"] is not None
                      else math.nan for x in points]
            ax.plot(times, values, label=short + " " + name, linewidth=1)
        ax.set_title("Experimental Development " + short + " frozen Capital × EXIT")
        ax.set_ylabel("Certified as-of equity JPY (null gaps)")
        ax.grid(alpha=.3)
        ax.legend(fontsize=7)
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(out / (short + "_asset_curve.png"), dpi=120)
        plt.close(fig)
    (out / "scorecard.json").write_bytes(v0.canonical(result))
    (out / "paired_layer_a.json").write_bytes(v0.canonical(paired))
    (out / "decision_trace.json.gz").write_bytes(
        gzip.compress(v0.canonical(trace), mtime=0))
    (out / "decision_support.json").write_bytes(v0.canonical(support))
    (out / "selection.json").write_bytes(v0.canonical(decision))
    (out / "manifest.json").write_bytes(v0.canonical({
        "schema": "phase57-r53-zero-fit-finite-result-v1",
        "protocolSha256": sha(PRECOMMIT),
        "savedPredictionSha256": sha(prediction_path), "newFits": 0,
        "candidateCount": 1, "replayAbIdentical": True,
        "archivedR50ControlByteIdentical": True, "sessions": p["sessions"],
        "filesSha256": {file.name: sha(file) for file in sorted(out.iterdir())
                        if file.is_file()},
        "providerRequests": 0, "protectedOpened": 0, "safety": v0.SAFETY}))
    print(v0.canonical({"stage": "FINITE_COMPLETE", "selection": decision["selection"],
                        "imFinalEquityJpy": result["IM"][NAME]["portfolio"]["finalEquityJpy"],
                        "newFits": 0}).decode().strip(), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "finite"), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prediction", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "preflight":
        args.out.write_bytes(v0.canonical(preflight(args.source, args.prediction)))
    else:
        finite(args.source, args.prediction, args.out)


if __name__ == "__main__":
    main()
