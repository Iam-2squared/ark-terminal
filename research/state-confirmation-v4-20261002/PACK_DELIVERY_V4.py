"""One complete evidence ZIP, with parent bytes, portable paths and all SHA256."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,csv,hashlib,copy,io,base64,re,zipfile,os,subprocess,sys
R=Path(__file__).resolve().parent;REPO='Iam-2squared/ark-terminal';PREFIX='research/state-confirmation-v4-20261002';PARENT=R.parent/'deliverables/Ark_Terminal_State_Predictiveness_V3_COMPLETE_20261002.zip'
REQUIRED='''00_README.txt PREDICTIVENESS_V4_CONTRACT.md PREDICTIVENESS_V4_PRECOMMIT.json FROZEN_IDENTITY_RECEIPT.json DEVELOPMENT_COMPLETION_LEDGER_V4.csv UNAVAILABLE_INPUTS_V4.csv DATA_SCOPE_V4.json DATASET_MANIFEST_V4.json SPLIT_PLAN_V4.json SPLIT_REALIZED_V4.json REVERSAL_METRICS_V4.csv UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V4.csv CALIBRATION_METRICS_V4.csv CALIBRATION_BUCKETS_V4.csv R0_R1_R2_R3_R4_INCREMENTAL_V4.csv PATH_ANATOMY_LENGTH1_V4.csv PATH_ANATOMY_LENGTH2_V4.csv PATH_ANATOMY_LENGTH3_V4.csv PATH_ANATOMY_LENGTH4_V4.csv NEXTSTATE_9CLASS_V4.csv CONFUSION_MATRIX_9STATE_V4.csv PER_STATE_PRECISION_RECALL_F1_V4.csv NEGATIVE_CONTROL_V4.csv SHIFT60_STRESS_V4.csv BOOTSTRAP_GLOBAL_1000_RECEIPT.json INDEPENDENT_AUDIT_V4.json EXPOSURE_APPEND_ONLY_DELTA.json BUDGET_START_V4.json BUDGET_FINAL_V4.json REPORT-ja.md NEXT_STAGE_HANDOFF.md FINAL_RECEIPT.json MODEL_EXECUTION_LEDGER.jsonl OOF_ALL.jsonl FIT_INDEX_V4.json GITHUB_REQUEST_USAGE_AT_DELIVERY.json CHART_MANIFEST.json CHART_VALIDATION_V4.json'''.split()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def encoded(x):return (json.dumps(x,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()
def load(n):return json.loads((R/n).read_text())
def stamp():return datetime.now(timezone(timedelta(hours=9))).isoformat()
def html():
 node=os.environ['CODEX_PRIMARY_RUNTIME_NODE'];program="const m = await import(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES + '/marked/lib/marked.esm.js'); let s=''; for await (const b of process.stdin) s+=b; process.stdout.write(m.marked.parse(s));"
 body=subprocess.run([node,'--input-type=module','-e',program],input=(R/'REPORT-ja.md').read_text(),capture_output=True,text=True,check=True).stdout
 body=re.sub(r'src="(CHARTS/[^"<>]+\.png)"',lambda m:'src="data:image/png;base64,'+base64.b64encode((R/m.group(1)).read_bytes()).decode()+'"',body)
 assert body.count('data:image/png;base64,')==12,'EMBED_ALL_TWELVE'
 return ('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ark Terminal State Predictiveness V4</title><style>body{max-width:1180px;margin:36px auto;padding:0 20px;font-family:system-ui,sans-serif;line-height:1.7;color:#17212e}img{max-width:100%;height:auto}table{border-collapse:collapse;display:block;overflow:auto;font-size:13px;width:100%;margin:20px 0}th,td{border:1px solid #d4dbe2;padding:8px;text-align:left}th{background:#eef3f7}h1,h2{line-height:1.4}code{word-break:break-all}@media print{body{font-size:10pt}table{font-size:8pt}img{break-inside:avoid}}</style><body>'+body+'</body></html>').encode()
def build(head,dst):
 for n in REQUIRED:assert (R/n).is_file(),n
 assert sha(PARENT)=='c04a71f4180474c17b6ab7e6abe6dfc701ac28cb917e36ce6dff1c616eaa27d2','V3_COMPLETE_UNCHANGED'
 for n,h in load('PREDICTIVENESS_V4_PRECOMMIT.json')['hashes'].items():assert sha(R/n)==h,'PRECOMMIT_CHANGED'
 for x in load('FIT_INDEX_V4.json')['items']:
  if x['status']=='FITTED':assert sha(R/x['path'])==x['SHA256'],'FIT_CHANGED'
 assert sha(R/'OOF_ALL.jsonl')==load('C5_OOF_FIXATION_RECEIPT.json')['OOF_SHA256'],'OOF_CHANGED'
 assert len(list((R/'CHARTS').glob('*.png')))==len(list((R/'CHARTS').glob('*.svg')))==12
 members={};allowed={'.json','.jsonl','.csv','.md','.txt','.log','.png','.svg','.html'}
 for p in sorted(R.iterdir()):
  if p.is_file() and p.suffix in allowed and p.name not in ['DELIVERY_MANIFEST.json','DELIVERY_PACKAGE_RECEIPT.json']:members[p.name]=p
 for directory in ['FEATURES','LABELS','STATE9_TRACES','FITTED','FROZEN_INPUTS','NEW_DEVELOPMENT','CHARTS','CHECKPOINTS','INHERITED_V3','INHERITED_V2','RECOVERY_FINDINGS']:
  for p in sorted((R/directory).rglob('*')):
   if p.is_file() and p.suffix in allowed:members[str(p.relative_to(R))]=p
 manifest=load('DATASET_MANIFEST_V4.json');portable=copy.deepcopy(manifest);locations=[]
 for original,pair in zip(manifest['pairs'],portable['pairs']):
  pid=pair['pair_id'];originalpath=Path(original['original_feature_path']);pathendpoint=Path(original['path_endpoint_path'])
  specs=[('feature_path',Path(original['feature_path']),f'FEATURES/{pid}.jsonl',original['feature_SHA256']),('original_feature_path',originalpath,f'ORIGINAL_FEATURES/{pid}.jsonl',original['original_feature_SHA256']),('trace_path',Path(original['trace_path']),f'STATE9_TRACES/{pid}.jsonl',original['state_trace_SHA256']),('path_endpoint_path',pathendpoint,f'PATH_ENDPOINTS/{pid}.jsonl',original['path_endpoint_SHA256']),('label_path',R/'LABELS'/f'{pid}.jsonl',f'LABELS/{pid}.jsonl',None)]
  if original.get('old_label_path'):specs.append(('old_label_path',Path(original['old_label_path']),f'PRIOR_V3_LABELS/{pid}.jsonl',None))
  for field,src,name,expected in specs:
   assert src.is_file(),str(src)
   h=sha(src);assert expected is None or h==expected,('INPUT_HASH',pid,field);members[name]=src;pair[field]=name;locations.append({'pair_id':pid,'date':pair['date'],'security_id':pair['security_id'],'field':field,'archive_path':name,'original_path':str(src),'SHA256':h,'bytes':src.stat().st_size})
 portable['portability']={'path_rewrite_only':True,'original_manifest_SHA256':sha(R/'DATASET_MANIFEST_V4.json'),'original_file':'DATASET_MANIFEST_V4.json'}
 code=[]
 for p in sorted(R.glob('*.py')):code.append({'file':p.name,'SHA256':sha(p),'repository':REPO,'commit':head,'path':PREFIX+'/'+p.name,'URL':f'https://github.com/{REPO}/blob/{head}/{PREFIX}/{p.name}'})
 for p in sorted((R/'runner').rglob('*')):
  if p.is_file() and '__pycache__' not in str(p):code.append({'file':'runner/'+str(p.relative_to(R/'runner')),'SHA256':sha(p),'repository':REPO,'commit':head,'path':PREFIX+'/payload.b64','archive_member':str(p.relative_to(R/'runner')),'URL':f'https://github.com/{REPO}/blob/{head}/{PREFIX}/payload.b64','payload_ZIP_SHA256':sha(R/'ACQUISITION_PAYLOAD_V4.zip')})
 sources={'JST':stamp(),'repository':REPO,'branch':'state-predictiveness-v4-confirmation-20261002-v1','final_verified_HEAD':head,'code_storage':'GitHub code; evidence ZIP contains index, not a duplicate git project','read_only_no_rerun':True,'source_files':code}
 buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(locations[0]));writer.writeheader();writer.writerows(locations)
 supplemental={'DATASET_MANIFEST_PORTABLE_V4.json':encoded(portable),'SOURCE_CODE_LOCATION_INDEX.json':encoded(sources),'INPUT_LOCATION_INDEX_V4.csv':buffer.getvalue().encode(),'REPORT-ja.html':html()}
 members['INHERITED_V3_ORIGINAL/'+PARENT.name]=PARENT
 if (R/'DEVELOPMENT_EXPANSION_ARTIFACT_V4.zip').exists():members['DEVELOPMENT_EXPANSION_ARTIFACT_V4.zip']=R/'DEVELOPMENT_EXPANSION_ARTIFACT_V4.zip'
 # Exact OOF alias requested by user; same bytes, not a second computation.
 members['REVERSAL_OOF_V4/CONTEXT_REVERSAL_OOF_V4.csv']=R/'CONTEXT_REVERSAL_OOF_PREDICTIONS.csv'
 files=[{'path':name,'SHA256':sha(p),'bytes':p.stat().st_size} for name,p in sorted(members.items())]+[{'path':name,'SHA256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for name,b in sorted(supplemental.items())]
 delivery={'JST':stamp(),'status':load('FINAL_RECEIPT.json')['status'],'one_complete_zip':True,'file_N_without_manifest':len(files),'files':files,'manifest_self_hash_excluded':True,'V3_original_complete_preserved':True,'original_V3_SHA256':sha(PARENT),'final_verified_GitHub_HEAD':head,'new_fits_draws_provider_requests':0}
 (R/'DELIVERY_MANIFEST.json').write_bytes(encoded(delivery));supplemental['DELIVERY_MANIFEST.json']=encoded(delivery)
 dst.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(dst,'x',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
  for name,p in sorted(members.items()):z.write(p,name,compress_type=zipfile.ZIP_STORED if p.suffix=='.zip' else zipfile.ZIP_DEFLATED)
  for name,b in sorted(supplemental.items()):z.writestr(name,b)
 with zipfile.ZipFile(dst) as z:
  assert z.testzip() is None,'FINAL_ZIP_CRC'
  assert len(z.namelist())==len(files)+1,'NO_MISSING_OR_EXTRA_MEMBERS'
  for x in files:
   assert len(z.read(x['path']))==x['bytes'] and hashlib.sha256(z.read(x['path'])).hexdigest()==x['SHA256'],('ZIP_MEMBER_HASH',x['path'])
  assert hashlib.sha256(z.read('INHERITED_V3_ORIGINAL/'+PARENT.name)).hexdigest()==sha(PARENT),'NESTED_PARENT_CHANGED'
 out={'JST':stamp(),'archive':str(dst),'bytes':dst.stat().st_size,'SHA256':sha(dst),'member_N':len(files)+1,'CRC_PASS':True,'all_member_hashes_PASS':True,'complete':True,'split_archives':False,'new_fits_draws_provider':0}
 (R/'DELIVERY_PACKAGE_RECEIPT.json').write_bytes(encoded(out));print(json.dumps(out))
if __name__=='__main__':build(sys.argv[1],Path(sys.argv[2]))
