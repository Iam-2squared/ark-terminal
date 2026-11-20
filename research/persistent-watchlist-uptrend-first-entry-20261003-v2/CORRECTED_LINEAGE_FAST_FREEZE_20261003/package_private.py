"""Preserve corrected private rows/models as an immutable overlay; fit=0."""
from repair_utils import *
import zipfile

def run():
 freeze=read(HERE/'FIRST_ENTRY_V2_FREEZE_RECEIPT.json');assert freeze['EntryFrozen'] and freeze['independent_audit_mismatch_N']==0
 base=SCRATCH/'recovered_first_entry/Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip';base_sha=sha(base);assert base_sha=='c0024055e9afa19089318c0f2a281e3fe15d48e10945b752be48e9239235ac15'
 selected=[]
 for p in sorted(HERE.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(HERE)
  if '_matrix_work' in rel.parts or '__pycache__' in rel.parts:continue
  if p.suffix in ['.gz','.npy','.npz','.pkl']:
   if p.name in ['features_numeric.npy','features_categories.npy','PERSISTENT_GRID.jsonl.gz','STATE_FEATURE_METADATA.jsonl.gz','STATE_TIMELINE_WATCH_RECEIPTS.jsonl.gz']:continue
   selected.append(p)
  elif rel.parts[0] in ['PRIVATE_MODELS','PRIVATE_AUDIT_HISTORY','LOCAL_GET_RECEIPTS'] or p.name=='category_vocabulary.json':selected.append(p)
 prefix=HERE.relative_to(SCRATCH).as_posix()
 private_files={p.relative_to(HERE).as_posix():{'archive_path':prefix+'/'+p.relative_to(HERE).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in selected}
 snapshot={'saved_at_jst':now(),'document_id':DOCUMENT_ID,'status':freeze['status'],'Primary_Freeze_Target':'P1_Q70','EntryFrozen':True,'productionReady':False,'actual_basis_head':freeze['basis_head'],'format':'private corrected-output overlay; original private evidence package retained unchanged','base_package':{'filename':base.name,'bytes':base.stat().st_size,'sha256':base_sha,'purpose':'immutable grid, causal matrices, State timeline, raw source, original30 fits and original prefit targets for independent replay'},'apply_overlay':'Extract the unchanged base package, then this overlay into the same workspace root. Corrected output paths are in CORRECTED_LINEAGE_FAST_FREEZE_20261003, so old fits/OOF/records remain preserved. Retrieve public contracts/code/receipts from the same GitHub branch and Work directory.','immutable_omitted_inputs':{n:{'sha256':sha(HERE/n),'available_from':'unchanged base private package'} for n in ['PERSISTENT_GRID.jsonl.gz','STATE_FEATURE_METADATA.jsonl.gz','STATE_TIMELINE_WATCH_RECEIPTS.jsonl.gz','PRIVATE_INPUTS/features_numeric.npy','PRIVATE_INPUTS/features_categories.npy']},'included_private_files':private_files,'public_repo_artifacts_not_duplicated':True,'new_Q_D_fits':20,'reused_UPSIDE_fits':10,'provider_EXIT_Reentry_Capital_orders':0,'safety':SAFETY}
 out=SCRATCH/'deliverables/Ark_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE_20261003_PRIVATE.zip';out.parent.mkdir(exist_ok=True)
 with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
  z.writestr('PRIVATE_SNAPSHOT_MANIFEST.json',json.dumps(snapshot,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
  for p in selected:z.write(p,prefix+'/'+p.relative_to(HERE).as_posix())
 with zipfile.ZipFile(out) as z:
  assert z.testzip() is None
  assert len(z.infolist())==len(selected)+1
 receipt={'saved_at_jst':now(),'actual_basis_head':freeze['basis_head'],'filename':out.name,'bytes':out.stat().st_size,'sha256':sha(out),'file_count':len(selected)+1,'private_overlay':True,'public_row_level_publication':0,'base_package_dependency':snapshot['base_package'],'selected_private_files':private_files,'safety':SAFETY}
 write(HERE/'PRIVATE_FREEZE_PACKAGE_RECEIPT.json',receipt)
 public_names=['FIRST_ENTRY_V2_FREEZE_RECEIPT.json','CORRECTED_TEACHER_FREEZE_RECEIPT.json','CORRECTED_FIT_LEDGER.json','CORRECTED_OOF_LINEAGE_RECEIPT.json','P1_Q70_ENTRY_CONTRACT.json','P1_Q70_ENTRY_EVALUATION.json','P1_Q70_SELECTOR_BUCKET_ENTRY_HIGH.json','P1_Q70_PRE_PEAK_MAE_EVIDENCE.json','P1_Q70_PATH_QUALITY_EVIDENCE.json','CORRECTED_REFERENCE_PANEL_P0_Q70_Q95.json','INDEPENDENT_REPAIR_AUDIT.json','FIRST_ENTRY_V2_FREEZE_HANDOFF.md','PRIVATE_FREEZE_PACKAGE_RECEIPT.json','CURRENT_FIRST_ENTRY_V2_FREEZE.json','SELECTOR_WATCH_BUCKET_EVALUATION.json','WINNER_PRESERVATION.json','DAILY_FIRST_ENTRY_ACTIVITY.json','repair_utils.py','preflight.py','repair_refit.py','reconstruct_oof.py','regenerate_first_entry.py','build_entry_contract.py','evaluate_primary.py','independent_repair_audit.py','finalize_freeze.py','package_private.py']
 manifest={'document_id':DOCUMENT_ID,'saved_at_jst':now(),'basis_head':freeze['basis_head'],'current_status':freeze['status'],'EntryFrozen':True,'productionReady':False,'Primary_Freeze_Target':'P1_Q70','public_files':{n:{'bytes':(HERE/n).stat().st_size,'sha256':sha(HERE/n)} for n in public_names},'private_row_level_files':private_files,'private_package':{'filename':out.name,'bytes':out.stat().st_size,'sha256':sha(out),'base_package_filename':base.name,'base_package_sha256':base_sha},'historical_completed':30,'new_repair_completed':20,'incremental_hard_cap':20,'cumulative_fit_ledger':50,'UPSIDE_additional_fit':0,'EXIT_Reentry_Capital_provider_protected_orders_main_merge':0,'safety':SAFETY}
 write(HERE/'MANIFEST.json',manifest)
 print(json.dumps({'private_package':str(out),'bytes':out.stat().st_size,'sha256':receipt['sha256'],'file_count':receipt['file_count'],'manifest_ready':True,'fit':0}))

if __name__=='__main__':run()
