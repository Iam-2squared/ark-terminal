"""Frozen-contract LONG v2: one weighted Ridge adverse-magnitude model.

Runtime accepts a strict causal envelope. Training labels are a separate argument.
No provider, executable order path, model search, or alternate policy is present.
"""
import collections
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import sys

for _key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[_key] = '1'
import numpy as np

CONTRACT_SHA = '18818ffd1157c7ba15c93eb4723c3e28945c238e0e2f6a2440bee98c7ad1267f'
MODEL_ID = 'MSH_ENTRY_LONG_V2_D30_RIDGE_V1'
FEATURE_ORDER = ['frozenSelectorRidgeScore','directionalMomentum3Pct',
                 'directionalPullback6Pct','momentum3Missing','pullback6Missing']
THRESHOLDS = (1.,2.,5.,10.)
ENVELOPE_KEYS = {'eventId','symbol','sessionDate','decisionTimestamp','decisionPrice',
                 'raw','missing','valid','invalidReason'}


class IntegrityError(ValueError):
    pass


class FitError(ValueError):
    pass


def finite(value):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)


def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def timestamp(value):
    t = dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None:
        raise IntegrityError('TIMEZONE_REQUIRED')
    return t.timestamp()


def sort_key(row):
    return row['sessionDate'],timestamp(row['decisionTimestamp']),row['symbol'],row['eventId']


def extract_inputs(source):
    """Allowlisted projection: future outcome columns are neither copied nor read."""
    raw = [source['ridgeScore']]
    missing = []
    for name in FEATURE_ORDER[1:3]:
        value = source['features'][name]
        if value['status'] == 'AVAILABLE':
            if not finite(value['value']):
                raise IntegrityError('AVAILABLE_NONFINITE:'+name)
            raw.append(float(value['value']))
            missing.append(0)
        else:
            if value.get('value') is not None:
                raise IntegrityError('UNAVAILABLE_HAS_VALUE:'+name)
            raw.append(None)
            missing.append(1)
    valid = (finite(raw[0]) and finite(source['decisionPrice']) and source['decisionPrice'] > 0)
    if source.get('direction','LONG') != 'LONG':
        raise IntegrityError('LONG_ONLY')
    date = dt.datetime.fromtimestamp(timestamp(source['decisionTimestamp']),dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    if date != source['sessionDate']:
        raise IntegrityError('CROSS_SESSION_REFERENCE')
    return {'eventId':source['selectorEventId'],'symbol':source['symbol'],
            'sessionDate':source['sessionDate'],'decisionTimestamp':source['decisionTimestamp'],
            'decisionPrice':source['decisionPrice'],'raw':raw,'missing':missing,
            'valid':valid,'invalidReason':None if valid else 'INPUT_INVALID'}


def validate_envelope(row):
    if set(row) != ENVELOPE_KEYS:
        raise IntegrityError('NON_CAUSAL_ENVELOPE')
    if len(row['raw']) != 3 or len(row['missing']) != 2:
        raise IntegrityError('FEATURE_ORDER_DIMENSION')
    for j,bit in enumerate(row['missing'],1):
        if type(bit) is not int or bit not in (0,1):
            raise IntegrityError('MISSING_FLAG')
        if (bit == 1) != (row['raw'][j] is None):
            raise IntegrityError('MISSING_VALUE_MISMATCH')
        if bit == 0 and not finite(row['raw'][j]):
            raise IntegrityError('FEATURE_NONFINITE')
    if row['valid'] and not (finite(row['raw'][0]) and finite(row['decisionPrice']) and row['decisionPrice'] > 0):
        raise IntegrityError('MANDATORY_VALUE_MISMATCH')


def d30_from_lows(reference, lows):
    """Training/evaluator helper only; caller supplies six strict valid future lows."""
    if not finite(reference) or reference <= 0 or len(lows) != 6 or any(not finite(v) or v <= 0 for v in lows):
        raise IntegrityError('STRICT_D30_LABEL_INVALID')
    return max(0.,-100.*(min(lows)/reference-1.))


def target_from_label(label):
    if not label['labelable']:
        return None
    if label.get('barCount') != 6 or not finite(label.get('trueMaePct')) or label['trueMaePct'] > 0:
        raise IntegrityError('STRICT_D30_LABEL_INVALID')
    return max(0.,-float(label['trueMaePct']))


def symbol_weights(rows):
    sessions = collections.defaultdict(set)
    counts = collections.Counter((r['symbol'],r['sessionDate']) for r in rows)
    for r in rows:
        sessions[r['symbol']].add(r['sessionDate'])
    if not rows:
        raise FitError('FIT_FAILED_EMPTY')
    return np.asarray([1./(len(sessions)*len(sessions[r['symbol']])*counts[r['symbol'],r['sessionDate']])
                       for r in rows],dtype=np.float64)


def weighted_median(values, weights, event_ids):
    data = sorted((float(v),eid,float(w)) for v,w,eid in zip(values,weights,event_ids) if v is not None)
    if len(data) < 2:
        raise FitError('FIT_FAILED_OBSERVED_SUPPORT')
    total = math.fsum(x[2] for x in data)
    if not (total > 0):
        raise FitError('FIT_FAILED_WEIGHT_SUPPORT')
    cumulative = 0.
    for value,_,weight in data:
        cumulative += weight/total
        if cumulative >= .5:
            return value
    raise FitError('FIT_FAILED_MEDIAN')


def fit(rows, labels):
    if sys.version_info[:2] != (3,12) or np.__version__ != '2.3.5':
        raise FitError('PINNED_RUNTIME_REQUIRED')
    ordered = sorted(rows,key=sort_key)
    if len({r['eventId'] for r in ordered}) != len(ordered):
        raise IntegrityError('DUPLICATE_TRAINING_ROW')
    targets = []
    eligible = []
    excluded = []
    for row in ordered:
        validate_envelope(row)
        if not row['valid']:
            raise FitError('FIT_FAILED_MANDATORY_INPUT')
        target = target_from_label(labels[row['eventId']])
        if target is None:
            excluded.append(row['eventId'])
        else:
            eligible.append(row)
            targets.append(target)
    if len(eligible) < 7 or len({r['symbol'] for r in eligible}) < 2:
        raise FitError('FIT_FAILED_MINIMUM_SUPPORT')
    weights = symbol_weights(eligible)
    ids = [r['eventId'] for r in eligible]
    raw = [r['raw'] for r in eligible]
    medians = [weighted_median([r[j] for r in raw],weights,ids) for j in (1,2)]
    for j in range(3):
        if sum(r[j] is not None for r in raw) < 2:
            raise FitError('FIT_FAILED_OBSERVED_SUPPORT')
    imputed = np.asarray([[r[0],r[1] if r[1] is not None else medians[0],
                           r[2] if r[2] is not None else medians[1]] for r in raw],dtype=np.float64)
    means = np.sum(weights[:,None]*imputed,axis=0)
    stds = np.sqrt(np.sum(weights[:,None]*(imputed-means)**2,axis=0))
    if not np.all(np.isfinite(stds)) or np.any(stds <= 0):
        raise FitError('FIT_FAILED_RAW_VARIANCE')
    masks = np.asarray([r['missing'] for r in eligible],dtype=np.float64)
    features = np.column_stack(((imputed-means)/stds,masks))
    X = np.column_stack((np.ones(len(eligible)),features))
    y = np.asarray(targets,dtype=np.float64)
    A = X.T@(weights[:,None]*X)+np.diag([0.,1.,1.,1.,1.,1.])
    rhs = X.T@(weights*y)
    try:
        theta = np.linalg.solve(A,rhs)
    except np.linalg.LinAlgError as exc:
        raise FitError('FIT_FAILED_SOLVER') from exc
    residual = float(np.max(np.abs(A@theta-rhs)))
    objective = float(.5*np.sum(weights*(y-X@theta)**2)+.5*np.sum(theta[1:]**2))
    if not np.all(np.isfinite(theta)) or not math.isfinite(objective) or residual > 1e-10*(1+float(np.max(np.abs(rhs)))):
        raise FitError('FIT_FAILED_NUMERICAL_CHECK')
    artifact = {'schemaVersion':1,'modelId':MODEL_ID,'contractSHA':CONTRACT_SHA,
        'featureOrder':FEATURE_ORDER,'lambda':1.,'intercept':float(theta[0]),'coefficients':theta[1:].tolist(),
        'medians':medians,'means':means.tolist(),'stds':stds.tolist(),
        'missingSeen':[bool(np.any(masks[:,j] == 1)) for j in range(2)],
        'runtime':{'python':'.'.join(map(str,sys.version_info[:3])),'numpy':np.__version__,'threads':1,'dtype':'float64'},
        'training':{'candidateRows':len(ordered),'eligibleRows':len(eligible),'excludedLabelRows':len(excluded),
            'eligibleIds':ids,'excludedIds':excluded,'symbols':sorted({r['symbol'] for r in eligible}),
            'sessions':sorted({r['sessionDate'] for r in eligible}),
            'weightsSHA':digest(list(zip(ids,weights.tolist()))),'weightSum':float(np.sum(weights)),
            'missingCounts':[int(np.sum(masks[:,j])) for j in range(2)],
            'observedCounts':[sum(r[j] is not None for r in raw) for j in range(3)],
            'objective':objective,'normalEquationResidualInf':residual},
        'readout':'max(0,rawLinear)','scoreUse':'ADVERSE_MAGNITUDE_ONLY_NO_SIZING'}
    artifact['artifactSHA'] = digest(artifact)
    validate_artifact(artifact)
    return artifact


def validate_artifact(artifact):
    a = dict(artifact)
    expected = a.pop('artifactSHA')
    if digest(a) != expected:
        raise IntegrityError('MODEL_HASH_MISMATCH')
    if (a['contractSHA'] != CONTRACT_SHA or a['modelId'] != MODEL_ID or a['featureOrder'] != FEATURE_ORDER
        or a['lambda'] != 1. or len(a['coefficients']) != 5):
        raise IntegrityError('MODEL_CONTRACT_MISMATCH')
    for key,n in [('medians',2),('means',3),('stds',3),('coefficients',5)]:
        if len(a[key]) != n or any(not finite(v) for v in a[key]):
            raise IntegrityError('MODEL_PARAMETERS_INVALID')
    if any(v <= 0 for v in a['stds']) or not finite(a['intercept']):
        raise IntegrityError('MODEL_SCALE_INVALID')


def save_artifact(path, artifact):
    validate_artifact(artifact)
    with Path(path).open('xb') as handle:
        handle.write(canonical(artifact)+b'\n')


def load_artifact(path):
    a = json.loads(Path(path).read_text())
    validate_artifact(a)
    return a


def predict(artifact, rows):
    validate_artifact(artifact)
    output = []
    for row in sorted(rows,key=sort_key):
        validate_envelope(row)
        base = {k:row[k] for k in ['eventId','symbol','sessionDate','decisionTimestamp']}
        reason = row['invalidReason'] if not row['valid'] else None
        if any(bit and not seen for bit,seen in zip(row['missing'],artifact['missingSeen'])):
            reason = 'UNSUPPORTED_MISSING_STATE'
        if reason:
            output.append(base|{'status':reason,'rawPrediction':None,'predictedD30':None})
            continue
        r = row['raw']
        imputed = [r[0],r[1] if r[1] is not None else artifact['medians'][0],r[2] if r[2] is not None else artifact['medians'][1]]
        values = [(v-m)/s for v,m,s in zip(imputed,artifact['means'],artifact['stds'])]+row['missing']
        raw = float(artifact['intercept']+np.asarray(values,dtype=np.float64)@np.asarray(artifact['coefficients'],dtype=np.float64))
        if not math.isfinite(raw):
            raise IntegrityError('NONFINITE_PREDICTION')
        output.append(base|{'status':'SCORED','rawPrediction':raw,'predictedD30':max(0.,raw)})
    return output


def decide(predictions, threshold):
    if not finite(threshold) or threshold not in THRESHOLDS:
        raise IntegrityError('THRESHOLD_NOT_FROZEN')
    entered = set()
    output = []
    seen_ids = set()
    for p in sorted(predictions,key=sort_key):
        if p['eventId'] in seen_ids:
            raise IntegrityError('DUPLICATE_DECISION')
        seen_ids.add(p['eventId'])
        key = p['symbol'],p['sessionDate']
        state,reason = 'SKIP_THIS_DECISION',p['status']
        if key in entered:
            reason = 'SYMBOL_SESSION_ALREADY_ENTERED'
        elif p['status'] == 'SCORED':
            if not finite(p['predictedD30']) or p['predictedD30'] < 0:
                raise IntegrityError('INVALID_D30_SCORE')
            if p['predictedD30'] <= threshold:
                state,reason = 'ENTER','PREDICTED_D30_WITHIN_THRESHOLD'
                entered.add(key)
            else:
                reason = 'PREDICTED_D30_ABOVE_THRESHOLD'
        output.append(p|{'threshold':threshold,'state':state,'reason':reason})
    return output
