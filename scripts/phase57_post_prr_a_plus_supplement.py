"""Source-limited time, matching, and feasibility receipts from saved records."""
from __future__ import annotations
import collections,gzip,json,hashlib
from decimal import Decimal
from scripts.phase57_post_prr_a_plus import BASE,OUT,D,S,sha,write,write_rows
from scripts.phase57_post_prr_a_plus_analysis import scope,summarize,sign

def main():
 with gzip.open(OUT/'INTENT_UNIVERSE_ROWS.jsonl.gz','rt') as f:a=[json.loads(x) for x in f]
 all100=[r for r in a if r['world']=='ALL_100']
 bykey={(r['arm'],r['entryId']):r for r in all100}
 byopp=collections.defaultdict(dict)
 for r in all100:
  assert r['arm'] not in byopp[r['opportunityId']]
  byopp[r['opportunityId']][r['arm']]=r
 match=[];classes=collections.Counter()
 for opp,d in sorted(byopp.items()):
  im,r1=d.get('IM'),d.get('R1')
  cls='BOTH_PRIMARY' if im and r1 and im['primary'] and r1['primary'] else 'ONE_PRIMARY' if im and r1 and (im['primary'] or r1['primary']) else 'BOTH_OUTSIDE' if im and r1 else 'IM_ONLY' if im else 'R1_ONLY'
  classes[cls]+=1
  x={'opportunityId':opp,'primaryClass':cls,'IM':im,'R1':r1}
  if im and r1:
   x['entryMinuteR1MinusIM']=r1['entryMinute']-im['entryMinute']
   x['deltaNetPpR1MinusIM']=S(D(r1['deltaNetPp'])-D(im['deltaNetPp'])) if im['deltaNetPp'] is not None and r1['deltaNetPp'] is not None else None
  match.append(x)
 write_rows('ARM_MATCHED_ROWS.jsonl.gz',match)
 write('ARM_MATCHED_ANATOMY.json',{'schema':'phase57-a-plus-arm-match-v1','opportunities':len(match),'classes':dict(classes),'bothArms':sum('IM' in d and 'R1' in d for d in byopp.values()),'oneToOneOnOpportunity':True,'rowFile':'ARM_MATCHED_ROWS.jsonl.gz','notAdditionalIndependentSamples':True,'entryWorlds':'IM and R1 alternative frozen Entry worlds, no redesign'})
 rowsout=[];stats={}
 for arm in ('IM','R1'):
  rs=scope(a,arm,'ALL_100')
  for typ in ('I','E','TIE'):
   z=[r for r in rs if (r['firstIntentKnown'] if typ=='I' else r['provisionalEligibility'] if typ=='E' else r['intentClass']=='SAME_TIME_INTENT_UNRESOLVED')]
   stats[arm+'|'+typ]={'totalN':len(z),'knownN':sum(r['labelKnown'] for r in z),'unknownN':sum(not r['labelKnown'] for r in z),'referenceToFillPriceMoveAvailableN':0,'ccmgFillDelayClockN':dict(collections.Counter('UNKNOWN' if r['ccmgExitMinute'] is None else str(r['ccmgExitMinute']-r['ccmgFirstIntentMinute']) for r in z)),'controlDecisionClassN':dict(collections.Counter(r['controlExitKind'] for r in z))}
   for r in z:
    rowsout.append({'arm':arm,'entryId':r['entryId'],'intentClass':r['intentClass'],'firstIntentMinute':r['ccmgFirstIntentMinute'],'r50DecisionMinute':r['controlDecisionMinute'],'r50DecisionClass':r['controlExitKind'],'r50FillReferenceMinute':r['controlExitMinute'],'ccmgFillReferenceMinute':r['ccmgExitMinute'],'ccmgFillStatus':r['fillStatus'],'ccmgExitPrice':r['ccmgExitPrice'],'r50ExitPrice':r['controlExitPrice'],'freshClosedPriceAtIntent':None,'priceMoveCCMGFromIntentJpy':None,'priceMoveR50FromIntentJpy':None,'deltaJpy':r['deltaPnlJpy'],'gapOrFreshnessAtIntent':'GUARD_ASOF_FLAG_ONLY','ccmgIntentToFillWallMinutes':None if r['ccmgExitMinute'] is None else r['ccmgExitMinute']-r['ccmgFirstIntentMinute'],'ccmgIntentToFillActiveMinutes':None})
 write_rows('INTENT_FILL_ROWS.jsonl.gz',rowsout)
 write('INTENT_FILL_ANATOMY.json',{'schema':'phase57-a-plus-intent-fill-v1','groups':stats,'rowFile':'INTENT_FILL_ROWS.jsonl.gz','referencePriceAtIntent':'BLOCKED_SOURCE; dry trace binary unavailable','A=q*(exitC−Pτ) and B=q*(exitR−Pτ)':'BLOCKED_SOURCE; do not label saved exit difference as slippage','knownExitDelta':'available from paired rows','R50DecisionNotFill':'controlNow 925 is forced decision, not auction fill 930','clock':'wall from saved minute arithmetic; active minutes require calendar contract for rows, not silently substituted'})
 write('REMAINING_UPSIDE_ANATOMY.json',{'schema':'phase57-a-plus-upside-v1','status':'BLOCKED_SOURCE','entryBasedFutureUpsideScalar':'present as futureUpsidePctEvaluatorOnly; is evaluator-only and not post-intent high','P_tau':'missing row-level trace','postIntentPath':'missing authorized row-level path','labelEnd':'not proven from scalar','coverageN':0,'noSubtractionShortcut':True,'required':'per-entry allowed price path, label endpoint, bar high/low/knownAt, first intent with exact minute; preserve intrabar unknown and missing'})
 write('STATE_SIGNAL_DELTA_RESULTS.json',{'schema':'phase57-a-plus-state-association-v1','status':'BLOCKED_SOURCE','intentN':{'IM':376,'R1':343},'provisionalEN':{'IM':370,'R1':339},'stateValueKnownAtIntentN':{'IM':0,'R1':0},'signalActivationKnownAtIntentN':{'IM':0,'R1':0},'guardTracePresenceBooleanN':{'IM':376,'R1':343},'interpretation':'no State/Signal Δ table can be verified from saved boolean; zero present snapshots is not zero historical signal events','notComputed':['State×delta','six signals×delta','State×signal cross','State×milestone/route'],'featureSubstitution':False})
 write_rows('CAUSAL_FEATURE_ROWS.jsonl.gz',({'schema':'phase57-a-plus-causal-row-v1','arm':r['arm'],'entryId':r['entryId'],'intentMinute':r['ccmgFirstIntentMinute'],'entryMinute':r['entryMinute'],'guardTracePresent':r['guardTracePresent'],'runtimeAsOf':r['runtimeAsOf'],'state':None,'signals':None,'certifiedMilestone':None,'freshPriceAtIntent':None,'knownAt':None,'sourceStatus':'GUARD_TRACE_BINARY_UNAVAILABLE; boolean is not feature value'} for r in all100 if r['firstIntentKnown']))
 write('STAGE2_LINEAGE_AUDIT.json',{'schema':'phase57-a-plus-stage2-lineage-v1','existingScore':'fold/score5/score10 and frozen ranks present; descriptive associations allowed','sourceLineageReceipt':'docs/evidence/phase57-prr-numerical-recovery/SOURCE_LINEAGE.json reports features.npy expected=actual SHA 54bf771f6a090eb3e8035f7ee433ca1fbd617c165d77955ab71054b4e259a3fe','featureArrayLocal':False,'foldColumnInSavedRows':True,'stage1ScoreTrainSessionsForEachStage2EvaluationFold':'UNPROVEN','transformerFitAsOf':'UNPROVEN','labelMaturityPurge':'UNPROVEN','status':'NESTED_LINEAGE_UNPROVEN','newFit':0})
 support={}
 for arm in ('IM','R1'):
  for typ in ('ALL','I','E','TIE','NO_INTENT'):
   for route in ('ALL','DEFENSIVE_ELIGIBLE','CONTROL_DEFAULT'):
    z=[r for r in scope(a,arm,'ALL_100') if (typ=='ALL' or typ=='I' and r['firstIntentKnown'] or typ=='E' and r['provisionalEligibility'] or typ=='TIE' and r['intentClass']=='SAME_TIME_INTENT_UNRESOLVED' or typ=='NO_INTENT' and not r['firstIntentKnown']) and (route=='ALL' or r['routeDecision']==route)]
    support[arm+'|'+typ+'|'+route]={**summarize(z),'foldN':dict(collections.Counter(str(r['fold']) for r in z)),'bandN':dict(collections.Counter(r['band5'] for r in z)),'stateSnapshotKnownN':0}
 write('SUPPORT_MATRIX.json',{'schema':'phase57-a-plus-support-v1','rows':support,'notTrainingEligibility':'winner and signs are diagnostics only','minimumSupport':None,'futureSplit':'session-forward only; label maturity and purge unresolved'})
 write('OPTION_B_FEASIBILITY.json',{'schema':'phase57-a-plus-option-b-v1','I_E_K':'I observed, E provisional, K post-outcome; 80 each missing CCMG branch','branchEquivalence':'STATIC_CONTRACT_SUPPORTED_ROW_WITNESS_PARTIAL','runtimeFeatureStateSignal':'BLOCKED_SOURCE','knownSubsetMeasurement':'SUPPORTED_CONDITIONAL_DESCRIPTIVE','fullRiskSetMeasurement':'BLOCKED_160_UNKNOWN_CCMG_OUTCOME','stage2NestedLineage':'UNPROVEN','design':'GO_TO_DESIGN_ONLY_FOR_MISSING_EVIDENCE_AND_CONTRACT_SPEC','experimentReady':'BLOCKED','experimentAuthorized':False,'selectedDevelopment':None,'productionReady':False})
 # Session/symbol gross concentrations are distinct from positive/negative net concentrations.
 with gzip.open(OUT/'GROUP_CONTRIBUTIONS.jsonl.gz','rt') as f:ct=[json.loads(line) for line in f]
 concentration={}
 for name in sorted({r['name'] for r in ct}):
  for axis in ('session','symbol'):
   z=[r for r in ct if r['name']==name and r['axis']==axis]
   sides={}
   for side in ('grossGainJpy','grossLossJpy','positiveNetJpy','negativeNetJpy'):
    values=[(max(D(r['netDeltaJpy']),Decimal(0)) if side=='positiveNetJpy' else max(-D(r['netDeltaJpy']),Decimal(0)) if side=='negativeNetJpy' else D(r[side]),r['value']) for r in z]
    values.sort(key=lambda v:(-v[0],v[1]));total=sum((v for v,k in values),Decimal(0));pos=[(v,k) for v,k in values if v>0]
    cumul=Decimal(0);curve=[]
    for v,k in pos:
     cumul+=v;curve.append({'id':k,'contributionJpy':S(v),'cumulativeFraction':S(cumul/total) if total else None})
    sides[side]={'totalJpy':S(total),'topShares':{str(i):S(sum((v for v,k in pos[:i]),Decimal(0))/total) if total else None for i in (1,3,5,10)},'minimumTo50Pct':next((i+1 for i,r in enumerate(curve) if D(r['cumulativeFraction'])>=Decimal('.5')),None),'curve':curve,'status':'DEFINED' if total else 'NOT_DEFINED_NO_CONTRIBUTION'}
   concentration[name+'|'+axis]=sides
 write('GROUP_CONCENTRATION.json',{'schema':'phase57-a-plus-group-concentration-v1','table':concentration,'grossAndNetKeptSeparate':True,'sourceRowsSha256':sha(OUT/'GROUP_CONTRIBUTIONS.jsonl.gz'),'sortTie':'fixed group identifier ascending after amount'})
 write('MISSING_EVIDENCE_REQUEST.json',{'schema':'phase57-a-plus-missing-evidence-v1','requests':[
  {'path':'docs/evidence/phase57-checkpoint-certified-guard-exit/CHECKPOINT_DRY_TRACE.jsonl.gz','expectedSha256':'7f10f3394ea2429b0135b66ec17bc99a317f74323e2a98d5c2b448ba835493a8','minimum':'719 first-intent rows: now,state,price/currentReturn,highestCertifiedMilestone,floorMarginPp,inputMaxBarEnd,inputMaxKnownAt','blocks':['guard values','Pτ','as-of feature table'],'scope':'only existing permitted Development'},
  {'path':'saved checkpoint market State/Signal snapshot or allowlisted price prefix','expectedSha256':None,'minimum':'row ID, version, six signal values, State, input knownAt and barEnd at each first intent','blocks':['State association','causality tests'],'scope':'Development only; no provider/protected'},
  {'path':'allowed owned price paths + original future-upside label contract','expectedSha256':None,'minimum':'post-intent bars through label endpoint, high/low/knownAt/coverage','blocks':['remaining upside','full reference-to-fill decomposition'],'scope':'Development only; no new fetch'},
  {'path':'stage1 fold/transformer training receipts and label knownAt','expectedSha256':None,'minimum':'train/eval sessions and fit timestamps for each stage2 split','blocks':['nested stage2 design'],'scope':'existing authorized metadata only'},
  {'path':'event ordering and pending ownership witness','expectedSha256':None,'minimum':'same-minute 10 rows and R50/CCMG hidden state before first intent','blocks':['ties','branch equivalence certification'],'scope':'saved evidence; no policy replay'}]})
 print('SUPPLEMENT',len(match),len(rowsout))
if __name__=='__main__':main()
