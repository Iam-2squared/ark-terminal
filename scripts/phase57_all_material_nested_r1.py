"""Precommitted finite nested temporal Entry experiment; Development only."""
from __future__ import annotations
import argparse,collections,gc,hashlib,json,math,pickle,platform,time,warnings
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
from scripts import phase57_state_conditioned_signal_entry_v1 as metric
from scripts import phase57_state_v3_9pattern_entry_v1 as v3
from scripts import phase57_entry_timing_census as census
from scripts import phase57_entry_ordered_range_scorecard_v1 as scorecard
from scripts import phase57_entry_pattern_v2 as pattern
from scripts import phase57_all_material_prefit_reconstruction_r1 as reg

ROOT=Path(__file__).resolve().parents[1]; PRE=reg.OUT
SOURCE=pattern.BASE/'ci-result/substrate'
NAME='ALL_MATERIAL_ENTRY_R1_NESTED_OOF'
SEED=570926
CONFIGS=tuple((m,h,p) for m in ('M1','M2','M3') for h in (5,10,20,30) for p in (.4,.5,.6))


def digest(value):return reg.canonical_hash(value)


def make_intent(points,h,p):
    """Decision-only API: chronological (minute, active delay, probability)."""
    points=[(int(t),int(d),float(q)) for t,d,q in points if 0<=d<=h]
    assert all(b[1]>a[1] for a,b in zip(points,points[1:])), 'TIME_ORDER'
    for t,d,q in points:
        if q>=p:return {'intentMinute':t,'intentDelay':d,'intentReason':'MODEL_TRIGGER','confidence':q}
    for t,d,q in points:
        if d==h:return {'intentMinute':t,'intentDelay':d,'intentReason':'FORCE_H','confidence':q}
    return {'intentMinute':None,'intentDelay':None,'intentReason':'H_CHECKPOINT_UNAVAILABLE','confidence':None}


class Preprocessor:
    def fit(self,x):
        x=np.array(x,dtype=np.float32,copy=True);x[~np.isfinite(x)]=np.nan
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',RuntimeWarning)
            self.median=np.nanmedian(x,axis=0)
        self.median=np.where(np.isfinite(self.median),self.median,0.).astype(np.float32)
        x=np.where(np.isfinite(x),x,self.median)
        self.mean=x.mean(axis=0,dtype=np.float64)
        self.std=x.std(axis=0,dtype=np.float64);self.std[self.std<1e-12]=1.
        return self
    def transform(self,x):
        x=np.asarray(x,dtype=np.float32); missing=~np.isfinite(x)
        z=((np.where(missing,self.median,x)-self.mean)/self.std).astype(np.float32)
        return np.concatenate((z,missing.astype(np.float32)),axis=1)


class ModelUntrainable(RuntimeError):
    pass


def fit_model(x,y,name):
    if set(np.unique(y))!={0.,1.}:raise ModelUntrainable('TRAIN_SINGLE_CLASS')
    pp=Preprocessor().fit(x); xx=pp.transform(x)
    if name in ('M1','M2'):
        model=LogisticRegression(C=1.,penalty='l2' if name=='M1' else 'l1',solver='liblinear',
            max_iter=1000,tol=1e-4,random_state=SEED,class_weight=None)
    else:
        model=HistGradientBoostingClassifier(max_depth=3,learning_rate=.05,max_iter=100,
            max_leaf_nodes=31,min_samples_leaf=20,l2_regularization=0.,early_stopping=False,random_state=SEED)
    with warnings.catch_warnings(record=True) as caught,threadpool_limits(limits=1):
        warnings.simplefilter('always');model.fit(xx,y)
    if any(issubclass(w.category,ConvergenceWarning) for w in caught):raise ModelUntrainable('TRAIN_NOT_CONVERGED')
    return pp,model


def predict(fitted,x):
    pp,model=fitted
    with threadpool_limits(limits=1):return model.predict_proba(pp.transform(x))[:,1]


def training_label(row,opportunity,outcome):
    """Evaluator/training-label-only; never a feature or runtime decision."""
    o=opportunity['orderedOracle']; price=outcome.get('price') if outcome else None
    if (not row['quoteAvailable'] or price is None or not o.get('fullSessionEvaluable')
        or o.get('status')!='OBSERVED_ORDERED_ORACLE' or o.get('high',0)<=o.get('low',0)
        or o['highMinute']<=row['minute']):return math.nan
    return float((price-o['low'])/(o['high']-o['low'])<=.25)


def build_replay_inputs():
    safe=metric.read_json(PRE/'safe-opportunities.json.gz');ids={o['id'] for o in safe}
    sources=metric.read_json(PRE/'decision-sources.json.gz')
    original=metric.read_json(SOURCE/'opportunities.json.gz')
    original={o['id']:o for o in original if o['id'] in ids}
    raw=metric.read_json(SOURCE/'raw-paths-evaluator-only.json.gz')
    current=metric.read_json(ROOT/'docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz')
    opportunities={o['opportunity']:o for o in current}
    for s in safe:
        oid=s['id']
        if oid in opportunities:continue
        o=original[oid]; path=raw[oid]; a=np.asarray(path['today'],float).reshape(-1,7)
        oracle=census.ordered_oracle(census.future_rows(s['session'],a,s['start']),s['start'])
        oracle['fullSessionEvaluable']=o['selectorOutcome']['mfeEnd'] is not None
        opportunities[oid]={'opportunity':oid,'session':s['session'],'symbol':s['symbol'],
            'selectorMinute':s['start'],'selectorPrice':s['selectorPrice'],
            'selectorOutcome':o['selectorOutcome'],'orderedOracle':oracle}
    del raw,original;gc.collect()
    outcomes_all=metric.read_json(SOURCE/'outcomes.json.gz')
    outcomes={k:v for k,v in outcomes_all.items() if k.rsplit('|',1)[0] in ids};del outcomes_all
    row_source=metric.read_json(SOURCE/'rows.json.gz')
    quotes={r['id']:r for r in row_source if r.get('eligible1') and r['opportunity'] in ids};del row_source
    grids={oid:[r for r in src['minuteRows'] if r['comparisonEligible']] for oid,src in sources.items()}
    t0={oid:src['stateRows'][0]['state'] for oid,src in sources.items()}
    def record(oid,intent,experiment):
        o=opportunities[oid]
        tr=v3.simulate_fill(oid,o['session'],grids[oid],intent,quotes,outcomes)
        tr['rangeRetention']=v3.range_retention(o,tr)
        rawintent=sources[oid]['intent']
        full={**rawintent,**intent,'initialState':t0[oid]}
        if experiment==NAME:
            st=[r for r in sources[oid]['stateRows'] if intent['intentMinute'] is not None and r['asOf']<=intent['intentMinute']]
            full['stateAtIntent']=st[-1]['state'] if st else None
            full['triggerSignals']=[];full['triggerSources']=[intent['intentReason']]
        out=v3.candidate_record(o,full,tr,metric.oracle_metrics(o,tr),metric.label_metrics(tr,outcomes))
        out['experiment']=experiment
        out['confidence']=intent.get('confidence')
        if experiment==NAME:out['sourceArm']=NAME;out['fallbackTargetDelay']=intent.get('horizon')
        return out
    baseline={oid:record(oid,sources[oid]['intent'],'DROP_PULLBACK_1M_STATE_RECHECK_V1') for oid in sorted(ids)}
    accepted=metric.read_json(ROOT/'artifacts/one-minute/replay-a/entry-records.json.gz')
    for exact in accepted:
        oid=exact['opportunity']
        assert all(baseline[oid][k]==exact[k] for k in ('entryId','entryMinute','price','delay','quality','labels'))
        baseline[oid]=exact
    current_saved=metric.read_json(ROOT/'docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/baseline-immediate-records.json.gz')
    state_records=metric.read_json(ROOT/'docs/evidence/phase57-state-v3-9pattern-entry-v1/measurement/entry-records.json.gz')
    return opportunities,outcomes,record,baseline,t0,current_saved,state_records


def simple_score(opportunities,records):
    positions=[r['quality']['entryPosition'] for r in records if r['entryId'] and r['quality']['entryPosition'] is not None]
    cap=metric.capture(opportunities,records)
    return {'N':len(records),'fills':sum(r['entryId'] is not None for r in records),
        'fillRatePct':100*sum(r['entryId'] is not None for r in records)/len(records),
        'positionN':len(positions),'meanEP':float(np.mean(positions)) if positions else None,
        'capture3':cap['3']['ratePct'],'capture5':cap['5']['ratePct']}


def admissible(result,reference):
    return result['meanEP'] is not None and result['fillRatePct']>=reference['fillRatePct']-2 and all(
        result[k] is not None and reference[k] is not None and result[k]>=reference[k]-5 for k in ('capture3','capture5'))


def select_config(scores,reference):
    choices=[c for c,r in scores.items() if r.get('status')!='UNTRAINABLE' and admissible(r,reference)]
    if not choices:return None
    best=min(scores[c]['meanEP'] for c in choices)
    ties=[c for c in choices if scores[c]['meanEP']<=best+.005]
    return min(ties,key=lambda c:(c[0],c[1],abs(c[2]-.5),c[2]))


def self_test():
    pp=Preprocessor().fit(np.array([[1.,np.nan],[3.,np.nan]],dtype=float))
    assert np.allclose(pp.mean,[2.,0]) and np.allclose(pp.median,[2.,0])
    before=pp.mean.copy();assert pp.transform([[100.,np.nan]]).shape==(1,4);assert np.array_equal(pp.mean,before)
    x=[(600,0,.1),(601,1,.7),(605,5,.2)]
    assert make_intent(x,5,.5)['intentMinute']==601
    assert make_intent([(600,0,.1),(605,5,.2)],5,.5)['intentReason']=='FORCE_H'
    assert make_intent([(600,0,.1)],5,.5)['intentReason']=='H_CHECKPOINT_UNAVAILABLE'
    assert make_intent(x+[(630,30,1.)],5,.5)==make_intent(x,5,.5)
    ref={'meanEP':.6,'fillRatePct':90.,'capture3':80.,'capture5':80.}
    scores={('M2',5,.5):{**ref,'meanEP':.2},('M1',10,.5):{**ref,'meanEP':.204}}
    assert select_config(scores,ref)==('M1',10,.5)
    assert select_config({('M1',5,.5):{**ref,'fillRatePct':70}},ref) is None
    bad={'quoteAvailable':True,'minute':11};o={'orderedOracle':{'fullSessionEvaluable':True,'status':'OBSERVED_ORDERED_ORACLE','low':100,'high':110,'highMinute':10}}
    assert math.isnan(training_label(bad,o,{'price':101}))
    o['orderedOracle']['highMinute']=20
    assert training_label(bad,o,{'price':102})==1 and training_label(bad,o,{'price':108})==0
    print('PASS: 12 model-policy/preprocessing/label-isolation/selection checks')


def run(output):
    import sklearn,scipy
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    freeze=metric.read_json(ROOT/'docs/evidence/phase57-entry-all-material-v1/PREFIT_FREEZE_R7.json')
    expected=freeze['featureAdmission']
    for file,key in [('features.npy','featuresFileSHA256'),('feature-names.json','featureNamesFileSHA256'),('row-metadata.json.gz','rowMetadataSHA256'),('decision-sources.json.gz','decisionSourcesSHA256')]:
        assert metric.sha256(PRE/file)==expected[key],('PREFIT_HASH',file)
    assert metric.sha256(PRE/'split-manifest.json')==freeze['folds']['splitManifestFileSHA256']
    assert sklearn.__version__=='1.8.0' and np.__version__=='2.3.5' and scipy.__version__=='1.17.0'
    parity=metric.read_json(PRE/'current-one-minute-parity.json')
    assert parity['status']=='PASS' and parity['canonicalRecordSHA256']==freeze['referenceReconstruction']['currentRecordSHA256']
    X=np.load(PRE/'features.npy',mmap_mode='r');rows=metric.read_json(PRE/'row-metadata.json.gz');splits=metric.read_json(PRE/'split-manifest.json')
    assert X.shape==(149900,566) and len(CONFIGS)==36
    index=collections.defaultdict(list)
    for i,r in enumerate(rows):index[r['opportunity']].append(i)
    opportunities,outcomes,record,baseline,t0,immediate,state_records=build_replay_inputs()
    y=np.array([training_label(r,opportunities[r['opportunity']],outcomes.get(r['id'])) for r in rows],dtype=np.float32)
    metric.write_json(out/'training-label-receipt.json',{'labelValid':int(np.isfinite(y).sum()),'labelMissing':int((~np.isfinite(y)).sum()),
        'positive':int(np.nansum(y)),'featureArraySHA256':metric.sha256(PRE/'features.npy'),'freezeSHA256':metric.sha256(ROOT/'docs/evidence/phase57-entry-all-material-v1/PREFIT_FREEZE_R7.json'),
        'labelFeatureIsolation':True,'protectedOpens':0})
    def idx_for(ids,labelled=False):
        ans=np.array([i for oid in ids for i in index[oid]],dtype=int)
        return ans[np.isfinite(y[ans])] if labelled else ans
    def points_for(ids,probs,ii):
        mapping={int(i):float(p) for i,p in zip(ii,probs)}
        return {oid:[(rows[i]['minute'],rows[i]['delay'],mapping[i]) for i in index[oid]] for oid in ids}
    def evaluate_config(ids,points,config):
        name,h,p=config;ans=[]
        for oid in ids:
            z={**make_intent(points[oid],h,p),'horizon':h}
            ans.append(record(oid,z,NAME))
        return ans
    ledger=[];oof=[];fit_count=0;fit_attempts=0;repeat=[];fold_receipts=[]
    for fold in splits['folds']:
        fid=fold['fold'];all_val_ids=[i for part in fold['inner'] for i in part['validation']['opportunityIds']]
        assert len(all_val_ids)==len(set(all_val_ids))
        reference=simple_score([opportunities[i] for i in all_val_ids],[baseline[i] for i in all_val_ids])
        trial_rows={c:[] for c in CONFIGS};failures={};inner_probs={}
        for number,inner in enumerate(fold['inner'],1):
            ti=idx_for(inner['train']['opportunityIds'],True);vi=idx_for(inner['validation']['opportunityIds'])
            assert max(rows[i]['session'] for i in ti)<inner['purgeSession']<min(rows[i]['session'] for i in vi)
            for model_name in ('M1','M2','M3'):
                try:
                    fit_attempts+=1
                    fitted=fit_model(X[ti],y[ti],model_name);fit_count+=1
                    probability=predict(fitted,X[vi]);del fitted;gc.collect()
                    points=points_for(inner['validation']['opportunityIds'],probability,vi)
                    for c in CONFIGS:
                        if c[0]==model_name:trial_rows[c].extend(evaluate_config(inner['validation']['opportunityIds'],points,c))
                    inner_probs[(number,model_name)]=digest(probability.tolist())
                    print(json.dumps({'stage':'INNER_FIT_DONE','outer':fid,'inner':number,'model':model_name,'fitRows':len(ti),'validationRows':len(vi)}),flush=True)
                except ModelUntrainable as err:
                    failures[model_name]=str(err)
                    print(json.dumps({'stage':'INNER_MODEL_UNTRAINABLE','outer':fid,'inner':number,'model':model_name,'error':str(err)}),flush=True)
        scores={}
        for c,recs in trial_rows.items():
            scores[c]={'status':'UNTRAINABLE','reason':failures[c[0]]} if c[0] in failures else simple_score([opportunities[i] for i in all_val_ids],recs)
            assert c[0] in failures or len(recs)==len(all_val_ids)
            ledger.append({'outerFold':fid,'config':list(c),'evaluation':'INNER_VALIDATION_ONLY','summary':scores[c],'reference':reference})
        chosen=select_config(scores,reference)
        test_ids=fold['test']['opportunityIds']; selected_model=None
        if chosen is None:
            recs=[dict(baseline[i]) for i in test_ids]
            for r in recs:r['selectionDisposition']='INNER_NO_ADMISSIBLE_CONFIG__ONE_MINUTE_FALLBACK'
            repeated=[dict(r) for r in recs]
            pred_hash=None
        else:
            ti=idx_for(fold['train']['opportunityIds'],True);vi=idx_for(test_ids)
            assert max(rows[i]['session'] for i in ti)<fold['purgeSession']<min(rows[i]['session'] for i in vi)
            fit_attempts+=1
            selected_model=fit_model(X[ti],y[ti],chosen[0]);fit_count+=1
            probs=predict(selected_model,X[vi]); points=points_for(test_ids,probs,vi)
            pred_hash=digest(probs.tolist())
            metric.write_json(out/f'outer-{fid}-prediction-freeze.json',{'fold':fid,'selectedConfig':list(chosen),
                'trainedThrough':fold['train']['sessions'][-1],'purge':fold['purgeSession'],
                'testOpportunityIds':test_ids,'probabilitiesSHA256':pred_hash,'selectionUsesOuterOutcomes':False})
            with (out/f'outer-{fid}-model.pkl').open('wb') as f:pickle.dump(selected_model,f,protocol=5)
            recs=evaluate_config(test_ids,points,chosen)
            repeat_probs=predict(selected_model,X[vi]);assert np.array_equal(probs,repeat_probs)
            repeated=evaluate_config(test_ids,points_for(test_ids,repeat_probs,vi),chosen)
            checks=0
            for oid,pnt in points.items():
                original=make_intent(pnt,chosen[1],chosen[2])
                for cutoff in (5,10,20):
                    if original['intentDelay'] is not None and original['intentDelay']<=cutoff:
                        changed=[(t,d,q if d<=cutoff else 1-q) for t,d,q in pnt]
                        assert make_intent(changed,chosen[1],chosen[2])==original
                        checks+=1
            repeat.append({'outerFold':fid,'predictionByteIdentical':True,'futureSuffixIntentChecks':checks})
            del selected_model;gc.collect()
        for r in recs:r['outerFold']=fid
        for r in repeated:r['outerFold']=fid
        assert recs==repeated
        oof.extend(recs)
        fold_receipts.append({'outerFold':fid,'selectedConfig':list(chosen) if chosen else None,'testN':len(test_ids),
            'testSource':'LEARNED_OOF' if chosen else 'UNCHANGED_ONE_MINUTE_FALLBACK','predictionSHA256':pred_hash})
        print(json.dumps({'stage':'OUTER_DONE','outer':fid,'chosen':list(chosen) if chosen else None,'N':len(test_ids)}),flush=True)
    current_ids={o['opportunity'] for o in immediate};assert {r['opportunity'] for r in oof}==current_ids and len(oof)==2155
    oof.sort(key=lambda r:r['opportunity']);op=[opportunities[i] for i in sorted(current_ids)]
    one_current=[baseline[i] for i in sorted(current_ids)]
    metric.write_gzip_json(out/'entry-records.json.gz',oof)
    metric.write_json(out/'candidate-freeze-before-final-scorecard.json',{'status':'OOF_STREAM_FROZEN','N':2155,
        'recordsSHA256':digest(oof),'folds':fold_receipts,'noFurtherEntryOptimization':True,'notSingleDeployableRefit':True})
    cards={}
    for name,recs in [('LATEST_R1',oof),('ONE_MINUTE',one_current),('IMMEDIATE',immediate)]:
        card=scorecard.build(op,recs,name,state_records,immediate,'IMMEDIATE')
        metric.write_json(out/(name+'.json'),card);cards[name]=card
        assert card==scorecard.build(op,recs,name,state_records,immediate,'IMMEDIATE'), 'SCORECARD_REPLAY_DIFFERENCE'
    compare=scorecard.canonical.evaluate(op,oof,'LATEST_R1',one_current,'ONE_MINUTE')['baselineComparison']
    metric.write_json(out/'paired-vs-one-minute.json',compare)
    metric.write_json(out/'trial-ledger.json',ledger)
    primary=cards['LATEST_R1']['overall'];base=cards['ONE_MINUTE']['overall']
    ep=primary['entryPosition']['mean']
    preservation={'fillMinus2pp':primary['fillRatePct']>=base['fillRatePct']-2,
        'capture3Minus5pp':primary['capture']['3']['ratePct']>=base['capture']['3']['ratePct']-5,
        'capture5Minus5pp':primary['capture']['5']['ratePct']>=base['capture']['5']['ratePct']-5}
    receipt={'status':'FINITE_NESTED_R1_MEASURED_ENTRY_RESEARCH_STOP','N':2155,'configuredCandidates':36,
        'innerTrialSummaries':len(ledger),'successfulModelFits':fit_count,'fitAttempts':fit_attempts,'outerFolds':fold_receipts,
        'meanEntryPosition':ep,'target25Reached':ep is not None and ep<.25,'stretch15Reached':ep is not None and ep<.15,
        'preservation':preservation,'twoReplayEquality':True,'predictionReplayTests':repeat,
        'sourceKnownAtCertification':'INHERITED_HISTORICAL_LIMITATION_NOT_INDEPENDENTLY_CERTIFIED',
        'notSingleDeployableModel':True,
        'modelCoverageOpportunities':sum(f['testN'] for f in fold_receipts if f['selectedConfig'] is not None),
        'referenceFallbackOpportunities':sum(f['testN'] for f in fold_receipts if f['selectedConfig'] is None),
        'developmentOnly':True,'freshOrOos':False,'automaticPromotion':False,'entryOptimizationStopped':True,
        'modelSelectionWholePipelineRefitReplicated':False,
        'nextStage':'FROZEN_EXIT_RESEARCH_ADAPTER_REQUIRES_VALID_INTEGRATION',
        'safety':scorecard.canonical.SAFETY,'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__}}
    metric.write_json(out/'RESULT_RECEIPT.json',receipt)
    metric.write_json(out/'manifest.json',{p.name:metric.sha256(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json'})
    print(json.dumps(receipt,sort_keys=True),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');p.add_argument('--output')
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.output:run(a.output)
    else:p.error('--output or --self-test required')

if __name__=='__main__':main()
