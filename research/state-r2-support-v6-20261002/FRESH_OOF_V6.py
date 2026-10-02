"""One-shot labels, whole provenance control, R1/R2 outer OOF. No metrics choices."""
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timezone,timedelta
import json,csv,hashlib
import numpy as np
import MODEL_V5 as m
import TARGET_KERNEL_V3_FROZEN as frozen
R=Path(__file__).resolve().parent;P=R/'PARENT_V4'
def precheck():
 pre=json.loads((R/'PREDICTIVENESS_V6_PRECOMMIT.json').read_text())
 for n,h in pre['hashes'].items():assert m.sha(R/n)==h,'V6_PRECOMMIT_BREACH:'+n
 for n,h in json.loads((R/'EVALUATION_CODE_FREEZE_V6.json').read_text())['hashes'].items():assert m.sha(R/n)==h,'V6_EVALUATION_CODE_BREACH:'+n
 return pre
def main():
 assert (R/'CHECKPOINTS/C3_POST_GET.json').exists(),'C4_POST_COMMIT_GET_REQUIRED_BEFORE_LABELS'
 pre=precheck();manifest=json.loads((R/'FRESH_DATA_MANIFEST_V6.json').read_text());old=json.loads((P/'DATASET_MANIFEST_PORTABLE_V4.json').read_text());features={};labels={};freshkeys=set();files=[];availability=Counter()
 assert not (R/'R1_R2_OOF_V6.jsonl').exists(),'ONE_SHOT_ALREADY_DONE'
 # Immutable V4 and V5 exposed outcomes are chronological training-only.
 old={**old,'pairs':old['pairs']+[{**p,'_V5':True} for p in json.loads((R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1/FRESH_DATA_MANIFEST_V5.json').read_text())['pairs']]}
 for p in old['pairs']:
  root=(R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1') if p.get('_V5') else P
  lab={r['row_key']:r['REAL']['CONTEXT_REVERSAL'] for r in map(json.loads,(root/p['label_path']).open())}
  for r in map(json.loads,(root/p['feature_path']).open()):
   if lab[r['row_key']]['available']:features[r['row_key']]=r;labels[r['row_key']]=lab[r['row_key']]
 for p in manifest['pairs']:
  assert m.sha(R/p['feature_path'])==p['feature_SHA256'],'INPUT_CHANGED';rows=list(map(json.loads,(R/p['feature_path']).open()));look={r['tradable_index']:i for i,r in enumerate(rows) if r['tradable_index'] is not None};fp=R/p['label_path'];fp.parent.mkdir(exist_ok=True)
  with fp.open('x') as f:
   for i,r in enumerate(rows):
    l=frozen.target(rows,i,'CONTEXT_REVERSAL',look);record={'row_key':r['row_key'],'date':r['date'],'security_id':r['security_id'],'session_id':r['session_id'],'bar_end':r['bar_end'],'REAL':{'CONTEXT_REVERSAL':l},'exposure':'V6_UNEXPOSED_DEVELOPMENT_PAIR'};f.write(json.dumps(record,sort_keys=True,separators=(',',':'))+'\n');availability[l['target'] if l['available'] else l['reason']]+=1
    if l['available']:
     assert r['row_key'] not in features,'PARTITION_DUPLICATE';features[r['row_key']]=r;labels[r['row_key']]=l;freshkeys.add(r['row_key'])
  files.append({'path':p['label_path'],'SHA256':m.sha(fp),'bytes':fp.stat().st_size})
 m.save('LABEL_FIXATION_RECEIPT_V6.json',{'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'files':files,'availability':dict(availability),'fresh_available_anchor_N':len(freshkeys),'new_endpoint_labels':sum(p['scheduled_endpoints_N'] for p in manifest['pairs']),'State_target_semantic_changes':0,'old_labels_regenerated':0,'precommit_SHA256':m.sha(R/'PREDICTIVENESS_V6_PRECOMMIT.json')})
 by=defaultdict(list);donor={};permutation=[]
 for k,r in sorted(features.items()):by[(r['date'],r['security_id'],r['session_id'])].append(k)
 for group,ks in sorted(by.items()):
  seed=int(hashlib.sha256((str(pre['null_seed_prefix'])+'|CONTEXT_REVERSAL|'+'|'.join(group)).encode()).hexdigest()[:16],16);perm=np.random.default_rng(seed).permutation(len(ks))
  for k,j in zip(ks,perm):donor[k]=ks[int(j)];permutation.append({'task':'CONTEXT_REVERSAL','date':group[0],'security_id':group[1],'session_id':group[2],'feature_key':k,'donor_key':donor[k],'group_N':len(ks),'identity':k==donor[k]})
 with (R/'PERMUTATION_MAPPING_V6.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['task','date','security_id','session_id','feature_key','donor_key','group_N','identity']);w.writeheader();w.writerows(permutation)
 split=json.loads((R/'SPLIT_REALIZED_V6.json').read_text());schema=json.loads((P/'FEATURE_SCHEMA_V4.json').read_text());oof=[];selections=[];inner=[];realized=[]
 for fold in split['folds']:
  stats={'fold':fold['fold'],'test_dates':fold['test_dates'],'train_input_dates':len(fold['train_dates']),'status':'EMPTY_OR_INSUFFICIENT_TRAIN','train_N':0,'test_N':0}
  if fold['test_dates'] and fold['initial_train_dates_sufficient']:
   test=[r for k,r in sorted(features.items()) if k in freshkeys and r['date'] in fold['test_dates']]
   trains={control:[r for k,r in sorted(features.items()) if r['date'] in fold['train_dates'] and labels[donor[k] if control=='TRUE_NULL' else k]['label_end']<fold['test_start']] for control in ['REAL','TRUE_NULL']}
   assert {r['row_key'] for r in trains['REAL']}=={r['row_key'] for r in trains['TRUE_NULL']},'CONTROL_PURGE_KEYS_MISMATCH'
   stats.update(train_N=len(trains['REAL']),test_N=len(test))
   if trains['REAL'] and test:
    stats['status']='EVALUABLE'
    for control in ['REAL','TRUE_NULL']:
     targets={k:labels[donor[k] if control=='TRUE_NULL' else k] for k in features}
     for model in ['R1','R2']:
      raw,cal,path,art=m.fit(trains[control],test,targets,model,schema,fold['train_dates'],'fresh',fold['fold'],control);selections.append({'fold':fold['fold'],'control':control,'model':model,'alpha':art['alpha'],'T':art['temperature'],'inner_plan':art['inner_plan'],'fallback_reason':art['fallback_reason'],'fit_path':path,'fit_SHA256':m.sha(R/path)})
      for ix in art['inner_artifacts']:
       for j,k in enumerate(ix['validation_keys']):inner.append({'fold':fold['fold'],'control':control,'model':model,'inner_fold':ix['inner_fold'],'alpha':ix['alpha'],'selected_alpha':ix['alpha']==art['alpha'],'row_key':k,'date':features[k]['date'],'actual':m.CLASSES[ix['validation_actual'][j]],'probabilities':json.dumps(ix['validation_probabilities'][j]),'outer_test_used':False})
      for i,r in enumerate(test):
       l=targets[r['row_key']]
       for calibrated,pred in [(False,raw),(True,cal)]:oof.append({'row_key':r['row_key'],'date':r['date'],'security_id':r['security_id'],'session_id':r['session_id'],'current_primary':r['features']['formal_primary'],'fold':fold['fold'],'control':control,'model':model,'calibrated':calibrated,'actual':l['target'],'predicted':m.CLASSES[int(pred[i].argmax())],'probabilities':pred[i].tolist(),'label_start':l['label_start'],'label_end':l['label_end'],'donor_anchor_key':l['donor_anchor_key'],'future_key':l['future_key'],'fit_path':path,'fresh_evaluation':True})
      print(json.dumps({'lane':'fresh','fold':fold['fold'],'control':control,'model':model,'train_N':len(trains[control]),'test_N':len(test),'alpha':art['alpha'],'T':art['temperature'],'fallback':art['fallback_reason']}),flush=True)
  realized.append(stats)
 with (R/'R1_R2_OOF_V6.jsonl').open('x') as f:
  for r in oof:f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
 fields=['row_key','date','security_id','session_id','current_primary','fold','control','model','calibrated','actual','predicted','probabilities','label_start','label_end','donor_anchor_key','future_key','fit_path','fresh_evaluation']
 with (R/'R1_R2_OOF_V6.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({**r,'probabilities':json.dumps(r['probabilities'])} for r in oof)
 with (R/'CALIBRATION_INNER_OOF_V6.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=['fold','control','model','inner_fold','alpha','selected_alpha','row_key','date','actual','probabilities','outer_test_used']);w.writeheader();w.writerows(inner)
 m.save('CALIBRATION_SELECTION_RECEIPT_V6.json',{'method':'ROLLING_INNER_OOF_TEMPERATURE_V1','selections':selections,'outer_test_labels_used':0,'successful_refits':0})
 m.save('FRESH_OOF_FIXATION_RECEIPT_V6.json',{'status':'MEASURED' if oof else 'NOT_EVALUABLE','OOF_SHA256':m.sha(R/'R1_R2_OOF_V6.jsonl'),'OOF_rows':len(oof),'realized_folds':realized,'new_scope_after_label':0,'precommit_changes':0,'R3_R4_fresh_fits':0,'successful_candidate_refits':0})
 print(json.dumps({'OOF_rows':len(oof),'folds':realized,'fresh_available':len(freshkeys)}))
if __name__=='__main__':main()
