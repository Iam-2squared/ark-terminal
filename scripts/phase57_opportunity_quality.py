"""Evaluator-only quality of immutable emitted opportunities; never trading decisions."""
import argparse,collections,csv,gzip,hashlib,json,math,statistics
from pathlib import Path
from scripts import phase57_new_long_entry_exit_conditional as c
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-price75-entry-opportunity-quality-v1'
SOURCE=ROOT/'docs/evidence/phase57-selector-min-price75-v1/measurement'
LEVELS=(1,2,3,5)
HORIZONS=(5,10,15,30,60)
INITIAL='INITIAL_ENTRY_OPPORTUNITY'
DIP='DIP_REPRICE_OPPORTUNITY'
PROTOCOL_COMMIT='e2450763f064761c4dccbc48c38cd124ddc8b5ae'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def encoded(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def write(p,x):
 b=encoded(x);p=Path(p)
 if p.suffix=='.gz':b=gzip.compress(b,mtime=0)
 with p.open('xb') as f:f.write(b)
def distribution(values):
 a=[v for v in values if v is not None]
 return {'n':len(a),'mean':statistics.mean(a) if a else None,'median':c.quantile(a,.5),**{f'p{int(p*100):02d}':c.quantile(a,p) for p in (.05,.1,.25,.75,.9,.95)},'min':min(a) if a else None,'max':max(a) if a else None,'positiveRate':sum(v>0 for v in a)/len(a) if a else None}
def rate(n,d):return {'n':n,'denominator':d,'rate':n/d if d else None}

def window(bars,expected_count,reason=None):
 valid=[b for b in bars if c.valid(b)]
 complete=reason is None and len(bars)==expected_count and expected_count>0 and len(valid)==len(bars)
 status='COMPLETE' if complete else reason or 'MISSING_BAR'
 hits={};times={}
 for k in LEVELS:
  hit=next((b for b in valid if b['h']>=k),None)
  hits[str(k)]=True if hit else False if complete else None
  if hit:
   preceding=[b for b in bars if b['slot']<hit['slot']]
   identified=all(c.valid(b) for b in preceding)
   times[str(k)]={'observedHitInterval':[hit['minutes']-5,hit['minutes']],'firstHitIdentified':identified,'firstHitBounds':[hit['minutes']-5 if identified else 0,hit['minutes']]}
  else:times[str(k)]=None
 return {'status':status,'complete':complete,'expectedBars':expected_count,'observedBars':len(valid),'allUnderlyingMinutesObserved':complete and all(b.get('observedMinutes')==5 for b in valid),'returnPct':bars[-1]['c'] if complete else None,'mfe':max(0,max(b['h'] for b in valid)) if valid else None,'mae':min(0,min(b['l'] for b in valid)) if valid else None,'reach':hits,'timeToHit':times}

def evaluate(op,path):
 a=c.adapt(op,path) # Mechanical OHLC rebase only; no EXIT policy is called/imported.
 if a['status']!='REFERENCE_POSITION':return {str(h):window([],h//5,op['referenceStatus']) for h in HORIZONS}|{'SESSION':window([],0,op['referenceStatus'])}
 assert a['positionStartTimestamp']==op['opportunityTimestamp']
 bars=a['future'];start=a['startMinute'];bound=c.segment_end(start,a['sessionEndMinute'])
 result={}
 for h in HORIZONS:
  bs=[b for b in bars if b['minutes']<=h]
  boundary=bound is None or start+h>bound
  result[str(h)]=window(bs,h//5,'SEGMENT_BOUNDARY' if boundary else None)
 result['SESSION']=window(bars,a['expectedBars'])
 return result

def aggregate(rows,h):
 allw=[r['windows'][h] for r in rows];complete=[w for w in allw if w['complete']];observed=[w for w in allw if w['observedBars']]
 reach={};times={}
 for k in LEVELS:
  key=str(k);true=sum(w['reach'][key] is True for w in allw);false=sum(w['reach'][key] is False for w in allw);unknown=len(allw)-true-false
  reach[key]={'completeCase':rate(sum(w['reach'][key] is True for w in complete),len(complete)),'knownPositive':true,'knownNegative':false,'unknown':unknown,'identifiedOutcome':rate(true,true+false),'allEmittedLowerBound':rate(true,len(allw)),'allEmittedUpperBound':rate(true+unknown,len(allw))}
  hit=[w['timeToHit'][key] for w in allw if w['timeToHit'][key]];identified=[x for x in hit if x['firstHitIdentified']]
  times[key]={'observedHitN':len(hit),'identifiedFirstHitN':len(identified),'ambiguousEarlierMissingN':len(hit)-len(identified),'identifiedIntervalStartMinutes':distribution([x['observedHitInterval'][0] for x in identified]),'identifiedIntervalEndMinutes':distribution([x['observedHitInterval'][1] for x in identified]),'allObservedHitUpperMinutes':distribution([x['observedHitInterval'][1] for x in hit])}
 return {'emittedN':len(rows),'completeN':len(complete),'observedPathN':len(observed),'fullUnderlyingMinuteN':sum(w['allUnderlyingMinutesObserved'] for w in allw),'status':dict(sorted(collections.Counter(w['status'] for w in allw).items())),'reach':reach,'return':distribution([w['returnPct'] for w in complete]),'completeMFE':distribution([w['mfe'] for w in complete]),'completeMAE':distribution([w['mae'] for w in complete]),'observedMFE':distribution([w['mfe'] for w in observed]),'observedMAE':distribution([w['mae'] for w in observed]),'completeMAETails':{str(k):rate(sum(w['mae']<=-k for w in complete),len(complete)) for k in (1,3,5,10)},'timeToHit':times}
def panel(rows):return {str(h):aggregate(rows,str(h)) for h in (*HORIZONS,'SESSION')}

def breadth(groups,h):
 n=len(groups);result={}
 for k in LEVELS:
  bounds=[];complete=[]
  for rows in groups.values():
   labels=[r['windows'][h]['reach'][str(k)] for r in rows];lo=sum(x is True for x in labels);hi=lo+sum(x is None for x in labels);bounds.append((lo,hi))
   if lo==hi:complete.append(lo)
  result[str(k)]={'timestamps':n,'outcomeIdentifiedTimestamps':len(complete),'knownWinnerCount':sum(lo for lo,hi in bounds),'possibleWinnerCount':sum(hi for lo,hi in bounds),'meanWinnersLowerBound':sum(lo for lo,hi in bounds)/n if n else None,'meanWinnersUpperBound':sum(hi for lo,hi in bounds)/n if n else None,'completeDistribution':{str(j):rate(sum(v==j for v in complete),len(complete)) for j in range(6)},'completeGroupedDistribution':{str(j) if j<4 else '4+':rate(sum(v==j or j==4 and v>=4 for v in complete),len(complete)) for j in range(5)},'atLeast':{str(j):{'lower':rate(sum(lo>=j for lo,hi in bounds),n),'upper':rate(sum(hi>=j for lo,hi in bounds),n)} for j in (1,2,3,4)},'zeroWinnerBounds':{'lower':rate(sum(hi==0 for lo,hi in bounds),n),'upper':rate(sum(lo==0 for lo,hi in bounds),n)}}
 return result
def by_timestamp(rows):
 groups=collections.defaultdict(list)
 for r in rows:groups[r['timestamp']].append(r)
 return dict(sorted(groups.items()))
def freq(rows,field):
 counts=collections.Counter(r[field] for r in rows);n=len(rows)
 return {'n':n,'unique':len(counts),'HHI':sum((v/n)**2 for v in counts.values()) if n else None,'top10':sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:10]}
def focus(groups):return {h:breadth(groups,h) for h in ('30','SESSION')}
def lower_test(f,three,five,min_n):
 b=f['SESSION'];return b['3']['timestamps']>=min_n and (b['3']['atLeast']['2']['lower']['rate'] or 0)>=three and (b['5']['atLeast']['2']['lower']['rate'] or 0)>=five
def dilution(rows):
 low=[r for r in rows if r['candidateCount']<=3];high=[r for r in rows if r['candidateCount']>=4]
 a=aggregate(low,'30');b=aggregate(high,'30');ok=a['completeN']>=30 and b['completeN']>=30
 diffs={str(k):(b['reach'][str(k)]['completeCase']['rate']-a['reach'][str(k)]['completeCase']['rate']) if a['completeN'] and b['completeN'] else None for k in (3,5)}
 return {'lowCompleteN':a['completeN'],'highCompleteN':b['completeN'],'delta':diffs,'pass':bool(ok and diffs['3']<=-.10 and diffs['5']<=-.05)}

def build():
 protocol=read(BASE/'protocol.json')
 for p,h in protocol['sourcePins'].items():assert sha(ROOT/p)==h,p
 frozen=read(ROOT/'predict/research/phase57-long-only-frozen-selector-min-price75-v1.json')
 for p,h in frozen['freezePayload']['filePins'].items():assert sha(ROOT/p)==h,p
 decisions=read(SOURCE/'downstream/entry-decisions.json.gz')['new'];paths={p['selectorEventId']:p for p in read(SOURCE/'new-paths.json.gz')['events']};selected={r['selectorEventId']:r for r in read(SOURCE/'selector/selector-ledger.json.gz')['new']}
 prior={(r['anchorId'],r['cohort']):r for r in read(SOURCE/'downstream/entry-ledger.json.gz')['new']}
 rows=[]
 for d in decisions:
  for key in ('initialEvent','secondaryEvent'):
   op=d['decision'][key]
   if op is None:continue
   s=selected[op['anchorId']];w=evaluate(op,paths[op['anchorId']]);old=prior[(op['anchorId'],op['eventType'])]
   assert w['30']['complete']==(old['strict30']['status']=='COMPLETE')
   if w['30']['complete']:assert w['30']['mfe']==old['strict30']['mfePct'] and w['30']['mae']==old['strict30']['maePct']
   rows.append({'anchorId':op['anchorId'],'source':op['eventType'],'symbol':op['symbol'],'session':d['sessionDate'],'timestamp':op['opportunityTimestamp'],'referenceStatus':op['referenceStatus'],'referencePrice':op.get('referencePrice'),'selectorAnchorRank':s['newEligibleRank'],'selectorAnchorScore':s['savedV1Score'],'windows':w})
 rows.sort(key=lambda r:(r['timestamp'],r['symbol'],r['source']))
 assert len(rows)==3508 and len({(r['anchorId'],r['source']) for r in rows})==3508
 groups=by_timestamp(rows);assert len(groups)==1181
 for ts,rs in groups.items():
  assert len({r['symbol'] for r in rs})==len(rs) and 1<=len(rs)<=5
  for r in rs:r['candidateCount']=len(rs)
 sessions=sorted({r['session'] for r in rows});assert len(sessions)==76
 assert collections.Counter(r['source'] for r in rows)=={INITIAL:2841,DIP:667}
 counts=read(ROOT/'docs/evidence/phase57-price75-entry-opportunity-timestamp-counts-v1/summary.json')
 assert collections.Counter(len(rs) for rs in groups.values())=={int(k[0]):v['timestamps'] for k,v in counts['panels']['OPPORTUNITY_EMISSION_TIMESTAMPS']['distribution'].items() if v['timestamps']}
 concentration={'symbol':freq(rows,'symbol'),'session':freq(rows,'session')};top3=[s for s,n in concentration['symbol']['top10'][:3]]
 high={ts:rs for ts,rs in groups.items() if len(rs)>=4};top3_high={ts:[r for r in rs if r['symbol'] not in top3] for ts,rs in high.items()}
 focus_high=focus(high);focus_ex=focus(top3_high)
 blocks={};focus_blocks={}
 for i in range(4):
  dates=sessions[i*19:(i+1)*19];rs=[r for r in rows if r['session'] in dates]
  blocks[str(i+1)]={'sessions':dates,'quality':panel(rs),'dilution':dilution(rs)}
  focus_blocks[str(i+1)]=focus({ts:rs for ts,rs in high.items() if ts[:10] in dates})
 dilute_sources={s:dilution([r for r in rows if r['source']==s]) for s in (INITIAL,DIP)}
 common=lower_test(focus_high,.20,.10,100) and lower_test(focus_ex,.20,.10,100) and sum(lower_test(v,.20,.10,1) for v in focus_blocks.values())>=3
 dilute=all(x['pass'] for x in dilute_sources.values()) and sum(b['dilution']['pass'] for b in blocks.values())>=3
 sufficient=lower_test(focus_high,.10,.05,100) and lower_test(focus_ex,.10,.05,100) and sum(lower_test(v,.10,.05,1) for v in focus_blocks.values())>=3
 verdict='MULTIPLE_HIGH_QUALITY_OPPORTUNITIES_COMMON' if common else 'ENTRY_OPPORTUNITY_QUALITY_DILUTES_AT_HIGH_BREADTH' if dilute else 'ENTRY_OPPORTUNITY_QUALITY_SUFFICIENT' if sufficient else 'INCONCLUSIVE'
 interactions={};candidate={};ranks={}
 for n in range(1,6):
  gs={ts:rs for ts,rs in groups.items() if len(rs)==n};rs=[r for rs in gs.values() for r in rs]
  candidate[str(n)]={'timestamps':len(gs),'opportunities':len(rs),'quality':panel(rs),'breadth':focus(gs)}
  ranks[str(n)]={'quality':panel([r for r in rows if r['selectorAnchorRank']==n]),'score':distribution([r['selectorAnchorScore'] for r in rows if r['selectorAnchorRank']==n])}
 for name,sources in [('INITIAL_ONLY',{INITIAL}),('DIP_ONLY',{DIP}),('MIXED',{INITIAL,DIP})]:
  gs={ts:rs for ts,rs in groups.items() if {r['source'] for r in rs}==sources};rs=[r for rs in gs.values() for r in rs]
  interactions[name]={'timestamps':len(gs),'opportunities':len(rs),'candidateCount':distribution([len(x) for x in gs.values()]),'quality':panel(rs)}
 result={'protocolCommit':PROTOCOL_COMMIT,'sourceHead':protocol['sourceHead'],'population':{'sessions':76,'opportunities':3508,'initial':2841,'dip':667,'timestamps':1181,'referenceStatus':dict(sorted(collections.Counter(r['referenceStatus'] for r in rows).items()))},'cohorts':{'TOTAL':panel(rows),INITIAL:panel([r for r in rows if r['source']==INITIAL]),DIP:panel([r for r in rows if r['source']==DIP])},'candidateCount':candidate,'focus45':{'timestamps':len(high),'opportunities':sum(map(len,high.values())),'breadth':focus_high,'chronological':focus_blocks},'interaction':interactions,'chronological':blocks,'sessions':{date:panel([r for r in rows if r['session']==date]) for date in sessions},'concentration':concentration,'top3Exclusion':{'symbols':top3,'quality':panel([r for r in rows if r['symbol'] not in top3]),'focus45OriginalTimestampDenominator':focus_ex},'selectorAnchorRankDescriptive':ranks,'verdict':{'quality':verdict,'closure':'ENTRY_RESEARCH_REOPEN_JUSTIFIED' if verdict=='ENTRY_OPPORTUNITY_QUALITY_DILUTES_AT_HIGH_BREADTH' else 'ENTRY_FREEZE_MAINTAIN','commonGate':common,'dilutionGate':dilute,'sufficientGate':sufficient,'sourceDilution':dilute_sources,'notValidated':True,'noImplementationChange':True},'audit':{'opportunityIdentityUnique':True,'symbolTimestampUnique':True,'timestampCountsParity':True,'oldStrict30Parity':sum(r['windows']['30']['complete'] for r in rows),'frozenPinsUnchanged':True,'noSameBarOrderingAssumed':True,'evaluatorOnly':True,'entryExitCapitalInvocations':0,'fitCalls':0,'providerRequests':0},'safety':protocol['safety'],'freshOOSOpened':False}
 return rows,result

def run(outdir):
 out=Path(outdir)
 if out.exists():raise FileExistsError(out)
 rows,s=build();out.mkdir(parents=True)
 write(out/'ledger.json.gz',rows);write(out/'summary.json',s)
 fields=['timestamp','candidates','sources','horizon','level','knownWinners','unknownCandidates','possibleWinners']
 with (out/'breadth.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
  for ts,rs in by_timestamp(rows).items():
   for h in ('30','SESSION'):
    for k in LEVELS:
     labs=[r['windows'][h]['reach'][str(k)] for r in rs];lo=sum(v is True for v in labs);unknown=sum(v is None for v in labs)
     writer.writerow(dict(zip(fields,[ts,len(rs),'|'.join(sorted({r['source'] for r in rs})),h,k,lo,unknown,lo+unknown])))
 write(out/'manifest.json',{'protocolCommit':PROTOCOL_COMMIT,'protocolSHA256':sha(BASE/'protocol.json'),'sourcePins':read(BASE/'protocol.json')['sourcePins'],'codePin':sha(__file__),'outputPins':{p:sha(out/p) for p in ('ledger.json.gz','summary.json','breadth.csv')},'safety':s['safety'],'freshOOSOpened':False})
 print(json.dumps({'population':s['population'],'focus45':s['focus45']['breadth'],'verdict':s['verdict'],'audit':s['audit']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();run(a.out)
