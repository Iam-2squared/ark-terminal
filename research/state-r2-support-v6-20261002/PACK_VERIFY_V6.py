"""3 independently openable ZIPs, unchanged V5 COMPLETE originals and hashes."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,zipfile,csv,sys
R=Path(__file__).resolve().parent;ROOT=R.parent;V=ROOT/'state_predictiveness_v5_r2_confirmation_20261002_v1';PREFIX='research/state-r2-support-v6-20261002/'
NAMES=['Ark_Terminal_V6_Part1_Results.zip','Ark_Terminal_V6_Part2_Data.zip','Ark_Terminal_V6_Part3_Parent_V5_V3.zip'];OLD=['Ark_Terminal_V5_Part1_Results.zip','Ark_Terminal_V5_Part2_Data.zip','Ark_Terminal_V5_Part3_Parent_V3.zip']
REQUIRED=['00_README.txt','V5_INHERITANCE_RECEIPT_V6.json','FRESH_SCOPE_V6.json','FRESH_SCOPE_PRECOMMIT_V6.json','DEVELOPMENT_COMPLETION_LEDGER_V6.csv','UNAVAILABLE_INPUTS_V6.csv','PREDICTIVENESS_V6_CONTRACT.md','PREDICTIVENESS_V6_PRECOMMIT.json','FROZEN_IDENTITY_RECEIPT_V6.json','R1_R2_OOF_V6.csv','R1_R2_HARD_METRICS_V6.csv','UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V6.csv','V5_V6_POOLED_METRICS.csv','V6_ONLY_METRICS.csv','TRUE_NULL_R2_V6.csv','STABILITY_AND_CONCENTRATION_V6.csv','CALIBRATION_METRICS_V6.csv','CALIBRATION_BUCKETS_V6.csv','CALIBRATION_STATUS_V6.json','BOOTSTRAP_GLOBAL_1000_RECEIPT_V6.json','INDEPENDENT_AUDIT_V6.json','BUDGET_START_V6.json','BUDGET_FINAL_V6.json','EXPOSURE_APPEND_ONLY_DELTA_V6.json','REPORT-ja.md','HYBRID_ENTRY_INTELLIGENCE_HANDOFF.md','NEXT_STAGE_HANDOFF.md']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
def save(n,obj):(R/n).write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def classify():
 excludedroots={'runner','PARENT_V4','__pycache__'};excluded={'ACQUISITION_PAYLOAD_V6.zip','DELIVERY_PACKAGE_RECEIPT_V6.json','ARCHIVE_VERIFICATION_V6.json','SPLIT_PACKAGE_MANIFEST_V6.json','SPLIT_README_V6.txt','DELIVERY_MANIFEST.json','DELIVERY_VERIFICATION_V6.json'};data={'ACQUISITION','FRESH_FITTED','FRESH_LABELS','PARENT_V5_ORIGINAL'};items={}
 for p in sorted(R.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(R)
  if rel.parts[0] in excludedroots or '__pycache__' in rel.parts or p.suffix in ['.py','.pyc','.b64','.yml'] or p.name in excluded or p.name.endswith('.tmp'):continue
  part=2 if rel.parts[0] in data or p.name in ['ACQUISITION_ARTIFACT_V6.zip','CALIBRATION_INNER_OOF_V6.csv','R1_R2_OOF_V6.csv','R1_R2_OOF_V6.jsonl'] else 1
  items[str(rel)]={'source':str(p),'part':part}
 for part,name in enumerate(OLD,1):items['PARENT_V5_ORIGINAL/'+name]={'source':str(ROOT/'delivery_v5'/name),'part':part}
 return items
def main():
 mode=sys.argv[1]
 if mode=='source':
  head=sys.argv[2];entries=[{'file':p.name,'path':PREFIX+p.name,'commit':head,'SHA256':sha(p),'url':'https://github.com/Iam-2squared/ark-terminal/blob/'+head+'/'+PREFIX+p.name} for p in sorted(R.glob('*.py'))]
  for name,path in [('state-r2-v6-support-20261002.yml','.github/workflows/state-r2-v6-support-20261002.yml'),('ACQUISITION_PAYLOAD_V6.b64',PREFIX+'payload.b64')]:entries.append({'file':name,'path':path,'commit':head,'SHA256':sha(R/name),'url':'https://github.com/Iam-2squared/ark-terminal/blob/'+head+'/'+path})
  save('SOURCE_CODE_LOCATION_INDEX_V6.json',{'repository':'Iam-2squared/ark-terminal','branch':'state-predictiveness-v6-support-completion-20261002-v1','verified_final_snapshot_HEAD':head,'source_files':entries,'acquisition_payload_zip_SHA256':sha(R/'ACQUISITION_PAYLOAD_V6.zip'),'State_Path_kernel_inside_exact_payload':True,'Git_backed_code_excluded_from_evidence_ZIPs':True,'V5_original_code_index_preserved_inside_original_ZIPs':True,'completed_acquisition_refits_draws_not_authorized':True});print('source index fixed');return
 if mode=='manifest':
  items=classify();rows=[{'path':name,'bytes':Path(v['source']).stat().st_size,'SHA256':sha(Path(v['source'])),'zip':NAMES[v['part']-1]} for name,v in sorted(items.items())];save('DELIVERY_MANIFEST.json',{'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':json.loads((R/'FINAL_RECEIPT_V6.json').read_text())['status'],'files':rows,'ordinary_zip_count':3,'manifest_self_excluded':True,'V5_original_archives_byte_preserved':True,'source_index':'SOURCE_CODE_LOCATION_INDEX_V6.json','new_fits_labels_draws':0});print(json.dumps({'files':len(rows),'counts':{n:sum(r['zip']==n for r in rows) for n in NAMES}}));return
 if mode=='verify':
  final=json.loads((R/'FINAL_RECEIPT_V6.json').read_text());pre=json.loads((R/'PREDICTIVENESS_V6_PRECOMMIT.json').read_text());manifest=json.loads((R/'DELIVERY_MANIFEST.json').read_text());items=classify();checks=[]
  for n in REQUIRED:assert (R/n).is_file(),'REQUIRED_MISSING:'+n
  for n,h in pre['hashes'].items():assert sha(R/n)==h,'PRECOMMIT_CHANGED:'+n
  for n,h in json.loads((R/'EVALUATION_CODE_FREEZE_V6.json').read_text())['hashes'].items():assert sha(R/n)==h,'EVALUATOR_CHANGED:'+n
  for row in manifest['files']:assert sha(Path(items[row['path']]['source']))==row['SHA256'] and Path(items[row['path']]['source']).stat().st_size==row['bytes'],'MANIFEST_BYTE_MISMATCH:'+row['path']
  assert len(json.loads((R/'REPORT_25_ANSWERS_V6.json').read_text())['answers'])==25,'REPORT_25';assert len(json.loads((R/'FIGURE_MANIFEST_V6.json').read_text())['files'])==7,'CHARTS_7'
  csvrows=list(csv.DictReader((R/'R1_R2_OOF_V6.csv').open()));jsonrows=list(map(json.loads,(R/'R1_R2_OOF_V6.jsonl').open()));assert len(csvrows)==len(jsonrows),'OOF_FORMAT_COUNT'
  for cr,jr in zip(csvrows,jsonrows):
   for k,v in jr.items():assert json.loads(cr[k])==v if k=='probabilities' else cr[k]==str(v),'OOF_CSV_JSON_FIELD:'+k
  audit=json.loads((R/'INDEPENDENT_AUDIT_V6.json').read_text());assert audit['status']=='PASS' and audit['mismatch_N']==0 and audit['new_fits']==audit['new_bootstrap_draws']==0,'AUDIT_NOT_PASS'
  gate=json.loads((R/'V6_GATE_MEASUREMENTS.json').read_text());allowed=final['status'] in ['STATE_R2_REVERSAL_INTELLIGENCE_CONFIRMED_ENTRY_RESEARCH_ALLOWED','STATE_R2_REVERSAL_INTELLIGENCE_CONFIRMED_CALIBRATED'];assert allowed==final['Hybrid_Entry_research_allowed'],'FINAL_PERMISSION';assert final['calibrated_probability_handoff_allowed']==(final['status']=='STATE_R2_REVERSAL_INTELLIGENCE_CONFIRMED_CALIBRATED'),'PROB_PERMISSION'
  exp=json.loads((R/'EXPOSURE_APPEND_ONLY_DELTA_V6.json').read_text());assert all(exp[k]==0 for k in ['Holdout','Protected','OOS','Prospective','Entry','EXIT','profit','orders','broker_write','State9_changes','Path_changes','target_changes']),'EXPOSURE_OR_MEANING_CHANGE'
  for n in ['C0','C1','C2','C3','C4','C5','C6','C7']:
   cp=json.loads((R/'CHECKPOINTS'/f'{n}_POST_GET.json').read_text());assert cp['verified'] and cp['actual_post_commit_GET'],'CHECKPOINT_GET:'+n
  record={'status':'PASS','required_N':len(REQUIRED),'complete_manifest_N':len(manifest['files']),'parent_V5_archives_exact':True,'OOF_CSV_JSON_equal':True,'report_25_answers':True,'figures7':True,'independent_mismatch_N':0,'checkpoint_C0_C7_actual_GET':True,'fresh_fit_or_new_labels_or_bootstrap_in_verification':[0,0,0],'precommit_SHA256':sha(R/'PREDICTIVENESS_V6_PRECOMMIT.json'),'final_status':final['status'],'model_output_or_gate_changes':0};save('DELIVERY_VERIFICATION_V6.json',record);print(json.dumps(record));return
 assert mode=='zip'
 data=json.loads((R/'DELIVERY_MANIFEST.json').read_text());items=classify();out=ROOT/'delivery_v6';out.mkdir(exist_ok=True);shared=['DELIVERY_MANIFEST.json','DELIVERY_VERIFICATION_V6.json','SPLIT_PACKAGE_MANIFEST_V6.json','SPLIT_README_V6.txt'];split={'ordinary_ZIPs':NAMES,'no_spanning_format':True,'extract_all_to_same_directory':True,'manifest_SHA256':sha(R/'DELIVERY_MANIFEST.json'),'source_index_SHA256':sha(R/'SOURCE_CODE_LOCATION_INDEX_V6.json'),'verification_SHA256':sha(R/'DELIVERY_VERIFICATION_V6.json'),'V5_original_ZIPs':[{'filename':n,'SHA256':sha(ROOT/'delivery_v5'/n)} for n in OLD]};save('SPLIT_PACKAGE_MANIFEST_V6.json',split);(R/'SPLIT_README_V6.txt').write_text('Ark Terminal V6 COMPLETE:3 ordinary independently openable ZIPs. Extract all into the same directory.\nPart1 V6 results/reports/receipts + unchanged V5 Part1. Part2 V6 data/OOF/fits/features/traces + unchanged V5 Part2. Part3 unchanged V5 Part3 preserving original V3.\nPARENT_V5_ORIGINAL contains all3 original V5 ZIPs; open/extract those together into a separate PARENT_V5 directory for V5/V4/V3 originals. Do not overwrite any original parent.\nRead00_README.txt, REPORT-ja.md/html, FINAL_RECEIPT_V6.json and handoff. New code exact Git commit/path/hash in SOURCE_CODE_LOCATION_INDEX_V6.json. No further acquisition/fits/labels/bootstrap are authorized by opening this package.\n')
 files=[];seen=set()
 for name in NAMES:
  dest=out/name
  with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
   for row in data['files']:
    if row['zip']==name:
     source=Path(items[row['path']]['source']);assert sha(source)==row['SHA256'],'PACK_CHANGED';z.write(source,row['path']);assert row['path'] not in seen;seen.add(row['path'])
   for n in shared:z.write(R/n,n)
  with zipfile.ZipFile(dest) as z:assert z.testzip() is None,'ZIP_CRC';assert all(hashlib.sha256(z.read(row['path'])).hexdigest()==row['SHA256'] for row in data['files'] if row['zip']==name),'ZIP_MEMBER_SHA'
  files.append({'filename':name,'local_path':str(dest),'bytes':dest.stat().st_size,'SHA256':sha(dest),'CRC':'PASS','member_SHA':'PASS'})
 assert seen=={r['path'] for r in data['files']},'ZIP_COVERAGE';save('DELIVERY_PACKAGE_RECEIPT_V6.json',{'status':'PASS','files':files,'unique_evidence_members':len(seen),'ordinary_ZIPs':3,'V5_original_ZIP_bytes_unchanged':True,'new_fits_labels_draws':[0,0,0]});print(json.dumps(files))
if __name__=='__main__':main()
