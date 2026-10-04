"""Evaluation-only label-blind lexicographic interval min-cost flow.

No runtime/policy module imports this module or its output. A relaxed scheduling
upper bound is called certified only when an exact cash-feasible witness attains
it. If the witness fails, STOP, not a second solve or objective rescue.
"""
from control import *
from execution_bridge import exit_source,execution_ok,BUY
from decimal import Decimal as D
from collections import deque,Counter
import math
NAME='PPRANK_CLAIRVOYANT_ADMISSION_DIAGNOSTIC'
def candidates():
 mask={r['entry_id'] for r in rows(PIN/'COMMON_EVAL_MASK.jsonl.gz') if r['included']};books={r['entry_id']:r for r in rows(INPUT/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};a=[];unavailable=[]
 for r in rows(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz'):
  if r['entry_id'] not in mask or r['band']=='P_BELOW':continue
  b=books[r['entry_id']]
  if not execution_ok(r,b):unavailable.append(r['entry_id']);continue
  src=exit_source(b)
  a.append({k:r[k] for k in ('entry_id','session','symbol','entry_timestamp','entry_minute','pP','r','rank_units','train_N','band')}|{'release_minute':src['release_minute'],'rank_utility':round(r['r']*1000000),'buy_lot':str(D(r['raw_reference'])*BUY*100),'sell_lot':str(D(src['price'])*100)})
 a.sort(key=lambda r:(r['entry_timestamp'],r['symbol'],r['entry_id']))
 assert len(a)==488 and len(unavailable)==2 and len({(r['session'],r['symbol']) for r in a})==488
 return a,unavailable
def solve(a):
 clocks=sorted({(r['session'],r[k]) for r in a for k in ('entry_minute','release_minute')});index={x:i for i,x in enumerate(clocks)};graph=[[] for _ in clocks];n=len(a);tie_base=1<<n;edges=[]
 def add(u,v,cap,cost):
  edge=[v,len(graph[v]),cap,cost];graph[u].append(edge);graph[v].append([u,len(graph[u])-1,0,-cost]);return edge
 for i in range(len(clocks)-1):add(i,i+1,3,0)
 for ordinal,r in enumerate(a):
  reward=(r['rank_utility']*(n+1)+1)*tie_base+(1<<(n-ordinal-1))
  edges.append(add(index[r['session'],r['entry_minute']],index[r['session'],r['release_minute']],1,-reward))
 total=0
 for _ in range(3):
  distance=[math.inf]*len(clocks);distance[0]=0;parent=[None]*len(clocks);q=deque([0]);queued={0}
  while q:
   u=q.popleft();queued.remove(u)
   for j,e in enumerate(graph[u]):
    v,rev,cap,cost=e
    if cap and distance[u]+cost<distance[v]:
     distance[v]=distance[u]+cost;parent[v]=(u,j)
     if v not in queued:q.append(v);queued.add(v)
  assert parent[-1] is not None;total+=distance[-1];v=len(clocks)-1
  while v:
   u,j=parent[v];e=graph[u][j];e[2]-=1;graph[v][e[1]][2]+=1;v=u
 selected=[r for r,e in zip(a,edges) if e[2]==0];cash=D(1000000);minimum=cash;peak=0;held={};events={}
 for r in selected:
  events.setdefault((r['session'],r['entry_minute']),{'buys':[],'sells':[]})['buys'].append(r)
  events.setdefault((r['session'],r['release_minute']),{'buys':[],'sells':[]})['sells'].append(r)
 for clock,event in sorted(events.items()):
  for r in sorted(event['sells'],key=lambda r:r['entry_id']):assert r['entry_id'] in held;held.pop(r['entry_id']);cash+=D(r['sell_lot'])
  for r in sorted(event['buys'],key=lambda r:(r['entry_timestamp'],r['symbol'],r['entry_id'])):cash-=D(r['buy_lot']);held[r['entry_id']]=r;minimum=min(minimum,cash)
  assert cash>=0,'CASH_WITNESS_BLOCKED_NO_SECOND_SOLVE';assert len(held)<=3 and len({r['symbol'] for r in held.values()})==len(held);peak=max(peak,len(held))
 assert not held
 objective=sum(r['rank_utility'] for r in selected);return selected,{'selected_N':len(selected),'rank_utility_integer_sum':objective,'sum_r':math.fsum(r['r'] for r in selected),'combined_integer_cost':str(total),'stable_tie':'lexicographically prefer selected earlier Entry timestamp / symbol / entry_id; exact arbitrary-precision bitset','rounding':'Python ties-to-even round(r*1000000), frozen float r','cash_minimum_exact':str(minimum),'final_cash_exact':str(cash),'MAX3_peak':peak,'cash_relaxed_bound_attained_by_exact_minimum_lot_witness':True,'quantity':100,'unrestricted_lot_objective_optimum_certified':True}
def precommit():
 save(OUT/'PPRANK_DIAGNOSTIC_PRECOMMIT.json',{'exact_jst':now(),'name':NAME,'primary_solve_budget':1,'independent_solve_budget':1,'population':'v7 executable admission 488; two unexecutable negatives remain in runtime 490','objective':['maximize sum round(r*1000000)','maximize selected N','lexicographic stable Entry timestamp / symbol / entry_id'],'U5_U10_PnL_in_objective':False,'constraints':['Frozen Entry/release','MAX3','same symbol','cash-only initial 1000000','minimum lot100','exact execution availability','no replacement/forced EXIT'],'algorithm':'three-unit integer min-cost flow (SPFA residual paths) cash-relaxed scheduling bound, attained exact minimum-lot cash witness; fail-closed if unattained, no rescue solve','tie_encoding':'(utility*(N+1)+selected_count)*2**N + earlier-selection bitset','runtime_access':False,'policy_design_access':False,'code_sha256':{'diagnostic.py':sha(CODE/'diagnostic.py'),'execution_bridge.py':sha(CODE/'execution_bridge.py')},'Safety':SAFETY})
 checkpoint('D4_PPRANK_DIAGNOSTIC_PRECOMMIT','ONE_LABEL_BLIND_DIAGNOSTIC_PRECOMMITTED',['objective','constraints','integer lex tie','cash certificate stop rule'],{'primary_solve_claim':1,'labels_in_objective':0},'Commit and actual GET this claim before the one solve')
def main():
 assert (OUT/'receipts/D4_PPRANK_DIAGNOSTIC_PRECOMMIT_ACTUAL_GET.json').exists()
 claim=read(OUT/'PPRANK_DIAGNOSTIC_PRECOMMIT.json')
 for n,v in claim['code_sha256'].items():assert sha(CODE/n)==v
 save(PRIVATE/f'{NAME}_STARTED.json',{'exact_jst':now(),'single_execution':True,'claim_sha256':sha(OUT/'PPRANK_DIAGNOSTIC_PRECOMMIT.json'),'rerun_allowed':False})
 a,unavailable=candidates();selected,result=solve(a)
 # Outcome teacher is loaded only after the schedule is completely solved.
 teacher={r['entry_id']:r for r in rows(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz')}
 result.update(U5=sum(teacher[r['entry_id']]['label_bigwinner5'] for r in selected),U10=sum(teacher[r['entry_id']]['label_bigwinner10'] for r in selected),below2_N=sum(teacher[r['entry_id']]['potential_return']<.02 for r in selected),rank_decile=dict(Counter(min(10,max(1,int(r['r']*10)+1)) for r in selected)))
 gzsave(PRIVATE/f'{NAME}_WITNESS.jsonl.gz',[r|{'quantity':100} for r in selected]);result.update(exact_jst=now(),name=NAME,candidate_N=488,execution_unavailable_N=2,execution_unavailable_ids=unavailable,witness_sha256=sha(PRIVATE/f'{NAME}_WITNESS.jsonl.gz'),evaluator_only=True,runtime_access=False,U5_upper_bound_claim=False,primary_solve_N=1,new_fits=0)
 save(OUT/'PPRANK_DIAGNOSTIC_RESULT.json',result);checkpoint('D5_PPRANK_DIAGNOSTIC_RESULT','PPRANK_CLAIRVOYANT_DIAGNOSTIC_FIXED',['one label-blind diagnostic solve','cash/interval certificate'],result,'B1/B2 as instructed, not changed by anatomy/diagnostic',{'primary_pP_diagnostic_solve':1});print(json.dumps(result))
if __name__=='__main__':
 import sys
 {'precommit':precommit,'solve':main}[sys.argv[1]]()
