"""Finite explicit path runner; atomic per-session checkpoints and no refit/search."""
from io_utils import *
from exit_adapter import compile_plan
from portfolio import day_replay
import collections,sys,argparse
from statistics import median

def inputs():
 stream=rows(ROOT/'inputs/v5/candidate_stream');books={r['entry_id']:r for r in rows(ROOT/'inputs/v5/books')}
 table=json.loads((ROOT/'inputs/v5/arrival').read_bytes());split=json.loads((ROOT/'inputs/v5/split').read_bytes())
 cache={r['entry_id']:r for r in rows(PRI/'immutable/STATE_PREFIX_CACHE.jsonl.gz')}
 return stream,books,table,split,cache

def plans(books,cache):
 p=PRI/'immutable/EXIT_PLANS.jsonl.gz'
 if not p.exists():
  out=[]
  for key,c in sorted(cache.items()):
   out.append({'entry_id':key,'plan':compile_plan(books[key],c['buy_fill_minute'],c['frames'],c['control_intent_minute'])})
  gzsave(p,out)
 return {r['entry_id']:r['plan'] for r in rows(p)}

def run_path(window,arm,sessions,stream,books,table,exit_plans,outroot=PRI/'runs',stage='formal'):
 dest=outroot/window/arm
 assert not (dest/'RESULT.json').exists(),('completed path may not rerun',window,arm,stage)
 started=dest/'STARTED.json'
 done={}
 if started.exists():
  done={p.stem:json.loads(p.read_bytes()) for p in (dest/'sessions').glob('*.json')}
 else:
  save(started,{'window_id':window,'arm':arm,'stage':stage,'sessions':sessions,'input_cash':'1000000','empty_portfolio':True,'policy':pin(PUB/'WORK_SPEC.json'),'code':pin(ROOT/'portfolio.py')})
 cash=D(1000000);daily=[];decision=[];trade=[];curve=[];intents=[];last=None
 for index,day in enumerate(sessions):
  dayroot=dest/'sessions';checkpoint=dayroot/(day+'.json')
  if day in done:
   d=done[day]['daily'];ds=rows(dayroot/(day+'_DECISIONS.gz'));ts=rows(dayroot/(day+'_TRADES.gz'));cs=rows(dayroot/(day+'_CURVE.gz'));it=rows(dayroot/(day+'_INTENTS.gz'))
  else:
   candidates=[r for r in stream if r['session']==day]
   try:d,ds,ts,cs,it=day_replay(3,day,candidates,books,cash,True,'CAPITAL_MAX3_SLOT_RESERVE_V1',tables=table,exit_plans=exit_plans if arm=='E' else None)
   except Exception:
    import traceback
    save(dest/'EXCEPTION_CHECKPOINT.json',{'window_id':window,'arm':arm,'event_cursor':{'session':day,'last_completed_session':last},'cash_before_session':str(cash),'holding_pending_at_last_completed_session':{'holdings':{},'pending':{}},'traceback':traceback.format_exc(),'input_hashes':{n:pin(ROOT/'inputs/v5'/n) for n in ['candidate_stream','books','arrival','split']},'code_spec_hash':{'code':pin(ROOT/'portfolio.py'),'spec':pin(PUB/'WORK_SPEC.json')},'completed_sessions':[x['session'] for x in daily],'next_command':'python3 capital_v5_sharp_drop/campaign.py --window '+window,'uncompleted_obligation':'diagnose exception before resume; do not reset completed sessions'})
    raise
   for label,rr in [('DECISIONS',ds),('TRADES',ts),('CURVE',cs),('INTENTS',it)]:gzsave(dayroot/(day+'_'+label+'.gz'),rr)
   save(checkpoint,{'window_id':window,'arm':arm,'session_index':index,'event_cursor':{'session':day,'minute':931 if d['status']=='COMPLETE' else d.get('resume_snapshot',{}).get('window_arm_event_cursor',{}).get('minute')},'daily':d,'cash':d['ending_cash'] if d['status']=='COMPLETE' else d.get('resume_snapshot',{}).get('cash'),'holdings':d.get('resume_snapshot',{}).get('holdings',{}) if d['status']!='COMPLETE' else {},'pending_SELL':d.get('resume_snapshot',{}).get('pending_SELL',{}) if d['status']!='COMPLETE' else {},'State_reference':pin(PRI/'immutable/STATE_PREFIX_CACHE.jsonl.gz'),'input_hashes':{n:pin(ROOT/'inputs/v5'/n) for n in ['candidate_stream','books','arrival','split']},'code_spec_hash':{'code':pin(ROOT/'portfolio.py'),'spec':pin(PUB/'WORK_SPEC.json')},'completed_stage':'SESSION_COMPLETE' if d['status']=='COMPLETE' else 'BLOCK_PRESERVED','next_command':'python3 capital_v5_sharp_drop/campaign.py --window '+window})
  daily.append(d);decision.extend(ds);trade.extend(ts);curve.extend(cs);intents.extend(it)
  if d['status']!='COMPLETE':break
  cash=D(d['ending_cash']);last=day
 valid=len(daily)==len(sessions) and all(d['status']=='COMPLETE' for d in daily)
 summary={'window_id':window,'arm':arm,'stage':stage,'start_session':sessions[0],'end_session':sessions[-1],'planned_sessions':sessions,'calendar_span_inclusive_days':(__import__('datetime').date.fromisoformat(sessions[-1])-__import__('datetime').date.fromisoformat(sessions[0])).days+1,'completed_session_N':sum(d['status']=='COMPLETE' for d in daily),'attempted_session_N':len(daily),'last_complete_session':last,'status':'COMPLETE' if valid else 'BLOCKED','initial_cash':'1000000','final_equity':str(cash) if valid else None,'profit':str(cash-D(1000000)) if valid else None,'return_pct':fmt(native_pct(cash-D(1000000),D(1000000))) if valid else None,'unsettled_N':len(daily[-1]['open_obligations']) if daily else 0,'funded_N':sum(d['reason']=='FUNDED' for d in decision),'closed_N':len(trade),'SHARP_DROP_intent_N':sum(i.get('reason')=='SHARP_DROP_FIRST_OBSERVED' for i in intents),'SHARP_DROP_fill_N':sum(t['exit_kind']=='SHARP_DROP_FIRST_OBSERVED_EXIT_V0' for t in trade),'daily_series':daily,'blockers':[b for d in daily for b in d['blockers']],'last_snapshot':daily[-1].get('resume_snapshot') if daily else None}
 for label,rr in [('DECISIONS',decision),('TRADES',trade),('CURVE',curve),('INTENTS',intents)]:gzsave(dest/(label+'.jsonl.gz'),rr)
 save(dest/'RESULT.json',summary)
 return summary,decision,trade,curve,intents

def parity(window,data):
 dest=ROOT/'inputs/reset_archive/Ark_Capital_V51_PRIVATE/runs/V5_RESET20'/window
 result,ds,ts,cs,it=data
 manifest=json.loads((ROOT/'inputs/reset_archive/Ark_Capital_V51_PRIVATE/PRIVATE_MANIFEST.json').read_text())
 identity=[];mismatch=[]
 for p in sorted(dest.glob('*')):
  name='runs/V5_RESET20/'+window+'/'+p.name
  expected=next(r for r in manifest['files'] if r['path']==name)
  actual=pin(p);assert actual['sha256']==expected['sha256'] and actual['bytes']==expected['bytes'],name
  identity.append({'path':name,**actual})
 for label,rr in [('DECISIONS',ds),('TRADES',ts),('CURVE',cs),('INTENTS',it)]:
  old=rows(dest/(label+'.jsonl.gz'))
  if len(old)!=len(rr):mismatch.append({'ledger':label,'length':[len(old),len(rr)]});continue
  for i,(a,b) in enumerate(zip(old,rr)):
   # S6 wrapper-only labels carry no allocator/event semantics. Bind them explicitly.
   b=dict(b)
   if 'window_id' in a:b['window_id']=window
   if a.get('profile')=='V5_RESET20':b['profile']='V5_RESET20'
   if a!=b:
    changed={k:[a.get(k),b.get(k)] for k in set(a)|set(b) if a.get(k)!=b.get(k)}
    mismatch.append({'ledger':label,'row':i,'entry_id':a.get('entry_id'),'changed':changed})
 old=json.loads((dest/'COMPLETE.json').read_bytes())
 if old['daily_series']!=result['daily_series']:mismatch.append({'ledger':'DAILY','reason':'daily_series_exact_mismatch'})
 # S6 aggregate uses final_equity_jpy and is bound separately from original legacy chain.
 for field in ['final_equity_jpy','ending_cash','final_cash']:
  if field in old and old[field] is not None and D(str(old[field]))!=D(result['final_equity']):mismatch.append({'ledger':'FINAL','field':field,'saved':old[field],'actual':result['final_equity']})
 audit={'window_id':window,'status':'PASS' if not mismatch else 'FAIL','comparison':'EXACT_WHOLE_DECISION_QUANTITY_CASH_RELEASE_MTM_DAILY_LEDGERS','old_saved_file_identities':identity,'mismatch_N':len(mismatch),'mismatches':mismatch}
 save(PRI/'runs'/window/'CONTROL_PARITY.json',audit)
 if mismatch:raise AssertionError(('CONTROL_PARITY_FAILED',window,mismatch[:2]))
 return audit

def main():
 a=argparse.ArgumentParser();a.add_argument('--window',required=True);args=a.parse_args()
 assert json.loads((PUB/'SYNTHETIC_TEST_RESULTS.json').read_text())['status']=='PASS'
 stream,books,table,split,cache=inputs();ep=plans(books,cache)
 if args.window=='CHAIN38':sessions=split['OOF38']
 else:
  windows=json.loads((ROOT/'inputs/S6_COVERAGE_AND_WINDOWS.json').read_text())['windows'];w=next(w for w in windows if w['window_id']==args.window)
  assert args.window in ['W%02d'%i for i in range(13,22)] and w['coverage_complete'];sessions=w['sessions']
 expected=json.loads((PUB/'WORK_SPEC.json').read_text())
 for arm in ['C','E']:
  dest=PRI/'runs'/args.window/arm/'RESULT.json'
  if dest.exists():
   data=(json.loads(dest.read_text()),*[rows(dest.parent/(n+'.jsonl.gz')) for n in ['DECISIONS','TRADES','CURVE','INTENTS']])
  else:data=run_path(args.window,arm,sessions,stream,books,table,ep)
  if arm=='C':
   if args.window!='CHAIN38':parity(args.window,data)
   else:
    mismatch=[]
    for label,rr in zip(['native_decisions','native_trades','native_curve','native_intents'],data[1:]):
     old=rows(ROOT/'inputs/v5'/label)
     if old!=rr:mismatch.append(label)
    save(PRI/'runs'/args.window/'CONTROL_PARITY.json',{'status':'PASS' if not mismatch else 'FAIL','mismatched_ledgers':mismatch})
    assert not mismatch,('CHAIN38_CONTROL_PARITY',mismatch)
  r=data[0]
  print(json.dumps({k:r[k] for k in ['window_id','arm','status','final_equity','funded_N','SHARP_DROP_intent_N','SHARP_DROP_fill_N','completed_session_N']}),flush=True)
  if arm=='C' and r['status']!='COMPLETE':break
 save(PUB/(args.window+'_PATH_STATUS.json'),{'window_id':args.window,'arms':{arm:json.loads((PRI/'runs'/args.window/arm/'RESULT.json').read_text()) for arm in ['C','E'] if (PRI/'runs'/args.window/arm/'RESULT.json').exists()},'control_parity':json.loads((PRI/'runs'/args.window/'CONTROL_PARITY.json').read_text())['status']})
 # Strip individual blockers/snapshot from public daily aggregate status.
 p=PUB/(args.window+'_PATH_STATUS.json');o=json.loads(p.read_text())
 for r in o['arms'].values():
  r['blocker_N']=len(r.pop('blockers'));r.pop('last_snapshot',None)
  for d in r['daily_series']:d.pop('resume_snapshot',None);d['blocker_N']=len(d.pop('blockers'));d['open_obligation_N']=len(d.pop('open_obligations'))
 save(p,o)
 completed=[p.name for p in (PRI/'runs').iterdir() if (p/'E/RESULT.json').exists()]
 state=json.loads((PUB/'CURRENT_STATE.json').read_text());state.update(status='PRIMARY_WINDOW_CHECKPOINT' if args.window!='CHAIN38' else 'SECONDARY_CHECKPOINT',completed_window_paths=completed,next_action='publish_current_window_and_actual_GET_before_next_window',primary_E_complete_N=sum(json.loads((PRI/'runs'/w/'E/RESULT.json').read_text())['status']=='COMPLETE' for w in completed if w!='CHAIN38'),primary_C_verified_complete_N=sum((PRI/'runs'/w/'CONTROL_PARITY.json').exists() for w in completed if w!='CHAIN38'));save(PUB/'CURRENT_STATE.json',state)
 atomic(PUB/'RESUME_NEXT_ACTION.txt',('First commit/readback '+args.window+' checkpoint. Then next fixed ID, no completed path rerun.\n').encode())
if __name__=='__main__':main()
