"""Count saved NEW Entry opportunities only; no Entry/EXIT/Capital replay."""
import argparse,collections,csv,gzip,hashlib,json,statistics
from datetime import datetime,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/evidence/phase57-selector-min-price75-v1/measurement'
INPUTS=['downstream/entry-decisions.json.gz','new-paths.json.gz','selector/selector-ledger.json.gz']
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted')}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def stats(v):return {'n':len(v),'mean':statistics.mean(v) if v else None,'median':statistics.median(v) if v else None,'min':min(v) if v else None,'max':max(v) if v else None}
def hist(rows):
 c=collections.Counter(r['candidateSymbols'] for r in rows)
 return {str(k) if k<5 else '5+':{'timestamps':sum(n for v,n in c.items() if v==k or k==5 and v>=5),'pct':100*sum(n for v,n in c.items() if v==k or k==5 and v>=5)/len(rows) if rows else None} for k in range(6)}
def events_from_decisions(decisions):
 events=[];seen=set()
 for row in decisions:
  for key in ('initialEvent','secondaryEvent'):
   op=row['decision'][key]
   if op is None:continue
   ts=datetime.fromisoformat(op['opportunityTimestamp'])
   assert ts.minute%5==0 and ts.second==0 and ts.microsecond==0
   assert ts.date().isoformat()==row['sessionDate']
   identity=(op['anchorId'],op['eventType'])
   assert identity not in seen;seen.add(identity)
   # The DIP's inherited decisionTimestamp is the t0 anchor, not its emission time.
   events.append({'anchorId':op['anchorId'],'symbol':op['symbol'],'session':row['sessionDate'],'timestamp':op['opportunityTimestamp'],'source':op['eventType'],'referenceStatus':op['referenceStatus']})
 return events

def build():
 decisions=read(SOURCE/INPUTS[0])['new'];paths=read(SOURCE/INPUTS[1])['events'];selection=read(SOURCE/INPUTS[2])['new']
 ends={}
 for p in paths:
  date=p['sessionDate'];end=p['sessionEndMinute']
  assert date not in ends or ends[date]==end;ends[date]=end
 assert len(ends)==76 and set(ends)=={r['sessionDate'] for r in decisions}
 grouped=collections.defaultdict(list)
 for e in events_from_decisions(decisions):grouped[e['timestamp']].append(e)
 rows=[]
 for date,end in sorted(ends.items()):
  # Reporting grid includes morning/session close decision boundaries because
  # the frozen Entry emits INITIAL opportunities there, even if reference expired.
  for minute in [*range(540,691,5),*range(750,end+1,5)]:
   ts=f'{date}T{minute//60:02d}:{minute%60:02d}:00+09:00';es=grouped.get(ts,[])
   syms=sorted({e['symbol'] for e in es})
   rows.append({'session':date,'timestamp':ts,'candidateSymbols':len(syms),'opportunityEvents':len(es),'initialSymbols':len({e['symbol'] for e in es if e['source']=='INITIAL_ENTRY_OPPORTUNITY'}),'dipSymbols':len({e['symbol'] for e in es if e['source']=='DIP_REPRICE_OPPORTUNITY'}),'pricedReferenceSymbols':len({e['symbol'] for e in es if e['referenceStatus']=='REFERENCE_OPEN'}),'symbols':syms})
 assert set(grouped)<={r['timestamp'] for r in rows}
 selected_times={r['decisionTimestamp'] for r in selection}
 panels={'ALL_TRADING_5M_GRID_WITH_BOUNDARIES':rows,'OPPORTUNITY_EMISSION_TIMESTAMPS':[r for r in rows if r['candidateSymbols']>0],'FROZEN_SELECTOR_DECISION_TIMESTAMPS':[r for r in rows if r['timestamp'] in selected_times]}
 out={name:{'candidateSymbols':stats([r['candidateSymbols'] for r in rs]),'distribution':hist(rs),'opportunityEvents':sum(r['opportunityEvents'] for r in rs)} for name,rs in panels.items()}
 events=events_from_decisions(decisions)
 result={'scope':'SAVED_OPPORTUNITY_TIMESTAMP_SYMBOL_COUNT_ONLY','sourceHead':'9a961acb4d5ef3ff41624f239a7e6fe895e2317a','selector':'FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75','entry':'phase57-new-long-entry-two-opportunity-v1','definition':{'timestamp':'opportunityTimestamp, exact 5m boundary; never inherited t0 decisionTimestamp for DIP','unit':'unique symbol per session/opportunityTimestamp; no cross-time holding/persistence','allEmittedIncluded':True,'referenceMissingExcluded':False,'grid':'09:00..11:30 inclusive and 12:30..saved session close inclusive every5m; lunch interior excluded; zero rows are reporting slots, not proof that Entry was invoked','panels':'All 5m reporting slots; positive emission times; original760 Selector decision timestamps. Third panel excludes +5m DIP timestamps by definition.','bins':['0','1','2','3','4','5+'],'notFirstENTER':True,'notConcurrentPositions':True,'noCapitalSimulation':True},'sessions':len(ends),'calendarSessionCounts':dict(sorted(collections.Counter(ends.values()).items())),'opportunityEvents':len(events),'cohorts':dict(sorted(collections.Counter(e['source'] for e in events).items())),'referenceStatus':dict(sorted(collections.Counter(e['referenceStatus'] for e in events).items())),'uniqueSymbols':len({e['symbol'] for e in events}),'panels':out,'perSourceEmission':{c:stats([len({e['symbol'] for e in es if e['source']==c}) for es in grouped.values() if any(e['source']==c for e in es)]) for c in ['INITIAL_ENTRY_OPPORTUNITY','DIP_REPRICE_OPPORTUNITY']},'audits':{'eventsConserved':sum(r['opportunityEvents'] for r in rows)==len(events),'symbolTimestampDuplicateEvents':sum(r['opportunityEvents']-r['candidateSymbols'] for r in rows),'allTimestampsOnGrid':True,'sourceSelectorTimestamps':len(selected_times),'noDecisionReplay':True,'noModelFit':True,'noExitOrCapitalEvaluation':True},'safety':SAFETY,'freshOOSOpened':False}
 assert result['opportunityEvents']==3508 and len(selected_times)==760
 return rows,result

def run(out):
 out=Path(out)
 if out.exists():raise FileExistsError(out)
 rows,result=build();out.mkdir(parents=True)
 def write(name,x):(out/name).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 write('summary.json',result)
 with (out/'timestamp-counts.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader()
  for r in rows:w.writerow({**r,'symbols':' '.join(r['symbols'])})
 lines=['# Frozen NEW Entry Opportunity / 5分timestamp銘柄数分布','', 'First ENTER・保有数・Capitalの診断ではない。保存済み¥75版Opportunityの集計のみ。', '', 'DIPはopportunityTimestamp（発行時刻）に計上し、anchorのdecisionTimestampへ戻さない。価格参照欠測・境界expiredを含め、発行されたOpportunityは除外しない。', '', '| 候補銘柄数 | 全取引5分枠（境界含む） | 発行あり時刻のみ | Selectorの元decision時刻のみ |','| --- | --- | --- | --- |']
 for k in ['0','1','2','3','4','5+']:
  vals=[p['distribution'][k] for p in result['panels'].values()]
  lines.append('| '+k+' | '+' | '.join(f"{v['timestamps']} ({v['pct']:.2f}%)" for v in vals)+' |')
 lines+=['','全5分枠は09:00〜11:30および12:30〜既存session closeの両端を含む。昼休み内部は含まない。0件枠は集計用calendarであり、実際にEntry関数が呼ばれた回数ではない。11:30/closeの発行も既存仕様どおり保持。','','| 分母 | timestamp数 | 平均候補数 | 中央値 | 最大 |','| --- | --- | --- | --- | --- |']
 for name,p in result['panels'].items():
  a=p['candidateSymbols'];lines.append(f"| {name} | {a['n']} | {a['mean']:.4f} | {a['median']} | {a['max']} |")
 lines+=['',f"76 sessions。INITIAL {result['cohorts']['INITIAL_ENTRY_OPPORTUNITY']}件、DIP {result['cohorts']['DIP_REPRICE_OPPORTUNITY']}件、計3,508件。異なる時刻に同じ銘柄のINITIALとDIPが出る場合はそれぞれの時刻で数える。",'', '全Safety9項目false、Fresh/OOS未開封。Selector/Entry/EXIT/Capital変更なし。集計後STOP。','']
 (out/'REPORT.md').write_text('\n'.join(lines))
 write('manifest.json',{'sourceHead':result['sourceHead'],'sourcePins':{str((SOURCE/p).relative_to(ROOT)):sha(SOURCE/p) for p in INPUTS},'codePin':sha(__file__),'outputPins':{p:sha(out/p) for p in ['summary.json','timestamp-counts.csv','REPORT.md']},'safety':SAFETY})
 print(json.dumps(result['panels'],ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();run(a.out)
