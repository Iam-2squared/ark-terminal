"""Evaluation-only cash/interval/symbol joint binary MILP, never policy input."""
from control import *
from execution_bridge import BUY,exit_source,execution_ok
from decimal import Decimal as D
from collections import Counter
import math,numpy as np,scipy
from scipy.optimize import milp,LinearConstraint,Bounds
from scipy.sparse import csc_matrix
NAME='PPRANK_CLAIRVOYANT_ADMISSION_DIAGNOSTIC_CASH_JOINT_V1'
OPTIONS={'presolve':True,'mip_rel_gap':0.0,'time_limit':120.0,'disp':False}
class DiagnosticOnlyFailure(Exception):pass
class SharedContractFailure(Exception):pass
def population():
 books={r['entry_id']:r for r in rows(INPUT/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};mask={r['entry_id'] for r in rows(PIN/'COMMON_EVAL_MASK.jsonl.gz') if r['included']};a=[];unavailable=[]
 for r in rows(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz'):
  if r['entry_id'] not in mask or r['band']=='P_BELOW':continue
  b=books[r['entry_id']]
  if not execution_ok(r,b):unavailable.append(r['entry_id']);continue
  z=exit_source(b)
  if z['release_minute']<=r['entry_minute']:raise SharedContractFailure('FROZEN_RELEASE_INTERVAL')
  a.append({k:r[k] for k in ('entry_id','session','symbol','entry_timestamp','entry_minute','pP','r','rank_units','train_N','band')}|{'start':[r['session'],r['entry_minute']],'end':[r['session'],z['release_minute']],'rank_utility':round(r['r']*1000000),'buy_cost':str(D(100)*D(r['raw_reference'])*BUY),'sell_proceeds':str(D(100)*D(z['price'])),'release_minute':z['release_minute']})
 a.sort(key=lambda r:(r['entry_timestamp'],r['symbol'],r['entry_id']))
 if len(a)!=488 or len(unavailable)!=2:raise SharedContractFailure('EXECUTABLE_ADMISSION_IDENTITY')
 return a,unavailable
def integerize(a,initial):
 values=[D(str(initial))]+[D(r[k]) for r in a for k in ('buy_cost','sell_proceeds')]
 digits=max(0,max(-v.normalize().as_tuple().exponent for v in values));scale=10**digits
 def exact(v):
  z=D(str(v))*scale
  if z!=z.to_integral_value():raise SharedContractFailure('MONEY_INTEGERIZATION_NOT_EXACT')
  x=int(z)
  if abs(x)>2**53:raise SharedContractFailure('TICK_NOT_EXACTLY_REPRESENTABLE_IN_FLOAT64')
  return x
 return [{'buy':exact(r['buy_cost']),'sell':exact(r['sell_proceeds'])} for r in a],exact(initial),{'decimal_digits':digits,'scale':scale,'method':'smallest power10 from normalized Decimal exponent; exact multiplication, no rounding','cost_proceeds_exact':True,'initial_cash_ticks':exact(initial),'max_integer_tick':max(exact(v) for v in values)}
def formulation(a,initial):
 ticks,cash,contract=integerize(a,initial);n=len(a);events=sorted({tuple(r['start']) for r in a});starts=[tuple(r['start']) for r in a];ends=[tuple(r['end']) for r in a];matrix=[];ub=[];kinds=[]
 for e in events:
  # Confirmed exits at e credit before every buy at e.
  matrix.append([ticks[i]['buy']*(starts[i]<=e)-ticks[i]['sell']*(ends[i]<=e) for i in range(n)]);ub.append(cash);kinds.append('CUMULATIVE_CASH')
  matrix.append([int(starts[i]<=e<ends[i]) for i in range(n)]);ub.append(3);kinds.append('MAX3')
 pair_N=0
 for i in range(n):
  for j in range(i):
   if a[i]['symbol']==a[j]['symbol'] and starts[i]<ends[j] and starts[j]<ends[i]:
    row=[0]*n;row[i]=row[j]=1;matrix.append(row);ub.append(1);kinds.append('SAME_SYMBOL_PAIRWISE');pair_N+=1
 constraints=[LinearConstraint(csc_matrix(np.array(matrix,dtype=np.float64)),np.full(len(matrix),-np.inf),np.array(ub,dtype=np.float64))]
 return constraints,contract,{'candidate_N':n,'Entry_event_N':len(events),'cash_constraint_N':len(events),'MAX3_constraint_N':len(events),'symbol_pairwise_constraint_N':pair_N,'matrix_sha256':hashlib.sha256(json.dumps({'matrix':matrix,'upper':ub},separators=(',',':')).encode()).hexdigest()}
def certify(a,selected,initial):
 cash=D(str(initial));minimum=cash;held={};ledger=[];events={}
 for i in selected:
  r=a[i];events.setdefault(tuple(r['start']),{'BUY':[],'SELL':[]})['BUY'].append(i);events.setdefault(tuple(r['end']),{'BUY':[],'SELL':[]})['SELL'].append(i)
 peak=0
 for e,z in sorted(events.items()):
  for i in sorted(z['SELL']):
   if i not in held:raise DiagnosticOnlyFailure('SELL_WITHOUT_HELD')
   held.pop(i);cash+=D(a[i]['sell_proceeds'])
  for i in sorted(z['BUY']):cash-=D(a[i]['buy_cost']);held[i]=a[i];minimum=min(minimum,cash)
  if cash<0 or len(held)>3 or len({r['symbol'] for r in held.values()})!=len(held):raise DiagnosticOnlyFailure('EXACT_CASH_CAPACITY_SYMBOL_WITNESS')
  peak=max(peak,len(held));ledger.append({'session':e[0],'minute':e[1],'cash_exact':str(cash),'occupancy':len(held),'held_entry_ids':[a[i]['entry_id'] for i in sorted(held)],'buys':[a[i]['entry_id'] for i in z['BUY']],'sells':[a[i]['entry_id'] for i in z['SELL']]})
 if held:raise DiagnosticOnlyFailure('UNCLOSED_INTERVAL')
 return {'cash_minimum_exact':str(minimum),'ending_cash_exact':str(cash),'maximum_occupancy':peak,'same_symbol_violation':0,'cash_negative':0,'exact_Decimal_certification':True},ledger
def solve_package(a,initial=D(1000000),uniqueness=True,progress=False):
 n=len(a);constraints,money,matrix=formulation(a,initial);u=np.array([r['rank_utility'] for r in a],dtype=np.float64);ones=np.ones(n);ordinal=np.arange(1,n+1,dtype=np.float64);stages=[]
 def stage(c,stage_name):
  r=milp(c=c,integrality=np.ones(n,dtype=int),bounds=Bounds(np.zeros(n),np.ones(n)),constraints=constraints,options=OPTIONS)
  stages.append({'stage':stage_name,'status':int(r.status),'message':r.message,'mip_gap':None if r.mip_gap is None else float(r.mip_gap),'solver_fun':None if r.fun is None else float(r.fun)})
  if r.status!=0 or not r.success or r.x is None:raise DiagnosticOnlyFailure('SOLVER_NOT_OPTIMAL_'+stage_name)
  if any(abs(float(v)-round(float(v)))>1e-7 for v in r.x):raise DiagnosticOnlyFailure('BINARY_INTEGRALITY_TOLERANCE')
  ix=[i for i,v in enumerate(r.x) if round(float(v))==1]
  if progress:print(json.dumps(stages[-1]),flush=True)
  return ix
 first=stage(-u,'UTILITY');utility=sum(a[i]['rank_utility'] for i in first);constraints.append(LinearConstraint(u[None,:],utility,utility))
 second=stage(-ones,'SELECTED_N');count=len(second);constraints.append(LinearConstraint(ones[None,:],count,count))
 third=stage(ordinal,'STABLE_ORDINAL_SUM');ordinal_sum=sum(i+1 for i in third)
 if sum(a[i]['rank_utility'] for i in third)!=utility or len(third)!=count:raise DiagnosticOnlyFailure('EXACT_LEX_OBJECTIVE_MISMATCH')
 exact,ledger=certify(a,third,initial);tie='UNIQUENESS_NOT_CHECKED'
 if uniqueness:
  constraints.append(LinearConstraint(ordinal[None,:],ordinal_sum,ordinal_sum));exclude=np.zeros(n);exclude[third]=1;constraints.append(LinearConstraint(exclude[None,:],-np.inf,count-1))
  r=milp(c=np.zeros(n),integrality=np.ones(n,dtype=int),bounds=Bounds(np.zeros(n),np.ones(n)),constraints=constraints,options=OPTIONS)
  if r.status==2:tie='UNIQUE_CANONICAL'
  elif r.status==0 and r.success:tie='NONUNIQUE_CANONICAL_TIE'
  else:raise DiagnosticOnlyFailure('UNIQUENESS_CERTIFICATION_UNAVAILABLE')
 return third,{'status':'CERTIFIED','stage1_utility':utility,'stage2_selected_N':count,'stage3_stable_ordinal_sum':ordinal_sum,'canonical_status':tie,'unique_optimum_claim':tie=='UNIQUE_CANONICAL','sum_r':math.fsum(a[i]['r'] for i in third) if 'r' in a[0] else None,'stage_receipts':stages,'money_contract':money,'formulation':matrix}|exact,ledger
def precommit():
 save(OUT/'CASH_SOLVER_PRECOMMIT.json',{'exact_jst':now(),'name':NAME,'full_execution_package_budget':1,'stages':['max sum round(r*1000000)','fixed utility, max N','fixed utility/N, min stable ordinal sum'],'stable_order':['Entry timestamp ASC','symbol ASC','entry_id ASC'],'optional_uniqueness_no_good_budget':1,'quantity':100,'population':488,'runtime_admission_unchanged':490,'money':'Decimal exact smallest decimal scale integer ticks, no rounding, float64 exact tick representability check','cash':'joint cumulative cash hard constraint after Entry event; same-minute confirmed exits before buys;38 sessions carry','interval':'[Frozen Entry,Frozen release), MAX3 hard constraints at all Entry events','same_symbol':'pairwise overlap hard constraints; independent uses symbol-event matrices','objective_U5_U10_PnL':0,'runtime_access':False,'policy_design_access':False,'failure_types':{'A':'diagnostic solver/optimization/tie/witness -> fixed UNAVAILABLE, do not repair/rerun; B1/B2 continue if shared contract PASS','B':'input/identity/Entry/EXIT/pP/band/cash/source ambiguity -> STOP'},'solver':'scipy.optimize.milp / HiGHS','scipy_version':scipy.__version__,'options':OPTIONS,'binary_tolerance':1e-7,'objective_integer_exact':True,'money_quantity_tolerance':0,'float_score_pressure_tolerance':1e-12,'synthetic_before_full':12,'code_sha256':{'cash_diagnostic.py':sha(CODE/'cash_diagnostic.py'),'solver_preflight.py':sha(CODE/'solver_preflight.py'),'cash_diagnostic_independent.py':sha(CODE/'cash_diagnostic_independent.py')},'Safety':SAFETY})
 checkpoint('R2_CASH_SOLVER_PRECOMMIT','CASH_JOINT_DIAGNOSTIC_PRECOMMITTED',['joint constraints','3 lex stages','exact integerization','A/B failure dependency separation'],{'full_package_budget':1,'optional_no_good':1,'independent_package':1},'Synthetic hand-fixed 12 cases before full solve; no old solve rerun')
def main():
 assert read(OUT/'CASH_SOLVER_SYNTHETIC_PREFLIGHT.json')['all_PASS']
 assert (OUT/'receipts/R3_CASH_SOLVER_SYNTHETIC_PREFLIGHT_ACTUAL_GET.json').exists()
 claim=read(OUT/'CASH_SOLVER_PRECOMMIT.json')
 for n,v in claim['code_sha256'].items():assert sha(CODE/n)==v
 # Shared sources checked independently of optional diagnostic optimization.
 for z in read(OUT/'INPUT_BYTE_FREEZE.json')['files']:assert sha(PRIOR/z['path'])==z['sha256'],'SHARED_SOURCE_BYTE_STOP'
 a,unavailable=population();save(OUT/'MONEY_INTEGERIZATION_CONTRACT.json',integerize(a,D(1000000))[2]);gzsave(PRIVATE/'CASH_DIAGNOSTIC_INPUT.jsonl.gz',a)
 save(PRIVATE/'CASH_DIAGNOSTIC_STARTED.json',{'exact_jst':now(),'single_execution':True,'claim_sha256':sha(OUT/'CASH_SOLVER_PRECOMMIT.json'),'rerun_allowed':False})
 try:
  ix,result,ledger=solve_package(a,progress=True);selected=[a[i] for i in ix];teacher={r['entry_id']:r for r in rows(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz')}
  result.update(U5=sum(teacher[r['entry_id']]['label_bigwinner5'] for r in selected),U10=sum(teacher[r['entry_id']]['label_bigwinner10'] for r in selected),below2_N=sum(teacher[r['entry_id']]['potential_return']<.02 for r in selected),pP_decile=dict(Counter(min(10,max(1,int(r['r']*10)+1)) for r in selected)))
  gzsave(PRIVATE/'CASH_DIAGNOSTIC_SELECTED.jsonl.gz',[r|{'quantity':100,'stable_ordinal':i+1} for i,r in enumerate(a) if i in ix]);gzsave(PRIVATE/'CASH_DIAGNOSTIC_EVENT_LEDGER.jsonl.gz',ledger)
  result.update(selected_sha256=sha(PRIVATE/'CASH_DIAGNOSTIC_SELECTED.jsonl.gz'),event_ledger_sha256=sha(PRIVATE/'CASH_DIAGNOSTIC_EVENT_LEDGER.jsonl.gz'),failure_type=None)
 except DiagnosticOnlyFailure as e:
  result={'status':'UNAVAILABLE','failure_type':'TYPE_A_DIAGNOSTIC_ONLY_FAILURE','reason':str(e),'shared_contract_PASS':True,'B1_B2_continuation_allowed':True,'solver_repair_rerun':False,'canonical_status':None}
 result.update(exact_jst=now(),name=NAME,initial_cash=1000000,candidate_N=488,runtime_admission_N=490,execution_unavailable_ids=unavailable,primary_execution_package_N=1,runtime_access=False,policy_design_access=False,U5_upper_bound_claim=False,Safety=SAFETY)
 save(OUT/'PPRANK_CASH_DIAGNOSTIC_RESULT.json',result);checkpoint('R4_PPRANK_CASH_DIAGNOSTIC','CASH_DIAGNOSTIC_FIXED',['one new diagnostic package','cash internal hard constraint','no labels in objective'],result,'Independent diagnostic raw matrix reconstruction; optional diagnostic failure does not feed policy',{'primary_pP_diagnostic_solve':1,'uniqueness_no_good_solve':1});print(json.dumps(result),flush=True)
if __name__=='__main__':
 import sys
 {'precommit':precommit,'full':main}[sys.argv[1]]()
