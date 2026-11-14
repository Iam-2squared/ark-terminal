"""Save immutable evidence snapshots; no model/feature computation."""
import argparse,io,json,tarfile
from common import ROOT,PUB,PRIV,clock,dump,pin

def build(kind):
    assert kind in ['PREDICTION','FINAL']
    files={}
    if kind=='PREDICTION':
        for p in (PRIV/'C11').rglob('*'):
            if p.is_file():files['c11/private/C11/'+p.relative_to(PRIV/'C11').as_posix()]=p
        for n in ['C11_PREDICTION_SEAL.json','C11_PRECOMMIT.json','C11_PRECOMMIT_READBACK.json','C11_FEATURE_SEAL.json','C11_CAUSAL_QA.json','C11_IMPLEMENTATION_LOCK.json','C11_QA_READBACK.json','BUDGET_LEDGER.json']:
            files['c11/public/'+n]=PUB/n
    else:
        for p in ROOT.glob('*.py'):files['c11/'+p.name]=p
        for p in PUB.rglob('*'):
            if p.is_file() and not p.name.endswith('_EVIDENCE_MANIFEST.json') and not p.name.startswith('READBACK_RECEIPT'):
                files['c11/public/'+p.relative_to(PUB).as_posix()]=p
        for p in PRIV.rglob('*'):
            if p.is_file() and not p.name.startswith(('PREDICTION_EVIDENCE','FINAL_EVIDENCE','BUDGET_WRITER')):
                files['c11/private/'+p.relative_to(PRIV).as_posix()]=p
        for n in ['TODAY_PREFIX_CACHE.jsonl.gz','DERIVED_CACHE_SCOPE_PRECOMMIT.json','DERIVED_CACHE_MANIFEST.json']:
            files['c11/inputs/'+n]=ROOT/'inputs'/n
    pins={n:pin(p) for n,p in sorted(files.items())}
    body=(json.dumps({'files':pins,'kind':kind,'parent_C09_C10_unchanged':True},ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    archive=PRIV/(kind+'_EVIDENCE.tar.xz')
    with tarfile.open(archive,'w:xz',preset=6) as tf:
        for n,b in [('EVIDENCE_MANIFEST.json',body)]+[(n,p.read_bytes()) for n,p in sorted(files.items())]:
            info=tarfile.TarInfo(n);info.size=len(b);info.mtime=0;info.mode=0o644;tf.addfile(info,io.BytesIO(b))
    data=archive.read_bytes();parts=[]
    for k,start in enumerate(range(0,len(data),600000),1):
        p=archive.with_name(archive.name+f'.part{k:02d}');p.write_bytes(data[start:start+600000]);parts.append({'path':p.name,**pin(p)})
    out={'kind':kind,'clock':clock(),'archive':{'name':archive.name,**pin(archive)},'ordered_parts':parts,'private_member_N':len(files)+1,'private_members':pins,'public_artifacts':{p.name:pin(p) for p in PUB.iterdir() if p.is_file() and p.name!=(kind+'_EVIDENCE_MANIFEST.json') and not p.name.startswith('READBACK_RECEIPT')},'new_fit':0,'new_threshold':0,'new_feature_build':0,'private_row_body_public':False}
    dump(PUB/(kind+'_EVIDENCE_MANIFEST.json'),out)
    print({'kind':kind,'bytes':len(data),'parts':len(parts),'members':len(files)+1,'sha256':pin(archive)['sha256']},flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('kind',choices=['PREDICTION','FINAL']);build(ap.parse_args().kind)
