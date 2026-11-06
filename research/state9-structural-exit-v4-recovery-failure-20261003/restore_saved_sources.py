"""Restore exact saved ZIP components only, never rebuild State9/Path semantics."""
import argparse,hashlib,json,zipfile
from pathlib import Path

PINS={'v2':'31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89','v3':'16cb53e6c986963f5a103e56c9f3fafad142548d7d9fd3286bb9e8c92e5a04b3','v4':'ef58f731c76c2e9966997b86e1903faceb298ade472adfdf9849654f3cd950f4'}
def restore(path,target,kind):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==PINS[kind],'BLOCKED_V4_LINEAGE_MISMATCH'
    with zipfile.ZipFile(path) as z:
        names=z.namelist();name=next(n for n in names if n.endswith('MANIFEST.json'))
        manifest=json.loads(z.read(name))
        for n,item in manifest['components'].items():
            assert not Path(n).is_absolute() and '..' not in Path(n).parts
            src=n if n in names else name.removesuffix('MANIFEST.json')+n
            data=z.read(src);assert hashlib.sha256(data).hexdigest()==item['sha256']
            dest=target/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        if kind=='v2':(target/'MANIFEST.json').write_bytes(z.read(name))
    return len(manifest['components'])
def main():
    p=argparse.ArgumentParser();p.add_argument('--v2-zip',type=Path,required=True);p.add_argument('--v3-zip',type=Path,required=True);p.add_argument('--v4-zip',type=Path);p.add_argument('--workspace',type=Path,required=True);a=p.parse_args()
    report={'V2_exact_components_restored':restore(a.v2_zip,a.workspace/'inputs_v3/v2_data','v2'),'V3_exact_components_restored':restore(a.v3_zip,a.workspace/'private_structural_v3','v3'),'State9_Path_reconstruction':0,'V3_replay':0}
    if a.v4_zip:report['V4_exact_saved_results_restored']=restore(a.v4_zip,a.workspace/'private_structural_v4','v4')
    print(json.dumps(report))
if __name__=='__main__':main()
