"""Index actual checkpoint receipts, then package immutable private delivery."""
from common import *
import shutil,zipfile,sys
NAME='Ark_Capital_v5_MAX3_Slot_Intelligence_20261004_PRIVATE.zip'
def index():
 result=[]
 for p in sorted((OUT/'checkpoints').glob('V*.json'),key=lambda p:int(p.name.split('_')[0][1:])):
  cp=json.loads(p.read_text());receipt=OUT/'receipts'/p.name;rc=json.loads(receipt.read_text());assert rc['actual_result_HEAD']==rc['ref']['object']['sha'] and rc['actual_result_tree']==rc['commit']['tree']['sha']
  result.append({'checkpoint':cp['checkpoint'],'JST':cp['JST'],'status':cp['status'],'instruction_basis_HEAD':cp['instruction_basis_HEAD'],'actual_result_HEAD':rc['actual_result_HEAD'],'actual_result_tree':rc['actual_result_tree'],'checkpoint_sha256':sha(p),'actual_GET_receipt_sha256':sha(receipt)})
 assert len(result)==11 and [r['checkpoint'].split('_')[0] for r in result]==[f'V{i}' for i in range(11)]
 save(OUT/'CHECKPOINT_INDEX.json',{'JST':now(),'checkpoints':result,'basis':BASIS,'count':len(result),'actual_GET_all_verified':True,'no_future_SHA':True,'status':'CLOSED_STOP'})
 print(json.dumps({'checkpoint_N':len(result),'actual_GET_all_verified':True}))
def package():
 delivery=WORK/'deliverables';delivery.mkdir(exist_ok=True)
 report=delivery/'Ark_Capital_v5_MAX3_Slot_Intelligence_20261004_Report.md';assert not report.exists();shutil.copyfile(OUT/'REPORT_FINAL-ja.md',report)
 figure=delivery/'Ark_Capital_v5_MAX3_Slot_Intelligence_20261004_Curves.png';assert not figure.exists();shutil.copyfile(PRIVATE/'CAPITAL_V5_ECONOMIC_AND_SLOT_CURVES.png',figure)
 bootstrap='''from pathlib import Path
import zipfile
root=Path(__file__).resolve().parent
outer=root/'input_archives/Ark_Capital_v4_Rank_Cutoff_Independent_20261004_PRIVATE.zip'
z=zipfile.ZipFile(outer)
name='deliverables/Ark_Capital_MAX3_Upward_Staircase_v4_20261004_PRIVATE.zip'
target=root/'source_v4'/name
target.parent.mkdir(parents=True,exist_ok=True)
if target.exists():
 assert target.read_bytes()==z.read(name)
else:target.write_bytes(z.read(name))
main=zipfile.ZipFile(target)
for item in main.infolist():
 if item.is_dir():continue
 p=root/'source_main'/item.filename
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==main.read(item.filename)
 else:p.write_bytes(main.read(item.filename))
print('Frozen Development sources materialized; no fit/replay/providers invoked.')
'''
 final=json.loads((PRIVATE/'FINAL_ACTUAL_GET_AND_APPEND_ONLY_RECEIPT.json').read_text())
 readme=f'''Capital v5 MAX3 Slot Intelligence — CLOSED / STOP

作成: {now()}
Repo: Iam-2squared/ark-terminal
Branch: capital-state9-vnext-20261004
Instruction basis: {BASIS}
Final actual GET HEAD: {final['actual_result_HEAD']}
Final actual GET tree: {final['actual_result_tree']}

Read repo/docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/REPORT_FINAL-ja.md.
SLOT_INTELLIGENCE_IMPROVED / CAPITAL_V5_IMPROVES.
U5 funded42→50; Net Slot Miss66→58; U10 funded23→26; Net Slot Miss21→19.
Oracle physical maximum U5=104, U10=47; v5 recovery50/104, remaining gap54.
Final Equity ¥1,477,436.15. North Star NOT_REACHED.
Medium31→27; overall loser rate slightly worse; 3rd-slot quality MIXED.

Complete ledgers, training-only tables, evaluator Oracle witnesses, standalone
Fraction/scalar audit, min-cost-flow Oracle audit, plots, 11 checkpoints and
postcommit actual GET receipts are included. Core+supplement150,943 checks,
mismatch0. Frozen Control is ledger-only; Control replay0. Primary policy1,
Primary replay1, independent replay1, full deterministic canary rerun1.
Execution-time synthetic/causal day canaries6. New fit0, new provider0,
retune0, rank/model/Entry/EXIT changes0, orders0, main merge0, force push0.
All Safety flags false; productionReady=false.

58 repeatedly reused Development days / OOF38 are not fresh/OOS.
Protected/Holdout/Fresh/Validation/OOS/Prospective opened0.
Oracle relaxes v4 allocation caps/utilization; it is evaluator-only.
No follow-on tuning in this cycle. Results fixed, STOP.

Original v4 private input archive is unchanged under input_archives.
bootstrap_sources.py reconstructs source_main and the nested frozen v4 ZIP;
it performs no model fit, replay, network access or trading.
Research writers refuse overwriting saved results. Do not rerun main cycles.
MANIFEST_SHA256.json hashes every packaged item except itself.
Terminal post-index GET is delivered privately, avoiding a self-referential
claim about the commit that stores its own future SHA.
'''
 files={}
 for folder in (CODE,OUT,PRIVATE):
  for p in sorted(folder.rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:files[p.relative_to(WORK).as_posix()]=p.read_bytes()
 files['remote_state.json']=(WORK/'remote_state.json').read_bytes();files['start_latest_get.json']=(WORK/'start_latest_get.json').read_bytes()
 files['input_archives/Ark_Capital_v4_Rank_Cutoff_Independent_20261004_PRIVATE.zip']=(WORK/'project_sources/20-Ark_Capital_v4_Rank_Cutoff_Independent_20261004_PRIVATE.zip').read_bytes()
 files['README_FIRST.md']=readme.encode();files['bootstrap_sources.py']=bootstrap.encode();files['REPORT_FINAL-ja.md']=report.read_bytes()
 manifest={'JST':now(),'final_actual_HEAD':final['actual_result_HEAD'],'final_actual_tree':final['actual_result_tree'],'files':{name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in files.items()}}
 files['MANIFEST_SHA256.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
 destination=delivery/NAME;assert not destination.exists()
 with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,data in sorted(files.items()):z.writestr(name,data)
 with zipfile.ZipFile(destination) as z:
  assert z.testzip() is None
  for name,spec in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==spec['sha256']
 save(delivery/'DELIVERY_HASH_RECEIPT.json',{'JST':now(),'final_HEAD':final['actual_result_HEAD'],'final_tree':final['actual_result_tree'],'files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in (destination,report,figure)},'zip_files':len(files),'CRC_and_all_item_hashes':'PASS'})
 print(json.dumps({'ZIP':str(destination),'zip_bytes':destination.stat().st_size,'packaged_files':len(files),'report':str(report),'figure':str(figure),'hash_verification':'PASS'}))
if __name__=='__main__':index() if sys.argv[1]=='index' else package()
