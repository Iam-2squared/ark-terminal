"""Read-only closure audit: saved estimators only; no new fit or sealed evaluation."""
import argparse
import collections
import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts import phase57_comprehensive_entry_v2 as v
from scripts import report_phase57_comprehensive_entry_v2 as report
from scripts.verify_phase57_comprehensive_entry import equal as numerical_equal, verify

m = v.m
PROTOCOL_SHA256 = '3ef0e87eeb370443240a5e6258adfd8e83a9797d60e9efbe61c8b88d9466dcdb'


def equal(a, b, label):
    # JSON evidence represents Python tuples (e.g. Counter pairs) as lists.
    numerical_equal(json.loads(m.enc(a)), json.loads(m.enc(b)), label)


def audit(outdir):
    out = Path(outdir)
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    source = v.BASE / 'measurement'
    manifest = m.read(source / 'manifest.json')
    assert m.sha(v.BASE / 'protocol.json') == PROTOCOL_SHA256
    assert manifest['protocolSHA256'] == PROTOCOL_SHA256
    assert manifest['codeSHA256'] == m.sha(v.__file__)
    for name, digest in manifest['outputs'].items():
        assert m.sha(source / name) == digest, name
    p, ops, paths, selectors, legacy = v.sources()
    assert manifest['sourcePins'] == p['sourcePins']
    assert p['architectures']['order'] == list(v.KINDS)
    assert [len(p['split'][k]) for k in ('TRAIN', 'VALIDATION', 'DEVELOPMENT_TEST')] == [38, 19, 19]
    s = m.read(source / 'summary.json')
    assert s['selected'] is None and s['developmentTest'] is None
    assert s['developmentTestOpened'] is False and s['freshOOSOpened'] is False
    assert s['audit']['supervisedFits'] == 5 and s['audit']['economicCohortEvaluations'] == 0
    assert s['status'] == 'COMPREHENSIVE_LONG_ENTRY_V2_DEVELOPMENT_LIMIT_REACHED'
    assert s['freeze'] == 'DO_NOT_FREEZE'
    assert len(p['safety']) == 9 and all(x is False for x in p['safety'].values())
    assert s['safety'] == manifest['safety'] == p['safety']
    assert not list(source.glob('*development-test*'))
    assert not list(source.glob('*economic*'))
    top3 = s['baselines']['B0_IMMEDIATE']['concentration']['top3Train']
    train = [x for x in ops if x['session'] in p['split']['TRAIN']]
    freq = collections.Counter(x['symbol'] for x in train)
    assert top3 == [k for k, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:3]]
    teacher = m.read(source / 'training-teacher-ledger.json.gz')
    # This constructs TRAIN labels and features, never estimators.
    equal(teacher, v.training(train, paths, selectors, legacy), 'TRAIN_teacher')
    assert len(teacher) == 4431 and len({r['id'] for r in teacher}) == 633
    for head, weight in [('waitAdvantage', 'waitWeight'), ('skipAdvantage', 'skipWeight')]:
        totals = collections.Counter()
        for r in teacher:
            assert r['session'] in p['split']['TRAIN']
            if r['labels'][head] is not None:
                totals[r['id']] += r[weight]
        assert all(abs(x - 1) < 1e-12 for x in totals.values())
    models = {k: m.read(source / (k.lower() + '-model.json')) for k in v.KINDS}
    for head in ('waitHead', 'skipHead'):
        equal(models['S1_LINEAR'][head], models['S3_GUARDED_LINEAR'][head], 'S3_reuses_S1')
        rs = [r for r in teacher if r['labels']['waitAdvantage'] is not None] if head == 'waitHead' else teacher
        a = m.matrix([r['features'] for r in rs], m.FEATURES)
        medians = np.array([np.median(z[np.isfinite(z)]) if np.isfinite(z).any() else 0 for z in a.T])
        z = np.concatenate([np.where(np.isnan(a), medians, a), np.isnan(a).astype(float)], axis=1)
        for k, md in models.items():
            d = md[head]
            assert d['features'] == m.FEATURES and len(m.FEATURES) == 43
            equal(d['medians'], medians.tolist(), k + '_TRAIN_medians')
            equal(d['scalerMean'], np.mean(z, axis=0).tolist(), k + '_TRAIN_mean')
            equal(d['scalerScale'], np.where(np.var(z, axis=0) == 0, 1, np.std(z, axis=0)).tolist(), k + '_TRAIN_scale')
    candidates = {}
    for kind in v.KINDS:
        model = report.SavedPolicy(models[kind])
        panels = {}
        for split in ('TRAIN', 'VALIDATION'):
            path = source / (kind.lower() + '-' + split.lower() + '.json.gz')
            if not path.exists():
                assert kind == 'S2_TREE' and split == 'VALIDATION'
                continue
            rows = m.read(path)
            selected_ops = [x for x in ops if x['session'] in p['split'][split]]
            assert [r['id'] for r in rows] == [x['id'] for x in selected_ops]
            equal(rows, v.measure(selected_ops, paths, selectors, legacy, model), kind + '_' + split)
            if split == 'TRAIN':
                equal(v.train_monitor(rows), s['trainMonitoring'][kind], kind + '_train_monitor')
            else:
                assert s['trainMonitoring'][kind]['pass']
                equal(v.panel(rows, top3), s['candidates'][kind]['entry'], kind + '_validation_gates')
            z = v.summarize(rows)
            panels[split] = {
                'metrics': z,
                'delaysIncludingZeroBins': {str(i): sum(r['decision']['delay'] == i for r in rows) for i in range(0, 31, 5)},
                'expireN': sum(r['decision']['status'].startswith('EXPIRE') for r in rows),
                'skipN': sum(r['decision']['status'] == 'MODEL_SKIP' for r in rows),
            }
        assert s['candidates'][kind]['status'].startswith('KILL')
        candidates[kind] = {'status': s['candidates'][kind]['status'], 'panels': panels}
    val = [x for x in ops if x['session'] in p['split']['VALIDATION']]
    for name in ('B0_IMMEDIATE', 'B1_FIXED_WAIT_1'):
        rows = m.read(source / (name.lower() + '.json.gz'))
        equal(rows, v.measure(val, paths, selectors, legacy, baseline=name), name)
        equal(v.panel(rows, top3), s['baselines'][name], name + '_panel')
    for kind in ('LINEAR', 'TREE'):
        rows = m.read(m.BASE / 'measurement' / ('validation-' + kind.lower() + '.json.gz'))
        reused = v.measure(val, paths, selectors, legacy, saved={r['id']: r for r in rows})
        equal(v.panel(reused, top3), s['baselines']['B2_V1_' + kind], 'B2_no_refit')
    report.run(source, out / 'report')
    report_files = verify(v.BASE / 'report', out / 'report')
    result = {
        'status': 'PASS', 'verdict': s['status'], 'candidateFreeze': False,
        'evidenceStatus': 'IMMUTABLE_LIMIT_EVIDENCE', 'protocolSHA256': PROTOCOL_SHA256,
        'sourcePinsVerified': len(p['sourcePins']), 'measurementFilesVerified': len(manifest['outputs']),
        'reportFilesVerified': report_files, 'newResearchFitCalls': 0,
        'priorDeterministicReplay': 'Existing local-verification.json records numerical regeneration; resume does not repeat fits.',
        'uniqueResearchEstimators': {'S1_LINEAR': 2, 'S2_TREE': 2, 'S3_GUARDED_LINEAR': 1, 'total': 5},
        'trainingTeacherRowsVerified': len(teacher), 'candidates': candidates,
        'economic': 'NOT_RUN_ENTRY_GATE_FAILED', 'developmentTestOpened': False,
        'freshOOSOpened': False, 'safety': p['safety'],
        'intrabarOrder': 'UNKNOWN_INTRABAR_ORDER retained; same-bar adverse/winner ordering is INCONCLUSIVE in pinned v1 classifier.',
    }
    m.write(out / 'audit.json', result)
    print(m.enc({k: value for k, value in result.items() if k != 'candidates'}).decode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    with ExitStack() as stack:
        for obj, name in ((m.Model, 'fit'), (v, 'fit_heads'), (v, 'fit_guard'), (v.LogisticRegression, 'fit'), (v, 'economic')):
            stack.enter_context(patch.object(obj, name, side_effect=AssertionError('FROZEN_RESUME_FORBIDS_FIT_OR_ECONOMIC')))
        audit(args.out)
