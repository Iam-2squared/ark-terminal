"""Finite R1 temporal nested OOF. No production, provider or protected-data access.

Run only after the implementation/data manifest has been committed pre-fit.
Future labels enter fit/evaluator functions only, never the sequential policy.
"""
from __future__ import annotations
import argparse, collections, gc, gzip, hashlib, json, math, os, pickle, time, warnings
from pathlib import Path
import numpy as np
import scipy, sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from scripts import phase57_entry_all_material_r1_data as data
from scripts import phase57_state_v3_9pattern_entry_v1 as v3
from scripts import phase57_state_conditioned_signal_entry_v1 as metric
from scripts import phase57_entry_timing_census as census
from scripts import phase57_entry_all_material_evaluator_v1 as canonical
from scripts import phase57_entry_ordered_range_scorecard_v1 as ordered

ROOT=data.ROOT;OUT=data.OUT;SUB=data.SUB;REF=data.REFERENCE
SEED=570926;HORIZONS=(5,10,20,30);THRESHOLDS=(.40,.50,.60)
MODELS=('M1','M2','M3');CONFIGS=[(m,h,p) for m in MODELS for h in HORIZONS for p in THRESHOLDS]
read=data.read;write=data.write;digest=data.digest;ohash=data.object_hash

def scoring_intent(rows,probabilities,horizon,threshold):
    """No labels/quotes/oracle arguments. Only causal row time and probability."""
    assert len(rows)==len(probabilities)
    assert all(np.isfinite(probabilities))
    for r,p in zip(rows,probabilities):
        if r['delay']>horizon:break
        if p>=threshold:return r['minute'],'MODEL_THRESHOLD',float(p)
    for r,p in zip(rows,probabilities):
        if r['delay']==horizon:return r['minute'],'FORCED_HORIZON',float(p)
    return None,'HORIZON_UNREACHABLE',None

def current_ids(sources):
    return sorted(o for o,s in sources.items() if s['opportunity']['session']>='2025-05-30')

def evaluator_bundle():
    """Open already-approved retrospective labels ONLY outside decision layer."""
    sources=read(OUT/'prefit/sources.json.gz');rows=read(OUT/'prefit/rows.json')
    current=read(REF/'opportunities.json.gz');opps={r['opportunity']:r for r in current}
    all_raw_opps=read(SUB/'opportunities.json.gz');raw=read(SUB/'raw-paths-evaluator-only.json.gz')
    for o in all_raw_opps:
        oid=o['id']
        if oid not in sources or oid in opps:continue
        a=np.asarray(raw[oid]['today'],float).reshape(-1,7)
        start=census.e.old.minute(o['origin']['decisionTimestamp'])
        oracle=census.ordered_oracle(census.future_rows(o['session'],a,start),start)
        oracle['fullSessionEvaluable']=o['selectorOutcome']['mfeEnd'] is not None
        opps[oid]={'opportunity':oid,'session':o['session'],'symbol':o['symbol'],
                   'selectorMinute':start,'selectorPrice':o['origin']['decisionPrice'],
                   'selectorOutcome':o['selectorOutcome'],'orderedOracle':oracle}
    del all_raw_opps
    outcomes=read(SUB/'outcomes.json.gz');quotes={r['id']:r for r in rows}
    baseline={};immediate={};lookups={}
    for oid in sorted(sources):
        s=sources[oid];op=opps[oid];obs=s['observations'];grid=[r for r in obs if r['comparisonEligible']]
        ini=dict(s['oneMinuteIntent']);start=obs[0]['minute']
        fast=dict(ini,intentMinute=start,intentDelay=0,intentReason='INITIAL_STATE_BUY')
        tr0=v3.simulate_fill(oid,op['session'],grid,fast,quotes,outcomes)
        immediate[oid]=tr0
        tr=v3.simulate_fill(oid,op['session'],grid,ini,quotes,outcomes)
        tr['rangeRetention']=v3.range_retention(op,tr)
        tr['waitMaxRiseVsImmediatePct']=v3.missed_upside(raw[oid],tr0,tr,obs[-1]['minute'])
        rec=v3.candidate_record(op,ini,tr,metric.oracle_metrics(op,tr),metric.label_metrics(tr,outcomes))
        rec['experiment']='DROP_PULLBACK_1M_STATE_RECHECK_V1';baseline[oid]=rec
        # Evaluator-only cache from candidate intent minute to first possible fill.
        future={}
        for ob in obs:
            fake={'intentMinute':ob['minute'],'intentReason':'MODEL_THRESHOLD'}
            future[ob['minute']]=v3.simulate_fill(oid,op['session'],grid,fake,quotes,outcomes)
            future[ob['minute']].pop('attempts',None)
        lookups[oid]=future
    accepted=read(REF/'one-minute.json.gz');cids=current_ids(sources)
    regen=[baseline[i] for i in cids]
    assert regen==accepted,'CURRENT_FULL_RECORD_PARITY_FAILED'
    assert ohash(regen)=='e3044c697d9573b9774f35a7408c90c1610309cb8634ade2bf9bee8aa367a186'
    write(OUT/'prefit/reference-parity.json',{'status':'PASS','fullRecordsExact':len(regen),
        'canonicalRecordSHA256':ohash(regen),'priorComparatorPolicyUnchanged':True,'modelFits':0})
    slim={k:{'price':v.get('price'),'labels':{'mfeEnd':v['labels'].get('mfeEnd')} if v.get('labels') else None} for k,v in outcomes.items() if k.rsplit('|',1)[0] in sources}
    return sources,rows,opps,slim,baseline,lookups,{k:raw[k] for k in cids},immediate

def construct_labels(rows,opps,outcomes):
    y=np.full(len(rows),np.nan,dtype=np.float64);reasons=collections.Counter()
    for i,r in enumerate(rows):
        oracle=opps[r['opportunity']]['orderedOracle'];o=outcomes.get(r['id']);price=o.get('price') if o else None
        if not r['quoteAvailable'] or price is None:reasons['NO_NEXT_FILL_NOW']+=1;continue
        if not oracle.get('fullSessionEvaluable') or oracle.get('status')!='OBSERVED_ORDERED_ORACLE':reasons['ORACLE_UNAVAILABLE']+=1;continue
        if oracle.get('high',0)<=oracle.get('low',0) or oracle.get('low',0)<=0:reasons['NONPOSITIVE_RANGE']+=1;continue
        if oracle['highMinute']<=r['minute']:reasons['NO_STRICTLY_LATER_ORACLE_HIGH']+=1;continue
        y[i]=float((price-oracle['low'])/(oracle['high']-oracle['low'])<=.25)
    return y,reasons

def fit_preprocessor(x):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',RuntimeWarning);median=np.nanmedian(x,axis=0)
    median=np.where(np.isfinite(median),median,0.)
    filled=np.where(np.isfinite(x),x,median)
    mean=np.mean(filled,axis=0);scale=np.std(filled,axis=0);scale=np.where(scale>0,scale,1.)
    return {'median':median,'mean':mean,'scale':scale,'columns':x.shape[1]}

def transform(x,pp):
    missing=~np.isfinite(x)
    real=(np.where(missing,pp['median'],x)-pp['mean'])/pp['scale']
    return np.concatenate((real,missing.astype(np.float64)),axis=1)

def model_factory(name):
    if name in ('M1','M2'):
        return LogisticRegression(penalty='l2' if name=='M1' else 'l1',C=1.,solver='liblinear',
            max_iter=1000,tol=.0001,class_weight=None,random_state=SEED)
    return HistGradientBoostingClassifier(max_depth=3,learning_rate=.05,max_iter=100,
        max_leaf_nodes=31,min_samples_leaf=20,l2_regularization=0.,early_stopping=False,random_state=SEED)

def fit_predict(name,x,y,train_idx,test_idx,save_path):
    good=train_idx[np.isfinite(y[train_idx])]
    if len(np.unique(y[good]))<2:return None,{'status':'UNTRAINABLE_SINGLE_CLASS','fitRows':len(good)}
    pp=fit_preprocessor(np.asarray(x[good]));train=transform(np.asarray(x[good]),pp)
    model=model_factory(name);started=time.monotonic()
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter('always');model.fit(train,y[good])
    del train
    if any(issubclass(w.category,ConvergenceWarning) for w in ws):
        return None,{'status':'CONVERGENCE_FAILURE','fitRows':len(good),'warnings':[str(w.message) for w in ws]}
    # Batching controls memory; it does not alter policy/model semantics.
    pred=np.concatenate([model.predict_proba(transform(np.asarray(x[a]),pp))[:,1] for a in np.array_split(test_idx,max(1,math.ceil(len(test_idx)/8000)))])
    save_path.parent.mkdir(parents=True,exist_ok=True)
    with save_path.open('wb') as f:pickle.dump({'preprocessor':pp,'model':model},f,protocol=5)
    ans={'status':'PASS','fitRows':len(good),'positiveFitRows':int(np.sum(y[good])),
         'predictRows':len(test_idx),'seconds':time.monotonic()-started,'modelFileSHA256':digest(save_path)}
    del model,pp;gc.collect()
    return pred,ans

def fast_metrics(ids,selected,opps,outcomes):
    filled=0;positions=[];capture={str(k):[0,0] for k in (1,2,3,4,5)}
    for oid in ids:
        tr=selected[oid];op=opps[oid];oracle=op['orderedOracle'];filled+=tr['entryId'] is not None
        if tr['entryId'] and oracle.get('fullSessionEvaluable') and oracle.get('status')=='OBSERVED_ORDERED_ORACLE' and oracle.get('high',0)>oracle.get('low',0)>0:
            positions.append((tr['price']-oracle['low'])/(oracle['high']-oracle['low']))
        lab=outcomes.get(tr['entryId'],{}).get('labels') if tr['entryId'] else None
        end=lab.get('mfeEnd') if lab else None;origin=op['selectorOutcome']['mfeEnd']
        for k in (1,2,3,4,5):
            if origin is not None and origin>=k:
                capture[str(k)][1]+=1;capture[str(k)][0]+=int(end is not None and end>=k)
    return {'population':len(ids),'fills':filled,'fillRatePct':100*filled/len(ids),
        'entryPositionN':len(positions),'meanEntryPosition':float(np.mean(positions)) if positions else None,
        'capture':{k:{'captured':v[0],'denominator':v[1],'ratePct':100*v[0]/v[1] if v[1] else None} for k,v in capture.items()}}

def stream_for_config(ids,indices,pred,rows,sources,lookups,horizon,threshold):
    mapping=collections.defaultdict(list)
    for ix,prob in zip(indices,pred):mapping[rows[ix]['opportunity']].append((int(ix),float(prob)))
    selected={};intents={}
    for oid in ids:
        pairs=mapping[oid];rr=[rows[i] for i,p in pairs];probs=np.array([p for i,p in pairs])
        minute,reason,prob=scoring_intent(rr,probs,horizon,threshold)
        s=sources[oid];intent=dict(s['oneMinuteIntent'])
        past=[c for c in s['originalState'] if minute is not None and c['asOf']<=minute]
        intent.update(intentMinute=minute,intentDelay=next((r['delay'] for r in rr if r['minute']==minute),None),
            intentReason=reason,stateAtIntent=past[-1]['state'] if past else None,
            triggerSources=[reason] if minute is not None else [],triggerSignals=[])
        # Diagnostic post-intent fields from the baseline are NOT model inputs.
        intents[oid]={'intent':intent,'p25':prob,'horizon':horizon,'threshold':threshold}
        if minute is not None:
            trade=dict(lookups[oid][minute]);trade['intentReason']=reason
        else:
            trade=v3.simulate_fill(oid,s['opportunity']['session'],[],intent,{},{});trade['unfilledReason']='HORIZON_UNREACHABLE'
        selected[oid]=trade
    return selected,intents

def ids_for(sources,days):
    dd=set(days);return sorted(o for o,s in sources.items() if s['opportunity']['session'] in dd)

def train(output_name):
    assert sklearn.__version__=='1.8.0' and np.__version__=='2.3.5' and scipy.__version__=='1.17.0'
    marker=OUT/'prefit/implementation-freeze.json'
    if not marker.exists():raise RuntimeError('MISSING_COMMITTED_PREFIT_IMPLEMENTATION_FREEZE')
    freeze=read(marker)
    assert freeze['githubCommit'] and freeze['modelFitsBeforeFreeze']==0
    for path,h in freeze['codeHashes'].items():assert digest(ROOT/path)==h,('CODE_CHANGED_AFTER_FREEZE',path)
    for name,h in read(OUT/'prefit/manifest.json').items():assert digest(OUT/'prefit'/name)==h,('PREFIT_FILE_CHANGED',name)
    dest=OUT/output_name
    if dest.exists():raise FileExistsError('APPEND_ONLY_RUN_ALREADY_EXISTS')
    dest.mkdir(parents=True)
    sources,rows,opps,outcomes,baseline,lookups,raw,immediate=evaluator_bundle()
    y,reasons=construct_labels(rows,opps,outcomes);np.save(dest/'training-labels.npy',y,allow_pickle=False)
    write(dest/'label-accounting.json',{'rows':len(y),'valid':int(np.isfinite(y).sum()),'missingReasons':dict(reasons),
        'scope':'training-only future label; no outcome columns in predictors; missing labels never exclude test predictions'})
    x=np.load(OUT/'prefit/features.npy',mmap_mode='r');folds=read(OUT/'prefit/folds.json')
    sessions=np.array([r['session'] for r in rows]);ledger=[];chosen=[];oof_trades={};oof_intents={};prediction_rows={}
    for fold in folds:
        config_trades={c:{} for c in CONFIGS};failed=set();valid_ids=[]
        for inner in fold['inner']:
            assert max(inner['train'])<inner['purge']<min(inner['validation'])
            ti=np.flatnonzero(np.isin(sessions,inner['train']));vi=np.flatnonzero(np.isin(sessions,inner['validation']))
            ids=ids_for(sources,inner['validation']);assert not set(valid_ids)&set(ids);valid_ids.extend(ids)
            for model_id in MODELS:
                pred,receipt=fit_predict(model_id,x,y,ti,vi,dest/'models'/f"outer{fold['id']}-inner{inner['id']}-{model_id}.pkl")
                row={'outer':fold['id'],'inner':inner['id'],'model':model_id,**receipt};ledger.append(row)
                write(dest/'fit-ledger.json',ledger);print(json.dumps(row),flush=True)
                if pred is None:failed.add(model_id);continue
                for c in CONFIGS:
                    if c[0]!=model_id:continue
                    tr,_=stream_for_config(ids,vi,pred,rows,sources,lookups,c[1],c[2]);config_trades[c].update(tr)
        base_stats=fast_metrics(valid_ids,baseline,opps,outcomes);evaluated=[]
        for c in CONFIGS:
            if c[0] in failed or len(config_trades[c])!=len(valid_ids):
                evaluated.append({'config':c,'status':'INCOMPLETE_FIT','admissible':False});continue
            v=fast_metrics(valid_ids,config_trades[c],opps,outcomes)
            ok=v['meanEntryPosition'] is not None and v['fillRatePct']>=base_stats['fillRatePct']-2.
            for level in ('3','5'):
                a=v['capture'][level]['ratePct'];b=base_stats['capture'][level]['ratePct']
                ok=ok and a is not None and b is not None and a>=b-5.
            evaluated.append({'config':c,'status':'EVALUATED','admissible':bool(ok),'metrics':v})
        admissible=[e for e in evaluated if e['admissible']]
        select=None
        if admissible:
            best=min(e['metrics']['meanEntryPosition'] for e in admissible)
            tied=[e for e in admissible if e['metrics']['meanEntryPosition']<=best+.005]
            select=min(tied,key=lambda e:(MODELS.index(e['config'][0]),e['config'][1],abs(e['config'][2]-.5),e['config'][2]))['config']
        write(dest/f"outer{fold['id']}-inner-selection.json",{'baseline':base_stats,'configs':evaluated,'selected':select})
        test_ids=ids_for(sources,fold['test']);assert len(test_ids)==fold['testN'];assert not set(oof_trades)&set(test_ids)
        fallback_reason='NO_INNER_ADMISSIBLE_CONFIG' if select is None else None
        if select is not None:
            trix=np.flatnonzero(np.isin(sessions,fold['train']));testix=np.flatnonzero(np.isin(sessions,fold['test']))
            assert max(fold['train'])<fold['purge']<min(fold['test'])
            pred,receipt=fit_predict(select[0],x,y,trix,testix,dest/'models'/f"outer{fold['id']}-selected.pkl")
            ledger.append({'outer':fold['id'],'inner':None,'model':select[0],**receipt});write(dest/'fit-ledger.json',ledger)
            if pred is None:fallback_reason='OUTER_MODEL_UNTRAINABLE'
            else:
                tr,intents=stream_for_config(test_ids,testix,pred,rows,sources,lookups,select[1],select[2]);oof_trades.update(tr);oof_intents.update(intents)
                for ix,prob in zip(testix,pred):prediction_rows[rows[ix]['id']]=float(prob)
        if fallback_reason:
            for oid in test_ids:
                oof_trades[oid]=baseline[oid]
                oof_intents[oid]={'intent':sources[oid]['oneMinuteIntent'],'fallback':'ONE_MINUTE','reason':fallback_reason,'p25':None}
        chosen.append({'outer':fold['id'],'testN':len(test_ids),'selectedConfig':select,'fallback':fallback_reason})
        write(dest/'fold-selection.json',chosen);print(json.dumps(chosen[-1]),flush=True)
        del config_trades;gc.collect()
    cids=current_ids(sources);assert len(cids)==len(oof_trades)==2155
    # Seal candidate intents BEFORE any aggregate outer-test score is computed.
    write(dest/'candidate-intents.json',oof_intents);write(dest/'oof-predictions.json.gz',prediction_rows)
    candidate_pin={'candidate':'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF','population':2155,
        'intentSHA256':digest(dest/'candidate-intents.json'),'predictionsSHA256':digest(dest/'oof-predictions.json.gz'),
        'selectionSHA256':digest(dest/'fold-selection.json'),'outerOutcomeScoreComputedBeforePin':False}
    write(dest/'candidate-freeze.json',candidate_pin)
    full_outcomes=read(SUB/'outcomes.json.gz')
    records=[]
    for oid in cids:
        entry=oof_intents[oid]
        if entry.get('fallback'):
            rec=dict(baseline[oid]);rec['experiment']='ALL_MATERIAL_R1_ONE_MINUTE_FALLBACK'
        else:
            trade=dict(oof_trades[oid]);intent=entry['intent'];op=opps[oid]
            trade['rangeRetention']=v3.range_retention(op,trade)
            trade['waitMaxRiseVsImmediatePct']=v3.missed_upside(raw[oid],immediate[oid],trade,sources[oid]['observations'][-1]['minute'])
            rec=v3.candidate_record(op,intent,trade,metric.oracle_metrics(op,trade),metric.label_metrics(trade,full_outcomes))
            rec.update(sourceArm='ALL_MATERIAL_R1',experiment='ALL_MATERIAL_R1_NESTED_OOF',
                policyAction='BUY_NOW' if intent['intentDelay']==0 else 'WAIT',fallbackTargetDelay=entry['horizon'])
        records.append(rec)
    write(dest/'entry-records.json.gz',records)
    cr=[opps[o] for o in cids];state_ref=read(REF/'state-v3.json.gz')
    comparisons={name:read(REF/file) for name,file in [('IMMEDIATE','immediate.json.gz'),('ENTRY_V1','entry-v1.json.gz'),('ORIGINAL_STATE_V3','state-v3.json.gz'),('ONE_MINUTE','one-minute.json.gz')]}
    score=ordered.build(cr,records,'ALL_MATERIAL_R1',state_ref,comparisons['ONE_MINUTE'],'ONE_MINUTE')
    score['rangeDefinitionClarification']['noNewEntryVersion']=False
    score['extraPairedBaselines']={n:canonical.evaluate(cr,records,'ALL_MATERIAL_R1',b,n)['baselineComparison'] for n,b in comparisons.items()}
    score['participation']={'selectorN':2155,'participatingN':2155,'ABSTAIN':0,'coveragePct':100.,
        'unfilledReasons':dict(collections.Counter(r['unfilledReason'] for r in records if not r['entryId'])),
        'coverageCurve':{'status':'NOT_EVALUABLE','reason':'No preapproved causal abstention calibration/cap; no abstention adopted'}}
    score['featureAdmissionScope']='CONDITIONAL_HISTORICAL_DEVELOPMENT_ONLY'
    score['frozenFolds']=chosen;score['candidateFreeze']=candidate_pin
    score['stateDisposition']={s:('NO_T0' if not any(r['initialState']==s for r in state_ref) else 'MEASURED') for s in ordered.STATES}
    score['A_J_status']={
        'A':'REPORTED','B':'REPORTED','C':'REPORTED','D':'REPORTED_ORDERED_RANGE_AND_LEGACY_MFE_SEPARATE',
        'E':'REPORTED_CANONICAL_1_TO_5','F':'REPORTED_WITH_VALID_N','G':'REPORTED_SECTOR_UNAVAILABLE',
        'H':'REPORTED_ALL_FOUR_BASELINES','I':'LOCAL_CHECKS_REPLAY_AND_CI_PENDING','J':'USER_REQUESTED_ENTRY_STOP_AFTER_ONE_FINITE_PASS_NO_AUTOMATIC_PROMOTION'}
    write(dest/'scorecard.json',score)
    for n,b in comparisons.items():write(dest/(n+'-scorecard.json'),ordered.build(cr,b,n,state_ref,comparisons['IMMEDIATE'],'IMMEDIATE'))
    write(dest/'result.json',{'status':'MEASURED_DEVELOPMENT_PENDING_INTEGRITY_CI','population':2155,
        'folds':chosen,'overall':score['overall'],'noMoreEntryOptimization':True,'modelFits':len(ledger),
        'providerRequests':0,'protectedOpens':0,'safety':dict.fromkeys(v3.SAFETY_KEYS,False)})
    print('MEASUREMENT_COMPLETE',json.dumps({'overall':score['overall']['entryPosition'],'folds':chosen}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-name',required=True);a=p.parse_args();train(a.output_name)
