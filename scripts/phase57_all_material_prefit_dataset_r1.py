"""Deterministic pre-fit feature/fold manifests and current reference replay."""
from __future__ import annotations
import argparse,collections,gc,gzip,hashlib,json,math
from pathlib import Path
import numpy as np
from scripts import phase57_entry_pattern_v2 as ptn
from scripts import phase57_entry_timing_signals as sig
from scripts import phase57_state_v3_9pattern_entry_v1 as v3
from scripts import phase57_state_conditioned_signal_entry_v1 as m
from scripts import phase57_entry_all_material_feature_coverage_v1 as cov
from scripts import phase57_all_material_prefit_reconstruction_r1 as reg
ROOT=Path(__file__).resolve().parents[1]; SRC=ptn.BASE/'ci-result/substrate'; OUT=reg.OUT
STATES=tuple(v3.PATTERNS)
WINDOWS=(3,5,10)

def overlay(row,observations,checks,closed_price):
    now=row['delay']; past=[s for s in checks if s['delay']<=now]; current=past[-1]
    previous=past[-2] if len(past)>1 else None
    cs=current.get('state'); ps=previous.get('state') if previous else None
    d={f'STATE/current/{s}':float(cs==s) for s in STATES}
    d.update({f'STATE/previous/{s}':float(ps==s) if ps else math.nan for s in STATES})
    changed=[s['delay'] for a,s in zip(past,past[1:]) if a.get('state')!=s.get('state')]
    d.update({'STATE/valid':float(cs in STATES),'STATE/priorAvailable':float(ps in STATES),
        'STATE/staleness':float(now-current['delay']),'STATE/dwell':float(now-(changed[-1] if changed else past[0]['delay'])),
        'STATE/dwellLeftCensored':float(not changed)})
    obs=[s for s in observations if s['delay']<=now]; at=obs[-1]
    assert at['minute']==row['minute']
    for w in WINDOWS:
        nn=[s for s in past if now-w < s['delay']<=now]
        count=sum(now-w<s['delay']<=now and a.get('state')!=s.get('state') for a,s in zip(past,past[1:]))
        d[f'STATE/transitions{w}']=float(count) if now>=w else math.nan
        d[f'STATE/churn{w}']=float(count/max(1,len(nn))) if now>=w else math.nan
        d[f'STATE/historyCoverage{w}']=min(1.,max(0.,now/w))
    for f in sig.FAMILIES:
        current_trigger=at['signals'][f]['trigger']
        d[f'SIX/{f}/known']=float(current_trigger is not None)
        d[f'SIX/{f}/trigger']=float(current_trigger) if current_trigger is not None else math.nan
        fired=[s['delay'] for s in obs if s['signals'][f]['trigger'] is True]
        d[f'SIX/{f}/sinceLastTrue']=float(now-fired[-1]) if fired else math.nan
        for w in WINDOWS:
            oo=[s for s in obs if now-w < s['delay']<=now]
            known=[s['signals'][f]['trigger'] for s in oo if s['signals'][f]['trigger'] is not None]
            d[f'SIX/{f}/count{w}']=float(sum(known)) if len(known)==w else math.nan
            d[f'SIX/{f}/knownFraction{w}']=len(known)/w
    t=row['minute']
    d.update({'TIME/activeMinute':float(cov.active_ordinal(t)),'TIME/pm':float(t>=750),
        'TIME/lunchBoundary':float(t in (690,750,751)),
        'PRICE/logClosed':math.log(closed_price) if closed_price is not None and closed_price>0 else math.nan})
    return d

def compact_sources():
    raw=m.read_json(OUT/'causal-sources.json.gz'); comp={}
    for oid,b in raw.items():
        comp[oid]={'intent':b['intent'],'stateRows':b['stateRows'],
            'minuteRows':[{k:r[k] for k in ('opportunity','session','minute','delay','comparisonEligible','signals','computedThroughBarStart')} for r in b['minuteRows']]}
    del raw;gc.collect()
    return comp

def build_splits(protocol,opps,feature_ids):
    prior=protocol['fit']+protocol['selection']; current=sorted({o['session'] for o in opps if o['session'] in protocol['evaluation']})
    assert len(prior)==75 and len(current)==58
    by_day=collections.defaultdict(list)
    for o in opps:by_day[o['session']].append(o['id'])
    def stats(days):
        ids=sorted(i for d in days for i in by_day[d]); missing=sorted(set(ids)-feature_ids)
        return {'sessions':list(days),'opportunityIds':ids,'N':len(ids),'featurelessIds':missing}
    blocks=np.array_split(np.array(current),5); folds=[]; before=[]
    for n,block in enumerate(blocks,1):
        block=block.tolist()
        if before: training=prior+before[:-1];purge=before[-1]
        else:training=prior;purge=protocol['embargo2'][-1]
        inner=[]; size=len(training)//5
        for start in range(len(training)-3*size,len(training),size):
            train=training[:start-1]; val=training[start:start+size]
            assert train[-1]<training[start-1]<val[0]
            a,b=stats(train),stats(val);assert not b['featurelessIds']
            inner.append({'train':a,'purgeSession':training[start-1],'validation':b})
        assert len(inner)==3
        test=stats(block); assert not test['featurelessIds'] and training[-1]<purge<block[0]
        folds.append({'fold':n,'train':stats(training),'purgeSession':purge,'test':test,'inner':inner})
        before.extend(block)
    assert [f['test']['N'] for f in folds]==[442,446,445,412,410]
    ids=[i for f in folds for i in f['test']['opportunityIds']]
    assert len(ids)==len(set(ids))==2155
    return {'version':'R2_PREFIT_AVAILABILITY_ONLY','splitter':'outer array_split 58 sessions into5; inner3 expanding test_size=floor(n/5), gap1 session',
        'folds':folds,'outerUniqueTestN':2155,'prior':stats(prior)}

def main(accepted_records):
    OUT.mkdir(parents=True,exist_ok=True)
    p=m.read_json(ptn.BASE/'protocol.json');allowed=set(p['fit']+p['selection']+p['evaluation'])
    originals=m.read_json(SRC/'opportunities.json.gz')
    safe=[{'id':o['id'],'session':o['session'],'symbol':o['symbol'],'start':ptn.old.minute(o['origin']['decisionTimestamp']),
        'selectorPrice':o['origin']['decisionPrice']} for o in originals if o['session'] in allowed]
    del originals;safe_by={o['id']:o for o in safe}
    rows_all=m.read_json(SRC/'rows.json.gz'); by_day=collections.defaultdict(list)
    for r in rows_all:by_day[r['session']].append(r)
    rows=[r for r in rows_all if r['opportunity'] in safe_by and r.get('eligible1') and 0<=r['delay']<=30]
    feature_ids={r['opportunity'] for r in rows}; splits=build_splits(p,safe,feature_ids)
    m.write_json(OUT/'split-manifest.json',splits)
    raw=m.read_json(SRC/'raw-paths-evaluator-only.json.gz')
    prices={}
    for r in rows:
        a=raw[r['opportunity']]['today']; k=[b for b in a if b[0]<r['minute']]
        prices[r['id']]=float(k[-1][4]) if k else None
    source=compact_sources()
    current_opp=m.read_json(ROOT/'docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz')
    immediate=m.read_json(ROOT/'docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/baseline-immediate-records.json.gz');im={r['opportunity']:r for r in immediate}
    accepted=m.read_json(Path(accepted_records));accepted_by={r['opportunity']:r for r in accepted}
    quotes={r['id']:r for r in rows_all if r.get('eligible1') and r['opportunity'] in accepted_by}
    all_outcomes=m.read_json(SRC/'outcomes.json.gz')
    outcomes={k:v for k,v in all_outcomes.items() if k.rsplit('|',1)[0] in accepted_by};del all_outcomes
    reproduced=[]
    for o in current_opp:
        oid=o['opportunity'];b=source[oid];intent=b['intent']
        grid=[r for r in b['minuteRows'] if r['comparisonEligible']]
        tr=v3.simulate_fill(oid,o['session'],grid,intent,quotes,outcomes)
        tr['rangeRetention']=v3.range_retention(o,tr)
        tr['waitMaxRiseVsImmediatePct']=v3.missed_upside(raw[oid],im[oid],tr,b['minuteRows'][-1]['minute'])
        rec=v3.candidate_record(o,intent,tr,m.oracle_metrics(o,tr),m.label_metrics(tr,outcomes))
        rec['experiment']='DROP_PULLBACK_1M_STATE_RECHECK_V1'
        assert rec==accepted_by[oid],('CURRENT_ONE_MINUTE_PARITY',oid,{k for k in rec if rec[k]!=accepted_by[oid].get(k)})
        reproduced.append(rec)
    h=reg.canonical_hash(sorted(reproduced,key=lambda r:r['opportunity']))
    assert h=='e3044c697d9573b9774f35a7408c90c1610309cb8634ade2bf9bee8aa367a186'
    m.write_json(OUT/'current-one-minute-parity.json',{'status':'PASS','records':2155,'canonicalRecordSHA256':h,
        'completeRecordEquality':True,'modelFits':0,'newNearLowTrainingLabelsBuilt':0})
    del raw,outcomes,quotes,accepted,accepted_by,reproduced,current_opp,immediate,im;gc.collect()
    pattern_names=m.read_json(SRC/'names.json'); overlay_names=None; cursor=0;fullnames=[]
    matrix=None; rowmeta=[]
    for day in sorted(allowed):
        rr=by_day[day]
        with gzip.open(SRC/(day+'.npy.gz'),'rb') as f:a=np.load(f,allow_pickle=False)
        for i,r in enumerate(rr):
            if r['opportunity'] not in safe_by or not r.get('eligible1') or not 0<=r['delay']<=30:continue
            assert r['computedThroughMinute'] is None or r['computedThroughMinute']<r['minute']
            assert r['previousThrough'] is None or r['previousThrough']<day
            b=source[r['opportunity']]
            d=overlay(r,b['minuteRows'],b['stateRows'],prices[r['id']])
            if overlay_names is None:
                overlay_names=sorted(d);fullnames=pattern_names+overlay_names
                assert len(fullnames)==len(set(fullnames))
                matrix=np.lib.format.open_memmap(OUT/'features.npy',mode='w+',dtype=np.float32,shape=(len(rows),len(fullnames)))
            assert sorted(d)==overlay_names
            matrix[cursor,:len(pattern_names)]=a[i]
            matrix[cursor,len(pattern_names):]=[d[k] for k in overlay_names]
            rowmeta.append({k:r[k] for k in ('id','opportunity','session','symbol','minute','delay','quoteAvailable')})
            cursor+=1
    assert cursor==len(rows)==149900
    matrix.flush()
    m.write_json(OUT/'feature-names.json',fullnames)
    m.write_gzip_json(OUT/'row-metadata.json.gz',rowmeta)
    m.write_gzip_json(OUT/'safe-opportunities.json.gz',safe)
    m.write_gzip_json(OUT/'decision-sources.json.gz',source)
    receipt={'status':'PREFIT_PASS_PENDING_REPO_FREEZE','patternColumns':len(pattern_names),'overlayColumns':len(overlay_names),
        'columns':len(fullnames),'rows':cursor,'rawOpportunities':len(safe),'featureOpportunities':len(feature_ids),
        'currentOpportunityN':2155,'priorRawOpportunityN':2866,'priorFeaturelessN':90,
        'innerValidationFeaturelessN':0,'outerEvaluationFeaturelessN':0,
        'sourceLimitations':['historical observed bars not independent knownAt certification','frozen upstream same-day metadata inherited'],
        'modelFits':0,'newNearLowTrainingLabelsBuilt':0,
        'hashes':{f.name:m.sha256(f) for f in OUT.iterdir() if f.is_file() and f.name!='dataset-prefit-receipt.json'}}
    m.write_json(OUT/'dataset-prefit-receipt.json',receipt)
    print(json.dumps(receipt,sort_keys=True),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--accepted-records',required=True)
    args=parser.parse_args();main(args.accepted_records)
