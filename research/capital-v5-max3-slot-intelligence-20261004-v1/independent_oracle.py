"""Independent residual min-cost-flow bound + interleaved integer-sizing MILP.

Imports only standalone Fraction IO/market validity, never Primary oracle,
policy, arrival or replay modules. Exact Fraction validation of both witnesses.
"""
from independent_engine import read,actual,minute,F,ROOT
from collections import deque
from pathlib import Path
import json,gzip,math
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import csr_matrix
W=ROOT.parent;S=W/'source_main';P=W/'capital_v5_slot_private';OUT=ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1'
def candidate_inputs():
 rows=read(S/'capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz');tt={r['entry_id']:r for r in read(S/'inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')};books={r['entry_id']:r for r in read(S/'inputs/v3/bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};candidates=[]
 for r in rows:
  if r['ML']<1 or r['entry_minute']>=920:continue
  b=books[r['entry_id']];x=b['frozen_exit'];fill=None
  if x['sell_status']=='FILLED' and minute(x['sell_source_assumed_available_at'])<=920:
   source=next((z for z in b['market'] if z['minute']==x['sell_minute']),None)
   if source and actual(source):fill=(minute(x['sell_source_assumed_available_at']),F(source['O'] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else source['C'])*F(9995,10000))
  else:
   regular=[z for z in b['market'] if z.get('session')==r['session'] and 920<=z['minute']<925 and actual(z)]
   auction=[z for z in b['market'] if z.get('session')==r['session'] and z['minute']==930 and actual(z,True)]
   if regular:
    source=min(regular,key=lambda z:z['minute']);fill=(source['minute']+1,F(source['O'])*F(9995,10000))
   elif auction:
    source=auction[0];fill=(931,F(source['C'])*F(9995,10000))
  if fill and b['capture_complete'] and b.get('entry_actual_source'):
   release,price=fill;candidates.append({'entry_id':r['entry_id'],'session':r['session'],'symbol':r['symbol'],'entry_minute':r['entry_minute'],'release_minute':release,'potential':tt[r['entry_id']]['potential_return'],'buy_lot':100*F(r['raw_reference'])*F(10005,10000),'sell_lot':100*price})
 assert len({(r['session'],r['symbol']) for r in candidates})==len(candidates)
 return candidates
def flow_bound(a):
 clocks=sorted({(r['session'],r[k]) for r in a for k in ('entry_minute','release_minute')});index={z:i for i,z in enumerate(clocks)};N=len(clocks);graph=[[] for _ in clocks];task_edges=[]
 def add(u,v,capacity,cost):
  forward=[v,len(graph[v]),capacity,cost];reverse=[u,len(graph[u]),0,-cost];graph[u].append(forward);graph[v].append(reverse);return forward
 for i in range(N-1):add(i,i+1,3,0)
 for r in a:
  reward=int(r['potential']>=.05)*1000000+int(r['potential']>=.10)*1000+int(.03<=r['potential']<.05)
  task_edges.append(add(index[(r['session'],r['entry_minute'])],index[(r['session'],r['release_minute'])],1,-reward))
 total_cost=0
 for unit in range(3):
  distance=[math.inf]*N;distance[0]=0;parent=[None]*N;queue=deque([0]);queued={0}
  while queue:
   u=queue.popleft();queued.remove(u)
   for e,z in enumerate(graph[u]):
    v,reverse,capacity,cost=z
    if capacity and distance[u]+cost<distance[v]:
     distance[v]=distance[u]+cost;parent[v]=(u,e)
     if v not in queued:queue.append(v);queued.add(v)
  assert parent[-1] is not None
  total_cost+=distance[-1];v=N-1
  while v:
   u,e=parent[v];edge=graph[u][e];edge[2]-=1;graph[v][edge[1]][2]+=1;v=u
 selected=[r for r,e in zip(a,task_edges) if e[2]==0]
 counts=[sum(r['potential']>=k for r in selected) for k in (.05,.10)]+[sum(.03<=r['potential']<.05 for r in selected)]
 assert -total_cost==counts[0]*1000000+counts[1]*1000+counts[2]
 return counts,{'flow_units':3,'integer_reward':-total_cost,'time_node_N':N,'candidate_arc_N':len(a)}
def cash_validate(witness,a):
 amap={r['entry_id']:r for r in a};selected=[]
 for r in witness:
  source=amap[r['entry_id']];q=r['quantity'];assert q>=100 and q%100==0
  assert F(r['debit'])==source['buy_lot']*(q//100) and F(r['credit'])==source['sell_lot']*(q//100)
  assert r['entry_minute']==source['entry_minute'] and r['release_minute']==source['release_minute'];selected.append((source,q//100))
 times=sorted({(r['session'],r[k]) for r in a for k in ('entry_minute','release_minute')});minimum=F(1000000);peak=0
 for day,t in times:
  balance=F(1000000);held=0
  for r,lots in selected:
   if (r['session'],r['entry_minute'])<=(day,t):balance-=lots*r['buy_lot']
   if (r['session'],r['release_minute'])<=(day,t):balance+=lots*r['sell_lot']
   held+=r['session']==day and r['entry_minute']<=t<r['release_minute']
  assert balance>=0 and held<=3;minimum=min(minimum,balance);peak=max(peak,held)
 counts=[sum(r['potential']>=k for r,lots in selected) for k in (.05,.10)]+[sum(.03<=r['potential']<.05 for r,lots in selected)]
 cost=sum((lots*(r['buy_lot']+r['sell_lot']) for r,lots in selected),F(0))
 return counts,cost,minimum,peak
def minimum_turnover(a,counts):
 n=len(a);times=sorted({(r['session'],r[k]) for r in a for k in ('entry_minute','release_minute')});matrix=[];lo=[];hi=[];maxlots=[]
 for r in a:
  ceiling=F(1000000)
  for z in a:
   if (z['session'],z['release_minute'])<=(r['session'],r['entry_minute']) and z['sell_lot']>z['buy_lot']:ceiling*=z['sell_lot']/z['buy_lot']
  maxlots.append(int(ceiling/r['buy_lot'])+1)
 for day,t in times:
  row=np.zeros(2*n)
  for i,r in enumerate(a):row[2*i]=r['session']==day and r['entry_minute']<=t<r['release_minute']
  matrix.append(row);lo.append(0);hi.append(3)
  row=np.zeros(2*n)
  for i,r in enumerate(a):
   value=F(0)
   if (r['session'],r['entry_minute'])<=(day,t):value-=r['buy_lot']
   if (r['session'],r['release_minute'])<=(day,t):value+=r['sell_lot']
   row[2*i+1]=float(value/1000000)
  matrix.append(row);lo.append(-1);hi.append(np.inf)
 for i,M in enumerate(maxlots):
  row=np.zeros(2*n);row[2*i]=-1;row[2*i+1]=1;matrix.append(row);lo.append(0);hi.append(np.inf)
  row=np.zeros(2*n);row[2*i]=M;row[2*i+1]=-1;matrix.append(row);lo.append(0);hi.append(np.inf)
 for kind,value in enumerate(counts):
  row=np.zeros(2*n)
  for i,r in enumerate(a):row[2*i]=r['potential']>=.05 if kind==0 else r['potential']>=.10 if kind==1 else .03<=r['potential']<.05
  matrix.append(row);lo.append(value);hi.append(value)
 objective=np.zeros(2*n);upper=np.empty(2*n)
 for i,r in enumerate(a):objective[2*i+1]=float((r['buy_lot']+r['sell_lot'])/1000000);upper[2*i]=1;upper[2*i+1]=maxlots[i]
 result=milp(c=objective,integrality=np.ones(2*n),bounds=Bounds(np.zeros(2*n),upper),constraints=LinearConstraint(csr_matrix(np.array(matrix)),np.array(lo),np.array(hi)),options={'mip_rel_gap':0.,'time_limit':300.})
 assert result.status==0 and result.mip_gap==0
 x=np.rint(result.x).astype(int);assert np.max(np.abs(x-result.x))<1e-5
 selected=[]
 for i,r in enumerate(a):
  if x[2*i]:selected.append({'entry_id':r['entry_id'],'entry_minute':r['entry_minute'],'release_minute':r['release_minute'],'quantity':int(x[2*i+1])*100,'debit':str(r['buy_lot']*int(x[2*i+1])),'credit':str(r['sell_lot']*int(x[2*i+1]))})
 return selected,{'status':int(result.status),'gap':float(result.mip_gap),'nodes':int(result.mip_node_count),'dual_bound_jpy':float(result.mip_dual_bound)*1e6}
def main():
 a=candidate_inputs();bound,flow=flow_bound(a);primary=json.loads((OUT/'ORACLE_UPPER_BOUND.json').read_text());witness=read(P/'ORACLE_WITNESS.jsonl.gz');counts,cost,minimum,peak=cash_validate(witness,a)
 independently,solver=minimum_turnover(a,bound);c2,cost2,cash2,peak2=cash_validate(independently,a)
 mismatch=[]
 for label,ok in [('U5_upper_bound',bound[0]==primary['maximum_feasible_U5']),('U10_upper_bound',bound[1]==primary['maximum_U10_conditional_on_max_U5']),('Medium_upper_bound',bound[2]==primary['maximum_Medium_conditional_on_max_U5_U10']),('primary_cash_witness_attains_bound',counts==bound),('independent_cash_witness_attains_bound',c2==bound),('turnover_independent_exact',cost==cost2 and abs(float(cost2)-primary['minimum_turnover_at_counts_jpy'])<1e-6),('turnover_dual_certificate',abs(float(cost2)-solver['dual_bound_jpy'])<1e-5)]:
  if not ok:mismatch.append(label)
 report={'mismatch_N':len(mismatch),'mismatch':mismatch,'independent_algorithm':'3-unit residual min-cost flow for cash-relaxed lexicographic counts; distinct interleaved-variable integer-sizing MILP for turnover; exact Fraction cash/lot validation.','maximum_U5':bound[0],'maximum_U10_at_max_U5':bound[1],'maximum_Medium_at_max_U5_U10':bound[2],'minimum_turnover_jpy':float(cost2),'primary_witness_min_cash':str(minimum),'independent_witness_min_cash':str(cash2),'max_concurrent':max(peak,peak2),'flow':flow,'MILP':solver,'Primary_imports':0,'evaluator_only':True}
 with (OUT/'INDEPENDENT_ORACLE_AUDIT.json').open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
 with (P/'INDEPENDENT_ORACLE_WITNESS.jsonl.gz').open('xb') as f:f.write(gzip.compress(('\n'.join(json.dumps(x,sort_keys=True) for x in independently)+'\n').encode(),mtime=0))
 print(json.dumps(report),flush=True);assert not mismatch
if __name__=='__main__':main()
