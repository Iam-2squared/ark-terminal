"""Three ordinary evidence ZIPs; original V4 members stay byte-identical."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,zipfile,sys,csv
R=Path(__file__).resolve().parent;P=R/'PARENT_V4';ROOT=R.parent;PREFIX='research/state-r2-confirmation-v5-20261002/'
NAMES=['Ark_Terminal_V5_Part1_Results.zip','Ark_Terminal_V5_Part2_Data.zip','Ark_Terminal_V5_Part3_Parent_V3.zip']
INPUT_PARTS=['15-Ark_Terminal_V4_Part1_Results.zip','17-Ark_Terminal_V4_Part2_Data.zip','16-Ark_Terminal_V4_Part3_V3_Original.zip']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def source_index(head):
 sources=[]
 for p in sorted(R.glob('*.py')):sources.append({'file':p.name,'SHA256':sha(p),'commit':head,'path':PREFIX+p.name,'url':'https://github.com/Iam-2squared/ark-terminal/blob/'+head+'/'+PREFIX+p.name})
 for name,path in [('state-r2-confirmation-v5-20261002.yml','.github/workflows/state-r2-confirmation-v5-20261002.yml'),('state-r2-v5-extension-20261002.yml','.github/workflows/state-r2-v5-extension-20261002.yml'),('ACQUISITION_PAYLOAD_V5.b64',PREFIX+'payload.b64'),('ACQUISITION_EXTENSION_PAYLOAD_V5.b64',PREFIX+'extension-payload.b64')]:
  p=R/name
  if p.exists():sources.append({'file':name,'SHA256':sha(p),'commit':head,'path':path,'url':'https://github.com/Iam-2squared/ark-terminal/blob/'+head+'/'+path})
 save('SOURCE_CODE_LOCATION_INDEX_V5.json',{'repository':'Iam-2squared/ark-terminal','branch':'state-predictiveness-v5-r2-confirmation-20261002-v1','verified_final_snapshot_HEAD':head,'source_files':sources,'State_and_Path_source_inside_public_payload':True,'public_payload_zip_SHA256':sha(R/'ACQUISITION_PAYLOAD_V5.zip'),'public_extension_payload_zip_SHA256':sha(R/'ACQUISITION_EXTENSION_PAYLOAD_V5.zip'),'Git_backed_source_excluded_from_library_evidence_archives':True,'original_V4_source_index_unchanged':'PARENT_V4/SOURCE_CODE_LOCATION_INDEX.json','no_re_execution_authorized':True})
def classify():
 items={};parent_manifest=json.loads((P/'DELIVERY_MANIFEST.json').read_text())
 for row in parent_manifest['files']:assert sha(P/row['path'])==row['SHA256'] and (P/row['path']).stat().st_size==row['bytes'],'PARENT_BYTE_CHANGED'
 for part,name in enumerate(INPUT_PARTS,1):
  with zipfile.ZipFile(ROOT/'project_sources'/name) as z:
   for f in z.infolist():
    if not f.is_dir():items.setdefault('PARENT_V4/'+f.filename,part)
 for p in sorted(P.rglob('*')):
  if p.is_file():assert 'PARENT_V4/'+str(p.relative_to(P)) in items,'UNTRACKED_PARENT_MEMBER'
 excluded_roots={'PARENT_V4','runner','extension_runner','__pycache__'};excluded_names={'ACQUISITION_PAYLOAD_V5.zip','ACQUISITION_EXTENSION_PAYLOAD_V5.zip','DELIVERY_PACKAGE_RECEIPT_V5.json','SPLIT_PACKAGE_MANIFEST_V5.json','SPLIT_README_V5.txt','DELIVERY_MANIFEST.json'}
 for p in sorted(R.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(R)
  if rel.parts[0] in excluded_roots or '__pycache__' in rel.parts or p.suffix in ['.py','.pyc','.b64','.yml'] or p.name in excluded_names or p.name.endswith('.tmp'):continue
  part=2 if rel.parts[0] in ['EXTENSION','RECOVERY','FRESH_LABELS','FRESH_FITTED','RESEARCH_FITTED','INVENTORY_METADATA'] or p.name in ['EXTENSION_ARTIFACT_V5.zip','RECOVERY_ARTIFACT_V5.zip','CALIBRATION_RESEARCH_OOF_V5.jsonl','CALIBRATION_INNER_OOF_V5.csv'] else 1
  items[str(rel)]=part
 return items
def main():
 mode=sys.argv[1]
 if mode=='source':source_index(sys.argv[2]);print('SOURCE_INDEX_FIXED');return
 if mode=='manifest':
  items=classify();rows=[{'path':name,'bytes':(R/name).stat().st_size,'SHA256':sha(R/name),'zip':NAMES[part-1]} for name,part in sorted(items.items())]
  save('DELIVERY_MANIFEST.json',{'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':json.loads((R/'FINAL_RECEIPT_V5.json').read_text())['status'],'files':rows,'ordinary_zip_count':3,'source_index':'SOURCE_CODE_LOCATION_INDEX_V5.json','manifest_self_excluded':True,'Parent_V4_bytes_unchanged':True,'new_model_fit':0,'new_bootstrap':0,'new_labels':0})
  print(json.dumps({'manifest_files':len(rows),'part_file_counts':{n:sum(r['zip']==n for r in rows) for n in NAMES}}));return
 assert mode=='zip'
 data=json.loads((R/'DELIVERY_MANIFEST.json').read_text());items={r['path']:NAMES.index(r['zip'])+1 for r in data['files']}
 for row in data['files']:assert sha(R/row['path'])==row['SHA256'] and (R/row['path']).stat().st_size==row['bytes'],'DELIVERY_CHANGED_AFTER_MANIFEST'
 text='Ark Terminal V5 COMPLETE — 3 ordinary ZIPs\nAll three can be opened separately. Extract all into the same directory. Do not concatenate or use .z01 spanning archives.\nPart1: V5 results/reports/receipts plus byte-identical V4 original results. Part2: V5 acquired/label/fit/research data plus byte-identical V4 data. Part3: immutable V3 original COMPLETE ZIP from the V4 parent.\nPARENT_V4 preserves all original member paths/bytes, including historical one-ZIP README instructions and original split manifests; the outer V5 split manifest governs this delivery.\nRead 00_README.txt / REPORT-ja.md / FINAL_RECEIPT_V5.json / NEXT_STAGE_HANDOFF.md. Use DELIVERY_MANIFEST.json to verify data paths/hash/size. Code sources are exact Git commit/path/SHA in SOURCE_CODE_LOCATION_INDEX_V5.json. No acquisition/refit/label/bootstrap reruns.\n'
 (R/'SPLIT_README_V5.txt').write_text(text)
 split={'ordinary_ZIPs':NAMES,'relative_paths_extract_together':True,'no_spanning_format':True,'manifest_SHA256':sha(R/'DELIVERY_MANIFEST.json'),'source_index_SHA256':sha(R/'SOURCE_CODE_LOCATION_INDEX_V5.json'),'Parent_V4_original_part_SHA256':[{'name':n,'SHA256':sha(ROOT/'project_sources'/n)} for n in INPUT_PARTS],'part_counts':{n:sum(x==i for x in items.values()) for i,n in enumerate(NAMES,1)}};save('SPLIT_PACKAGE_MANIFEST_V5.json',split)
 delivery=ROOT/'delivery_v5';delivery.mkdir(exist_ok=True);receipt=[];seen=set()
 for part,name in enumerate(NAMES,1):
  dest=delivery/name
  with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
   for rel,p in sorted(items.items()):
    if p==part:z.write(R/rel,rel);assert rel not in seen;seen.add(rel)
   for rel in ['DELIVERY_MANIFEST.json','SPLIT_PACKAGE_MANIFEST_V5.json','SPLIT_README_V5.txt']:z.write(R/rel,rel)
  with zipfile.ZipFile(dest) as z:assert z.testzip() is None,'FINAL_ZIP_CRC'
  receipt.append({'part':part,'filename':name,'local_path':str(dest),'bytes':dest.stat().st_size,'SHA256':sha(dest),'CRC':'PASS'})
 assert seen==set(items),'ARCHIVE_MEMBER_COVERAGE'
 save('DELIVERY_PACKAGE_RECEIPT_V5.json',{'status':'PASS','files':receipt,'unique_evidence_members':len(seen),'manifest_self_shared_across_parts':True,'Parent_V4_full_manifest_reverified':True,'ordinary_zip_count':3,'new_fits_draws_labels':[0,0,0]});print(json.dumps(receipt))
if __name__=='__main__':main()
