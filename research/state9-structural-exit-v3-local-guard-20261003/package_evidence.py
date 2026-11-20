"""New private v3 metadata/outcomes only. Frozen v2 trace remains a hash dependency."""
import hashlib,json,zipfile
from settings import HERE,WORKSPACE,PRIVATE,SAFETY,BUDGET,now,sha,load,save

NAME='Ark_State9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_EVIDENCE_20261003_PRIVATE.zip'

def main():
    audit=load(HERE/'INDEPENDENT_AUDIT.json');assert audit['mismatch_N']==audit['future_causal_leakage_N']==0
    components=[]
    receipts=load(PRIVATE/'DECISION_TRACE_RECEIPTS.json')
    for r in receipts:
        f=PRIVATE/'DECISION_TRACE'/(r['watch_key'].replace('|','_')+'.jsonl.gz')
        assert sha(f)==r['sha256']
        components.append(('DECISION_TRACE/'+f.name,f))
    assert len(components)==1600
    for name in ['REPLAY_ROWS.jsonl.gz','ECONOMICS_ROWS.jsonl.gz','PAIRED_ROWS.jsonl.gz','EXIT_C_ROWS.jsonl.gz','DECISION_TRACE_RECEIPTS.json']:
        components.append((name,PRIVATE/name))
    manifest={'saved_at_jst':now(),'document_id':'WORK_STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_FASTTRACK_20261003','Entry_N':1600,'decision_trace_files_N':1600,'position_decision_rows_N':load(HERE/'REPLAY_RECEIPT.json')['decision_N'],'EXIT_C_N':43,'Winner_GE5_EXIT_C_N':17,'v2_frozen_trace_dependency':{'filename':'Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip','sha256':'31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89','exact_trace_files_N':1600,'full_trace_slots_N':523200,'reconstructed':False,'duplicate_copy_in_this_package':False},'code_repository':'Iam-2squared/ark-terminal','code_branch':'state9-structural-exit-v3-local-guard-20261003','code_path':'research/state9-structural-exit-v3-local-guard-20261003/','actual_basis_head':'06ed4b6ae371aced35c4dbf2f3591d092a4698a1','final_code_checkpoint':'V3_FINAL_AUDIT_AND_EVIDENCE; actual result HEAD returned after commit, not predicted','contract_sha256':load(HERE/'CONTRACT_FREEZE_RECEIPT.json')['contract_sha256'],'audit_mismatch_N':0,'future_causal_leakage_N':0,'historical_actual_known_at':'UNKNOWN; inherited bar_end availability assumption','public_code_reports_duplicated':False,'budget':BUDGET,'safety':SAFETY,'components':{name:{'sha256':sha(f),'bytes':f.stat().st_size} for name,f in components}}
    target=WORKSPACE/NAME
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
        for name,f in components:archive.write(f,name)
        archive.writestr('MANIFEST.json',json.dumps(manifest,sort_keys=True,indent=2)+'\n')
        archive.writestr('README.txt','STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD private evidence\n\n1600 v3 decision metadata streams; all replay/economics/paired rows and43 EXIT-C paired rows. >=5 C subgroup has17 positions and per-entry later observed High/time.\nOriginal State9/Path trace, raw source and Frozen Entry are exact dependencies in the already saved v2 private ZIP, SHA31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89. They are not reconstructed or redundantly packaged. Each v3 trace receipt includes the original State9 trace SHA.\nCode, 17-answer report, paired tables and separate-logic audit are at the named Git branch FINAL checkpoint. No v2 Replay, State9/Path reconstruction, model/teacher/score/search/provider/new market data.\nHistorical arrival time UNKNOWN; bar_end availability assumed. Observed High is partial where original source is incomplete. Missing fills/highs remain null or UNRESOLVED, never0.\nSTOP at evidence ready; no formal EXIT adoption, Re-entry, Capital or orders.\n')
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name,item in manifest['components'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==item['sha256']
    receipt={'saved_at_jst':now(),'basis_head':manifest['actual_basis_head'],'filename':NAME,'bytes':target.stat().st_size,'sha256':sha(target),'component_sha256_all_pass':True,'zip_crc_all_pass':True,'private_data_components_N':len(components),'Entry_N':1600,'EXIT_C_N':43,'public_code_reports_duplicated':False,'original_v2_trace_duplicated_or_reconstructed':False,'safety':SAFETY}
    save(HERE/'PRIVATE_EVIDENCE_PACKAGE_RECEIPT.json',receipt);print(json.dumps(receipt))

if __name__=='__main__':main()
