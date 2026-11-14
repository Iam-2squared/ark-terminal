#!/usr/bin/env python3
"""Frozen four-prefix Development experiment; no provider, Validation or OOS access."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / 'predict/research/phase57-msh-entry-long-v1-fit-contract-v1.json'
CONTRACT_SHA = '64c20d785be5f23b0a9103f419726b191a12a58fd5d3a7ad5185c69f9644a938'
LEDGERS = {
    'features': ('phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz',
                 '73e566aba4d1a3f5af33b74be52ae90736c088b1091841f1eb44e93d5476084c'),
    'transfer': ('phase57-long-only-current-entry-transfer-v1-events.ndjson.gz',
                 'a36eecfed29aa0e9da50b051839578ca2e8f3a37d500de17bd6c3acfd8ce3a53'),
    'current': ('phase57-long-only-entry-filter-recovery-audit-v1-first-opportunities.json.gz',
                '74ca5797a117df37ec78f7e2f859a52ab634affa088fcdabd2a3a0ec4e16d30a'),
}
LEVELS = (1, 2, 3, 5)
CORE = ('frozenSelectorRidgeScore', 'frozenSelectorRidgeRank')
FOLDS = ((16, 31), (31, 46), (46, 61), (61, 76))
THRESHOLDS = (1.0, 2.0, 3.0)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def require(condition, message):
    if not condition:
        raise ValueError('PRE_FIT_OR_INTEGRITY_GATE_FAILED: ' + message)


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def pct(n, d):
    return 100.0 * n / d if d else None


def distribution(values):
    a = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    names = ('mean', 'median', 'p25', 'p75', 'p90', 'min', 'max')
    if not a.size:
        return dict(n=0, **dict.fromkeys(names))
    return dict(n=int(a.size), mean=float(a.mean()), median=float(np.median(a)),
                p25=float(np.quantile(a, .25)), p75=float(np.quantile(a, .75)),
                p90=float(np.quantile(a, .9)), min=float(a.min()), max=float(a.max()))


def grouped(rows):
    result = defaultdict(list)
    for row in sorted(rows, key=lambda r: (timestamp(r['decisionTimestamp']), r['ridgeRank'], r['symbol'])):
        result[row['symbolSessionId']].append(row)
    return dict(result)


def matrix(rows):
    return np.asarray([[r['ridgeScore'], r['ridgeRank']] for r in rows], dtype=float)


def classes(rows, field='ordinalClass'):
    return [sum(r['label'][field] == k for r in rows) for k in range(5)]


def hit(row, level, horizon='high30'):
    if horizon in ('high30', 'close30'):
        key = 'ordinalClass' if horizon == 'high30' else 'closeOrdinalClass'
        return row['label'][key] >= LEVELS.index(level) + 1
    value = row['transfer'].get(f'selectorOpportunity{level}')
    return None if value is None else bool(value)


def outcome_metrics(rows, horizon):
    result = {}
    for level in LEVELS:
        observed = [hit(r, level, horizon) for r in rows]
        valid = [v for v in observed if v is not None]
        result[str(level)] = {'hitN': sum(valid), 'evaluableN': len(valid),
                              'precisionPct': pct(sum(valid), len(valid))}
    return result


def evaluate(pool, entries, n_sessions, original_first):
    """Identical first-eligible cohort denominators, separate reference/horizon metrics."""
    first = {key: rows[0] for key, rows in grouped(pool).items()}
    selected = {r['symbolSessionId']: r for r in entries}
    require(len(entries) == len(selected), 'duplicate symbol-session ENTER')
    require(set(selected) <= set(first), 'entries outside evaluation pool')
    report = {'candidateSymbolSessions': len(first), 'enterCount': len(entries),
              'firstEntryCoveragePct': pct(len(entries), len(first)),
              'entriesPerSession': len(entries) / n_sessions, 'sessionCount': n_sessions}
    for horizon in ('high30', 'close30', 'session'):
        quality = outcome_metrics(entries, horizon)
        baseline = outcome_metrics(list(first.values()), horizon)
        for level in LEVELS:
            k = str(level)
            winners = {key for key, r in first.items() if hit(r, level, horizon) is True}
            admitted = winners & set(selected)
            timely = {key for key in admitted if timestamp(selected[key]['decisionTimestamp']) <
                      timestamp(first[key]['label']['windowEndTimestamp'])}
            remaining = {key for key in admitted if hit(selected[key], level, horizon) is True}
            quality[k].update(
                baselineFirstEligibleHitN=len(winners), admittedBaselineWinnerN=len(admitted),
                admissionPreservationPct=pct(len(admitted), len(winners)),
                admittedBeforeFirst30mWindowEndN=len(timely),
                timelyAdmissionPreservationPct=pct(len(timely), len(winners)),
                baselineWinnerAndRemainingN=len(remaining),
                remainingPreservationPct=pct(len(remaining), len(winners)),
                preservedPerSession=len(admitted) / n_sessions,
                entryTimeHitsPerSession=quality[k]['hitN'] / n_sessions,
                baselinePrecisionPct=baseline[k]['precisionPct'],
                enrichmentPp=(quality[k]['precisionPct'] - baseline[k]['precisionPct'])
                    if quality[k]['precisionPct'] is not None and baseline[k]['precisionPct'] is not None else None)
        report[horizon] = quality
    for name, references in [('firstEligible', first), ('firstOriginal', original_first)]:
        report[name + 'LatencyMinutes'] = distribution([
            (timestamp(r['decisionTimestamp']) - timestamp(references[r['symbolSessionId']]['decisionTimestamp'])).total_seconds() / 60
            for r in entries])
        report[name + 'ConsumedReturnBps'] = distribution([
            10000 * (r['decisionPrice'] / references[r['symbolSessionId']]['decisionPrice'] - 1) for r in entries])
    report['sameEventLatencyMinutes'] = distribution([0] * len(entries))
    report['sameEventConsumedReturnBps'] = distribution([0] * len(entries))
    report['strict30mMfePct'] = distribution([max(0, r['label']['highReturnPct']) for r in entries])
    report['strict30mTrueMaePct'] = {'n': 0, 'status': 'UNAVAILABLE_NOT_SAVED_IN_REUSED_LEDGERS'}
    report['sessionMfePct'] = distribution([r['transfer']['selectorMfePct'] for r in entries])
    report['sessionTrueMaePct'] = distribution([r['transfer']['selectorMaePct'] for r in entries])
    quality_mean = np.mean([v['precisionPct'] for v in report['high30'].values()]) if entries else 0
    preservation = [v['admissionPreservationPct'] for v in report['high30'].values()]
    report['frozenBalanceMetric'] = (float((quality_mean / 100 * np.mean(preservation) / 100 *
                                          len(entries) / len(first)) ** (1 / 3))
                                     if len(first) and all(v is not None for v in preservation) else None)
    return report


def replay(pool, threshold):
    entries, decisions, entered = [], [], set()
    for row in sorted(pool, key=lambda r: (timestamp(r['decisionTimestamp']), r['ridgeRank'], r['symbol'])):
        qualifies = row['expectedLevel'] >= threshold
        duplicate = row['symbolSessionId'] in entered
        action = 'ENTER' if qualifies and not duplicate else 'SKIP_THIS_DECISION'
        if action == 'ENTER':
            entries.append(row)
            entered.add(row['symbolSessionId'])
        decisions.append({'selectorEventId': row['selectorEventId'], 'threshold': threshold,
                          'fold': row['fold'], 'symbolSessionId': row['symbolSessionId'],
                          'action': action, 'scoreQualifies': qualifies,
                          'reason': 'ALREADY_ENTERED' if duplicate else 'SCORE_THRESHOLD',
                          'entryReferencePrice': row['decisionPrice'] if action == 'ENTER' else None})
    return entries, decisions


def event_metrics(pool, selected):
    result = {'eventN': len(pool), 'qualifiedEventN': len(selected),
              'qualificationRatePct': pct(len(selected), len(pool)),
              'independentTrades': False}
    for horizon in ('high30', 'close30'):
        base, quality = outcome_metrics(pool, horizon), outcome_metrics(selected, horizon)
        for level in LEVELS:
            k = str(level)
            quality[k].update(baselineHitN=base[k]['hitN'],
                              preservationPct=pct(quality[k]['hitN'], base[k]['hitN']))
        result[horizon] = quality
    return result


def current_baseline(pool, current, original_first, n_sessions):
    """Reuse unchanged actual first PASS; do not reinterpret cached ALREADY_ENTERED as ENTER."""
    first = {key: rows[0] for key, rows in grouped(pool).items()}
    actual_passes = [current[key] for key in first if current[key]['firstPassTimestamp'] is not None]
    exact = [r for r in pool if current[r['symbolSessionId']]['firstPassTimestamp'] is not None
             and timestamp(current[r['symbolSessionId']]['firstPassTimestamp']) == timestamp(r['decisionTimestamp'])
             and current[r['symbolSessionId']]['firstPassPrice'] == r['decisionPrice']]
    exact_metrics = evaluate(pool, exact, n_sessions, original_first)
    result = {'poolSymbolSessions': len(first), 'actualFirstPassCount': len(actual_passes),
              'actualFirstPassCoveragePct': pct(len(actual_passes), len(first)),
              'actualPassPerSession': len(actual_passes) / n_sessions,
              'strict30mExactEventMatchedPassCount': len(exact),
              'strict30mUnmatchedPassCount': len(actual_passes) - len(exact),
              'passBeforeFirstEligible': sum(timestamp(r['firstPassTimestamp']) <
                  timestamp(first[r['symbolSessionId']]['decisionTimestamp']) for r in actual_passes),
              'strict30mExactEventSubsetOnly': exact_metrics,
              'exactEventMetricsAreNotFullCurrentEntryPerformance': True,
              'actualPassSessionQuality': {}, 'sessionAdmissionPreservation': {}}
    passed_keys = {r['symbolSessionId'] for r in actual_passes}
    for level in LEVELS:
        vals = [(r.get('entryOutcome') or {}).get(f'opportunity{level}') for r in actual_passes]
        valid = [v for v in vals if v in (0, 1)]
        winners = {key for key, r in first.items() if hit(r, level, 'session') is True}
        result['actualPassSessionQuality'][str(level)] = {'hitN': sum(valid), 'evaluableN': len(valid),
                                                         'precisionPct': pct(sum(valid), len(valid))}
        result['sessionAdmissionPreservation'][str(level)] = {
            'hitN': len(winners), 'preservedN': len(winners & passed_keys),
            'preservationPct': pct(len(winners & passed_keys), len(winners)),
            'preservedPerSession': len(winners & passed_keys) / n_sessions}
    return result


def prepare_folds(rows, sessions):
    result = []
    for fold, (end_train, end_eval) in enumerate(FOLDS, 1):
        train_dates, eval_dates = sessions[:end_train], sessions[end_train:end_eval]
        train = [r for r in rows if r['sessionDate'] in train_dates and r['label']['labelable']]
        evaluation = [r for r in rows if r['sessionDate'] in eval_dates and r['label']['labelable']]
        X = matrix(train)
        require(len(train) > 0 and len(evaluation) > 0, f'fold {fold}: empty rows')
        means, std = X.mean(0), X.std(0, ddof=0)
        checks = {
            'trainRowsPositive': len(train) > 0, 'evalRowsPositive': len(evaluation) > 0,
            'allFiveTrainingClasses': all(classes(train)),
            'coreFinite': bool(np.isfinite(X).all() and np.isfinite(matrix(evaluation)).all()),
            'scalerFinite': bool(np.isfinite(means).all() and np.isfinite(std).all()),
            'stdPositive': bool((std > 0).all()),
            'noDuplicateEventId': len({r['selectorEventId'] for r in train + evaluation}) == len(train) + len(evaluation),
            'noSessionOverlap': not set(train_dates) & set(eval_dates),
            'noSymbolSessionOverlap': not {r['symbolSessionId'] for r in train} & {r['symbolSessionId'] for r in evaluation},
            'noFutureScalerData': max(train_dates) < min(eval_dates),
        }
        require(all(checks.values()), f'fold {fold}: {checks}')
        scaler = {'featureOrder': list(CORE), 'mean': means.tolist(), 'std': std.tolist(), 'ddof': 0,
                  'fitSessionDates': train_dates, 'fitEventIdsSha256': digest(canonical([r['selectorEventId'] for r in train]))}
        info = {'fold': fold, 'trainSessions': train_dates, 'evalSessions': eval_dates,
                'trainRows': len(train), 'evalRows': len(evaluation), 'trainClassCounts': classes(train),
                'evalClassCounts': classes(evaluation), 'scaler': scaler,
                'scalerSha256': digest(canonical(scaler)), 'preFitChecks': checks}
        result.append((train, evaluation, info))
    return result


def read_inputs():
    require(digest(CONTRACT_PATH.read_bytes()) == CONTRACT_SHA, 'Frozen Contract SHA mismatch')
    contract = json.loads(CONTRACT_PATH.read_text())
    for path_key, sha_key in [('implementationPath', 'implementationSha256'), ('syntheticTestPath', 'syntheticTestSha256')]:
        source = contract['sourceIntegrity']
        require(digest((ROOT / source[path_key]).read_bytes()) == source[sha_key], sha_key)
    require(np.__version__ == contract['runtime']['numpy'], 'NumPy version')
    require(scipy.__version__ == contract['runtime']['scipy'], 'SciPy version')
    require(sys.version_info[:2] == (3, 12), 'Python version')
    data, hashes = {}, {}
    for key, (name, expected) in LEDGERS.items():
        raw = (ROOT / 'docs/evidence' / name).read_bytes()
        require(digest(raw) == expected, 'ledger SHA ' + name)
        payload = gzip.decompress(raw)
        data[key] = json.loads(payload) if key == 'current' else [json.loads(line) for line in payload.splitlines() if line]
        hashes[name] = {'gzipSha256': digest(raw), 'payloadSha256': digest(payload)}
    selector = json.loads((ROOT / 'predict/research/phase57-long-only-frozen-selector-v1.json').read_text())
    selector_bytes = json.dumps(selector['freezePayload'], sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    require(digest(selector_bytes) == contract['sourceIntegrity']['frozenSelectorPayloadSha256'], 'selector payload')
    require(selector['hashes']['savedModelArtifactSha256'] == contract['sourceIntegrity']['frozenSelectorRidgeArtifactSha256'], 'Ridge artifact')
    source = json.loads((ROOT / 'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-report.json').read_text())['source']
    for path, key in [('predict/research/phase57-msh-entry-v1-model.json', 'currentEntryModelSha256'),
                      ('predict/research/phase57-minimal-stateful-entry-contract.json', 'currentEntryFeatureContractSha256'),
                      ('scripts/lib/phase57-minimal-stateful-entry.mjs', 'currentEntryFeatureImplementationSha256')]:
        require(digest((ROOT / path).read_bytes()) == source[key], key)
    rows = data['features']
    old = {r['selectorEventId']: r for r in data['transfer']}
    require(len(old) == 3800 and len(rows) == 3800, 'event count')
    require(len({r['selectorEventId'] for r in rows}) == 3800, 'duplicate events')
    require(set(old) == {r['selectorEventId'] for r in rows}, 'event identities')
    for row in rows:
        prior = old[row['selectorEventId']]
        require(row['direction'] == 'LONG' and row['shortScoreEvaluated'] is False, 'LONG-only')
        require(prior['direction'] == 'LONG' and prior['shortScoreEvaluated'] is False, 'transfer LONG-only')
        for key in ('sessionDate', 'symbol', 'decisionPrice', 'ridgeRank', 'ridgeScore', 'symbolSessionId'):
            require(row[key] == prior[key], 'lineage ' + key)
        require(timestamp(row['decisionTimestamp']) == timestamp(prior['decisionTimestamp']), 'decision timestamp')
        require(timestamp(prior['selectorFeatureAvailableAt']) <= timestamp(row['decisionTimestamp']), 'feature PIT')
        require(0 <= row['decisionPriceAgeMinutes'] <= 5 and row['decisionPrice'] > 0, 'fresh decision price')
        require(np.isfinite([row['ridgeScore'], row['ridgeRank'], row['decisionPrice']]).all(), 'finite core/price')
        require(row['ridgeRank'] in range(1, 6), 'rank')
        label = row['label']
        if label['labelable']:
            require(label['expectedBarCount'] == label['observedBarCount'] == 6, 'complete 30m path')
            require(label['highAvailable'] and label['closeAvailable'], 'HIGH/CLOSE availability')
            require((timestamp(label['windowEndTimestamp']) - timestamp(row['decisionTimestamp'])).total_seconds() == 1800, 'strict wall clock')
            for key, return_key in [('ordinalClass', 'highReturnPct'), ('closeOrdinalClass', 'closeReturnPct')]:
                require(label[key] == sum(label[return_key] >= t for t in LEVELS), 'ordinal reconstruction')
        else:
            require(label['ordinalClass'] is None and label['closeOrdinalClass'] is None, 'missing is not class zero')
        row['transfer'] = prior
    sessions = selector['freezePayload']['development']['sessions']
    require(sorted({r['sessionDate'] for r in rows}) == sessions and len(sessions) == 76, 'session membership')
    require(len(grouped(rows)) == 2743, 'unique symbol sessions')
    decisions = defaultdict(list)
    for r in rows:
        decisions[r['decisionTimestamp']].append(r['ridgeRank'])
    require(len(decisions) == 760 and all(sorted(v) == [1, 2, 3, 4, 5] for v in decisions.values()), '760 Top5 decisions')
    labelable = [r for r in rows if r['label']['labelable']]
    require(len(labelable) == 1828 and classes(labelable) == [606, 423, 271, 281, 247], 'label totals')
    reasons = dict(Counter(r['label']['reason'] for r in rows if not r['label']['labelable']))
    require(reasons == {'PROVIDER_GAP': 1424, 'LUNCH_BREAK': 380, 'SESSION_END': 168}, 'unlabelable counts')
    current = {r['symbolSessionId']: r for r in data['current']}
    require(set(current) == set(grouped(rows)) and len(data['current']) == 2743, 'current opportunity identities')
    return contract, rows, sessions, current, hashes


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def write_gzip_rows(path, rows):
    payload = b''.join(canonical(row) + b'\n' for row in rows)
    path.write_bytes(gzip.compress(payload, mtime=0))
    return {'fileSha256': digest(path.read_bytes()), 'payloadSha256': digest(payload), 'rows': len(rows)}


def run(output, preflight_only=False):
    require(not output.exists(), 'output path must be new; never overwrite an experiment')
    contract, rows, sessions, current, input_hashes = read_inputs()
    folds = prepare_folds(rows, sessions)  # ALL pre-fit checks before any project fit.
    output.mkdir(parents=True)
    preflight = {'status': 'PASS', 'contractSha256': CONTRACT_SHA, 'inputHashes': input_hashes,
                 'folds': [info for _, _, info in folds], 'sessions': sessions, 'events': len(rows),
                 'labelable': 1828, 'unlabelable': 1972, 'projectFitCalls': 0}
    write_json(output / 'preflight.json', preflight)
    if preflight_only:
        print(json.dumps({'status': 'PREFLIGHT_PASS_NO_FIT', 'folds': preflight['folds']}))
        return
    spec = importlib.util.spec_from_file_location('phase57_frozen_ordinal', ROOT / contract['sourceIntegrity']['implementationPath'])
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    original = {key: group[0] for key, group in grouped(rows).items()}
    oof, fold_artifacts, fit_calls = [], [], 0
    for train, evaluation, info in folds:
        fit_calls += 1
        try:
            model = module.ProportionalOddsOrdinalLogit().fit(matrix(train),
                np.asarray([r['label']['ordinalClass'] for r in train]), feature_order=CORE)
            require(np.array_equal(model.scaler_mean_, info['scaler']['mean']) and
                    np.array_equal(model.scaler_std_, info['scaler']['std']), 'prefix scaler identity')
            probabilities = model.predict_proba(matrix(evaluation))
            scores = probabilities @ np.arange(5)
            require(probabilities.shape == (len(evaluation), 5) and np.isfinite(probabilities).all(), 'OOF probabilities')
            require((probabilities >= 0).all() and np.allclose(probabilities.sum(1), 1, atol=1e-12, rtol=0), 'OOF probability conservation')
            require(((scores >= 0) & (scores <= 4)).all(), 'score range')
        except Exception as error:
            write_json(output / 'FIT_FAILED.json', {'fold': info['fold'], 'fitCalls': fit_calls,
                'status': 'FIT_FAILED', 'error': str(error), 'diagnostics': getattr(error, 'diagnostics', None),
                'retryAllowed': False, 'verdict': 'MSH_ENTRY_LONG_V1_DEVELOPMENT_FAIL'})
            raise
        artifact_path = output / f"fold-{info['fold']}-model.json"
        model.save_json(artifact_path)
        loaded = module.ProportionalOddsOrdinalLogit.load_json(artifact_path)
        require(np.array_equal(probabilities, loaded.predict_proba(matrix(evaluation))), 'project artifact roundtrip')
        info = dict(info, convergence=model.last_fit_diagnostics, artifactFileSha256=digest(artifact_path.read_bytes()),
                    beta=model.beta_.tolist(), cutpoints=model.cutpoints_.tolist())
        fold_artifacts.append(info)
        for row, probability, score in zip(evaluation, probabilities, scores):
            oof.append(dict(row, fold=info['fold'], probabilities=probability.tolist(), expectedLevel=float(score)))
    require(len({r['selectorEventId'] for r in oof}) == len(oof), 'OOF duplicates')
    expected = {r['selectorEventId'] for r in rows if r['sessionDate'] in sessions[16:] and r['label']['labelable']}
    require(expected == {r['selectorEventId'] for r in oof}, 'OOF exactly eval labelable only')
    eligible_first = [group[0] for group in grouped(oof).values()]
    selector_baseline = evaluate(oof, eligible_first, 60, original)
    current_paired = current_baseline(oof, current, original, 60)
    all_eval = [r for r in rows if r['sessionDate'] in sessions[16:]]
    thresholds, decisions = {}, []
    for threshold in THRESHOLDS:
        entries, actions = replay(oof, threshold)
        thresholds[str(threshold)] = {
            'firstEntry': evaluate(oof, entries, 60, original),
            'eventLevel': event_metrics(oof, [r for r in oof if r['expectedLevel'] >= threshold]),
            'folds': [],
        }
        for fold in range(1, 5):
            pool = [r for r in oof if r['fold'] == fold]
            first_entries = [r for r in entries if r['fold'] == fold]
            thresholds[str(threshold)]['folds'].append(dict(
                fold=fold, oofRows=len(pool), **evaluate(pool, first_entries, 15, original)))
        decisions.extend(actions)
    out_rows = []
    for r in oof:
        out_rows.append({key: r[key] for key in ('selectorEventId', 'sessionDate', 'symbol',
            'symbolSessionId', 'decisionTimestamp', 'decisionPrice', 'ridgeRank', 'ridgeScore', 'fold', 'expectedLevel')} |
            {'trueOrdinalLabel': r['label']['ordinalClass'], 'closeOrdinalLabel': r['label']['closeOrdinalClass'],
             'labelWindowEndTimestamp': r['label']['windowEndTimestamp'],
             **{f'P{k}': r['probabilities'][k] for k in range(5)}, 'direction': 'LONG'})
    ledger = []
    for r in rows:
        ledger.append({key: r[key] for key in ('selectorEventId', 'sessionDate', 'symbol', 'decisionTimestamp')} |
            {'labelable': r['label']['labelable'], 'reason': r['label']['reason'],
             'oofStatus': 'OOF' if r['selectorEventId'] in expected else
                 ('UNLABELABLE' if not r['label']['labelable'] else 'INITIAL_TRAINING_PREFIX_NO_OOF')})
    files = {'oof': write_gzip_rows(output / 'oof.ndjson.gz', out_rows),
             'exclusions': write_gzip_rows(output / 'row-ledger.ndjson.gz', ledger),
             'decisions': write_gzip_rows(output / 'threshold-decisions.ndjson.gz', decisions)}
    report = {
        'status': 'DEVELOPMENT_EVALUATION_COMPLETE_AWAIT_VERDICT_REVIEW',
        'contractSha256': CONTRACT_SHA, 'inputHashes': input_hashes, 'files': files,
        'implementationSha256': contract['sourceIntegrity']['implementationSha256'],
        'sourceHead': '97617f410a181108ab533632487d05c65f3a9ea8',
        'dataAudit': {'sessions': 76, 'events': 3800, 'labelable': 1828, 'unlabelable': 1972,
            'unlabelableReasons': {'PROVIDER_GAP': 1424, 'LUNCH_BREAK': 380, 'SESSION_END': 168},
            'uniqueSymbolSessions': 2743, 'evaluationSessions': sessions[16:], 'oofRows': len(oof),
            'oofUniqueSymbolSessions': len(eligible_first), 'allEvaluationEvents': len(all_eval),
            'allEvaluationSymbolSessions': len(grouped(all_eval)), 'oofDuplicateIds': 0,
            'trainingEvaluationSessionOverlap': 0, 'trainingEvaluationSymbolSessionOverlap': 0,
            'warmupOofRows': 0},
        'folds': fold_artifacts, 'selectorPaired': selector_baseline,
        'selectorEventPaired': event_metrics(oof, oof), 'currentPaired': current_paired,
        'currentAllEvaluationSessions': {
            'candidateSymbolSessions': len(grouped(all_eval)),
            'actualFirstPassN': sum(current[key]['firstPassTimestamp'] is not None for key in grouped(all_eval)),
            'note': 'ALL_60_SESSIONS_CONTEXT_NOT_PAIRED_LABELABLE_DENOMINATOR'},
        'thresholds': thresholds,
        'methodology': {'projectFitCalls': fit_calls, 'finalAll76SessionRefit': 0,
            'projectOofRows': len(oof), 'thresholdCandidatesEvaluated': list(THRESHOLDS),
            'validationNewAccess': 0, 'oosNewAccess': 0, 'exitAccess': 0,
            'providerRequests': 0, 'shortEvaluations': 0},
        'safety': contract['safety'],
        'limitations': [
            'OOF is conditional on future 30m labelability, not deployable full-universe coverage.',
            'The upstream Selector is already Development-exposed; Entry OOF is not end-to-end OOS.',
            'Actual frozen selection schedule is 30-minute spacing, not five-minute reselection.',
            'Only saved Development evidence reused; no raw provider requests.',
            'Strict 30m true MAE is unavailable; session true MAE is explicitly a separate horizon.',
            'CURRENT exact-event 30m comparison excludes other first-PASS times; not full CURRENT performance.',
            'Event probability predictions are not independent trades. Entries are unique symbol-sessions.',
            'Same-event reference is not an executed fill. No costs, EXIT or portfolio performance inferred.',
        ]}
    write_json(output / 'development-report.json', report)
    print(json.dumps({'status': report['status'], 'oofRows': len(oof), 'fitCalls': fit_calls,
                      'entries': {t: r['firstEntry']['enterCount'] for t, r in thresholds.items()}}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    run(args.output_dir, args.preflight_only)
