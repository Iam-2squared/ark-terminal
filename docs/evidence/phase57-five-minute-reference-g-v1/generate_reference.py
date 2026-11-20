"""G Gate only: fixed-cohort five-minute reference labels from preserved data.

No legacy State/Signal, selector features, Dictionary, outcomes, models or trading.
The adopted reference.py is verified and imported without any modification.
"""
from __future__ import annotations
import argparse, collections, csv, datetime as dt, gzip, hashlib, importlib.util
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
from pathlib import Path

COHORT_SHA='6b02b3088dd8ea7f8ce53112bc276df442bae3ce0716b8139c92733be4de2994'
PINS={
 'opportunities.json.gz':'1138960e489c3403e49f502a7ff7ab1fa1e9ef205910d2d018f2bb938df813ea',
 'raw-paths-evaluator-only.json.gz':'37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b',
 'manifest.json':'0295c4d6ccda95efe48ba805ea52b0739c2e78c2e2486277a3b93dc8f9c6da0c',
 'source-ledger.json':'5463256720a5276a86c49043b6ceb27a0c42907a5f63354425cc251588d18e96',
 'inventory.json':'62f5c837e9eae56632b65ff870948ed2cfc6bfc3cf0e106dcd68760d1907b6ff',
 'daily.json.gz':'885c80846e62df178d37c735a152b730464122fd35df7224d55ce2e98e32976d',
 'cohort-protocol.json':COHORT_SHA}
DEF_PINS={'reference.py':'e57d41b1a9472fb0ed254895d956623a438557f540443c0bee14a6db8f2d8d3d','contract.json':'f00134b85218eba4dad8409a00ce7f1076d1a3abdc02d8a4cb7e2e2b3511279e','test_reference.py':'eed192e39e957a97229e8bdfc4b75e0c79dc393a70d150ca0b714eab31907ec6'}
BASIS='JQUANTS_NONADJUSTED_OHLC_COMMON_RAW_PRICE_UNITS'
QUALITY=['INHERITED_RAW_PRICE_BASIS','INHERITED_SAME_DAY_METADATA_NOT_INDEPENDENT_PIT','CURRENT_ACTION_RAW_NOT_REAUDITED','SOURCE_ALREADY_FILTERED_INVALID_ROWS_CAUSE_NOT_ALWAYS_RECOVERABLE']
_r=None

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(x):
 if isinstance(x,Fraction):return {'numerator':x.numerator,'denominator':x.denominator}
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [clean(v) for v in x]
 return x

def encoded(x):return (json.dumps(clean(x),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def read(p):
 with (gzip.open(p,'rt',encoding='utf-8') if str(p).endswith('.gz') else open(p,encoding='utf-8')) as f:return json.load(f)
def write_json(p,x):
 with Path(p).open('xb') as f:f.write(encoded(x))
def load_ref(root):
 global _r
 for n,h in DEF_PINS.items():
  if sha(Path(root)/n)!=h:raise ValueError('ADOPTED_SOURCE_CHANGED:'+n)
 spec=importlib.util.spec_from_file_location('adopted_reference_g',Path(root)/'reference.py')
 _r=importlib.util.module_from_spec(spec);sys.modules[spec.name]=_r;spec.loader.exec_module(_r)
 return _r

def source_paths(repo,override=None):
 if override:return {n:Path(override)/n for n in list(PINS)+['step1-audit-records.json.gz','step1-future-paths.json.gz','step1-receipt.json','receipt.json']}
 root=Path(repo)/'docs/evidence'
 d={n:root/'phase57-entry-pattern-v2/ci-result/substrate'/n for n in PINS}
 d['daily.json.gz']=root/'phase57-causal-entry-state-v1/ci-result/daily.json.gz'
 d['receipt.json']=root/'phase57-causal-entry-state-v1/ci-result/receipt.json'
 d['cohort-protocol.json']=root/'phase57-entry-timing-signal-census-v1/protocol.json'
 for key,rel in [('step1-audit-records.json.gz','measurement/raw/audit-records.json.gz'),('step1-future-paths.json.gz','measurement/raw/future-paths.json.gz'),('step1-receipt.json','receipt.json')]:
  d[key]=root/'phase57-future-path-deep-audit-v1/ci-result'/rel
 return d

def ends_for(day):
 return tuple(range(541,691))+tuple(range(751,901 if day<'2024-11-05' else 926))
def regular_start(day,t):return 540<=t<690 or 750<=t<(900 if day<'2024-11-05' else 925)
def convert_rows(rows,day):
 """Validated regular bars and separately retained actual auction records."""
 r=_r;bars=[];auctions=[];outside=[];seen=set()
 for x in rows:
  if len(x)!=7 or isinstance(x[0],bool) or int(x[0])!=x[0]:raise ValueError('RAW_COLUMNS_OR_TIME')
  t=int(x[0])
  if t in seen:raise ValueError('DUPLICATE_SOURCE_MINUTE')
  if seen and t<max(seen):raise ValueError('UNSORTED_SOURCE_MINUTE')
  seen.add(t)
  # Validate actual OHLCV/value even for the separate auction sidecar.
  b=r.Bar(t+1,*x[1:],available_at=None)
  if regular_start(day,t):bars.append(b)
  elif t in (690,900 if day<'2024-11-05' else 930):auctions.append(x)
  else:outside.append(x)
 return tuple(bars),auctions,outside

def hhmm(t):return f'{t//60:02d}:{t%60:02d}'
def pctnum(x):return None if x is None else float(x)

def admission(paths,out):
 r=_r
 for n,h in PINS.items():
  if sha(paths[n])!=h:raise ValueError('INPUT_HASH:'+n)
 manifest=read(paths['manifest.json'])
 for n in ('opportunities.json.gz','raw-paths-evaluator-only.json.gz','source-ledger.json','inventory.json'):
  if manifest[n]!=PINS[n]:raise ValueError('SUBSTRATE_MANIFEST:'+n)
 receipt=read(paths['receipt.json'])
 if receipt['evidencePins']['daily.json.gz']!=PINS['daily.json.gz']:raise ValueError('DAILY_RECEIPT')
 ar=read(paths['step1-receipt.json'])
 for n,rel in [('step1-audit-records.json.gz','measurement/raw/audit-records.json.gz'),('step1-future-paths.json.gz','measurement/raw/future-paths.json.gz')]:
  if sha(paths[n])!=ar['evidencePins'][rel]:raise ValueError('STEP1_RECEIPT:'+n)
 cohort=read(paths['cohort-protocol.json']);ids=cohort['opportunityIds'];allowed=set(cohort['developmentSessions']);evaldays=cohort['evaluationSessions']
 if len(ids)!=2155 or ids!=sorted(set(ids)):raise ValueError('COHORT_IDS')
 for obj in (cohort,receipt):
  if len(obj['safety'])!=9 or any(v is not False for v in obj['safety'].values()):raise ValueError('SOURCE_SAFETY')
 ds=read(paths['daily.json.gz']);contexts=ds['contexts'];records=read(paths['step1-audit-records.json.gz'])
 audit={x['opportunity']:{k:x[k] for k in ('opportunity','session','symbol','start','referencePrice')} for x in records};del records
 if set(ids)!=set(contexts) or set(ids)!=set(audit):raise ValueError('COHORT_CROSS_SOURCE')
 cal=sorted(set(evaldays)|{d for c in contexts.values() for d in c['dates']})
 ledger=read(paths['source-ledger.json']);pins={(x['session'],x['kind']):x['sha256'] for x in ledger}
 for z in ds['sourceLedger']:
  if z['status']=='AVAILABLE' and (z['day'] not in allowed or pins.get((z['day'],'daily'))!=z['sha256']):raise ValueError('DAILY_LINEAGE')
 opraw=read(paths['opportunities.json.gz']);opps={}
 for o in opraw:
  if o['id'] not in audit:continue
  origin=o['origin'];stamp=dt.datetime.fromisoformat(origin['decisionTimestamp'])
  if stamp.utcoffset()!=dt.timedelta(hours=9) or stamp.second or stamp.microsecond:raise ValueError('SELECTOR_TIME')
  m=stamp.hour*60+stamp.minute;a=audit[o['id']]
  if (o['session'],o['symbol'],m,origin['decisionPrice'])!=(a['session'],a['symbol'],a['start'],a['referencePrice']):raise ValueError('SOURCE_IDENTITY_VALUE')
  if stamp.date().isoformat()!=o['session'] or o['id']!=o['session']+'|'+o['symbol'] or o['session'] not in evaldays:raise ValueError('IDENTITY')
  if o['id'] in opps:raise ValueError('DUPLICATE_OPPORTUNITY')
  opps[o['id']]={'id':o['id'],'session':o['session'],'symbol':o['symbol'],'selectorAt':origin['decisionTimestamp'],'selectorMinute':m,'selectorPrice':origin['decisionPrice']}
 del opraw
 if set(opps)!=set(ids):raise ValueError('OPPORTUNITY_LOSS')
 raw=read(paths['raw-paths-evaluator-only.json.gz']);saved_future=read(paths['step1-future-paths.json.gz'])
 tasks=[];issues=collections.Counter();future_matches=0;previous_matches=0
 daily_seen={};inputs_path=out/'inputs.jsonl.gz'
 with inputs_path.open('xb') as fh,gzip.GzipFile(fileobj=fh,mode='wb',mtime=0,filename='') as gz:
  for oid in ids:
   o=opps[oid];day=o['session'];code=o['symbol'];path=raw[oid];ctx=contexts[oid];ix=cal.index(day)
   if cal[ix-6:ix]!=ctx['dates'] or ctx['computedThrough']!=ctx['dates'][-1]:raise ValueError('EXACT_CALENDAR_LAGS')
   prevday=ctx['dates'][-1]
   if path['sourceHash']!=pins[(day,'minute')]:raise ValueError('MINUTE_LINEAGE')
   if path['previousSession'] not in (None,prevday):raise ValueError('WRONG_PREVIOUS')
   if path['previous'] and (path['previousSession']!=prevday or prevday not in allowed):raise ValueError('PREVIOUS_OUTSIDE_AUTHORIZED')
   today,auction,outside=convert_rows(path['today'],day)
   previous,pauction,poutside=convert_rows(path['previous'],prevday)
   if outside or poutside:raise ValueError('UNEXPECTED_SOURCE_SESSION_TIMES')
   # Verify independently saved selected future rows, without using old states or outcomes.
   # Step1 retains regular plus eligible auction rows; inspect its container shape explicitly.
   future=saved_future[oid]
   if isinstance(future,dict):future=future.get('rows',future.get('path',future.get('future')))
   if future is None:raise ValueError('STEP1_PATH_SCHEMA')
   expected=[x for x in path['today'] if (x[0]>o['selectorMinute'] if x[0] in (690,930 if day>='2024-11-05' else 900) else x[0]>=o['selectorMinute']) and (regular_start(day,x[0]) or x[0] in (690,930 if day>='2024-11-05' else 900))]
   if future!=expected:raise ValueError('STEP1_RAW_PARITY:'+oid)
   future_matches+=1
   pk=prevday+'|'+code
   if previous and pk in raw and raw[pk]['today']==path['previous']:previous_matches+=1
   daily_rows=[];daily_reasons={}
   for lag in range(1,6):
    d=ctx['dates'][-lag];reason=ctx['reasons'][-lag]
    if d not in allowed:reason='OUTSIDE_AUTHORIZED_DEVELOPMENT'
    if reason:
     daily_reasons[d]=reason;issues['DAILY/'+reason]+=1;continue
    f=ctx['features'];vals={k:f.get(f'D{lag}/{old}') for k,old in [('o','O'),('h','H'),('l','L'),('c','C'),('volume','Vo'),('value','Va')]}
    # Persist exact raw-field projection provenance, not the old derived features.
    row={'date':d,'security':code,'basis':BASIS,**vals}
    r.Bar(1,vals['o'],vals['h'],vals['l'],vals['c'],vals['volume'],vals['value'])
    dk=(d,code)
    if dk in daily_seen and daily_seen[dk]!=row:raise ValueError('CONFLICTING_DAILY_PROJECTION')
    daily_seen[dk]=row;daily_rows.append(row)
   previous_basis=None if daily_reasons.get(prevday)=='CORPORATE_ACTION' else BASIS
   previous_session=r.Session(prevday,code,previous_basis,ends_for(prevday),previous) if previous else None
   scale=r.scale_from_previous(previous_session,day,prevday,code,BASIS) if previous_session else {'status':'PREVIOUS_CONTEXT_UNAVAILABLE','scale':None,'blockN':0}
   c=r.daily_context(day,cal,daily_rows,code,BASIS);c['reasons'].update(daily_reasons)
   pc=None
   if previous_session:
    # Past-end state context is computed once, not a trading-policy test.
    pc=r.snapshot(previous,ends_for(prevday),ends_for(prevday)[-1],scale['scale'])
    pc['scope']='PREVIOUS_SESSION_END_CONTEXT_ONLY';pc['sourceSession']=prevday
    pc['observedHigh']=max(b.h for b in previous);pc['observedLow']=min(b.l for b in previous)
    pc['coverage']=Fraction(len(previous),len(ends_for(prevday)))
    late=[b for b in previous if b.end in ends_for(prevday)[-30:]]
    pc['final30']=r.metrics(late) if len(late)==30 else {'status':'PARTIAL'}
   task={**o,'today':today,'previous':previous,'auction':auction,'previousAuction':pauction,'scale':scale,'daily':c,'dailyRows':daily_rows,'dailyReasons':daily_reasons,'previousContext':pc,'previousDay':prevday,'previousBasis':previous_basis,'sourceHashes':{'todayMinute':path['sourceHash'],'previousMinute':pins.get((prevday,'minute')),'dailyProjection':PINS['daily.json.gz']},'quality':QUALITY,'calendar':cal}
   tasks.append(task)
   gz.write(encoded({**o,'today':path['today'],'previous':path['previous'],'previousDay':prevday,'dailyRows':daily_rows,'dailyReasons':daily_reasons,'sourceHashes':task['sourceHashes'],'quality':QUALITY}))
   issues['SCALE/'+scale['status']]+=1;issues['LATEST_DAILY/'+('COMPLETE5' if c['complete5'] else 'PARTIAL')]+=1
 del raw,saved_future
 report={'status':'SOURCE_IDENTITY_HASH_AND_RAW_UNIT_CONTRACT_VERIFIED_WITH_INHERITED_LIMITATIONS','cohortN':2155,'idsSHA256':hashlib.sha256(encoded(ids)).hexdigest(),'sourcePins':{n:sha(p) for n,p in paths.items()},'definitionPins':DEF_PINS,'evaluationSessions':evaldays,'sessionsWithOpportunities':sorted({o['session'] for o in tasks}),'emptyEvaluationSessions':sorted(set(evaldays)-{o['session'] for o in tasks}),'authorizedDevelopmentSessionN':len(allowed),'exactCalendarLagMismatches':0,'calendar':cal,'calendarScope':'REQUIRED_EXACT_LAG_UNION_NOT_FULL_EXCHANGE_CALENDAR','rawFutureParityN':future_matches,'previousAlsoTodayByteValueMatches':previous_matches,'inputCoverage':dict(issues),'limitations':QUALITY,'independentlyVerifiedCorporateActions':False,'independentlyVerifiedHistoricalReceivedAt':False,'protectedDataOpened':0,'providerRequests':0,'safety':r.SAFETY}
 write_json(out/'admission.json',report)
 return tasks,report

CSV_FIELDS=['opportunity','session','symbol','selectorTime','asOf','elapsedActiveMinutes','observation','observed1m','missing1m','direction','return5Pct','scaleStatus','scale','dailyComplete5','structure','phase','attributes','stateReason','futureStatus','futureMissing','lateConfirmedPivots','pivotN','localRange','sameBarOrderAmbiguities','closedCrossEvents','semanticAny','contextPriceBasis','transitionObservablePair','phaseChanged']

def work_day(args):
 day,tasks,outstr=args;r=_r;out=Path(outstr);stats=collections.defaultdict(collections.Counter);rows_n=0;representatives={};csv_rows=[]
 target=out/'raw'/(day+'.jsonl.gz');contexts_path=out/'contexts'/(day+'.jsonl.gz')
 with target.open('xb') as f,gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0) as z,contexts_path.open('xb') as cf,gzip.GzipFile(fileobj=cf,mode='wb',filename='',mtime=0) as cz:
  for task in tasks:
   oid=task['id'];es=ends_for(day);bs=task['today'];s=task['scale']['scale'];grid=r.grid(task['selectorMinute'],es);prior=None
   cz.write(encoded({'opportunity':oid,'daily':task['daily'],'previousDay':task['previousContext'],'scale':task['scale'],'sourceHashes':task['sourceHashes'],'quality':QUALITY,'auctionRows':task['auction'],'previousAuctionRows':task['previousAuction'],'tailEnds':grid['tailEnds']}))
   for k,t in enumerate(grid['checkpoints']):
    ref=r.reference_at(bs,es,t,s)
    prefix=[b for b in bs if b.end<=t];w=ref['observation'];st=ref['state'];met=ref['descriptors'];fc=ref['futureConfirmation']
    start=w['expectedEnds'][0]-1 if w['expectedEnds'] else t
    before=[b for b in prefix if b.end<=start]
    levels={}
    if task['previousContext'] and task['previousBasis']:
     pc=task['previousContext'];levels.update(PREVIOUS_OBSERVED_HIGH=pc['observedHigh'],PREVIOUS_OBSERVED_LOW=pc['observedLow'])
    if 'D1Levels' in task['daily']:levels.update({f'PREVIOUS_DAILY_{n.upper()}':v for n,v in task['daily']['D1Levels'].items()})
    if before:levels.update(TODAY_PRIOR_HIGH=max(b.h for b in before),TODAY_PRIOR_LOW=min(b.l for b in before))
    # Freeze extra levels at window start using only confirmed-prefix witnesses, never oracle future.
    baseline=r.snapshot(before,es,start,s) if s is not None and before and before[-1].end==start else None
    if baseline:
     bst=baseline['state'];rg=bst.get('localRange')
     if rg:levels.update(LOCAL_RANGE_UPPER=rg['upper'],LOCAL_RANGE_LOWER=rg['lower'])
     for kind in ('HIGH','LOW'):
      piv=[p for p in bst.get('pivots',[]) if p['kind']==kind]
      if piv:levels['STRUCTURAL_SWING_'+kind]=piv[-1]['price']
    events=[e for name,value in sorted(levels.items()) for e in r.level_events(prefix,value,name,start,start,t)]
    future_cut=fc['cutoff'];within=[b for b in bs if b.end<=future_cut]
    conf=[{**e,'confirmation':r.confirmation(e,within,es,future_cut)} for e in events if e['kind'] in ('CLOSE_CROSS_UP','CLOSE_CROSS_DOWN','RECLAIM_UP','RECLAIM_DOWN')]
    vw=r.vwap_events(prefix,es,start,t)
    structure=(st.get('structure') or {}).get('kind');phase=st.get('phase',[]);attrs=ref['attributes']['tags']
    reason=st['identificationStatus']
    detail=[]
    if reason=='UNRESOLVED_STRUCTURE':
     if len(st.get('pivots',[]))<4:detail.append('STRUCTURAL_PIVOT_COUNT_LT_4')
     else:detail.append('NO_ACTIVE_STRUCTURE_UNDER_FIXED_RULES')
     if len(prefix)<30 or (prefix and prefix[-1].end-prefix[0].end+1!=len(prefix)):detail.append('RANGE_CONTIGUOUS_HISTORY_NOT_ESTABLISHED_OR_GAPS')
    elif reason!='IDENTIFIED':detail.append(reason)
    identity={'security':task['symbol'],'session':day,'basis':BASIS};ref['identity']=identity
    tr=r.transition(prior,ref) if prior else None
    pair=bool(prior and prior['observation']['status']=='COMPLETE' and w['status']=='COMPLETE')
    changed=bool(pair and tr and (tr['addedPhase'] or tr['removedPhase']))
    item={'opportunity':oid,'session':day,'symbol':task['symbol'],'selectorAt':task['selectorAt'],'elapsedActiveMinutes':k*5,'asOfJST':day+'T'+hhmm(t)+':00+09:00','reference':ref,'contextsRef':'contexts/'+day+'.jsonl.gz#'+oid,'inputsRef':'inputs.jsonl.gz#'+oid,'stateDetailReasons':detail,'levelSnapshotAtWindowStart':levels,'levelEvents':events,'eventConfirmations':conf,'vwapRelations':vw,'transition':tr,'transitionObservablePair':pair,'dataQualification':QUALITY}
    z.write(encoded(item));rows_n+=1
    row={'opportunity':oid,'session':day,'symbol':task['symbol'],'selectorTime':hhmm(task['selectorMinute']),'asOf':hhmm(t),'elapsedActiveMinutes':k*5,'observation':w['status'],'observed1m':len(w['observedEnds']),'missing1m':len(w['missingEnds']),'direction':met['direction'] if met else None,'return5Pct':pctnum(met['returnPct']) if met else None,'scaleStatus':task['scale']['status'],'scale':pctnum(s),'dailyComplete5':task['daily']['complete5'],'structure':structure,'phase':'|'.join(phase),'attributes':'|'.join(attrs),'stateReason':reason,'futureStatus':fc['status'],'futureMissing':len(fc['missingEnds']),'lateConfirmedPivots':fc['lateConfirmedPivotN'],'pivotN':len(st.get('pivots',[])),'localRange':bool(st.get('localRange')),'sameBarOrderAmbiguities':sum(e['kind']=='INTRABAR_ORDER_UNRESOLVED' for e in events),'closedCrossEvents':sum(e['kind'].startswith('CLOSE_CROSS') for e in events),'semanticAny':bool(structure or phase),'contextPriceBasis':'INHERITED_RAW_PRICE_BASIS','transitionObservablePair':pair,'phaseChanged':changed}
    csv_rows.append(row)
    stats['observation'][w['status']]+=1;stats['direction'][row['direction'] or 'UNAVAILABLE']+=1;stats['structure'][structure or 'UNIDENTIFIED']+=1
    stats['phaseSet']['+'.join(phase) or 'NONE']+=1;stats['stateReason'][reason]+=1;stats['futureStatus'][fc['status']]+=1
    for name in phase:stats['phase'][name]+=1
    for name in attrs:stats['attributes'][name]+=1
    for name in w['reasons']:stats['observationReason'][name]+=1
    for name in detail:stats['stateDetailReason'][name]+=1
    stats['totals']['semanticAny']+=int(row['semanticAny']);stats['totals']['phaseMultiLabel']+=int(len(phase)>1);stats['totals']['observablePairs']+=int(pair);stats['totals']['phaseChanged']+=int(changed)
    for group in ([structure] if structure else [])+phase+([reason] if not structure else []):
     if group not in representatives:representatives[group]={'opportunity':oid,'asOf':hhmm(t),'minute':t}
    prior=ref
 with (out/'csv'/(day+'.csv')).open('x',encoding='utf-8',newline='') as f:
  cw=csv.DictWriter(f,fieldnames=CSV_FIELDS);cw.writeheader();cw.writerows(csv_rows)
 return {'session':day,'opportunities':len(tasks),'checkpointN':rows_n,'stats':{k:dict(v) for k,v in stats.items()},'representatives':representatives}

def run(args):
 root=Path(args.repo);definition=Path(args.definition_root) if args.definition_root else root/'docs/phase57-five-minute-entry-state/mechanical-v1'
 r=load_ref(definition);out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
 for n in ('raw','contexts','csv'): (out/n).mkdir()
 tasks,a=admission(source_paths(root,args.source_root),out)
 if args.admission_only:return
 by=collections.defaultdict(list)
 for task in tasks:by[task['session']].append(task)
 grouped=[(d,by[d],str(out)) for d in sorted(by)]
 if args.workers==1:results=list(map(work_day,grouped))
 else:
  with ProcessPoolExecutor(max_workers=args.workers,initializer=load_ref,initargs=(str(definition),)) as pool:
   results=[]
   for z in pool.map(work_day,grouped):
    results.append(z);print(json.dumps({'session':z['session'],'checkpointN':z['checkpointN']}),flush=True)
 combined=collections.defaultdict(collections.Counter)
 for d in results:
  for k,v in d['stats'].items():combined[k].update(v)
 total=sum(d['checkpointN'] for d in results)
 # All scheduled rows survive. Empty sessions are explicit and not manufactured.
 for d in a['emptyEvaluationSessions']:results.append({'session':d,'opportunities':0,'checkpointN':0,'stats':{},'representatives':{}})
 results.sort(key=lambda z:z['session'])
 csv_path=out/'checkpoints.csv.gz'
 with csv_path.open('xb') as fh,gzip.GzipFile(fileobj=fh,mode='wb',mtime=0,filename='') as gz:
  gz.write((','.join(CSV_FIELDS)+'\r\n').encode())
  for p in sorted((out/'csv').glob('*.csv')):
   lines=p.read_bytes().splitlines(keepends=True);gz.write(b''.join(lines[1:]))
 summary={'version':'five-minute-reference-g-v1','definitionVersion':r.VERSION,'status':'REFERENCE_TABLE_GENERATED_WITH_EXPLICIT_SOURCE_LIMITATIONS_HUMAN_REVIEW_REQUIRED','opportunityN':len(tasks),'evaluationSessionN':len(results),'nonemptySessionN':len(by),'checkpointN':total,'stats':{k:dict(v) for k,v in combined.items()},'sourcePins':a['sourcePins'],'definitionPins':DEF_PINS,'qualification':QUALITY,'newProviderRequests':0,'protectedDataOpened':0,'selectorChanges':0,'definitionChanges':0,'causalRecognitionEvaluated':False,'signalsEvaluated':False,'entryTimingEvaluated':False,'safety':r.SAFETY,'stop':True}
 write_json(out/'by-session.json',results);write_json(out/'summary.json',summary)
 manifest={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
 write_json(out/'manifest.json',manifest)
 print(json.dumps({'DONE':True,'checkpointN':total,'opportunityN':len(tasks)},sort_keys=True),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',default='.');p.add_argument('--source-root');p.add_argument('--definition-root');p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--admission-only',action='store_true')
 run(p.parse_args())
