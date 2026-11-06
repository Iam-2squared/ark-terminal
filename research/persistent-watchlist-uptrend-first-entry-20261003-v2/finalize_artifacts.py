"""Hash finite Work evidence and package private records. No fits or network calls."""
import argparse,datetime,hashlib,json,pathlib,zipfile
from zoneinfo import ZoneInfo
HERE=pathlib.Path(__file__).resolve().parent
SCRATCH=HERE.parents[2]
STATUS='BLOCKED_SPLIT_OR_LINEAGE_MISMATCH'
BRANCH='persistent-watchlist-uptrend-first-entry-20261003-v2'
PACKAGE_NAME='Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip'
REQUIRED=['SELECTOR_REPEAT_AUDIT.json','WATCH_IDENTITY_CONTRACT.json','PERSISTENT_GRID_RECEIPT.json','FEATURE_FREEZE.json','CLEAN_UPTREND_TEACHER_CONTRACT.json','TEACHER_LABELS.jsonl.gz','SPLIT_PRECOMMIT.json']+[f'OOF_{f}_{h}.jsonl.gz' for f in ['P0','P1'] for h in ['UPSIDE','QUALITY','ADVERSE']]+['UPTREND_SCORE_ROWS.jsonl.gz']+[f'FIRST_ENTRY_{p}.jsonl.gz' for p in ['Q70','Q80','Q90','Q95']]+['SELECTOR_WATCH_BUCKET_EVALUATION.json','WINNER_PRESERVATION.json','ENTRY_HIGH_EVALUATION.json','PATH_QUALITY_EVALUATION.json','MAE_EVALUATION.json','DAILY_FIRST_ENTRY_ACTIVITY.json','QUALITY_CANDIDATE.json','BALANCED_CANDIDATE.json','STATE_INCREMENTAL_VALUE.json','INDEPENDENT_AUDIT.json','REPORT-ja.md','FINAL_HANDOFF.md']
def now():return datetime.datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def eligible(path):
    return path.is_file() and not any(x.startswith('.') or x in ['__pycache__','_matrix_work'] for x in path.relative_to(HERE).parts)
def private_members():
    files=[p for p in HERE.glob('*.gz')]
    for folder in ['PRIVATE_INPUTS','PRIVATE_MODELS','PRIVATE_PREFIT_LINEAGE','LOCAL_GET_RECEIPTS']:
        files.extend(p for p in (HERE/folder).rglob('*') if eligible(p) and (folder!='PRIVATE_PREFIT_LINEAGE' or p.suffix in ['.gz','.npy','.npz','.pkl']))
    return sorted(set(files))
def describe(path,scope):return {'path':str(path.relative_to(HERE)),'bytes':path.stat().st_size,'sha256':digest(path),'publication':scope}
def manifest(basis):
    assert all((HERE/n).is_file() for n in REQUIRED)
    private=set(private_members())
    all_files=[p for p in HERE.rglob('*') if eligible(p) and p.name!='MANIFEST.json' and 'LOCAL_GET_RECEIPTS' not in p.relative_to(HERE).parts]
    artifacts=[describe(p,'private_package' if p in private else 'historical_git_copy' if 'PRIVATE_PREFIT_LINEAGE' in p.relative_to(HERE).parts else 'github_public') for p in sorted(all_files)]
    audit=json.loads((HERE/'INDEPENDENT_AUDIT.json').read_text())
    obj={'document_id':'WORK_PERSISTENT_WATCHLIST_STATE_UPTREND_FIRST_ENTRY_V2_20261003','saved_at_jst':now(),'actual_basis_head':basis,'status':STATUS,'repo':'Iam-2squared/ark-terminal','branch':BRANCH,'artifacts':artifacts,'private_deliverable':PACKAGE_NAME,'required_files_present':{n:True for n in REQUIRED},'completion_gate':{'first_entry_generation_complete':True,'all_fixed_policies_saved':True,'corrected_teacher_evaluator_saved':True,'successful_correct_teacher_OOF_model_design':False,'independent_audit_pass':False,'candidate_freeze_allowed':False,'next_EXIT_research_handoff_allowed':False,'ended_under_authorized_integrity_STOP':True},'lineage':{'original_completed_fits':30,'teacher_calendar_newly_eligible_rows_each_Q_D':13948,'affected_head_fits':20,'additional_fits':0,'refits_required':20,'would_total_fits':50,'hard_cap':36,'original_training_labels_models_preserved':True,'current_teacher_labels':'correct chronological evaluator labels','OOF_predictions_and_scores':'original 30 fitted models; Q/D training eligibility differs from corrected teacher','candidate_names':'diagnostic ranking only, not valid frozen Development candidates'},'audit':{'status':audit['status'],'mismatch_N':audit['mismatch_N'],'failure_counts':audit['failure_counts'],'fit':0},'exposure':{'provider':0,'Protected':0,'Fresh':0,'Validation':0,'OOS':0,'Prospective':0,'EXIT_Replay':0,'Reentry_Replay':0,'Capital_Replay':0,'orders':0,'main_merge':0,'fits':30,'searches':0,'bootstrap':0},'safety':{k:False for k in ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady']},'manifest_self_hash':'excluded; final Git commit binds this file without inventing future commit SHA'}
    save(HERE/'MANIFEST.json',obj)
    print(json.dumps({'status':STATUS,'manifest_artifacts':len(artifacts),'required_files_present_N':len(REQUIRED),'private_evidence_uncompressed_bytes':sum(p.stat().st_size for p in private)},ensure_ascii=False))
def package(result_head):
    final_get=json.loads((HERE/'LOCAL_GET_RECEIPTS/FINAL.json').read_text())
    assert result_head in json.dumps(final_get),'Package must use actual post-commit GET receipt'
    files=private_members()
    source_files=sorted(p for p in (SCRATCH/'persistent_sources').rglob('*') if p.is_file())+[SCRATCH/'private_source/PRIVATE_SELECTED_SOURCE_TOKENS.json.gz',SCRATCH/'downloads/immediate.json.gz',SCRATCH/'downloads/R1_ENTRY_RECORDS.json.gz']
    assert all(p.is_file() for p in source_files)
    entries=[{'archive_path':str(p.relative_to(SCRATCH)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in files+source_files]
    receipt={'saved_at_jst':now(),'status':STATUS,'actual_final_github_head':result_head,'github_commit':f'https://github.com/Iam-2squared/ark-terminal/commit/{result_head}','records_and_models_are_diagnostic_only':True,'model_teacher_lineage_valid':False,'fits':30,'additional_fits':0,'audit_fit':0,'EXIT_calls':0,'reentry_calls':0,'entries':entries,'reproduction':'Obtain public code/contracts/report from exact GitHub commit, extract private members next to repo in original relative layout. Do not run model_oof.py: corrected teacher/model eligibility mismatch is blocked and repair exceeds authorized fit cap.'}
    readme=f'''Ark Terminal — FIRST ENTRY v2 private evidence\n\nStatus: {STATUS}\nActual final GitHub HEAD: {result_head}\nPublic report/contracts/code: https://github.com/Iam-2squared/ark-terminal/tree/{result_head}/research/{BRANCH}\n\nThis package preserves generated FIRST ENTRY records, original models/labels, corrected evaluator labels, full causal grid/features, saved-source inputs and actual GET receipts. It does not contain a validated corrected-teacher OOF design. QUALITY=P0_Q80 and BALANCED=P1_Q70 are diagnostic rankings only. Do not Freeze, promote or hand off to EXIT from this Work.\n\n30 fits were completed. The chronological calendar fix changes training eligibility for 20 Q/D head fits; repair would require 50 total fits, exceeding hard cap36. No extra fit was run. All trading permissions remain false. EXIT, R50 adapter, Re-entry, Capital, new provider, Fresh, orders and main merge are zero.\n\nArchive members preserve paths relative to the workspace. Restore alongside an ark-terminal checkout of the exact commit. Public Git-backed code/artifacts are kept in GitHub; private files and saved inputs are here. Per-file SHA256 values are in PRIVATE_PACKAGE_MANIFEST.json. Running independent_audit.py with the preserved models correctly reports the 20 training-label cohort mismatches.\n'''
    out=SCRATCH/'deliverables'/PACKAGE_NAME;out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        z.writestr('PRIVATE_PACKAGE_MANIFEST.json',json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        z.writestr('README_PRIVATE_EVIDENCE.txt',readme)
        for p in files+source_files:
            method=zipfile.ZIP_STORED if p.suffix in ['.gz','.npz'] else zipfile.ZIP_DEFLATED
            z.write(p,str(p.relative_to(SCRATCH)),compress_type=method)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None,'ZIP integrity failure'
        assert len(z.namelist())==len(entries)+2
    print(json.dumps({'local_path':str(out),'bytes':out.stat().st_size,'sha256':digest(out),'members':len(entries)+2,'zip_integrity':'PASS','actual_final_head':result_head},ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest-basis-head');p.add_argument('--package-result-head');a=p.parse_args()
    if a.manifest_basis_head:manifest(a.manifest_basis_head)
    if a.package_result_head:package(a.package_result_head)
