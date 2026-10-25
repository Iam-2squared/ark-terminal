#!/usr/bin/env python3
"""Development-only causal coverage audit. No model fit or performance reads.

R6 repairs structural session/T0 accounting; feature and trading policies are
unchanged. Missing T0 checkpoints are retained in the full cohort denominator.
"""
from __future__ import annotations
import argparse
import collections
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PATTERN = ROOT / 'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate'
TIMING = ROOT / 'docs/evidence/phase57-entry-timing-signal-census-v1/measurement'
STATE = ROOT / 'docs/evidence/phase57-state-v3-9pattern-entry-v1/measurement'
SAFETY = dict.fromkeys(('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed',
    'rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed',
    'automaticPromotionAllowed','productionUpdateAllowed','transmitted'), False)
SIGNAL_FAMILIES = ('CONTINUATION','BREAKOUT','COMPRESSION_EXPANSION','HIGHER_LOW','LOWER_WICK','RECLAIM')
STATE_LABELS = ('RISE_STOP','RISE','SHARP_RISE','PULLBACK','RANGE','REBOUND','SHARP_DROP','DROP','DROP_STOP')
HORIZONS = (0,5,10,20,30)


def read_json(path):
    with (gzip.open if path.suffix == '.gz' else open)(path,'rt',encoding='utf-8') as f:
        return json.load(f)


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def active_ordinal(minute):
    if 540 <= minute <= 690:
        return minute - 540
    if 750 <= minute <= 930:
        return 150 + minute - 750
    raise ValueError(f'OUTSIDE_ACTIVE_SESSION:{minute}')


def active_elapsed(start,end):
    return active_ordinal(end)-active_ordinal(start)


def pct(n,d):
    return 100.0*n/d if d else None


def summary(values):
    xs = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return dict(n=len(xs), min=min(xs) if xs else None,
        median=statistics.median(xs) if xs else None,
        mean=statistics.fmean(xs) if xs else None, max=max(xs) if xs else None)


def load_matrix(path):
    with gzip.open(path,'rb') as f:
        return np.load(f,allow_pickle=False)


def checkpoint_geometry(ids,rows):
    """Keep even an opportunity with zero rows; never synthesize a checkpoint."""
    ds = {oid:set() for oid in ids}
    keys = set()
    for r in rows:
        oid = r['opportunity']
        assert oid in ds, 'FOREIGN_OPPORTUNITY'
        delay = int(r['delay'])
        assert 0 <= delay <= 30, 'OUT_OF_WINDOW'
        key = (oid,delay)
        assert key not in keys, 'DUPLICATE_CHECKPOINT'
        keys.add(key)
        ds[oid].add(delay)
    first = collections.Counter(min(v) for v in ds.values() if v)
    return {
        'population':len(ds),
        'opportunitiesWithCausalCheckpoint':sum(bool(v) for v in ds.values()),
        'noCausalCheckpoint':sum(not v for v in ds.values()),
        't0Rows':sum(0 in v for v in ds.values()),
        'noCausalT0Checkpoint':sum(0 not in v for v in ds.values()),
        'firstAvailableDelayCounts':{str(k):v for k,v in sorted(first.items())},
        'horizonAvailability':{str(h):sum(h in v for v in ds.values()) for h in HORIZONS},
        'opportunityDecisionRows':summary(map(len,ds.values())),
    }


def column_coverage(available,t0_available,decision_n,t0_n,population):
    assert 0 <= t0_available <= t0_n <= population
    return {'available':int(available),'missing':int(decision_n-available),
        'coveragePct':pct(int(available),decision_n),'t0Available':int(t0_available),
        't0Denominator':population,'t0Missing':int(population-t0_available),
        't0CoveragePct':pct(int(t0_available),population),
        'existingT0Denominator':t0_n,'existingT0Missing':int(t0_n-t0_available),
        'existingT0CoveragePct':pct(int(t0_available),t0_n),
        'missingSemantics':'RAW_NAN_PRESERVED__NO_FUTURE_FILL__TRAIN_FOLD_ONLY_IMPUTATION_IF_MODEL_ADMITTED'}


def cohort_ids():
    cohort=read_json(TIMING/'opportunity-records.json.gz')
    ids={r['opportunity'] for r in cohort}
    sessions={r['session'] for r in cohort}
    assert len(cohort)==len(ids)==2155
    assert len(sessions)==58, 'OPPORTUNITY_BEARING_SESSIONS_MUST_BE_58'
    return cohort,ids,sessions


def build_pattern_coverage(ids,sessions):
    p0=read_json(PATTERN/'p0-audit.json')
    assert p0['status']=='PASS'
    assert all(p0[k] is True for k in ('all144','previousCausal','todayPrefixCausal','featureNoWHO'))
    assert p0['holdoutOpened']==0 and all(v is False for v in p0['safety'].values())
    names=read_json(PATTERN/'names.json')
    assert len(names)==len(set(names))==476
    opps=[r for r in read_json(PATTERN/'opportunities.json.gz') if r['session'] in sessions]
    assert len(opps)==len(ids) and {r['id'] for r in opps}==ids
    by_day=collections.defaultdict(list)
    for r in read_json(PATTERN/'rows.json.gz'):
        if r['session'] in sessions:
            by_day[r['session']].append(r)
    decision_rows=[]
    finite_counts=np.zeros(len(names),dtype=np.int64)
    t0_counts=np.zeros(len(names),dtype=np.int64)
    row_meta=collections.Counter()
    matrix_hashes={}
    for day in sorted(sessions):
        rr=by_day[day]
        path=PATTERN/f'{day}.npy.gz'
        a=load_matrix(path)
        matrix_hashes[day]=sha256(path)
        assert a.shape==(len(rr),len(names)), (day,a.shape,len(rr))
        for i,r in enumerate(rr):
            assert r['opportunity'] in ids
            if not r.get('eligible1') or int(r['delay'])>30:
                continue
            assert int(r['delay'])>=0
            finite=np.isfinite(a[i])
            finite_counts+=finite
            if int(r['delay'])==0:
                t0_counts+=finite
            for k in ('quoteAvailable','previousCoverage','todayCoverage'):
                row_meta[f'{k}={r.get(k)}']+=1
            decision_rows.append(dict(opportunity=r['opportunity'],session=r['session'],
                minute=int(r['minute']),delay=int(r['delay'])))
    g=checkpoint_geometry(ids,decision_rows)
    assert g['opportunitiesWithCausalCheckpoint']==2155 and g['noCausalCheckpoint']==0
    assert len(decision_rows)==65312
    assert g['t0Rows']==1954 and g['noCausalT0Checkpoint']==201
    assert g['firstAvailableDelayCounts']=={'0':1954,'1':201}
    assert g['horizonAvailability']=={'0':1954,'5':2155,'10':2155,'20':2155,'30':1758}
    cols={n:column_coverage(int(finite_counts[i]),int(t0_counts[i]),len(decision_rows),g['t0Rows'],len(ids)) for i,n in enumerate(names)}
    groups=collections.defaultdict(list)
    for n,c in cols.items():
        groups[n.split('/',1)[0]].append(c)
    gs={}
    for group,cc in sorted(groups.items()):
        cov=[c['coveragePct'] for c in cc]
        gs[group]={'columns':len(cc), 'coveragePct':summary(cov),
            't0CoveragePct':summary(c['t0CoveragePct'] for c in cc),
            'existingT0CoveragePct':summary(c['existingT0CoveragePct'] for c in cc),
            'fullCoverageColumns':sum(c==100 for c in cov),
            'ge95CoverageColumns':sum(c>=95 for c in cov),
            'ge80CoverageColumns':sum(c>=80 for c in cov)}
    return {'source':'phase57-entry-pattern-v2/ci-result/substrate',
        'p0Audit':{k:p0[k] for k in ('status','all144','previousCausal','todayPrefixCausal','featureNoWHO','holdoutOpened')},
        **g,'sessions':len(sessions),'decisionRows':len(decision_rows),'featureColumns':len(names),
        'structuralMissingReasons':{'NO_CAUSAL_T0_CHECKPOINT':g['noCausalT0Checkpoint']},
        'rowAvailability':dict(sorted(row_meta.items())),'columns':cols,'groups':gs,
        'decisionRowsKey':decision_rows,
        'sourceHashes':{**{n:sha256(PATTERN/p) for n,p in (
            ('manifest','manifest.json'),('names','names.json'),('rows','rows.json.gz'),
            ('opportunities','opportunities.json.gz'),('p0Audit','p0-audit.json'))},
            'matrices':matrix_hashes}}


def build_signal_coverage(ids,sessions,decision_rows):
    by_key={}
    hashes=[]
    for day in sorted(sessions):
        p=TIMING/'minute-census'/f'{day}.json.gz'
        hashes.append((day,sha256(p)))
        for r in read_json(p):
            assert r['opportunity'] in ids
            k=(r['opportunity'],int(r['minute']))
            assert k not in by_key
            by_key[k]=r
    exact=closed=pivot_bad=0
    fam={n:collections.Counter(available=0,true=0,false=0,unknown=0) for n in SIGNAL_FAMILIES}
    for b in decision_rows:
        r=by_key.get((b['opportunity'],b['minute']))
        if r is None:
            continue
        exact+=1
        through=r.get('computedThroughBarStart')
        closed+=through is not None and int(through)>=b['minute']
        for n in SIGNAL_FAMILIES:
            sig=r['signals'][n]; t=sig.get('trigger')
            assert t is None or type(t) is bool
            fam[n]['available']+=t is not None
            fam[n]['true']+=t is True
            fam[n]['false']+=t is False
            fam[n]['unknown']+=t is None
            p=sig.get('pivot')
            if p and not (p['lowBarStart']<p['confirmedAt']<=b['minute']):
                pivot_bad+=1
    assert closed==pivot_bad==0
    assert exact==len(decision_rows)
    return {'source':'phase57-entry-timing-signal-census-v1/measurement/minute-census',
        'sourceRows':len(by_key),'decisionRows':len(decision_rows),'exactJoinRows':exact,
        'exactJoinCoveragePct':pct(exact,len(decision_rows)),
        'closedBarViolations':closed,'futurePivotViolations':pivot_bad,
        'families':{n:{**dict(c),'coveragePct':pct(c['available'],exact),
            'missingSemantics':'TRISTATE_UNKNOWN_PRESERVED__NO_FUTURE_INFERENCE'} for n,c in fam.items()},
        'sourceHashes':{'manifest':sha256(TIMING/'manifest.json'),'cohort':sha256(TIMING/'cohort.json'),
            'minuteCensusAggregate':hashlib.sha256('\n'.join(f'{d}:{h}' for d,h in hashes).encode()).hexdigest()}}


def build_state_coverage(ids,decision_rows):
    rows=read_json(STATE/'state-checkpoints.json.gz')
    by_opp=collections.defaultdict(list)
    for r in rows:
        assert r['opportunity'] in ids
        by_opp[r['opportunity']].append((int(r.get('asOf',r.get('minute'))),r))
    assert set(by_opp)==ids
    for checks in by_opp.values():
        checks.sort(key=lambda x:x[0])
    exact=asof=valid=invalid=future=prior=0
    stale=[]; counts=collections.Counter()
    for b in decision_rows:
        hist=[(m,r) for m,r in by_opp[b['opportunity']] if m<=b['minute']]
        if not hist:
            continue
        m,r=hist[-1]; asof+=1; exact+=m==b['minute']; prior+=len(hist)>1
        stale.append(active_elapsed(m,b['minute']))
        source=r.get('maxSourceBarStart')
        future+=source is not None and int(source)>=m
        if r.get('state') in STATE_LABELS and r.get('dataQuality')!='INVALID':
            valid+=1; counts[r['state']]+=1
        else:
            invalid+=1
    assert future==0 and asof==len(decision_rows)
    return {'source':'phase57-state-v3-9pattern-entry-v1/measurement/state-checkpoints.json.gz',
        'sourceRows':len(rows),'decisionRows':len(decision_rows),
        'exactCheckpointRows':exact,'exactCheckpointCoveragePct':pct(exact,len(decision_rows)),
        'asOfJoinRows':asof,'asOfJoinCoveragePct':pct(asof,len(decision_rows)),
        'validStateRows':valid,'validStateCoveragePct':pct(valid,len(decision_rows)),
        'invalidStateRows':invalid,'asOfStalenessActiveMinutes':summary(stale),
        'stateCounts':dict(sorted(counts.items())),
        'derivedCausalCoverage':{'currentStateAsOf':asof,'priorCheckpoint':prior,'observedHistoryAvailable':asof},
        'futureBarViolations':future,
        'missingSemantics':'LAST_KNOWN_FROZEN_STATE_CHECKPOINT_ONLY__NEVER_FUTURE_STATE',
        'sourceHashes':{'manifest':sha256(STATE/'manifest.json'),
            'stateCheckpoints':sha256(STATE/'state-checkpoints.json.gz'),
            'causalityAudit':sha256(STATE/'causality-audit.json')}}


def run():
    cohort,ids,sessions=cohort_ids()
    pattern=build_pattern_coverage(ids,sessions)
    keys=pattern.pop('decisionRowsKey')
    sig=build_signal_coverage(ids,sessions,keys)
    state=build_state_coverage(ids,keys)
    ids_hash=hashlib.sha256(json.dumps(sorted(ids),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    pinned=read_json(TIMING/'cohort.json')['opportunityIdsSHA256']
    assert ids_hash==pinned
    integrity={'patternPopulationExact2155':pattern['population']==2155,
        'opportunityBearingSessionsExact58':len(sessions)==58,
        'allOpportunitiesHaveCausalCheckpoint':pattern['opportunitiesWithCausalCheckpoint']==2155,
        't0RowsExact1954':pattern['t0Rows']==1954,
        'noCausalT0Exact201':pattern['noCausalT0Checkpoint']==201,
        'signalExactJoinComplete':sig['exactJoinRows']==pattern['decisionRows'],
        'stateAsOfJoinComplete':state['asOfJoinRows']==pattern['decisionRows'],
        'futureBarViolations':sig['closedBarViolations']+sig['futurePivotViolations']+state['futureBarViolations'],
        'performanceMetricsRead':0,'modelFits':0,'modelPredictions':0,'providerRequests':0,'protectedDataOpened':0}
    assert all(v is True for k,v in integrity.items() if type(v) is bool)
    assert integrity['futureBarViolations']==0
    blocked={k:{'availableInAuditedSources':False,'automaticAdmission':False} for k in
        ('marketContext','sectorContext','liquidityTradabilityTick','pointInTimeSymbolProfile','dictionaryDescriptors')}
    return {'id':'PHASE57_ALL_MATERIAL_COHORT_NATIVE_FEATURE_COVERAGE_V1','accountingRevision':'R6_STRUCTURAL_T0',
        'scope':'Development-only causal coverage/missingness audit; zero performance metrics read',
        'cohort':{'population':len(cohort),'sessions':len(sessions),'firstSession':min(sessions),
            'lastSession':max(sessions),'opportunityIdsSHA256':ids_hash,'timingCensusPinnedOpportunityIdsSHA256':pinned},
        'patternSubstrate':pattern,'sixSignals':sig,'stateV3':state,'integrity':integrity,
        'conditionalFamilyDispositionInputs':{'volumeTurnover':{'sourceProof':'PATTERN_P0_PREFIX_CAUSAL',
            'columns':[n for n in pattern['columns'] if any(t in n.lower() for t in ('volume','/value','/va','/vo'))],
            'automaticAdmission':False},**blocked},
        'missingPolicy':{'decisionTime':'missing remains missing','futureBackfill':False,
            'interpolationFromFuture':False,'modelPreprocessing':'fit imputer/scaler on train fold only; missing indicators allowed'},
        'inheritedCausalityLimitations':read_json(TIMING/'cohort.json').get('causalityLimitations',[]),
        'safety':SAFETY}


def self_test():
    assert active_elapsed(689,690)==1
    assert active_elapsed(690,750)==0
    assert active_elapsed(750,755)==5
    assert pct(1,4)==25 and pct(0,0) is None
    g=checkpoint_geometry({'a','b','c'},[
        {'opportunity':'a','delay':0},{'opportunity':'a','delay':30},{'opportunity':'b','delay':1}])
    assert g['population']==3 and g['noCausalCheckpoint']==1
    assert g['t0Rows']==1 and g['noCausalT0Checkpoint']==2
    assert g['firstAvailableDelayCounts']=={'0':1,'1':1}
    assert g['horizonAvailability']=={'0':1,'5':0,'10':0,'20':0,'30':1}
    c=column_coverage(2,1,3,1,3)
    assert c['t0Missing']==2 and c['existingT0Missing']==0
    assert c['t0CoveragePct']==100/3 and c['existingT0CoveragePct']==100
    try:
        checkpoint_geometry({'a'},[{'opportunity':'a','delay':0}]*2)
        raise RuntimeError('duplicate checkpoint accepted')
    except AssertionError as e:
        assert str(e)=='DUPLICATE_CHECKPOINT'
    assert all(v is False for v in SAFETY.values())
    print(json.dumps({'status':'PASS','checks':12,'syntheticOnly':True},sort_keys=True))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output'); ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args()
    if args.self_test:
        self_test(); return
    if not args.output:
        raise SystemExit('--output required')
    result=run(); out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','population':result['cohort']['population'],
        'decisionRows':result['patternSubstrate']['decisionRows'],'features':result['patternSubstrate']['featureColumns'],
        't0Rows':result['patternSubstrate']['t0Rows'],'noCausalT0':result['patternSubstrate']['noCausalT0Checkpoint'],
        'performanceMetricsRead':0,'modelFits':0},sort_keys=True))

if __name__=='__main__':
    main()
