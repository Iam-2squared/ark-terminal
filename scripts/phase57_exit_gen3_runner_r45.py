"""R45 one-shot finite classifiers and immutable-prediction causal replay.

Prepare and fit/replay are separate workflow steps. No scorecard, candidate
selection or promotion is performed here. The decision runtime receives only
three scores and a current-only causal fact envelope; no label availability.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import importlib.metadata
import json
import os
from pathlib import Path
import pickle
import platform
import subprocess
import uuid
import warnings

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning

from scripts import phase57_exit_finite_r36 as r36
from scripts import phase57_exit_gen3_data_r45 as data_builder
from scripts import phase57_exit_gen3_preflight_r45 as preflight
from scripts import phase57_exit_gen3_runtime_r45 as runtime


ROOT = Path(__file__).resolve().parents[1]
HEADS = runtime.HEADS
require = r36.require
sha = r36.sha
write_json = r36.write_json
SAFETY = dict(r36.SAFETY)


def support_slices(data, protocol: dict) -> tuple[list[tuple], list[dict]]:
    """Check every fold/arm/head before the first estimator can be constructed."""
    require(data.targets.shape == (len(data.sessions), 3), "TARGET_SHAPE")
    require(np.all(np.isnan(data.targets[data.now == 925])), "TERMINAL_TARGET_PRESENT")
    codes = {s: i for i, s in enumerate(data.session_names)}
    gate = protocol["supportGate"]
    slices, rows = [], []
    scored_seen: set[str] = set()
    for fold in protocol["split"]["folds"]:
        require(not set(fold["train"]) & set(fold["score"]), "TRAIN_SCORE_OVERLAP")
        require(not scored_seen & set(fold["score"]), "DUPLICATE_SCORE_SESSION")
        scored_seen.update(fold["score"])
        train_sessions = [codes[s] for s in fold["train"]]
        score_sessions = [codes[s] for s in fold["score"]]
        for arm_code, arm in enumerate(protocol["entryArms"]):
            base = np.flatnonzero((data.arms == arm_code) & np.isin(data.sessions, train_sessions))
            score = np.flatnonzero((data.arms == arm_code) & np.isin(data.sessions, score_sessions)
                                   & (data.now != 925))
            require(len(score) > 0, "EMPTY_SCORE_ARM_FOLD")
            for head, name in enumerate(HEADS):
                # Independent target eligibility, never the intersection of heads.
                train = base[data.fresh[base] & np.isfinite(data.targets[base, head])]
                values, counts = np.unique(data.targets[train, head], return_counts=True)
                require(values.tolist() == [0.0, 1.0], "CLASS_SUPPORT_MUST_BE_ZERO_ONE")
                n_opp = len(np.unique(data.entries[train]))
                n_sessions = len(np.unique(data.sessions[train]))
                require(len(train) >= gate["minimumRowsPerFoldArmHead"], "INSUFFICIENT_TRAIN_ROWS")
                require(int(counts.min()) >= gate["minimumClassRows"], "INSUFFICIENT_CLASS_ROWS")
                require(n_opp >= gate["minimumOpportunities"], "INSUFFICIENT_TRAIN_OPPORTUNITIES")
                require(n_sessions >= gate["minimumSessions"], "INSUFFICIENT_TRAIN_SESSIONS")
                slices.append((fold, arm, head, train, score))
                rows.append({"fold": fold["fold"], "arm": arm, "head": name,
                             "trainRows": len(train), "scoreRows": len(score),
                             "classRows": {"0": int(counts[0]), "1": int(counts[1])},
                             "opportunities": n_opp, "sessions": n_sessions})
    require(len(slices) == protocol["execution"]["folds"] * 2 * 3, "SUPPORT_SLICE_COUNT")
    return slices, rows


def build_model(spec: dict):
    require(spec["family"] == "HGB", "UNREGISTERED_MODEL_FAMILY")
    return HistGradientBoostingClassifier(**spec["parameters"])


def fit_predictions(data, out: Path, protocol: dict) -> tuple[dict, dict]:
    require(getattr(data, "pattern_computed", False) is True, "SUPPORT_ONLY_CACHE_CANNOT_FIT")
    slices, support = support_slices(data, protocol)
    require(not any((out / name).exists() for name in (
        "models", "fit-start.json", "fit-progress.jsonl", "fit-receipt.json", "oof-predictions.npz")),
        "ONE_SHOT_FIT_OUTPUT_ALREADY_EXISTS")
    require(protocol == runtime.load_protocol(), "R45_EXACT_FIT_PROTOCOL")
    specs = protocol["predictionSpecs"]
    require(len(specs) == 1 and len({s["specId"] for s in specs}) == 1, "ONE_UNIQUE_SPEC_REQUIRED")
    require(protocol["execution"]["expectedModelFitCount"] == 24, "FIT_BUDGET_NOT_24")
    write_json(out / "support-gate.json", {"status": "PASS_BEFORE_ANY_FIT", "slices": support,
                                         "modelFits": 0, "fallback": False})
    write_json(out / "fit-start.json", {"status": "FITTING_AUTHORIZED_SUPPORT_COMPLETE",
                "expectedModelFits": 24, "candidateCount": len(protocol["candidates"]), "safety": SAFETY})
    model_dir = out / "models"
    model_dir.mkdir(parents=True, exist_ok=False)
    predictions = {s["specId"]: np.full((len(data.sessions), 3), np.nan, dtype=np.float32) for s in specs}
    model_rows = []
    with (out / "fit-progress.jsonl").open("xb") as journal:
        for fold, arm, head, train, score in slices:
            weights = r36.weights_for(data, train)
            target = data.targets[train, head].astype(np.int8)
            for spec in specs:
                sid = spec["specId"]
                dense = spec["family"] == "HGB"
                include_pattern = spec["featureSet"] == "CORE_CALENDAR_FACTS_PATTERN187"
                require(dense and include_pattern, "R45_HGB_PATTERN_ONLY")
                x_train, x_score, encoder, imputer, scaler = r36._fit_preprocess(
                    data, train, score, include_pattern, dense, not dense)
                model = build_model(spec)
                identity = {"ordinal": len(model_rows) + 1, "spec": sid,
                            "fold": fold["fold"], "arm": arm, "head": HEADS[head]}
                journal.write(r36.canonical({**identity, "status": "FIT_ATTEMPT_STARTED"})); journal.flush()
                if not model_rows:
                    print("FITTING_STARTED " + r36.canonical({"expectedModelFits": 24,
                          "candidateCount": len(protocol["candidates"])}).decode().strip(), flush=True)
                with warnings.catch_warnings():
                    warnings.simplefilter("error", ConvergenceWarning)
                    model.fit(x_train, target, sample_weight=weights)
                require(model.classes_.tolist() == [0, 1], "MODEL_CLASS_ORDER")
                scores = model.predict_proba(x_score)[:, 1]
                require(np.all(np.isfinite(scores)) and np.all((scores >= 0) & (scores <= 1)),
                        "INVALID_CLASSIFIER_SCORE")
                predictions[sid][score, head] = scores.astype(np.float32)
                name = f"{sid}__F{fold['fold']}__{arm}__{HEADS[head]}.joblib"
                path = model_dir / name
                require(not path.exists(), "MODEL_BUNDLE_EXISTS")
                bundle = {"spec": spec, "fold": fold["fold"], "arm": arm, "head": HEADS[head],
                          "model": model, "encoder": encoder, "imputer": imputer, "scaler": scaler,
                          "categoricalNames": data.categorical_names,
                          "numericNames": data.numeric_names,
                          "patternNames": data.pattern_names if include_pattern else [],
                          "categoricalRepresentation": "data/categorical-representation.json",
                          "calibratedProbabilityClaim": False}
                joblib.dump(bundle, path, compress=3)
                # Persist exact train supports and actual weight vectors for audit.
                support_path=model_dir/(name+'.support.npz')
                with support_path.open('xb') as sf:
                    np.savez_compressed(sf, trainIndices=train, scoreIndices=score, weights=weights)

                model_rows.append({**identity, "file": name, "sha256": sha(path),
                                   "trainRows": len(train), "scoreRows": len(score),
                                   "featureColumns": int(x_train.shape[1]),
                                   "supportFile": support_path.name, "supportSha256":sha(support_path)})
                journal.write(r36.canonical({**identity, "status": "FIT_AND_BUNDLE_COMPLETED",
                                            "sha256": sha(path)})); journal.flush()
                print(r36.canonical({**identity, "status": "FIT_COMPLETED"}).decode().strip(), flush=True)
    require(len(model_rows) == 24, "MODEL_FIT_COUNT_NOT_24")
    score_names = {s for f in protocol["split"]["folds"] for s in f["score"]}
    score_codes = [i for i, s in enumerate(data.session_names) if s in score_names]
    scored = np.isin(data.sessions, score_codes) & (data.now != 925)
    for sid, values in predictions.items():
        require(np.all(np.isfinite(values[scored])), "MISSING_OOF_SCORES:" + sid)
        require(np.all(np.isnan(values[~scored])), "SCORES_OUTSIDE_OOF_OR_TERMINAL:" + sid)
    pred_path = out / "oof-predictions.npz"
    with pred_path.open("xb") as fh:
        np.savez_compressed(fh, **predictions)
    receipt = {"schemaVersion": "phase57-exit-gen3-fit-r45-v1", "modelFits": len(model_rows),
               "models": model_rows, "predictionSha256": sha(pred_path), "heads": list(HEADS),
               "predictionSpecs": 1, "calibratedProbabilities": False, "safety": SAFETY,
               "providerRequests": 0, "protectedPartitionsOpened": 0}
    write_json(out / "fit-receipt.json", receipt)
    return predictions, receipt


def position(data, index: int) -> dict:
    """Transport np.float32 to Python scalars; leave the frozen R36 untouched."""
    result = {}
    for j, name in enumerate(data.numeric_names):
        if name.startswith("position."):
            value = float(data.numeric[index, j])
            result[name.removeprefix("position.")] = value if np.isfinite(value) else None
    return result


def fact_envelope(data,index):
    values={k:float(v) if np.isfinite(v) else None for k,v in zip(data_builder.FACT_NAMES,data.fact_values[index])}
    integer=('weakRun','signalTrueN','signalFalseN','signalUnknownN','signalLossN','signalRecoveryN',
             'stateRecovery','failedRecovery','higherHigh','higherLow','lowerHigh','lowerLow','newPeak')
    for k in integer:
        if values[k] is not None: values[k]=int(values[k])
    now=int(data.now[index])
    return dict(now=now,maxKnownAt=now,maxBarEnd=now,fresh=bool(data.fresh[index]),values=values)


def replay_candidate(data, scores: np.ndarray, candidate: dict, protocol: dict,
                     *, neutral: bool = False, trace=None) -> list[dict]:
    """Choose action before reading execution prices or evaluator geometry."""
    require(scores.shape == (len(data.sessions), 3), "REPLAY_SCORE_SHAPE")
    score_sessions = {s for f in protocol["split"]["folds"] for s in f["score"]}
    score_codes = [i for i, s in enumerate(data.session_names) if s in score_sessions]
    groups = collections.defaultdict(list)
    for idx in np.flatnonzero(np.isin(data.sessions, score_codes)):
        groups[int(data.entries[idx])].append(int(idx))
    rows = []
    for entry_code in sorted(groups):
        sequence = sorted(groups[entry_code], key=lambda i: int(data.now[i]))
        require(int(data.now[sequence[-1]]) == 925, "MISSING_TERMINAL_CHECKPOINT")
        require(len({int(data.now[i]) for i in sequence}) == len(sequence), "DUPLICATE_CHECKPOINT_NOW")
        entry = data.entry_rows[data.entry_ids[entry_code]]
        memory = runtime.Memory(); chosen = None; trigger = None; missing_refs = 0; missing_events=[]
        for idx in sequence:
            now = int(data.now[idx])
            facts=fact_envelope(data,idx)
            result=({'action':'FORCE_TERMINAL' if now==925 else 'HOLD','authority':'FORCE_TERMINAL' if now==925 else 'NEUTRAL_DIAGNOSTIC','state':dict(lastNow=now,armed=False,dCount=0,pCount=0,neutralCount=0,probationRemaining=0,mode='OBSERVE')}
                    if neutral else runtime.intent(scores[idx].tolist(),facts,memory,candidate))
            memory=runtime.Memory(**result['state'])
            if trace is not None: trace({'sourceRowIndex':idx,'now':now,**result})
            if result["action"] == "HOLD":
                continue
            # Raw execution access begins only after runtime has emitted an action.
            path = data.raw[entry["opportunity"]]["today"]
            if result["action"] == "FORCE_TERMINAL":
                require(now == 925, "TERMINAL_ACTION_BEFORE_925")
                terminal = r36.execution.terminal_execution_reference(path)
                trigger = idx
                if terminal["status"] == "RESOLVED_TERMINAL_AUCTION":
                    chosen = (float(terminal["price"]), 930, "FORCED_TERMINAL")
                break
            require(result["action"] == "EXIT_INTENT", "UNREGISTERED_RUNTIME_ACTION")
            ref = r36.execution.ordinary_execution_reference(entry["session"], now, path)
            if ref["status"] == "RESOLVED_NEXT_SCHEDULED_OPEN":
                chosen = (float(ref["price"]), int(ref["referenceStart"]), "MODEL_EXIT")
                trigger = idx
                break
            missing_refs += 1
            missing_events.append({"now":now,"authority":result["authority"],"state":result["state"],"reference":ref["referenceStart"]})
        require(trigger is not None, "NO_EXIT_OR_TERMINAL_DECISION")
        # Everything below is evaluator-only and cannot alter a chosen action.
        path = data.raw[entry["opportunity"]]["today"]
        price = chosen[0] if chosen else None
        minute = chosen[1] if chosen else None
        pos = position(data, trigger)
        peak, peak_at = pos.get("observedRunningHigh"), pos.get("peakConfirmedAt")
        if price is None or not r36.finite(peak) or not r36.finite(peak_at):
            peak = peak_at = None
        metrics = r36.evaluate_capture(
            entry_price=float(entry["price"]), entry_minute=int(entry["entryMinute"]),
            exit_price=price, exit_minute=minute, cost_pp=0.05,
            geometry=r36._ordered_geometry(data.opportunity_records[entry["opportunity"]]),
            post_entry_high=r36._post_entry_high(entry, path), owned_peak=peak,
            owned_peak_confirmed_at=int(peak_at) if peak_at is not None else None,
            owned_path_complete=bool(pos.get("fullOwnedPrefix") == 1),
        )
        later_highs = [] if minute is None else [float(r[2]) for r in path
            if len(r) == 7 and r36.finite(r[2]) and
            ((int(r[0]) if int(r[0]) == 930 else int(r[0]) + 1) > minute)]
        early = (None if minute is None else
                 100 * max(0.0, (max(later_highs, default=price) - price) / entry["price"]))
        rows.append({
            "candidateId": "HOLD_TO_TERMINAL_DIAGNOSTIC" if neutral else candidate["candidateId"],
            "nonselectableDiagnostic": neutral,
            "entryArm": protocol["entryArms"][int(data.arms[sequence[0]])],
            "fold": next(f["fold"] for f in protocol["split"]["folds"] if entry["session"] in f["score"]),
            "session": entry["session"], "opportunity": entry["opportunity"], "entryId": entry["entryId"],
            "entryMinute": entry["entryMinute"], "entryPrice": entry["price"],
            "decisionNow": int(data.now[trigger]),
            "decisionSourceRowIndex": trigger, "authority":result["authority"],
            "decisionState":result["state"], "decisionFacts":fact_envelope(data,trigger),
            "decisionScores":[float(v) if np.isfinite(v) else None for v in scores[trigger]],
            "missingIntentHistory":missing_events,
            "exitStatus": "RESOLVED" if chosen else "UNRESOLVED_TERMINAL_EXIT",
            "exitKind": chosen[2] if chosen else None, "exitMinute": minute, "exitPrice": price,
            "missingOrdinaryReferences": missing_refs,
            "activeMinutesHeld": None if minute is None else r36.execution.active_minutes(
                entry["session"], entry["entryMinute"], minute),
            "wallMinutesHeld": None if minute is None else minute - entry["entryMinute"],
            "earlyExitOpportunityCostPp": early,
            "netReturnPctBySellCost": {f"{cost:.2f}": None if price is None else
                100 * (price / entry["price"] - 1) - cost for cost in r36.COSTS},
            "metrics": metrics,
        })
    return rows


def replay_ab(data, out: Path, protocol: dict, fit_receipt: dict) -> dict:
    pred_path = out / "oof-predictions.npz"
    require(sha(pred_path) == fit_receipt["predictionSha256"], "SAVED_PREDICTION_HASH")
    candidates = protocol["candidates"]
    require(len(candidates) == 4, "CANDIDATE_COUNT_NOT_4")
    manifests = {}
    for label in ("run-a", "run-b"):
        run_dir = out / label
        run_dir.mkdir(exist_ok=False)
        # Each independent replay loads the same saved prediction bytes afresh.
        with np.load(pred_path, allow_pickle=False) as saved:
            predictions = {key: saved[key] for key in saved.files}
        require(set(predictions) == {s["specId"] for s in protocol["predictionSpecs"]}, "PREDICTION_SPEC_KEYS")
        for values in predictions.values():
            values.setflags(write=False)
        files = {}
        for candidate,neutral in [(c,False) for c in candidates]+[(candidates[0],True)]:
            cid='HOLD_TO_TERMINAL_DIAGNOSTIC' if neutral else candidate['candidateId']
            trace_name=cid+'.trace.jsonl.gz'
            with (run_dir/trace_name).open('xb') as f, gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0) as z:
                ledger=replay_candidate(data,predictions[candidate['predictionSpec']],candidate,protocol,
                    neutral=neutral,trace=lambda row:z.write(r36.canonical(row)))
            filename=cid+'.jsonl.gz'
            r36.write_jsonl_gz(run_dir/filename,ledger)
            files[filename]=sha(run_dir/filename)
            files[trace_name]=sha(run_dir/trace_name)
        write_json(run_dir / "ledger-hashes.json", files)
        manifests[label] = files
        require(sha(pred_path) == fit_receipt["predictionSha256"], "PREDICTIONS_CHANGED_DURING_REPLAY")
    require(manifests["run-a"] == manifests["run-b"], "REPLAY_AB_BYTES_DIFFER")
    receipt = {"runABByteIdentical": True, "ledgerHashes": manifests["run-a"],
               "candidatePoliciesReplayed": 4, "policyReplayPasses": 8,
               "neutralDiagnosticReplayPasses": 2, "selection": None,
               "scorecardsProduced": 0, "predictionRefits": 0}
    write_json(out / "replay-receipt.json", receipt)
    return receipt


def dependencies(protocol: dict) -> dict:
    expected = protocol["dependencies"]
    versions = {name: importlib.metadata.version(name) for name in
                ("numpy", "scipy", "scikit-learn", "pandas", "joblib")}
    require(all(versions[k] == expected[k] for k in versions), "DEPENDENCY_VERSION_MISMATCH")
    versions["python"] = platform.python_version()
    require(versions["python"].startswith(expected["python"] + "."), "PYTHON_VERSION_MISMATCH")
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        require(os.environ.get(key) == str(expected["threads"]), "THREAD_LIMIT:" + key)
    versions["threads"] = expected["threads"]
    return versions


def read_ci_receipt():
    path=Path(os.environ['R45_CONTRACT_RECEIPT'])
    receipt=r36.read_json(path)
    require(receipt['status']=='GEN3_PREFLIGHT_CONTRACT_PASS_NOT_PERFORMANCE_PASS','R45_CI_RECEIPT')
    return receipt


def prepare(core_root: Path, out: Path, workers: int, cache: Path,
            protocol: dict, execution_sha: str, dependency_versions: dict) -> None:
    require(not out.exists(), "PREPARE_OUTPUT_EXISTS")
    require(not cache.exists(), "PREPARED_CACHE_EXISTS")
    require(not cache.resolve().is_relative_to(out.resolve()), "PREPARED_CACHE_MUST_BE_OUTSIDE_ARTIFACT")
    require(workers == protocol["execution"]["workers"], "WORKER_COUNT_DRIFT")
    sources = preflight.source_manifest(ROOT)
    out.mkdir(parents=True, exist_ok=False)
    with (out / "protocol.json").open("xb") as fh:
        fh.write(runtime.PROTOCOL_PATH.read_bytes())
    write_json(out / "execution-identity.json", {"executionHead": execution_sha,
        "protocolSha256": sha(runtime.PROTOCOL_PATH), "sourceSha256": sources,
        "dependencies": dependency_versions, "safety": SAFETY})
    data = data_builder.build_data(core_root, out / "data", workers, protocol)
    ci=read_ci_receipt()
    for name,h in ci['support']['supportHashes'].items():
        require(sha(out/'data'/name)==h,'R45_PREPARED_SUPPORT_IDENTITY:'+name)
    _,support=support_slices(data,protocol)
    write_json(out/'support-only-before-fitting.json',{'status':'PASS','slices':support,'modelFits':0,'policyReplays':0,'performanceInspections':0})
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("xb") as fh:
        pickle.dump(data, fh, protocol=5)
    files = {str(p.relative_to(out)): sha(p) for p in sorted((out / "data").rglob("*")) if p.is_file()}
    write_json(out / "prepare-receipt.json", {"status": "PREPARED_NO_MODEL_FITS",
        "executionHead": execution_sha, "protocolSha256": sha(runtime.PROTOCOL_PATH),
        "sourceSha256": sources, "dependencies": dependency_versions,
        "preparedCacheSha256": sha(cache), "preparedDataHashes": files,
        "rows": len(data.sessions), "modelFits": 0, "candidateReplays": 0,
        "providerRequests": 0, "protectedPartitionsOpened": 0, "safety": SAFETY})
    print("PREPARED_NO_MODEL_FITS", flush=True)


def fit_replay(out: Path, cache: Path, protocol: dict, execution_sha: str,
               dependency_versions: dict) -> None:
    require((out / "prepare-receipt.json").is_file(), "PREPARATION_REQUIRED")
    require(not any((out / name).exists() for name in ("receipt.json", "models", "fit-start.json")),
            "ONE_SHOT_ALREADY_STARTED")
    receipt = r36.read_json(out / "prepare-receipt.json")
    require(receipt["executionHead"] == execution_sha, "PREPARE_EXECUTION_SHA_DRIFT")
    require(receipt["protocolSha256"] == sha(runtime.PROTOCOL_PATH) == sha(out / "protocol.json"),
            "PREPARE_PROTOCOL_DRIFT")
    require(receipt["sourceSha256"] == preflight.source_manifest(ROOT), "PREPARE_SOURCE_DRIFT")
    require(receipt["dependencies"] == dependency_versions, "PREPARE_DEPENDENCY_DRIFT")
    require(sha(cache) == receipt["preparedCacheSha256"], "PREPARED_CACHE_HASH_MISMATCH")
    for name, expected in receipt["preparedDataHashes"].items():
        require(sha(out / name) == expected, "PREPARED_DATA_HASH:" + name)
    # The own-process cache is deserialized only after its preparation hash check.
    with cache.open("rb") as fh:
        data = pickle.load(fh)
    _, fitted = fit_predictions(data, out, protocol)
    replay = replay_ab(data, out, protocol, fitted)
    write_json(out / "receipt.json", {
        "schemaVersion": "phase57-exit-gen3-pending-audit-r45-v1",
        "status": "AWAITING_POST_RUN_AUDIT", "executionHead": execution_sha,
        "protocolSha256": sha(runtime.PROTOCOL_PATH), "sourceSha256": receipt["sourceSha256"],
        "preparedCacheSha256": receipt["preparedCacheSha256"],
        "dependencies": dependency_versions, "modelFits": fitted["modelFits"],
        "predictionSha256": fitted["predictionSha256"], **replay,
        "providerRequests": 0, "protectedPartitionsOpened": 0, "safety": SAFETY,
        "claims": {"exitFrozen": False, "selected": False, "portfolioReplayed": False,
                   "independentSecondFullModelFit": False, "calibratedProbabilities": False},
    })
    print("AWAITING_POST_RUN_AUDIT", flush=True)


def partial_failure(out: Path, phase: str, error: Exception) -> Path:
    # A repeated failed invocation can add evidence but never replace a receipt.
    location = out if out.is_dir() else out.parent
    location.mkdir(parents=True, exist_ok=True)
    path = location / ("partial-failure-" + uuid.uuid4().hex + ".json")
    write_json(path, {"status": "FAILED_NO_SILENT_RESUME", "phase": phase,
        "exception": type(error).__name__, "reason": str(error),
        "persistedModelBundles": len(list((out / "models").glob("*.joblib"))),
        "selection": None, "providerRequests": 0, "protectedPartitionsOpened": 0, "safety": SAFETY})
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("prepare", "fit-replay"), required=True)
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--prepared-cache", type=Path, required=True)
    args = parser.parse_args()
    try:
        require(os.environ.get("GITHUB_ACTIONS") == "true", "REAL_FINITE_RUN_GITHUB_ACTIONS_ONLY")
        execution_sha = os.environ["ARK_GEN3_EXECUTION_SHA"]
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        require(head == execution_sha, "EXECUTION_GIT_HEAD_MISMATCH")
        protocol = runtime.load_protocol()
        versions = dependencies(protocol)
        if args.phase == "prepare":
            prepare(args.core_root, args.out, args.workers, args.prepared_cache,
                    protocol, execution_sha, versions)
        else:
            fit_replay(args.out, args.prepared_cache, protocol, execution_sha, versions)
    except Exception as error:
        partial_failure(args.out, args.phase, error)
        raise


if __name__ == "__main__":
    main()
