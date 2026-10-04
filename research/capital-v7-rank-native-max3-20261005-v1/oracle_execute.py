"""Use explicit exact-execution availability, preserving unavailable row identities.

Initial oracle.py preflight asserted all rows executable before starting any
solve. That assertion is stricter than the requested Oracle population contract.
No primary solve was executed before this append-only clarification.
"""
from control import *
from oracle import inputs,solve
def main():
 assert (OUT/'receipts/D3_ORACLE_EXECUTION_AVAILABILITY_ACTUAL_GET.json').exists()
 a,invalid=inputs();tt={r['entry_id']:r for r in rows(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz')}
 assert all(tt[k]['label_bigwinner5']==tt[k]['label_bigwinner10']==0 for k in invalid)
 claim=read(OUT/'ORACLE_EXECUTION_CLAIM.json');allresults={}
 for name in claim['solves']:
  assert not (PRIVATE/f'{name}_STARTED.json').exists(),'AMBIGUOUS_OR_COMPLETED_SOLVE_STOP'
  save(PRIVATE/f'{name}_STARTED.json',{'exact_jst':now(),'claim_sha256':sha(OUT/'ORACLE_EXECUTION_CLAIM.json'),'availability_clarification_sha256':sha(OUT/'EXECUTION_AVAILABILITY_CLARIFICATION.json'),'single_execution':True})
  population=[r for r in a if r['band']!='P_BELOW'] if name.startswith('ADMISSION') else a
  result,witness=solve(population,name.split('_')[-1]);result.update(name=name,execution_unavailable_N=len(invalid),population_U5=sum(r['U5'] for r in population),population_U10=sum(r['U10'] for r in population),original_primary_population_N=1028)
  gzsave(PRIVATE/f'{name}_WITNESS.jsonl.gz',witness);result['witness_sha256']=sha(PRIVATE/f'{name}_WITNESS.jsonl.gz');save(OUT/f'ORACLE_{name}.json',result);allresults[name]=result
  print(json.dumps({k:result[k] for k in ('name','maximum_U5','maximum_U10','candidate_N','minimum_lot_witness_cash_min')}),flush=True)
 save(OUT/'ORACLE_RESULT.json',{'exact_jst':now(),'solves':allresults,'oracle_solves':4,'execution_unavailable_N':len(invalid),'execution_unavailable_U5':0,'execution_unavailable_U10':0,'primary_population_N':1028,'U5':170,'U10':67,'old_104_47_ceiling_not_reused':True})
 checkpoint('D4_ORACLE_RESULT','FOUR_CEILINGS_CERTIFIED',['ALL_U5','ALL_U10','ADMISSION_U5','ADMISSION_U10'],allresults,'Acknowledge already-precommitted bands; freeze future-max table',{'oracle_solves':4})
if __name__=='__main__':main()
