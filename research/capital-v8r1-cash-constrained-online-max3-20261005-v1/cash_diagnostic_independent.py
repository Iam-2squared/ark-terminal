"""Independent raw-source event/cash/symbol matrices; no Primary imports."""
from independent_engine import ROOT,I,P,PIN,O,read,rows,early,late,actual
from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal
from fractions import Fraction
import json,hashlib,numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import csr_matrix
def save(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n')
def now():return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='microseconds')
def raw_candidates():
 books={r['entry_id']:r for r in rows(I/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};mask={r['entry_id'] for r in rows(PIN/'COMMON_EVAL_MASK.jsonl.gz') if r['included']};a=[]
 for row in rows(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz'):
  if row['entry_id'] not in mask or row['band']=='P_BELOW':continue
  book=books[row['entry_id']];exit=early(book) or late(book)
  if not book['capture_complete'] or not book['entry_actual_source'] or not exit:continue
  cost=Decimal(row['raw_reference'])*Decimal('1.0005')*Decimal(100);proceeds=Decimal(exit['price'].numerator)/Decimal(exit['price'].denominator)*Decimal(100)
  a.append({'id':row['entry_id'],'symbol':row['symbol'],'timestamp':row['entry_timestamp'],'enter':(row['session'],row['entry_minute']),'release':(row['session'],exit['release']),'cost':cost,'credit':proceeds,'utility':round(row['r']*1000000)})
 a.sort(key=lambda r:(r['timestamp'],r['symbol'],r['id']));assert len(a)==488
 return a
def independent_exact(a,selected):
 selected=set(selected);cash=Fraction(1000000);minimum=cash;maximum=0;times=sorted(set(z for r in a for z in (r['enter'],r['release'])));ledger=[]
 for t in times:
  cash+=sum((Fraction(r['credit']) for i,r in enumerate(a) if i in selected and r['release']==t),Fraction(0));cash-=sum((Fraction(r['cost']) for i,r in enumerate(a) if i in selected and r['enter']==t),Fraction(0));held=[r for i,r in enumerate(a) if i in selected and r['enter']<=t<r['release']];minimum=min(minimum,cash);maximum=max(maximum,len(held));assert cash>=0 and len(held)<=3 and len({r['symbol'] for r in held})==len(held)
  ledger.append((t,cash,len(held)))
 return minimum,maximum
def main():
 result=read(O/'PPRANK_CASH_DIAGNOSTIC_RESULT.json');save(P/'CASH_DIAGNOSTIC_INDEPENDENT_STARTED.json',{'exact_jst':now(),'single_execution':True,'primary_status':result['status']})
 if result['status']!='CERTIFIED':
  save(O/'PPRANK_INDEPENDENT_AUDIT.json',{'exact_jst':now(),'status':'UNAVAILABLE_PRIMARY_DIAGNOSTIC','mismatch_N':0,'not_certification_PASS':True,'independent_full_solve_N':0,'runtime_policy_dependency':False});return
 a=raw_candidates();n=len(a)
 # Independently count the minimum decimal places by stripping coefficient zeros,
 # without Primary normalize/integerize implementation.
 places=0
 for z in [Decimal(1000000)]+[r[k] for r in a for k in ('cost','credit')]:
  sign,digits,exponent=z.as_tuple();digits=list(digits)
  while digits and digits[-1]==0:digits.pop();exponent+=1
  places=max(places,-exponent)
 scale=10**places;cost=[];credit=[]
 for r in a:
  values=[r['cost']*scale,r['credit']*scale];assert all(v==int(v) for v in values);cost.append(int(values[0]));credit.append(int(values[1]))
 events=sorted({r['enter'] for r in a});A=[];upper=[];symbol_rows=0
 for event in events:
  A.append([cost[i] if r['enter']<=event else 0 for i,r in enumerate(a)])
  for i,r in enumerate(a):
   if r['release']<=event:A[-1][i]-=credit[i]
  upper.append(1000000*scale)
  live=[int(r['enter']<=event<r['release']) for r in a];A.append(live);upper.append(3)
  for symbol in sorted({r['symbol'] for i,r in enumerate(a) if live[i]}):A.append([int(live[i] and r['symbol']==symbol) for i,r in enumerate(a)]);upper.append(1);symbol_rows+=1
 constraints=[LinearConstraint(csr_matrix(np.array(A,dtype=float)),-np.inf,np.array(upper,dtype=float))];u=np.array([r['utility'] for r in a],float);one=np.ones(n);ord=np.arange(1,n+1,dtype=float);values=[];stage_status=[];chosen=[]
 for objective,coeff in [(-u,u),(-one,one),(ord,ord)]:
  sol=milp(c=objective,integrality=np.ones(n,dtype=int),bounds=Bounds(0,1),constraints=constraints,options={'presolve':True,'mip_rel_gap':0.0,'time_limit':120.0,'disp':False});assert sol.status==0 and sol.success;assert all(abs(v-round(v))<=1e-7 for v in sol.x)
  chosen=[i for i,v in enumerate(sol.x) if round(v)==1];value=sum(int(coeff[i]) for i in chosen);values.append(value);stage_status.append(int(sol.status));constraints.append(LinearConstraint(coeff[None,:],value,value));print(json.dumps({'independent_stage':len(values),'objective':value}),flush=True)
 mismatch=[]
 for field,value in zip(['stage1_utility','stage2_selected_N','stage3_stable_ordinal_sum'],values):
  if result[field]!=value:mismatch.append(field)
 if scale!=read(O/'MONEY_INTEGERIZATION_CONTRACT.json')['scale']:mismatch.append('money_scale')
 minimum,maximum=independent_exact(a,chosen);primary_selected=rows(P/'CASH_DIAGNOSTIC_SELECTED.jsonl.gz');ids={r['entry_id'] for r in primary_selected};primary_indices=[i for i,r in enumerate(a) if r['id'] in ids];pmin,pmax=independent_exact(a,primary_indices)
 if pmin!=Fraction(result['cash_minimum_exact']) or pmax!=result['maximum_occupancy']:mismatch.append('primary_exact_cash_capacity_certificate')
 if result['canonical_status']=='UNIQUE_CANONICAL' and {a[i]['id'] for i in chosen}!=ids:mismatch.append('unique_selected_identity')
 audit={'exact_jst':now(),'status':'PASS' if not mismatch else 'FAIL','mismatch_N':len(mismatch),'mismatches':mismatch,'independent_full_solve_package_N':1,'primary_runtime_replay_evaluator_import':0,'raw_candidate_N':n,'stage1_utility':values[0],'stage2_selected_N':values[1],'stage3_stable_ordinal_sum':values[2],'solver_stages_OPTIMAL':stage_status,'independent_money_scale':scale,'independent_cash_minimum_exact':str(Decimal(minimum.numerator)/Decimal(minimum.denominator)),'primary_cash_minimum_independently_verified':True,'maximum_occupancy':maximum,'same_symbol_event_constraint_N':symbol_rows,'symbol_event_builder':True,'cash_and_occupancy_event_builder_independent':True,'canonical_status':result['canonical_status'],'identity_equality_required':result['canonical_status']=='UNIQUE_CANONICAL','NONUNIQUE_different_feasible_schedule_not_mismatch':True,'same_market_source_not_external_source_independence':True}
 save(O/'PPRANK_INDEPENDENT_AUDIT.json',audit);assert not mismatch,mismatch;print(json.dumps(audit),flush=True)
if __name__=='__main__':main()
