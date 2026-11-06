"""One-shot R45 learning and causal replay. Performance scoring stays deferred."""
from __future__ import annotations
import argparse
import collections
import json
import os
from pathlib import Path
import pickle
import subprocess
import warnings

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from scripts import phase57_exit_finite_r36 as r36
from scripts import phase57_exit_gen3_runtime_r45 as runtime
from scripts import phase57_exit_gen3_data_r45 as builder
from scripts.phase57_exit_gen2_runner_r41 import position, dependencies, partial_failure

ROOT = runtime.ROOT
HEADS = runtime.HEADS


def fit_predictions(data, out, protocol):
    slices, support = builder.support_slices(data, protocol)
    r36.require(data.pattern.shape == (len(data.now), 187) and len(data.numeric_names) == 106,
                'R45_FULL_FEATURE_MATRIX_REQUIRED')
    r36.require(not any((out / n).exists() for n in ('models', 'fit-start.json', 'oof-predictions.npz', 'fit-progress.jsonl')),
                'R45_ONE_SHOT_FIT_EXISTS')
    spec = protocol['predictionSpecs'][0]
    r36.require(len(protocol['predictionSpecs']) == 1 and spec['family'] == 'HGB', 'R45_EXACT_MODEL_FAMILY')
    r36.write_json(out / 'fit-support.json', {'slices': support, 'status': 'ALL_24_PASS_BEFORE_FIT'})
    r36.write_json(out / 'fit-start.json', {'expectedModelFits': 24, 'candidateCount': 4, 'protocolSha256': runtime.PROTOCOL_SHA256})
    model_dir = out / 'models'; model_dir.mkdir(exist_ok=False)
    predictions = np.full((len(data.now), 3), np.nan, np.float32); models = []
    with (out / 'fit-progress.jsonl').open('xb') as journal:
        for fold, arm, h, train, score in slices:
            identity = {'ordinal': len(models) + 1, 'fold': fold['fold'], 'arm': arm, 'head': HEADS[h], 'spec': spec['specId']}
            journal.write(r36.canonical({**identity, 'status': 'FIT_ATTEMPT_STARTED'})); journal.flush()
            weights = r36.weights_for(data, train)
            x_train, x_score, encoder, imputer, scaler = r36._fit_preprocess(data, train, score, True, True, False)
            r36.require(scaler is None, 'R45_HGB_MUST_BE_UNSCALED')
            model = HistGradientBoostingClassifier(**spec['parameters'])
            with warnings.catch_warnings():
                warnings.simplefilter('error', ConvergenceWarning)
                model.fit(x_train, data.targets[train, h].astype(np.int8), sample_weight=weights)
            r36.require(model.classes_.tolist() == [0, 1], 'R45_CLASS_ORDER')
            scores = model.predict_proba(x_score)[:, 1]
            r36.require(np.all(np.isfinite(scores)) and np.all((scores >= 0) & (scores <= 1)), 'R45_INVALID_SCORE')
            predictions[score, h] = scores.astype(np.float32)
            name = f"F{fold['fold']}__{arm}__{HEADS[h]}"
            model_file = model_dir / (name + '.joblib')
            joblib.dump({'spec': spec, 'fold': fold['fold'], 'arm': arm, 'head': HEADS[h], 'model': model,
                'encoder': encoder, 'imputer': imputer, 'scaler': None, 'numericNames': data.numeric_names,
                'categoricalNames': data.categorical_names, 'patternNames': data.pattern_names,
                'calibratedProbabilityClaim': False}, model_file, compress=3)
            with (model_dir / (name + '-train-support.npz')).open('xb') as f:
                np.savez_compressed(f, trainIndices=train, weights=weights)
            models.append({**identity, 'file': model_file.name, 'sha256': r36.sha(model_file),
                'weightFile': name + '-train-support.npz', 'weightSha256': r36.sha(model_dir / (name + '-train-support.npz')),
                'trainRows': len(train), 'scoreRows': len(score), 'featureColumns': int(x_train.shape[1])})
            journal.write(r36.canonical({**identity, 'status': 'FIT_COMPLETED', 'sha256': r36.sha(model_file)})); journal.flush()
            print(r36.canonical({**identity, 'status': 'FIT_COMPLETED'}).decode().strip(), flush=True)
    r36.require(len(models) == 24, 'R45_FIT_COUNT')
    names = {s for f in protocol['split']['folds'] for s in f['score']}
    scored = np.isin(data.sessions, [i for i, s in enumerate(data.session_names) if s in names]) & (data.now != 925)
    r36.require(np.all(np.isfinite(predictions[scored])) and np.all(np.isnan(predictions[~scored])), 'R45_OOF_MASK')
    with (out / 'oof-predictions.npz').open('xb') as f:
        np.savez_compressed(f, **{spec['specId']: predictions})
    receipt = {'modelFits': 24, 'models': models, 'predictionSha256': r36.sha(out / 'oof-predictions.npz'),
               'heads': list(HEADS), 'calibratedProbabilities': False, 'safety': protocol['safety']}
    r36.write_json(out / 'fit-receipt.json', receipt)
    return receipt


def decision_facts(data, idx, protocol):
    values = {}
    for name in protocol['features']['decisionFactFields']:
        value = float(data.numeric[idx, data.numeric_names.index('facts.' + name)])
        values[name] = value if np.isfinite(value) else None
    now = int(data.now[idx])
    return {'now': now, 'maxKnownAt': now, 'maxBarEnd': now, 'fresh': bool(data.fresh[idx]), 'values': values}


def replay_candidate(data, scores, candidate, protocol, *, neutral=False):
    r36.require(scores.shape == (len(data.now), 3), 'R45_REPLAY_SCORE_SHAPE')
    score_sessions = {s for f in protocol['split']['folds'] for s in f['score']}
    codes = [i for i, s in enumerate(data.session_names) if s in score_sessions]
    groups = collections.defaultdict(list)
    for idx in np.flatnonzero(np.isin(data.sessions, codes)): groups[int(data.entries[idx])].append(int(idx))
    rows = []
    for entry_code in sorted(groups):
        seq = sorted(groups[entry_code], key=lambda i: int(data.now[i]))
        entry = data.entry_rows[data.entry_ids[entry_code]]
        r36.require(int(data.now[seq[-1]]) == 925, 'R45_MISSING_TERMINAL_CHECKPOINT')
        state = runtime.initial_state(); chosen = None; trigger = None; missing_refs = []
        authorities = collections.Counter(); trace_hash = __import__('hashlib').sha256()
        for idx in seq:
            now = int(data.now[idx]); facts = decision_facts(data, idx, protocol)
            result = ({'action': 'FORCE_TERMINAL' if now == 925 else 'HOLD',
                       'authority': 'NEUTRAL_DIAGNOSTIC', 'state': state} if neutral else
                      runtime.intent(entry['session'], facts, scores[idx].tolist(), state, candidate))
            state = result['state']; authorities[result['authority']] += 1
            trace_hash.update(r36.canonical({'row': idx, **result}))
            if result['action'] == 'HOLD': continue
            # No execution reference or future evaluator is read until after intent.
            path = data.raw[entry['opportunity']]['today']
            if result['action'] == 'FORCE_TERMINAL':
                terminal = r36.execution.terminal_execution_reference(path); trigger = idx
                if terminal['status'] == 'RESOLVED_TERMINAL_AUCTION':
                    chosen = (float(terminal['price']), 930, 'FORCED_TERMINAL')
                break
            r36.require(result['action'] == 'EXIT_INTENT', 'R45_ACTION_ENUM')
            ref = r36.execution.ordinary_execution_reference(entry['session'], now, path)
            if ref['status'] == 'RESOLVED_NEXT_SCHEDULED_OPEN':
                chosen = (float(ref['price']), int(ref['referenceStart']), 'MODEL_EXIT'); trigger = idx; break
            missing_refs.append({'decisionNow': now, 'authority': result['authority'], 'status': ref['status']})
        r36.require(trigger is not None, 'R45_NO_TERMINAL_OR_EXIT')
        # Frozen evaluator-only formulas below cannot alter chosen decisions.
        path = data.raw[entry['opportunity']]['today']
        price = chosen[0] if chosen else None; minute = chosen[1] if chosen else None
        pos = position(data, trigger)
        peak, peak_at = pos.get('observedRunningHigh'), pos.get('peakConfirmedAt')
        if price is None or not r36.finite(peak) or not r36.finite(peak_at): peak = peak_at = None
        metrics = r36.evaluate_capture(entry_price=float(entry['price']), entry_minute=int(entry['entryMinute']),
            exit_price=price, exit_minute=minute, cost_pp=0.05,
            geometry=r36._ordered_geometry(data.opportunity_records[entry['opportunity']]),
            post_entry_high=r36._post_entry_high(entry, path), owned_peak=peak,
            owned_peak_confirmed_at=int(peak_at) if peak_at is not None else None,
            owned_path_complete=bool(pos.get('fullOwnedPrefix') == 1))
        later = [] if minute is None else [float(r[2]) for r in path if len(r) == 7 and r36.finite(r[2]) and
                   ((int(r[0]) if int(r[0]) == 930 else int(r[0]) + 1) > minute)]
        early = None if minute is None else 100 * max(0., (max(later, default=price) - price) / entry['price'])
        rows.append({'candidateId': 'HOLD_TO_TERMINAL_DIAGNOSTIC' if neutral else candidate['candidateId'],
            'nonselectableDiagnostic': neutral, 'entryArm': entry['entryArm'],
            'fold': next(f['fold'] for f in protocol['split']['folds'] if entry['session'] in f['score']),
            'session': entry['session'], 'opportunity': entry['opportunity'], 'entryId': entry['entryId'],
            'entryMinute': entry['entryMinute'], 'entryPrice': entry['price'], 'decisionNow': int(data.now[trigger]),
            'exitStatus': 'RESOLVED' if chosen else 'UNRESOLVED_TERMINAL_EXIT', 'exitKind': chosen[2] if chosen else None,
            'exitMinute': minute, 'exitPrice': price, 'missingOrdinaryReferences': len(missing_refs),
            'missingReferenceDetails': missing_refs, 'authority': result['authority'], 'authorityCounts': dict(authorities),
            'decisionState': state, 'decisionFacts': decision_facts(data, trigger, protocol),
            'decisionScores': [float(v) if np.isfinite(v) else None for v in scores[trigger]],
            'decisionSequenceSha256': trace_hash.hexdigest(),
            'activeMinutesHeld': None if minute is None else r36.execution.active_minutes(entry['session'], entry['entryMinute'], minute),
            'wallMinutesHeld': None if minute is None else minute - entry['entryMinute'],
            'earlyExitOpportunityCostPp': early, 'netReturnPctBySellCost': {
                f'{cost:.2f}': None if price is None else 100 * (price / entry['price'] - 1) - cost for cost in r36.COSTS},
            'metrics': metrics})
    return rows


def replay_ab(data, out, protocol, fitted):
    manifests = {}
    for label in ('run-a', 'run-b'):
        r36.require(r36.sha(out / 'oof-predictions.npz') == fitted['predictionSha256'], 'R45_SAVED_PREDICTION_HASH')
        run = out / label; run.mkdir(exist_ok=False); hashes = {}
        with np.load(out / 'oof-predictions.npz', allow_pickle=False) as saved:
            r36.require(saved.files == [protocol['predictionSpecs'][0]['specId']], 'R45_PREDICTION_SPEC')
            scores = saved[saved.files[0]]
        scores.setflags(write=False)
        for candidate in protocol['candidates']:
            name = candidate['candidateId'] + '.jsonl.gz'
            r36.write_jsonl_gz(run / name, replay_candidate(data, scores, candidate, protocol))
            hashes[name] = r36.sha(run / name)
        name = 'HOLD_TO_TERMINAL_DIAGNOSTIC.jsonl.gz'
        r36.write_jsonl_gz(run / name, replay_candidate(data, np.full((len(data.now), 3), np.nan),
                                                      protocol['candidates'][0], protocol, neutral=True))
        hashes[name] = r36.sha(run / name); manifests[label] = hashes
        r36.write_json(run / 'ledger-hashes.json', hashes)
    r36.require(manifests['run-a'] == manifests['run-b'], 'R45_REPLAY_AB_MISMATCH')
    return {'candidatePoliciesReplayed': 4, 'policyReplayPasses': 8, 'neutralDiagnosticReplayPasses': 2,
            'runABByteIdentical': True, 'ledgerHashes': manifests['run-a'], 'scorecardsProduced': 0,
            'selection': None, 'gen3PerformanceInspected': False, 'predictionRefits': 0}


def main():
    from scripts import phase57_exit_gen3_preflight_r45 as preflight
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=('support', 'prepare', 'fit-replay'), required=True)
    parser.add_argument('--core-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--contract-receipt', type=Path)
    args = parser.parse_args(); p = runtime.load_protocol()
    try:
        r36.require(os.environ.get('GITHUB_ACTIONS') == 'true', 'R45_WORKFLOW_ONLY')
        execution = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True, cwd=ROOT).strip()
        versions = dependencies(p); sources = preflight.source_manifest(ROOT)
        if args.phase in ('support', 'prepare'):
            r36.require(not args.out.exists(), 'R45_OUTPUT_EXISTS'); args.out.mkdir(parents=True)
            r36.write_json(args.out / 'execution-identity.json', {'executionSha': execution,
                'protocolSha256': runtime.PROTOCOL_SHA256, 'sourceHashes': sources, 'dependencies': versions})
            data = builder.build_data(args.core_root, args.out / 'data', support_only=args.phase == 'support')
            _, support = builder.support_slices(data, p)
            r36.write_json(args.out / 'support-gate.json', {'status': 'ALL_24_PASS_BEFORE_FIT', 'slices': support,
                'modelFits': 0, 'policyReplays': 0, 'performanceInspected': False})
            if args.phase == 'support': return
            r36.require(not args.cache.exists() and not args.cache.resolve().is_relative_to(args.out.resolve()), 'R45_CACHE_PATH')
            args.cache.parent.mkdir(parents=True, exist_ok=True)
            with args.cache.open('xb') as f: pickle.dump(data, f, protocol=5)
            r36.write_json(args.out / 'prepare-receipt.json', {'cacheSha256': r36.sha(args.cache),
                'sourceHashes': sources, 'executionSha': execution, 'protocolSha256': runtime.PROTOCOL_SHA256,
                'dependencies': versions, 'files': {str(f.relative_to(args.out)): r36.sha(f) for f in args.out.rglob('*') if f.is_file()}})
            return
        r36.require(args.contract_receipt is not None, 'R45_LAUNCH_RECEIPT_REQUIRED')
        authorization = r36.read_json(args.contract_receipt)
        r36.require(authorization['status'] == 'R45_LAUNCH_AUTHORIZED' and authorization['executionSha'] == execution
                    and authorization['sourceHashes'] == sources, 'R45_LAUNCH_AUTHORIZATION')
        prepared = r36.read_json(args.out / 'prepare-receipt.json')
        r36.require(prepared['executionSha'] == execution and prepared['sourceHashes'] == sources and
                    prepared['protocolSha256'] == runtime.PROTOCOL_SHA256 and prepared['dependencies'] == versions,
                    'R45_PREPARED_IDENTITY')
        r36.require(prepared['cacheSha256'] == r36.sha(args.cache), 'R45_PREPARED_CACHE_HASH')
        for name, digest in prepared['files'].items(): r36.require(r36.sha(args.out / name) == digest, 'R45_PREPARED_FILE_HASH')
        with args.cache.open('rb') as f: data = pickle.load(f)
        fitted = fit_predictions(data, args.out, p)
        replay = replay_ab(data, args.out, p, fitted)
        r36.write_json(args.out / 'receipt.json', {'schema': 'phase57-gen3-awaiting-audit-r45-v1',
            'status': 'AWAITING_POST_RUN_AUDIT', 'modelFits': 24, **replay, 'executionSha': execution,
            'protocolSha256': runtime.PROTOCOL_SHA256, 'sourceHashes': sources, 'dependencies': versions,
            'predictionSha256': fitted['predictionSha256'], 'providerRequests': 0, 'protectedPartitionsOpened': 0,
            'safety': p['safety'], 'finalExitFrozen': False, 'capitalIntegrated': False})
        print('AWAITING_POST_RUN_AUDIT', flush=True)
    except Exception as error:
        partial_failure(args.out, args.phase, error)
        raise


if __name__ == '__main__':
    main()
