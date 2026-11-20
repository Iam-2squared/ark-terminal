"""Package only new V4 metadata/outcomes. Immutable trace dependencies referenced."""
import hashlib,json,zipfile
from settings import *

def run():
    audit=load(HERE/'INDEPENDENT_AUDIT.json');assert audit['mismatch_N']==audit['future_causal_leakage_N']==0
    reuse=load(HERE/'V3_TRACE_REUSE_RECEIPT.json');freeze=load(HERE/'CONTRACT_FREEZE_RECEIPT.json')
    for n,d in {**freeze['decision_code_hashes'],**freeze['evaluation_and_selection_code_hashes']}.items():assert sha(HERE/n)==d,n
    paths=sorted((PRIVATE/'DECISION_TRACE').glob('*.gz'))+[PRIVATE/n for n in ['DECISION_TRACE_RECEIPTS.json','REPLAY_ROWS.jsonl.gz','ECONOMICS_ROWS.jsonl.gz','PAIRED_ROWS.jsonl.gz','EXIT_D_ROWS.jsonl.gz','RUN_ONCE.json']]
    assert len(paths)==1606
    components={str(p.relative_to(PRIVATE)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in paths}
    name='Ark_State9_STRUCTURAL_EXIT_V4_RECOVERY_FAILURE_EVIDENCE_20261003_PRIVATE.zip';target=WORKSPACE/name
    manifest={'saved_at_jst':now(),'actual_basis_head':'d423f77bb67a586f1dd2a02858adfabad5af787c','status':'V4_NOT_BETTER_KEEP_V3','Entry_N':1600,'EXIT_D_N':127,'components':components,'contract_sha256':freeze['contract_sha256'],'decision_code_hashes':freeze['decision_code_hashes'],'evaluation_and_selection_code_hashes':freeze['evaluation_and_selection_code_hashes'],'dependencies':{'original_full_trace_zip':'Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip','original_full_trace_zip_sha256':reuse['original_full_trace_archive_sha256'],'V3_saved_outcome_zip':'Ark_State9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_EVIDENCE_20261003_PRIVATE.zip','V3_saved_outcome_zip_sha256':reuse['V3_archive_sha256'],'V3_actual_HEAD':reuse['actual_v3_HEAD']},'code_repository':'Iam-2squared/ark-terminal','code_branch':'state9-structural-exit-v4-recovery-failure-20261003','code_path':'research/state9-structural-exit-v4-recovery-failure-20261003/','primary_V4_replay_invocation_N':1,'V3_replay':0,'State9_Path_reconstruction':0,'original_full_trace_duplicated':False,'V3_saved_rows_duplicated':False,'audit_mismatch_N':0,'future_causal_leakage_N':0,'budget':BUDGET,'safety':SAFETY}
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in paths:z.write(p,str(p.relative_to(PRIVATE)))
        z.writestr('MANIFEST.json',json.dumps(manifest,sort_keys=True,indent=2)+'\n')
        z.writestr('README.txt','V4 private position metadata and outcomes only. Full State9/Path bytes and saved V3 outcomes remain exact immutable dependencies listed in MANIFEST.json. No engine reconstruction or V3 Replay. Public code/tables/report are in the GitHub code_path. Selection: V4_NOT_BETTER_KEEP_V3; no formal EXIT adoption Freeze/Reentry/Capital.\n')
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for n,item in components.items():assert hashlib.sha256(z.read(n)).hexdigest()==item['sha256']
    receipt={'saved_at_jst':now(),'basis_head':manifest['actual_basis_head'],'filename':name,'bytes':target.stat().st_size,'sha256':sha(target),'private_component_N':1606,'Entry_N':1600,'EXIT_D_N':127,'zip_crc_all_pass':True,'component_sha256_all_pass':True,'original_full_trace_duplicated_or_reconstructed':False,'V3_replay':0,'public_code_reports_duplicated':False,'safety':SAFETY}
    save(HERE/'PRIVATE_EVIDENCE_PACKAGE_RECEIPT.json',receipt);print(json.dumps(receipt))

if __name__=='__main__':run()
