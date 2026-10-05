"""Preserve completed evidence and source bytes. Never invokes research scripts."""
from context import *
import zipfile

ZIPNAME='Ark_Capital_V5_Reserve_Past_Qualified_Recovery_20261005_PRIVATE.zip'
DELIVER=SCRATCH/'deliverables'
BRIDGEZIP=SCRATCH/'work/downloads/Ark_Capital_V5_Frozen_Expert_Bridge_Feasibility_20261005_PRIVATE.zip'

def payloads():
    files={}
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.name not in ('PRIVATE_MANIFEST.json','DELIVERY_RECEIPT.json'):
            files['repo/'+str(p.relative_to(REPO))]=p
    for p in sorted(CODE.glob('*.py')):files['repo/'+str(p.relative_to(REPO))]=p
    for p in sorted(PRIVATE.rglob('*')):
        if p.is_file():files['private/'+str(p.relative_to(PRIVATE))]=p
    for folder in ('bridge_public','r1_remote'):
        root=SCRATCH/'work'/folder
        for p in sorted(root.rglob('*')):
            if p.is_file():files['source_receipts/'+folder+'/'+str(p.relative_to(root))]=p
    workflow=SCRATCH/'work/workflow_new_branch_parse.json'
    files['source_receipts/workflow_new_branch_parse.json']=workflow
    files['inputs/'+BRIDGEZIP.name]=BRIDGEZIP
    return files

def manifest():
    assert json.loads((OUT/'CLOSURE.json').read_text())['FIXED_STOP']
    assert sha(BRIDGEZIP)=='a31eae5a5aea92bcd96bcc093e8379f588d801faee7858b2265a1de150401686'
    files=payloads()
    save('PRIVATE_MANIFEST.json',{'schema':'V5_R_PRIVATE_PAYLOAD_MANIFEST_V1','exact_jst':now(),
        'archive_name':ZIPNAME,'payload_N':len(files),'hashes':{k:{'bytes':p.stat().st_size,'sha256':sha(p)} for k,p in files.items()},
        'manifest_self_excluded':True,'internal_MANIFEST_self_excluded':True,
        'archive_sha256_recorded_after_bytes_created_in':'DELIVERY_RECEIPT.json',
        'source_bytes_included':'Entire verified Bridge PRIVATE ZIP plus new retained private/public/code/receipts',
        'new_R_ledgers_charts':'NOT_EXECUTED; placeholders only','no_policy_or_research_resume':True,'Safety':SAFETY})
    print(json.dumps({'manifest_payload_N':len(files),'archive_name':ZIPNAME}))

def build():
    m=json.loads((OUT/'PRIVATE_MANIFEST.json').read_text());files=payloads()
    # Package only identities fixed by the payload manifest. Later delivery receipts
    # are external append-only metadata and cannot cause self-referential hashes.
    files={k:files[k] for k in m['hashes']}
    for k,p in files.items():assert p.stat().st_size==m['hashes'][k]['bytes'] and sha(p)==m['hashes'][k]['sha256']
    manifest_path=OUT/'PRIVATE_MANIFEST.json';files['repo/'+str(manifest_path.relative_to(REPO))]=manifest_path
    internal={'schema':'V5_R_ARCHIVE_INTERNAL_MANIFEST_V1','exact_jst':now(),'files':{k:{'bytes':p.stat().st_size,'sha256':sha(p)} for k,p in files.items()},
        'self_excluded':'MANIFEST.json','Replay_N':0,'terminal_status':'PAST_SUPPORT_NOT_ESTABLISHED'}
    DELIVER.mkdir(parents=True,exist_ok=True);path=DELIVER/ZIPNAME;assert not path.exists()
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('MANIFEST.json',json.dumps(internal,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        for k,p in files.items():z.write(p,k,compress_type=zipfile.ZIP_STORED if p==BRIDGEZIP else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for k,meta in internal['files'].items():
            body=z.read(k);assert len(body)==meta['bytes'] and hashlib.sha256(body).hexdigest()==meta['sha256']
        assert len(z.namelist())==len(internal['files'])+1
    copies={'Ark_Terminal_V5_Reserve_Past_Qualified_Recovery_20261005_REPORT-ja.md':OUT/'REPORT_FINAL-ja.md',
        'PAIRED20_EXACT_V5_RESERVE_R_20261005.csv':OUT/'PAIRED20_EXACT.csv'}
    for name,source in copies.items():
        target=DELIVER/name;assert not target.exists();target.write_bytes(source.read_bytes())
    save('ARCHIVE_VERIFY.json',{'schema':'V5_R_DELIVERY_ARCHIVE_VERIFY_V1','exact_jst':now(),'archive_name':ZIPNAME,
        'archive_bytes':path.stat().st_size,'archive_sha256':sha(path),'member_N':len(internal['files'])+1,
        'payload_hash_checked_N':len(internal['files']),'CRC':'PASS','all_payload_sha256':'PASS',
        'manifest_sha256':sha(manifest_path),'source_Bridge_ZIP_sha256':sha(BRIDGEZIP)},private=True)
    print(json.dumps({'archive':str(path),'bytes':path.stat().st_size,'sha256':sha(path),'payloads_checked':len(internal['files'])}))

if __name__=='__main__':
    import sys
    assert sys.argv[1] in ('manifest','build')
    manifest() if sys.argv[1]=='manifest' else build()
