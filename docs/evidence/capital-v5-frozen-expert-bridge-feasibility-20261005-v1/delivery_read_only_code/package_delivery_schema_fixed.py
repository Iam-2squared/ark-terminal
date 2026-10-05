"""Package completed read-only evidence; never evaluate or replay a market path."""
import datetime,gzip,hashlib,json,pathlib,zipfile

ROOT=pathlib.Path('/workspace/scratch/f3d0aa747c89')
W=ROOT/'bridge_work';E=W/'evidence';D=ROOT/'deliverables'

def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()

def sha(p):
    h=hashlib.sha256()
    with pathlib.Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def save(p,obj):
    with p.open('x') as f:json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')

def main():
    closure=json.loads((E/'CLOSURE.json').read_text())
    get=json.loads((E/'GET_RECEIPT_F9.json').read_text())
    assert closure['CURRENT_STATE']=='F9_CLOSURE_FIXED_STOP' and get['actual_GET_verified']
    assert closure['counts']['CapitalReplays']==closure['counts']['currentInference']==closure['counts']['newFits']==0
    source=json.loads((E/'SOURCE_MANIFEST.json').read_text())
    files={}
    for sub in ['code','evidence','private','sources']:
        for p in (W/sub).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':files[p.relative_to(ROOT).as_posix()]=p
    for p in [D/'REPORT_FINAL_V5_EXPERT_BRIDGE-ja.md',D/'V5_EXPERT_BRIDGE_FLAG_TRADEOFF.csv']:
        assert p.is_file();files[p.relative_to(ROOT).as_posix()]=p
    transport=[]
    for row in source['members']:
        p=pathlib.Path(row['local']);member=p.relative_to(ROOT).as_posix()
        assert p.is_file() and sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],member
        files[member]=p
        transport.append({'previous_absolute_path':row['local'],'pack_member':member,'source_manifest_provenance':{k:v for k,v in row.items() if k not in ['local','sha256','bytes']},'sha256':row['sha256'],'bytes':row['bytes'],'source_manifest_match':True})
    tp=E/'PACK_TRANSPORT_MAP.json';save(tp,{'exact_jst':now(),'root_contract':'extract pack at a new task root; transport paths are provenance, not guessed aliases; the original scripts retain the archived execution root and are NOT automatically run','map':transport,'provider_fetches':0,'replay_authorization':0})
    files[tp.relative_to(ROOT).as_posix()]=tp
    records=[]
    for member,p in sorted(files.items()):
        rec={'member':member,'sha256':sha(p),'bytes':p.stat().st_size}
        if member.startswith('bridge_work/private/') and p.name.endswith('.jsonl.gz'):
            uncompressed_hash=hashlib.sha256();count=0;size=0
            with gzip.open(p,'rb') as f:
                for line in f:
                    uncompressed_hash.update(line);size+=len(line)
                    if line.strip():json.loads(line);count+=1
            rec.update(jsonl_rows=count,uncompressed_bytes=size,uncompressed_sha256=uncompressed_hash.hexdigest(),gzip_crc_and_json_valid=True)
        records.append(rec)
    manifest={'schema':'V5_EXPERT_BRIDGE_PRIVATE_PAYLOAD_MANIFEST_V1','exact_jst':now(),'known_F9_commit':get['commit'],'known_F9_tree':get['tree'],'payload_member_N':len(records),'payload_members':records,'manifest_self_excluded':True,'manifest_member':'bridge_work/evidence/PRIVATE_MANIFEST.json','full_ZIP_member_N':len(records)+1,'late_delivery_receipts':'post-package Git/Library delivery receipts are intentionally external to avoid self-hash/future-commit cycles','transport_map':'bridge_work/evidence/PACK_TRANSPORT_MAP.json','canonical_new_AUC_diagnostics':'bridge_work/evidence/corrections/*.json; earlier failed outputs retained, not canonical','new_primary_batch':1,'independent_verification':1,'new_fit_inference_replay':0,'Safety':closure['Safety'],'Exposure':closure['Exposure'],'activeCapitalChampion':'V5','selectedCapitalCandidate':None,'CapitalImproved':'NOT_EVALUATED'}
    mp=E/'PRIVATE_MANIFEST.json';save(mp,manifest)
    zpath=D/'Ark_Capital_V5_Frozen_Expert_Bridge_Feasibility_20261005_PRIVATE.zip'
    assert not zpath.exists()
    with zipfile.ZipFile(zpath,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for member,p in sorted(files.items()):z.write(p,member)
        z.write(mp,manifest['manifest_member'])
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None
        assert len(z.namelist())==manifest['full_ZIP_member_N'] and len(set(z.namelist()))==len(z.namelist())
        for row in records:
            b=z.read(row['member']);assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
        assert z.read(manifest['manifest_member'])==mp.read_bytes()
    receipt={'schema':'V5_EXPERT_BRIDGE_PACKAGE_DELIVERY_RECEIPT_V1','exact_jst':now(),'CURRENT_STATE':'F9_CLOSURE_FIXED_STOP','status':closure['status'],'known_F9_commit':get['commit'],'known_F9_tree':get['tree'],'zip_filename':zpath.name,'zip_bytes':zpath.stat().st_size,'zip_sha256':sha(zpath),'zip_member_N':manifest['full_ZIP_member_N'],'payload_member_N':len(records),'manifest_sha256':sha(mp),'all_payload_member_hashes_exact':True,'archive_crc_PASS':True,'source_transport_members_verified':len(transport),'packet_sha256':closure['packet_sha256'],'report_sha256':closure['report_sha256'],'code_hashes':closure['code_hashes'],'counts':closure['counts'],'Safety':closure['Safety'],'Exposure':closure['Exposure'],'activeCapitalChampion':'V5','selectedCapitalCandidate':None,'CapitalImproved':'NOT_EVALUATED','postcommit_receipt':'separate actual GET receipt; no future commit SHA predicted','Library_save':'separate ordered task deliverable upload after this package is fixed','next':'STOP; no runtime or replay authorization'}
    save(E/'DELIVERY_RECEIPT.json',receipt)
    print(json.dumps({k:receipt[k] for k in ['CURRENT_STATE','zip_filename','zip_bytes','zip_sha256','zip_member_N','payload_member_N','all_payload_member_hashes_exact']},ensure_ascii=False))

if __name__=='__main__':main()
