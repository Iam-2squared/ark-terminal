"""Development-only, post-hoc eligibility diagnosis. Never changes a research gate."""
import argparse, collections, csv, gzip, io, json, hashlib
from pathlib import Path
import numpy as np
from scripts import phase57_sparse_handoff as s

ROOT=s.ROOT
BASE=ROOT/'docs/evidence/phase57-temporal-zero-eligibility-v1'
OLD=s.BASE/'ci-result/measurement'

def stats(x):
    a=np.asarray(x).reshape(-1);finite=a[np.isfinite(a)]
    return {**s.coverage.stats(a), "min":float(finite.min()) if len(finite) else None,"max":float(finite.max()) if len(finite) else None}
def distribution(mask,codes):
    ix=np.flatnonzero(mask)
    return {'symbolTraits':int(len(ix)), 'symbols':int(len(set(codes[i] for i in ix)))}
def hashfile(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify_sources():
    s.invariants()
    for name,h in s.read(OLD/'manifest.json').items():assert hashfile(OLD/name)==h,name
    return {'protocol':hashfile(BASE/'protocol.json'),'oldManifest':hashfile(OLD/'manifest.json'),'registry':hashfile(s.v.BASE/'registry.json')}

def conjuncts(a,b,source_conf,x,y,change):
    return {
        'SOURCE_NOT_HIGH_MEDIUM':np.isin(source_conf,['HIGH','MEDIUM']),
        'SOURCE_NEFF_BELOW_20':a['eff']>=20,
        'TARGET_NEFF_BELOW_8':b['eff']>=8,
        'TARGET_OBSERVATIONS_BELOW_8':b['n']>=8,
        'MISSING_NORMALIZED_COMPARISON':np.isfinite(x)&np.isfinite(y),
        'MISSING_TARGET_OR_SOURCE_POSTERIOR':np.isfinite(change)}

def first_failure(checks):
    n=len(next(iter(checks.values())));reasons=np.full(n,'ELIGIBLE',object);remaining=np.ones(n,bool)
    for label,ok in checks.items():reasons[remaining&~ok]=label;remaining &= ok
    return reasons,remaining

def medium_reasons(a,j,dr):
    # HIGH implies all MEDIUM numerical minima, so MEDIUM conjunct failures explain no H/M.
    p=s.sample_policy()['MEDIUM'];out=[]
    if not a['mask'][j]:out.append('SNAPSHOT_BASE_MASK_FALSE')
    if a['fit'] is None:out.append('PEER_COHORT_BELOW_100')
    for key in ['post','sd','peer','weight']:
        if not np.isfinite(a[key][j]):out.append('MISSING_'+key.upper())
    for key,limit in [('n',p['nSessionsMin']),('eff',p['nEffMin']),('weight',p['shrinkWeightMin']),('coverage',p['coverageMin'])]:
        if not np.isfinite(a[key][j]) or a[key][j]<limit:out.append({'n':'INSUFFICIENT_SESSIONS','eff':'INSUFFICIENT_NEFF','weight':'INSUFFICIENT_SHRINK_WEIGHT','coverage':'SOURCE_COVERAGE_BELOW_0_5'}[key])
    ref=a['reference']
    if not ref or ref<=0 or not np.isfinite(a['sd'][j]) or a['sd'][j]/ref>p['posteriorSdOverReferenceSdMax']:out.append('POSTERIOR_UNCERTAINTY_UNAVAILABLE_OR_HIGH')
    if dr[j] is True:out.append('DRIFT_TRUE')
    return out

def pair(data,cv,eligible,item,train,test,anchor):
    a=s.snapshot(data,cv,eligible,item,train);b=s.snapshot(data,cv,eligible,item,test)
    dr=s.drift(data,item['transform'],anchor);conf=[s.sample(a,j,dr[j]) for j in range(data.shape[1])]
    ref=a['reference'];nan=np.full(data.shape[1],np.nan);pb=nan.copy()
    if a['fit'] is not None:
        f=a['fit'];pb=np.column_stack([np.ones(len(nan)),(s.v.mean(cv[test])-f['mean'])/f['sd']])@f['beta']
    x=(a['post']-a['peer'])/ref if ref and ref>0 else nan.copy()
    y=(b['value']-pb)/ref if ref and ref>0 else nan.copy()
    ch=(b['post']-a['post'])/ref if ref and ref>0 else nan.copy()
    checks=conjuncts(a,b,conf,x,y,ch);reason,ok=first_failure(checks)
    return a,b,dr,conf,checks,reason,ok

def date_bounds(data,indices,sessions):
    valid=np.isfinite(data[indices]);first=np.argmax(valid,axis=0);last=len(indices)-1-np.argmax(valid[::-1],axis=0)
    return [(sessions[indices[f]],sessions[indices[l]]) if valid[:,j].any() else (None,None) for j,(f,l) in enumerate(zip(first,last))]

def run(matrix,output):
    before=verify_sources();out=Path(output);out.mkdir(parents=True,exist_ok=False)
    meta=s.read(Path(matrix)/'metadata.json');z=np.load(Path(matrix)/'matrix.npz');sessions=meta['sessions'];codes=meta['codes'];n=len(codes);p=s.admission.plan()
    assert len(codes)==len(set(codes)) and sessions==sorted(set(sessions))
    assert not (set(x['session'] for x in meta['inputLedger'])&set(p['commonHoldout']))
    assert not (set(x['session'] for x in meta['inputLedger'])&set(p['excluded']))
    schedule=s.folds(sessions,p);profiles={x['symbol']:x for x in s.read(OLD/'06_sparse_profiles.json.gz')}
    assert set(profiles)==set(codes)
    saved={(r['lane'],r['trait'],r['fold']):r for r in s.read(OLD/'02_walk_forward.json')}
    old_summary={(r['lane'],r['trait']):r for r in s.read(OLD/'01_trait_coverage.json')}
    usable=[];watch=[];all_period=[];all_cf=[];flatcodes=[];flatfamilies=[];flatcandidate=[];flatfolds=[[],[],[]];cell_reasons=[]
    fields=['lane','trait','symbol','fold','currentCandidate','trainStart','computedThrough','predictionOrigin','targetStart','targetEnd','sourceFirst','sourceLast','targetFirst','targetLast','sourceNSessions','sourceNEff','sourceEligibleSessions','sourceCoverage','sourceBaseMask','sourcePeerCohort','sourceConfidence','sourceReasons','targetNSessions','targetNEff','targetEligibleSessions','targetBaseMask','targetPeerCohort','targetPosteriorFinite','eligible','firstFailure','allFailedConjuncts']
    with (out/'symbol-trait-fold.csv.gz').open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz,io.TextIOWrapper(gz,encoding='utf-8',newline='') as f:
      writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
      for lane,items in meta['targets'].items():
       cv=z['cov'].copy()
       if lane=='intraday':cv[:,:,3]=z['intraCoverage']
       for k,item in enumerate(items):
        if item['globalStatus'] not in ['USABLE','WATCH']:continue
        data=z[lane][:,:,k];tier=0 if item['tier']=='daily' else 1;eligible=z['eligible'][:,:,tier].copy()
        if lane=='intraday':eligible &= np.array([d in p['intradayDevelopment'] for d in sessions])[:,None]
        current=[next(r for r in profiles[c]['traits'] if r['lane']==lane and r['trait_id']==item['id']) for c in codes]
        candidate=np.array([r['globalStatus']=='USABLE' and r['sampleConfidence'] in ['HIGH','MEDIUM'] for r in current])
        folds=[];masks=[]
        for fi,fold in enumerate(schedule):
         train,test=fold['train'],fold['test'];a,b,dr,conf,checks,reasons,ok=pair(data,cv,eligible,item,train,test,fold['end'])
         assert int(ok.sum())==saved[lane,item['id'],fi]['eligibleHMSymbols'],'ORIGINAL_ELIGIBILITY_MISMATCH'
         source_days=eligible[train].sum(0);target_days=eligible[test].sum(0)
         sourcebounds=date_bounds(data,train,sessions);targetbounds=date_bounds(data,test,sessions)
         overlapping=collections.Counter();source_fail=collections.Counter();exclusive=collections.Counter(reasons.tolist())
         for label,q in checks.items():overlapping[label]=int((~q).sum())
         constraints={'SOURCE_ELIGIBLE_SESSIONS_BELOW_20':source_days>=20,'SOURCE_TRAIT_OBSERVATIONS_BELOW_MIN':a['n']>=(8 if item['id'] in s.v.CONDITIONAL else 20),'SOURCE_COVARIATES_MISSING':np.all(np.isfinite(s.v.mean(cv[train])),axis=1),'SOURCE_PEER_COHORT_BELOW_100':np.full(n,a['fit'] is not None),'SOURCE_COVERAGE_BELOW_0_5':a['coverage']>=.5,**checks}
         deep_reason,_=first_failure(constraints)
         counterfactual={label:int(np.logical_and.reduce([v for key,v in checks.items() if key!=label]).sum()) for label in checks}
         # Explicit8 target support vs the inherited target snapshot20/posterior guard.
         target_explicit=(b['eff']>=8)&(b['n']>=8)
         base_without=np.isin(conf,['HIGH','MEDIUM'])&(a['eff']>=20)&target_explicit
         fr={'fold':fi+1,'trainStart':sessions[train[0]],'trainEnd':fold['anchor'],'predictionOrigin':fold['anchor']+'T15:31:00+09:00','computedThrough':fold['anchor']+'T15:30:00+09:00','testStart':fold['testStart'],'testEnd':fold['testEnd'],'sourceWindowPositions':len(train),'targetWindowPositions':len(test),'sourceAuthorizedSessions':sum(sessions[i] in (set(p['dailyDevelopment'])|set(p['intradayDevelopment'])) for i in train),'sourceTraitSessions':stats(a['n']),'sourceEligibleSessions':stats(source_days),'sourceNEff':stats(a['eff']),'sourceCoverage':stats(a['coverage']),'sourceBaseMaskCount':int(a['mask'].sum()),'sourcePeerFit':a['fit'] is not None,'sourceConfidence':dict(collections.Counter(conf)),'targetTraitSessions':stats(b['n']),'targetEligibleSessions':stats(target_days),'targetNEff':stats(b['eff']),'targetBaseMaskCount':int(b['mask'].sum()),'targetPeerFit':b['fit'] is not None,'targetExplicit8Count':int(target_explicit.sum()),'sourceHMAndExplicitTarget8':int(base_without.sum()),'targetPosteriorFinite':int(np.isfinite(b['post']).sum()),'eligibleSymbols':int(ok.sum()),'currentCandidatesEligible':int((ok&candidate).sum()),'firstFailureExclusive':dict(exclusive),'deepFirstFailureExclusive':dict(collections.Counter(deep_reason.tolist())),'allFailedConjunctsOverlapping':dict(overlapping),'singleConditionRemovalSupportOnly':counterfactual}
         for j,c in enumerate(codes):
          sr=medium_reasons(a,j,dr);source_fail.update(sr)
          writer.writerow({'lane':lane,'trait':item['id'],'symbol':c,'fold':fi+1,'currentCandidate':bool(candidate[j]),'trainStart':sessions[train[0]],'computedThrough':fr['computedThrough'],'predictionOrigin':fr['predictionOrigin'],'targetStart':fold['testStart'],'targetEnd':fold['testEnd'],'sourceFirst':sourcebounds[j][0],'sourceLast':sourcebounds[j][1],'targetFirst':targetbounds[j][0],'targetLast':targetbounds[j][1],'sourceNSessions':int(a['n'][j]),'sourceNEff':a['eff'][j],'sourceEligibleSessions':int(source_days[j]),'sourceCoverage':a['coverage'][j],'sourceBaseMask':bool(a['mask'][j]),'sourcePeerCohort':int(a['mask'].sum()),'sourceConfidence':conf[j],'sourceReasons':'|'.join(sr),'targetNSessions':int(b['n'][j]),'targetNEff':b['eff'][j],'targetEligibleSessions':int(target_days[j]),'targetBaseMask':bool(b['mask'][j]),'targetPeerCohort':int(b['mask'].sum()),'targetPosteriorFinite':bool(np.isfinite(b['post'][j])),'eligible':bool(ok[j]),'firstFailure':deep_reason[j],'allFailedConjuncts':'|'.join(key for key,q in checks.items() if not q[j])})
         fr['sourceConfidenceReasonsOverlapping']=dict(source_fail);folds.append(fr);masks.append(ok);all_period.append({'lane':lane,'trait':item['id'],**fr})
        last=len(sessions)-1;anchor=last-25;train=np.arange(anchor-59,anchor+1);test=np.arange(anchor+6,anchor+26)
        ca,cb,cd,cc,cq,cr,co=pair(data,cv,eligible,item,train,test,anchor)
        all_cf.append({'lane':lane,'trait':item['id'],'fixedEndpointOnly':True,'trainStart':sessions[train[0]],'anchor':sessions[anchor],'testStart':sessions[test[0]],'testEnd':sessions[test[-1]],'sourceConfidence':dict(collections.Counter(cc)),'sourcePeerFit':ca['fit'] is not None,'targetPeerFit':cb['fit'] is not None,'pairSupport':int(co.sum()),'currentCandidatesWithPairSupport':int((co&candidate).sum()),'rawMinimum8TargetCount':int(((cb['n']>=8)&(cb['eff']>=8)).sum()),'noTemporalPassComputed':True})
        finite=np.isfinite(data);counts=finite.sum(0);bounds=date_bounds(data,np.arange(len(sessions)),sessions)
        detail={'lane':lane,'trait':item['id'],'availableSymbolSessions':int(finite.sum()),'availableSessions':int(finite.any(1).sum()),'anyObservedSymbols':int((counts>0).sum()),'perSymbolAvailableSessions':stats(counts),'firstUsableDate':min((a for a,b in bounds if a),default=None),'lastUsableDate':max((b for a,b in bounds if b),default=None),'currentHighMedium':int(candidate.sum()),'folds':folds,'comparableFirstTwo':int((masks[0]&masks[1]).sum()),'comparableAllThree':int(np.logical_and.reduce(masks).sum()),'requiredMinimum':{'sourceEligibleSessions':20,'sourceObservations':8 if item['id'] in s.v.CONDITIONAL else 20,'sourceHMEffectiveSessions':20,'sourceHMCoverage':.5,'sourceHMObservedSessions':20,'targetExplicitNEff':8,'targetExplicitObservations':8,'targetSnapshotEligibleSessions':20,'targetSnapshotObservations':8 if item['id'] in s.v.CONDITIONAL else 20,'peerCohort':100,'requiredFolds':3},'finalTemporalStatus':old_summary[lane,item['id']]['temporalReliability']}
        if item['globalStatus']=='USABLE':
         usable.append(detail);flatcodes+=codes;flatfamilies += [lane+'/'+item['id']]*n;flatcandidate.extend(candidate)
         for fi in range(3):flatfolds[fi].extend(masks[fi])
        else:
         old=next(r for r in s.read(OLD/'03_watch_mapping.json') if r['lane']==lane and r['trait']==item['id'])
         complete=schedule[0]['testEnd'];remaining=[d for d in p['intradayDevelopment'] if d>complete]
         watch.append({**detail,'calibrationFitSourceStart':folds[0]['trainStart'],'calibrationTargetStart':folds[0]['testStart'],'nominalCalibrationCompletion':complete+'T15:30:00+09:00','actualMappingConstructed':old['mappingFold1'] is not None,'earliestActualMappingAvailableAt':complete+'T15:30:00+09:00' if old['mappingFold1'] is not None else None,'firstTimeOrderingPermitsPrediction':complete+'T15:31:00+09:00','earliestNextAuthorizedSession':remaining[0] if remaining else None,'remainingAuthorizedIndependentSessions':len(remaining),'remainingDisjoint20SessionBlocksCalendarUpperBound':len(remaining)//20,'validationOrigins':[f['predictionOrigin'] for f in folds[1:]],'period2TimingValid':s.calibration_available(complete,schedule[1]['anchor']),'period3TimingValid':s.calibration_available(complete,schedule[2]['anchor']),'currentDesignPossible':False,'reason':'INSUFFICIENT_CALIBRATION_PAIRS_AND_PREDICTION_ORIGIN_BEFORE_CALIBRATION' if old['mappingFold1'] is None else 'PREDICTION_ORIGIN_BEFORE_CALIBRATION','savedMapping':old})
        print(json.dumps({'diagnosed':lane+'/'+item['id'],'foldSupport':[int(m.sum()) for m in masks],'endpointSupport':int(co.sum())}),flush=True)
    flatcandidate=np.array(flatcandidate,bool);fm=[np.array(x,bool) for x in flatfolds];total=len(flatcodes)
    stages=[('ALL_USABLE_SYMBOL_TRAITS',np.ones(total,bool)),('CURRENT_HIGH_MEDIUM',flatcandidate),('TEMPORAL_TEST_TARGET',flatcandidate),('PERIOD1_ELIGIBLE',flatcandidate&fm[0]),('PERIOD1_AND_PERIOD2_COMPARABLE',flatcandidate&fm[0]&fm[1]),('ALL_THREE_PERIODS_COMPARABLE',flatcandidate&fm[0]&fm[1]&fm[2])]
    stages += [(key,stages[-1][1]) for key in ['TEMPORAL_COMPUTABLE','TEMPORAL_PASS','HANDOFF_ELIGIBLE']]
    funnel=[];previous=None
    for label,mask in stages:
        rec={'stage':label,**distribution(mask,flatcodes),'pctOfCandidateSymbols':100*len(set(flatcodes[i] for i in np.flatnonzero(mask)))/2533,'pctOfCandidateCells':100*int(mask.sum())/max(1,int(flatcandidate.sum())),'byFamily':dict(collections.Counter(flatfamilies[i] for i in np.flatnonzero(mask)))}
        if previous is not None:rec['droppedCells']=int((previous&~mask).sum());rec['droppedSymbols']=distribution(previous,flatcodes)['symbols']-rec['symbols']
        funnel.append(rec);previous=mask
    assert funnel[1]['symbols']==2533
    assert all(sum(old_summary[x['lane'],x['trait']]['temporalReliability'].get(k,0) for k in ['PASS','FAIL'])==0 for x in usable)
    independent=[{'period':i+1,**distribution(flatcandidate&fm[i],flatcodes)} for i in range(3)]
    # Raw-free calendar feasibility, without opening sealed dates.
    allowed=set(p['dailyDevelopment'])|set(p['intradayDevelopment']);longest=runlength=0
    for day in sessions:
        runlength=runlength+1 if day in p['intradayDevelopment'] else 0;longest=max(longest,runlength)
    calendar_audit={'folds':[{key:val for key,val in f.items() if key not in ['train','test']} for f in schedule],'longestConsecutiveIntradayAuthorizedRun':longest,'strictNonoverlapThreeTargetCalendarLowerBound':125,'calendarOnlyAdditionalLowerBound':max(0,125-longest),'warning':'125 is a hypothetical uninterrupted calendar support bound (60+5+3*20), NOT an approved new spec or a guarantee for event traits/nEff. Exact additional data requirement is not identifiable before resolving eligibility/design. No acquisition.','excludedDatesCount':len(meta['excludedNoPayloadRead']),'historyReset':'Collector clears 10-session histories at each excluded exchange date, then requires prior true-range scale>=5. No excluded payload read.'}
    s.write(out/'01_funnel.json',{'sequential':funnel,'independentPeriods':independent,'firstZeroStage':'PERIOD1_ELIGIBLE','candidateSymbols':2533,'candidateSymbolTraits':int(flatcandidate.sum()),'finalInsufficientCandidateCells':int(flatcandidate.sum()),'finalPass':0,'finalFail':0,'percentDenominator':'Current candidates except first all-universe reference row; may exceed100 for universe row'})
    s.write(out/'02_usable9.json',usable);s.write(out/'03_watch23.json',watch);s.write(out/'04_period_reasons.json',all_period);s.write(out/'05_counterfactual_support_only.json',all_cf);s.write(out/'06_calendar.json',calendar_audit)
    s.write(out/'07_boundary.json',{'sourceHashes':before,'inputLedger':meta['inputLedger'],'commonHoldoutIntersection':[],'excludedIntersection':[],'protectedPayloadReads':0,'providerRequests':0,'oldEvidenceUnchanged':True,'exposureLedger':'UNCHANGED; historical REPORT19 derived exposure retained, no claim of never viewed','safety':s.read(BASE/'protocol.json')['safety']})
    assert verify_sources()==before
    s.write(out/'manifest.json',{f.name:hashfile(f) for f in sorted(out.iterdir())})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--matrix',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.matrix,a.output)
