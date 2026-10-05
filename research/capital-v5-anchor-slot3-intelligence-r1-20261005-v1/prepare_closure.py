from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json,argparse,hashlib
from publish_stage import ROOT,PUBLIC,RESEARCH,sha,save
from prepare_main_claim import checkpoint,payload

def prepare(head,tree):
 out=ROOT/'r1_work/evidence';final=ROOT/'r1_work/metrics/final';files=[]
 counts={'controlVerificationReplays':1,'DPrimaryReplays':1,'DRPrimaryReplays':1,'candidatePrimaryReplays':2,
  'DIndependentReconstructionReplays':1,'DRIndependentReconstructionReplays':1,'independentReconstructionReplays':2,
  'newFits':0,'teacherRegeneration':0,'calibration':0,'grid':0,'extraArms':0,'providerRequests':0,'Fresh':0,'Claude':0,
  'orders':0,'mainMerge':0,'forcePush':0,'championUpdates':0,'explicitWorkflowDispatches':0,'blindReruns':0,
  'replaysForEvaluationOrReporting':0,'postOutcomeThresholdRetune':0}
 common=json.loads((out/'START_AUDIT.json').read_text())
 common.update(exact_jst=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),basis_HEAD=head,basis_tree=tree,parent=head,counts=counts,
  strategyParent='710656491be06235901b45c50a8b5cbd714ba4eb',activeCapitalChampion='V5',selectedResearchCandidate=None,
  proposedResearchCandidate=None,selectedCapitalCandidate=None,championUpdated=False)
 decision=json.loads((final/'NONREGRESSION_DECISION.json').read_text())
 gate={arm:{k:v['status'] for k,v in decision['arms'][arm]['gates'].items()} for arm in ('D','DR')}
 assert all(gate[a]['Q11']=='PASS' and gate[a]['E2']==gate[a]['E3']==gate[a]['Q6']=='FAIL' for a in gate)
 independent={}
 for arm in ('D','DR'):
  p=ROOT/f'r1_work/runs/{arm}_INDEPENDENT/INDEPENDENT_RECONSTRUCTION_AUDIT.json';r=json.loads(p.read_text());assert r['mismatch_N']==0
  m=ROOT/f'r1_work/independent/{arm}_FINAL_EXACT_METRIC_COMPARE.json';mr=json.loads(m.read_text());assert mr['mismatch_N']==0 and not mr['primary_audit_pending_gates']
  independent[arm]={'reconstruction':r,'exact_metric_projection':mr}
 audit=save(out/'INDEPENDENT_AUDIT.json',{**common,'status':'PASS','arms':independent,'primary_import_N':0,'market_runs_each':1,'exact_checks_each':219,'mismatch_N':0})
 files.append((audit,PUBLIC+'/'+audit.name))
 closure=save(out/'CLOSURE.json',{**common,'schema':'V5_ANCHOR_SLOT3_R1_CLOSURE_V1','CURRENT_STATE':'R12_CLOSURE_FIXED_STOP',
  'status':'V5_ANCHOR_NO_EFFECT','fixed_STOP':True,'V5_exceeded':False,'execution_complete':True,
  'economic_result':'D and DR exactly equal V5 in all19 windows, allMTM DD, funded IDs/quantity/PnL/quality; strict E2/E3/Q6 FAIL',
  'gates':gate,'paired19':{'D':{'better':0,'equal':19,'worse':0},'DR':{'better':0,'equal':19,'worse':0}},
  'trigger':{'native_planned_slot3_qty_ge100':50,'available_four_heads':50,'unanimous_LOW':0,'D_veto':0,'DR_veto':0,'DR_token':0,'DR_recovery':0},
  'SC01_SC02':'Explicit specification recovery succeeded; economic improvement did not occur',
  'trial_budgets_consumed':True,'next_policy':'Fixed STOP. No automatic D2/DR2, refit, threshold relaxation, replay, orders or Champion update.',
  'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','Fresh_OOS_claim':False,'productionReady':False,
  'future_source_missing_candidate_N':12,'future_source_missing_funded_by_arms_N':0,
  'metadata_repairs':'Report MAX_POSITION_CAP display alias and independent synthetic fixture/source probes repaired with prior failure history retained; no policy/Gate retune',
  'input_manifest_sha256':sha(ROOT/'r1_work/inputs/RUNTIME_INPUT_MANIFEST.json'),
  'report_sha256':sha(final/'REPORT_FINAL-ja.md'),'inference_score_tolerance':'1e-12','money_quantity_tolerance':0})
 files.append((closure,PUBLIC+'/'+closure.name))
 handoff=save(out/'NEXT_WORK_HANDOFF.json',{**common,'CURRENT_STATE':'R12_CLOSURE_FIXED_STOP','status':'V5_ANCHOR_NO_EFFECT',
  'restart_authorized':False,'next_policy':'V5 retained; no next-cycle action is launched by this handoff',
  'measured_bottleneck':'No unanimous-LOW among50 actual planned Slot3 native proposals, hence no veto/token/recovery.',
  'cannot_claim':'No loser discovery or winner recovery contribution was demonstrated.',
  'do_not_repeat':['new fits','same-threshold rescue runs','D2/DR2','automatic provider/Fresh/Claude','main merge','force push','Champion update']})
 files.append((handoff,PUBLIC+'/'+handoff.name))
 for stage,result,nextp in [
  ('R9_INDEPENDENT_RECONSTRUCTION',{'D':'PASS','DR':'PASS','mismatch_N':0,'exact_checks_each':219},'R10 gates from immutable ledgers'),
  ('R10_20SESSION_AND_QUALITY_GATE',{'status':'NO_EFFECT','gates':gate,'noninferiority19_of19':True,'strict_improvement_pass':False},'R11 candidate decision, no tuning'),
  ('R11_WINNER_DECISION',{'selectedResearchCandidate':None,'selectedCapitalCandidate':None,'V5_exceeded':False,'status':'V5_ANCHOR_NO_EFFECT'},'R12 fixed STOP'),
  ('R12_CLOSURE_FIXED_STOP',{'status':'V5_ANCHOR_NO_EFFECT','Champion':'V5','selectedResearchCandidate':None,'championUpdated':False},'No automatic next cycle')]:
  p=checkpoint(stage,'PASS' if stage=='R9_INDEPENDENT_RECONSTRUCTION' else 'FIXED',result,head,tree,primary=2,independent=2,next_policy=nextp)
  c=json.loads(p.read_text());c['counts']=counts
  c['input_hashes']={'runtime_manifest':sha(ROOT/'r1_work/inputs/RUNTIME_INPUT_MANIFEST.json'),'causal_current_four_heads':sha(ROOT/'r1_work/score_certification/CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz'),'ordered_training_references':sha(ROOT/'r1_work/score_certification/TRAINING_REFERENCE_POPULATIONS.json')}
  c['code_hashes']={p.name:sha(p) for p in sorted((ROOT/'r1_work/code').glob('*.py'))}
  save(p,c);files.append((p,PUBLIC+'/checkpoints/'+p.name))
 aliases={
  'V5_OFF_EQUIVALENCE.json':out/'OFF_INDEPENDENT_SAVED_COMPARISON.json',
  'SCORE_LINEAGE_AND_COVERAGE.json':out/'SCORE_REFERENCE_CERTIFICATION.json',
  'PRE_MAIN_INDEPENDENT_AUDIT.json':out/'PRE_MAIN_ALL_CANDIDATE_AUDIT.json'}
 for name,p in aliases.items():
  target=out/name;target.write_bytes(p.read_bytes());files.append((target,PUBLIC+'/'+name))
 authority=save(out/'AUTHORITY_MANIFEST.json',{**common,'frozen_authorities':json.loads((out/'START_AUDIT.json').read_text())['frozen_authorities'],
  'strategy_parent':'710656491be06235901b45c50a8b5cbd714ba4eb','transport_manifest_sha256':sha(ROOT/'r1_work/inputs/INPUT_TRANSPORT_MANIFEST.json'),
  'runtime_input_manifest_sha256':sha(ROOT/'r1_work/inputs/RUNTIME_INPUT_MANIFEST.json'),
  'remote_code_manifest_sha256':sha(ROOT/'r1_work/authority_code/REMOTE_CODE_MANIFEST.json'),
  'prior_reused_audit_sha256':sha(ROOT/'audit_input/INPUT_AUDIT_SUMMARY.json')})
 files.append((authority,PUBLIC+'/'+authority.name))
 dnr=save(out/'DO_NOT_REPEAT.json',{**common,'fixed_STOP':True,'fits_and_extra_trials_permitted':0,'all_market_budgets_consumed':True,
  'auto_next_cycle':False,'Champion':'V5','D_DR_policy_retune_permitted':False})
 files.append((dnr,PUBLIC+'/'+dnr.name))
 for p in sorted(final.iterdir()):
  if p.is_file():files.append((p,PUBLIC+'/'+p.name))
 for p in sorted((ROOT/'r1_work/metrics/supplement').iterdir()):
  if p.is_file() and p.suffix!='.gz':files.append((p,PUBLIC+'/diagnostics/'+p.name))
 p=out/'CAUSAL_TRIGGER_DIAGNOSTIC.json';files.append((p,PUBLIC+'/'+p.name))
 extras=[ROOT/'r1_work/INDEPENDENT_ACTUAL_GET_RECEIPT.json',ROOT/'r1_work/metrics/REPORT_REASON_ENCODING_REPAIR.json']
 for p in extras:
  if p.exists():files.append((p,PUBLIC+'/receipts/'+p.name))
 for p in sorted((ROOT/'r1_work/spec_review').glob('*FINAL*json')):
  files.append((p,PUBLIC+'/reviews/'+p.name))
 for name in ('PRIMARY_REPLAY_BUDGET_AUDIT.json','SOURCE_REVIEW_HASH_REFERENCE_SCOPE_RECEIPT.json','CAUSAL_SOURCE_REVIEW_PRE_CANARY_SNAPSHOT.json'):
  p=ROOT/'r1_work/spec_review'/name
  if p.exists():files.append((p,PUBLIC+'/reviews/'+p.name))
 for arm in ('D','DR'):
  for name in ('STARTED.json','COMPLETE.json','INDEPENDENT_RECONSTRUCTION_AUDIT.json'):
   p=ROOT/f'r1_work/runs/{arm}_INDEPENDENT'/name;files.append((p,PUBLIC+f'/receipts/{arm}_INDEPENDENT_'+name))
  p=ROOT/f'r1_work/independent/{arm}_FINAL_EXACT_METRIC_COMPARE.json';files.append((p,PUBLIC+'/'+p.name))
 for name in ('metrics_exact.py','report_r1.py','evaluate_r1.py','plot_r1.py','compare_independent_metrics.py'):
  p=ROOT/'r1_work/code'/name
  if p.exists():files.append((p,RESEARCH+'/'+name))
 for name in ('score_distribution_diagnostic.py','prepare_closure.py'):
  p=ROOT/'r1_work'/name;files.append((p,RESEARCH+'/'+name))
 log=[]
 for p in sorted((out/'checkpoints').glob('*.json')):
  a=json.loads(p.read_text());log.append({'checkpoint':p.name,'sha256':sha(p),'exact_JST':a.get('exact_jst'),'basis_HEAD':a.get('basis_HEAD'),'basis_tree':a.get('basis_tree'),'counts':a.get('counts'),'result':a.get('result'),'Safety':a.get('Safety'),'next_policy':a.get('next_policy')})
 p=out/'WORK_STATUS_LOG.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in log));files.append((p,PUBLIC+'/'+p.name))
 private=save(out/'PRIVATE_DELIVERY_MANIFEST_PREPACK.json',{'schema':'R1_PRIVATE_DELIVERY_PREPACK_V1','basis_HEAD':head,'basis_tree':tree,
  'files':{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'r1_work').rglob('*')) if p.is_file() and 'WRITE_PAYLOAD' not in p.name and '__pycache__' not in p.parts and p.name!='PRIVATE_DELIVERY_MANIFEST_PREPACK.json'},
  'delivery_final_hash_and_ZIP_GET':'Appended after deterministic packing; not predicted in this commit','market_runs_after_closure':0})
 files.append((private,PUBLIC+'/'+private.name))
 payload(files,ROOT/'r1_work/CLOSURE_WRITE_PAYLOAD.json')

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--head',required=True);ap.add_argument('--tree',required=True);a=ap.parse_args();prepare(a.head,a.tree)
