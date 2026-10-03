"""Read saved evidence only. No model/runtime import, fit, prediction, or replay.

ENTER identities preserve decisions; future labels are diagnostic only. Feature
terms are aggregated individually and never summed into new model predictions.
"""
import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/evidence/phase57-msh-entry-long-v2-root-cause'
DEV = ROOT / 'docs/evidence/phase57-msh-entry-long-v2-development'
CONTRACT = ROOT / 'predict/research/phase57-msh-entry-long-v2-predevelopment-contract-v1.json'
FEATURES = ROOT / 'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz'
LABELS = ROOT / 'docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/path-diagnostics.json.gz'
LEVELS = (1, 2, 3, 5)
ORDER = ['frozenSelectorRidgeScore', 'directionalMomentum3Pct', 'directionalPullback6Pct', 'momentum3Missing', 'pullback6Missing']


def read(path):
    b = Path(path).read_bytes()
    return json.loads(gzip.decompress(b) if str(path).endswith('.gz') else b)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(a, b):
    return a is b if a is None or b is None else math.isclose(a, b, abs_tol=1e-10, rel_tol=1e-10)


def quantile(values, q):
    if not values:
        return None
    v = sorted(values)
    x = (len(v) - 1) * q
    lo, hi = math.floor(x), math.ceil(x)
    return v[lo] if lo == hi else v[lo] * (hi - x) + v[hi] * (x - lo)


def dist(values):
    values = [v for v in values if v is not None]
    return {'n': len(values), 'mean': statistics.mean(values) if values else None,
            'median': statistics.median(values) if values else None,
            'p05': quantile(values, .05), 'p90': quantile(values, .9),
            'p95': quantile(values, .95), 'min': min(values) if values else None,
            'max': max(values) if values else None}


def correlation(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 2:
        return {'n': len(pairs), 'pearson': None}
    xs, ys = zip(*pairs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return {'n': len(pairs), 'pearson': sum((x - mx) * (y - my) for x, y in pairs) / den if den else None}


def group_id(symbol):
    return int(hashlib.sha256(('PHASE57_MSH_LONG_V2_GROUP_V1|' + symbol).encode()).hexdigest(), 16) % 5


def feature_values(row):
    raw = [row['ridgeScore']]
    flags = []
    for name in ORDER[1:3]:
        f = row['features'][name]
        present = f['status'] == 'AVAILABLE'
        require((f['value'] is not None) == present, 'FEATURE_MISSING_SEMANTICS')
        raw.append(f['value'] if present else None)
        flags.append(int(not present))
    return raw + flags


def scorable(row, artifact):
    v = feature_values(row)
    mandatory = [v[0], row['decisionPrice']]
    valid = all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in mandatory)
    return valid and row['decisionPrice'] > 0 and all(not bit or seen for bit, seen in zip(v[3:], artifact['missingSeen']))


def restore_saved_states(rows, enter_ids, artifact):
    """Decode saved outcomes of the unchanged state machine; never score a row."""
    chosen = set(enter_ids)
    require(chosen <= {r['selectorEventId'] for r in rows}, 'SAVED_ENTER_OUTSIDE_CALIBRATION')
    entered = set()
    states = {}
    for r in sorted(rows, key=lambda r: (r['decisionTimestamp'], r['symbol'], r['selectorEventId'])):
        eid, key = r['selectorEventId'], r['symbolSessionId']
        if eid in chosen:
            require(key not in entered and scorable(r, artifact), 'INVALID_SAVED_ENTER')
            states[eid] = 'ENTER'
            entered.add(key)
        elif key in entered:
            states[eid] = 'STATE_ALREADY_ENTERED'
        elif not scorable(r, artifact):
            states[eid] = 'INPUT_UNSCORABLE'
        else:
            states[eid] = 'RISK_REJECT'
    return states


def outcomes(ids, labels):
    values = [labels[e] for e in ids]
    known = [v for v in values if v['labelable']]
    d = [max(0., -v['trueMaePct']) for v in known]
    m = [v['mfePct'] for v in known]
    n = len(known)
    return {'rows': len(values), 'known': n, 'censored': len(values) - n,
            'censorReasons': dict(sorted(collections.Counter(v['reason'] for v in values if not v['labelable']).items())),
            'D30': dist(d), 'MFE': dist(m),
            'MAE': dist([v['trueMaePct'] for v in known]),
            'opportunity': {str(k): {'count': sum(x >= k for x in m), 'rate': sum(x >= k for x in m) / n if n else None} for k in LEVELS},
            'adverse': {str(k): {'count': sum(x >= k for x in d), 'rate': sum(x >= k for x in d) / n if n else None} for k in (2, 5, 10)},
            'D30_MFE': correlation(d, m)}


def verify_saved_metrics(rows, metrics, labels):
    ids = set(metrics['enterIds'])
    require(len(ids) == metrics['enterCount'], 'ENTER_COUNT')
    o = outcomes(ids, labels)
    require(o['known'] == metrics['strict30mCount'], 'STRICT30M_COUNT')
    require(close(o['D30']['mean'], metrics['meanD30']), 'MEAN_D30')
    observed_d30 = sorted([-labels[e]['trueMaePct'] for e in ids if labels[e]['labelable']], reverse=True)
    es = statistics.mean(observed_d30[:max(1, math.ceil(.05 * len(observed_d30)))]) if observed_d30 else None
    require(close(es, metrics['ES95D30']), 'ES95_D30')
    require(close(o['known'] / len(ids) if ids else None, metrics['coverageRate']), 'COVERAGE_RATE')
    for k in LEVELS:
        require(o['opportunity'][str(k)]['count'] == metrics['precision'][str(k)]['hits'], 'PRECISION_HITS')
        require(close(o['opportunity'][str(k)]['rate'], metrics['precision'][str(k)]['rate']), 'PRECISION_RATE')
    grouped = collections.defaultdict(list)
    for r in rows:
        grouped[r['symbolSessionId']].append(r)
    anchors = collections.Counter(); hits = collections.Counter()
    for rs in grouped.values():
        ordered = sorted(rs, key=lambda r: r['decisionTimestamp'])
        first = ordered[0]; first_time = dt.datetime.fromisoformat(first['decisionTimestamp'])
        # Every later saved decision lies at/after the original 30m endpoint.
        require(all((dt.datetime.fromisoformat(r['decisionTimestamp']) - first_time).total_seconds() >= 1800 for r in ordered[1:]), 'PRESERVATION_REQUIRES_SAVED_PATH')
        label = labels[first['selectorEventId']]
        if not label['labelable']:
            continue
        for k in LEVELS:
            if label['mfePct'] >= k:
                anchors[k] += 1
                hits[k] += int(first['selectorEventId'] in ids)
    for k in LEVELS:
        require(metrics['preservation'][str(k)]['anchors'] == anchors[k], 'PRESERVATION_ANCHOR')
        require(metrics['preservation'][str(k)]['hits'] == hits[k], 'PRESERVATION_HITS')
    return o


def independent_gate_status(g):
    a, b, limit = g.get('baseline'), g.get('candidate'), g['limit']
    if a is None or b is None:
        return 'INCONCLUSIVE'
    if g['name'] == 'absoluteStrictLabelCoverageGapMax':
        return 'PASS' if abs(a - b) <= limit + 1e-12 else 'FAIL'
    if a == 0:
        if g['operator'] == '<=' and g['name'] != 'adverseMeanRatioMax':
            return 'PASS' if b == 0 else 'FAIL'
        return 'INCONCLUSIVE'
    return 'PASS' if (b / a <= limit + 1e-12 if g['operator'] == '<=' else b / a >= limit - 1e-12) else 'FAIL'


def matrix(ids, labels):
    result = [[0] * 5 for _ in range(5)]
    unknown = 0
    joint = collections.Counter()
    for eid in ids:
        l = labels[eid]
        if not l['labelable']:
            unknown += 1
            continue
        d, m = max(0., -l['trueMaePct']), l['mfePct']
        i = sum(d >= x for x in (1, 2, 5, 10)); j = sum(m >= x for x in (1, 2, 3, 5))
        result[i][j] += 1
        joint[('HighRisk' if d >= 2 else 'LowRisk') + ('HighOpp' if m >= 3 else 'LowOpp')] += 1
    return {'cells': result, 'censored': unknown, 'quadrants': dict(sorted(joint.items()))}


def concentration(values):
    positive = sorted([(s, v) for s, v in values.items() if v > 0], key=lambda x: (-x[1], x[0]))
    mass = sum(v for _, v in positive)
    return {'total': sum(values.values()), 'positiveMass': mass,
            'negativeMass': -sum(v for v in values.values() if v < 0),
            'top1ShareOfPositiveMass': positive[0][1] / mass if positive else None,
            'top3ShareOfPositiveMass': sum(v for _, v in positive[:3]) / mass if mass else None,
            'positiveHHI': sum((v / mass) ** 2 for _, v in positive) if mass else None,
            'orderedPositive': positive, 'bySymbol': dict(sorted(values.items()))}


def save_json(path, value):
    Path(path).write_bytes(canonical(value) + b'\n')


def save_csv(path, rows):
    require(bool(rows), 'EMPTY_CSV')
    with Path(path).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def precision_decomposition(rows, baseline, candidate, states, labels):
    b, a = set(baseline['enterIds']), set(candidate['enterIds'])
    groups = {'common': b & a, 'v1Only': b - a, 'v2Only': a - b}
    detail = {name: outcomes(ids, labels) for name, ids in groups.items()}
    by_id = {r['selectorEventId']: r for r in rows}
    v2_by_session = {by_id[e]['symbolSessionId']: e for e in a}
    removed = []
    for eid in sorted(b - a):
        replacement = v2_by_session.get(by_id[eid]['symbolSessionId'])
        timing = None if not replacement else ('EARLIER_V2_ENTER' if by_id[replacement]['decisionTimestamp'] < by_id[eid]['decisionTimestamp'] else 'LATER_V2_ENTER')
        removed.append({'eventId': eid, 'stateAtV1Entry': states[eid], 'replacementV2Entry': replacement,
                        'timing': timing, 'labelable': labels[eid]['labelable'],
                        'MFE': labels[eid].get('mfePct') if labels[eid]['labelable'] else None})
    changes = {}
    for k in LEVELS:
        key = str(k)
        pb = baseline['precision'][key]['rate']; pa = candidate['precision'][key]['rate']
        pc = detail['common']['opportunity'][key]['rate']
        removal = pc - pb if pc is not None and pb is not None else None
        addition = pa - pc if pa is not None and pc is not None else None
        changes[key] = {'v1Precision': pb, 'commonPrecision': pc, 'v2Precision': pa,
                        'removalEffect': removal, 'additionEffect': addition,
                        'totalChange': pa - pb if pa is not None and pb is not None else None}
        if removal is not None and addition is not None:
            require(close(removal + addition, pa - pb), 'PRECISION_DECOMPOSITION')
    bounds = {}
    for name, metrics in [('v1', baseline), ('v2', candidate)]:
        n, known = metrics['enterCount'], metrics['strict30mCount']
        bounds[name] = {str(k): {'worst': metrics['precision'][str(k)]['hits'] / n if n else None,
                                'best': (metrics['precision'][str(k)]['hits'] + n - known) / n if n else None}
                        for k in LEVELS}
    return {'groups': detail, 'precisionChange': changes, 'v1OnlySavedDecisions': removed,
            'v1OnlyReasons': dict(collections.Counter(x['stateAtV1Entry'] for x in removed)),
            'censoringSensitivityBoundsNotImputation': bounds}


def cohorts(rows, states, labels):
    flags = collections.Counter(); partition = collections.Counter(); details = []
    for r in rows:
        eid = r['selectorEventId']; label = labels[eid]; state = states[eid]
        d = max(0., -label['trueMaePct']) if label['labelable'] else None
        m = label['mfePct'] if label['labelable'] else None
        found = []
        if not label['labelable']:
            found = ['F_CENSORED_UNKNOWN']; primary = found[0]
        elif state == 'STATE_ALREADY_ENTERED':
            primary = 'STATE_ALREADY_ENTERED_NOT_RISK_REJECTION'
        elif state == 'INPUT_UNSCORABLE':
            primary = 'INPUT_UNSCORABLE'
        elif state == 'RISK_REJECT':
            if d >= 2: found.append('A_CORRECT_RISK_REJECTION')
            if 1 <= m < 3: found.append('B_FALSE_REJECTION_LOW_OPPORTUNITY')
            if m >= 3: found.append('C_FALSE_REJECTION_HIGH_OPPORTUNITY')
            primary = ('C_FALSE_REJECTION_HIGH_OPPORTUNITY' if m >= 3 else
                       'B_FALSE_REJECTION_LOW_OPPORTUNITY' if m >= 1 else
                       'A_CORRECT_RISK_REJECTION_NO_OPPORTUNITY' if d >= 2 else
                       'OTHER_LOW_RISK_LOW_OPPORTUNITY_REJECTION')
        else:
            require(state == 'ENTER', 'UNKNOWN_SAVED_STATE')
            if d >= 2:
                found.append('D_FALSE_ACCEPT_RISK'); primary = found[0]
            elif m >= 1:
                found.append('E_GOOD_ACCEPT'); primary = found[0]
            else:
                primary = 'OTHER_LOW_RISK_LOW_OPPORTUNITY_ACCEPT'
        flags.update(found); partition[primary] += 1
        raw = feature_values(r)
        pattern = ('MOMENTUM_MISSING' if raw[3] else 'MOMENTUM_AVAILABLE') + '__' + ('PULLBACK_MISSING' if raw[4] else 'PULLBACK_AVAILABLE')
        details.append({'eventId': eid, 'symbol': r['symbol'], 'sessionDate': r['sessionDate'],
                        'decisionTimestamp': r['decisionTimestamp'], 'savedState': state,
                        'stateSource': 'SAVED_ENTER_IDS_PLUS_FROZEN_LATCH_AND_INPUT_VALIDITY',
                        'labelable': label['labelable'], 'D30': d, 'MFE': m,
                        'censorReason': None if label['labelable'] else label['reason'],
                        'diagnosticFlags': found, 'exclusiveDiagnostic': primary, 'missingPattern': pattern})
    return {'overlappingFlags': dict(sorted(flags.items())), 'exclusivePartition': dict(sorted(partition.items()))}, details


def input_attribution(rows, states, labels, artifact):
    """Marginal terms only. This function never returns predicted D30 values."""
    subsets = {'ALL': rows}
    for state in ('ENTER', 'RISK_REJECT', 'STATE_ALREADY_ENTERED', 'INPUT_UNSCORABLE'):
        subsets[state] = [r for r in rows if states[r['selectorEventId']] == state]
    subsets['FALSE_REJECT_HIGH_OPPORTUNITY'] = [r for r in subsets['RISK_REJECT'] if labels[r['selectorEventId']]['labelable'] and labels[r['selectorEventId']]['mfePct'] >= 3]
    subsets['FALSE_ACCEPT_RISK'] = [r for r in subsets['ENTER'] if labels[r['selectorEventId']]['labelable'] and labels[r['selectorEventId']]['trueMaePct'] <= -2]
    result = []
    for j, name in enumerate(ORDER):
        coefficient = artifact['coefficients'][j]
        scale = artifact['stds'][j] if j < 3 else 1.
        center = artifact['means'][j] if j < 3 else 0.
        median = artifact['medians'][j - 1] if j in (1, 2) else None
        for group, rs in subsets.items():
            raw = [feature_values(r)[j] for r in rs]
            imputed = [median if v is None else v for v in raw]
            # One component at a time. No vector dot-product, intercept addition,
            # score reconstruction, threshold application or feature ablation.
            terms = [coefficient * ((v - center) / scale) for v in imputed]
            result.append({'input': name, 'group': group, 'coefficient': coefficient, 'scale': scale,
                           'center': center, 'savedMedian': median, 'rawUnitSlope': coefficient / scale,
                           'directionOnD30': 'INCREASES' if coefficient > 0 else 'DECREASES' if coefficient < 0 else 'ZERO',
                           'observed': sum(v is not None for v in raw), 'missing': sum(v is None for v in raw),
                           'rawDistribution': dist(raw), 'additiveTermDistribution': dist(terms),
                           'meaning': 'MARGINAL_SAVED_MODEL_TERM_NOT_CAUSAL_ABLATION_NOT_NEW_PREDICTION'})
    patterns = collections.defaultdict(list)
    for r in rows:
        flags = feature_values(r)[3:]
        patterns['both_available' if flags == [0, 0] else 'both_missing' if flags == [1, 1] else 'momentum_missing' if flags[0] else 'pullback_missing'].append(r)
    missing = {}
    for pattern, rs in sorted(patterns.items()):
        ids = [r['selectorEventId'] for r in rs]
        missing[pattern] = {'outcomes': outcomes(ids, labels), 'states': dict(collections.Counter(states[e] for e in ids)),
                            'accepted': outcomes([e for e in ids if states[e] == 'ENTER'], labels),
                            'riskRejected': outcomes([e for e in ids if states[e] == 'RISK_REJECT'], labels)}
    known = [r for r in rows if labels[r['selectorEventId']]['labelable']]
    score = [r['ridgeScore'] for r in known]
    relations = {'ridgeVsActualD30': correlation(score, [-labels[r['selectorEventId']]['trueMaePct'] for r in known]),
                 'ridgeVsMFE': correlation(score, [labels[r['selectorEventId']]['mfePct'] for r in known]),
                 'ridgeVsOpportunity': {str(k): correlation(score, [int(labels[r['selectorEventId']]['mfePct'] >= k) for r in known]) for k in LEVELS},
                 'ridgeVsPredictedD30': None,
                 'continuousPredictionUnavailable': 'Inner predictions not serialized; no regeneration permitted.'}
    return {'marginalTerms': result, 'missingPatterns': missing, 'opportunityContamination': relations}


def symbol_attribution(rows, states, labels, baseline_ids, accepted_ids):
    by_id = {r['selectorEventId']: r for r in rows}
    known_b = [e for e in baseline_ids if labels[e]['labelable']]
    known_a = [e for e in accepted_ids if labels[e]['labelable']]
    contribution = collections.defaultdict(float)
    for ids, sign in ((known_b, 1.), (known_a, -1.)):
        for eid in ids:
            contribution[by_id[eid]['symbol']] += sign * (-labels[eid]['trueMaePct']) / len(ids)
    false_reject = collections.Counter(); false_accept = collections.Counter(); rejected_risk = collections.Counter()
    by_symbol = collections.defaultdict(list)
    for r in rows:
        e = r['selectorEventId']; l = labels[e]; state = states[e]; symbol = r['symbol']
        by_symbol[symbol].append(e)
        if not l['labelable']: continue
        if state == 'RISK_REJECT':
            if l['mfePct'] >= 1: false_reject[symbol] += 1
            if l['trueMaePct'] <= -2: rejected_risk[symbol] += 1
        if state == 'ENTER' and l['trueMaePct'] <= -2: false_accept[symbol] += 1
    per_symbol = {}
    for symbol, ids in sorted(by_symbol.items()):
        per_symbol[symbol] = {'rows': len(ids), 'states': dict(collections.Counter(states[e] for e in ids)),
                              'accepted': outcomes([e for e in ids if states[e] == 'ENTER'], labels),
                              'riskRejected': outcomes([e for e in ids if states[e] == 'RISK_REJECT'], labels)}
    return {'meanD30ImprovementComposition': concentration(contribution),
            'falseRejectedOpportunityConcentration': concentration(false_reject),
            'falseAcceptedRiskConcentration': concentration(false_accept),
            'correctRiskRejectionConcentration': concentration(rejected_risk),
            'bySymbol': per_symbol,
            'supportingOnly89180And57590': {s: per_symbol.get(s) for s in ('89180', '57590')}}


def review():
    scope = read(BASE / 'analysis-scope.json')
    require(sha(CONTRACT) == scope['contractSHA'], 'FROZEN_CONTRACT_SHA')
    require(sha(DEV / 'manifest.json') == scope['developmentEvidenceSHA'], 'FROZEN_EVIDENCE_SHA')
    manifest = read(DEV / 'manifest.json')
    for name, expected in manifest['files'].items():
        require(sha(ROOT / name) == expected, 'SOURCE_CHANGED:' + name)
    c = read(CONTRACT); old = read(DEV / 'run/development.json.gz')
    with gzip.open(FEATURES, 'rt') as f:
        rows = list(map(json.loads, f))
    labels = {r['selectorEventId']: r for r in read(LABELS)['events']}
    require(len(rows) == len(labels) == 3800, 'SHARED_UNIVERSE')
    require({r['selectorEventId'] for r in rows} == set(labels), 'LABEL_IDENTITIES')
    require(old['projectCounters']['projectFits'] == 24 and old['projectCounters']['predictionRows'] == 10000, 'DEVELOPMENT_COUNTS')
    require(all(v == 0 for v in old['integrity'].values()), 'PRIOR_INTEGRITY')
    require(len(old['safety']) == 9 and all(v is False for v in old['safety'].values()), 'SAFETY')
    results = []; candidate_details = []; threshold_csv = []; coefficient_csv = []; unit_csv = []
    failure_counts = collections.defaultdict(collections.Counter)
    for saved in old['chronological'] + old['symbolDisjoint']:
        fold = c['cv']['folds'][saved['fold'] - 1]
        start, end = fold['innerCalibrationOrdinals']
        dates = set(c['universe']['sessions'][start - 1:end])
        group = saved['heldGroup']
        calibration = [r for r in rows if r['sessionDate'] in dates and (group is None or group_id(r['symbol']) != group)]
        require(len(calibration) == saved['innerBaseline']['candidateRows'], 'CALIBRATION_MEMBERSHIP')
        artifact_path = DEV / 'run/models' / (saved['name'] + '-inner.json')
        artifact = read(artifact_path)
        expected = artifact['artifactSHA']
        require(hashlib.sha256(canonical({k: v for k, v in artifact.items() if k != 'artifactSHA'})).hexdigest() == expected, 'MODEL_ARTIFACT_SHA')
        require(artifact['featureOrder'] == ORDER and artifact['lambda'] == 1., 'MODEL_FROZEN')
        require(not set(artifact['training']['sessions']) & dates, 'INNER_LEAKAGE')
        if group is not None:
            require(all(group_id(s) != group for s in artifact['training']['symbols']), 'SYMBOL_FIT_LEAKAGE')
        require(saved['outerPredictions'] == [] and saved['outerDecisions'] == [], 'NO_OUTER_PREDICTIONS_EXPECTED')
        baseline = saved['innerBaseline']
        verify_saved_metrics(calibration, baseline, labels)
        failure_by_threshold = {}
        for threshold in (1, 2, 5, 10):
            original = saved['innerThresholdResults'][str(threshold)]
            verify_saved_metrics(calibration, original['metrics'], labels)
            independently_failed = []
            for gate in original['gates']:
                limits = {**c['numericGates']['primary'], **c['numericGates']['guardrails']}
                require(gate['limit'] == limits[gate['name']], 'FROZEN_GATE_LIMIT')
                status = independent_gate_status(gate)
                require(status == gate['status'], 'GATE_STATUS_CHANGED')
                if status != 'PASS':
                    independently_failed.append(gate['name'] + ':' + status)
                    failure_counts[threshold][gate['name'] + ':' + status] += 1
            require(bool(independently_failed), 'ELIGIBLE_THRESHOLD_CONTRADICTS_NONE')
            failure_by_threshold[str(threshold)] = independently_failed
            m = original['metrics']
            threshold_csv.append({'unit': saved['name'], 'fold': saved['fold'], 'heldGroup': group,
                                  'threshold': threshold, 'v1Enter': baseline['enterCount'], 'enter': m['enterCount'],
                                  'strict': m['strict30mCount'], 'D30': m['meanD30'],
                                  **{f'precision{k}': m['precision'][str(k)]['rate'] for k in LEVELS},
                                  'failures': '|'.join(independently_failed), 'selection': 'NONE'})
        require(saved['selection']['threshold'] is None, 'NONE_REQUIRED')
        target = saved['innerThresholdResults']['2']['metrics']
        states = restore_saved_states(calibration, target['enterIds'], artifact)
        all_ids = set(states); accepted = {e for e in states if states[e] == 'ENTER'}
        rejected = {e for e in states if states[e] == 'RISK_REJECT'}
        active = accepted | rejected
        observed = {name: outcomes([e for e in states if states[e] == name], labels) for name in ('ENTER', 'RISK_REJECT', 'STATE_ALREADY_ENTERED', 'INPUT_UNSCORABLE')}
        counts, event_details = cohorts(calibration, states, labels)
        for event in event_details:
            candidate_details.append({'unit': saved['name'], 'heldGroup': group, **event})
        rejected_winners = {}
        rejected_tails = {}
        for k in LEVELS:
            r = sum(labels[e]['labelable'] and labels[e]['mfePct'] >= k for e in rejected)
            n = sum(labels[e]['labelable'] and labels[e]['mfePct'] >= k for e in active)
            rejected_winners[str(k)] = {'count': r, 'activeWinnerDenominator': n, 'fractionOfActiveWinners': r / n if n else None,
                                        'fractionOfKnownRiskRejects': r / observed['RISK_REJECT']['known'] if observed['RISK_REJECT']['known'] else None}
        for k in (2, 5, 10):
            r = sum(labels[e]['labelable'] and labels[e]['trueMaePct'] <= -k for e in rejected)
            n = sum(labels[e]['labelable'] and labels[e]['trueMaePct'] <= -k for e in active)
            rejected_tails[str(k)] = {'count': r, 'activeTailDenominator': n, 'fractionOfActiveTails': r / n if n else None}
        decomp = precision_decomposition(calibration, baseline, target, states, labels)
        inputs = input_attribution(calibration, states, labels, artifact)
        symbols = symbol_attribution(calibration, states, labels, baseline['enterIds'], target['enterIds'])
        require(close(symbols['meanD30ImprovementComposition']['total'], baseline['meanD30'] - target['meanD30']), 'SYMBOL_IMPROVEMENT_SUM')
        v1_intersection = len(set(baseline['enterIds']) & accepted)
        unit = {'unit': saved['name'], 'fold': saved['fold'], 'heldGroup': group, 'calibrationDates': sorted(dates),
                'scope': 'CHRONOLOGICAL_INNER_CALIBRATION' if group is None else 'SYMBOL_COMPLEMENT_INNER_CALIBRATION_NOT_HELD_SYMBOL_OOF',
                'candidateRows': len(calibration), 'uniqueSymbols': len({r['symbol'] for r in calibration}),
                'stateCounts': dict(sorted(collections.Counter(states.values()).items())),
                'failureByThreshold': failure_by_threshold, 'selectedThreshold': None,
                'v1': baseline, 'threshold2': target, 'cohorts': counts, 'stateOutcomes': observed,
                'rejectedWinners': rejected_winners, 'rejectedTails': rejected_tails,
                'riskOpportunityMatrices': {name: matrix(ids, labels) for name, ids in [('riskRejected', rejected), ('accepted', accepted), ('allActive', active), ('allCandidates', all_ids)]},
                'precisionDecomposition': decomp, 'inputAttribution': inputs, 'symbolAttribution': symbols,
                'modelFileSHA': sha(artifact_path), 'interceptSaved': artifact['intercept'],
                'modelArtifactSHA': artifact['artifactSHA'], 'v1EnterRetainedSameTimestamp': v1_intersection,
                'savedThreshold5ContrastDiagnostic': {
                    'scope': 'EXISTING_FROZEN_TAU5_RESULT_ONLY_NO_NEW_CONTROL_OR_PREDICTION',
                    'tau5Enter': saved['innerThresholdResults']['5']['metrics']['enterCount'],
                    'tau5MeanD30': saved['innerThresholdResults']['5']['metrics']['meanD30'],
                    'tau2MinusTau5MeanD30': target['meanD30'] - saved['innerThresholdResults']['5']['metrics']['meanD30'],
                    'percentImprovementOverTau5': 100 * (1 - target['meanD30'] / saved['innerThresholdResults']['5']['metrics']['meanD30'])}}
        results.append(unit)
        unit_csv.append({'unit': unit['unit'], 'heldGroup': group, 'candidateRows': len(calibration),
                         'v1Enter': baseline['enterCount'], 'v2Enter': target['enterCount'],
                         'v1Strict': baseline['strict30mCount'], 'v2Strict': target['strict30mCount'],
                         'v1D30': baseline['meanD30'], 'v2D30': target['meanD30'],
                         'D30ImprovementPct': 100 * (1 - target['meanD30'] / baseline['meanD30']),
                         'riskReject': len(rejected), 'latchSkip': observed['STATE_ALREADY_ENTERED']['rows'],
                         'riskRejectKnown': observed['RISK_REJECT']['known'], 'riskRejectCensored': observed['RISK_REJECT']['censored'],
                         **{f'rejectedWinner{k}': rejected_winners[str(k)]['count'] for k in LEVELS},
                         **{f'v1Precision{k}': baseline['precision'][str(k)]['rate'] for k in LEVELS},
                         **{f'v2Precision{k}': target['precision'][str(k)]['rate'] for k in LEVELS},
                         **{f'v1Preservation{k}': baseline['preservation'][str(k)]['rate'] for k in LEVELS},
                         **{f'v2Preservation{k}': target['preservation'][str(k)]['rate'] for k in LEVELS},
                         **{f'flag{k}': v for k, v in counts['overlappingFlags'].items()} })
        for term in inputs['marginalTerms']:
            coefficient_csv.append({'unit': unit['unit'], 'input': term['input'], 'group': term['group'],
                'coefficient': term['coefficient'], 'scale': term['scale'], 'center': term['center'],
                'savedMedian': term['savedMedian'], 'rawUnitSlope': term['rawUnitSlope'],
                'direction': term['directionOnD30'], 'observed': term['observed'], 'missing': term['missing'],
                **{'term_' + k: v for k, v in term['additiveTermDistribution'].items()}})
    require(len(results) == 24 and len(threshold_csv) == 96 and len(candidate_details) == 10000, 'REVIEW_TOTALS')
    p = old['portfolioBaseline']
    unresolved = p['unresolvedPositions']
    require(close(sum(r['notional'] for r in unresolved), p['lockedPurchaseNotionalJpy']), 'LOCKED_CAPITAL_SUM')
    portfolio = {'scope': 'SAVED_V1_FULL_EVAL60_STREAM_NOT_173_COMPLETE_CASE_REFERENCE',
                 'status': p['status'], 'candidateEnterSignals': p['trade']['candidates'],
                 'acceptedPositions': p['trade']['accepted'], 'closedPositions': p['trade']['closed'],
                 'unresolvedCount': len(unresolved), 'lockedPurchaseNotionalJpy': p['lockedPurchaseNotionalJpy'],
                 'unresolvedPositions': unresolved, 'reasonCounts': dict(collections.Counter(r['reason'] for r in unresolved)),
                 'reasonTaxonomy': {'sessionEnd': 0, 'missingBeforeExit': len(unresolved), 'explicitNoTrade': 0, 'auction': 0, 'other': 0},
                 'reasonQualification': 'Only recorded reasons. MISSING_BEFORE_EXIT does not distinguish no-trade versus provider gap; zero explicit categories does not prove absence.',
                 'allocationRejections': p['trade']['rejectionReasons'], 'firstUnknownValuation': p['firstUnknownValuation'],
                 'cashBalanceJpy': p['cashBalanceJpy'], 'finalEquityJpy': p['finalEquityJpy'], 'maxDrawdownPct': p['maxDrawdownPct'],
                 'cashReleasesAlreadyRecorded': p['capital']['cashReleaseCount'],
                 'replayPerformedThisReview': False, 'engineChanged': False,
                 'prior173SubsetReturnPct': 23.0531, 'prior173IsDifferentScope': True}
    audit = {'contractSHA': scope['contractSHA'], 'developmentEvidenceSHA': scope['developmentEvidenceSHA'],
             'sourceHead': scope['sourceHead'], 'priorModelFits': 24, 'priorPredictionRows': 10000,
             'savedInnerNumericPredictionRows': 0, 'savedThresholdEvaluationsVerified': 96,
             'NONESelectionsVerified': 24, 'savedOuterOOFRows': 0,
             'unavailableAnalyses': ['Continuous predictedD30 correlations/residuals/calibration: numeric inner predictions were not saved.',
                                     'Held-symbol OOF generalization: all outer replicas stopped before prediction.',
                                     'Causal feature/model ablation: prohibited. Marginal term associations do not establish causation.'],
             'safety': old['safety'], 'counters': {k: scope[k] for k in ['newFit', 'newPrediction', 'newOOF', 'thresholdSearch', 'contractChanges', 'freshAccess', 'oosAccess', 'prospectiveAccess', 'jquantsRequests', 'yahooRequests', 'otherProviderRequests', 'shortEvaluation']}}
    stability = {}
    for name, units in [('chronological', results[:4]), ('symbolComplementInner', results[4:])]:
        def gate_pass(u, gate):
            return not any(x.startswith(gate + ':') for x in u['failureByThreshold']['2'])
        stability[name] = {'units': len(units), 'D30ImprovementAtLeast10Pct': sum(gate_pass(u, 'adverseMeanRatioMax') for u in units),
            'D30NonWorseThanV1': sum(u['threshold2']['meanD30'] <= u['v1']['meanD30'] for u in units),
            'precision1Pass': sum(gate_pass(u, 'precision1RatioMin') for u in units),
            'precision2Pass': sum(gate_pass(u, 'precision2RatioMin') for u in units),
            'preservation3Pass': sum(gate_pass(u, 'preservation3RatioMin') for u in units),
            'preservation5Pass': sum(gate_pass(u, 'preservation5RatioMin') for u in units),
            'throughputPass': sum(gate_pass(u, 'throughputRatioMin') for u in units),
            'coveragePass': sum(gate_pass(u, 'absoluteStrictLabelCoverageGapMax') for u in units),
            'rejectedKnownD30HigherThanAccepted': sum(u['stateOutcomes']['RISK_REJECT']['D30']['mean'] is not None and u['stateOutcomes']['RISK_REJECT']['D30']['mean'] > u['stateOutcomes']['ENTER']['D30']['mean'] for u in units),
            'heldSymbolGeneralizationMeasured': False}
    repeated = {}
    for name, detail in [('chronological', [r for r in candidate_details if r['heldGroup'] is None]), ('symbolComplementInner', [r for r in candidate_details if r['heldGroup'] is not None])]:
        reject = [r for r in detail if r['savedState'] == 'RISK_REJECT']
        known_reject = [r for r in reject if r['labelable']]
        winner_counts = {str(k): collections.Counter(r['symbol'] for r in known_reject if r['MFE'] >= k) for k in LEVELS}
        repeated[name] = {'scope': 'REPLICA_MEMBERSHIPS_NOT_INDEPENDENT_SAMPLES',
            'riskRejections': len(reject), 'uniqueRiskRejectedEventIds': len({r['eventId'] for r in reject}),
            'knownRiskRejections': len(known_reject), 'uniqueKnownRiskRejectedEventIds': len({r['eventId'] for r in known_reject}),
            'rejectedWinnersByLevel': {k: concentration(v) for k, v in winner_counts.items()},
            'knownRiskRejectD30AtLeast2': sum(r['D30'] >= 2 for r in known_reject),
            'knownRiskRejectD30AtLeast5': sum(r['D30'] >= 5 for r in known_reject),
            'knownRiskRejectD30AtLeast10': sum(r['D30'] >= 10 for r in known_reject),
            'riskRejectWithAnyMissingInput': sum('MISSING' in r['missingPattern'] for r in reject),
            'uniqueKnownLowRiskHighOppRejected': len({r['eventId'] for r in known_reject if r['D30'] < 2 and r['MFE'] >= 3})}
    result = {'audit': audit, 'units': results, 'failureSummaryByThreshold': {str(k): dict(v) for k, v in failure_counts.items()},
              'stability': stability, 'repeatedObservationDiagnostics': repeated,
              'portfolioCoverageIndependentProblem': portfolio,
              'repeatObservationNotice': {'chronologicalRows': 2000, 'chronologicalUniqueEventIds': len({r['eventId'] for r in candidate_details if r['heldGroup'] is None}),
                 'symbolComplementRows': 8000, 'allUnitRows': 10000, 'independentSampleClaim': False}}
    (BASE / 'review.json.gz').write_bytes(gzip.compress(canonical(result) + b'\n', mtime=0))
    (BASE / 'candidate-attribution.ndjson.gz').write_bytes(gzip.compress(b''.join(canonical(r) + b'\n' for r in candidate_details), mtime=0))
    save_csv(BASE / 'threshold-failure-reproduction.csv', threshold_csv)
    # All units expose the same explicit cohort columns, including zero counts.
    flag_columns = sorted({k for r in unit_csv for k in r if k.startswith('flag')})
    for r in unit_csv:
        for k in flag_columns: r.setdefault(k, 0)
    keys = [k for k in unit_csv[0] if not k.startswith('flag')] + flag_columns
    save_csv(BASE / 'threshold2-by-unit.csv', [{k: r[k] for k in keys} for r in unit_csv])
    save_csv(BASE / 'input-attribution.csv', coefficient_csv)
    save_json(BASE / 'audit.json', audit)
    print(json.dumps({'verifiedNONE': 24, 'savedThresholdResults': 96, 'diagnosticMembershipRows': 10000, 'newFit': 0, 'newPrediction': 0}))
    return result


if __name__ == '__main__':
    review()
