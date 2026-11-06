"""Phase F: exact hash/identity only. Never import an EXIT/Entry engine."""
from work_io import *
import gzip, zipfile, shutil

def require(ok,label,audit=False):
    if not ok:raise RuntimeError(('BLOCKED_EXIT_V3_FREEZE_AUDIT_MISMATCH' if audit else 'BLOCKED_EXIT_V3_FREEZE_IDENTITY_MISMATCH')+': '+label)

def run():
    starts=read(INPUT/'actual_GET/START_BRANCH_GETS.json')
    for name,expected in [('v3',V3_HEAD),('v4',V4_HEAD)]:
        require(starts[name]['commit']['sha']==expected,name+' actual start HEAD')
    public_N={}
    for name,path in [('v3',V3),('v4',V4)]:
        for f in ['FINAL_PROVENANCE_MANIFEST.json','FINAL_STATUS.json','INDEPENDENT_AUDIT.json','CONTRACT_FREEZE_RECEIPT.json']:
            require((path/f).read_bytes()==(INPUT/'actual_GET'/name/f).read_bytes(),name+' actual GET '+f)
        manifest=read(path/'FINAL_PROVENANCE_MANIFEST.json')
        for f,item in manifest['files'].items():
            require(sha(path/f)==item['sha256'] and (path/f).stat().st_size==item['bytes'],name+' public '+f)
        public_N[name]=len(manifest['files'])
    m3=read(V3/'FINAL_PROVENANCE_MANIFEST.json');m4=read(V4/'FINAL_PROVENANCE_MANIFEST.json')
    require(m3['status']=='STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_EVIDENCE_READY','V3 final ready')
    require(m4['status']=='V4_NOT_BETTER_KEEP_V3','V4 rejected status')
    a=read(V3/'INDEPENDENT_AUDIT.json')
    require(a['mismatch_N']==a['future_causal_leakage_N']==0,'V3 audited zero mismatch/leakage',True)
    ea=read(INPUT/'first_entry_public/INDEPENDENT_REPAIR_AUDIT.json')
    ef=read(INPUT/'first_entry_public/FIRST_ENTRY_V2_FREEZE_RECEIPT.json')
    require(ef['status']=='PERSISTENT_UPTREND_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE' and ef['EntryFrozen'] and ef['Entry_N']==1600,'Entry official freeze')
    require(ea['mismatch_N']==ea['future_causal_leakage']==0,'Frozen Entry audit',True)
    epath=TRACE/'FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'
    require(sha(epath)==ef['evidence_files']['P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz']['sha256'],'Entry exact bytes')
    with gzip.open(epath,'rt') as f: entries=[json.loads(x) for x in f]
    chosen=[x for x in entries if x['entry_status']=='FIRST_ENTRY']
    require(len(chosen)==1600 and len({x['watch_key'] for x in chosen})==1600,'Entry identity N')
    for f,pin in PINS.items():require(sha(WORK/'inputs_v3/v2_public/FROZEN_SOURCE'/f)==pin,'Frozen semantic '+f)
    contract=read(V3/'CONTRACT_FREEZE_RECEIPT.json')
    # Every frozen decision / fill / clock file remains byte-identical at source.
    for f,pin in contract['decision_code_hashes'].items():require(sha(V3/f)==pin,'V3 core '+f)
    archive=WORK/m3['private_evidence_package']['filename']
    require(sha(archive)==m3['private_evidence_package']['sha256'],'V3 private archive')
    with zipfile.ZipFile(archive) as z:private_manifest=json.loads(z.read('MANIFEST.json'))
    for f,item in private_manifest['components'].items():
        require(sha(P3/f)==item['sha256'] and (P3/f).stat().st_size==item['bytes'],'V3 private '+f)
    dep=WORK/'inputs_v3/saved_v2/Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip'
    require(sha(dep)==m3['v2_exact_trace_reuse_receipt']['package_sha256'],'Original full-trace archive')
    tm=read(TRACE/'MANIFEST.json')
    for f,item in tm['components'].items():
        require(sha(TRACE/f)==item['sha256'] and (TRACE/f).stat().st_size==item['bytes'],'Original trace dependency '+f)
    keys={x['watch_key'] for x in chosen}
    for f in ['REPLAY_ROWS.jsonl.gz','ECONOMICS_ROWS.jsonl.gz','PAIRED_ROWS.jsonl.gz']:
        with gzip.open(P3/f,'rt') as z:r=[json.loads(x) for x in z]
        require(len(r)==1600 and {x['watch_key'] for x in r}==keys,'V3 saved join '+f)
    receipt={'saved_at_jst':now(),'actual_basis_head':V4_HEAD,'document_id':DOCUMENT,'status':'STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_OFFICIAL_FREEZE','name':'State9 Structural EXIT v3 — Local Guard','policy':'STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD','ExitFrozen':True,'EntryFrozen':True,'ReentryPending':True,'CapitalPending':True,'productionReady':False,'V3_FINAL_HEAD':V3_HEAD,'V4_FINAL_HEAD':V4_HEAD,'V4_status':'V4_NOT_BETTER_KEEP_V3','V4_EXIT_D_adopted':False,'V4_Recovery_Floor_adopted':False,'FIRST_ENTRY_HEAD':ENTRY_HEAD,'Frozen_Entry_N':1600,'Frozen_Entry_sha256':sha(epath),'V3_contract_sha256':contract['contract_sha256'],'V3_manifest_sha256':sha(V3/'FINAL_PROVENANCE_MANIFEST.json'),'V3_private_archive_sha256':sha(archive),'original_trace_archive_sha256':sha(dep),'Frozen_semantic_pins':PINS,'V3_decision_code_hashes':contract['decision_code_hashes'],'V3_A_B_C_PRE_quality_fill_calendar_semantics_changes':0,'V3_evidence_changes':0,'V3_public_file_hash_checks_N':public_N['v3'],'V4_public_file_hash_checks_N':public_N['v4'],'V3_private_component_hash_checks_N':len(private_manifest['components']),'full_trace_dependency_hash_checks_N':len(tm['components']),'formal_full_trace_files_N':1600,'V3_audit_mismatch_N':a['mismatch_N'],'V3_audit_future_causal_leakage_N':a['future_causal_leakage_N'],'freeze_performance_recalculation_N':0,'Entry_replay_refit_N':0,'State9_Path_reconstruction_N':0,'V3_replay_N':0,'model_teacher_search_N':0,'provider_new_data_N':0,'frozen_reason_semantics':{'EXIT_A':'main context UP→DOWN','EXIT_B':'independent RANGE retires old UP context','EXIT_C':'confirmed local higher-low Local Guard broken','fallback':'SESSION_CLOSE'},'safety':SAFETY}
    write(ROOT/'EXIT_V3_OFFICIAL_FREEZE_RECEIPT.json',receipt)
    write(ROOT/'START_ACTUAL_GET_RECEIPT.json',{'saved_at_jst':now(),'actual_basis_head':V4_HEAD,'V3_HEAD':V3_HEAD,'FIRST_ENTRY_HEAD':ENTRY_HEAD,'actual_GETs':starts})
    # Whole immutable copies for later re-entry positions. No execution in Phase F.
    for f in ['frozen_v2_lifecycle.py','local_guard.py','reused_clock.py','reused_fill.py']:
        shutil.copyfile(V3/f,ROOT/f)
    checkpoint('F0_EXIT_V3_OFFICIAL_FREEZE',V4_HEAD,receipt['status'],['V3 OFFICIAL FREEZE','Frozen Entry identity and all State9/Path pins','V3 audited hashes unchanged; V4 rejected D excluded'],['EXIT_V3_OFFICIAL_FREEZE_RECEIPT.json','START_ACTUAL_GET_RECEIPT.json'],'Verify post-exit Frozen P1_Q70 signals; precommit one Re-entry contract')
    print(json.dumps({k:receipt[k] for k in ['status','Frozen_Entry_N','V3_public_file_hash_checks_N','V3_private_component_hash_checks_N','full_trace_dependency_hash_checks_N','V3_audit_mismatch_N','V3_audit_future_causal_leakage_N']}))

if __name__=='__main__':run()
