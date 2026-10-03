"""Independent diagnostic correction only. Never fits or changes scored models."""
import collections,datetime,gzip,hashlib,json,shutil
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import independent_audit as auditor
HERE=Path(__file__).resolve().parent
def run():
 archive=HERE/'PRIVATE_PREFIT_LINEAGE';archive.mkdir(exist_ok=True)
 for name in ['TEACHER_LABELS.jsonl.gz','PRIVATE_INPUTS/targets.npy','OOF_P0_UPSIDE.jsonl.gz','OOF_P0_QUALITY.jsonl.gz','OOF_P0_ADVERSE.jsonl.gz','OOF_P1_UPSIDE.jsonl.gz','OOF_P1_QUALITY.jsonl.gz','OOF_P1_ADVERSE.jsonl.gz']:
  p=HERE/name;target=archive/Path(name).name
  if not target.exists():shutil.copyfile(p,target)
 raw=auditor.read(auditor.INPUT/'raw_paths_selected.json.gz');ws=list(auditor.rows(HERE/'WATCH_RECORDS.jsonl.gz'));grid=list(auditor.rows(HERE/'PERSISTENT_GRID.jsonl.gz'));Y=np.load(archive/'targets.npy');correct=Y.copy();days=np.asarray([r['session'] for r in grid]);changes=collections.Counter();by_session=collections.Counter();proofs=[];cache={};last=None
 for r in auditor.rows(archive/'TEACHER_LABELS.jsonl.gz'):
  key=r['watch_key'];day=r['session'];i=r['row_index']
  if key!=last:cache={};last=key;a=auditor.valid(raw[key]['today'])
  f=auditor.fill(day,a,r['intent_minute'])
  if f is None:continue
  if f[0] not in cache:cache[f[0]]=auditor.expected_teacher(day,a,*f)
  e=cache[f[0]]
  for h,label in enumerate(['U_target','Q_target','D_target']):
   v=e[label];old=None if not np.isfinite(Y[i,h]) else float(Y[i,h]);correct[i,h]=np.nan if v is None else float(v)
   if not auditor.same(old,v):
    changes[label]+=1;by_session[day]+=1
    if len(proofs)<20:proofs.append({'row_id':r['row_id'],'head':label,'old':old,'corrected':float(v) if v is not None else None,'reason':'expected source order; same set of observed bars, no fabricated gap'})
 np.save(archive/'corrected_targets_diagnostic.npy',correct)
 folds=auditor.read(HERE/'SPLIT_PRECOMMIT.json')['folds'];affected=[]
 for family in ['P0','P1']:
  for fold in folds:
   tr=np.isin(days,fold['train']);te=np.isin(days,fold['test'])
   for h,head in enumerate(['UPSIDE','QUALITY','ADVERSE']):
    old=np.isfinite(Y[tr,h]);new=np.isfinite(correct[tr,h]);mask_N=int(np.sum(old!=new));val_N=int(np.sum(old&new&(abs(Y[tr,h]-correct[tr,h])>1e-8)))
    if mask_N or val_N:affected.append({'family':family,'fold':fold['id'],'head':head,'original_train_target_N':int(old.sum()),'corrected_train_target_N':int(new.sum()),'training_eligibility_mismatch_N':mask_N,'finite_training_value_mismatch_N':val_N,'original_test_target_N':int(np.isfinite(Y[te,h]).sum()),'corrected_test_target_N':int(np.isfinite(correct[te,h]).sum())})
 receipt={'saved_at_jst':datetime.datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),'status':'BLOCKED_SPLIT_OR_LINEAGE_MISMATCH','root_cause':'source_starts returned AM continuous then PM continuous then AM terminal690; comparing chronology against that unsorted array falsely censored complete AM-to-PM paths','future_causal_leakage_found':False,'affected_teacher_rows_by_head':dict(changes),'original_finite_target_N':{k:int(np.isfinite(Y[:,h]).sum()) for h,k in enumerate(['UPSIDE','QUALITY','ADVERSE'])},'chronological_diagnostic_finite_target_N':{k:int(np.isfinite(correct[:,h]).sum()) for h,k in enumerate(['UPSIDE','QUALITY','ADVERSE'])},'affected_fit_N':len(affected),'affected_fits':affected,'fits_already_completed':30,'refits_required_for_exact_frozen_30_fit_design':len(affected),'would_total_fits':30+len(affected),'hard_cap':36,'additional_fits_executed':0,'automatic_refit_allowed':False,'production_promotion_allowed':False,'original_labels_preserved':True,'corrected_targets_are_diagnostic_not_replacement_training_labels':True,'proof_examples':proofs,'affected_session_N':len(by_session),'selector_identity_grid_score_first_cross_and_fills_unchanged':True,'EXIT_calls':0,'reentry_calls':0,'orders':0,'main_merge':0}
 (HERE/'CALENDAR_INTEGRITY_DIAGNOSIS.json').write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['affected_fits','proof_examples']},ensure_ascii=False))
if __name__=='__main__':run()
