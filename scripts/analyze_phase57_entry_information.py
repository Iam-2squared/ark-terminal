"""Descriptive eight-field screen. No fitted predictive model or Entry decision changes."""
import collections, gzip, hashlib, json, pathlib, statistics, sys, unittest
FEATURES=['last5CloseLocation','last5UpperWickFraction','trailing30MeanRangePct','trailing15ToPrior15TurnoverRatio','trailing15ObservedMinuteFraction','scoreChangeSincePriorSelection','priorSelectionCount','observedTurnoverVwapDistancePct']
FAMILY=dict(zip(FEATURES,['BAR_SHAPE','BAR_SHAPE','RANGE','TURNOVER','OBSERVABILITY','SELECTION_HISTORY','SELECTION_HISTORY','OBSERVED_VWAP']))
S='docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz'
P='docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/frozen-predictions.ndjson.gz'
L='docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/path-diagnostics.json.gz'
N='docs/evidence/phase57-entry-v2-2-fast-fail/target-ledger.json.gz'
def sha(b): return hashlib.sha256(b).hexdigest()
def read(p):
 b=pathlib.Path(p).read_bytes()
 if str(p).endswith('.gz'): b=gzip.decompress(b)
 if '.ndjson.' in str(p): return [json.loads(x) for x in b.splitlines()]
 return json.loads(b)
def auc(pairs,min_class=2):
 rows=sorted(pairs,key=lambda r:r[0]); pos=sum(y for x,y in rows); neg=len(rows)-pos
 if min(pos,neg)<min_class: return None
 below=0.;u=0.;i=0
 while i<len(rows):
  j=i+1
  while j<len(rows) and rows[j][0]==rows[i][0]: j+=1
  p=sum(y for x,y in rows[i:j]);n=j-i-p
  u+=p*(below+.5*n);below+=n;i=j
 return u/(pos*neg)
def group(symbol): return int.from_bytes(hashlib.sha256(('PHASE57_MSH_LONG_V2_GROUP_V1|'+symbol).encode()).digest(),'big')%5
def target(r,t):
 if t=='profit': return None if r['net'] is None else int(r['net']>0)
 if t=='risk': return None if r['D30'] is None else int(r['D30']>=5)
 if t=='tail10': return None if r['D30'] is None else int(r['D30']>=10)
 return None if r['MFE'] is None else int(r['MFE']>=int(t[-1]))
def panel(rows,field,t,direction=1):
 obs=[r for r in rows if r['values'][field] is not None and target(r,t) is not None]
 pairs=[(direction*r['values'][field],target(r,t)) for r in obs]
 by=collections.defaultdict(list)
 for r in obs: by[r['symbol']].append((direction*r['values'][field],target(r,t)))
 per={s:auc(v) for s,v in by.items()}; eligible=[v for v in per.values() if v is not None]
 positive=[r['values'][field] for r in obs if target(r,t)==1]
 negative=[r['values'][field] for r in obs if target(r,t)==0]
 return {'rows':len(obs),'positive':len(positive),'negative':len(negative),'symbols':len(by),'AUC':auc(pairs),
  'macroSymbolAUC':statistics.mean(eligible) if len(eligible)>=3 else None,'macroEligibleSymbols':len(eligible),'symbolAUC':per,
  'medianPositive':statistics.median(positive) if positive else None,'medianNegative':statistics.median(negative) if negative else None}
def analyze(base,featurefile,output):
 base,featurefile,output=map(pathlib.Path,(base,featurefile,output))
 if output.exists(): raise ValueError('APPEND_ONLY_OUTPUT')
 x=read(featurefile);rules=x['protocol']['candidateRule'];assert x['protocol']['features']==FEATURES
 src=read(base/S);old=read(base/P);labs=read(base/L)['events'];net=read(base/N)
 ids={r['selectorEventId'] for r in src};assert len(ids)==3800 and {r['eventId'] for r in x['events']}==ids
 pred={r['selectorEventId']:r for r in old};lab={r['selectorEventId']:r for r in labs};ns={r['eventId']:r for r in net}
 for k in (pred,lab,ns): assert set(k)==ids
 rows=[]
 for f in x['events']:
  eid=f['eventId'];d=lab[eid]
  rows.append(f|{'v1':pred[eid]['state']=='ENTER','net':ns[eid]['target'],'D30':max(0.,-d['trueMaePct']) if d['labelable'] else None,'MFE':d['mfePct'] if d['labelable'] else None})
 dates=sorted({r['sessionDate'] for r in rows});assert len(dates)==76
 initial=set(dates[:16]);windows=[set(dates[a:a+15]) for a in (16,31,46,61)]
 anchors=[r for r in rows if r['v1']];assert len(anchors)==277
 warm=[r for r in anchors if r['sessionDate'] in initial];held=[r for r in anchors if r['sessionDate'] not in initial]
 summaries=[]
 for name in FEATURES:
  avail=[r for r in anchors if r['values'][name] is not None]
  feature={'name':name,'family':FAMILY[name],'availableAll':sum(r['values'][name] is not None for r in rows),'available277':len(avail),'coverage277':len(avail)/277,
   'missingReasons277':dict(collections.Counter(r['missingReasons'][name] for r in anchors if r['values'][name] is None)),'targets':{}}
  for t in ('profit','risk'):
   training=panel(warm,name,t);a=training['AUC'];direction=None if a is None or a==.5 else (1 if a>.5 else -1)
   direction_used=direction if direction is not None else 1
   overall=panel(held,name,t,direction_used)
   chrono=[panel([r for r in held if r['sessionDate'] in dateset],name,t,direction_used) for dateset in windows]
   hashes=[panel([r for r in held if group(r['symbol'])==g],name,t,direction_used) for g in range(5)]
   removed=panel([r for r in held if r['symbol'] not in {'89180','57590'}],name,t,direction_used)
   checks={'initialDirectionDefined':direction is not None,'anchorCoverage':feature['coverage277']>=rules['anchorCoverageMin'],
    'pairedRows':overall['rows']>=rules['anchorPairRowsMin'],'pairedSymbols':overall['symbols']>=rules['anchorSymbolsMin'],
    'heldAUC':overall['AUC'] is not None and overall['AUC']>=rules['heldOrientedAUROCMin'],
    'chronologicalConsistency':sum(v['AUC'] is not None and v['AUC']>.5 for v in chrono)>=rules['chronologicalPositiveMin'],
    'hashGroupConsistency':sum(v['AUC'] is not None and v['AUC']>.5 for v in hashes)>=rules['hashGroupPositiveMin'],
    'withinSymbolMacro':overall['macroSymbolAUC'] is not None and overall['macroSymbolAUC']>=rules['macroSymbolOrientedAUROCMin'],
    'dominantRemoval':removed['AUC'] is not None and removed['AUC']>=rules['knownDominantSymbolsRemovedAUROCMin']}
   feature['targets'][t]={'warmup16':training,'direction':direction,'held60':overall,'chronological':chrono,'hashGroupPanels':hashes,
    'knownDominantRemoved':removed,'checks':checks,'screenPassed':all(checks.values()),'all3800RawAUC':panel(rows,name,t)['AUC'],
    'supportingMFE3':panel(held,name,'MFE3',direction_used),'supportingMFE5':panel(held,name,'MFE5',direction_used)}
  feature['screenPassed']=any(t['screenPassed'] for t in feature['targets'].values());summaries.append(feature)
 families=sorted({f['family'] for f in summaries if f['screenPassed']})
 verdict='FAST_FAIL_CONTINUE' if len(families)>=rules['minimumIndependentFamiliesToContinue'] else 'FAST_FAIL_KILL'
 result={'verdict':verdict,'scope':x['protocol']['scope'],'protocol':x['protocol'],'sourceHead':x['sourceHead'],
  'featureExportSHA':sha(featurefile.read_bytes()),'counts':{'candidates':len(rows),'anchors':len(anchors),'warmupAnchors':len(warm),'heldAnchors':len(held),
   'strictAnchorObserved':sum(r['D30'] is not None for r in anchors),'netAnchorObserved':sum(r['net'] is not None for r in anchors)},
  'featureResults':summaries,'passingFamilies':families,'sourceRawAudit':x['rawSelectedAudit'],'causalInvarianceChecks':x['realCausalInvarianceChecks'],
  'modelFits':0,'newModelPredictions':0,'providerRequests':0,'freshAccess':0,'oosAccess':0,
  'limitations':['All data have previously been exposed to research; held windows are not Fresh/OOS.',
   'Single-feature association and orientation screen is not incremental model validation.',
   'Same-row samples differ between fields. Missing minutes cannot identify absence of trade vs provider gaps.',
   'Frozen candidate membership has historical future-label-availability conditioning.',
   'Direction selection uses initial16 Development dates; two targets and eight fields are multiple exploratory tests.',
   'Macro-symbol AUC excludes single-class/insufficient support symbols; group panels are descriptive, not retrained OOS.',
   'No order book/tick entitlement/fill quality proof. No new gate, threshold, Entry model or v2.4 created.',
   'KILL rejects progression under this heuristic screen only; it does not establish no predictive information.']}
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({'verdict':verdict,'counts':result['counts'],'passingFamilies':families,'resultSHA':sha(output.read_bytes())}))
 return result
class Tests(unittest.TestCase):
 def test_auc_order(self): self.assertEqual(auc([(0,0),(1,0),(2,1),(3,1)]),1.)
 def test_auc_reversed(self): self.assertEqual(auc([(0,1),(1,1),(2,0),(3,0)]),0.)
 def test_auc_ties(self): self.assertEqual(auc([(1,1),(1,1),(1,0),(1,0)]),.5)
 def test_auc_single_class(self): self.assertIsNone(auc([(1,0),(2,0)]))
 def test_target_unknown(self): self.assertIsNone(target({'net':None},'profit'))
 def test_loss_not_mae(self): self.assertEqual(target({'net':1.,'D30':10},'profit'),1)
 def test_hash_deterministic(self): self.assertEqual(group('89180'),group('89180'))
 def test_families(self): self.assertEqual(FAMILY[FEATURES[0]],FAMILY[FEATURES[1]])
if __name__=='__main__':
 if sys.argv[1:]==['--test']: unittest.main(argv=[sys.argv[0]])
 else: analyze(*sys.argv[1:])
