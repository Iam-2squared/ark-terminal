"""Bounded no-fit descriptive audit of eight predeclared Entry-time fields.
No network, model training, probability prediction, entry decision or portfolio replay.
"""
from __future__ import annotations
import collections, gzip, hashlib, json, math, os, platform, sys
from pathlib import Path
import numpy as np

BASE = Path(os.environ.get('ARK_ENTRY_INFO_WORKDIR', str(Path(__file__).resolve().parent))).resolve()
SOURCE = BASE / 'source_export'
PROTO_SHA = '6b5c96d578dde9dee5dfbfa80b8e1ff83c7920b2ae6a890dff0ca5d9d30ce2f7'

def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p: Path):
    raw = p.read_bytes()
    if p.suffix == '.gz': raw = gzip.decompress(raw)
    return [json.loads(v) for v in raw.decode().splitlines()] if '.ndjson.' in p.name else json.loads(raw)

def finite(x): return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)

def weights(rows):
    """Equal symbol; equal session within symbol; equal observed event within symbol-session."""
    days = collections.defaultdict(set)
    counts = collections.Counter((r['symbol'], r['sessionDate']) for r in rows)
    for r in rows: days[r['symbol']].add(r['sessionDate'])
    return np.array([1/(len(days)*len(days[r['symbol']])*counts[(r['symbol'],r['sessionDate'])]) for r in rows])

def auc(x, y, w=None):
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=int)
    if not len(x) or set(y.tolist()) != {0,1} or not np.all(np.isfinite(x)): return None
    w = np.ones(len(x),dtype=float) if w is None else np.asarray(w,dtype=float)
    if np.any(w<0) or not np.all(np.isfinite(w)): raise ValueError('WEIGHTS')
    order=np.argsort(x,kind='stable'); x,y,w=x[order],y[order],w[order]
    wp=float(w[y==1].sum()); wn=float(w[y==0].sum())
    if min(wp,wn)<=0:return None
    concordant=0.; negatives=0.;i=0
    while i<len(x):
        j=i+1
        while j<len(x) and x[j]==x[i]:j+=1
        p=float(w[i:j][y[i:j]==1].sum()); n=float(w[i:j][y[i:j]==0].sum())
        concordant += p*(negatives+.5*n); negatives+=n;i=j
    return concordant/(wp*wn)

def ranks(x):
    x=np.asarray(x,dtype=float); out=np.empty(len(x),dtype=float); order=np.argsort(x,kind='stable'); i=0
    while i<len(x):
        j=i+1
        while j<len(x) and x[order[j]]==x[order[i]]:j+=1
        out[order[i:j]]=(i+j-1)/2.; i=j
    return out

def spearman(x,y):
    if len(x)<3:return None
    a=ranks(x);b=ranks(y);a-=a.mean();b-=b.mean();den=float(np.linalg.norm(a)*np.linalg.norm(b))
    return float(a@b/den) if den>0 else None

def dist(x):
    x=[float(v) for v in x if finite(v)]
    return {'n':len(x),'median':float(np.median(x)) if x else None,'mean':float(np.mean(x)) if x else None,
            'min':min(x) if x else None,'max':max(x) if x else None}

def label(row,name):
    if name=='netPositive':return int(row['net']>0) if finite(row['net']) else None
    if name=='tailD30ge5':return int(row['D30']>=5) if finite(row['D30']) else None
    if name in ('mfeGe3','mfeGe5'):
        return int(row['MFE']>=int(name[-1])) if finite(row['MFE']) else None
    raise ValueError(name)

def association(rows,f,lab='netPositive'):
    observed=[r for r in rows if finite(r['values'][f]) and label(r,lab) is not None]
    x=[r['values'][f] for r in observed]; y=[label(r,lab) for r in observed]
    positive=[a for a,b in zip(x,y) if b]; negative=[a for a,b in zip(x,y) if not b]
    return {'populationN':len(rows),'featureAvailableN':sum(finite(r['values'][f]) for r in rows),
      'outcomeAvailableN':sum(label(r,lab) is not None for r in rows), 'jointN':len(observed),
      'positiveN':len(positive),'negativeN':len(negative),'symbols':len({r['symbol'] for r in observed}),
      'sessions':len({r['sessionDate'] for r in observed}), 'uniqueFeatureValues':len(set(x)),
      'aucHigherFeatureIsPositive':auc(x,y),
      'symbolSessionBalancedAUC':auc(x,y,weights(observed)) if observed else None,
      'positiveFeature':dist(positive),'negativeFeature':dist(negative)}

def group_id(s):return int.from_bytes(hashlib.sha256(('PHASE57_MSH_LONG_V2_GROUP_V1|'+s).encode()).digest(),'big')%5

def analyze(rows,features,cv):
    result={}
    contributions=collections.defaultdict(float)
    for r in rows:
        if finite(r['net']):contributions[r['symbol']]+=r['net']
    positive=max(contributions,key=contributions.get);negative=min(contributions,key=contributions.get)
    removed={positive,negative}; sensitivity=[r for r in rows if r['symbol'] not in removed]
    last15=set(cv[-1]['evaluationDates'])
    for f in features:
        a=association(rows,f); direction=1 if a['aucHigherFeatureIsPositive'] is not None and a['aucHigherFeatureIsPositive']>.5 else -1
        chrono={c['name']:association([r for r in rows if r['sessionDate'] in c['evaluationDates']],f) for c in cv}
        groups={str(g):association([r for r in rows if group_id(r['symbol'])==g],f) for g in range(5)}
        finalgroups={str(g):association([r for r in rows if group_id(r['symbol'])==g and r['sessionDate'] in last15],f) for g in range(5)}
        within=[]
        for s in sorted({r['symbol'] for r in rows}):
            q=association([r for r in rows if r['symbol']==s],f)
            if q['aucHigherFeatureIsPositive'] is not None:within.append(q['aucHigherFeatureIsPositive'])
        netpairs=[r for r in rows if finite(r['values'][f]) and finite(r['net'])]
        riskpairs=[r for r in rows if finite(r['values'][f]) and finite(r['D30'])]
        agree=lambda x:sum(v['aucHigherFeatureIsPositive'] is not None and direction*(v['aucHigherFeatureIsPositive']-.5)>0 for v in x.values())
        sa=association(sensitivity,f)
        sensitivity_ok=sa['aucHigherFeatureIsPositive'] is not None and direction*(sa['aucHigherFeatureIsPositive']-.5)>0
        p=a['aucHigherFeatureIsPositive']
        heuristic=(p is not None and (p>=.6 or p<=.4) and agree(chrono)>=3 and agree(groups)>=3 and sensitivity_ok)
        result[f]={'primary':a,'chronological':chrono,'symbolGroupsAll76':groups,'symbolGroupsLast15':finalgroups,
          'directionForDescriptiveConcordanceOnly':direction,'chronoConcordant':agree(chrono),'symbolConcordantAll76':agree(groups),
          'symbolConcordantLast15':agree(finalgroups),'removeLargestPositiveAndNegativeContributors':{'symbols':sorted(removed),'metric':'SUM_FIXED_EXIT_REFERENCE_RETURN_NOT_CASH_PNL','association':sa},
          'withinSymbolAUC':{'symbolsWithBothClasses':len(within),'median':float(np.median(within)) if within else None,'mean':float(np.mean(within)) if within else None},
          'spearmanNet':spearman([r['values'][f] for r in netpairs],[r['net'] for r in netpairs]),
          'spearmanD30':spearman([r['values'][f] for r in riskpairs],[r['D30'] for r in riskpairs]),
          'supporting':{lab:association(rows,f,lab) for lab in ['tailD30ge5','mfeGe3','mfeGe5']},
          'missingReasons':dict(collections.Counter(r['reasons'].get(f,'UNKNOWN_MISSING') for r in rows if not finite(r['values'][f]))),
          'advanceHeuristic':bool(heuristic)}
    return result

def test():
    n=0
    def check(cond):
        nonlocal n
        if not cond:raise AssertionError(n+1)
        n+=1
    check(auc([0,1],[0,1])==1);check(auc([0,1],[1,0])==0);check(auc([1,1],[0,1])==.5)
    check(auc([1,2],[1,1]) is None);check(auc([],[]) is None)
    x=[1,3,3,4,5];y=[0,1,0,1,0];w=[1,2,3,2,4]
    brute=sum(w[i]*w[j]*((x[i]>x[j])+.5*(x[i]==x[j])) for i in range(5) for j in range(5) if y[i] and not y[j])/sum(w[i]*w[j] for i in range(5) for j in range(5) if y[i] and not y[j])
    check(abs(auc(x,y,w)-brute)<1e-14);check(spearman([1,2,3],[1,2,3])>.999999)
    check(spearman([1,2,3],[3,2,1])<-.999999);check(spearman([1,1,1],[3,2,1]) is None)
    rs=[{'symbol':'A','sessionDate':'a'},{'symbol':'A','sessionDate':'a'},{'symbol':'B','sessionDate':'a'}]
    check(np.allclose(weights(rs),[.25,.25,.5]));check(group_id('89180')==group_id('89180'))
    check(not finite(None));check(not finite(float('nan')));check(not finite(True))
    return {'statisticalUnitTests':n,'passed':n}

def main(feature_file):
    tests=test();assert digest(BASE/'protocol.json')==PROTO_SHA
    manifest=read(SOURCE/'export-manifest.json')
    for name, v in manifest['sourceFiles'].items():assert digest(SOURCE/name)==v['sha256'],name
    protocol=read(BASE/'protocol.json');features=[x['name'] for x in protocol['featurePanel']]
    feature_rows=read(feature_file);audit=read(feature_file.parent/'export-audit.json')
    assert digest(feature_file)==audit['featureSHA'];assert len(audit['sourceAudit'])==76
    envelopes=read(SOURCE/'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz')
    pred=read(SOURCE/'docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/frozen-predictions.ndjson.gz')
    targets=read(SOURCE/'docs/evidence/phase57-entry-v2-2-fast-fail/target-ledger.json.gz')
    legacy=read(SOURCE/'docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/path-diagnostics.json.gz')
    v23=read(SOURCE/'predict/research/phase57-entry-v2-3-fast-fail-protocol-v1.json')
    env={r['selectorEventId']:r for r in envelopes};pm={r['selectorEventId']:r for r in pred}
    tm={r['eventId']:r for r in targets};lm={r['selectorEventId']:r for r in legacy['events']}
    assert len(feature_rows)==3800 and len({r['eventId'] for r in feature_rows})==3800
    assert {r['eventId'] for r in feature_rows}==set(env)==set(pm)==set(tm)==set(lm)
    rows=[]
    for f in feature_rows:
        eid=f['eventId'];e=env[eid];l=lm[eid];t=tm[eid]
        assert f['sessionDate']==e['sessionDate'] and f['symbol']==e['symbol']
        assert set(f['values'])==set(features)
        assert all(v is None or finite(v) for v in f['values'].values())
        anchor=pm[eid]['state']=='ENTER'; assert anchor==t['v1Anchor']
        d=max(0,-l['trueMaePct']) if l['labelable'] else None
        row={**f,'net':t['target'],'D30':d,'MFE':l['mfePct'] if l['labelable'] else None,'v1Anchor':anchor,'ridgeScore':e['ridgeScore'],'v1Score':pm[eid]['expectedClass']}
        rows.append(row)
    anchors=[r for r in rows if r['v1Anchor']]
    assert len(anchors)==277 and sum(finite(r['D30']) for r in anchors)==181
    dates=sorted({r['sessionDate'] for r in rows});assert len(dates)==76
    all_results=analyze(rows,features,v23['cv']['chronological']);anchor_results=analyze(anchors,features,v23['cv']['chronological'])
    full_candidates=[f for f in features if all_results[f]['advanceHeuristic']]
    nominated=[f for f in features if anchor_results[f]['advanceHeuristic'] and 'ALREADY_SCREENED' not in next(x['novelty'] for x in protocol['featurePanel'] if x['name']==f)]
    joint_counts={p:{'rows':len(rs),'symbols':len({r['symbol'] for r in rs}),'exitKnown':sum(finite(r['net']) for r in rs),'exitPositive':sum(finite(r['net']) and r['net']>0 for r in rs),'D30Known':sum(finite(r['D30']) for r in rs),'MFE3':sum(finite(r['MFE']) and r['MFE']>=3 for r in rs),'MFE5':sum(finite(r['MFE']) and r['MFE']>=5 for r in rs)} for p,rs in [('allCandidates',rows),('v1Anchors',anchors)]}
    result={'id':protocol['id'],'protocolSHA':PROTO_SHA,'sourceHead':protocol['sourceHead'],'featureExportSHA':audit['featureSHA'],
      'populations':joint_counts,'primaryV1Anchors':anchor_results,'supportingAllCandidates':all_results,
      'nominatedNewFeaturesForFurtherResearchOnly':nominated,'allCandidateHeuristicFeatures':full_candidates,
      'verdict':'FAST_FAIL_CONTINUE_FOR_PRECOMMITTED_MODEL_TEST_ONLY' if nominated else 'FAST_FAIL_NO_NEW_FEATURE_NOMINATED',
      'novelty':protocol['featurePanel'],'modelFits':0,'modelPredictions':0,'thresholdSweeps':0,'portfolioReplays':0,
      'providerRequests':0,'freshAccess':0,'oosAccess':0,'safety':protocol['safety'],'tests':tests,
      'runtime':{'python':platform.python_version(),'numpy':np.__version__},'limitations':protocol['limitations']}
    out=BASE/'result.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(joint_counts,ensure_ascii=False))
    print('FEATURE | avail277 | primaryN | AUC | balanced | chrono concordant | symbol concordant | sensitivity | nominated')
    for f,r in anchor_results.items():
        print(f,r['primary']['featureAvailableN'],r['primary']['jointN'],r['primary']['aucHigherFeatureIsPositive'],r['primary']['symbolSessionBalancedAUC'],r['chronoConcordant'],r['symbolConcordantAll76'],r['removeLargestPositiveAndNegativeContributors']['association']['aucHigherFeatureIsPositive'],f in nominated)
    print('VERDICT',result['verdict'],'nominated',nominated,'SHA',digest(out),'TESTS',tests)

if __name__=='__main__':
    if sys.argv[1:] == ['--self-test']:print(json.dumps(test()))
    else:main(Path(sys.argv[1]))
