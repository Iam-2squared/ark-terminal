"""P0 read-only attribution. Standard library only: never loads an Entry model/runtime."""
import argparse
import collections
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path
from datetime import datetime

OUT=Path('docs/evidence/phase57-msh-entry-long-v2-architecture')
CONTRACT=Path('predict/research/phase57-msh-entry-long-v2-architecture-diagnostic-v1.json')
FEAS='docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz'
TRANSFER='docs/evidence/phase57-long-only-current-entry-transfer-v1-events.ndjson.gz'
PATHS='docs/evidence/phase57-long-exit-v345-paired/paths.json.gz'
PREDS='docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/frozen-predictions.ndjson.gz'
FREEZE='docs/evidence/phase57-msh-entry-long-v1-upstream-freeze/manifest.json'
PORT='docs/evidence/phase57-long-capital-integration-v1/measurement.json.gz'
BOT='docs/evidence/phase57-long-portfolio-bottleneck-v1/diagnostic.json'
MAE_NAMES=['SAFE_LOW_ADVERSE','MILD_ADVERSE','MODERATE_ADVERSE','SEVERE_ADVERSE','EXTREME_FAILURE']
MFE_NAMES=['LT1','1_TO_2','2_TO_3','3_TO_5','GE5']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 b=Path(p).read_bytes();b=gzip.decompress(b) if str(p).endswith('.gz') else b
 return [json.loads(x) for x in b.splitlines()] if 'ndjson' in str(p) else json.loads(b)
def stamp(s):return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def q(v,p):
 a=sorted(v)
 if not a:return None
 i=(len(a)-1)*p;lo=math.floor(i);hi=math.ceil(i);return a[lo]+(a[hi]-a[lo])*(i-lo)
def dist(v):
 a=[x for x in v if x is not None]
 return {'n':len(a),'mean':statistics.mean(a) if a else None,'median':statistics.median(a) if a else None,'p05':q(a,.05),'p25':q(a,.25),'p75':q(a,.75),'min':min(a) if a else None,'max':max(a) if a else None}
def perf(v):
 a=[x for x in v if x is not None];g=sum(max(x,0) for x in a);l=-sum(min(x,0) for x in a)
 return {**dist(a),'sum':sum(a),'PF':g/l if l else ('INF' if g else None),'positiveRate':sum(x>0 for x in a)/len(a) if a else None}
def mae_bucket(v):return MAE_NAMES[0 if v>-1 else 1 if v>-2 else 2 if v>-5 else 3 if v>-10 else 4]
def mfe_bucket(v):return MFE_NAMES[0 if v<1 else 1 if v<2 else 2 if v<3 else 3 if v<5 else 4]
def summarize(rs):
 ev=[r for r in rs if r['strict30m']]
 return {'N':len(rs),'strictN':len(ev),'symbols':len({r['symbol'] for r in rs}),
  'net30ReferencePct':perf([r['net30'] for r in ev]),'selectedExitNetPct':perf([r['longNet'] for r in rs]),
  'acceptedPortfolioPnlJpy':perf([r['pnlJpy'] for r in rs]),'mfe':dist([r['mfe'] for r in ev]),'mae':dist([r['mae'] for r in ev]),
  'tail':{str(k):{'n':sum(r['mae']<=k for r in ev),'denominator':len(ev)} for k in [-2,-5,-10]},
  'precision':{str(k):{'hits':sum(r['mfe']>=k for r in ev),'denominator':len(ev)} for k in [1,2,3,5]},
  'mshScore':dist([r['mshScore'] for r in rs]),'selectorScore':dist([r['ridgeScore'] for r in rs]),
  'firstBarAdverse':sum(r['firstBarClose'] is not None and r['firstBarClose']<0 for r in rs),
  'firstBarObserved':sum(r['firstBarClose'] is not None for r in rs)}
def grouped(rs,key):return {str(k):summarize([r for r in rs if r[key]==k]) for k in sorted(set(r[key] for r in rs))}
def delta(a,b):
 if not a or not b:return None
 return sum((x>y)-(x<y) for x in a for y in b)/(len(a)*len(b))
def separation(rs,field):
 ts=[r for r in rs if r['mae']<=-10 and r['x'].get(field) is not None]
 ns=[r for r in rs if r['mae']>-10 and r['x'].get(field) is not None]
 a=[r['x'][field] for r in ts];b=[r['x'][field] for r in ns]
 both=[]
 for s in sorted(set(r['symbol'] for r in ts)&set(r['symbol'] for r in ns)):
  aa=[r['x'][field] for r in ts if r['symbol']==s];bb=[r['x'][field] for r in ns if r['symbol']==s]
  both.append({'symbol':s,'tailN':len(aa),'nonTailN':len(bb),'cliffDelta':delta(aa,bb)})
 return {'tail':dist(a),'nonTail':dist(b),'cliffDelta':delta(a,b),
 'tailInsideNonTailRangeRate':sum(min(b)<=x<=max(b) for x in a)/len(a) if a and b else None,
 'withinSymbol':both,'symbolBalancedDelta':statistics.mean(r['cliffDelta'] for r in both) if both else None,
 'severity':{k:dist([r['x'].get(field) for r in rs if r['maeBucket']==k]) for k in MAE_NAMES},
 'winners':{str(k):dist([r['x'].get(field) for r in rs if r['mfe']>=k]) for k in [3,5]},
 'lowAdverseWinners':{str(k):dist([r['x'].get(field) for r in rs if r['mfe']>=k and r['mae']>-2]) for k in [3,5]},
 'tailWinnerJoint':{str(k):dist([r['x'].get(field) for r in ts if r['mfe']>=k]) for k in [3,5]}}

# Formula/availability inventory only: classifications are provisional, never a feature freeze.
DEFS={
 'ridgeScore':('Frozen Selector Ridge score','frozen Top5 output','decision', 'CORE_CANDIDATE','DIRECT_DUPLICATION'),
 'ridgeRank':('Frozen within-decision Top5 rank','frozen Top5 output','decision','CORE_CANDIDATE','DIRECT_DUPLICATION'),
 'decisionPrice':('Frozen latest accepted minute close; reference only','normalized minute provenance','<=5 minutes age','DIAGNOSTIC_ONLY','price-scale confounding'),
 'timeOfDay':('Decision JST time','frozen schedule','none','STATE_ONLY','Selector time feature'),
 'minutesFromOpen':('Decision wall-clock minutes since09:00; includes lunch','frozen schedule','none','STATE_ONLY','Selector time feature'),
 'segment':('Dated JPX common-equity segment','dated Master via L0/transfer','same session Master','DIAGNOSTIC_ONLY','Selector segment feature; exact Master release clock absent'),
 'liquidityBucket':('Cumulative turnover cross-section tercile at same decision, not daily-final turnover','L1 assignCausalLiquidityBuckets via transfer','observed session prefix + same-time cross-section','DIAGNOSTIC_ONLY','Selector liquidity feature'),
 'directionalMomentum3Pct':('100*(latest completed close/close3 trading bars earlier-1)','feasibility featureAudit','4 exact completed5m bars','OPTIONAL_CANDIDATE','related Selector momentum'),
 'directionalMomentumAccelerationPct':('Momentum3 minus Momentum6; NOT 5m acceleration','feasibility featureAudit','7 exact completed5m bars','OPTIONAL_CANDIDATE','related Selector momentum'),
 'directionalPullback6Pct':('100*(latest close/maxHIGH of latest6 completed bars-1)','feasibility featureAudit','6 exact completed5m bars','OPTIONAL_CANDIDATE','related range/trend; complementary local shape'),
 'relativeVolume5':('Latest5m volume / mean preceding5 bars volume','feasibility featureAudit','6 exact completed5m bars; denominator>0','OPTIONAL_CANDIDATE','related Selector volume; NOT liquidity or spread'),
 'directionalReturnFromOpenPct':('100*(latest close/exact09:00 open-1)','feasibility featureAudit','exact session open and latest slot','OPTIONAL_CANDIDATE','related Selector return'),
 'directionalVwapDistancePct':('Close distance to cumulative HLC3-volume VWAP PROXY','feasibility featureAudit','all regular completed5m slots from09:00; positivevolume','OPTIONAL_CANDIDATE','Selector VWAP related but different formula; NOT turnover VWAP'),
 'minutesSinceFirstSelection':('Wall-clock elapsed from earliest frozen Top5 selection today','historical Top5 lineage','same-session prior selections','STATE_ONLY','Selector persistence'),
 'priorSelectionCount':('Count earlier frozen Top5 events for same symbol-session','historical Top5 lineage','same session only','STATE_ONLY','Selector persistence'),
 'decisionPriceAgeMinutes':('Decision minus observed reference-price minute timestamp','corrected-measurement reference provenance','latest observed minute','STATE_ONLY','already<=5min selection constraint'),
 'hybridReciprocalRank':('1/ridgeRank','feasibility lineage','same decision','REJECT','exact rank redundancy'),
 'direction':('Constant1 LONG','contract','none','REJECT','zero variation'),
 'mshScore':('Saved v1 E[ordinal30m HIGH opportunity class]','frozen predictions; NO inference rerun','same decision; in-sample fitted parameters','DIAGNOSTIC_ONLY','v1 score only, not probability of loss'),
}
UNAVAILABLE={
 'absoluteVolumeState':'Absolute volume values not retained in these event projections; only relativeVolume5.',
 'cumulativeTurnover':'Builder exists but event-level numeric snapshot not retained; liquidityBucket alone is not absolute liquidity.',
 'gapFromPriorClose':'Builder needs previous adjusted close + same-day open; paired event snapshot unavailable.',
 'intradayRange':'L1 formula exists; causal numeric snapshot not retained in event ledger.',
 'recentVolatility':'L1 formula exists; causal numeric snapshot not retained in event ledger.',
 'spreadProxy':'No bid/ask/tick-size or spread snapshot; do not infer spread from LOW/HIGH or nominal price.',
 'recentBarStructure':'No pre-entry raw OHLC vector in derived ledger; use existing momentum/pullback availability only.',
 'marketWideContext':'L1 breadth formula exists; full causal cross-section numeric values not retained here.'}

def run(output=OUT):
 c=read(CONTRACT)
 for p,h in c['sourcePins'].items():assert sha(p)==h,p
 frozen=read(FREEZE)
 for p,h in frozen['evidencePins'].items():assert sha(p)==h,p
 exit_spec=read('docs/evidence/phase57-long-exit-continuation-v1/development-final.json')
 for p,h in {**exit_spec['upstreamPins'],**exit_spec['evidencePins']}.items():assert sha(p)==h,p
 feas=read(FEAS);fmap={r['selectorEventId']:r for r in feas};transfer=read(TRANSFER);tmap={r['selectorEventId']:r for r in transfer}
 pred=read(PREDS);pmap={r['selectorEventId']:r for r in pred};paths=read(PATHS)['events'];byid={r['selectorEventId']:r for r in paths}
 ids=read(frozen['historicalEnterLedger']['path']);assert len(ids)==277
 assert len(feas)==3800 and len(fmap)==3800 and len({r['sessionDate'] for r in feas})==76
 assert [r['selectorEventId'] for r in ids]==[r['selectorEventId'] for r in pred if r['state']=='ENTER']
 saved={r['selectorEventId']:r for r in read('docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/path-diagnostics.json.gz')['events']}
 bot=read(BOT);cov={r['eventId']:r for r in bot['coverage']['perEntry']}
 port=read(PORT)['reports']['EXPOSED_COMMON173_DIAGNOSTIC']['EQUAL_MAX3'];trades={r['eventId']:r for r in port['closedTrades']}
 ex=read('docs/evidence/phase57-long-exit-continuation-v1/replay-ledger.json')
 # Validate decision-time source lineage; never project labels/outcomes into x.
 seen=collections.defaultdict(list)
 for f in feas:
  eid=f['selectorEventId'];t=tmap[eid];at=stamp(f['decisionTimestamp'])
  assert all(f[k]==t[k] for k in ['sessionDate','symbol','decisionPrice','ridgeRank','ridgeScore'])
  assert stamp(t['selectorFeatureAvailableAt'])<=at and stamp(t['selectorFeatureTimestamp'])<=at
  assert 0<=f['decisionPriceAgeMinutes']<=5
  prior=seen[f['symbolSessionId']];assert f['priorSelectionCount']==len(prior)
  assert all(stamp(x)<at for x in prior)
  assert stamp(f['firstSelectionTimestamp'])==(stamp(prior[0]) if prior else at)
  prior.append(f['decisionTimestamp'])
 rows=[]
 for e in ids:
  eid=e['selectorEventId'];f=fmap[eid];t=tmap[eid];pa=byid[eid];h=pa['horizons']['30'];old=saved[eid]
  assert all(pa[k]==v and f[k]==v for k,v in e.items())
  assert h['available']==old['labelable']
  if h['available']:
   assert abs(h['maePct']-old['trueMaePct'])<1e-8 and abs(h['mfePct']-max(0,old['mfePct']))<1e-8
  time=f['decisionTimestamp'][11:16];minute=int(time[:2])*60+int(time[3:])
  x={k:f[k] for k in ['ridgeScore','ridgeRank','decisionPrice','decisionPriceAgeMinutes']}
  x.update({k:v['value'] if v['status']=='AVAILABLE' else None for k,v in f['features'].items()})
  x.update(timeOfDay=time,minutesFromOpen=minute-540,segment=t['segment'],liquidityBucket=t['liquidityBucket'],mshScore=pmap[eid]['expectedClass'])
  ext=ex[eid]['BAR5_TWO_LOWER_CLOSES'];trade=trades.get(eid)
  bars=[b for b in pa['future'] if b['minutes']<=30];mae=h.get('maePct');mfe=h.get('mfePct')
  tail_at=next((i for i,b in enumerate(bars) if not b['missing'] and b['l']<=-10),None)
  later_reclaim=any(not b['missing'] and b['c']>=0 for b in bars[tail_at+1:]) if tail_at is not None else None
  rows.append({'eventId':eid,'symbol':e['symbol'],'sessionDate':e['sessionDate'],'entryTimestamp':f['decisionTimestamp'],
   'timeOfDay':time,'timeGroup':next(k for k,v in c['timingGroups'].items() if time in v),'segment':t['segment'],'liquidityBucket':t['liquidityBucket'],
   'strict30m':h['available'],'missingReason':None if h['available'] else h['reason'],'mae':mae,'mfe':mfe,
   'maeBucket':mae_bucket(mae) if h['available'] else 'UNKNOWN','mfeBucket':mfe_bucket(mfe) if h['available'] else 'UNKNOWN',
   'net30':h['returnPct']-.05 if h['available'] else None,'longNet':ext.get('netPct') if ext['status']=='EXIT_REFERENCE' else None,
   'longStatus':ext['status'],'portfolioPaired':cov[eid]['included'],'pnlJpy':trade['pnlJpy'] if trade else None,
   'portfolioAccepted':trade is not None,'mshScore':pmap[eid]['expectedClass'],'ridgeScore':f['ridgeScore'],'ridgeRank':f['ridgeRank'],
   'firstBarClose':pa['future'][0].get('c') if pa['future'] else None,'laterStrict30mReclaimAfterTail':later_reclaim,
   'strict30mSparseMinuteBars':h.get('sparseMinuteBars'),'intrabarOrdering':h.get('ordering'),'x':x,
   'featureStatuses':{k:v['status'] for k,v in f['features'].items()}})
 ev=[r for r in rows if r['strict30m']];assert len(ev)==181
 joint={a:{b:sum(r['maeBucket']==a and r['mfeBucket']==b for r in ev) for b in MFE_NAMES} for a in MAE_NAMES}
 cuts=[q([r['mshScore'] for r in ev],p) for p in [.25,.5,.75]]
 for r in ev:r['scoreQuartile']='Q'+str(1+sum(r['mshScore']>v for v in cuts))
 score=grouped(ev,'scoreQuartile')
 def monotonic(key,ascending=True):
  vals=[v[key[0]][key[1]] for v in score.values()]
  return all(b>=a if ascending else b<=a for a,b in zip(vals,vals[1:]))
 scoremono={'netReturnMeanIncreasing':monotonic(('net30ReferencePct','mean')),'mfeMeanIncreasing':monotonic(('mfe','mean')),'maeMeanImproving':monotonic(('mae','mean')),
  'tailRateDecreasing':all(b<=a for a,b in zip([v['tail']['-10']['n']/v['strictN'] for v in score.values()],[v['tail']['-10']['n']/v['strictN'] for v in list(score.values())[1:]]))}
 symbols=grouped(rows,'symbol');sp={k:v['acceptedPortfolioPnlJpy']['sum'] for k,v in symbols.items()}
 positive=sorted([s for s,p in sp.items() if p>0],key=lambda s:(-sp[s],s));negative=sorted([s for s,p in sp.items() if p<0],key=lambda s:(sp[s],s))
 top1=positive[0];top3=positive[:3];top5=positive[:5];total=sum(sp.values());gp=sum(sp[s] for s in positive);gl=-sum(sp[s] for s in negative)
 concentration={'top1':top1,'top3':top3,'top5':top5,'symbolNetPnlJpy':sp,'totalPnlJpy':total,
  'uniqueSymbols277':len(symbols),'uniqueAcceptedSymbols':len({t['symbol'] for t in trades.values()}),'profitableSymbols':len(positive),'losingSymbols':len(negative),
  'zeroOrUnacceptedSymbols':[s for s in sp if sp[s]==0],'medianAcceptedSymbolPnlJpy':statistics.median(sp[s] for s in {t['symbol'] for t in trades.values()}),
  'positiveSymbolNetTotalJpy':gp,'negativeSymbolNetTotalAbsJpy':gl,
  'positiveSymbolHHI':sum((sp[s]/gp)**2 for s in positive),'negativeSymbolHHI':sum((sp[s]/gl)**2 for s in negative),
  'profits':{str(k):{'symbols':positive[:k],'pnlJpy':sum(sp[s] for s in positive[:k]),'shareOfNetPnl':sum(sp[s] for s in positive[:k])/total,'shareOfPositiveSymbolPnl':sum(sp[s] for s in positive[:k])/gp} for k in [1,3,5]},
  'losses':{str(k):{'symbols':negative[:k],'pnlJpy':sum(sp[s] for s in negative[:k]),'shareOfNegativeSymbolPnl':-sum(sp[s] for s in negative[:k])/gl} for k in [1,3,5]},
  'priorCashStress':bot['concentration']['stress'],
  'leaveMajorSymbolOut':{s:{'interpretation':'FIXED_QUANTITY_ADDITIVE_DIAGNOSTIC_NOT_CASH_REPLAY','remaining':summarize([r for r in rows if r['symbol']!=s]),'removedPnlJpy':sp[s]} for s in top5}}
 signal={}
 for field in c['descriptiveSignalPanel']:
  signal[field]=separation(ev,field)
  signal[field]['excludeTop1']=separation([r for r in ev if r['symbol']!=top1],field)
  signal[field]['excludeTop3']=separation([r for r in ev if r['symbol'] not in top3],field)
 tail_leader=collections.Counter(r['symbol'] for r in ev if r['mae']<=-10).most_common(1)[0][0]
 for field in c['descriptiveSignalPanel']:
  signal[field]['leaveDominantTailSymbolOutInfluenceDiagnostic']=separation([r for r in ev if r['symbol']!=tail_leader],field)
 concentration['tailCountsBySymbol']=dict(collections.Counter(r['symbol'] for r in ev if r['mae']<=-10))
 concentration['dominantTailSymbol']=tail_leader
 concentration['top1Mechanism']={'allEnterCount':symbols[top1]['N'],'strictCount':symbols[top1]['strictN'],'portfolioAccepted':sum(t['symbol']==top1 for t in trades.values()),'entryPriceCounts':dict(collections.Counter(str(fmap[t['eventId']]['decisionPrice']) for t in trades.values() if t['symbol']==top1)),'positiveExits':sum(t['symbol']==top1 and t['pnlJpy']>0 for t in trades.values()),'grossFlatExits':sum(t['symbol']==top1 and abs(t['netPct']+.05)<1e-8 for t in trades.values()),'perTrade':[dict(t,entryPrice=fmap[t['eventId']]['decisionPrice'],priceChangeJpy=t['exitPrice']-fmap[t['eventId']]['decisionPrice']) for t in trades.values() if t['symbol']==top1]}
 featuregroups={label:{field:dist([r['x'][field] for r in rows if r['symbol'] in syms]) for field in c['descriptiveSignalPanel']} for label,syms in [('TOP1',{top1}),('TOP3',set(top3)),('OTHER',set(symbols)-set(top3))]}
 inventory=[]
 for name,(definition,source,lookback,cl,overlap) in DEFS.items():
  available=sum(r['x'].get(name) is not None for r in rows)
  inventory.append({'name':name,'definition':definition,'source':source,'sourceArtifact':FEAS if name not in ['segment','liquidityBucket','mshScore'] else TRANSFER if name!='mshScore' else PREDS,
   'available277':available,'missing277':277-available,'missingRate':(277-available)/277,'strictAvailable181':sum(r['x'].get(name) is not None for r in ev),
   'timestamp':'decisionTimestamp; normalized historical bar availability<=decision','availableAt':'code-guarded bar-close/decision lineage; per-feature raw timestamp not serialized' if name not in ['segment','mshScore'] else 'dated Master; exact release clock not serialized' if name=='segment' else 'saved prediction from Development-fitted frozen model; no prospective claim',
   'lookback':lookback,'missingSemantics':'null + original status; no fill; no implicit healthy/risky class','sessionDependency':'same session','previousSessionDependency':name in ['ridgeScore','ridgeRank','hybridReciprocalRank','mshScore'],
   'forwardFill':False,'pitStatus':'CONDITIONAL_HISTORICAL_FORMULA_CAUSAL' if name not in ['segment','mshScore'] else 'DATED_MASTER_RELEASE_CLOCK_UNPROVEN' if name=='segment' else 'DIAGNOSTIC_FROZEN_IN_SAMPLE_SCORE',
   'selectorOverlap':overlap,'potentialLeakage':'x excludes outcome columns; inherited Selector universe includes future-label-availability matching and daily-based eligibility. Conditional historical field causality only; not full pipeline PIT certification','complexity':'LOW','preliminaryClassification':cl,
   'tailFailureDirection':signal.get(name,{}).get('cliffDelta'),'winnerDirection':signal.get(name,{}).get('winners','NOT_TESTED_IN_FIXED_PANEL'),
   'crossSymbolConsistency':signal.get(name,{}).get('withinSymbol','NOT_TESTED_IN_FIXED_PANEL')})
 for name,why in UNAVAILABLE.items():
  inventory.append({'name':name,'definition':why,'source':'L1 code inventory only / no matched event snapshot','available277':0,'missing277':277,'missingRate':1,'strictAvailable181':0,
   'timestamp':None,'availableAt':None,'lookback':'NOT_AUDITABLE_FROM_RETAINED_VALUES','missingSemantics':'UNAVAILABLE_DO_NOT_RECONSTRUCT_FROM_FUTURE','sessionDependency':'unknown','previousSessionDependency':name=='gapFromPriorClose','forwardFill':False,
   'pitStatus':'UNKNOWN','selectorOverlap':'possible upstream overlap','potentialLeakage':'using daily-final or future path as substitute prohibited','complexity':'UNKNOWN','preliminaryClassification':'UNKNOWN','tailFailureDirection':None,'winnerDirection':'UNAVAILABLE','crossSymbolConsistency':'UNAVAILABLE'})
 for label,rs in [('TOP1',[r for r in rows if r['symbol']==top1]),('TOP3',[r for r in rows if r['symbol'] in top3]),('OTHER',[r for r in rows if r['symbol'] not in top3])]:
  featuregroups[label]['scoreCalibration']=grouped([r for r in rs if r['strict30m']],'scoreQuartile')
 result={'status':'DIAGNOSTICS_COMPUTED_ARCHITECTURE_REVIEW_REQUIRED','contractSHA':sha(CONTRACT),'sourceHead':c['sourceHead'],'mainAtStart':c['mainAtStart'],'dataset':{'period':frozen['historicalDatasetPeriod'],'sessions':76,'selectorEvents':3800,'enterCount':277,'strict30m':181,'portfolioPaired':173,'equalAccepted':166},
 'identities':{k:frozen[k] for k in ['selectorFreezeCommit','selectorPayloadSHA','selectorRidgeSHA','candidateContractSHA','finalModelSHA','finalScalerSHA','globalBudgetSHA']},
 'all277':summarize(rows),'strict181':summarize(ev),'tailCohorts':grouped(ev,'maeBucket'),'winnerCohorts':grouped(ev,'mfeBucket'),'jointMatrix':joint,
 'extremeRows':[r for r in ev if r['mae']<=-10],'highMfeExtremeMaeCount':sum(r['mae']<=-10 and r['mfe']>=5 for r in ev),
 'scoreQuartileCutpoints':cuts,'scoreQuantiles':score,'scoreMonotonicity':scoremono,'bySymbol':symbols,'concentration':concentration,'featureDistributionByContributorGroup':featuregroups,
 'byTime':grouped(rows,'timeGroup'),'byExactTime':grouped(rows,'timeOfDay'),'bySegment':grouped(rows,'segment'),'byLiquidity':grouped(rows,'liquidityBucket'),
 'withinGroupCalibration':{key:{str(v):grouped([r for r in ev if r[key]==v],'scoreQuartile') for v in sorted(set(r[key] for r in rows))} for key in ['segment','liquidityBucket']},
 'signals':signal,'featureInventory':inventory,'inventoryCounts':{'total':len(inventory),'fullyPitCertifiedForDeployment':0,'conditionalFormulaCausal':sum(r['pitStatus']=='CONDITIONAL_HISTORICAL_FORMULA_CAUSAL' for r in inventory),'unavailable':len(UNAVAILABLE),'datedMasterClockUnproven':1,'diagnosticFrozenScore':1},
 'coverage':{'277':277,'181Strict':181,'173Paired':173,'intersectionStrictAndPaired':sum(r['strict30m'] and r['portfolioPaired'] for r in rows),'excludedReasons':bot['coverage']['reasons'],'strictMissing':dict(collections.Counter(r['missingReason'] for r in rows if not r['strict30m'])),'full277Equity':'UNKNOWN','futureEligibilityAllowedAsEntryFilter':False},
 'inheritedSourceAudit':{'futureAvailabilityMembership':'L1 cross-section returns matchedFeatures filtered by labelKeys. Label creation requires future rows. Frozen3800 identity preserved but upstream membership is outcome-availability conditioned; magnitude not reconstructable from selected ledgers.', 'dailyEligibility':'Daily row validation/corporateActionFlag and adjustmentScale use historical daily metadata; exact pre-decision release provenance not retained. No new current-day final values used as Entry features.', 'volumeMissingDefault':'Inherited minute normalizer maps nonfinite volume/turnover to0; raw missing counts not present. No new substitution here; relative-volume/VWAP/liquidity need raw provenance audit before feature freeze.', 'scope':'17 formula-time causal fields conditional on inherited frozen events, NOT17 fully PIT-certified production predictors.'},
 'rows':rows,'counters':c['counters'],'safety':c['safety']}
 output=Path(output);output.mkdir(parents=True,exist_ok=True)
 for name,data in [('diagnostic.json.gz',result),('feature-inventory.json',inventory)]:
  raw=(json.dumps(data,indent=2,allow_nan=False)+'\n').encode();p=output/name;assert not p.exists();p.write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)
 print(json.dumps({'tailCounts':{k:v['N'] for k,v in result['tailCohorts'].items()},'joint':joint,'strict':result['strict181'],'concentration':{k:concentration[k] for k in ['top1','top3','top5','positiveSymbolHHI','negativeSymbolHHI','profitableSymbols','losingSymbols']},'mono':scoremono,'inventory':result['inventoryCounts']}))
 return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',default=str(OUT));run(a.parse_args().output)
