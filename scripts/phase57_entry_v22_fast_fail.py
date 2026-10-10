"""Bounded v2.2 Development screen. One target/model/cut; nine fits at most."""
import collections
import gzip
import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path

from predict.research import phase57_entry_v22_quality_probe as m
from scripts import audit_phase57_msh_entry_v2_1_predevelopment as frozen
from scripts.phase57_msh_entry_v2_development import exit_outcome
from scripts.phase57_msh_entry_v2_evaluation import quantile

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'predict/research/phase57-entry-v2-2-fast-fail-protocol-v1.json'
BASE = ROOT / 'docs/evidence/phase57-entry-v2-2-fast-fail'
PREFIT_SOURCES = ['predict/research/phase57_entry_v22_quality_probe.py',
                  'scripts/phase57_entry_v22_fast_fail.py',
                  'scripts/test_phase57_entry_v22_fast_fail.py']
np = m.np


def read(path):
    path = ROOT / path
    data = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
    return json.loads(data)


def ndjson(path):
    with gzip.open(ROOT / path, 'rt') as f:
        return [json.loads(line) for line in f]


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    b = m.canonical(value) + b'\n'
    with path.open('xb') as f:
        f.write(gzip.compress(b, mtime=0) if path.suffix == '.gz' else b)


def audit_protocol():
    if sha(PROTOCOL) != m.PROTOCOL_SHA:
        raise m.IntegrityError('PROTOCOL_HASH_MISMATCH')
    c = read(PROTOCOL)
    if c['features']['order'] != m.FEATURE_ORDER or c['cv']['maximumProjectFits'] != 9:
        raise m.IntegrityError('PROTOCOL_IMPLEMENTATION_MISMATCH')
    for path, expected in c['sourcePins'].items():
        if sha(path) != expected:
            raise m.IntegrityError('SOURCE_PIN_CHANGED:' + path)
    if any(c['safety'].values()) or any(c['precommitCounters'].values()):
        raise m.IntegrityError('SAFETY_OR_PRECOMMIT')
    return c


def average_ranks(a):
    order = sorted(range(len(a)), key=lambda i: a[i])
    ranks = np.zeros(len(a), dtype=float)
    j = 0
    while j < len(a):
        k = j + 1
        while k < len(a) and a[order[k]] == a[order[j]]:
            k += 1
        for i in order[j:k]:
            ranks[i] = (j + k - 1) / 2 + 1
        j = k
    return ranks


def spearman(rows):
    if len(rows) < 7 or len({r['symbol'] for r in rows}) < 2:
        return None
    a = average_ranks([r['predictedQ'] for r in rows])
    b = average_ranks([r['actualQ'] for r in rows])
    a -= a.mean()
    b -= b.mean()
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(a @ b / denominator) if denominator > 0 else None


def regression_metrics(rows):
    complete = [r for r in rows if r['status'] == 'SCORED' and r['actualQ'] is not None]
    by_unit = collections.defaultdict(list)
    for r in complete:
        by_unit[r['unit']].append(r)
    errors, constants = [], []
    for values in by_unit.values():
        w = m.symbol_weights(values)
        errors.append(float(w @ np.asarray([(r['predictedQ'] - r['actualQ']) ** 2 for r in values])))
        constants.append(float(w @ np.asarray([(r['trainingConstantQ'] - r['actualQ']) ** 2 for r in values])))
    mse = statistics.mean(errors) if errors else None
    constant = statistics.mean(constants) if constants else None
    return {'rows': len(rows), 'scored': sum(r['status'] == 'SCORED' for r in rows),
            'targetEvaluable': len(complete), 'symbols': len({r['symbol'] for r in complete}),
            'spearman': spearman(complete), 'balancedMSE': mse, 'constantBalancedMSE': constant,
            'mseSkill': 1 - mse / constant if constant is not None and constant > 0 else None,
            'unitCount': len(by_unit), 'unitBalancedSquaredErrors': errors,
            'unitConstantBalancedSquaredErrors': constants}


def distribution(values):
    n = len(values)
    return {'n': n, 'mean': statistics.mean(values) if n else None,
            'median': statistics.median(values) if n else None,
            'p05': quantile(values, .05), 'p90': quantile(values, .9),
            'p95': quantile(values, .95), 'min': min(values) if n else None,
            'max': max(values) if n else None,
            'upperES95': statistics.mean(sorted(values, reverse=True)[:max(1, math.ceil(.05*n))]) if n else None}


def band_metrics(rows):
    n = len(rows)
    q = [r['actualQ'] for r in rows if r['actualQ'] is not None]
    d = [r['D30'] for r in rows if r['D30'] is not None]
    mfe = [r['MFE'] for r in rows if r['MFE'] is not None]
    counts = collections.Counter(r['symbol'] for r in rows)
    profit, loss = sum(max(0., v) for v in q), sum(max(0., -v) for v in q)
    return {'events': n, 'uniqueSymbols': len(counts),
            'entryCountHHI': sum((v/n)**2 for v in counts.values()) if n else None,
            'targetCoverage': len(q)/n if n else None, 'D30Coverage': len(d)/n if n else None,
            'Q': distribution(q), 'D30': distribution(d), 'MFE': distribution(mfe),
            'referenceReturnPF': profit/loss if loss else ('INF' if profit else None),
            'tailCounts': {str(k): sum(v >= k for v in d) for k in (2, 5, 10)},
            'precisionStrict30m': {str(k): {'hits': sum(v >= k for v in mfe), 'denominator': len(mfe),
                'rate': sum(v >= k for v in mfe)/len(mfe) if mfe else None} for k in (1, 2, 3, 5)},
            'missingCounts': [sum(r['missing'][j] for r in rows) for j in (0, 1)],
            'bothMissing': sum(all(r['missing']) for r in rows)}


def coexistence(rows):
    scored = [r for r in rows if r['status'] == 'SCORED']
    positive = [r for r in scored if r['positiveScoreBand']]
    nonpositive = [r for r in scored if not r['positiveScoreBand']]
    anchors = [r for r in scored if r['v1Anchor']]
    retained = [r for r in anchors if r['positiveScoreBand']]
    winners = {}
    for k in (1, 2, 3, 5):
        baseline = [r for r in anchors if r['MFE'] is not None and r['MFE'] >= k]
        keep = sum(r['positiveScoreBand'] for r in baseline)
        winners[str(k)] = {'baselineWinners': len(baseline), 'positiveScoreWinners': keep,
                          'retention': keep/len(baseline) if baseline else None}
    by_symbol = collections.defaultdict(list)
    for r in scored:
        by_symbol[r['symbol']].append(r)
    return {'allScored': band_metrics(scored), 'positive': band_metrics(positive),
            'nonpositive': band_metrics(nonpositive), 'v1ScoredAnchors': band_metrics(anchors),
            'v1PositiveAnchors': band_metrics(retained), 'v1WinnerRetention': winners,
            'v1AnchorScoreBandThroughput': len(retained)/len(anchors) if anchors else None,
            'symbols': {s: {'all': band_metrics(v),
                           'positive': band_metrics([r for r in v if r['positiveScoreBand']])}
                        for s, v in sorted(by_symbol.items())},
            'warning': 'SCORE BANDS ONLY; no Entry state, no executable trade count or Portfolio result'}


def partition(rows, c, index, group=None):
    fold = c['cv']['chronological'][index]
    training = [r for r in rows if r['sessionDate'] in fold['trainDates'] and
                (group is None or frozen.symbol_group(r['symbol']) != group)]
    held = [r for r in rows if r['sessionDate'] in fold['evaluationDates'] and
            (group is None or frozen.symbol_group(r['symbol']) == group)]
    if ({r['sessionDate'] for r in training} & {r['sessionDate'] for r in held}
            or {r['symbolSessionId'] for r in training} & {r['symbolSessionId'] for r in held}):
        raise m.IntegrityError('SESSION_LEAKAGE')
    if group is not None and {r['symbol'] for r in training} & {r['symbol'] for r in held}:
        raise m.IntegrityError('HELD_SYMBOL_LEAKAGE')
    return training, held


def gate(name, value, op, limit):
    status = 'INCONCLUSIVE'
    if value is not None:
        passed = {'>': value > limit, '>=': value >= limit, '<=': value <= limit}[op]
        status = 'PASS' if passed else 'FAIL'
    return {'name': name, 'value': value, 'operator': op, 'limit': limit, 'status': status}


def decide(units, chrono, symbols, removed, bands, c):
    limits = c['screenGates']
    by = {u['name']: u['metrics'] for u in units}
    cr = [by['chrono-'+str(i)]['spearman'] for i in range(1, 5)]
    sy = [by['symbol-'+str(i)]['spearman'] for i in range(5)]
    g = [gate('chronologicalPositiveSpearmanFolds', sum(x is not None and x > 0 for x in cr), '>=', limits['chronologicalPositiveSpearmanFoldsMin']),
         gate('chronologicalPooledMseSkill', chrono['mseSkill'], '>', 0.),
         gate('symbolPositiveSpearmanGroups', sum(x is not None and x > 0 for x in sy), '>=', limits['symbolPositiveSpearmanGroupsMin']),
         gate('symbolPooledMseSkill', symbols['mseSkill'], '>', 0.),
         gate('top2RemovedChronologicalSpearman', removed['spearman'], '>', 0.),
         gate('top2RemovedChronologicalMseSkill', removed['mseSkill'], '>', 0.)]
    # A missing unit is unknown support, not a measured negative association.
    if any(x is None for x in cr):
        g[0]['status'] = 'INCONCLUSIVE'
    if any(x is None for x in sy):
        g[2]['status'] = 'INCONCLUSIVE'
    all_, pos = bands['allScored'], bands['positive']
    a, b = all_['Q']['mean'], pos['Q']['mean']
    g.append(gate('positiveBandMeanQUplift', b-a if a is not None and b is not None else None, '>', 0.))
    a, b = all_['D30']['mean'], pos['D30']['mean']
    g.append(gate('positiveBandMeanD30Ratio', b/a if a is not None and a > 0 and b is not None else None, '<=', limits['positiveBandMeanD30RatioMax']))
    for k in (3, 5):
        g.append(gate('v1AnchorWinnerRetention'+str(k), bands['v1WinnerRetention'][str(k)]['retention'], '>=', limits['v1AnchorWinnerRetention'+str(k)+'Min']))
    g.append(gate('v1AnchorScoreBandThroughput', bands['v1AnchorScoreBandThroughput'], '>=', limits['v1AnchorScoreBandThroughputMin']))
    for metric, key in [('targetCoverage', 'absoluteTargetCoverageGapMax'), ('D30Coverage', 'absoluteD30CoverageGapMax')]:
        a, b = all_[metric], pos[metric]
        g.append(gate(key, abs(a-b) if a is not None and b is not None else None, '<=', limits[key]))
    verdict = 'FAST_FAIL_KILL' if any(x['status'] == 'FAIL' for x in g) else (
        'FAST_FAIL_CONTINUE' if all(x['status'] == 'PASS' for x in g) else 'FAST_FAIL_INCONCLUSIVE')
    return verdict, g


def run():
    c = audit_protocol()
    if (BASE/'result.json').exists() or (BASE/'predictions.json.gz').exists():
        raise m.IntegrityError('SINGLE_RUN_ALREADY_EXISTS_NO_PERFORMANCE_RETRY')
    receipt = read(str((BASE/'prefit.json').relative_to(ROOT)))
    if receipt['protocolSHA'] != m.PROTOCOL_SHA or receipt['status'] != 'PASS' or not receipt['syntheticOnly']:
        raise m.IntegrityError('PREFIT_GATE')
    for path in PREFIT_SOURCES:
        if sha(path) != receipt['sourcePins'][path]:
            raise m.IntegrityError('PREFIT_CODE_CHANGED:'+path)
    frozen_report, _, _ = frozen.audit()
    rows = ndjson(frozen.FEATURES)
    baseline = {r['selectorEventId']: r for r in ndjson(frozen.PREDICTIONS)}
    strict = {r['selectorEventId']: r for r in read(frozen.LABELS)['events']}
    paths = {r['selectorEventId']: r for r in read('docs/evidence/phase57-msh-entry-long-v2-development/paths.json.gz')['events']}
    ids = {r['selectorEventId'] for r in rows}
    if len(rows) != 3800 or len(ids) != 3800 or ids != set(paths) or ids != set(strict) or ids != set(baseline):
        raise m.IntegrityError('CONDITIONAL_UNIVERSE_IDENTITY')
    # All inputs materialized before future labels, with an explicit narrow schema.
    inputs = {r['selectorEventId']: m.extract_inputs(r) for r in rows}
    labels, ledger, ends = {}, [], {}
    for r in rows:
        eid = r['selectorEventId']
        out = exit_outcome(paths[eid])
        labels[eid] = m.target_from_exit(out)
        ends[eid] = out.get('exitTimestamp')
        ledger.append({'eventId': eid, 'symbol': r['symbol'], 'sessionDate': r['sessionDate'],
                       'target': labels[eid], 'exit': out, 'v1Anchor': baseline[eid]['state'] == 'ENTER',
                       'strictD30Labelable': strict[eid]['labelable'], 'strictCensorReason': strict[eid]['reason']})
    write(BASE/'target-ledger.json.gz', ledger)
    units, records, models, attempts = [], [], [], 0
    plan = [('chrono-'+str(i+1), i, None) for i in range(4)] + [('symbol-'+str(g), 3, g) for g in range(5)]
    for name, index, group in plan:
        training, evaluation = partition(rows, c, index, group)
        next_start = min(m.helpers.timestamp(r['decisionTimestamp']) for r in evaluation)
        purged = [r['selectorEventId'] for r in training if ends[r['selectorEventId']] is not None and
                  m.helpers.timestamp(ends[r['selectorEventId']]) >= next_start]
        training = [r for r in training if r['selectorEventId'] not in set(purged)]
        if attempts >= c['cv']['maximumProjectFits']:
            raise m.IntegrityError('FIT_BUDGET')
        attempts += 1
        try:
            artifact = m.roundtrip(m.fit([inputs[r['selectorEventId']] for r in training], labels))
            scored = m.predict(artifact, [inputs[r['selectorEventId']] for r in evaluation])
        except m.FitError as exc:
            units.append({'name': name, 'status': 'FIT_SUPPORT_UNKNOWN', 'reason': str(exc),
                          'metrics': regression_metrics([])})
            continue
        models.append({'unit': name, 'artifact': artifact})
        enriched = []
        for p in scored:
            eid = p['eventId']; lab = strict[eid]
            enriched.append(p | {'unit': name, 'scope': 'chronological' if group is None else 'symbolDisjointLastWindow',
                'actualQ': labels[eid], 'D30': max(0., -lab['trueMaePct']) if lab['labelable'] else None,
                'MFE': lab['mfePct'] if lab['labelable'] else None, 'v1Anchor': baseline[eid]['state'] == 'ENTER'})
        records.extend(enriched)
        units.append({'name': name, 'status': 'MEASURED', 'trainInputRows': len(training),
            'trainLabelableRows': artifact['training']['labelableRows'], 'evaluationRows': len(evaluation),
            'purgedIds': purged, 'sessionOverlap': 0, 'symbolSessionOverlap': 0,
            'heldSymbolOverlap': 0 if group is not None else 'NOT_APPLICABLE',
            'modelSHA': artifact['artifactSHA'], 'metrics': regression_metrics(enriched),
            'bands': coexistence(enriched), 'trainIdsSHA': m.digest([r['selectorEventId'] for r in training]),
            'evalIdsSHA': m.digest([r['selectorEventId'] for r in evaluation])})
        print(json.dumps({'unit': name, 'train': len(training), 'labelable': artifact['training']['labelableRows'],
                          'eval': len(evaluation), 'measured': units[-1]['metrics']}), flush=True)
    scopes = {k: [r for r in records if r['scope'] == k] for k in ['chronological', 'symbolDisjointLastWindow']}
    duplicates = {k: len(v)-len({r['eventId'] for r in v}) for k, v in scopes.items()}
    if any(duplicates.values()):
        raise m.IntegrityError('DUPLICATE_HELD_RECORD')
    sums = collections.defaultdict(float)
    for r in scopes['chronological']:
        if r['status'] == 'SCORED' and r['actualQ'] is not None:
            sums[r['symbol']] += r['actualQ']
    ranked = sorted(((s, v) for s, v in sums.items() if v > 0), key=lambda x: (-x[1], x[0]))
    top = {s for s, _ in ranked[:2]}
    reduced = regression_metrics([r for r in scopes['chronological'] if r['symbol'] not in top])
    pooled = {k: regression_metrics(v) for k, v in scopes.items()}
    bands = coexistence(scopes['chronological'])
    verdict, gates = decide(units, pooled['chronological'], pooled['symbolDisjointLastWindow'], reduced, bands, c)
    old_summary = read('docs/evidence/phase57-msh-entry-long-v2-1-development/run/summary.json')
    result = {'protocolSHA': m.PROTOCOL_SHA, 'protocolPrecommitHead': 'ab6fa75fa778b2790165781e7c7749cb596d4741',
        'verdict': verdict, 'exposure': 'HISTORICAL_DEVELOPMENT_OUTCOME_EXPOSED_CONDITIONAL_UNIVERSE',
        'target': c['target'], 'featureOrder': m.FEATURE_ORDER, 'units': units, 'pooled': pooled,
        'coexistence': bands, 'gates': gates,
        'top2RemovalDiagnostic': {'symbols': sorted(top), 'ranking': ranked, 'metrics': reduced,
            'scope': 'SUM_REFERENCE_RETURN_OVER_REPEATED_SELECTION_EVENTS_NOT_PORTFOLIO_CONTRIBUTION'},
        'coverage': {'candidates': len(rows), 'sessions': len(c['universe']['sessions']),
            'QLabelable': sum(x is not None for x in labels.values()),
            'QCensored': sum(x is None for x in labels.values()),
            'QReasons': dict(collections.Counter(r['exit']['reason'] for r in ledger if r['target'] is None)),
            'strictD30Labelable': sum(r['labelable'] for r in strict.values()),
            'v1Anchors': sum(r['state'] == 'ENTER' for r in baseline.values()),
            'rawQualified': sum(r['expectedClass'] >= 2 for r in baseline.values()),
            'inheritedV1FullStream': old_summary['coverage']},
        'integrity': {'sourcePinsVerified': len(c['sourcePins']), 'frozenAudit': frozen_report['verdict'],
            'scopeDuplicateCounts': duplicates, 'sessionOverlap': 0, 'heldSymbolOverlap': 0,
            'projectFitAttempts': attempts, 'successfulProjectFits': len(models),
            'predictionRecords': len(records), 'numericPredictions': sum(r['status'] == 'SCORED' for r in records),
            'prototypeTargetCount': 1, 'modelFamilyCount': 1, 'thresholdSearch': 0,
            'prototypeRetuning': 0, 'newFeatures': 0, 'extraTargets': 0,
            'fresh': 0, 'entryOos': 0, 'exitOos': 0, 'prospective': 0,
            'jQuantsRequests': 0, 'yahooRequests': 0, 'otherPriceRequests': 0,
            'shortEvaluation': 0, 'fullDevelopmentRuns': 0, 'newPortfolioRuns': 0},
        'portfolio': {'role': 'SECONDARY_REUSED_EVIDENCE', 'unresolvedPositions': 1,
            'lockedCashJpy': 335300, 'finalEquity': None, 'maxDrawdown': None,
            'reason': 'UNRESOLVED_FROZEN_EXIT_EXPOSURE; historical +23.05% belongs to different173 subset',
            'engineChanged': False, 'syntheticLiquidation': False}, 'safety': c['safety'],
        'limitations': ['Upstream Selector/v1 are outcome-exposed and are not refitted in each fold.',
            'Score bands are not executable accepted sets; overlapping selection events are not independent trades.',
            'EXIT net labels are reference marks; no bid/ask/depth/fill proof.',
            'Target/D30 censoring can be nonrandom; no interpolation or missing-as-zero.',
            'Held-symbol screen covers only the last15 sessions, not every chronological window.',
            'No p-values or Fresh/OOS generalization claim; failed screen kills this specified hypothesis only.'],
        'nextAction': 'STOP ON KILL/INCONCLUSIVE. CONTINUE requires full Pre-Development contract before further fits.'}
    write(BASE/'models.json.gz', models)
    write(BASE/'predictions.json.gz', records)
    write(BASE/'result.json', result)
    print(json.dumps({'verdict': verdict, 'failed': [g['name'] for g in gates if g['status'] == 'FAIL'],
                      'fits': attempts, 'predictions': len(records)}))


if __name__ == '__main__':
    run()
