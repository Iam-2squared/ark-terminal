"""Finite delivery: new private outputs plus the exact immutable v11 parent ZIP."""
from control import *
import zipfile
def main():
    assert read(OUT/'INDEPENDENT_AUDIT.json')['mismatch_N']==0
    assert (OUT/'WINNER_AND_NEXT_BOTTLENECK.json').exists()
    target=ROOT.parent/'Ark_Capital_v11R1_Numeric_Cert_Recovery_20261005_PRIVATE.zip';assert not target.exists(),'DELIVERY_ALREADY_EXISTS_NO_REBUILD'
    private=sorted(p for p in PRIVATE.rglob('*') if p.is_file());files={str(p.relative_to(WORK)):sha(p) for p in private};authority='authority/'+PACK.name;files[authority]=sha(PACK);assert files[authority]==PACK_SHA
    manifest={'schema':'CAPITAL_V11R1_NUMERIC_CERT_PRIVATE_DELIVERY_V1','exact_jst':now(),'basis':read(WORK/'latest_basis.json'),'v11_parent_SHA':PARENT_SHA,'files':files,'parent_private':{'path':authority,'sha256':PACK_SHA,'read_only':True},'public_authority_references':{str(p.relative_to(ROOT)):sha(p) for p in OUT.rglob('*') if p.is_file()},'oldV11Status':'V11_CONTRACT_FAIL','oldS9':'FAIL','newS9R':'PASS','newFits':0,'reusedMRETFits':8,'CapitalReplays':2,'M1_invocations':1,'M2_invocations':1,'M1_scope':'28 complete sessions + unresolved29th session; no rolling20/Final38','M2_scope':'full38 sessions','no_public_git_content_duplicated':True,'Safety':SAFETY}
    data=(json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode();manifest_sha=hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in private:z.write(p,str(p.relative_to(WORK)))
        z.write(PACK,authority,compress_type=zipfile.ZIP_STORED);z.writestr('MANIFEST.json',data)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        saved=json.loads(z.read('MANIFEST.json'));assert saved==manifest
        for name,h in files.items():assert hashlib.sha256(z.read(name)).hexdigest()==h
    o={'exact_jst':now(),'schema':manifest['schema'],'filename':target.name,'file_sha256':sha(target),'bytes':target.stat().st_size,'content_manifest_sha256':manifest_sha,'private_member_N':len(files),'public_reference_N':len(manifest['public_authority_references']),'all_member_hashes_verified':True,'nested_v11_private_sha256':PACK_SHA,'newFits':0,'CapitalReplays':2,'M1_complete_invocations':1,'M2_complete_invocations':1,'M1_capital_measurement':'BLOCKED','M2_capital_measurement':'38_COMPLETE','Safety':SAFETY}
    save(OUT/'PRIVATE_PACK_MANIFEST.json',o);print(json.dumps(o),flush=True)
if __name__=='__main__':main()
