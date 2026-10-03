"""Availability-only fixed calendar feasibility. Does not compute temporal PASS/performance."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scripts import phase57_temporal_zero_diagnostic as d
s=d.s
BASE=s.ROOT/"docs/evidence/phase57-temporal-feasibility-v1"

def calendar_schedule(days,allowed,intraday):
    # Calendar-only upper bound assumes every allowed day has valid raw bars/positive TR.
    intraday=set(intraday);allowed=set(allowed);warm=0;potential=[]
    for day in days:
        if day not in allowed:warm=0;potential.append(False)
        else:potential.append(day in intraday and warm>=6);warm+=1
    anchors=[i for i in range(59,len(days)) if days[i] in intraday and sum(potential[i-59:i+1])>=30]
    def period(anchor,start=None):
        if start is None:start=next((i for i in range(anchor+6,len(days)) if days[i] in intraday),None)
        if start is None:return None
        end=next((i for i in range(start,len(days)) if sum(potential[start:i+1])>=20),None)
        return (anchor,start,end)
    if not anchors:return {'feasible':False,'reason':'NO_SOURCE_CALENDAR_SUPPORT'}
    first=period(anchors[0])
    if first is None or first[2] is None:return {'feasible':False,'reason':'NO_CALIBRATION_TARGET_SUPPORT'}
    second_anchor=next((i for i in anchors if i>=first[2]),None)
    if second_anchor is None:return {'feasible':False,'reason':'NO_POST_CALIBRATION_SOURCE'}
    second=period(second_anchor)
    if second is None or second[2] is None:return {'feasible':False,'reason':'NO_VALIDATION1_TARGET_SUPPORT'}
    start=next((i for i in range(second[2]+1,len(days)) if days[i] in intraday),None)
    third_anchor=max((i for i in anchors if first[2]<=i<=start-6),default=None) if start is not None else None
    if third_anchor is None:return {'feasible':False,'reason':'NO_VALIDATION2_SOURCE'}
    third=period(third_anchor,start)
    if third[2] is None:return {'feasible':False,'reason':'NO_VALIDATION2_TARGET_SUPPORT','calendarAdditionalEligibleDaysLowerBound':20-sum(potential[start:])}
    rows=[]
    for name,(a,b,c) in zip(['CALIBRATION','VALIDATION1','VALIDATION2'],[first,second,third]):
        rows.append({'name':name,'anchorIndex':a,'trainStartIndex':a-59,'testStartIndex':b,'testEndIndex':c,'trainStart':days[a-59],'computedThrough':days[a]+'T15:30:00+09:00','predictionOrigin':days[a]+'T15:31:00+09:00','testStart':days[b],'testEnd':days[c],'sourceCalendarPositions':60,'sourcePotentialEligible':sum(potential[a-59:a+1]),'targetPotentialEligible':sum(potential[b:c+1]),'targetAllowedSessions':sum(x in intraday for x in days[b:c+1]),'targetCalendarPositions':c-b+1,'embargoExchangePositions':b-a-1})
    assert rows[0]['testEnd']<=rows[1]['computedThrough'][:10] and rows[0]['testEnd']<=rows[2]['computedThrough'][:10]
    assert rows[0]['testEnd']<rows[1]['testStart'] and rows[1]['testEnd']<rows[2]['testStart']
    return {'feasible':True,'rows':rows,'calendarAdditionalDaysLowerBound':0,'method':'Earliest calendar-only 60-position source with30 potentially valid sessions; earliest20-potentially-valid target after embargo5. Mapping completes calibration before both validation origins. Second validation target begins after first target ends; source origin is latest eligible past origin with embargo5. No scoring/window alternatives.','minimality':'Calendar support witness with earliest first/second origins; not a global optimum over unspecified designs. Source windows can include earlier observed portions of previous validation target, but targets are disjoint and mapping is fixed at calibration completion. Independence means disjoint target dates, not iid statistical independence.'}

def run(matrix,output):
    out=Path(output);out.mkdir(parents=True,exist_ok=False);before=d.verify_sources();meta=s.read(Path(matrix)/'metadata.json');arrays=np.load(Path(matrix)/'matrix.npz');p=s.admission.plan();days=meta['sessions'];codes=meta['codes'];allowed=set(p['dailyDevelopment'])|set(p['intradayDevelopment']);schedule=calendar_schedule(days,allowed,p['intradayDevelopment']);assert schedule['feasible']
    protocol=s.read(BASE/'protocol.json');assert schedule==protocol['fixedSchedule'],'SCHEDULE_CHANGED'
    assert len(p['intradayDevelopment'])==144 and len(p['commonHoldout'])==244
    assert before==protocol['sourceHashes']
    assert meta['hashes']==s.invariants()
    assert meta['inputLedger']==s.read(d.OLD/'10_boundary_evidence.json')['inputLedger'],'INPUT_LEDGER_CHANGED'
    assert days==sorted(set(days)) and len(codes)==len(set(codes))
    assert set(r['session'] for r in meta['inputLedger'] if r['kind']=='minute')==set(p['intradayDevelopment'])
    assert set(x['session'] for x in meta['inputLedger'])<=allowed
    for lane in ['daily','intraday']:assert arrays[lane].shape==(len(days),len(codes),len(meta['targets'][lane]))
    assert not set(x['session'] for x in meta['inputLedger'])&set(p['commonHoldout']);assert not set(x['session'] for x in meta['inputLedger'])&set(p['excluded'])
    old={x['symbol']:x for x in s.read(d.OLD/'06_sparse_profiles.json.gz')};rows=[];union=set();candidateunion=set();proof=[]
    for lane,items in meta['targets'].items():
      cv=arrays['cov'].copy()
      if lane=='intraday':cv[:,:,3]=arrays['intraCoverage']
      for k,item in enumerate(items):
        if item['globalStatus'] not in ['USABLE','WATCH']:continue
        data=arrays[lane][:,:,k];eligible=arrays['eligible'][:,:,0 if item['tier']=='daily' else 1].copy()
        if lane=='intraday':eligible &= np.array([day in p['intradayDevelopment'] for day in days])[:,None]
        masks=[];folds=[];mapping_pairs=[]
        for f in schedule['rows']:
          ix=np.arange(f['trainStartIndex'],f['anchorIndex']+1);iy=np.arange(f['testStartIndex'],f['testEndIndex']+1)
          a,b,dr,conf,checks,reasons,ok=d.pair(data,cv,eligible,item,ix,iy,f['anchorIndex']);masks.append(ok)
          # Original mapping pair definition excludes H/M but retains finite x/y + source20 target8.
          fitmask=(a['eff']>=20)&(b['eff']>=8)&(b['n']>=8)&checks['MISSING_NORMALIZED_COMPARISON'];mapping_pairs.append(int(fitmask.sum()))
          folds.append({'period':f['name'],'sourceHM':int(np.isin(conf,['HIGH','MEDIUM']).sum()),'sourceEligibleDays':d.stats(eligible[ix].sum(0)),'targetEligibleDays':d.stats(eligible[iy].sum(0)),'sourceNEff':d.stats(a['eff']),'targetNEff':d.stats(b['eff']),'sourcePeerCohort':int(a['mask'].sum()),'targetPeerCohort':int(b['mask'].sum()),'firstFailureCounts':dict(__import__('collections').Counter(reasons.tolist())),'comparablePairs':int(ok.sum()),'mappingPairs':int(fitmask.sum())})
        joint=np.logical_and.reduce(masks);indices=np.flatnonzero(joint)
        current=np.array([next(r for r in old[c]['traits'] if r['lane']==lane and r['trait_id']==item['id'])['sampleConfidence'] in ['HIGH','MEDIUM'] for c in codes])
        candidate=joint&current
        if item['globalStatus']=='USABLE':
          union.update(codes[j] for j in indices);candidateunion.update(codes[j] for j in np.flatnonzero(candidate))
        proof += [{'symbol':codes[j],'lane':lane,'trait':item['id'],'globalStatus':item['globalStatus'],'currentHM':bool(current[j]),'threePeriodEligibility':True,'temporalReliability':'NOT_SCORED'} for j in indices]
        rows.append({'lane':lane,'trait':item['id'],'globalStatus':item['globalStatus'],'periods':folds,'threePeriodComparableSymbols':int(joint.sum()),'currentHMThreePeriodComparableSymbols':int(candidate.sum()),'calibrationPairSupportAtLeast100AllPeriods':all(x>=100 for x in mapping_pairs),'temporalPass':'NOT_SCORED','formalPromotion':False,'additionalDataForEverySymbolOrTrait':'UNKNOWN; this diagnostic establishes a cohort, not universal support'})
        print(json.dumps({'feasibility':lane+'/'+item['id'],'threePeriodSupport':int(joint.sum())}),flush=True)
    verdict={'calendarFeasible':True,'usableThreePeriodComparableSymbols':len(union),'currentHMUsableThreePeriodComparableSymbols':len(candidateunion),'minimumAdditionalDevelopmentDaysForDemonstratedComparableCohort':0 if union else None,'decision':'READY_TO_PRECOMMIT_REMEASUREMENT_SPEC_ONLY' if union else 'CALENDAR_FEASIBLE_BUT_NO_OBSERVED_COHORT','formalGate':'BLOCKED_UNCHANGED','temporalPass':'NOT_SCORED','warning':'Feasible comparisons are not temporal reliability PASS, not calibrated WATCH, not profitable Entry/EXIT. Existing sample/temporal thresholds remain fixed. New dates/target spans proposed only, never adopted.'}
    s.write(out/'01_calendar_schedule.json',schedule);s.write(out/'02_trait_support.json',rows);s.write(out/'03_verdict.json',verdict);s.gzwrite(out/'04_comparable_cells.json.gz',proof)
    spec={'status':'PROPOSED_NOT_ADOPTED_NOT_REMEASURED','sourceDiagnosticHead':'84e456c49bc47f642c9e4c7312b4510576152ebc','schedule':schedule,'sourceWindow':'60 exchange calendar positions ending at fixed origin; excluded slots NaN, no compressed time; unchanged history reset/scale warm-up','targetWindow':'Frozen calendar ranges shown above, containing26/26/20 authorized sessions and20 calendar-potential eligible observations. Changes target span, not minimum-N. All actual20 eligible-day constraints retained; insufficient cells remain insufficient.','minimumObservations':{'source':20,'sourceConditionalEventSessionsBase':8,'target':8,'minimumSourceNEff':20,'minimumTargetNEff':8,'sourceEligibleDays':20,'targetEligibleDays':20,'nonconditionalSnapshotObservations':20,'conditionalSnapshotObservations':8,'peerFitSymbols':100},'sampleConfidence':s.sample_policy(),'temporalPolicy':s.read(s.BASE/'protocol.json')['temporalPolicy'],'calibration':'Unchanged intercept+slope mapping; fit calibration-period pairs only>=100. availableAt strictly after calibration final close. Freeze artifact and apply only at later validation origins. Separate two validation targets, no fit on validation targets. Pair support is measured now but no mapping or validation scores fitted.','asOf':'All source/peer/normalization artifacts computedThrough at or before source close < prediction origin. Calibration availableAt after first target close < both validation origins. Temporal reliability artifact availableAt after final target closes; cannot be dispatched earlier. Final dictionary snapshots retain same-as-of across lanes.','missing':'No low-confidence substitution, no fabricated priors, NaN gaps retained; old registry/Gate/result unchanged.','frozenSelector':'UNCHANGED','entryExitAllowed':False}
    s.write(out/'05_validation_spec_proposal.json',spec)
    s.write(out/'06_boundary.json',{'sourceHashes':before,'precommitProtocolSHA256':d.hashfile(BASE/'protocol.json'),'authorizedIntradaySessions':len(p['intradayDevelopment']),'firstIntradaySession':min(p['intradayDevelopment']),'lastIntradaySession':max(p['intradayDevelopment']),'intradaySessionsRead':len({r['session'] for r in meta['inputLedger'] if r['kind']=='minute'}),'commonHoldoutCount':len(p['commonHoldout']),'matrixFileSHA256':d.hashfile(Path(matrix)/'matrix.npz'),'metadataSHA256':d.hashfile(Path(matrix)/'metadata.json'),'commonHoldoutAdditionalReads':0,'report19ValidationOosFreshAdditionalReads':0,'newProviderRequests':0,'oldEvidenceUnchanged':True,'safety':s.read(d.BASE/'protocol.json')['safety']})
    assert d.verify_sources()==before
    s.write(out/'manifest.json',{f.name:d.hashfile(f) for f in sorted(out.iterdir())})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--matrix',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.matrix,a.output)
