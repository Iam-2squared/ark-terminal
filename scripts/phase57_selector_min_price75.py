"""Development impact only. Uses exact parent evaluator, no fitting or tuning."""
from __future__ import annotations
import argparse, collections, gzip, hashlib, importlib.util, json, math, sys
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run_phase57_long_only_corrected_measurement as base
import run_phase57_long_only_eligibility_measurement as parent
import run_phase57_long_only_top5_hit_distribution as hits
POLICY=ROOT/'predict/research/phase57-long-only-min-price-75-policy-v1.json'
IMPL=ROOT/'predict/long-only/phase57_long_selector_min_price75.py'
spec=importlib.util.spec_from_file_location('p75',IMPL);gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
LEVELS=(1,2,3,5)
PROTOCOL_COMMIT='dd93029c7e1b68ba8f0d030740c055ea81ef0fc1'

def encoded(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    p=Path(p);b=p.read_bytes()
    if p.suffix=='.gz':b=gzip.decompress(b)
    return [json.loads(x) for x in b.splitlines()] if '.ndjson' in p.name else json.loads(b)
def write(p,x):
    b=encoded(x);p=Path(p)
    if p.suffix=='.gz':b=gzip.compress(b,mtime=0)
    with p.open('xb') as f:f.write(b)
def verify():
    p=read(POLICY);core={k:v for k,v in p.items() if k!='policyDigest'}
    assert hashlib.sha256(encoded(core).rstrip(b'\n')).hexdigest()==p['policyDigest']
    assert p['MIN_DECISION_PRICE_JPY']==gate.MIN_DECISION_PRICE_JPY==75
    for n,h in p['sourcePins'].items():assert sha(ROOT/n)==h,n
    assert all(v is False for v in p['safety'].values())
    return p

def eid(r):return f"{r['sessionDate']}|{r['sessionDate']}T{r['decisionTimeJst']}:00+09:00|{r['symbol']}"
def records(f):return json.loads(f.to_json(orient='records',double_precision=15))
def exact_records(f):
    # pandas to_json rounds score bits; keep native IEEE values for source parity.
    return [{k:(None if pd.isna(v) else v.item() if isinstance(v,np.generic) else v) for k,v in r.items()} for r in f.to_dict('records')]
def concentration(rs,field):
    c=collections.Counter(r[field] for r in rs);n=sum(c.values())
    return {'n':n,'unique':len(c),'HHI':sum((v/n)**2 for v in c.values()) if n else None,'top10':sorted(c.items(),key=lambda x:(-x[1],x[0]))[:10]}
def selected_summary(u,s):
    out={}
    for level in LEVELS:
        out[str(level)]={}
        for kind,prefix in [('high','highOpportunity'),('close','closeOpportunity')]:
            out[str(level)][kind]={'metrics':base.opportunity_metrics(u,s,prefix,level),'distribution':hits.hit_distribution(s,prefix,level)}
    return out

def run(dataset,outdir):
    policy=verify();out=Path(outdir)
    if out.exists():raise FileExistsError(out)
    frame,manifest=base.load(Path(dataset))
    keep=base.IDENTITY+['sourceGroup','decisionPrice','decisionPriceValid','decisionPriceKind','referenceAgeMin','savedV1Score','futureBarCount','futureAuctionCount']+[f'{p}{k}' for p in ['highOpportunity','closeOpportunity'] for k in LEVELS]
    frame=frame[keep].copy()
    for prefix in ['highOpportunity','closeOpportunity']:
        for k in LEVELS:frame[f'{prefix}{k}']=pd.to_numeric(frame[f'{prefix}{k}'],errors='coerce')
    frozen=read(ROOT/'predict/research/phase57-long-only-frozen-selector-v1.json')
    sessions=frozen['freezePayload']['development']['sessions']
    assert sorted(frame.sessionDate.unique())==sessions and len(frame)==2758341
    u=parent.eligible_universe(frame);assert len(u)==1755720
    del frame
    ranks=u.sort_values(base.KEYS+['savedV1Score','symbol'],ascending=[True,True,False,True],kind='mergesort').groupby(base.KEYS,sort=False).cumcount()+1
    u['oldEligibleRank']=ranks
    status=u.decisionPrice.map(gate.price_status);excluded=u[status.ne('ELIGIBLE_MIN_PRICE')].copy()
    newu=u[status.eq('ELIGIBLE_MIN_PRICE')].copy()
    newu['newEligibleRank']=newu.sort_values(base.KEYS+['savedV1Score','symbol'],ascending=[True,True,False,True],kind='mergesort').groupby(base.KEYS,sort=False).cumcount()+1
    old=base.select_top5(u);new=base.select_top5(newu)
    assert len(old)==3800 and u[base.KEYS].drop_duplicates().shape[0]==760
    assert new.savedV1Score.equals(u.loc[new.index,'savedV1Score'])
    assert set(base.select_top5(newu.iloc[::-1]).index)==set(new.index)
    # Independent production-wrapper comparison, causal-only input; suffix/labels absent.
    runtimeids=[]
    for _,g in u.groupby(base.KEYS,sort=True):
        causal=exact_records(g[base.IDENTITY+['decisionPrice','referenceAgeMin','decisionPriceValid','savedV1Score']])
        runtimeids.extend(eid(r) for r in gate.select_top5(causal))
    assert runtimeids==[eid(r) for r in exact_records(new)]
    previous=read(ROOT/'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz')
    expected={r['selectorEventId']:r for r in previous}
    score_transport_differences=[]
    for r in exact_records(old):
        e=expected[eid(r)]
        assert r['decisionPrice']==e['decisionPrice'] and r['oldEligibleRank']==e['ridgeRank']
        assert math.isclose(r['savedV1Score'],e['ridgeScore'],rel_tol=0,abs_tol=1e-12)
        if r['savedV1Score']!=e['ridgeScore']:score_transport_differences.append(abs(r['savedV1Score']-e['ridgeScore']))
    assert set(expected)=={eid(r) for r in exact_records(old)}
    prior=read(ROOT/'docs/evidence/phase57-long-only-frozen-selector-v1-development-evidence.json')
    oldmetrics=selected_summary(u,old);newmetrics=selected_summary(newu,new)
    for k in LEVELS:
        for field,value in oldmetrics[str(k)]['high']['metrics'].items():
            if field in prior['highTouch'][str(k)]['metrics']:
                target=prior['highTouch'][str(k)]['metrics'][field]
                assert value==target or (value is not None and target is not None and math.isclose(value,target,abs_tol=1e-8)),(k,field,value,target)
    oldids=set(old.index);newids=set(new.index);removed=old.loc[sorted(oldids-newids)];added=new.loc[sorted(newids-oldids)]
    oldrows=exact_records(old);newrows=exact_records(new)
    def export(rs):
        return [{**r,'selectorEventId':eid(r),'decisionTimestamp':r['sessionDate']+'T'+r['decisionTimeJst']+':00+09:00','decisionPriceAvailableAtJst':(pd.Timestamp(r['sessionDate']+'T'+r['decisionTimeJst']+':00+09:00')-pd.Timedelta(minutes=r['referenceAgeMin'])).isoformat(),'priceGateStatus':gate.price_status(r['decisionPrice'])} for r in rs]
    ledger={'old':export(oldrows),'new':export(newrows),'excludedCandidates':export(exact_records(excluded)),'removedOldTop5':export(exact_records(removed)),'replacements':export(exact_records(added))}
    timestamps=sorted(set(tuple(r[k] for k in base.KEYS) for r in oldrows))
    affected=set(map(tuple,removed[base.KEYS].to_numpy()))
    replacements=[]
    for date,time in sorted(affected):
        replacements.append({'sessionDate':date,'decisionTimeJst':time,'removed':[r for r in ledger['removedOldTop5'] if r['sessionDate']==date and r['decisionTimeJst']==time],'added':[r for r in ledger['replacements'] if r['sessionDate']==date and r['decisionTimeJst']==time]})
    def loss_metrics(f):return {str(k):{'highHits':int((base.evaluator_valid(f,'highOpportunity') & f[f'highOpportunity{k}'].eq(1)).sum()),'highEvaluable':int(base.evaluator_valid(f,'highOpportunity').sum()),'n':len(f)} for k in LEVELS}
    stability={date:{'old':selected_summary(u[u.sessionDate.eq(date)],old[old.sessionDate.eq(date)]),'new':selected_summary(newu[newu.sessionDate.eq(date)],new[new.sessionDate.eq(date)])} for date in sessions}
    blocks={}
    for i in range(4):
        dates=sessions[i*19:(i+1)*19]
        blocks[str(i+1)]={'sessions':dates,'old':selected_summary(u[u.sessionDate.isin(dates)],old[old.sessionDate.isin(dates)]),'new':selected_summary(newu[newu.sessionDate.isin(dates)],new[new.sessionDate.isin(dates)])}
    top3=[x[0] for x in concentration(oldrows,'symbol')['top10'][:3]]
    def selection_diag(f):return {'n':len(f),'high':loss_metrics(f),'symbol':concentration(exact_records(f),'symbol'),'session':concentration(exact_records(f),'sessionDate')}
    audit={'scoreTransportDifferences':len(score_transport_differences),'maxScoreTransportDifference':max(score_transport_differences,default=0),'scoreTransportComparisonOnlyTolerance':1e-12,'oldSelectedParity':3800,'oldMetricsParity':True,'runtimeWrapperParity':True,'reverseInputSelectionParity':True,'scoresUnchanged':True,'sourcePinsUnchanged':True,'causalAgeBounds':True,'eligiblePriceMin':float(newu.decisionPrice.min()),'price75Selected':int(new.decisionPrice.eq(75).sum()),'lowPriceSelected':int(new.decisionPrice.le(75).sum()),'missingFailOpen':False,'excludedPlusAddedCountBalance':len(removed)==len(added),'outputOnlyLabels':True}
    result={'policyId':policy['policyId'],'policyDigest':policy['policyDigest'],'policyCommit':PROTOCOL_COMMIT,'sourceHead':policy['sourceHead'],'sourceManifest':manifest,'safety':policy['safety'],'impact':{'sessions':76,'decisionTimestamps':len(timestamps),'preEligibilityCandidates':2758341,'oldEligibleCandidates':len(u),'newEligibleCandidates':len(newu),'oldSelected':len(old),'newSelected':len(new),'excludedCandidates':len(excluded),'excludedOldTop5':len(removed),'affectedTimestamps':len(affected),'replacements':len(added),'newTop5ShortfallTimestamps':sum(n<5 for n in new.groupby(base.KEYS).size())+len(set(timestamps)-set(map(tuple,new[base.KEYS].drop_duplicates().to_numpy()))),'excludedUniqueSymbols':int(excluded.symbol.nunique()),'excludedPrices':base.distribution(excluded.decisionPrice),'removedTop5Prices':base.distribution(removed.decisionPrice)},'opportunity':{'old':oldmetrics,'new':newmetrics,'excludedCandidates':loss_metrics(excluded),'removedOldTop5':loss_metrics(removed),'replacements':loss_metrics(added),'commonOldUniverseRecallPct':{str(k):base.ratio(newmetrics[str(k)]['high']['metrics']['selectedHits'],oldmetrics[str(k)]['high']['metrics']['opportunities'],100) for k in LEVELS}},'replacementsByTimestamp':replacements,'sessionStability':stability,'chronological':blocks,'concentration':{'old':selection_diag(old),'new':selection_diag(new),'oldTop3FixedExclusion':top3,'oldExTop3':selection_diag(old[~old.symbol.isin(top3)]),'newExTop3':selection_diag(new[~new.symbol.isin(top3)])},'audit':audit,'freshOOSOpened':False,'freezeStatus':'PENDING_DOWNSTREAM_AND_CI_AUDIT'}
    out.mkdir(parents=True)
    write(out/'selector-ledger.json.gz',ledger);write(out/'selector-summary.json',result)
    manifestout={'policyDigest':policy['policyDigest'],'sourcePins':{**policy['sourcePins'],str(POLICY.relative_to(ROOT)):sha(POLICY)},'codePins':{str(IMPL.relative_to(ROOT)):sha(IMPL),'scripts/phase57_selector_min_price75.py':sha(__file__)},'outputPins':{n:sha(out/n) for n in ['selector-ledger.json.gz','selector-summary.json']}}
    write(out/'selector-manifest.json',manifestout)
    print(json.dumps({'impact':result['impact'],'audit':audit,'output':str(out)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset-dir',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.dataset_dir,a.out)
