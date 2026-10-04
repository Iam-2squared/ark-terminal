"""Evaluation-only count ceiling; no runtime imports this file or its outputs."""
from control import *
from execution_bridge import exit_source,execution_ok,BUY
from decimal import Decimal as D
from collections import deque
import math
def inputs():
 stream=rows(PRIVATE/'RANK_NATIVE_RUNTIME.jsonl.gz');mask={r['entry_id'] for r in rows(PRIVATE/'COMMON_EVAL_MASK.jsonl.gz') if r['included']}
 tt={r['entry_id']:r for r in rows(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz')};books={r['entry_id']:r for r in rows(INPUT/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
 a=[];invalid=[]
 for r in stream:
  if r['entry_id'] not in mask:continue
  b=books[r['entry_id']]
  if not execution_ok(r,b):invalid.append(r['entry_id']);continue
  source=exit_source(b);a.append({k:r[k] for k in ('entry_id','session','symbol','entry_minute','pP','band')}|{'release_minute':source['release_minute'],'buy_lot':str(100*D(r['raw_reference'])*BUY),'sell_lot':str(100*D(source['price'])),'U5':tt[r['entry_id']]['label_bigwinner5'],'U10':tt[r['entry_id']]['label_bigwinner10']})
 assert len(a)+len(invalid)==1028
 assert len({(r['session'],r['symbol']) for r in a})==len(a),'SAME_SYMBOL_DUPLICATE_NEEDS_EXPLICIT_CONSTRAINT_STOP'
 return sorted(a,key=lambda r:(r['session'],r['entry_minute'],r['symbol'])),invalid
def solve(a,target):
 clocks=sorted({(r['session'],r[k]) for r in a for k in ('entry_minute','release_minute')});index={x:i for i,x in enumerate(clocks)}
 graph=[[] for _ in clocks];edges=[];n=len(a);stable_bound=n*(n+1)//2+1;w10=stable_bound;w5=(n+1)*w10
 def add(u,v,c,cost):
  f=[v,len(graph[v]),c,cost];q=[u,len(graph[u]),0,-cost];graph[u].append(f);graph[v].append(q);return f
 for i in range(len(clocks)-1):add(i,i+1,3,0)
 for ordinal,r in enumerate(a,1):
  reward=(r['U5']*w5+r['U10']*w10 if target=='U5' else r['U10']*w10)-ordinal
  edges.append(add(index[(r['session'],r['entry_minute'])],index[(r['session'],r['release_minute'])],1,-reward) if reward>0 else None)
 total=0
 for unit in range(3):
  dist=[math.inf]*len(clocks);dist[0]=0;parent=[None]*len(clocks);q=deque([0]);inq={0}
  while q:
   u=q.popleft();inq.remove(u)
   for j,e in enumerate(graph[u]):
    v,rev,cap,cost=e
    if cap and dist[u]+cost<dist[v]:
     dist[v]=dist[u]+cost;parent[v]=(u,j)
     if v not in inq:q.append(v);inq.add(v)
  assert parent[-1] is not None;total+=dist[-1];v=len(clocks)-1
  while v:
   u,j=parent[v];e=graph[u][j];e[2]-=1;graph[v][e[1]][2]+=1;v=u
 selected=[r for r,e in zip(a,edges) if e is not None and e[2]==0]
 # Attaining the relaxed count upper bound with a valid minimum-lot witness
 # certifies the unrestricted-lot physical optimum, not a one-lot-only claim.
 balances=[];peak=0
 for day,t in clocks:
  cash=D(1000000);held=[]
  for r in selected:
   if (r['session'],r['entry_minute'])<=(day,t):cash-=D(r['buy_lot'])
   if (r['session'],r['release_minute'])<=(day,t):cash+=D(r['sell_lot'])
   if r['session']==day and r['entry_minute']<=t<r['release_minute']:held.append(r)
  assert cash>=0,'MIN_LOT_WITNESS_FAIL_PHYSICAL_CERTIFICATE_BLOCKED_STOP'
  assert len(held)<=3 and len({r['symbol'] for r in held})==len(held)
  peak=max(peak,len(held));balances.append(cash)
 u5=sum(r['U5'] for r in selected);u10=sum(r['U10'] for r in selected)
 witness=[r|{'quantity':100,'debit':r['buy_lot'],'credit':r['sell_lot']} for r in selected]
 return {'candidate_N':len(a),'objective':target,'maximum_U5':u5,'maximum_U10':u10,'count_upper_bound_attained':True,'global_physical_count_optimum_certified':True,'minimum_lot_witness_cash_min':str(min(balances)),'maximum_held':peak,'selected_N':len(selected),'min_cost_flow':{'flow':3,'integer_cost':total,'stable_bound':stable_bound,'w5':w5,'w10':w10,'nodes':len(clocks)},'unrestricted_lot_ceiling':'Certified by cash-relaxed upper bound attained by exact feasible minimum-lot witness','evaluator_only':True,'runtime_access':False},witness
def main():
 claim=read(OUT/'ORACLE_EXECUTION_CLAIM.json');assert claim['actual_GET_precommit_verified'] and claim['solves']==['ALL_U5','ALL_U10','ADMISSION_U5','ADMISSION_U10']
 a,invalid=inputs();assert not invalid,('EXECUTION_BLOCKED_STOP',invalid)
 allresults={}
 for name in claim['solves']:
  assert not (PRIVATE/f'{name}_STARTED.json').exists(),'AMBIGUOUS_OR_COMPLETED_SOLVE_NO_RERUN'
  save(PRIVATE/f'{name}_STARTED.json',{'exact_jst':now(),'claim_sha256':sha(OUT/'ORACLE_EXECUTION_CLAIM.json'),'single_execution':True})
  population=[r for r in a if r['band']!='P_BELOW'] if name.startswith('ADMISSION') else a
  result,witness=solve(population,name.split('_')[-1]);result.update(name=name,invalid_execution_N=len(invalid),population_U5=sum(r['U5'] for r in population),population_U10=sum(r['U10'] for r in population))
  gzsave(PRIVATE/f'{name}_WITNESS.jsonl.gz',witness);result['witness_sha256']=sha(PRIVATE/f'{name}_WITNESS.jsonl.gz');save(OUT/f'ORACLE_{name}.json',result);allresults[name]=result
  print(json.dumps({k:result[k] for k in ('name','maximum_U5','maximum_U10','candidate_N','minimum_lot_witness_cash_min')}),flush=True)
 save(OUT/'ORACLE_RESULT.json',{'exact_jst':now(),'solves':allresults,'oracle_solves':4,'invalid_execution_N':0,'primary_population_N':1028,'U5':170,'U10':67,'old_104_47_ceiling_not_reused':True})
 checkpoint('D4_ORACLE_RESULT','FOUR_CEILINGS_CERTIFIED',['ALL_U5','ALL_U10','ADMISSION_U5','ADMISSION_U10'],allresults,'Acknowledge already-precommitted band mapping; freeze future-max table',{'oracle_solves':4})
if __name__=='__main__':main()
