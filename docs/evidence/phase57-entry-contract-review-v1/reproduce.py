import gzip,json,math,collections,hashlib
from pathlib import Path
import argparse
a=argparse.ArgumentParser();a.add_argument('--prior',required=True);a.add_argument('--output',required=True);args=a.parse_args();root=Path(args.prior)
pins={'measurement/metrics.json': '19bf1962961a9699958f8ea5f38d4278ede846ce27e8ce76d5b40dfd48f253e1', 'measurement/trades.json.gz': '5dc3012e98255506afb8fa3778fda09eb8eb542e10857e827e6e32072a1a268d', 'substrate/features.json.gz': '35fd35c9c7bd0c54d38a1ca3f73558a57d76cf7f7f58da9e4e625a01e029ecd7', 'substrate/opportunities.json.gz': '6334ebf16e323496b49abf38754bd4f3b056eff8cace4eceafe92ecb02989d88', 'substrate/outcomes.json.gz': '33f12956133fa86e975adba77a0535ff1003d32d7ccf8a0ef96303d586fad327'}
for name,h in pins.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h,name
def read(p):
 p=root/p
 return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_text())
tr=read('measurement/trades.json.gz');op=read('substrate/opportunities.json.gz');labs=read('substrate/outcomes.json.gz');rs=read('substrate/features.json.gz')
ids={t['opportunity'] for t in tr['E5']};op=[o for o in op if o['id'] in ids];rows={x['id']:x for x in rs if x['opportunity'] in ids};ob={o['id']:o for o in op};e5={t['opportunity']:t for t in tr['E5']};im={t['opportunity']:t for t in tr['IMMEDIATE']}
def cap(t,level):
 l=labs[t['entryId']]['labels'] if t['entryId'] else None
 return bool(l and l['mfeEnd'] is not None and l['mfeEnd']>=level)
def eligible(o):
 return [o['id']+'|'+str(t) for t in o['grid'] if rows[o['id']+'|'+str(t)]['quoteAvailable'] and labs[o['id']+'|'+str(t)]['price'] is not None]
retry={}
for o in op:
 tick=eligible(o);retry[o['id']]={'opportunity':o['id'],'session':o['session'],'symbol':o['symbol'],'entryId':tick[0] if tick else None}
res={'n':len(op),'twoByTwo':dict(collections.Counter(f'E5={bool(e5[i]["entryId"])} Immediate={bool(im[i]["entryId"])}' for i in ids)),'noEntryReasons':dict(collections.Counter('EMPTY_GRID' if not ob[i]['grid'] else e5[i]['attempts'][-1]['reason'] if e5[i]['attempts'] else 'NO_ATTEMPT' for i in ids if not e5[i]['entryId'])),'buyFinalReason':dict(collections.Counter(t['attempts'][-1]['reason'] for t in e5.values() if t['entryId'])),'gridLengths':dict(collections.Counter(len(o['grid']) for o in op)),'lunchGridLengths':dict(collections.Counter(len(o['grid']) for o in op if 660<=int(o['origin']['decisionTimeJst'][:2])*60+int(o['origin']['decisionTimeJst'][3:])<690)),'thresholds':{}}
for level in [3,5]:
 win={o['id'] for o in op if o['selectorOutcome']['mfeEnd'] is not None and o['selectorOutcome']['mfeEnd']>=level}
 hits={k:{i for i in win if cap(t[i],level)} for k,t in [('E5',e5),('Immediate',im),('Retry',retry)]}
 ceiling={i for i in win if any(labs[key]['labels']['mfeEnd'] is not None and labs[key]['labels']['mfeEnd']>=level for key in eligible(ob[i]))}
 new=hits['E5']-hits['Immediate'];empty={i for i in win if not ob[i]['grid']};newOnly={i for i in new if not im[i]['entryId']}
 res['thresholds'][str(level)]={'winners':len(win),'gateRequired':math.ceil(.9*len(win)),'captureCounts':{k:len(v) for k,v in hits.items()},'ceiling':len(ceiling),'remainingToCeiling':len(ceiling-hits['E5']),'newVsImmediate':len(new),'lostVsImmediate':len(hits['Immediate']-hits['E5']),'newE5OnlyEntry':len(newOnly),'newBothEntry':len(new-newOnly),'newOnlyImmediateReasons':dict(collections.Counter(im[i]['attempts'][-1]['reason'] if im[i]['attempts'] else 'EMPTY_GRID' for i in newOnly)),'emptyGridWinners':len(empty),'optimisticOnlyEmptyRepairCaptured':len(hits['E5'])+len(empty),'newVsRetry':len(hits['E5']-hits['Retry']),'lostVsRetry':len(hits['Retry']-hits['E5'])}
res['retryBUY']=sum(bool(t['entryId']) for t in retry.values())
# Availability by current continuous-session elapsed wall minutes, new eligible evaluation ticks only.
buckets=collections.defaultdict(list)
for x in rows.values():
 if not x['newEligibleTick']:continue
 t=x['minute'];age=t-(540 if t<=690 else 750);bucket='00-14' if age<15 else '15-29' if age<30 else '30-59' if age<60 else '60+'
 buckets[bucket].append(x)
res['availabilityBySegmentAge']={}
for k,xs in sorted(buckets.items()):
 res['availabilityBySegmentAge'][k]={'n':len(xs),**{'w'+str(w):{'available':sum(x['SEQ']['features']['w'+str(w)+'_return'] is not None for x in xs),'pct':100*sum(x['SEQ']['features']['w'+str(w)+'_return'] is not None for x in xs)/len(xs)} for w in [15,30,60]}}
res['evaluationDecisionRows']=len(rows);res['newEligibleRows']=sum(x['newEligibleTick'] for x in rows.values())
res['codeClockExamples']={}
from scripts import phase57_chart_entry as e
for t in [660,665,670,675,680,685,690]:res['codeClockExamples'][str(t)]=e.clock('2025-06-02',t)
res['retryMetrics']=e.metrics(op,[{**t,'delay':int(t['entryId'].split('|')[-1])-e.minute(ob[i]['origin']['decisionTimestamp']) if t['entryId'] else None} for i,t in retry.items()],labs)
res['inputHashes']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

no=collections.Counter();buy=collections.Counter();emptytimes=collections.Counter()
for o in op:
 t=e5[o['id']];kk=[o['id']+'|'+str(m) for m in o['grid']]
 if not o['grid']:emptytimes[o['origin']['decisionTimeJst']]+=1
 if not t['entryId']:
  no['EMPTY_GRID' if not kk else 'NO_FILL_PRICE_AT_ANY_TICK' if not any(labs[k]['price'] is not None for k in kk) else 'NO_QUOTE_AND_FILL_SAME_TICK' if not eligible(o) else 'LEARNED_WAIT_MISSED_AVAILABLE_TICK']+=1
 else:
  reasons={x['reason'] for x in t['attempts'][:-1]};buy[str(sorted(reasons))]+=1
res['noEntryByEligibleTick']=dict(no);res['buyPriorWaitReasons']=dict(buy);res['emptySelectionTime']=dict(emptytimes)
res['gateBoundsWithEmptyRepair']={k:{'oracleSavedPlusEmptyWinner':z['ceiling']+z['emptyGridWinners'],'pct':100*(z['ceiling']+z['emptyGridWinners'])/z['winners'],'currentE5PlusEmptyWinner':z['captureCounts']['E5']+z['emptyGridWinners']} for k,z in res['thresholds'].items()}

Path(args.output).write_text(json.dumps(res,indent=2,sort_keys=True)+'\n')
