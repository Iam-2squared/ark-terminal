"""Exact saved v2 bytes only. Never rebuild State9, Path or v2 outcomes."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
from settings import HERE,INPUT,V2,PUBLIC_V2,now,sha,save

PACKAGE_SHA='31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89'
PUBLIC_NAMES=['FINAL_PROVENANCE_MANIFEST.json','IDENTITY_RECEIPT.json','PRIVATE_EVIDENCE_PACKAGE_RECEIPT.json','FINAL_STATUS.json','lifecycle.py','replay.py','settings.py','CONTRACT.md','INDEPENDENT_AUDIT.json','REPLAY_RECEIPT.json','EVALUATION_RECEIPT.json','ALL_ENTRY_ECONOMICS.json','WINNER_EXCLUSIVE.json','WINNER_GE5_DETAILED.json','FROZEN_SOURCE/RC2_CONTRACT.txt','FROZEN_SOURCE/profile.json','FROZEN_SOURCE/M0.md','FROZEN_SOURCE/source_snapshot.json','FROZEN_SOURCE/PATH_FROZEN.py','FROZEN_SOURCE/STATE_PATH_CONTRACT_V1.md']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package',type=Path)
    parser.add_argument('--v2-public',type=Path,default=HERE.parent/'state9-structural-exit-v2-20261003')
    args=parser.parse_args()
    if not args.package.is_file() or sha(args.package)!=PACKAGE_SHA:
        raise SystemExit('BLOCKED_V3_FROZEN_TRACE_NOT_AVAILABLE')
    for name in PUBLIC_NAMES:
        original=args.v2_public/name;dest=PUBLIC_V2/name
        if not original.is_file():raise SystemExit('BLOCKED_V3_LINEAGE_MISMATCH: missing frozen public file '+name)
        dest.parent.mkdir(parents=True,exist_ok=True)
        if original.resolve()!=dest.resolve():shutil.copyfile(original,dest)
    manifest=json.loads((PUBLIC_V2/'FINAL_PROVENANCE_MANIFEST.json').read_text())['files']
    for name in PUBLIC_NAMES:
        if name!='FINAL_PROVENANCE_MANIFEST.json' and sha(PUBLIC_V2/name)!=manifest[name]['sha256']:
            raise SystemExit('BLOCKED_V3_LINEAGE_MISMATCH: '+name)
    with zipfile.ZipFile(args.package) as archive:
        frozen_manifest=json.loads(archive.read('MANIFEST.json'));components=frozen_manifest['components']
        for name,item in components.items():
            original=archive.read(name)
            if hashlib.sha256(original).hexdigest()!=item['sha256'] or len(original)!=item['bytes']:
                raise SystemExit('BLOCKED_V3_FROZEN_TRACE_NOT_AVAILABLE: '+name)
            dest=V2/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(original)
        (V2/'MANIFEST.json').write_bytes(archive.read('MANIFEST.json'))
    assert len(list((V2/'FULL_TRACE').glob('*.gz')))==1600
    receipt={'saved_at_jst':now(),'actual_v2_HEAD':'823fe3a7203e58fbc20fa73acab1d77e1da62c8e','status':'V2_FROZEN_TRACE_EXACT_REUSE_AVAILABLE','package_sha256':PACKAGE_SHA,'component_hash_checks_N':len(components),'component_mismatch_N':0,'trace_files_N':1600,'trace_slots_N':523200,'entry_source_sha256':sha(V2/'FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'),'State9_full_reconstruction':0,'Path_full_reconstruction':0,'v2_replay':0,'provider':0,'new_market_data':0}
    save(HERE/'V2_TRACE_REUSE_RECEIPT.json',receipt)
    print(json.dumps(receipt))

if __name__=='__main__':main()
