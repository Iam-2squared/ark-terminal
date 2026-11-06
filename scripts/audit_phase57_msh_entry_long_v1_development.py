#!/usr/bin/env python3
"""Read-only evidence audit. No model import, fit, scaler fit, or new predictions."""
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.special import expit

import run_phase57_msh_entry_long_v1_development as evaluation


def audit():
    folder = evaluation.ROOT / 'docs/evidence/phase57-msh-entry-long-v1-first-development'
    report = json.loads((folder / 'development-report.json').read_text())
    contract, rows, sessions, current, _ = evaluation.read_inputs()
    by_id = {r['selectorEventId']: r for r in rows}
    original = {key: group[0] for key, group in evaluation.grouped(rows).items()}
    oof_saved = [json.loads(line) for line in gzip.decompress((folder / 'oof.ndjson.gz').read_bytes()).splitlines()]
    assert len(oof_saved) == len({r['selectorEventId'] for r in oof_saved}) == 1451
    expected = {r['selectorEventId'] for r in rows if r['label']['labelable'] and r['sessionDate'] in sessions[16:]}
    assert {r['selectorEventId'] for r in oof_saved} == expected
    oof = []
    max_probability_error = 0.0
    for info in report['folds']:
        path = folder / f"fold-{info['fold']}-model.json"
        assert evaluation.digest(path.read_bytes()) == info['artifactFileSha256']
        artifact = json.loads(path.read_text())
        assert artifact['solver']['success'] is True
        assert artifact['regularization'] == {'cutpointsPenalized': False, 'lambda': 1.0,
            'objective': 'SUM_NLL+lambda/2*||beta||^2', 'type': 'L2_SLOPES_ONLY'}
        assert artifact['featureOrder'] == list(evaluation.CORE)
        assert all(v is False for v in artifact['safety'].values())
        beta, theta = np.array(artifact['beta']), np.array(artifact['cutpoints'])
        assert np.isfinite(beta).all() and np.isfinite(theta).all() and (np.diff(theta) > 0).all()
        train = [r for r in rows if r['sessionDate'] in info['trainSessions'] and r['label']['labelable']]
        X = evaluation.matrix(train)
        assert np.array_equal(X.mean(0), artifact['scaler']['mean'])
        assert np.array_equal(X.std(0), artifact['scaler']['std'])
        assert evaluation.digest(evaluation.canonical(info['scaler'])) == info['scalerSha256']
        assert max(info['trainSessions']) < min(info['evalSessions'])
        # Independent mathematical reconstruction from persisted coefficients, not model API.
        for item in [r for r in oof_saved if r['fold'] == info['fold']]:
            r = by_id[item['selectorEventId']]
            assert r['sessionDate'] in info['evalSessions']
            assert item['trueOrdinalLabel'] == r['label']['ordinalClass']
            assert item['closeOrdinalLabel'] == r['label']['closeOrdinalClass']
            for key in ('symbol', 'sessionDate', 'decisionTimestamp', 'decisionPrice', 'ridgeScore', 'ridgeRank'):
                assert item[key] == r[key]
            x = (np.array([r['ridgeScore'], r['ridgeRank']]) - artifact['scaler']['mean']) / artifact['scaler']['std']
            cdf = expit(theta - x @ beta)
            p = np.diff(np.r_[0., cdf, 1.])
            stored = np.array([item[f'P{k}'] for k in range(5)])
            max_probability_error = max(max_probability_error, float(np.max(np.abs(p - stored))))
            np.testing.assert_allclose(p, stored, atol=1e-12, rtol=0)
            assert abs(item['expectedLevel'] - stored @ np.arange(5)) < 1e-12
            oof.append(dict(r, fold=item['fold'], expectedLevel=item['expectedLevel']))
    decisions = []
    for threshold in evaluation.THRESHOLDS:
        entries, actions = evaluation.replay(oof, threshold)
        actual = report['thresholds'][str(threshold)]
        assert evaluation.evaluate(oof, entries, 60, original) == actual['firstEntry']
        assert evaluation.event_metrics(oof, [r for r in oof if r['expectedLevel'] >= threshold]) == actual['eventLevel']
        # Independent set-count checks (not the evaluation aggregator).
        first = {key: group[0] for key, group in evaluation.grouped(oof).items()}
        admitted = {r['symbolSessionId'] for r in entries}
        assert len(admitted) == len(entries)
        for klass, level in enumerate((1, 2, 3, 5), 1):
            winners = {key for key, r in first.items() if r['label']['ordinalClass'] >= klass}
            metric = actual['firstEntry']['high30'][str(level)]
            assert metric['admittedBaselineWinnerN'] == len(winners & admitted)
            assert metric['hitN'] == sum(r['label']['ordinalClass'] >= klass for r in entries)
        decisions.extend(actions)
    saved = [json.loads(x) for x in gzip.decompress((folder / 'threshold-decisions.ndjson.gz').read_bytes()).splitlines()]
    assert decisions == saved and len(saved) == 4353
    assert evaluation.current_baseline(oof, current, original, 60) == report['currentPaired']
    for key, name in [('oof', 'oof.ndjson.gz'), ('exclusions', 'row-ledger.ndjson.gz'),
                      ('decisions', 'threshold-decisions.ndjson.gz')]:
        raw = (folder / name).read_bytes()
        assert evaluation.digest(raw) == report['files'][key]['fileSha256']
        assert evaluation.digest(gzip.decompress(raw)) == report['files'][key]['payloadSha256']
    assert report['methodology']['projectFitCalls'] == 4
    assert all(report['methodology'][k] == 0 for k in ('validationNewAccess', 'oosNewAccess', 'exitAccess',
        'providerRequests', 'shortEvaluations', 'finalAll76SessionRefit'))
    assert report['contractSha256'] == evaluation.CONTRACT_SHA
    assert all(v is False for v in report['safety'].values())
    return {'status': 'PASS', 'projectFitCallsByAudit': 0, 'modelApiPredictionCallsByAudit': 0,
        'savedOofRowsIndependentlyChecked': 1451, 'decisionRowsChecked': 4353,
        'maxProbabilityAbsoluteError': max_probability_error,
        'contractSha256': report['contractSha256'], 'frozenSourcesUnchanged': True}


if __name__ == '__main__':
    print(json.dumps(audit(), sort_keys=True))
