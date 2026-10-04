"""Block-scoped training union and support gate. Zero test teacher construction."""
from common import *
from features import make
from frozen_trajectory import day_replay
from staircase import candidate_order
from execution import BUY,frozen_execution,eod_source
from teacher_oracle import solve,action
from decimal import Decimal as D
from collections import Counter
import sys
def execution_row(r,books,labels):
 b=books[r['entry_id']]
 if not b['capture_complete'] or not b.get('entry_actual_source'):return None
 s=frozen_execution(b) or eod_source(b['market'],r['session'])
 if not s or s['release_minute']<=r['entry_minute']:return None
 return {'entry_id':r['entry_id'],'session':r['session'],'symbol':r['symbol'],'entry_minute':r['entry_minute'],'release_minute':s['release_minute'],'debit':str(D(r['raw_reference'])*BUY*100),'credit':str(D(s['price'])*100),'potential':labels[r['entry_id']]['potential_return']}
def union(block,scored,books,labels,table):
 runtime={r['entry_id']:r for r in rows(SRC/'capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz')};stream=[dict(r,raw_reference=runtime[r['entry_id']]['raw_reference'],entry_timestamp=runtime[r['entry_id']]['entry_timestamp']) for r in scored if r['block']==block]
 states={};census=Counter();trajectory=[]
 for mode in ('v4','v5'):
  cash=D(1000000)
  for day in table['training_sessions']:
   candidates=[r for r in stream if r['session']==day]
   def hook(row,positions,pending,cash,eq,history,bsize,idx,prefix):
    occ=len(positions)+len(pending)
    if occ not in (1,2):return
    minimum=sum((D(r['raw_reference'])*BUY*100 for r in pending+[row]),D(0))
    if minimum>cash:census['not_cash_lot_fundable']+=1;return
    if any(r['symbol']==row['symbol'] for r in pending):census['same_symbol_pending']+=1;return
    if not all(execution_row(r,books,labels) for r in pending+[row]):census['invalid_current_or_pending_execution']+=1;return
    held={k:{f:(str(p[f]) if isinstance(p[f],D) else p[f]) for f in ('symbol','entry_minute','ML','m5','rank','quantity','buy','mark','mark_known_minute','band')} for k,p in sorted(positions.items())}
    feature=make(row,positions,pending,str(cash),str(eq),history,bsize,idx,table)
    state={'block':block,'session':day,'entry_id':row['entry_id'],'minute':row['entry_minute'],'cash':str(cash),'equity':str(eq),'held':held,'pending_ids':[r['entry_id'] for r in pending],'funded_prefix_ids':prefix,'occupancy':occ,'features':feature,'batch_size':bsize,'batch_order_index':idx,'history_ids':[r['entry_id'] for r in history]}
    key=hashlib.sha256(json.dumps(state,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if key not in states:states[key]=dict(state,state_key=key,trajectories=[mode])
    elif mode not in states[key]['trajectories']:states[key]['trajectories'].append(mode)
    census[mode+'_raw_opportunities']+=1
   result,ds,ts,frames,it=day_replay(3,day,candidates,books,cash,True,'TRAINING_TEACHER_ONLY_'+mode.upper(),tables={str(block):table},state_hook=hook,trajectory_mode=mode)
   trajectory.append({'block':block,'mode':mode,**result})
   assert result['status']=='COMPLETE',('TRAINING_EXECUTION_BLOCKED',mode,day,result['blockers'])
   cash=D(result['ending_cash'])
 return list(states.values()),stream,dict(census),trajectory
def main():
 block=int(sys.argv[1]);split=json.loads((SOURCE/'repo/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json').read_text());spec=split['blocks'][block-1]
 table=json.loads((V5OUT/'ARRIVAL_TABLE.json').read_text())[str(block)];assert table['training_sessions']==spec['train'] and not set(spec['train'])&set(spec['test']) and max(spec['train'])<min(spec['test'])
 scored=rows(V5PRIVATE/'TRAINING_ONLY_SCORED_ARRIVALS.jsonl.gz');books={r['entry_id']:r for r in rows(SRC/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};labels={r['entry_id']:r for r in rows(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
 states,stream,census,trajectory=union(block,scored,books,labels,table)
 gzwrite(PRIVATE/f'TRAINING_STATES_BLOCK_{block:02d}.jsonl.gz',states);save(PRIVATE/f'TRAINING_TRAJECTORIES_BLOCK_{block:02d}.json',trajectory)
 print(json.dumps({'block':block,'unique_states':len(states),'occupancy':dict(Counter(s['occupancy'] for s in states)),'census':census}),flush=True)
 byid={r['entry_id']:r for r in stream};out=[]
 for j,state in enumerate(states):
  cur=byid[state['entry_id']];remaining=[r for r in stream if r['session']==state['session'] and r['admission'] and r['entry_minute']<920 and (r['entry_id'] in state['pending_ids'] or (r['entry_minute'],candidate_order(r))>=(cur['entry_minute'],candidate_order(cur)))]
  a=[z for r in remaining if (z:=execution_row(r,books,labels)) is not None];h=[]
  for key,p in state['held'].items():
   z=execution_row(byid[key],books,labels);assert z and z['release_minute']>state['minute'];h.append({'entry_id':key,'release_minute':z['release_minute'],'credit':str(D(z['credit'])*(p['quantity']//100))})
  aa=solve(state,a,h,labels,True);rr=solve(state,a,h,labels,False);act,why=action(labels[cur['entry_id']]['potential_return']>=.05,aa,rr)
  out.append({'state_key':state['state_key'],'block':block,'session':state['session'],'entry_id':state['entry_id'],'occupancy':state['occupancy'],'rank':cur['rank'],'features':state['features'],'teacher':act,'reason':why,'current_U5':labels[cur['entry_id']]['potential_return']>=.05,'ACCEPT':aa,'RESERVE':rr,'U5_margin':aa['U5']-rr['U5'],'candidate_physical_continuation':a,'held_release_obligations':h})
  if (j+1)%50==0:print(json.dumps({'block':block,'teachers_complete':j+1,'total':len(states)}),flush=True)
 gzwrite(PRIVATE/f'TRAINING_TEACHERS_BLOCK_{block:02d}.jsonl.gz',out)
 counts=Counter(r['teacher'] for r in out);occ=Counter(r['occupancy'] for r in out);passes=len(out)>=100 and counts['ACCEPT']>=20 and counts['RESERVE']>=20 and occ[1]>=20 and occ[2]>=20
 gate={'exact_jst':now(),'block':block,'unique_examples':len(out),'ACCEPT':counts['ACCEPT'],'RESERVE':counts['RESERVE'],'occupancy1':occ[1],'occupancy2':occ[2],'support_pass':passes,'state_census':census,'U5_margin_distribution':dict(Counter(r['U5_margin'] for r in out)),'U5_tie_priority_ACCEPT':sum(r['current_U5'] and r['U5_margin']==0 and r['teacher']=='ACCEPT' for r in out),'teacher_sha256':sha(PRIVATE/f'TRAINING_TEACHERS_BLOCK_{block:02d}.jsonl.gz'),'state_sha256':sha(PRIVATE/f'TRAINING_STATES_BLOCK_{block:02d}.jsonl.gz'),'training_sessions':spec['train'],'test_sessions_used':0,'slot_fits':0,'main_replay':0,'status':'SUPPORT_PASS' if passes else 'V6_SLOT_TEACHER_SUPPORT_BLOCKED'}
 save(OUT/f'TEACHER_SUPPORT_BLOCK_{block:02d}.json',gate);print(json.dumps(gate),flush=True)
if __name__=='__main__':main()
