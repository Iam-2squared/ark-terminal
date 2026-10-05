"""Authenticate supplied archives, pinned tracked files and closed negative history."""
import io, zipfile, hashlib, subprocess
from control import *
def unpack(data,destination,lineage,receipts):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=z.namelist(); assert len(names)==len(set(names))
        for n in names:assert not n.startswith('/') and '..' not in Path(n).parts
        manifest_names=[n for n in names if n.rsplit('/',1)[-1] in ('MANIFEST.json','DELIVERY_MANIFEST.json')]
        for mn in manifest_names:
            d=json.loads(z.read(mn));fs=d.get('files',[])
            if isinstance(fs,dict):fs=[dict(v,path=k) for k,v in fs.items()]
            checked=0
            for f in fs:
                if not isinstance(f,dict) or 'sha256' not in f:continue
                n=f['path']; candidates=[n,str(Path(mn).parent/n)]
                n=next((p for p in candidates if p in names),None);assert n is not None,(lineage,f)
                raw=z.read(n);assert hashlib.sha256(raw).hexdigest()==f['sha256'],(lineage,n)
                size=f.get('bytes',f.get('size'));assert size is None or len(raw)==size
                checked+=1
            receipts.append({'archive':lineage,'manifest':mn,'manifest_sha256':hashlib.sha256(z.read(mn)).hexdigest(),'verified_file_N':checked,'schema':d.get('schema')})
        if destination:
            assert not destination.exists();z.extractall(destination)
        for n in names:
            if n.endswith('.zip') and n.startswith('authority/'):
                if 'v9_' in n:dest=AUTH/'v9'
                elif 'v8R1_' in n:dest=AUTH/'main'
                elif 'v1R1_' in n:dest=AUTH/'quality'
                elif 'Quality_v1_' in n:dest=AUTH/'quality_original'
                else:dest=None
                unpack(z.read(n),dest,lineage+'/'+n,receipts)
def main():
    assert not OUT.exists(),'EXISTING_EVIDENCE_NO_OVERWRITE'
    assert sha(PACK)==PACK_SHA,'V11_SOURCE_BLOCKED'
    c=read(PARENT/'CLOSURE.json');assert c['CURRENT_STATE']=='CAPITAL_V10_M15_CLOSURE_FIXED_STOP'
    assert c['status']=='V10_REALIZED_MONETIZATION_LIMIT' and c['NEXT_BOTTLENECK']=='REALIZED_MONETIZATION_SIGNAL'
    assert c['selectedCapitalCandidate'] is None and c['diagnosticArm']=='S1' and c['private_sha256']==PACK_SHA
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==PARENT_SHA
    protected={}
    for line in subprocess.check_output(['git','ls-files','-s','-z','docs','research'],cwd=ROOT,text=True).split('\0'):
        if not line:continue
        info,path=line.split('\t');blob=info.split()[1];p=ROOT/path
        raw=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,path
        protected[path]=hashlib.sha256(raw).hexdigest()
    save(WORK/'PROTECTED_TRACKED_HASHES.json',protected)
    receipts=[];unpack(PACK.read_bytes(),V10,'v10',receipts)
    save(OUT/'PARENT_AUTHORITY_FREEZE.json',{'exact_jst':now(),'v10_HEAD':PARENT_SHA,'tree':read(WORK/'latest_basis.json')['tree'],'v10_closure':c,'canonical_v10_close_time':read(PARENT/'FINAL_TERMINAL_RECEIPT_ONLY.json')['canonical_closure_exact_jst'],'quality_history_merge':False,'old_evidence_rewrite':0,'Safety':SAFETY})
    save(OUT/'PRIVATE_SOURCE_AUDIT.json',{'status':'PASS','v10_sha256':PACK_SHA,'bytes':PACK.stat().st_size,'recursive_manifest_receipts':receipts,'hash_mismatch_N':0,'provider_request':0,'Safety':SAFETY})
    checkpoint('R0_START_LATEST_AND_V10_FREEZE','V10 terminal/private identity certified','R1 negative history')
    required=['DESIGN_PRECOMMIT.json','NEW_HEAD_FITS.json','HEAD_QUALITY_DIAGNOSTICS.json','REPORT-ja.md','CAPITAL_QUALITY_V3_CLOSURE.json']
    texts={n:(NEG/n).read_text() for n in required};heads=json.loads(texts['HEAD_QUALITY_DIAGNOSTICS.json'])['heads']
    negclosure=json.loads(texts['CAPITAL_QUALITY_V3_CLOSURE.json'])
    save(OUT/'HF1_HL0_NEGATIVE_HISTORY_FREEZE.json',{'status':'READ_AND_FROZEN','files':{n:sha(NEG/n) for n in required},'HF1':{k:heads['HF1'][k] for k in ('N','ROC_AUC','Brier')},'HL0':{k:heads['HL0'][k] for k in ('N','ROC_AUC','Brier')},'old_selection_status':negclosure['selection_status'],'old_status':negclosure['status'],'prior_X':'CORE 27 numeric +7 categorical','prior_teacher':'HF1 realized>=1%; HL0 realized<=0','new_teacher':'within-potential-bucket strictly above completed-train realized median','new_X':'Frozen Movement 46 numeric +7 categorical','HF1_HL0_refit_allowed':False,'LSAFE_Q1_Q8_reconstruction_allowed':False,'Safety':SAFETY})
    checkpoint('R1_INPUT_PRIVATE_AND_NEGATIVE_HISTORY_AUDIT','All nested manifest hashes match; HF1/HL0 negative read','R2/R3 precommit before teacher generation')
    print(json.dumps({'source':'PASS','manifests':len(receipts),'protected_tracked_N':len(protected),'negative':'READ'}))
if __name__=='__main__':main()
