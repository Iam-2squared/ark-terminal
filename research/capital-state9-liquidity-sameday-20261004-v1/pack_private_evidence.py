"""Create a new private evidence package; never publish rows into Git.

Code and public reports stay in their external Git repository. The package
contains non-repository private data plus a receipt referring to the actual
already-created public closure commit, not a guessed future SHA.
"""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import hashlib,json,sys,zipfile

def main():
    root=Path(sys.argv[1]);commit=sys.argv[2]
    if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):raise ValueError('ACTUAL_COMMIT_REQUIRED')
    folder=root/'deliverables/capital-svnext-20261004-v1';folder.mkdir(parents=True,exist_ok=True)
    target=folder/'Ark_Capital_vNext_Closure_20261004_PRIVATE.zip'
    if target.exists():raise FileExistsError('NEW_CYCLE_PACKAGE_ALREADY_EXISTS; do not overwrite')
    included=[]
    for p in sorted((root/'svnext_private').rglob('*')):
        if p.is_file():included.append(p)
    for directory in ['eod_private/primary','eod_private/independent','f1520_private/primary-v1','f1520_private/independent']:
        included.extend(p for p in sorted((root/directory).glob('*')) if p.is_file())
    components=[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in included]
    manifest={'jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'private':True,'status':'CAPITAL_VNEXT_NO_FREEZE_CANDIDATE',
        'repo':'Iam-2squared/ark-terminal','branch':'capital-state9-vnext-20261004','actual_public_C10_result_commit':commit,
        'public_report':'https://github.com/Iam-2squared/ark-terminal/blob/'+commit+'/docs/evidence/phase57-capital-state9-liquidity-sameday-20261004-v1/REPORT-ja.md',
        'C2_contract_status':'CAPITAL_C2_CONTRACT_PASS','State9_gate':'NOT_DEMONSTRATED','full_Portfolio':'MEASUREMENT_BLOCKED',
        'private_decisions_N':9600,'known_prefix_curves_N':54,'full_curves_created':False,'fits_consumed':42,'rank_fits':0,'baseline_replays':6,
        'components':components,'component_count':len(components),
        'large_immutable_dependencies_not_duplicated':[
            {'name':'Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip','sha256':'c0024055e9afa19089318c0f2a281e3fe15d48e10945b752be48e9239235ac15','bytes':524938461,'role':'Original frozen shared numeric archive. Current indexed NPZ included for diagnostic/audit rerun.'},
            {'name':'Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip','sha256':'31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89','role':'Immutable original full trace inside prior handoff attachment. Derived causal join rows/hash included.'}],
        'public_repo_row_upload':False,'source_price_imputation':0,'protected_opened':0,'provider_requests':0,'orders':0,'main_merges':0,'force_pushes':0,
        'safety':{k:False for k in ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady']}}
    readme='''# Private Capital vNext evidence / 20261004 new cycle

This package is PRIVATE. Do not upload raw rows or this ZIP to the public repo.
Status: CAPITAL_VNEXT_NO_FREEZE_CANDIDATE / STOP; C2 contract PASS.
All six baseline arms stop at the first necessary exact MTM source gap.
Full Final Equity/DD/utilization/rolling metrics are null, not zero.
Known prefix curves (54 frames) are not a complete Portfolio curve.
State9 current and Path finite promotion gates failed; no State-aware ranker.

The verified public closure commit/report and exact byte hashes are in
MANIFEST_PRIVATE.json. Code/public reports/charts are Git-backed, not duplicated
here. Keep parent Frozen source packages unchanged. This is not a live/paper
order authorization, a broker fill receipt, or Fresh/OOS performance evidence.

To reproduce the finite diagnostic and independent source/prefix audit:
1. Check out the actual public closure commit referenced in the manifest.
2. Extract this ZIP beside the ark-terminal source directory, preserving paths.
3. Use the research diagnostic.py / independent_audit.py paths in that commit.
4. The original large frozen feature and State trace archives are required only
   for rebuilding the joined input artifacts from their own immutable lineage;
   current 1600-row NPZ/State9 rows are included for model/audit replay.
5. Verify model hashes before loading pickle files. Only trusted package models
   should be loaded; pickle is not an untrusted portable data format.

Do not expand fits, retune thresholds/capacity, fill missing prices, zero blocked
PnL, or infer live known-at from a historical saved source.
'''
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in included:z.write(p,str(p.relative_to(root)))
        z.writestr('MANIFEST_PRIVATE.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        z.writestr('README_PRIVATE.md',readme)
    with zipfile.ZipFile(target) as z:
        for c in components:
            if hashlib.sha256(z.read(c['path'])).hexdigest()!=c['sha256']:raise ValueError('ARCHIVE_COMPONENT_HASH')
    receipt={'jst':manifest['jst'],'file':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'verified_components_N':len(components),'actual_public_closure_commit':commit,'library_save_pending':True}
    (folder/'PACKAGE_RECEIPT_LOCAL.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
