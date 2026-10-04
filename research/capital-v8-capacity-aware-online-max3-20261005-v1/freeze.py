"""Read-only byte / authority audit. Does not run prior models or replays."""
from control import *
import zipfile,subprocess
from collections import Counter
def start():
 basis=read(WORK/'latest_basis.json');assert basis['actual_GET_verified']
 paths=subprocess.check_output(['git','ls-tree','-r','--name-only',basis['HEAD']],cwd=ROOT,text=True).splitlines()
 assert not any('capital-v8-capacity-aware-online-max3-20261005-v1/' in p for p in paths),'EXISTING_CYCLE_RECOVERY_REQUIRED'
 assert not any(p.endswith('AGENTS.md') for p in paths),'NEW_INSTRUCTIONS_READ_REQUIRED'
 save(OUT/'START_LATEST_AUDIT.json',{'exact_jst':now(),'actual_GET_HEAD':basis['HEAD'],'actual_GET_tree':basis['tree'],'local_HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'tree_GET_verified':True,'original_path_N':len(paths),'applicable_instructions':['MASTER_PROMPT.md','explicit user branch overrides default branch policy'],'AGENTS_in_tree':[],'new_cycle_identity':'capital-v8-capacity-aware-online-max3-20261005-v1','existing_completed_v8':False})
 checkpoint('D0_START_LATEST_AUDIT','LATEST_ACTUAL_GET_VERIFIED',['branch and tree GET','applicable instructions','cycle collision check'],{'HEAD':basis['HEAD'],'tree':basis['tree']},'Freeze read-only Rank/v7/v5/v6 and private bytes; no legacy re-execution')
def authority():
 names=['CLOSURE.json','NEXT_WORK_HANDOFF.json','REPORT_FINAL-ja.md','RANK_NATIVE_BAND_MAP.json','BAND_VOLUME_IDENTITY_AUDIT.json','FUTURE_MAX_RANK_TABLE.json','LAST_SLOT_POLICY_PRECOMMIT.json','PRESERVATION_RESULT.json','ORACLE_RESULT.json','ORACLE_ADMISSION_U5.json','ORACLE_ADMISSION_U10.json','ORACLE_ALL_U5.json','ORACLE_ALL_U10.json','INDEPENDENT_AUDIT.json','PRIVATE_DELIVERY_RECEIPT.json','INPUT_BYTE_AND_SOURCE_FREEZE.json','PRIVATE_PACK_MANIFEST.json']
 hashes={str((V7/n).relative_to(ROOT)):sha(V7/n) for n in names}
 for n in ('SELECTED_RANK_CONTRACT.json','CLOSURE.json','NEXT_WORK_HANDOFF.json'):hashes[str((RANK/n).relative_to(ROOT))]=sha(RANK/n)
 rc=read(RANK/'SELECTED_RANK_CONTRACT.json');assert rc['status']=='RANK_VNEXT_STRONG' and rc['selectedRankCandidate']=='EXISTING_MOVE_P5' and rc['score_field']=='pP'
 assert sha(RANK/'SELECTED_RANK_CONTRACT.json')=='6e8687f36f6f60fc9e9921e1ef29e0520cf1ea8bc01f14386963f1020b209518'
 assert read(V7/'CLOSURE.json')['CURRENT_STATE']=='CAPITAL_V7_D15_CLOSURE_FIXED_STOP'
 pack=ROOT.parent/'deliverables/Ark_Capital_v7_Rank_Native_MAX3_20261005_PRIVATE.zip';receipt=read(V7/'PRIVATE_DELIVERY_RECEIPT.json')
 assert sha(pack)==receipt['sha256'] and pack.stat().st_size==receipt['bytes']
 checks=[]
 with zipfile.ZipFile(pack) as z:
  mb=z.read('MANIFEST.json');manifest=json.loads(mb);assert manifest==read(V7/'PRIVATE_PACK_MANIFEST.json')['manifest']
  assert set(z.namelist())==set(manifest['files'])|{'MANIFEST.json'}
  for name,v in manifest['files'].items():
   b=z.read(name);p=PRIOR/name
   assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256']==sha(p)
   checks.append({'path':name,'sha256':v['sha256'],'bytes':len(b),'ZIP_and_local_exact':True})
 for c in read(V7/'INPUT_BYTE_AND_SOURCE_FREEZE.json')['checks']:assert sha(PRIOR/c['path'])==c['sha256']
 assert sha(INPUT/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz')==rc['score_stream_sha256']
 for n,v in rc['model_sha256'].items():assert sha(INPUT/'movement/models'/n)==v
 stream=rows(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz');mask={r['entry_id'] for r in rows(PIN/'COMMON_EVAL_MASK.jsonl.gz') if r['included']};tt={r['entry_id']:r for r in rows(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz')}
 population=[r for r in stream if r['entry_id'] in mask];adm=[r for r in population if r['band']!='P_BELOW'];oracle=read(V7/'ORACLE_RESULT.json')
 assert len(population)==1028 and sum(tt[r['entry_id']]['label_bigwinner5'] for r in population)==170 and sum(tt[r['entry_id']]['label_bigwinner10'] for r in population)==67
 assert len(adm)==490 and sum(tt[r['entry_id']]['label_bigwinner5'] for r in adm)==124 and sum(tt[r['entry_id']]['label_bigwinner10'] for r in adm)==55
 for n,k,value in [('ALL_U5','maximum_U5',149),('ALL_U10','maximum_U10',67),('ADMISSION_U5','maximum_U5',116),('ADMISSION_U10','maximum_U10',55)]:assert oracle['solves'][n][k]==value
 save(OUT/'AUTHORITY_FREEZE.json',{'exact_jst':now(),'sha256':hashes,'selectedRankCandidate':'EXISTING_MOVE_P5','Rank_status':'RANK_VNEXT_STRONG','frozen_order':rc['frozen_order'],'permanent_freeze':['Selector','Entry','EXIT'],'rank_calibration':'NOT_AUTHORIZED','v7_closed':True,'Safety':SAFETY})
 save(OUT/'INPUT_BYTE_FREEZE.json',{'exact_jst':now(),'pack_sha256':sha(pack),'pack_manifest_sha256':hashlib.sha256(mb).hexdigest(),'pack_delivery_receipt_sha256':sha(V7/'PRIVATE_DELIVERY_RECEIPT.json'),'files':checks,'mismatch_N':0,'source_boundary':'Existing Development bytes; assumed closed-bar end, historical actual arrival UNKNOWN','new_provider_request':0,'teacher_regeneration':0})
 save(OUT/'ADMISSION_POPULATION_CONTRACT_AUDIT.json',{'primary_N':1028,'U5':170,'U10':67,'runtime_admission_N':490,'execution_available_admission_N':488,'runtime_admission_U5':124,'runtime_admission_U10':55,'difference':'v7 488 is the execution-available diagnostic/Oracle population; runtime frozen band admits 490 including two negative candidates without complete future exit support. Do not delete or add a future-availability runtime gate. If funded and unresolved, fail closed.','band_map_sha256':sha(V7/'RANK_NATIVE_BAND_MAP.json'),'admission_change':0})
 checkpoint('D1_AUTHORITY_AND_INPUT_FREEZE','AUTHORITIES_AND_INPUT_BYTES_EXACT',['Rank contract','v7 closure','ZIP manifest 64 members','saved band/runtime bytes'],{'byte_mismatch':0,'primary_N':1028,'U5':170,'U10':67,'runtime_admission_N':490,'executable_admission_N':488},'Freeze v5 benchmark / negative v6/v7 / four saved Oracles; never rerun')
def references():
 prohibited=['Rank refit','Slot ML fit','teacher regeneration','v5/v6/v7 replay','old Oracle solve','threshold/grid/time bucket/support search','B3','Admission/Sizing/Liquidity change','result rescue','same-cycle retune','MAX4/MAX5','replacement','forced EXIT','new provider','protected/fresh open','orders','main merge','force push']
 save(OUT/'DO_NOT_REPEAT.json',{'exact_jst':now(),'prohibited':prohibited,'new_primary_replay_budget':{'B1':1,'B2':1},'new_pP_diagnostic_solve':1,'independent_pP_solve':1,'fits':0,'Safety':SAFETY})
 for d in ['capital-v5-max3-slot-intelligence-20261004-v1','capital-v6-counterfactual-slot-value-20261004-v1']:assert (ROOT/'docs/evidence'/d/'CLOSURE.json').exists()
 save(OUT/'SAVED_REFERENCE_FREEZE.json',{'exact_jst':now(),'v5_benchmark':{'U5':50,'U10':26,'below2':0.38666667,'rolling20_minimum':1.0823662751,'rolling20_arithmetic_mean':1.1906460126,'rolling20_median':1.1991541915,'rolling20_maximum':1.2970310262,'north_star_hit_N':0,'geometric_mean_daily_return':0.01032420041,'final_equity':1477436.15,'max_drawdown':0.10225325014},'v7_saved_profiles':read(V7/'MAIN_REPLAY_RESULT.json')['arms'],'v7_saved_preservation':read(V7/'PRESERVATION_RESULT.json')['profiles'],'saved_oracles':read(V7/'ORACLE_RESULT.json'),'v5_closure_sha256':sha(ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/CLOSURE.json'),'v6_closure_sha256':sha(ROOT/'docs/evidence/capital-v6-counterfactual-slot-value-20261004-v1/CLOSURE.json'),'replay_N':0,'old_Oracle_solve_N':0})
 checkpoint('D2_V7_NEGATIVE_AND_ORACLE_REUSE_FREEZE','PRIOR_COMPLETED_ARTIFACTS_READ_ONLY',['v5 benchmark','v6 negative','v7 A1/A2 negative','four saved Oracles'],{'Physical_U5':149,'Admission_U5':116,'Physical_unavoidable':21,'Admission_ceiling_loss':33,'old_replays':0,'old_solves':0},'Read-only anatomy, then one label-blind pP clairvoyant diagnostic; B1/B2 specifications remain fixed')
if __name__=='__main__':
 import sys
 {'start':start,'authority':authority,'references':references}[sys.argv[1]]()
