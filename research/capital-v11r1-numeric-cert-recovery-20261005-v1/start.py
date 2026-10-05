"""Authenticated private chain and exact completed-fit reuse, no numerical repair."""
from control import *
import io,zipfile,subprocess,numpy as np
REQUIRED=['CLOSURE.json','NEXT_WORK_HANDOFF.json','REPORT_FINAL-ja.md','NUMERIC_CONTRACT_FAILURE_RECEIPT.json','INDEPENDENT_SIGNAL_AUDIT.json','MRET_8_FITS_RESULT.json','MRET_FIT_CLAIM.json','MRET_TEACHER_FEATURE_MODEL_PRECOMMIT.json','MRET_TEACHER_RESULT.json','ZERO_FIT_MRET_CONTROL_RESULT.json','MRET_PRIMARY_RESULT.json','POTENTIAL_BUCKET_REALIZED_CONCORDANCE.json','SESSION_BOOTSTRAP_RESULT.json','FROZEN_EXIT_REALIZED_DIAGNOSTICS.json','MRET_POINT_GATE_PENDING_INDEPENDENT_AUDIT.json','SIGNAL_GATE_DECISION.json','M1_M2_CAPITAL_POLICY_PRECOMMIT.json','PRIVATE_PACK_MANIFEST.json']
def unpack(data,destination,lineage,receipts):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=z.namelist();assert len(names)==len(set(names))
        assert all(not n.startswith('/') and '..' not in Path(n).parts for n in names)
        for mn in [n for n in names if n.rsplit('/',1)[-1] in ('MANIFEST.json','DELIVERY_MANIFEST.json')]:
            d=json.loads(z.read(mn));fs=d.get('files',[])
            if isinstance(fs,dict):fs=[dict(v,path=k) for k,v in fs.items()]
            ncheck=0
            for f in fs:
                if not isinstance(f,dict) or 'sha256' not in f:continue
                n=next((x for x in [f['path'],str(Path(mn).parent/f['path'])] if x in names),None);assert n is not None
                raw=z.read(n);assert hashlib.sha256(raw).hexdigest()==f['sha256'],(lineage,n)
                size=f.get('bytes',f.get('size'));assert size is None or size==len(raw);ncheck+=1
            receipts.append({'archive':lineage,'manifest':mn,'manifest_sha256':hashlib.sha256(z.read(mn)).hexdigest(),'verified_file_N':ncheck,'schema':d.get('schema')})
        if destination:
            assert not destination.exists();z.extractall(destination)
        for n in names:
            if n.endswith('.zip') and n.startswith('authority/'):
                if 'v10_' in n:dest=V10
                elif 'v9_' in n:dest=V9
                elif 'v8R1_' in n:dest=MAIN
                elif 'v1R1_' in n:dest=AUTH/'quality'
                elif 'Quality_v1_' in n:dest=QUALITY
                else:dest=None
                unpack(z.read(n),dest,lineage+'/'+n,receipts)
def main():
    assert not OUT.exists(),'EXISTING_CYCLE_NO_OVERWRITE'
    assert sha(PACK)==PACK_SHA,'V11R1_SOURCE_BLOCKED'
    c=read(PARENT/'CLOSURE.json');g=read(PARENT/'SIGNAL_GATE_DECISION.json');a=read(PARENT/'INDEPENDENT_SIGNAL_AUDIT.json')
    assert c['CURRENT_STATE']=='CAPITAL_V11_R10_SIGNAL_NO_GO_CLOSURE_FIXED_STOP' and c['status']=='V11_CONTRACT_FAIL'
    assert c['CapitalReplays']==0 and g['gate']['S9'] is False and a['mismatch_N']==1
    assert c['private_sha256']==PACK_SHA
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==PARENT_SHA
    protected={}
    for line in subprocess.check_output(['git','ls-files','-s','-z','docs','research'],cwd=ROOT,text=True).split('\0'):
        if not line:continue
        info,path=line.split('\t');raw=(ROOT/path).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==info.split()[1],path
        protected[path]=hashlib.sha256(raw).hexdigest()
    save(WORK/'PROTECTED_TRACKED_HASHES.json',protected)
    authority={n:sha(PARENT/n) for n in REQUIRED}
    for n in ['model.py','independent_signal.py','runtime.py']:authority['research/'+n]=sha(ROOT/'research/capital-v11-realized-monetization-signal-20261005-v1'/n)
    save(OUT/'V11_PARENT_AUTHORITY_FREEZE.json',{'exact_jst':now(),'v11_HEAD':PARENT_SHA,'tree':read(WORK/'latest_basis.json')['tree'],'old_closure':c,'oldS9':'FAIL','old_evidence_rewrite':0,'required_authority_sha256':authority,'Safety':SAFETY})
    checkpoint('N0_START_LATEST_AND_V11_FREEZE','Actual v11 terminal HEAD; old failure retained','N1 source and completed fit identity')
    receipts=[];unpack(PACK.read_bytes(),V11,'v11',receipts)
    save(OUT/'PRIVATE_SOURCE_AUDIT.json',{'status':'PASS','private_sha256':PACK_SHA,'bytes':PACK.stat().st_size,'recursive_manifest_receipts':receipts,'mismatch_N':0,'provider_request':0,'Safety':SAFETY})
    fits=read(PARENT/'MRET_8_FITS_RESULT.json');assert (fits['fits'],fits['OOF_N'],fits['train_score_N'])==(8,1039,8057)
    assert fits['ConvergenceWarning_N']==fits['within_block_refits']==fits['other_fits']==0
    for rec in fits['fit_ledger']:
        b=rec['block'];m=V11/f'private/models/MRET_BLOCK_{b:02d}.json';s=V11/f'private/fitted_state/MRET_BLOCK_{b:02d}.npz'
        assert sha(m)==rec['model_sha256'] and sha(s)==rec['snapshot_sha256']
        model=read(m);done=read(V11/f'private/claims/MRET_BLOCK_{b:02d}_COMPLETE.json');assert done==rec
        assert model['optimizer_calls']==rec['optimizer_calls']==1
        assert all(model[k]==rec[k] for k in ['train_N','train_positive_N','iterations'])
        assert model['train_N']==len(model['train_entry_ids'])
        with np.load(s) as snap:
            assert np.array_equal(snap['coef'][0],model['coef']) and snap['intercept'][0]==model['intercept'] and np.array_equal(snap['classes'],model['classes'])
    assert len(rows(V11/'private/MRET_OOF_SCORES.jsonl.gz'))==1039 and len(rows(V11/'private/MRET_TRAIN_RESUBSTITUTION_SCORES.jsonl.gz'))==8057
    save(OUT/'MRET_COMPLETED_FITS_REUSE_FREEZE.json',{'status':'EXACT_REUSE','reusedMRETFits':8,'newFits':0,'refits':0,'audit_refits':0,'optimizer_calls':0,'OOF_N':1039,'train_score_N':8057,'fit_ledger':fits['fit_ledger'],'OOF_sha256':sha(V11/'private/MRET_OOF_SCORES.jsonl.gz'),'train_scores_sha256':sha(V11/'private/MRET_TRAIN_RESUBSTITUTION_SCORES.jsonl.gz'),'ConvergenceWarning_N':0,'Safety':SAFETY})
    checkpoint('N1_PRIVATE_AND_COMPLETED_FIT_REUSE_AUDIT','All nested manifests and eight model/snapshot/claim identities exact; newFits0','N2 formal numerical operator precommit')
    print(json.dumps({'source':'PASS','nested_manifests':len(receipts),'reused_fits':8,'newFits':0}))
if __name__=='__main__':main()
