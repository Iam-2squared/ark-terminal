"""Targeted contract bug repair only. Does not rerun completed metric/rank/channel stages."""
import json,pathlib,numpy as np
from adapter import ROOT,BASE,OUT,PRIVATE,read,rows,save,sha,now
from diagnostics import load_data,HEADS
from metrics import cluster_auc,ci
def main():
 assert (OUT/'INDEPENDENT_INITIAL_AUDIT.json').exists() and not (OUT/'BOOTSTRAP_PAIR_REPAIR_RECEIPT.json').exists()
 data,masks,sessions,M=load_data();initial=read(OUT/'INDEPENDENT_INITIAL_AUDIT.json');assert initial['mismatch_N']==194 and all('CI' in r['check'] for r in initial['failures'])
 matrix=read(OUT/'EXPERT_TARGET_MATRIX.json');oldmatrixhash=sha(OUT/'EXPERT_TARGET_MATRIX.json');arrays={k:v for k,v in np.load(PRIVATE/'PRIMARY_SUBSET_BOOTSTRAP_VALUES.npz').items()};repaired=0
 for name,z in matrix['cohorts'].items():
  if name=='C2':ids=masks['C2']
  elif name=='C3':ids=masks['C3']
  elif name.startswith('C2_slot'):ids=[k for k in masks['C2'] if data[k]['native_funded_slot']==int(name[-1])]
  else:ids=masks['C4'][name[3:]]
  for r in z['metrics']:
   if r.get('AUC') is None:continue
   h,t,d=r['head'],r['target'],r['direction'];rr=[data[k] for k in ids if data[k][t] is not None and data[k]['scores'][h] is not None];idx=[sessions.index(q['session']) for q in rr];bs=cluster_auc([d*q['scores'][h] for q in rr],[q[t] for q in rr],idx,M);r['AUC_bootstrap']=ci(bs);arrays[name+'|'+h+'|'+t]=bs;repaired+=1
 save('corrections/EXPERT_TARGET_MATRIX.json',matrix)
 np.savez_compressed(PRIVATE/'PRIMARY_SUBSET_BOOTSTRAP_VALUES_CORRECTED.npz',**arrays)
 signed=read(OUT/'MRET_SIGNED_CONTROLS.json');signedarrays={k:v for k,v in np.load(PRIVATE/'PRIMARY_SIGNED_BOOTSTRAP_VALUES.npz').items()}
 for name,z in signed['cohorts'].items():
  ids=masks[name];target=z['target']
  for tag,r in z['scores'].items():
   h=tag.lstrip('-');d=-1 if tag.startswith('-') else 1;rr=[data[k] for k in ids if data[k][target] is not None];idx=[sessions.index(q['session']) for q in rr];bs=cluster_auc([d*q['scores'][h] for q in rr],[q[target] for q in rr],idx,M);r['AUC_bootstrap']=ci(bs);signedarrays[name+'|'+tag+'|AUC']=bs
  for tag,r in z['all_control_deltas'].items():r['paired_bootstrap']=ci(signedarrays[name+'|MRET|AUC']-signedarrays[name+'|'+tag+'|AUC'])
 save('corrections/MRET_SIGNED_CONTROLS.json',signed);np.savez_compressed(PRIVATE/'PRIMARY_SIGNED_BOOTSTRAP_VALUES_CORRECTED.npz',**signedarrays)
 roles=read(OUT/'ROLE_DECISIONS.json')
 for role,c,h,targets in [('Winner Priority','C3','pP',['U5','U10']),('Weak Risk','C2','MOVE_U2',['Weak']),('Medium+ Priority','C3','MOVE_U3',['U3'])]:
  mm=[next(r for r in matrix['cohorts'][c]['metrics'] if r.get('head')==h and r.get('target')==t) for t in targets];passed=all(m['AUC_bootstrap']['valid_N']>=1900 and m['AUC_bootstrap']['CI95'][0]>.5 and m['known_N']==m['total_N'] for m in mm);point=all(m['AUC'] is not None and m['AUC']>.5 for m in mm);roles[role]['metrics']=mm;roles[role]['status']='SUPPORTED_FOR_DESIGN' if passed else 'INCONCLUSIVE' if point else 'UNSUPPORTED_ON_V5'
 z=signed['cohorts']['C2'];m=z['scores']['MRET'];passed=m['AUC_bootstrap']['CI95'][0]>.5 and m['AUC_bootstrap']['valid_N']>=1900 and m['known_N']==m['total_N'] and all(r['paired_bootstrap']['valid_N']>=1900 and r['paired_bootstrap']['CI95'][0]>0 for r in z['all_control_deltas'].values());role=roles['Absolute-Loss Defense via MRET'];role['metric']=m;role['all_signed_contrasts']=z['all_control_deltas'];role['status']='SUPPORTED_FOR_DESIGN' if passed else 'INCONCLUSIVE' if m['AUC']>.5 else 'UNSUPPORTED_ON_V5';role['incremental_status']='SUPPORTED_FOR_DESIGN' if passed else 'NUMERICALLY_CERTIFIED_BUT_INCREMENTAL_VALUE_NOT_ESTABLISHED'
 save('corrections/ROLE_DECISIONS.json',roles)
 boot=read(OUT/'SESSION_BOOTSTRAP_DIAGNOSTICS.json');boot.update({'subset_values_sha256':sha(PRIVATE/'PRIMARY_SUBSET_BOOTSTRAP_VALUES_CORRECTED.npz'),'signed_values_sha256':sha(PRIVATE/'PRIMARY_SIGNED_BOOTSTRAP_VALUES_CORRECTED.npz'),'within_session_pair_bug_repair':True,'old_failed_outputs_preserved':True,'roles':{k:v['status'] for k,v in roles.items()}});save('corrections/SESSION_BOOTSTRAP_DIAGNOSTICS.json',boot)
 save('BOOTSTRAP_PAIR_REPAIR_RECEIPT.json',{'exact_jst':now(),'failure':'row-weighted AUC resamples used within-session pair m squared instead of fixed contract m once','fixed_definition_unchanged':True,'initial_mismatch_N':initial['mismatch_N'],'failed_original_matrix_sha256':oldmatrixhash,'original_F4_F5_outputs_preserved':True,'changed_calculations':['AUC bootstrap resamples and CIs','paired signed AUC delta CIs','dependent role screens'],'unchanged':['raw scores','identity masks','original metrics','point AUC/AP/Spearman','AP bootstrap','TopK sets and their conditioned CIs','concordance bootstrap','rank pair ledger','channel census','screen thresholds/seed/resamples/tolerance'],'new_fit_inference_replay':0,'primaryDiagnosticBatch':1,'independentDiagnosticVerification':1,'correction_code_sha256':sha(pathlib.Path(__file__)),'metric_code_sha256':sha(BASE/'code/metrics.py'),'original_failed_code_sha256':'c27dd1fc2e89cc5bcc6b3e2e112e0bedf9d356827e932e538c147785476cd375','corrected_subset_metric_N':repaired,'resume':'independent compare failed resamples only; omitted concordance CI checks added without rerun of completed checks'})
 print(json.dumps({'repaired_subset_AUC_bootstraps':repaired,'roles':{k:v['status'] for k,v in roles.items()}}))
if __name__=='__main__':main()
