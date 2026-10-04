"""Read controlling closed Evidence; recover only explicitly pinned input bytes."""
from control import *
import sys,zipfile,io,subprocess
RANK=ROOT/'docs/evidence/capital-rank-bigwinner-vnext-20261005-v1'
V5=ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1'
V6=ROOT/'docs/evidence/capital-v6-counterfactual-slot-value-20261004-v1'
def start():
 assert not subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD'],cwd=ROOT,text=True).split('capital-v7-rank-native-max3-20261005-v1')[1:] ,'EXISTING_CYCLE_STOP'
 tree=subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD'],cwd=ROOT,text=True).splitlines()
 assert not [p for p in tree if p.endswith('AGENTS.md')]
 files=['SELECTED_RANK_CONTRACT.json','NEXT_WORK_HANDOFF.json','CLOSURE.json','COMMON_EVAL_MASK_FREEZE.json','TEACHER_CONTRACT_AUDIT.json','STAGE_A_RESULT.json','INDEPENDENT_AUDIT.json']
 cc=read(RANK/files[0]);assert sha(RANK/files[0])=='6e8687f36f6f60fc9e9921e1ef29e0520cf1ea8bc01f14386963f1020b209518'
 assert cc['status']=='RANK_VNEXT_STRONG' and cc['selectedRankCandidate']=='EXISTING_MOVE_P5' and cc['score_field']=='pP'
 assert read(V6/'CLOSURE.json')['CURRENT_STATE']=='CAPITAL_V6_RECOVERY_D11_CLOSED_FIXED_STOP'
 inventory={'exact_jst':now(),'start_HEAD':read(WORK/'latest_basis.json')['HEAD'],'start_tree':read(WORK/'latest_basis.json')['tree'],'instructions':['MASTER_PROMPT.md','explicit user branch overrides generic start-main rule'],'AGENTS_found':[],'rank_authority':{f:sha(RANK/f) for f in files},'v5_authority':{f:sha(V5/f) for f in ('CLOSURE.json','MAIN_REPLAY_RESULT.json','SLOT_QUALITY_AND_RESERVATION.json','OPPORTUNITY_AND_ORACLE_GAP.json','INDEPENDENT_AUDIT.json','SOURCE_HASHES.json')},'v6_authority':{f:sha(V6/f) for f in ('CLOSURE.json','SCORE_ACTION_FREEZE.json')},'freeze':['Selector','Entry','EXIT','Rank vNext pP ordering'],'no_existing_v7_cycle':True,'no_prior_completed_fit_or_replay_rerun':True,'Safety':SAFETY}
 save(OUT/'START_LATEST_AUDIT.json',inventory)
 checkpoint('D0_START_LATEST_AUDIT','LATEST_AUDITED',['branch actual GET','tree actual GET','instructions inventory','no prior v7 cycle'],inventory,'Freeze Rank/v5/v6 read-only authority; no fits/replays')
def authority():
 v5=read(V5/'MAIN_REPLAY_RESULT.json');slot=read(V5/'SLOT_QUALITY_AND_RESERVATION.json');opp=read(V5/'OPPORTUNITY_AND_ORACLE_GAP.json')
 out={'exact_jst':now(),'selectedRankCandidate':'EXISTING_MOVE_P5','ordering':['pP DESC','Entry timestamp ASC','symbol ASC'],'rank_contract_sha256':sha(RANK/'SELECTED_RANK_CONTRACT.json'),'v5_economics_saved':v5,'v5_slot_quality_saved':slot,'v5_opportunity_saved':opp,'v6_closure_saved':read(V6/'CLOSURE.json'),'rank_refit':0,'Control_replay':0,'v6_replay':0,'capital_benchmark':'V5_FROZEN_REFERENCE','pP_calibrated_true_probability_claim':False,'Safety':SAFETY}
 save(OUT/'RANK_V5_V6_FREEZE.json',out)
 checkpoint('D1_RANK_VNEXT_AND_V5_V6_FREEZE','AUTHORITIES_FROZEN',['Rank strong closure','v5 benchmark','v6 negative closed'],{'Rank':'EXISTING_MOVE_P5','v5_funded_U5':50,'v5_funded_U10':26,'v6_models_reused':False},'Verify existing private pack and pinned upstream input bytes')
def inputs():
 checks=[]
 def copybytes(target,data,expected,origin):
  assert hashlib.sha256(data).hexdigest()==expected,('HASH_MISMATCH',origin)
  target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(data)
  checks.append({'path':str(target.relative_to(WORK)),'sha256':expected,'origin':origin,'exact_byte_identity':True})
 pack=ROOT.parent/'deliverables/Ark_Capital_BigWinner_Rank_vNext_20261005_PRIVATE.zip'
 delivery=read(RANK/'PRIVATE_DELIVERY_RECEIPT.json')
 with zipfile.ZipFile(pack) as z:
  manifest=json.loads(z.read('MANIFEST.json'));save(WORK/'PACK_MANIFEST_READ.json',manifest)
  # The archive is a byte transport; GitHub pinned contracts remain authority.
  for name in ['inputs/movement/MOVE_P5_SCORE_STREAM.jsonl.gz','inputs/v4/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz','private/COMMON_EVAL_MASK.jsonl.gz','private/TEACHER_SUPPORT_LEDGER.jsonl.gz']+[f'inputs/movement/models/MOVE_P_BLOCK_{b:02}.json' for b in range(1,9)]:
   data=z.read(name);expected=manifest['files'][name]['sha256'] if isinstance(manifest['files'],dict) else next(x['sha256'] for x in manifest['files'] if x['path']==name)
   copybytes(WORK/name,data,expected,str(pack.name)+'!'+name)
 # Original saved runtime/teacher/execution byte pins, never a provider request.
 for c in read(RANK/'INPUT_BYTE_RECOVERY.json')['checks']:
  src=ROOT.parent/c['local_relative'];dest=None
  if c['member']=='capital_v2_private/RUNTIME_CAUSAL.jsonl.gz':dest=INPUT/'movement/RUNTIME_CAUSAL.jsonl.gz'
  elif c['member'].endswith('CORE_RUNTIME_CAUSAL.jsonl.gz'):dest=INPUT/'core/CORE_RUNTIME_CAUSAL.jsonl.gz'
  elif c['member'].endswith('MARKET_EXECUTION_BOOK_V2.jsonl.gz'):dest=INPUT/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz'
  elif c['member']=='inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz':dest=INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz'
  elif c['member'].endswith('P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'):dest=INPUT/'entry/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'
  if dest:copybytes(dest,src.read_bytes(),c['sha256'],c['member'])
 outer=ROOT.parent/'project_sources/20-Ark_Capital_v4_Rank_Cutoff_Independent_20261004_PRIVATE.zip'
 with zipfile.ZipFile(outer) as z:
  nested=z.read('deliverables/Ark_Capital_MAX3_Upward_Staircase_v4_20261004_PRIVATE.zip')
 with zipfile.ZipFile(io.BytesIO(nested)) as z:
  pin=read(V5/'SOURCE_HASHES.json')
  for h in (2,3,5):
   for b in range(1,9):
    member=f'capital_staircase_v4_private/models/H{h}_BLOCK_{b:02}.json'
    copybytes(INPUT/'current/models'/Path(member).name,z.read(member),pin[member],str(outer.name)+'!'+member)
 contract=read(RANK/'SELECTED_RANK_CONTRACT.json');assert sha(INPUT/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz')==contract['score_stream_sha256']
 for name,value in contract['model_sha256'].items():assert sha(INPUT/'movement/models'/name)==value
 mask=rows(PRIVATE/'COMMON_EVAL_MASK.jsonl.gz');print('mask sample',mask[0],flush=True)
 save(OUT/'INPUT_BYTE_AND_SOURCE_FREEZE.json',{'exact_jst':now(),'checks':checks,'mismatch_N':0,'pack_sha256':sha(pack),'pack_manifest_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),'original_manifest_byte_sha256':hashlib.sha256(zipfile.ZipFile(pack).read('MANIFEST.json')).hexdigest(),'pack_manifest':manifest,'protected_open':0,'provider_request':0,'teacher_regeneration':0,'source_boundary':'Inherited complete Development source and bar-close availability; historical actual arrival UNKNOWN, never upgraded to measured PIT.'})
 checkpoint('D2_INPUT_BYTE_AND_SOURCE_FREEZE','PINNED_BYTES_FROZEN',['private pack','score/models','current models','execution/runtime/teacher original bytes'],{'files':len(checks),'hash_mismatch':0},'Precommit mapping, policies and Oracle before outcome-based solver results')
if __name__=='__main__':globals()[sys.argv[1]]()
