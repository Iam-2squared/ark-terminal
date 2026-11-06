"""One preregistered signed-reference-quality probe, not an Entry policy.

Reuses audited causal projection/math helpers, never the old D30 fit/readout.
No state machine, portfolio, provider, threshold search or trading integration.
"""
import collections
import json
import math
import sys
from pathlib import Path

from predict.research import phase57_msh_entry_long_v2_d30 as helpers
np = helpers.np
PROTOCOL_SHA = '5349d28259b0764385a8de3b29038464eb8d639c992427df76a3fceb671ee5c6'
MODEL_ID = 'MSH_ENTRY_V22_NET_REFERENCE_QUALITY_PROBE_V1'
FEATURE_ORDER = ['frozenSelectorRidgeScore', 'directionalMomentum3Pct',
                 'directionalPullback6Pct', 'momentum3Missing', 'pullback6Missing']
extract_inputs = helpers.extract_inputs
validate_envelope = helpers.validate_envelope
symbol_weights = helpers.symbol_weights
weighted_median = helpers.weighted_median
canonical = helpers.canonical
digest = helpers.digest
finite = helpers.finite
IntegrityError = helpers.IntegrityError
FitError = helpers.FitError


def target_from_exit(outcome):
    if outcome['status'] == 'CENSORED':
        if outcome.get('netPct') is not None:
            raise IntegrityError('CENSORED_TARGET_HAS_VALUE')
        return None
    if outcome['status'] != 'EXIT_REFERENCE':
        raise IntegrityError('NONTERMINAL_EXIT_TARGET')
    gross, net = outcome.get('grossPct'), outcome.get('netPct')
    if not finite(gross) or not finite(net) or abs(net - (gross - .05)) > 1e-10:
        raise IntegrityError('FROZEN_COST_TARGET_MISMATCH')
    return float(net)


def fit(rows, labels):
    """Separate labels argument. Input membership never depends on evaluation labels."""
    if sys.version_info[:2] != (3, 12) or np.__version__ != '2.3.5':
        raise FitError('PINNED_RUNTIME_REQUIRED')
    ordered = sorted(rows, key=helpers.sort_key)
    if len({r['eventId'] for r in ordered}) != len(ordered):
        raise IntegrityError('DUPLICATE_TRAINING_ROW')
    selected, targets, excluded = [], [], []
    for r in ordered:
        validate_envelope(r)
        if not r['valid']:
            raise FitError('INVALID_MANDATORY_TRAINING_INPUT')
        q = labels[r['eventId']]
        if q is None:
            excluded.append(r['eventId'])
        elif not finite(q):
            raise IntegrityError('INVALID_SIGNED_TARGET')
        else:
            selected.append(r)
            targets.append(float(q))
    if len(selected) < 7 or len({r['symbol'] for r in selected}) < 2:
        raise FitError('INSUFFICIENT_TRAINING_SUPPORT')
    w = symbol_weights(selected)
    ids = [r['eventId'] for r in selected]
    raw = [r['raw'] for r in selected]
    if any(sum(r[j] is not None for r in raw) < 2 for j in range(3)):
        raise FitError('INSUFFICIENT_OBSERVED_SUPPORT')
    medians = [weighted_median([r[j] for r in raw], w, ids) for j in (1, 2)]
    filled = np.asarray([[r[0], r[1] if r[1] is not None else medians[0],
                          r[2] if r[2] is not None else medians[1]] for r in raw])
    mean = np.sum(w[:, None] * filled, axis=0)
    std = np.sqrt(np.sum(w[:, None] * (filled - mean) ** 2, axis=0))
    if not np.all(np.isfinite(std)) or np.any(std <= 0):
        raise FitError('INVALID_RAW_VARIANCE')
    masks = np.asarray([r['missing'] for r in selected], dtype=float)
    X = np.column_stack((np.ones(len(selected)), (filled - mean) / std, masks))
    y = np.asarray(targets)
    A = X.T @ (w[:, None] * X) + np.diag([0., 1., 1., 1., 1., 1.])
    rhs = X.T @ (w * y)
    theta = np.linalg.solve(A, rhs)
    residual = float(np.max(np.abs(A @ theta - rhs)))
    if not np.all(np.isfinite(theta)) or residual > 1e-10 * (1 + float(np.max(np.abs(rhs)))):
        raise FitError('NUMERICAL_SOLVE_FAILED')
    symbol_mass, session_mass = collections.defaultdict(float), collections.defaultdict(float)
    for r, weight in zip(selected, w):
        symbol_mass[r['symbol']] += float(weight)
        session_mass[r['symbol'] + '|' + r['sessionDate']] += float(weight)
    artifact = {'modelId': MODEL_ID, 'protocolSHA': PROTOCOL_SHA,
        'featureOrder': FEATURE_ORDER, 'lambda': 1., 'solver': 'numpy.linalg.solve',
        'readout': 'SIGNED_LINEAR_NO_CLIPPING', 'intercept': float(theta[0]),
        'coefficients': theta[1:].tolist(), 'medians': medians,
        'means': mean.tolist(), 'stds': std.tolist(),
        'missingSeen': [bool(np.any(masks[:, j] == 1)) for j in range(2)],
        'training': {'inputRows': len(rows), 'labelableRows': len(selected),
            'excludedIds': excluded, 'eligibleIds': ids,
            'sessions': sorted({r['sessionDate'] for r in selected}),
            'symbols': sorted(symbol_mass), 'symbolSessions': len(session_mass),
            'weightsSHA': digest(list(zip(ids, w.tolist()))),
            'weightSum': float(np.sum(w)), 'largestSymbolWeight': max(symbol_mass.values()),
            'largestSymbolSessionWeight': max(session_mass.values()),
            'missingCounts': np.sum(masks, axis=0).astype(int).tolist(),
            'bothMissingCount': int(np.sum(np.all(masks == 1, axis=1))),
            'constantMeanQ': float(w @ y), 'normalEquationResidualInf': residual,
            'objective': float(.5 * np.sum(w * (y - X @ theta) ** 2) + .5 * np.sum(theta[1:] ** 2))},
        'runtime': {'python': '.'.join(map(str, sys.version_info[:3])),
                    'numpy': np.__version__, 'dtype': 'float64', 'threads': 1}}
    artifact['artifactSHA'] = digest(artifact)
    validate_artifact(artifact)
    return artifact


def validate_artifact(artifact):
    a = dict(artifact)
    expected = a.pop('artifactSHA')
    if expected != digest(a):
        raise IntegrityError('ARTIFACT_HASH_MISMATCH')
    if (a['modelId'] != MODEL_ID or a['protocolSHA'] != PROTOCOL_SHA
            or a['featureOrder'] != FEATURE_ORDER or a['lambda'] != 1.
            or a['solver'] != 'numpy.linalg.solve' or a['readout'] != 'SIGNED_LINEAR_NO_CLIPPING'):
        raise IntegrityError('PROBE_CONTRACT_MISMATCH')
    for key, size in [('coefficients', 5), ('medians', 2), ('means', 3), ('stds', 3)]:
        if len(a[key]) != size or not all(finite(x) for x in a[key]):
            raise IntegrityError('ARTIFACT_PARAMETERS')
    if min(a['stds']) <= 0 or not finite(a['intercept']):
        raise IntegrityError('ARTIFACT_SCALE')


def predict(artifact, rows):
    validate_artifact(artifact)
    result = []
    if len({r['eventId'] for r in rows}) != len(rows):
        raise IntegrityError('DUPLICATE_PREDICTION_ROW')
    for r in sorted(rows, key=helpers.sort_key):
        validate_envelope(r)
        status = 'SCORED' if r['valid'] else r['invalidReason']
        if any(bit and not seen for bit, seen in zip(r['missing'], artifact['missingSeen'])):
            status = 'UNSUPPORTED_MISSING_STATE'
        prediction, contributions = None, None
        if status == 'SCORED':
            raw = r['raw']
            values = [raw[0], raw[1] if raw[1] is not None else artifact['medians'][0],
                      raw[2] if raw[2] is not None else artifact['medians'][1]]
            x = [(v - m) / s for v, m, s in zip(values, artifact['means'], artifact['stds'])] + r['missing']
            contributions = [v * beta for v, beta in zip(x, artifact['coefficients'])]
            prediction = float(artifact['intercept'] + math.fsum(contributions))
            if not finite(prediction):
                raise IntegrityError('NONFINITE_PREDICTION')
        result.append({k: r[k] for k in ['eventId', 'symbol', 'sessionDate', 'decisionTimestamp']} |
            {'status': status, 'predictedQ': prediction, 'contributions': contributions,
             'positiveScoreBand': (prediction > 0) if prediction is not None else None,
             'missing': r['missing'], 'trainingConstantQ': artifact['training']['constantMeanQ']})
    return result


def roundtrip(artifact):
    """Serialization check only, no refit or repeated Project prediction."""
    copy = json.loads(canonical(artifact))
    validate_artifact(copy)
    if copy != artifact:
        raise IntegrityError('SERIALIZATION_MISMATCH')
    return copy
