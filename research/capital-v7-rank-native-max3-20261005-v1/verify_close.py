"""Non-mutating integrity checks followed by append-only terminal closure."""
from control import *
import ast,sys
ARMS=['RANK_NATIVE_GREEDY_MAX3','RANK_NATIVE_LAST_SLOT_OPTION_MAX3']
def verify():
 failures=[];checks=0
 def check(name,ok):
  nonlocal checks
  checks+=1
  if not ok:failures.append(name)
 for c in read(OUT/'INPUT_BYTE_AND_SOURCE_FREEZE.json')['checks']:check('input/'+c['path'],sha(WORK/c['path'])==c['sha256'])
 for arm in ARMS:
  r=read(OUT/f'{arm}_RESULT.json');check(arm+'/38 COMPLETE',r['valid_primary_day_N']==38 and r['blocked_execution_day_N']==r['execution_source_unresolved_N']==0)
  for name,value in r['ledger_sha256'].items():check(arm+'/'+name,sha(PRIVATE/f'{arm}_{name}.jsonl.gz')==value)
  ds=rows(PRIVATE/f'{arm}_DECISIONS.jsonl.gz');check(arm+'/identity',len(ds)==1039 and len({r['entry_id'] for r in ds})==1039);check(arm+'/cutoff',all(r['quantity']==0 for r in ds if r['minute']>=920))
  unavailable={r['entry_id'] for r in read(OUT/'EXECUTION_AVAILABILITY_CLARIFICATION.json')['execution_unavailable']};check(arm+'/unavailable not funded',all(r['quantity']==0 for r in ds if r['entry_id'] in unavailable))
 for name in ('ALL_U5','ALL_U10','ADMISSION_U5','ADMISSION_U10'):
  r=read(OUT/f'ORACLE_{name}.json');check(name+'/witness',sha(PRIVATE/f'{name}_WITNESS.jsonl.gz')==r['witness_sha256']);check(name+'/certified',r['global_physical_count_optimum_certified'])
 check('Main markers2',len(list(PRIVATE.glob('RANK_NATIVE_*_STARTED.json')))==2);check('Oracle markers4',len([p for p in PRIVATE.glob('*_STARTED.json') if p.name.startswith(('ALL_','ADMISSION_'))])==4)
 for name,value in read(OUT/'MAIN_REPLAY_CLAIM.json')['code_sha256'].items():check('Main code/'+name,sha(CODE/name)==value)
 for p in CODE.glob('*.py'):ast.parse(p.read_text());checks+=1
 for p in OUT.rglob('*.json'):read(p);checks+=1
 check('Independent mismatch0',read(OUT/'INDEPENDENT_AUDIT.json')['mismatch_N']==0);check('Final selection match0',read(OUT/'WINNER_AND_BOTTLENECK.json')['independent_final_selection_mismatch_N']==0)
 check('Report hash',sha(OUT/'REPORT_FINAL-ja.md')==read(OUT/'REPORT_FACTS.json')['report_sha256']);delivery=read(OUT/'PRIVATE_DELIVERY_RECEIPT.json');check('private hash',sha(ROOT.parent/'deliverables'/delivery['filename'])==delivery['sha256']);check('private saved',delivery['save_status']=='succeeded')
 report=(OUT/'REPORT_FINAL-ja.md').read_text();check('report ordered A..I',all(report.index(f'## {x}.')<report.index(f'## {y}.') for x,y in zip('ABCDEFGH','BCDEFGHI')));check('stop status',read(OUT/'WINNER_AND_BOTTLENECK.json')['final_status']=='NO_GO')
 out={'exact_jst':now(),'check_N':checks,'mismatch_N':len(failures),'mismatches':failures,'model_fit_or_replay_rerun':0,'complete_Oracle_solves':4,'complete_primary_replays':2,'source_unavailable_IDs_preserved':True,'complete_saved_artifacts_recomputed':False,'Safety':SAFETY}
 save(OUT/'FOCUSED_FINAL_VERIFICATION.json',out);print(json.dumps(out),flush=True);assert not failures
def close():
 assert read(OUT/'FOCUSED_FINAL_VERIFICATION.json')['mismatch_N']==0
 decision=read(OUT/'WINNER_AND_BOTTLENECK.json');audit=read(OUT/'INDEPENDENT_AUDIT.json')
 closure={'exact_jst':now(),'CURRENT_STATE':'CAPITAL_V7_D15_CLOSURE_FIXED_STOP','final_status':'NO_GO','selectedCapitalCandidate':None,'selectedRankCandidate':'EXISTING_MOVE_P5','retainedCapitalBenchmark':'V5_FROZEN_REFERENCE','NEXT_BOTTLENECK':decision['NEXT_BOTTLENECK'],'completed_checkpoints':[f'D{i}' for i in range(16)],'new_fits':0,'counts':BASE_COUNTS|{'Oracle_solves':4,'Primary_replays':2,'A1_replays':1,'A2_replays':1,'independent_recalculations':2,'independent_Oracle_upper_bound_solves':4},'independent_audit_check_N':audit['check_N'],'independent_audit_mismatch_N':0,'focused_verification_mismatch_N':0,'report_sha256':sha(OUT/'REPORT_FINAL-ja.md'),'private_delivery_receipt_sha256':sha(OUT/'PRIVATE_DELIVERY_RECEIPT.json'),'rank_contract_sha256':'6e8687f36f6f60fc9e9921e1ef29e0520cf1ea8bc01f14386963f1020b209518','rank_score_sha256':'14c48e61554bd58c6d5289b410d6a8c859cb37efd0dbc5d98987fcb440aac2ed','source_asof_boundary':'Inherited closed-bar contract; historical actual arrival UNKNOWN, no stronger PIT claim','teacher_changes':0,'Selector_Entry_EXIT_changes':0,'Safety':SAFETY,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS_claim':False,'productionReady':False,'STOP':True,'next_policy':'Preserve results; only terminal publication/actual GET receipts and append-only preservation audit remain. No research, model, policy, replay, Oracle solve or external trading action.','do_not':['A3','threshold sweep','result rescue','same-cycle retune','new model','Rank recalibration/refit','replay rerun','Oracle rerun','protected/fresh open','Selector/Entry/EXIT change','MAX4/MAX5','replacement','main merge','force push','orders']}
 save(OUT/'CLOSURE.json',closure)
 checkpoint('D15_CLOSURE_FIXED_STOP','CAPITAL_V7_D15_CLOSURE_FIXED_STOP',['D0..D14','NO_GO fixed','Rank kept','v5 retained','private pack saved','final Report','independent0'],closure,'STOP; terminal receipts only, no research restart',{'oracle_solves':4,'primary_replays':2,'independent_recalculations':2,'independent_oracle_solves':4})
if __name__=='__main__':globals()[sys.argv[1]]()
