"""Existing saved v5 ledger authority only; no control replay."""
from control import *
import zipfile
def main():
    pack=AUTH/'downloads/Ark_Capital_v5_MAX3_Slot_Intelligence_20261004_PRIVATE.zip';dest=AUTH/'v5';assert not dest.exists();dest.mkdir()
    with zipfile.ZipFile(pack) as z:
        for n in z.namelist():assert not Path(n).is_absolute() and '..' not in Path(n).parts
        z.extractall(dest)
    m=read(dest/'MANIFEST_SHA256.json');checks=[]
    for path,r in m['files'].items():
        p=dest/path;assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes'];checks.append({'path':path,'sha256':sha(p)})
    candidates=list(dest.rglob('CAPITAL_MAX3_SLOT_RESERVE_V1_TRADES.jsonl.gz'));assert len(candidates)==1;private=candidates[0].parent
    pub=read(V5/'DETERMINISTIC_RERUN.json')
    for key,value in pub.items():
        if isinstance(value,dict) and 'TRADES' in value:
            for name,h in value.items():assert sha(private/f'CAPITAL_MAX3_SLOT_RESERVE_V1_{name}.jsonl.gz')==h
    result=read(private/'CAPITAL_MAX3_SLOT_RESERVE_V1_RESULT.json');assert result==read(V5/'MAIN_REPLAY_RESULT.json')
    save(WORK/'v5_saved_paths.json',{'private':str(private),'pack':str(pack)})
    save(OUT/'V5_PRIVATE_SAVED_LEDGER_AUTHORITY.json',{'exact_jst':now(),'status':'PASS','manifest_member_N':len(checks),'pack_sha256':sha(pack),'private_folder':str(private),'v5_public_result_exact':True,'public_deterministic_ledger_hashes_exact':True,'members':checks,'v5_replay':0,'Safety':SAFETY})
if __name__=='__main__':main()
