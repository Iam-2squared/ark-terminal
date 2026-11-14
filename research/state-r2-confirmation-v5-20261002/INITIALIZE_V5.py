"""Verify and reconstruct the immutable user-supplied V4 parent. No fits or labels."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json, zipfile

ROOT = Path(__file__).resolve().parent
PARENT = ROOT / 'PARENT_V4'
WORKSPACE = ROOT.parent
PARTS = [
 ('15-Ark_Terminal_V4_Part1_Results.zip','731544013d09b6a34fb1ec88b4cbfac3d751d517874faa52b541fc191e319fff'),
 ('17-Ark_Terminal_V4_Part2_Data.zip','19f418fe8290e45232c47c137e9ca57c7ade08bc16137c0a99c2cd5d8ac9b99d'),
 ('16-Ark_Terminal_V4_Part3_V3_Original.zip','72115585043e16a50e6ba82b4623859159a1ad4d638f1b56dcdca9abe309eaf9'),
]
EXPECTED = {
 'PREDICTIVENESS_V4_CONTRACT.md':'d75ef5436ce496ab6c8f793474a0db72ec97de821008984ed8f1a08a048a08ff',
 'PREDICTIVENESS_V4_PRECOMMIT.json':'abbca554a30276cad3d2d7729e6581343dab1e640ef9deeff502acbdb7b5aff7',
 'DATA_SCOPE_V4.json':'c0c1d5f3d4d1498b28271c31cc507055af7cbb656ee32c13c41ad06fadb5bfee',
 'OOF_ALL.jsonl':'0ffef17b392904f95267dc137a5f226f51974922b1d7142bb1b9abe2fe7f2cfb',
}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(name,obj):
 p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def main():
 PARENT.mkdir(exist_ok=True)
 rows=[]; seen={}; dup=0
 for fname,expected in PARTS:
  src=WORKSPACE/'project_sources'/fname; got=sha(src)
  assert got==expected,(fname,got,expected)
  with zipfile.ZipFile(src) as z:
   assert z.testzip() is None
   for info in z.infolist():
    rel=Path(info.filename)
    assert not rel.is_absolute() and '..' not in rel.parts
    if info.is_dir():continue
    if info.filename in seen:
     assert info.filename in ('SPLIT_README-ja.txt','SPLIT_PACKAGE_MANIFEST.json')
     assert seen[info.filename]==hashlib.sha256(z.read(info)).hexdigest()
     dup+=1;continue
    data=z.read(info); digest=hashlib.sha256(data).hexdigest();seen[info.filename]=digest
    dest=PARENT/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():assert sha(dest)==digest
    else:dest.write_bytes(data)
  rows.append({'filename':fname,'sha256':got,'bytes':src.stat().st_size,'CRC':'PASS'})
 for name,digest in EXPECTED.items():assert sha(PARENT/name)==digest,(name,sha(PARENT/name))
 receipt=json.loads((PARENT/'FINAL_RECEIPT.json').read_text())
 audit=json.loads((PARENT/'INDEPENDENT_AUDIT_V4.json').read_text())
 print(json.dumps({'parent_receipt':receipt,'audit_fields':{k:v for k,v in audit.items() if k in ('status','mismatch_N','assertions','new_fit_count','new_bootstrap_draws')}},ensure_ascii=False))
 manifest=json.loads((PARENT/'DELIVERY_MANIFEST.json').read_text())
 for item in manifest['files']:
  assert sha(PARENT/item['path'])==item['SHA256'],item['path']
  assert (PARENT/item['path']).stat().st_size==item['bytes']
 assert receipt['status']=='BLOCKED_V4_INTEGRITY' and receipt['integrity']=='FAIL_CONTROL'
 assert receipt['independent_audit']=='PASS' and receipt['mismatch_N']==0
 source_index=json.loads((PARENT/'SOURCE_CODE_LOCATION_INDEX.json').read_text())
 old=WORKSPACE/'state_predictiveness_v4_confirmation_20261002_v1'
 code_receipts=[]
 for item in source_index['source_files']:
  local=old/item['file']
  if local.exists():
   assert sha(local)==item['SHA256'],item['file']
   code_receipts.append({'file':item['file'],'sha256':item['SHA256'],'local_verified':True,'git_commit':item['commit'],'git_path':item['path']})
 save('V4_SOURCE_CODE_HASH_VERIFICATION_V5.json',{'verified':code_receipts,'missing':[i['file'] for i in source_index['source_files'] if not (old/i['file']).exists()]})
 save('INHERITANCE_INPUT_VERIFICATION_V5.json',{'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'parent_head':'1b0b5c3c28f8f092f16c81b07c11f818e77879ef','parts':rows,'unique_members':len(seen),'duplicate_split_metadata_members':dup,'frozen_hashes':EXPECTED,'parent_status_unchanged':receipt,'manifest_full_verification':'PASS','manifest_verified_file_N':len(manifest['files']),'initial_readonly_input_mapping_repair':'The user OOF hash identifies OOF_ALL.jsonl, not the task-specific CSV. Resolved from original manifest and receipt; original bytes unchanged.','new_labels':0,'new_fits':0,'new_bootstrap_draws':0,'state_kernel_reruns':0})
 print('VERIFIED_PARENT_EXTRACTION',len(seen))
if __name__=='__main__':main()
