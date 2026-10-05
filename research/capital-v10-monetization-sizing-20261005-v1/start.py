"""Actual parent receipt + verified private hierarchy; no diagnostic outcomes."""
from control import *
import subprocess,zipfile
def gitbytes(path):
    # Base index is the actual terminal V9 tree. Verify local bytes against its
    # Git blob ID without triggering a promisor network download per file.
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()==V9_SHA
    data=(ROOT/path).read_bytes()
    line=subprocess.check_output(['git','ls-files','-s','--',path],cwd=ROOT).decode().strip()
    assert line and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==line.split()[1]
    return data
def parent():
    c=read(PARENT/'CLOSURE.json');receipt=read(WORK/'v9_actual_GET.json')
    assert receipt['commit']['sha']==V9_SHA
    assert c['CURRENT_STATE']=='CAPITAL_V9_V14_CLOSURE_FIXED_STOP' and c['status']=='V9_QUALITY_PRESERVED_CAPITAL_FAIL'
    assert c['diagnosticArm']=='I2' and c['NEXT_BOTTLENECK']=='CAPITAL_MONETIZATION_OR_SIZING' and c['fixed_stop']
    assert c['selectedCapitalCandidate'] is None and c['Main_parent_SHA']==MAIN_SHA and c['Quality_parent_SHA']==QUALITY_SHA
    required=['CLOSURE.json','REPORT_FINAL-ja.md','NEXT_WORK_HANDOFF.json','INTEGRATION_DESIGN_PRECOMMIT.json',I2+'_RESULT.json','MAIN_REPLAY_RESULT.json','PRESERVATION_RESULT.json','CAPITAL_ROLLING20_RESULT.json','POLICY_DELTA_RESULT.json','INDUCED_OCCUPANCY_RESULT.json','INDEPENDENT_AUDIT.json','FROZEN_CODE_AND_TABLE_AUTHORITY.json','PRIVATE_PACK_MANIFEST.json']
    hashes={}
    for d,nn in [(PARENT,required),(V5,['REPORT_FINAL-ja.md','SLOT_QUALITY_AND_RESERVATION.json','MAIN_REPLAY_RESULT.json','PAIRED_DAILY.csv','PAIRED_ROLLING20.csv'])]:
        for n in nn:
            path=str((d/n).relative_to(ROOT));data=gitbytes(path);assert data==(ROOT/path).read_bytes();hashes[path]=sha(ROOT/path)
    frozen={str(p.relative_to(ROOT)):sha(p) for name in ['capital-v5-max3-slot-intelligence-20261004-v1','capital-v7-rank-native-max3-20261005-v1','capital-v8r1-cash-constrained-online-max3-20261005-v1','capital-v9-quality-aware-max3-integration-20261005-v1'] for p in (ROOT/'research'/name).glob('*.py')}
    assert sha(ROOT/'research/capital-v7-rank-native-max3-20261005-v1/runtime.py')=='14358d7e85190e41cfe90e488b9e6e84e0f7acd8ace96952da542c81fd16353b'
    save(OUT/'V9_PARENT_AUTHORITY_FREEZE.json',{'exact_jst':now(),'v9_HEAD':V9_SHA,'v9_tree':receipt['commit']['commit']['tree']['sha'],'closure':c,'required_public_sha256':hashes,'frozen_parent_source_sha256':frozen,'branch_base':V9_SHA,'actual_GET_verified':True,'old_cycle_resume':False,'Safety':SAFETY})
    checkpoint('M0_START_LATEST_AND_V9_FREEZE',{'v9':'FIXED_STOP','branch_base':V9_SHA},'Verify private manifests, no diagnostic calculation')
def extract(pack,dst,manifest):
    assert not dst.exists();dst.mkdir(parents=True)
    with zipfile.ZipFile(pack) as z:
        for n in z.namelist():assert not Path(n).is_absolute() and '..' not in Path(n).parts
        z.extractall(dst)
    m=read(dst/manifest);ff=m['files'];ff=ff if isinstance(ff,list) else [dict(v,path=k) for k,v in ff.items()];checks=[]
    for r in ff:
        p=dst/r['path'];assert sha(p)==r['sha256'];assert p.stat().st_size==r.get('bytes',r.get('size',p.stat().st_size));checks.append({'path':str(p.relative_to(AUTH)),'sha256':sha(p)})
    return checks
def private():
    pack=ROOT.parent/'project_sources/22-Ark_Capital_v9_Quality_Aware_MAX3_Integration_20261005_PRIVATE-1-.zip'
    pub=read(PARENT/'PRIVATE_PACK_MANIFEST.json');assert sha(pack)==pub['sha256']=='16356ece8b6b65e2490c5c48400c003d747ad438ab7d93d96c9ffbdab7d5ef1b'
    checks=extract(pack,AUTH/'v9','MANIFEST.json');assert read(AUTH/'v9/MANIFEST.json')==pub['manifest'] and sha(AUTH/'v9/MANIFEST.json')==pub['manifest_sha256']
    mp=AUTH/'v9/authority/Ark_Capital_v8R1_Cash_Constrained_Online_MAX3_20261005_PRIVATE.zip';qp=AUTH/'v9/authority/Ark_Capital_Quality_v1R1_Recovery_20261005_PRIVATE_STRONG.zip'
    checks+=extract(mp,MAIN,'MANIFEST.json');checks+=extract(qp,RECOVERY,'DELIVERY_MANIFEST.json')
    checks+=extract(RECOVERY/'authority/Ark_Capital_Quality_v1_20261005_PRIVATE_CONTRACT_FAIL.zip',QUALITY,'DELIVERY_MANIFEST.json')
    save(OUT/'INPUT_PRIVATE_AUTHORITY_AUDIT.json',{'exact_jst':now(),'status':'PASS','mismatch_N':0,'attached_v9_pack':{'path':str(pack),'sha256':sha(pack)},'manifest_member_N':len(checks),'members':checks,'read_only_parents':True,'Safety':SAFETY})
    checkpoint('M1_INPUT_PRIVATE_AUTHORITY_AUDIT',{'manifest_member_N':len(checks),'mismatch_N':0},'Precommit sizing policies before any new outcome diagnostic')
if __name__=='__main__':
    import sys
    {'parent':parent,'private':private}[sys.argv[1]]()
