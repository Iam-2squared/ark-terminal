"""Hand-fixed synthetic cases only; no Development optimization exposure."""
from control import *
from cash_diagnostic import solve_package,integerize
from decimal import Decimal as D
def row(k,entry,release,cost,proceeds,u,symbol=None):
 return {'entry_id':k,'symbol':symbol or k,'start':['S',entry],'end':['S',release],'buy_cost':str(cost),'sell_proceeds':str(proceeds),'rank_utility':u}
def main():
 cases=[
 ('cash_relaxed_optimum_infeasible',[row('A',0,2,80,80,10),row('B',0,2,80,80,9)],100,(10,1,1)),
 ('cash_recycle',[row('A',0,1,80,80,5),row('B',1,2,80,80,4)],80,(9,2,3)),
 ('same_minute_exit_before_entry',[row('A',0,1,100,100,1),row('B',1,2,100,100,1)],100,(2,2,3)),
 ('three_concurrent_fourth_reject',[row(chr(65+i),0,2,10,10,i+1) for i in range(4)],100,(9,3,9)),
 ('same_symbol_overlap',[row('A',0,2,10,10,5,'X'),row('B',1,3,10,10,3,'X')],100,(5,1,1)),
 ('negative_return_reduces_later_cash',[row('A',0,1,60,40,10),row('B',1,2,60,60,9)],60,(10,1,1)),
 ('positive_return_increases_later_cash',[row('A',0,1,60,90,1),row('B',1,2,90,90,1)],60,(2,2,3)),
 ('exact_100_share_cost',[row('A',0,1,D(100)*D('1479')*D('1.0005'),D(100)*D('1475')*D('.9995'),1)],D('147973.95'),(1,1,1)),
 ('exact_decimal_tick',[row('A',0,1,D('.003'),D('.001'),1)],D('.003'),(1,1,1)),
 ('lex_utility_over_count',[row('A',0,2,50,50,5),row('B',0,1,50,50,2),row('C',1,2,50,50,2)],50,(5,1,1)),
 ('lex_count_then_ordinal',[row('A',0,2,50,50,5),row('B',0,1,50,50,2),row('C',1,2,50,50,3)],50,(5,2,5)),
 ('nonunique_tie',[row('A',0,2,60,60,1),row('B',0,2,50,50,1),row('C',0,2,50,50,1),row('D',0,2,40,40,1)],100,(2,2,5))]
 results=[]
 for name,a,cash,expected in cases:
  selected,result,ledger=solve_package(a,D(str(cash)),uniqueness=True)
  actual=(result['stage1_utility'],result['stage2_selected_N'],result['stage3_stable_ordinal_sum']);assert actual==expected,(name,actual,expected)
  if name=='nonunique_tie':assert result['canonical_status']=='NONUNIQUE_CANONICAL_TIE'
  if name=='exact_decimal_tick':assert result['money_contract']['scale']==1000
  results.append({'case':name,'expected_utility_N_ordinal':expected,'actual':actual,'cash_min':result['cash_minimum_exact'],'canonical_status':result['canonical_status'],'PASS':True})
 # Outcome values cannot change the objective or selected schedule.
 a=[row('A',0,2,10,10,2),row('B',0,2,10,10,1)];ix,r,led=solve_package(a,D(10),uniqueness=False)
 mutated=[z|{'U5':999,'U10':-999,'potential_return':123,'realized_PnL':9999999} for z in a];jx,s,_=solve_package(mutated,D(10),uniqueness=False);assert ix==jx and r['stage1_utility']==s['stage1_utility']
 result={'exact_jst':now(),'synthetic_case_N':12,'all_PASS':True,'cases':results,'no_outcome_label_in_objective_mutation_PASS':True,'hand_fixed_expected_answers_before_Development_solve':True,'full_diagnostic_execution_N':0,'new_fit':0}
 save(OUT/'CASH_SOLVER_SYNTHETIC_PREFLIGHT.json',result);checkpoint('R3_CASH_SOLVER_SYNTHETIC_PREFLIGHT','TWELVE_SYNTHETIC_PREFLIGHT_PASS',['cash/exit recycle/ordering/MAX3/symbol','tick exact','lex3/nonunique','label mutation'],{'case_N':12,'PASS':12,'full_diagnostic_N':0},'Commit/actual GET then the one full cash-joint diagnostic package');print(json.dumps({'synthetic_PASS':12,'full_diagnostic_N':0}))
if __name__=='__main__':main()
