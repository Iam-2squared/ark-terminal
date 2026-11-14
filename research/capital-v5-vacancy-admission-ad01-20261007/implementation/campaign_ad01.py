"""AD01 fixed finite campaign; completed paths are never rerun by the formal runner."""
from pathlib import Path
from decimal import Decimal
import argparse, datetime, gzip, hashlib, json, traceback
ROOT=Path(__file__).resolve().parents[1]
D=Decimal
def read(p): return json.loads(Path(p).read_bytes())
def rows(p): return [json.loads(l) for l in gzip.decompress(Path(p).read_bytes()).splitlines() if l]
def write(p,b):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_bytes(b);t.replace(p)
def save(p,x):write(p,(json.dumps(x,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())
def gzsave(p,x):write(p,gzip.compress((''.join(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n' for r in x)).encode(),mtime=0))
def pin(p):
 b=Path(p).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def baseline(w):return ROOT/'baseline/private/runs'/w/'E'
def inputs():
 return rows(ROOT/'inputs/candidate_stream'),{r['entry_id']:r for r in rows(ROOT/'inputs/books')},read(ROOT/'inputs/arrival'),{r['entry_id']:r['plan'] for r in rows(ROOT/'private/immutable/EXIT_PLANS.jsonl.gz')}
def bindings():
 return {str(p.relative_to(ROOT)):pin(p) for p in [ROOT/'public/SPEC_AD01_PRECOMMIT.json',ROOT/'implementation/admission_adapter.py',ROOT/'implementation/baseline_adapter.py',ROOT/'native/allocation.py',ROOT/'inputs/candidate_stream',ROOT/'inputs/books',ROOT/'inputs/arrival',ROOT/'private/immutable/EXIT_PLANS.jsonl.gz']}
def run(w,policy,outroot):
 from admission_adapter import day_replay
 dest=outroot/w/policy
 assert not (dest/'RESULT.json').exists(),('completed_path_rerun_forbidden',w,policy)
 stream,books,tables,plans=inputs();old=read(baseline(w)/'RESULT.json');sessions=old['planned_sessions'];bind=bindings()
 if (dest/'STARTED.json').exists():assert read(dest/'STARTED.json')['bindings']==bind,'RESUME_BINDING_CHANGED'
 else:save(dest/'STARTED.json',{'window_id':w,'policy':policy,'bindings':bind,'planned_sessions':sessions,'initial_cash':'1000000'})
 cash=D(1000000);daily=[];ledgers={n:[] for n in ['DECISIONS','TRADES','CURVE','INTENTS']}
 for index,day in enumerate(sessions):
  checkpoint=dest/'sessions'/(day+'.json')
  if checkpoint.exists():
   cp=read(checkpoint);assert cp['bindings']==bind and D(cp['daily']['starting_cash'])==cash
   d=cp['daily'];values=[rows(dest/'sessions'/(day+'_'+n+'.gz')) for n in ledgers]
  else:
   try:d,*values=day_replay(3,day,[r for r in stream if r['session']==day],books,cash,True,'CAPITAL_MAX3_SLOT_RESERVE_V1',tables=tables,exit_plans=plans,policy=policy)
   except Exception:
    save(dest/'EXCEPTION_CHECKPOINT.json',{'window_id':w,'policy':policy,'session':day,'cash_before_session':str(cash),'completed_sessions':[d['session'] for d in daily],'bindings':bind,'traceback':traceback.format_exc(),'next_command':f'python work/ad01/implementation/campaign_ad01.py formal --window {w} --policy {policy}'})
    raise
   for n,rr in zip(ledgers,values):gzsave(dest/'sessions'/(day+'_'+n+'.gz'),rr)
   save(checkpoint,{'window_id':w,'policy':policy,'session_index':index,'daily':d,'bindings':bind,'flat_confirmed':d['status']=='COMPLETE' and not d['open_obligations'],'next_command':f'python work/ad01/implementation/campaign_ad01.py formal --window {w} --policy {policy}'})
  daily.append(d)
  for n,rr in zip(ledgers,values):ledgers[n].extend(rr)
  if d['status']!='COMPLETE':break
  assert not d['open_obligations'];cash=D(d['ending_cash'])
 valid=len(daily)==len(sessions) and all(d['status']=='COMPLETE' for d in daily)
 result={'window_id':w,'arm':policy,'status':'COMPLETE' if valid else 'BLOCKED','initial_cash':'1000000','final_equity':str(cash) if valid else None,'profit':str(cash-D(1000000)) if valid else None,'return_pct':str((cash/D(1000000)-1)*100) if valid else None,'planned_sessions':sessions,'start_session':sessions[0],'end_session':sessions[-1],'calendar_span_inclusive_days':(datetime.date.fromisoformat(sessions[-1])-datetime.date.fromisoformat(sessions[0])).days+1,'completed_session_N':sum(d['status']=='COMPLETE' for d in daily),'daily_series':daily,'funded_N':sum(d['reason']=='FUNDED' for d in ledgers['DECISIONS']),'closed_N':len(ledgers['TRADES']),'SHARP_DROP_fill_N':sum(t['exit_kind']=='SHARP_DROP_FIRST_OBSERVED_EXIT_V0' for t in ledgers['TRADES']),'SHARP_DROP_intent_N':sum(i.get('reason')=='SHARP_DROP_FIRST_OBSERVED' for i in ledgers['INTENTS']),'unsettled_N':sum(len(d['open_obligations']) for d in daily),'blockers':[b for d in daily for b in d['blockers']]}
 for n,rr in ledgers.items():gzsave(dest/(n+'.jsonl.gz'),rr)
 save(dest/'RESULT.json',result)
 return result
def parity():
 target=ROOT/'public/E0_PARITY_RECEIPT.json';assert not target.exists(),'parity_campaign_once'
 checks=[]
 for w in ['W13','CHAIN38']:
  actual=run(w,'E0',ROOT/'private/parity');prior=read(baseline(w)/'RESULT.json');mismatch=[]
  for n in ['DECISIONS','TRADES','CURVE','INTENTS']:
   a=rows(ROOT/'private/parity'/w/'E0'/(n+'.jsonl.gz'));b=rows(baseline(w)/(n+'.jsonl.gz'))
   if a!=b:mismatch.append({'ledger':n,'row_counts':[len(a),len(b)],'first_difference':next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),None)})
  if actual['daily_series']!=prior['daily_series']:mismatch.append({'ledger':'daily_series'})
  if D(actual['final_equity'])!=D(prior['final_equity']):mismatch.append({'ledger':'final_equity'})
  checks.append({'window_id':w,'status':'PASS' if not mismatch else 'FAIL','mismatches':mismatch,'verified_final':actual['final_equity']})
  print(json.dumps(checks[-1]),flush=True)
  if mismatch:break
 save(target,{'status':'PASS' if len(checks)==2 and all(x['status']=='PASS' for x in checks) else 'FAIL','replay_path_N':len(checks),'scope':'Original E0 full decisions quantities cash MTM intents fill release daily final exact comparison','checks':checks})
 assert read(target)['status']=='PASS','E0_PARITY_FAIL'
def reproduction():
 target=ROOT/'public/REPRODUCTION_RECEIPT.json';assert not target.exists(),'one_reproduction_campaign_only'
 checks=[]
 for w in [f'W{i:02}' for i in range(13,22)]+['CHAIN38']:
  for policy in ['H1','H2']:
   original=ROOT/'private/runs'/w/policy
   if not (original/'RESULT.json').exists() or read(original/'RESULT.json')['status']!='COMPLETE':continue
   run(w,policy,ROOT/'private/reproduction')
   differences=[];identities={}
   for name in ['RESULT.json']+[n+'.jsonl.gz' for n in ['DECISIONS','TRADES','CURVE','INTENTS']]:
    a=pin(original/name);b=pin(ROOT/'private/reproduction'/w/policy/name)
    if a!=b:differences.append(name)
    identities[name]=a
   checks.append({'window_id':w,'policy':policy,'exact_payload':not differences,'differences':differences,'payload_pins':identities})
   print(json.dumps({'reproduction':w,'policy':policy,'exact_payload':not differences}),flush=True)
 save(target,{'status':'PASS' if len(checks)==20 and all(x['exact_payload'] for x in checks) else 'PARTIAL_OR_FAIL','campaign_N':1,'path_N':len(checks),'checks':checks})
def main():
 a=argparse.ArgumentParser();a.add_argument('stage',choices=['parity','formal','reproduction']);a.add_argument('--window');a.add_argument('--policy',choices=['H1','H2']);args=a.parse_args()
 assert read(ROOT/'public/SYNTHETIC_TEST_RESULTS.json')['status']=='PASS'
 if args.stage=='parity':parity();return
 assert read(ROOT/'public/E0_PARITY_RECEIPT.json')['status']=='PASS'
 if args.stage=='reproduction':reproduction();return
 assert args.window in [f'W{i:02}' for i in range(13,22)]+['CHAIN38'] and args.policy
 r=run(args.window,args.policy,ROOT/'private/runs');print(json.dumps({k:r[k] for k in ['window_id','arm','status','final_equity','funded_N','SHARP_DROP_fill_N']}),flush=True)
if __name__=='__main__':main()
