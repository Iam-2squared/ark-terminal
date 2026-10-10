"""Three predeclared LONG EXIT candidates, fixed277 historical Development only."""
import collections,gzip,hashlib,importlib.util,json,math
from pathlib import Path
from scripts.summarize_phase57_long_exit_paired import dist,rate,concentration

BASE=Path('docs/evidence/phase57-long-exit-continuation-v1')
def runtime():
 p=Path('predict/long-only/phase57_long_exit_continuation_v1.py');sp=importlib.util.spec_from_file_location('long_exit',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def dd(xs):
 equity=peak=0;worst=0
 for x in xs:equity+=x;peak=max(peak,equity);worst=min(worst,equity-peak)
 return worst
def measure(es,results,mode):
 rs=[results[e['selectorEventId']][mode] for e in es];nets=[r['netPct'] for r in rs];loss=[x for x in nets if x<0];wins=[x for x in nets if x>0]
 available=[e['future'][:min(12,e['expectedBars'])] for e in es]
 mfes=[max(0,max(b['h'] for b in rows)) for rows in available];maes=[min(0,min(b['l'] for b in rows)) for rows in available]
 winners={}
 for k in [1,2,3,5]:
  ix=[i for i,x in enumerate(mfes) if x>=k]
  winners[str(k)]={'available':len(ix),'finalNet':dist([nets[i] for i in ix]),'positiveFinal':rate(sum(nets[i]>0 for i in ix),len(ix)),'realizedAtLeastLevel':rate(sum(nets[i]>=k for i in ix),len(ix)),'prematureBeforeFirstTouch':rate(sum(next(b['slot'] for b in available[i] if b['h']>=k)>rs[i]['exitBar'] for i in ix),len(ix))}
 recovered=[i for i,r in enumerate(rs) if r['recovered']];failed=[i for i,r in enumerate(rs) if r['reason']=='BAR5_NO_RECLAIM'];base=[results[e['selectorEventId']]['FIXED12']['netPct'] for e in es];delta=[a-b for a,b in zip(nets,base)];positiveDelta=sorted([max(0,x) for x in delta],reverse=True);sumPos=sum(positiveDelta)
 trade_order=sorted(range(len(es)),key=lambda i:(rs[i]['exitTimestamp'],es[i]['selectorEventId']))
 return {'n':len(es),'netSumPctPoints':sum(nets),'grossSumPctPoints':sum(r['grossPct'] for r in rs),'net':dist(nets),'winRate':rate(len(wins),len(nets)),'profitFactor':sum(wins)/abs(sum(loss)) if loss else None,'loss':dist(loss),'tailMinus10':sum(x<=-10 for x in nets),'ddCommonEntryOrderProxyPctPoints':dd(nets),'ddExitOrderProxyPctPoints':dd([nets[i] for i in trade_order]),'notPortfolioDrawdown':True,'holdingBars':dist([r['exitBar'] for r in rs]),'holdingClockMinutes':dist([r['holdingClockMinutes'] for r in rs]),'exitReasons':dict(collections.Counter(r['reason'] for r in rs)),'availableMfe':dist(mfes),'availableMae':dist(maes),'preExitMae':dist([min(0,min(b['l'] for b in available[i][:r['exitBar']])) for i,r in enumerate(rs)]),'mfeCaptureGross':dist([r['grossPct']/mfes[i] for i,r in enumerate(rs) if mfes[i]>0]),'mfeCaptureUndefined':sum(x<=0 for x in mfes),'givebackPctPoints':dist([mfes[i]-r['grossPct'] for i,r in enumerate(rs)]),'winnerLevels':winners,'dynamic':{'defensive':sum(r['defensive'] for r in rs),'recovered':len(recovered),'bar5Failure':len(failed),'recoveredNet':dist([nets[i] for i in recovered]),'recoveredWinRate':rate(sum(nets[i]>0 for i in recovered),len(recovered)),'failedRecovery':sum(nets[i]<0 for i in recovered),'noReclaimNet':dist([nets[i] for i in failed]),'falseDefensiveExitLaterPositiveFixedClose':sum(base[i]>0 for i in failed)},'pathMaeMinus10CohortFinalNet':dist([nets[i] for i,x in enumerate(maes) if x<=-10]),'savedNetWinnersVsFixed':sum(nets[i]>0 and base[i]<=0 for i in range(len(es))),'lostNetWinnersVsFixed':sum(nets[i]<=0 and base[i]>0 for i in range(len(es))),'netDeltaVsFixedPctPoints':sum(delta),'largestPositiveDeltaRemoved':sum(delta)-max([0,*delta]),'positiveImprovementTopShares':{str(k):sum(positiveDelta[:k])/sumPos if sumPos else None for k in [1,3,5]},'concentration':concentration(es,nets)}

def choose(metrics,contract):
 names=contract['candidates'];components={n:{'tail':-metrics[n]['tailMinus10'],'p05':metrics[n]['net']['p05'],'worst':metrics[n]['net']['min'],'winner3':metrics[n]['winnerLevels']['3']['positiveFinal']['count'],'winner5':metrics[n]['winnerLevels']['5']['positiveFinal']['count'],'pf':metrics[n]['profitFactor'] or 0,'dd':metrics[n]['ddCommonEntryOrderProxyPctPoints'],'median':metrics[n]['net']['median'],'capture':metrics[n]['mfeCaptureGross']['median'] or 0,'concentration':-(metrics[n]['positiveImprovementTopShares']['3'] if metrics[n]['positiveImprovementTopShares']['3'] is not None else 1)} for n in names}
 ranks={n:{k:sum(components[o][k]>v for o in names) for k,v in components[n].items()} for n in names}
 scores={n:sum(contract['selectionWeights'][k]*v for k,v in ranks[n].items()) for n in names}
 best=min(names,key=lambda n:(scores[n],names.index(n)))
 return {'selected':best,'weightedRankLoss':scores,'ranks':ranks,'components':components,'rule':'MIN_WEIGHTED_RANK_LOSS_THEN_PREDECLARED_SIMPLICITY_ORDER','notStatisticalProof':True}

def run(out=BASE):
 c=json.loads((BASE/'contract.json').read_text())
 for p,h in c['pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
 for p,h in json.loads(Path('docs/evidence/phase57-long-exit-v345-paired/contract.json').read_text())['sourcePins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
 d=json.loads(gzip.decompress(Path(c['pathArtifact']).read_bytes()));es=sorted(d['events'],key=lambda e:(e['decisionTimestamp'],e['symbol'],e['selectorEventId']));assert len(es)==277
 old=json.loads(Path(c['ledgerPath']).read_text());by={e['selectorEventId']:e for e in es}
 for r in old:
  for k,v in r.items():assert by[r['selectorEventId']][k]==v
 m=runtime();results={e['selectorEventId']:{mode:m.replay(e,mode) for mode in m.MODES} for e in es}
 paired=[e for e in es if all(r['status']=='EXIT_REFERENCE' for r in results[e['selectorEventId']].values())]
 assert paired,'NO_COMMON_PAIRS'
 metrics={mode:measure(paired,results,mode) for mode in m.MODES};selected=choose(metrics,c)
 cohort={r['selectorEventId']:r['cohort'] for r in json.loads((BASE/'path-diagnostic-ledger.json').read_text())}
 split={g:{mode:measure([e for e in paired if cohort[e['selectorEventId']]==g],results,mode) for mode in m.MODES} for g in sorted(set(cohort.values())) if any(cohort[e['selectorEventId']]==g for e in paired)}
 strictTail=[e for e in es if e['horizons']['30']['available'] and e['horizons']['30']['maePct']<=-10];pairedids={e['selectorEventId'] for e in paired}
 result={'status':'LONG_EXIT_DEVELOPMENT_FINAL_SELECTED_NOT_VALIDATED','historicalExposure':'DIRECT_ENTRY_DEVELOPMENT_IN_SAMPLE_OUTCOME_EXPOSED','entries':277,'pairedN':len(paired),'excludedN':277-len(paired),'pairedIdentities':[e['selectorEventId'] for e in paired],'standaloneAvailability':{mode:sum(results[e['selectorEventId']][mode]['status']=='EXIT_REFERENCE' for e in es) for mode in m.MODES},'censoring':{mode:dict(collections.Counter(results[e['selectorEventId']][mode]['reason'] for e in es if results[e['selectorEventId']][mode]['status']=='CENSORED')) for mode in m.MODES},'metrics':metrics,'cohortSplit':split,'selection':selected,'strict30mMinus10TailCoverage':{'all':len(strictTail),'inPaired':sum(e['selectorEventId'] in pairedids for e in strictTail),'excludedIdentities':[e['selectorEventId'] for e in strictTail if e['selectorEventId'] not in pairedids]},'contractSHA':hashlib.sha256((BASE/'contract.json').read_bytes()).hexdigest(),'v4Dependency':False,'providerRequests':0,'freshConsumption':0,'oosAccess':0,'entryChanges':0,'selectorChanges':0,'safety':c['safety']}
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 for name,value in [('measurement.json',result),('replay-ledger.json',results)]:
  p=out/name;assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps({'pairedN':len(paired),'selection':selected,'metrics':{k:{'net':v['net'],'pf':v['profitFactor'],'delta':v['netDeltaVsFixedPctPoints'],'tail':v['tailMinus10'],'winner3':v['winnerLevels']['3']['positiveFinal'],'winner5':v['winnerLevels']['5']['positiveFinal']} for k,v in metrics.items()}}))
 return result
if __name__=='__main__':run()
