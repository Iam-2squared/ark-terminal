"""Additive strict-Daily ablation correction; never changes timing or old evidence."""
import argparse
import collections
import copy
from pathlib import Path
from scripts import phase57_causal_entry_anatomy as a

DAILY_DERIVED = ('dailyHighDistance', 'dailyLowDistance', 'dailyCloseDistance',
                 'fiveHighDistance', 'fiveLowDistance', 'todayGap')


def corrected_rows(rows):
    result = copy.deepcopy(rows)
    for row in result:
        if row['features'] is None:
            continue
        for key in DAILY_DERIVED:
            if key in row['features']:
                row['features']['DAILY/derived/' + key] = row['features'].pop(key)
    return result


def run(output):
    root = a.BASE / 'ci-result'
    protocol = a.BASE / 'completion-audit/PROTOCOL.md'
    assert a.c.sha(protocol) == 'c284749a7ad17079b925ee94ee33310588059d55be997f65ceb2d95df286654a', 'PRECOMMIT_CHANGED'
    rows = a.c.read(root / 'measurement/checkpoints.json.gz')
    original = a.c.read(root / 'measurement/predictions.json.gz')
    revised = corrected_rows(rows)
    diagnostic, predictions, _ = a.diagnostic(revised)
    identity = lambda r: (r['opportunity'], r['checkpoint'], r['variant'])
    orig_plus = {identity(r): r for r in original if r['variant'] == 'PLUS_DAILY'}
    new_plus = {identity(r): r for r in predictions if r['variant'] == 'PLUS_DAILY'}
    assert orig_plus == new_plus, 'PLUS_DAILY_PREDICTIONS_CHANGED'
    for fit in diagnostic['fits']:
        if fit['variant'] == 'INTRADAY':
            assert not any(k.startswith('DAILY/') or k in DAILY_DERIVED for k in fit['features'])
    pairs = []
    by_key = {identity(r): r for r in predictions}
    fit_sessions = set(diagnostic['fitSessions'])
    for t in a.CHECKPOINTS:
        intraday = [r for r in predictions if r['checkpoint'] == t and r['variant'] == 'INTRADAY']
        plus = [r for r in predictions if r['checkpoint'] == t and r['variant'] == 'PLUS_DAILY']
        assert {r['opportunity'] for r in intraday} == {r['opportunity'] for r in plus}
        train = [r for r in revised if r['checkpoint'] == t and r['features'] is not None and r['session'] in fit_sessions]
        counts = collections.Counter(r['path'] for r in train)
        majority = sorted(counts, key=lambda k: (-counts[k], k))[0]
        results = collections.Counter()
        for r in intraday:
            d = by_key[(r['opportunity'], t, 'PLUS_DAILY')]
            x = r['prediction'] == r['actualEvaluatorOnly']
            y = d['prediction'] == d['actualEvaluatorOnly']
            results['BOTH_CORRECT' if x and y else 'DAILY_ONLY_CORRECT' if y else 'INTRADAY_ONLY_CORRECT' if x else 'BOTH_WRONG'] += 1
        pairs.append({'checkpoint': t, 'pairedN': len(intraday), 'correctness': dict(results),
                      'fitMajorityClass': majority, 'majorityTestAccuracy': sum(r['actualEvaluatorOnly'] == majority for r in intraday) / len(intraday)})
    audit = {'protocolSHA256': a.c.sha(protocol), 'sourceCheckpointsSHA256': a.c.sha(root/'measurement/checkpoints.json.gz'),
             'renamedDailyDerived': list(DAILY_DERIVED), 'sourceImmutable': rows == a.c.read(root/'measurement/checkpoints.json.gz'),
             'plusDailyPredictionsUnchanged': True, 'paired': pairs,
             'scope': 'ADDITIVE_DEVELOPMENT_DIAGNOSTIC_CORRECTION_NOT_ENTRY_TRAINING', 'safety': a.s.verify()['safety'], 'stop': True}
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    for name, value in [('diagnostic.json.gz', diagnostic), ('predictions.json.gz', predictions), ('audit.json', audit)]:
        a.c.write(out/name, value)
    a.c.write(out/'manifest.json', {f.name: a.c.sha(f) for f in sorted(out.iterdir()) if f.is_file()})
    for fit in diagnostic['fits']:
        print(fit['checkpoint'], fit['variant'], fit['accuracy'], fit['balancedAccuracy'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    run(parser.parse_args().output)
