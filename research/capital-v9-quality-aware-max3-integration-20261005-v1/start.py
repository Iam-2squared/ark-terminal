"""Parent identities and all private-manifest members; no inference or replay."""
from control import *
import subprocess,sys
def gitbytes(ref,path):return subprocess.check_output(['git','show',f'{ref}:{path}'],cwd=ROOT)
def parent():
    m=read(PARENT/'CLOSURE.json');q=json.loads(gitbytes(QUALITY_SHA,'docs/evidence/capital-quality-anti-weak-medium-v1r1-recovery-20261005/CLOSURE.json'))
    assert m['CURRENT_STATE']=='CAPITAL_V8R1_R15_CLOSURE_FIXED_STOP' and m['status']=='V8R1_NO_GO' and m['fixed_stop']
    assert q['qualityStatus']=='ANTI_WEAK_MEDIUM_STRONG' and q['recoveryStatus']=='QUALITY_RECOVERY_PASS' and q['selectedAuxiliaryHeads']==['MOVE_U2','MOVE_U3'] and q['terminal_checkpoint']=='R12_CLOSURE_FIXED_STOP'
    assert read(AUTH/'main_closure_actual_GET.json')==m and read(AUTH/'quality_closure_actual_GET.json')==q
    mainfiles=['CLOSURE.json','REPORT_FINAL-ja.md','NEXT_WORK_HANDOFF.json','B1_B2_SEMANTIC_FREEZE.json','B2_TENURE_LOOKUP_TABLE.json','B2_CAPACITY_PRESSURE_TABLE.json','TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1_RESULT.json','PRESERVATION_RESULT.json','CAPITAL_ROLLING20_RESULT.json','PPRANK_CASH_DIAGNOSTIC_RESULT.json','INDEPENDENT_AUDIT.json','PRIVATE_PACK_MANIFEST.json','SAVED_REFERENCE_FREEZE.json']
    qualityfiles=['CLOSURE.json','QUALITY_DECISION.json','REPORT_FINAL-ja.md','BIG_WINNER_PRESERVATION.json','P_P_CONDITIONAL_INCREMENTAL.json','INDEPENDENT_PERFORMANCE_AUDIT.json','INTEGRITY_CANARY_AUDIT.json','BASELINE_RECOVERY_ROOT.json','COMPLETED_FITS_REUSE_FREEZE.json','RECOVERY_PRIVATE_ARTIFACT_ROOT.json','MODEL_ARTIFACT_AUDIT.json']
    authorities={}
    for name in mainfiles:
        p=str((PARENT/name).relative_to(ROOT));data=gitbytes(MAIN_SHA,p);assert data==(ROOT/p).read_bytes();authorities[p]={'commit':MAIN_SHA,'sha256':hashlib.sha256(data).hexdigest()}
    qp='docs/evidence/capital-quality-anti-weak-medium-v1r1-recovery-20261005'
    for name in qualityfiles:
        p=f'{qp}/{name}';data=gitbytes(QUALITY_SHA,p);authorities[p]={'commit':QUALITY_SHA,'sha256':hashlib.sha256(data).hexdigest()}
        dst=AUTH/'quality_public'/name;dst.parent.mkdir(exist_ok=True)
        with dst.open('xb') as f:f.write(data)
    for p in ['docs/evidence/capital-rank-bigwinner-vnext-20261005-v1/SELECTED_RANK_CONTRACT.json','docs/evidence/capital-rank-bigwinner-vnext-20261005-v1/CLOSURE.json',str(SPLIT.relative_to(ROOT)),str((V7/'RANK_NATIVE_BAND_MAP.json').relative_to(ROOT)),str((V7/'ORACLE_RESULT.json').relative_to(ROOT)),str((V5/'CLOSURE.json').relative_to(ROOT)),str((V5/'REPORT_RESULT_FACTS.json').relative_to(ROOT))]:
        data=gitbytes(MAIN_SHA,p);authorities[p]={'commit':MAIN_SHA,'sha256':hashlib.sha256(data).hexdigest()}
    o={'exact_jst':now(),'Main':{'branch':'capital-v8r1-cashfix-20261005','HEAD':MAIN_SHA,'tree':'f814bf0e60e75b8187f4dfb52f6791cdb565de52','closure':m['CURRENT_STATE'],'status':m['status']},'Quality':{'branch':'capital-quality-v1r1-recovery-20261005','HEAD':QUALITY_SHA,'tree':'3215e0d5f4e9299d3fc86900d3cc4c221d379fda','closure':q['terminal_checkpoint'],'status':q['qualityStatus'],'recoveryStatus':q['recoveryStatus'],'heads':q['selectedAuxiliaryHeads']},'branch_base':MAIN_SHA,'Quality_history_merge':False,'required_public_authorities':authorities,'canonical_resolution':{'Quality INDEPENDENT_AUDIT':'INDEPENDENT_PERFORMANCE_AUDIT + INTEGRITY_CANARY_AUDIT','v7 ORACLE_ALL/ADMISSION_U5/U10':'ORACLE_RESULT.json.solves.ALL_U5/ALL_U10/ADMISSION_U5/ADMISSION_U10'},'Safety':SAFETY}
    save(OUT/'PARENT_AUTHORITY_FREEZE.json',o)
    checkpoint('V0_START_LATEST_AND_PARENT_FREEZE',{'Main':'FIXED_STOP','Quality':'FIXED_STOP','branch_base':MAIN_SHA,'Quality_history_merge':0},'Authenticate all private manifests')
def private():
    checks=[]
    for folder,name in [(MAIN,'MANIFEST.json'),(RECOVERY,'DELIVERY_MANIFEST.json'),(QUALITY,'DELIVERY_MANIFEST.json')]:
        m=read(folder/name);ff=m['files'];ff=ff if isinstance(ff,list) else [dict(v,path=k) for k,v in ff.items()]
        for z in ff:
            p=folder/z['path'];assert sha(p)==z['sha256'];assert p.stat().st_size==z.get('bytes',z.get('size',p.stat().st_size));checks.append({'authority':folder.name,'path':z['path'],'sha256':sha(p)})
    expected={'*v8R1*.zip':'0faca69c7c4260a36402a366b89a02fa3daecdd1049f87d4626f5271c6375293','*Quality*v1R1*.zip':'e3d3496072075a7929bdaca726e73f020cbee83aec7954fc153934ba5b9f0c6d'}
    packs=[]
    for pat,h in expected.items():
        p=next(AUTH.glob(pat));assert sha(p)==h;packs.append({'filename':p.name,'sha256':h})
    assert sha(RECOVERY/'authority/Ark_Capital_Quality_v1_20261005_PRIVATE_CONTRACT_FAIL.zip')=='b91b15dab231c39170f1c2b650bb0220b855efd0474ea049fb6a6c3910d69de9'
    assert sha(RECOVERY/'private/QUALITY_COMMON_EVAL_ROWS_V1R1.jsonl.gz')=='d6d5cb8e22f1affd08e58ad2628f1fa176f85850fba80a0f6a72190d4e132768'
    pairs=[('inputs/movement/RUNTIME_CAUSAL.jsonl.gz','inputs/RUNTIME_CAUSAL.jsonl.gz'),('inputs/movement/MOVE_P5_SCORE_STREAM.jsonl.gz','inputs/MOVE_P5_SCORE_STREAM.jsonl.gz'),('private/COMMON_EVAL_MASK.jsonl.gz','inputs/COMMON_EVAL_MASK.jsonl.gz'),('inputs/entry/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz','inputs/FROZEN_ENTRY.jsonl.gz'),('inputs/evaluation/TEACHERS_EVALUATION.jsonl.gz','inputs/TEACHERS_EVALUATION.jsonl.gz')]
    cross=[]
    for a,b in pairs:assert sha(MAIN/a)==sha(QUALITY/b);cross.append({'Main_path':a,'Quality_path':b,'sha256':sha(MAIN/a)})
    for b in range(1,9):
        a=MAIN/f'inputs/movement/models/MOVE_P_BLOCK_{b:02}.json';z=QUALITY/f'inputs/models/MOVE_P_BLOCK_{b:02}.json';assert sha(a)==sha(z)
    public=read(PARENT/'PRIVATE_PACK_MANIFEST.json');assert public['manifest']==read(MAIN/'MANIFEST.json') and public['manifest_sha256']==sha(MAIN/'MANIFEST.json') and public['sha256']==expected['*v8R1*.zip']
    save(OUT/'PRIVATE_PACK_CROSS_AUTHORITY_AUDIT.json',{'exact_jst':now(),'status':'PASS','mismatch_N':0,'private_packs':packs,'manifest_member_N':len(checks),'members':checks,'shared_byte_identity':cross,'pP_model_byte_identity_N':8,'nested_pack_sha256':sha(RECOVERY/'authority/Ark_Capital_Quality_v1_20261005_PRIVATE_CONTRACT_FAIL.zip'),'quality_common_sha256':sha(RECOVERY/'private/QUALITY_COMMON_EVAL_ROWS_V1R1.jsonl.gz'),'Main_public_manifest_exact':True,'Safety':SAFETY})
    checkpoint('V1_MAIN_QUALITY_PRIVATE_AUTHORITY_AUDIT',{'manifest_members':len(checks),'mismatch_N':0,'status':'PASS'},'Precommit exactly two policies and fixed gates')
if __name__=='__main__':{'parent':parent,'private':private}[sys.argv[1]]()
