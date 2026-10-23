#!/usr/bin/env python3
"""Frozen, all-event causal historical replay. No fitting; not Fresh/OOS evidence."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement'
CONTRACT_SHA = '4a1d3e4ec4229d32ee2a50678db8fe3f8739abb3530df521e3036d201e75b441'
LEVELS = [1, 2, 3, 5]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def stamp(s):
    return datetime.fromisoformat(s)

def read_gzip(name, lines=True):
    with gzip.open(ROOT / 'docs/evidence' / name, 'rt') as f:
        return [json.loads(s) for s in f] if lines else json.load(f)

def inputs():
    raw = (OUT / 'dataset-contract.json').read_bytes()
    assert sha(raw) == CONTRACT_SHA, 'CONTRACT_SHA_MISMATCH'
    c = json.loads(raw)
    for p, h in c['sourcePins'].items():
        assert sha((ROOT / p).read_bytes()) == h, 'SOURCE_SHA_MISMATCH:' + p
    assert c['threshold'] == 2.0 and not any(c['safety'].values())
    rows = read_gzip('phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz')
    transfer = read_gzip('phase57-long-only-current-entry-transfer-v1-events.ndjson.gz')
    refs = {r['selectorEventId']: r for r in transfer}
    assert len(rows) == len(refs) == 3800
    assert sha(canonical([r['selectorEventId'] for r in rows])) == c['eventIdentitySHA']
    assert sorted({r['sessionDate'] for r in rows}) == c['sessionList']
    for r in rows:
        t = refs[r['selectorEventId']]
        for k in ['sessionDate', 'symbol', 'decisionPrice', 'ridgeScore', 'ridgeRank', 'symbolSessionId']:
            assert r[k] == t[k], 'SAVED_FEATURE_IDENTITY:' + k
        assert stamp(r['decisionTimestamp']) == stamp(t['decisionTimestamp'])
        assert r['direction'] == 'LONG' and not r['shortScoreEvaluated']
        assert stamp(t['selectorFeatureAvailableAt']) <= stamp(r['decisionTimestamp'])
        assert stamp(t['selectorFeatureTimestamp']) <= stamp(r['decisionTimestamp'])
        assert 0 <= r['decisionPriceAgeMinutes'] <= 5
        assert r['decisionTimestamp'][11:16] in c['cadence']
        assert 1 <= r['ridgeRank'] <= 5
    return c, rows

def causal_decisions(rows, scores):
    """Only identity/time/score enter this function; labels are never consulted."""
    if len(rows) != len(scores):
        raise ValueError('SCORE_IDENTITY_MISMATCH')
    seen = set()
    result = {}
    for r, score in sorted(zip(rows, scores), key=lambda pair: (pair[0]['decisionTimestamp'], pair[0]['selectorEventId'])):
        key = r['symbolSessionId']
        admit = score >= 2.0 and key not in seen
        reason = 'FIRST_QUALIFYING_DECISION' if admit else 'ALREADY_ENTERED' if key in seen else 'BELOW_FROZEN_THRESHOLD'
        if admit:
            seen.add(key)
        result[r['selectorEventId']] = {'state': 'ENTER' if admit else 'SKIP_THIS_DECISION', 'reason': reason}
    return [result[r['selectorEventId']] for r in rows]

def predict_once():
    import numpy as np
    target = OUT / 'frozen-predictions.ndjson.gz'
    if target.exists():
        raise RuntimeError('PREDICTION_ALREADY_EXISTS_NO_REPLAY')
    c, rows = inputs()
    name = 'phase57_frozen_ordinal_replay'
    spec = importlib.util.spec_from_file_location(name, ROOT / 'predict/research/phase57_msh_entry_long_v1_proportional_odds.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    model = mod.ProportionalOddsOrdinalLogit.load_json(ROOT / 'docs/evidence/phase57-msh-entry-long-v1-final-validation-model/final-model.json')
    scaler = json.loads((ROOT / 'docs/evidence/phase57-msh-entry-long-v1-final-validation-model/final-scaler.json').read_text())
    assert list(model.feature_order_) == c['features']
    assert np.array_equal(model.scaler_mean_, scaler['mean']) and np.array_equal(model.scaler_std_, scaler['std'])
    matrix = np.array([[r['ridgeScore'], r['ridgeRank']] for r in rows], dtype=float)
    probabilities = model.predict_proba(matrix)
    assert probabilities.shape == (3800, 5) and np.isfinite(probabilities).all()
    assert (probabilities >= 0).all() and (probabilities <= 1).all() and np.allclose(probabilities.sum(axis=1), 1, atol=1e-12, rtol=0)
    scores = probabilities @ np.arange(5)
    decisions = causal_decisions(rows, scores)
    output = [{'selectorEventId': r['selectorEventId'], 'symbolSessionId': r['symbolSessionId'], 'sessionDate': r['sessionDate'], 'decisionTimestamp': r['decisionTimestamp'], 'probabilities': p.tolist(), 'expectedClass': float(s), **d} for r, p, s, d in zip(rows, probabilities, scores, decisions)]
    data = ''.join(json.dumps(x, separators=(',', ':'), allow_nan=False) + '\n' for x in output).encode()
    with target.open('xb') as f:
        f.write(gzip.compress(data, mtime=0))
    receipt = {'datasetContractSHA': CONTRACT_SHA, 'predictionArtifactSHA': sha(target.read_bytes()), 'predictionTimestampUtc': datetime.now().astimezone().isoformat(), 'modelPredictionCalls': 1, 'scoredEvents': len(rows), 'fit': 0, 'scalerRefit': 0, 'thresholdSearch': 0, 'providerRequests': 0, 'exposure': c['exposure'], 'safety': c['safety']}
    (OUT / 'prediction-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ['exposure', 'safety']}))

def rate(n, d):
    return 100 * n / d if d else None

def distribution(values):
    import numpy as np
    a = np.array(values, dtype=float)
    if not len(a):
        return {'n': 0}
    assert np.isfinite(a).all()
    return {'n': len(a), 'mean': float(a.mean()), 'min': float(a.min()), 'p05': float(np.quantile(a, .05)), 'p25': float(np.quantile(a, .25)), 'median': float(np.median(a)), 'p75': float(np.quantile(a, .75)), 'p95': float(np.quantile(a, .95)), 'max': float(a.max())}

def quality(events, paths):
    evaluated = [paths[r['selectorEventId']] for r in events if paths[r['selectorEventId']]['labelable']]
    return {'candidates': len(events), 'labelable': len(evaluated), 'unlabelable': len(events) - len(evaluated), 'availabilityPct': rate(len(evaluated), len(events)), 'unlabelableReasons': dict(Counter(paths[r['selectorEventId']]['reason'] for r in events if not paths[r['selectorEventId']]['labelable'])), 'high': {str(k): {'hits': sum(p['highReturnPct'] >= k for p in evaluated), 'precisionPct': rate(sum(p['highReturnPct'] >= k for p in evaluated), len(evaluated))} for k in LEVELS}, 'close': {str(k): {'hits': sum(p['closeReturnPct'] >= k for p in evaluated), 'precisionPct': rate(sum(p['closeReturnPct'] >= k for p in evaluated), len(evaluated))} for k in LEVELS}, 'trueMaePct': distribution([p['trueMaePct'] for p in evaluated]), 'mfePct': distribution([p['mfePct'] for p in evaluated]), 'sparseMinutePathCount': sum(p['sparseMinuteBars'] > 0 for p in evaluated)}

def preservation(first, admitted, paths, session_count):
    results = {}
    for k in LEVELS:
        winners = [r for r in first.values() if paths[r['selectorEventId']]['labelable'] and paths[r['selectorEventId']]['highReturnPct'] >= k]
        transferred = [r for r in winners if r['symbolSessionId'] in admitted]
        timely = [r for r in transferred if (stamp(admitted[r['symbolSessionId']]['decisionTimestamp']) - stamp(r['decisionTimestamp'])).total_seconds() < 1800]
        remaining = [r for r in transferred if paths[admitted[r['symbolSessionId']]['selectorEventId']]['labelable'] and paths[admitted[r['symbolSessionId']]['selectorEventId']]['highReturnPct'] >= k]
        results[str(k)] = {'selectorWinners': len(winners), 'transferred': len(transferred), 'preservationPct': rate(len(transferred), len(winners)), 'preservedPerSession': len(transferred) / session_count, 'admittedBeforeOriginalHorizonEnd': len(timely), 'timelyPreservationPct': rate(len(timely), len(winners)), 'winnerAndRemainingHit': len(remaining), 'winnerAndRemainingPreservationPct': rate(len(remaining), len(winners)), 'transferredEntryLabelable': sum(paths[admitted[r['symbolSessionId']]['selectorEventId']]['labelable'] for r in transferred)}
    return results

def measure(path_file):
    c, rows = inputs()
    receipt = json.loads((OUT / 'prediction-receipt.json').read_text())
    pred_file = OUT / 'frozen-predictions.ndjson.gz'
    assert sha(pred_file.read_bytes()) == receipt['predictionArtifactSHA']
    preds = [json.loads(s) for s in gzip.decompress(pred_file.read_bytes()).decode().splitlines()]
    assert [p['selectorEventId'] for p in preds] == [r['selectorEventId'] for r in rows]
    path_raw = Path(path_file).read_bytes()
    path_record = json.loads(path_raw)
    assert path_record['datasetContractSHA'] == CONTRACT_SHA
    assert path_record['integrity']['savedLabelParityRows'] == 1828
    paths = {r['selectorEventId']: r for r in path_record['events']}
    assert len(paths) == len(rows) and set(paths) == {r['selectorEventId'] for r in rows}
    for r in rows:
        p = paths[r['selectorEventId']]
        assert p['labelable'] == r['label']['labelable']
        if p['labelable']:
            assert abs(p['highReturnPct'] - r['label']['highReturnPct']) < 1e-9
            assert abs(p['closeReturnPct'] - r['label']['closeReturnPct']) < 1e-9
    first = {}
    for r in sorted(rows, key=lambda r: (r['decisionTimestamp'], r['selectorEventId'])):
        first.setdefault(r['symbolSessionId'], r)
    entered = [r for r, p in zip(rows, preds) if p['state'] == 'ENTER']
    admits = {r['symbolSessionId']: r for r in entered}
    assert len(admits) == len(entered)
    selector_quality = quality(list(first.values()), paths)
    candidate_quality = quality(entered, paths)
    common = {k for k, r in first.items() if paths[r['selectorEventId']]['labelable']}
    common_entries = [r for r in entered if r['symbolSessionId'] in common]
    first_ops = read_gzip('phase57-long-only-entry-filter-recovery-audit-v1-first-opportunities.json.gz', lines=False)
    assert {r['symbolSessionId'] for r in first_ops} == set(first)
    current_paths = {r['symbolSessionId']: r for r in path_record['currentEvents']}
    current_rows, all_paths = [], dict(paths)
    for r in first_ops:
        if r['firstPassTimestamp']:
            k = r['symbolSessionId']; p = current_paths[k]
            assert p['firstPassTimestamp'] == r['firstPassTimestamp'] and p['firstPassPrice'] == r['firstPassPrice']
            identifier = 'CURRENT:' + k
            all_paths[identifier] = p
            current_rows.append({'selectorEventId': identifier, 'symbolSessionId': k, 'sessionDate': r['sessionDate'], 'decisionTimestamp': r['firstPassTimestamp'], 'decisionPrice': r['firstPassPrice']})
    current_admits = {r['symbolSessionId']: r for r in current_rows}
    sessions = []
    for d in c['sessionList']:
        fr = {k: r for k, r in first.items() if r['sessionDate'] == d}
        er = [r for r in entered if r['sessionDate'] == d]
        sessions.append({'sessionDate': d, 'selectorEvents': sum(r['sessionDate'] == d for r in rows), 'firstEntryCandidates': len(fr), 'enter': len(er), 'selector': quality(list(fr.values()), paths), 'candidate': quality(er, paths), 'preservation': preservation(fr, {r['symbolSessionId']: r for r in er}, paths, 1)})
    latency = [(stamp(r['decisionTimestamp']) - stamp(first[r['symbolSessionId']]['decisionTimestamp'])).total_seconds()/60 for r in entered]
    consumed = [10000 * (r['decisionPrice']/first[r['symbolSessionId']]['decisionPrice']-1) for r in entered]
    result = {'measurementName': 'MSH-Entry LONG v1 HISTORICAL RE-MEASUREMENT', 'exposure': c['exposure'], 'freshClaim': False, 'oosClaim': False, 'officialValidationPassClaim': False, 'freshConfirmation': 'PENDING', 'datasetContractSHA': CONTRACT_SHA, 'predictionReceipt': receipt, 'pathArtifactSHA': sha(path_raw), 'sessions': 76, 'selectorEvents': len(rows), 'firstEntryCandidates': len(first), 'enter': len(entered), 'skip': len(rows)-len(entered), 'decisionReasons': dict(Counter(p['reason'] for p in preds)), 'firstEntryCoveragePct': rate(len(entered), len(first)), 'enterPerSession': len(entered)/76, 'allSelectorEventLabelability': quality(rows, paths), 'selectorFirstOpportunity': selector_quality, 'candidateActualEntry': candidate_quality, 'entryTimeRemainingOpportunity': candidate_quality['high'], 'preservation': preservation(first, admits, paths, 76), 'firstSelectorLabelableCohort': {'symbolSessions': len(common), 'enter': len(common_entries), 'coveragePct': rate(len(common_entries), len(common)), 'candidate': quality(common_entries, paths)}, 'currentSupportingReference': {'scope': 'Frozen saved first PASS, native5m cadence; Candidate uses10 saved decisions/session. Different decision schedules disclosed, not a cadence-controlled causal comparison.', 'enter': len(current_rows), 'firstEntryCoveragePct': rate(len(current_rows), len(first)), 'enterPerSession': len(current_rows)/76, 'quality': quality(current_rows, all_paths), 'preservation': preservation(first, current_admits, all_paths, 76), 'firstSelectorLabelableCohort': quality([r for r in current_rows if r['symbolSessionId'] in common], all_paths)}, 'latencyFromFirstSelectorMinutes': distribution(latency), 'consumedReturnFromFirstSelectorBps': distribution(consumed), 'sameDecisionProcessingLatencyMinutes': 0, 'latencyLimitation': 'Historical timestamp/reference convention only; no measured execution or compute latency, no broker fill.', 'sessionStability': {'zeroEnterSessions': sum(s['enter']==0 for s in sessions), 'enterDistribution': distribution([s['enter'] for s in sessions]), 'top5SessionsEnterSharePct': rate(sum(sorted([s['enter'] for s in sessions],reverse=True)[:5]),len(entered)), 'highHitsTop5SessionSharePct': {str(k): rate(sum(sorted([s['candidate']['high'][str(k)]['hits'] for s in sessions],reverse=True)[:5]), candidate_quality['high'][str(k)]['hits']) for k in LEVELS}}, 'sessionResults': sessions, 'integrity': path_record['integrity'], 'cost': c['pathContract']['cost'], 'counts': {'providerRequests':0,'fit':0,'scalerRefit':0,'thresholdSearch':0,'oosAccess':0,'exitOutcomeAccess':0,'shortEvaluation':0,'forwardFill':0,'interpolation':0,'futureSubstitution':0,'freshBudgetConsumed':0}, 'safety': c['safety']}
    target=OUT/'measurement.json'
    if target.exists():
        raise RuntimeError('MEASUREMENT_EXISTS_NO_OVERWRITE')
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['sessionResults','predictionReceipt','exposure','safety']},indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['predict','measure']);parser.add_argument('--paths')
    args=parser.parse_args()
    predict_once() if args.action=='predict' else measure(args.paths)
