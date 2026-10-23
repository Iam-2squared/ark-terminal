"""Freeze selected saved Development evidence and Capital research handoff."""
import gzip,hashlib,json
from pathlib import Path
from scripts.summarize_phase57_long_exit_paired import dist,rate

B=Path('docs/evidence/phase57-long-exit-continuation-v1')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def freeze():
 m=read(B/'measurement.json');c=read(B/'contract.json');selected=m['selection']['selected'];assert selected=='BAR5_TWO_LOWER_CLOSES'
 d=json.loads(gzip.decompress(Path(c['pathArtifact']).read_bytes()));ids=set(m['pairedIdentities']);es=[e for e in d['events'] if e['selectorEventId'] in ids]
 rows=[e['future'][:min(12,e['expectedBars'])] for e in es]
 coverage={}
 for n in [1,2,3,4,5,6,9,12]:
  eligible=[r for r in rows if len(r)>=n];positive=[r for r in eligible if max(b['h'] for b in r)>0]
  coverage[str(n)]={'n':len(eligible),'meanObservedMfeFractionOfFixedWindow':dist([max(0,max(b['h'] for b in r[:n]))/max(b['h'] for b in r) for r in positive]),'firstHitByBar':{str(k):rate(sum(max(b['h'] for b in r[:n])>=k for r in eligible if max(b['h'] for b in r)>=k),sum(max(b['h'] for b in r)>=k for r in eligible)) for k in [1,2,3,5]}}
 giveback={}
 for lag in [1,2,3,6]:
  xs=[]
  for r in rows:
   hi=max(b['h'] for b in r);i=next(i for i,b in enumerate(r) if b['h']==hi)
   if i+lag<len(r):xs.append(max(0,hi)-r[i+lag]['c'])
  giveback[str(lag)]=dist(xs)
 supplemental={'role':'POST_SELECTION_DIAGNOSTIC_NOT_SELECTION_INPUT','pairedN':len(es),'referenceWindow':'Fixed12/calendar cap, not whole session','mfeFractionsAndHitsByBar':coverage,'givebackAfterHindsightMfeBar':giveback,'notExecutableSignals':True}
 (B/'winner-timing-supplement.json').write_text(json.dumps(supplemental,indent=2)+'\n')
 files=[str(B/p) for p in ['contract.json','measurement.json','replay-ledger.json','path-diagnostic.json','path-diagnostic-ledger.json','winner-timing-supplement.json']]+['predict/long-only/phase57_long_exit_continuation_v1.py','predict/long-only/phase57_long_exit_development_final.py']
 v=m['metrics'][selected]
 final={'schemaVersion':1,'status':m['status'],'policyId':'LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1','selectedMode':selected,'singleCandidate':True,'direction':'LONG','cashEquityOnly':True,'v4Dependency':False,'selectionContractSHA':sha(B/'contract.json'),'evidencePins':{p:sha(p) for p in files},'upstreamPins':read('docs/evidence/phase57-long-exit-v345-paired/contract.json')['sourcePins'],'rules':{'firstCloseNonAdverse':'CONTINUATION; zero is non-adverse','firstCloseAdverse':'DEFENSIVE','reclaim':'completed CLOSE return >=0 by bar5 inclusive; enter CONTINUATION, reset decline streak','noReclaim':'exit at completed bar5 reference close','continuation':'exit after two consecutive strictly lower completed CLOSEs; equal/rising resets','maxHolding':'12 expected trading bars or shorter calendar-known remaining regular slots','costPct':.05,'missing':'CENSOR before exit; do not fill','fillSemantics':'COMPLETED_CLOSE_REFERENCE_ONLY_NOT_GUARANTEED_EXECUTION'},'exposure':'DIRECT_ENTRY_DEVELOPMENT_IN_SAMPLE_OUTCOME_EXPOSED','fixedEntryCount':277,'primaryPairedN':m['pairedN'],'standaloneResultN':m['standaloneAvailability'][selected],'freshValidation':'PENDING','oos':'PENDING_SEALED','officialPass':False,'productionReady':False,'capitalResearchHandoffReady':True,'knownLimitations':['Same exposed data used to design/choose3 candidates; no independent performance claim','Primary common coverage173/277; no replacement; standalone192 not used as comparator','Worst net reference trade still -23.5794%; not a risk guarantee','Largest positive paired improvement removed makes net delta negative','Recovered cohort mean net remains negative','Median net trade remains -0.05%; observed MFE capture median remains0','Closing-price fills/latency/slippage not established; execution adapter required before realistic portfolio claims','Session-end15:25/auction coverage unresolved; not silently changed','DD is unweighted trade-order proxy, not portfolio mark-to-market drawdown'],'developmentMetrics':{'netMean':v['net']['mean'],'pf':v['profitFactor'],'worst':v['net']['min'],'p05':v['net']['p05'],'netDeltaVsFixed':v['netDeltaVsFixedPctPoints'],'largestPositiveDeltaRemoved':v['largestPositiveDeltaRemoved']},'modificationPolicy':'Single Development Final frozen; no automatic retune or promotion. Any change requires a new version and exposed-data disclosure.','freshBudget195Unchanged':True,'safety':c['safety']}
 (B/'development-final.json').write_text(json.dumps(final,indent=2)+'\n');(B/'development-final.sha256').write_text(sha(B/'development-final.json')+'\n')
 print(sha(B/'development-final.json'))
if __name__=='__main__':freeze()
