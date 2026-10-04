"""Separate policy reconstruction before any OOF portfolio replay."""
from control import *
from runtime import gate,predicted_release
from independent_engine import Audit
from independent_policy import build,accept,predicted
def main():
 audit=Audit();stream,tables,train=build(audit);actionchecks=0
 for r in stream:
  if r['entry_minute']>=920 or r['band']=='P_BELOW':continue
  table=tables[str(r['block'])]
  for arm in ARMS:
   for occupancy in range(4):
    allowed,reason,z=gate(arm,r,occupancy,r['entry_minute'],table);ok,why,count,n=accept(arm,r,occupancy,r['entry_minute'],table)
    tag=f'{r["entry_id"]}/{arm}/{occupancy}';audit.check(tag+'/action',allowed==ok and reason==why);audit.check(tag+'/counts',z['future_pressure_session_N']==count and z['training_session_N']==n);audit.check(tag+'/capacity',z['free_slots']==3-occupancy)
    if count is not None:audit.num(tag+'/pressure',z['P_future_capacity_pressure'],count/n)
    if occupancy<3 and arm==ARMS[1]:
     horizon,duration=predicted(r,table);audit.check(tag+'/tenure',z['predicted_release_minute']==horizon and z['predicted_active_duration']==duration)
    actionchecks+=1
 # Hand-fixed majority tie and rank monotonicity, in addition to 43 canaries.
 rr={'entry_minute':550,'pP':.3,'r':.3,'rank_units':30,'train_N':100,'band':'P_BASE'};days=['A','B','C','D'];table={'train_N':100,'training_sessions':days,'sessions':{'A':[[600,90],[601,80],[602,70]],'B':[[600,90],[601,80],[602,70]],'C':[],'D':[]}}
 for occupancy in (0,1,2):
  z=gate(ARMS[0],rr,occupancy,550,table);audit.check('majority_0_5_reserve/'+str(occupancy),not z[0] and z[2]['P_future_capacity_pressure']==.5)
  low=rr|{'pP':.1,'r':.1,'rank_units':10};audit.check('reserved_high_implies_reserved_lower/'+str(occupancy),not gate(ARMS[0],low,occupancy,550,table)[0])
 assert not audit.mismatches,audit.mismatches
 result={'exact_jst':now(),'status':'PASS','check_N':audit.checks,'action_case_N':actionchecks,'mismatch_N':len(audit.mismatches),'mismatches':audit.mismatches,'float_tolerance':1e-12,'max_float_delta':audit.max_float_delta,'independent_implementation_Primary_runtime_replay_evaluator_import':0,'comparator_only_imports_Primary_gate_to_compare':True,'independent_calculation':'independent_policy build/accept/predicted; raw saved scores and completed train releases; no Primary model inference/mapping/table builder','exact_half_reserve_and_same_occupancy_monotonicity_PASS':True,'OOF_Development_primary_replays':0,'runtime_module_sha256':sha(CODE/'runtime.py'),'table_hashes':{n:sha(OUT/n) for n in ('B1_CAPACITY_PRESSURE_TABLE.json','B2_TENURE_LOOKUP_TABLE.json','B2_CAPACITY_PRESSURE_TABLE.json')},'Safety':SAFETY}
 save(OUT/'PRE_MAIN_INDEPENDENT_POLICY_AUDIT.json',result);checkpoint('R8_PRE_MAIN_INDEPENDENT_POLICY_AUDIT','PRE_MAIN_INDEPENDENT_POLICY_MISMATCH0',['raw score percentile/band/tenure rebuilt separately','all admitted rows at occupancy0/1/2/3','exact majority and monotonic reserve'],result,'Claim exact two primary Main replays, commit/GET then execute once each',{'primary_pP_diagnostic_solve':1,'uniqueness_no_good_solve':1,'independent_pP_diagnostic_solve':1});print(json.dumps({'checks':audit.checks,'action_cases':actionchecks,'mismatch':0}))
if __name__=='__main__':main()
