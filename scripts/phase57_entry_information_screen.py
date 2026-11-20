"""Entry information screen: eight predeclared causal fields; no fitting or scoring."""
import collections, datetime as dt, gzip, hashlib, json, math, pathlib, sys, unittest

SOURCE_HEAD = '7599df41199a8c4d1ea86d5f3cb595edd599dd21'
FEAT = 'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz'
PRIOR = 'docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/path-diagnostics.json.gz'
OUTCOMES = 'docs/evidence/phase57-entry-v2-3-fast-fail/label-ledger.json.gz'
FEATURE_ORDER = ['last5CloseLocation', 'last5UpperWickFraction', 'trailing30MeanRangePct',
 'trailing15ToPrior15TurnoverRatio', 'trailing15ObservedMinuteFraction',
 'scoreChangeSincePriorSelection', 'priorSelectionCount', 'observedTurnoverVwapDistancePct']
PROTOCOL = {
 'id':'PHASE57_ENTRY_INFORMATION_SCREEN_V1','sourceHead':SOURCE_HEAD,
 'features':FEATURE_ORDER,'maxCandidateFields':8,'newFit':0,'newModelPredictions':0,
 'targets':['frozen_EXIT_net_gt_0','strict_D30_ge_5'],
 'supportingOutcomes':['MFE_ge_3','MFE_ge_5','D30_ge_10'],
 'scope':'HISTORICAL_CONDITIONAL_UNIVERSE_DESCRIPTIVE_SCREEN_NOT_ENTRY_PERFORMANCE',
 'baseline':'Frozen v1 anchors; all3800 secondary; same-row outcomes only',
 'chronology':'Initial16 dates set feature direction only. Next15 dates x4 descriptive panels.',
 'symbolGroups':'sha256(PHASE57_MSH_LONG_V2_GROUP_V1|symbol) mod 5; no model fits',
 'candidateRule':{'anchorCoverageMin':0.5,'anchorPairRowsMin':50,'anchorSymbolsMin':15,
  'heldOrientedAUROCMin':0.575,'chronologicalPositiveMin':3,'hashGroupPositiveMin':3,
  'macroSymbolOrientedAUROCMin':0.55,'knownDominantSymbolsRemovedAUROCMin':0.55,
  'minimumClassRowsPerPanel':2,'minimumIndependentFamiliesToContinue':2},
 'gateMeaning':'Heuristic triage, not significance/power/economic guarantee. Direction chosen on first16 only.',
 'riskOutcomeTradeoff':'Report MFE associations separately; no inferred winner-loss claims from risk alone.',
 'missing':'NULL+reason, no fills. Absent minute is unknown, not zero-volume trade.',
 'tickRatio':'NOT_TESTED; dated tick-table classification not audited. No inverse-price substitution.',
 'multipleTesting':'Eight predeclared fields, two targets; screening remains exposed Development.',
 'failScope':'KILL applies to this field panel only; never means Entry improvement impossible.',
 'safety':dict.fromkeys(['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed',
 'rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed',
 'automaticPromotionAllowed','productionUpdateAllowed','transmitted'],False)}

def sha(b): return hashlib.sha256(b).hexdigest()
def read(p):
 b=pathlib.Path(p).read_bytes()
 return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def val(row,*keys):
 for k in keys:
  x=row.get(k)
  if x is None or isinstance(x,bool) or (isinstance(x,str) and not x.strip()): continue
  try: z=float(x)
  except (ValueError,TypeError): continue
  if math.isfinite(z): return z
 return None

def regular(m): return 540<=m<690 or 750<=m<930

def aggregate(rows,date,symbols):
 by=collections.defaultdict(dict); stats=collections.Counter()
 for r in rows:
  if str(r.get('Date',r.get('date',''))) != date: raise ValueError('UNAUTHORIZED_DATE')
  s=str(r.get('Code',r.get('code',r.get('symbol','')))).strip().upper()
  if s not in symbols: continue
  t=str(r.get('Time',r.get('time','')))[:5]
  try: hh,mm=map(int,t.split(':')); minute=hh*60+mm
  except (ValueError,TypeError): stats['invalidTime']+=1; continue
  if not regular(minute): continue
  o,h,l,c=[val(r,*names) for names in [('O','Open','open'),('H','High','high'),('L','Low','low'),('C','Close','close')]]
  if any(x is None or x<=0 for x in (o,h,l,c)) or h<max(o,c) or l>min(o,c):
   stats['invalidOHLC']+=1;continue
  v=val(r,'Vo','Volume','volume'); a=val(r,'Va','Turnover','turnover')
  if v is not None and v<0: v=None
  if a is not None and a<0: a=None
  stats['observedRows']+=1; stats['missingVolume']+=v is None; stats['missingTurnover']+=a is None
  z={'m':minute,'o':o,'h':h,'l':l,'c':c,'v':v,'a':a}
  if minute in by[s] and by[s][minute]!=z: raise ValueError('DUPLICATE_CONFLICT')
  by[s][minute]=z
 return by,dict(stats)

def snapshot(minutes,decision,price,score,prior_score,count):
 # Input may include entire day, but every feature sees this strictly causal prefix only.
 prefix=[r for m,r in sorted(minutes.items()) if m+1<=decision]
 buckets=collections.defaultdict(list)
 for r in prefix:
  k=(r['m']//5)*5
  if k+5<=decision: buckets[k].append(r)
 bars={k:{'o':rs[0]['o'],'h':max(r['h'] for r in rs),'l':min(r['l'] for r in rs),
          'c':rs[-1]['c'],'v':None if any(r['v'] is None for r in rs) else sum(r['v'] for r in rs),
          'a':None if any(r['a'] is None for r in rs) else sum(r['a'] for r in rs),'n':len(rs)}
       for k,rs in buckets.items()}
 result={k:None for k in FEATURE_ORDER}; why={k:'NOT_AVAILABLE' for k in FEATURE_ORDER}
 def put(k,v,reason=None):
  if v is not None and not math.isfinite(v): raise ValueError('NONFINITE_FEATURE')
  result[k]=v;why[k]=reason
 last=bars.get(decision-5)
 if last:
  span=last['h']-last['l']
  put('last5CloseLocation',(last['c']-last['l'])/span if span>0 else None,'ZERO_RANGE' if span==0 else None)
  put('last5UpperWickFraction',(last['h']-max(last['o'],last['c']))/span if span>0 else None,'ZERO_RANGE' if span==0 else None)
 sixkeys=list(range(decision-30,decision,5))
 if all(regular(k) and k in bars for k in sixkeys):
  six=[bars[k] for k in sixkeys]
  put('trailing30MeanRangePct',sum((r['h']-r['l'])/price*100 for r in six)/6)
  if all(r['a'] is not None for r in six):
   den=sum(r['a'] for r in six[:3]);num=sum(r['a'] for r in six[3:])
   put('trailing15ToPrior15TurnoverRatio',num/den if den>0 else None,'ZERO_DENOMINATOR' if den==0 else None)
  else: why['trailing15ToPrior15TurnoverRatio']='RAW_TURNOVER_MISSING'
 if all(regular(k) for k in range(decision-15,decision)):
  observed=sum(decision-15<=r['m']<decision for r in prefix)
  put('trailing15ObservedMinuteFraction',observed/15)
 put('scoreChangeSincePriorSelection',score-prior_score if prior_score is not None else None,
     'NO_PRIOR_SELECTION' if prior_score is None else None)
 put('priorSelectionCount',float(count))
 if prefix and all(r['a'] is not None and r['v'] is not None for r in prefix):
  amount=sum(r['a'] for r in prefix);vol=sum(r['v'] for r in prefix)
  if amount>0 and vol>0: put('observedTurnoverVwapDistancePct',(price/(amount/vol)-1)*100)
  else: why['observedTurnoverVwapDistancePct']='ZERO_VWAP_DENOMINATOR'
 else: why['observedTurnoverVwapDistancePct']='RAW_VOLUME_OR_TURNOVER_MISSING'
 return {'values':result,'missingReasons':why,'prefixLastMinute':max((r['m'] for r in prefix),default=None),
         'observedPrefixMinuteCount':len(prefix),'lastBarObservedMinuteCount':last['n'] if last else 0}

def run(root,cache,out):
 root,cache,out=map(pathlib.Path,(root,cache,out))
 if out.exists(): raise ValueError('APPEND_ONLY_OUTPUT')
 fb=(root/FEAT).read_bytes(); rows=[json.loads(x) for x in gzip.decompress(fb).splitlines()]
 protocol=read(root/'predict/research/phase57-entry-v2-3-fast-fail-protocol-v1.json')
 assert sha(fb)==protocol['sourcePins'][FEAT]
 assert len(rows)==3800 and len({r['selectorEventId'] for r in rows})==3800
 for r in rows:
  assert r['direction']=='LONG'
 dates=sorted({r['sessionDate'] for r in rows});assert len(dates)==76
 prior=read(root/PRIOR); source_by={x['sessionDate']:x for x in prior['sources']}
 events=[];sources=[];raw_stats=collections.Counter();checked=0
 for date in dates:
  selected=sorted([r for r in rows if r['sessionDate']==date],key=lambda r:(r['decisionTimestamp'],r['symbol']))
  p=cache/'phase57-long-only/raw/jquants-v2'/date/'minute-pages.json'
  raw=p.read_bytes();assert sha(raw)==source_by[date]['rawPagesSHA'],'SOURCE_BYTES'
  pages=json.loads(raw); selected_symbols={r['symbol'] for r in selected}
  raw_rows=[]
  for page in pages:
   assert sha(page['responseText'].encode())==page['responseSha256'],'PAGE_SHA'
   for r in json.loads(page['responseText'])['data']:
    assert str(r.get('Date',r.get('date','')))==date,'DATE_SCOPE'
    if str(r.get('Code',r.get('code',r.get('symbol','')))).strip().upper() in selected_symbols: raw_rows.append(r)
  data,stats=aggregate(raw_rows,date,selected_symbols);raw_stats.update(stats)
  seen={};counts=collections.Counter()
  for r in selected:
   t=dt.datetime.fromisoformat(r['decisionTimestamp']);decision=t.hour*60+t.minute;s=r['symbol']
   assert t.date().isoformat()==date and t.utcoffset()==dt.timedelta(hours=9)
   assert counts[s]==r['priorSelectionCount'],'PRIOR_SELECTION_COUNT'
   z=snapshot(data.get(s,{}),decision,r['decisionPrice'],r['ridgeScore'],seen.get(s),counts[s])
   assert z['prefixLastMinute'] is None or z['prefixLastMinute']+1<=decision
   trimmed={m:x for m,x in data.get(s,{}).items() if m+1<=decision}
   assert z==snapshot(trimmed,decision,r['decisionPrice'],r['ridgeScore'],seen.get(s),counts[s])
   checked+=1
   events.append({'eventId':r['selectorEventId'],'sessionDate':date,'symbol':s,
    'decisionTimestamp':r['decisionTimestamp'],'symbolSessionId':r['symbolSessionId'],**z})
   seen[s]=r['ridgeScore'];counts[s]+=1
  sources.append({'sessionDate':date,'rawPagesSHA':sha(raw),'selectedRawAudit':stats})
  print(json.dumps({'date':date,'featureEvents':len(selected),'providerRequests':0}),flush=True)
 result={'protocol':PROTOCOL,'sourceHead':SOURCE_HEAD,'featureSourceSHA':sha(fb),'sources':sources,
  'events':events,'rawSelectedAudit':dict(raw_stats),'realCausalInvarianceChecks':checked,
  'modelFit':0,'modelPrediction':0,'freshAccess':0,'oosAccess':0,'providerRequests':0,
  'limitation':'Later-fetched historical source. Only formula-time causality in frozen conditional universe; not actual feed arrival proof.'}
 out.parent.mkdir(parents=True,exist_ok=True)
 b=gzip.compress((json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n').encode(),mtime=0)
 out.write_bytes(b);out.with_suffix(out.suffix+'.sha256').write_text(sha(b)+'\n')
 print(json.dumps({'status':'FEATURE_EXPORT_COMPLETE','events':len(events),'sha256':sha(b),'causalChecks':checked}))

class Tests(unittest.TestCase):
 def minute(self,m=565): return {'m':m,'o':10.,'h':12.,'l':9.,'c':11.,'v':100.,'a':1050.}
 def test_formula(self):
  z=snapshot({565:self.minute()},570,11,4,2,1)
  self.assertAlmostEqual(z['values']['last5CloseLocation'],2/3)
  self.assertAlmostEqual(z['values']['last5UpperWickFraction'],1/3)
  self.assertEqual(z['values']['scoreChangeSincePriorSelection'],2)
 def test_future(self):
  a={565:self.minute()};b=a|{570:dict(self.minute(570),h=999,c=999)}
  self.assertEqual(snapshot(a,570,11,4,None,0),snapshot(b,570,11,4,None,0))
 def test_missing(self):
  z=snapshot({565:dict(self.minute(),v=None,a=None)},570,11,4,None,0)
  self.assertIsNone(z['values']['observedTurnoverVwapDistancePct'])
 def test_zero_span(self):
  z=snapshot({565:dict(self.minute(),o=10,h=10,l=10,c=10)},570,10,4,None,0)
  self.assertIsNone(z['values']['last5CloseLocation']);self.assertEqual(z['missingReasons']['last5CloseLocation'],'ZERO_RANGE')
 def test_zero_not_missing(self):
  self.assertEqual(val({'Vo':0},'Vo'),0);self.assertIsNone(val({'Vo':None},'Vo'))
 def test_turnover(self):
  a={m:dict(self.minute(m),a=100. if m<555 else 200.) for m in range(540,570)}
  self.assertEqual(snapshot(a,570,11,4,None,0)['values']['trailing15ToPrior15TurnoverRatio'],2)
 def test_lunch(self): self.assertIsNone(snapshot({},750,11,4,None,0)['values']['trailing15ObservedMinuteFraction'])
 def test_no_trade_not_zero(self):
  z=snapshot({},570,11,4,None,0);self.assertIsNone(z['values']['last5CloseLocation'])
  self.assertEqual(z['values']['trailing15ObservedMinuteFraction'],0)
 def test_duplicates(self):
  r={'Date':'2024-09-17','Code':'A','Time':'09:25','O':10,'H':12,'L':9,'C':11,'Vo':100,'Va':1000}
  with self.assertRaises(ValueError): aggregate([r,r|{'C':10}],r['Date'],{'A'})
 def test_unauthorized_date(self):
  with self.assertRaises(ValueError): aggregate([{'Date':'2026-09-17'}],'2024-09-17',set())
 def test_eight_fields(self): self.assertEqual(len(FEATURE_ORDER),8)
 def test_all_safety_false(self): self.assertFalse(any(PROTOCOL['safety'].values()))

if __name__=='__main__':
 if sys.argv[1:]==['--test']:
  unittest.main(argv=[sys.argv[0]])
 else: run(*sys.argv[1:])
