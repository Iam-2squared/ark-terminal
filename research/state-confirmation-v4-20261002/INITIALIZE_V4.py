from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, hashlib, shutil, zipfile

R=Path(__file__).resolve().parent
P=Path('/workspace/scratch/a1e749e0bd6c/state_predictiveness_v3_reversal_20261002_v1')
V2=P.parent/'state_predictiveness_v2_nextstate_20261002_v1'
ZIP=R.parent/'deliverables/Ark_Terminal_State_Predictiveness_V3_COMPLETE_20261002.zip'
PARENT='c0e6968292f1a79c089a267d3f3a72cc1f7b5ead'
BRANCH='state-predictiveness-v4-confirmation-20261002-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now(timezone(timedelta(hours=9))).isoformat()
def save(n,x):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')

assert sha(ZIP)=='c04a71f4180474c17b6ab7e6abe6dfc701ac28cb917e36ce6dff1c616eaa27d2','PARENT_COMPLETE_IDENTITY'
with zipfile.ZipFile(ZIP) as z:
 assert z.testzip() is None,'PARENT_ZIP_CRC'
assert not (R/'PREDICTIVENESS_V4_PRECOMMIT.json').exists(),'NO_PRECOMMIT_OVERWRITE'
inherited=['00_README.txt','REPORT-ja.md','FINAL_RECEIPT.json','NEXT_STAGE_HANDOFF.md','PREDICTIVENESS_V3_REVERSAL_CONTRACT.md','PREDICTIVENESS_V3_REVERSAL_PRECOMMIT.json','DATA_SCOPE_V3.json','SPLIT_REALIZED_V3.json','REVERSAL_METRICS_AGGREGATE.csv','UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE.csv','CALIBRATION_METRICS.csv','CALIBRATION_BUCKETS.csv','R0_R1_R2_R3_R4_INCREMENTAL.csv','NEGATIVE_CONTROL_V3.csv','SHIFT60_STRESS_V3.csv','INDEPENDENT_AUDIT_V3.json','BUDGET_FINAL_V3.json','EXPOSURE_APPEND_ONLY_DELTA.json','FEATURE_SCHEMA_V3.json','REVERSAL_TARGET_SCHEMA.json','DATASET_MANIFEST.json']+['REVERSAL_PATH_ANATOMY_LENGTH'+str(k)+'.csv' for k in range(1,5)]
receipts=[]
for n in inherited:
 assert (P/n).is_file(),n
 dst=R/'INHERITED_V3'/n;dst.parent.mkdir(exist_ok=True);shutil.copyfile(P/n,dst)
 receipts.append({'file':n,'SHA256':sha(dst),'bytes':dst.stat().st_size,'parent_unchanged':True})
for n in ['FEATURE_SCHEMA_V3.json','REVERSAL_TARGET_SCHEMA.json']:
 shutil.copyfile(P/n,R/n.replace('_V3','_V4'))
shutil.copytree(P/'FROZEN_INPUTS',R/'FROZEN_INPUTS',dirs_exist_ok=True)
identity=json.loads((P/'FROZEN_IDENTITY_RECEIPT.json').read_text())
for check in identity['checks']:
 fp=R/check['member'];assert sha(fp)==check['expected_SHA256'],'FROZEN_IDENTITY'
identity.update(JST=now(),V3_receipt_SHA256=sha(P/'FROZEN_IDENTITY_RECEIPT.json'),family_mapping_changes=0,reversal_target_changes=0)
save('FROZEN_IDENTITY_RECEIPT.json',identity)
scope2=json.loads((V2/'DATA_SCOPE_V2.json').read_text());scope3=json.loads((P/'DATA_SCOPE_V3.json').read_text())
exposed=sorted(set(scope3['V1_V2_exposed_dates'])|set(scope3['new_evaluation_dates']))
links=[x for x in scope2['authorized_current_links'] if x['date'] not in exposed]
assert len(links)==106 and [x['date'] for x in links]==sorted(x['date'] for x in links),'FIXED_LINK_ORDER'
dates=[x['date'] for x in links];warmup=dates[:5];rest=dates[5:];q,n=divmod(len(rest),3);blocks=[];i=0
for k in range(3):
 count=q+(k<n);blocks.append(rest[i:i+count]);i+=count
scope={'document':'WORK_STATE_PREDICTIVENESS_V4_CONFIRMATION_20261002_V1','JST':now(),'authorization':'Current user V4 sections2/3: consume still-unacquired approved Development in original fixed order, never outcome-driven replacement','scope':'DEVELOPMENT_ONLY','authorized_Development_days':scope2['authorized_Development_days'],'authorized_current_links':scope2['authorized_current_links'],'blocked_days':scope2['blocked_days'],'V1_V2_V3_exposed_dates':exposed,'new_acquisition_links':links,'new_evaluation_dates':dates,'max_new_proposals':318,'max_completed_pairs':408,'metadata_selection':scope2['metadata_selection'],'metadata_selection_source_SHA256':sha(V2/'BUILD_EXPANSION.py'),'metadata_only_factor_continuity_before_raw':True,'future_result_selection':False,'old_72_proposals_classified':72,'old_65_acquired_reused':65,'old_7_conclusive_unavailable_retained_no_retry':7,'parent_scope_SHA256':sha(P/'DATA_SCOPE_V3.json'),'approved_V2_scope_SHA256':sha(V2/'DATA_SCOPE_V2.json'),'provider_authority':scope3['provider_authority'],'provider_contract_basis':scope2['provider_contract_basis'],'exclusion_identity_scope':scope3['exclusion_identity_scope'],'Holdout':0,'Protected':0,'Fresh_OOS':0,'Prospective':0}
save('DATA_SCOPE_V4.json',scope)
save('SPLIT_PLAN_V4.json',{'JST':now(),'mode':'V4_NEW_DEV_EVAL','warmup_new_dates':warmup,'fixed_three_blocks':blocks,'old_exposed_dates_training_only':exposed,'train_rule':'all acquired dates strictly earlier than fixed test-block start; target end strictly earlier than test_start','initial_train_date_min':5,'random_row_split':False,'empty_test_dates_retained':True,'availability_or_result_refolding':False,'exposed_diagnostic_fallback':False,'minimum_evaluable_dates':8,'preferred_evaluable_dates':12,'minimum_folds':2,'preferred_folds':3})
priorbudget=json.loads((P/'BUDGET_FINAL_V3.json').read_text())
caps={'new_proposals':318,'completed_pairs':408,'new_frozen_steps':110000,'provider_HTTP_requests':2200,'isolated_Actions_runs':2,'Actions_fanout':1,'fit_operations':1200,'outer_folds':3,'model_families':5,'tasks':4,'controls':3,'strengths':3,'bootstrap_generated_vectors':1000,'independent_new_draws':0,'independent_new_fits':0}
save('BUDGET_START_V4.json',{'JST':now(),'finite_caps':caps,'inherited_budget_SHA256':sha(P/'BUDGET_FINAL_V3.json'),'inherited_budget':priorbudget,'no_reset':True,'V1_3000_cap1000_breach_retained':True,'delta_before_start':{'new_provider_HTTP':0,'new_frozen_steps':0,'new_labels':0,'fits':0,'bootstrap_vectors':0,'Actions_runs':0,'GitHub_connector_reads':5,'GitHub_connector_writes':1},'connector_HTTP_fanout':'UNKNOWN; actual connector invocation counts separate'})
save('INHERITANCE_V4.json',{'JST':now(),'parent_status':'STATE_REVERSAL_PREDICTIVENESS_LIMITED_SAMPLE','parent_actual_GET_HEAD':PARENT,'parent_actual_GET_tree':'d4f520ca109e853c686dbefaa3e280d1a0be9cbd','dedicated_branch':BRANCH,'V3_COMPLETE_SHA256':sha(ZIP),'V3_COMPLETE_bytes':ZIP.stat().st_size,'V3_COMPLETE_CRC_PASS':True,'files':receipts,'V3_original_results_overwritten':0,'old16FAIL':16,'old88workflow_incident':88,'old_V2_fit_ledger_gap':4,'new_labels_seen':0})

contract='''# State Predictiveness V4 Confirmation Contract

Document: WORK_STATE_PREDICTIVENESS_V4_CONFIRMATION_20261002_V1. Fixed before new V4 evaluation labels, fits, and bootstrap. V3 COMPLETE and actual GitHub HEAD are inherited without overwriting. State9, Path, profile, M0, family mapping and primary reversal target changes: zero.

## Scope and acquisition

DATA_SCOPE_V4 fixes 106 unexposed current/previous links from the original 142 approved links, in original chronological order. All 36 V1/V2/V3 exposure dates are acknowledged as exposed and training-only. Reuse 90 acquired parent pairs; retain the original seven conclusive unavailable proposals without a raw retry. No protected or new unapproved date. Per link use the identical V2 paired dated-master compatibility (Code/Mkt/CoName/ProdCat), current/previous exclusion pairs, lexically sorted SHA256 of current master metadata excluding _source, first three factor-compatible candidates (AdjFactor exact1 and ExRT null on both dates). This metadata/factor filtering may skip factor-incompatible codes BEFORE any raw prices; no refill based on raw, U, State, labels, prediction or outcomes. Fix the complete acquisition universe before any minute raw request. Master/provider/date failure gets an explicit record and subsequent approved links continue; hard auth/rate/cap refusal stops only external acquisition without bypass. Every selected proposal gets ACQUIRED/RAW_UNAVAILABLE/U_UNAVAILABLE/FACTOR_UNAVAILABLE/DATE_MASTER_UNAVAILABLE/INVALID_SESSION/PROVIDER_FAILURE/OTHER_EXPLICIT_REASON. Daily fields except factor metadata never enter features. Temporary raw uses exact lexemes and source hashes, same frozen M0/State/Path kernel, current-slot worker only, purged, never public exported. Historical known_at UNKNOWN remains UNKNOWN; operational bar-end availability is an assumption, not historical attestation.

## Inherited target and features

The exact byte-identical REVERSAL_TARGET_SCHEMA and FEATURE_SCHEMA_V3 are inherited as V4 files. INHERITED_V3/PREDICTIVENESS_V3_REVERSAL_CONTRACT.md sections Anchor/continuity, Primary ordered scan, Secondary targets, Causal features, and Calibration are normative unchanged. Primary UP_CONTEXT is RISE/SHARP_RISE/PULLBACK/RISE_STOP, next30 scheduled tradable slots, first genuine down-context transition versus up continuation confirmation; provisional Range/Stop resolves only after full observable horizon; null/gap/reset/session break censors. UP_CONTINUE, DOWN_REVERSAL, RANGE_OR_STOP, NO_DECISION_WITHIN30 in fixed order; UNAVAILABLE excluded, never class5. No price-return interpretation. Anatomy is current prefix plus up to four completed prior runs, lengths1–4 oldest-to-current, zero semantic changes. Secondary MOTION_REVERSAL and both nine-State targets unchanged.

R0 weighted prior; R1 current Primary lookup pseudo-count10; R2 exact Full State9; R3 R2+standard Path; R4 R2+reversal anatomy. Date-equal/security-session-equal weights, train-only encoder, ridge one-hot strengths [.01,.1,1], unpenalized intercept, raw score clip1e-12 then normalization. Last usable train date inner validation; earlier dates inner train. Alpha minimizes inner uncalibrated logloss, tie larger alpha. Temperature grid [.5,.75,1,1.25,1.5,2] on the same train-only validation, ties closest1 then largerT. Fallback alpha .1/T1 only if inner data unavailable, reported. No outer labels used for encoder, alpha, temperature. Both uncalibrated and calibrated OOF fixed and saved; calibrated primary, no retrospective switch to uncalibrated. No new family/search/threshold.

## Split and metrics

SPLIT_PLAN_V4 fixes first five new dates as initial warmup, remaining101 in three chronological blocks 34/34/33. All available earlier exposed/new dates may train; test dates are strictly new, held-out per fold within Development, not a separately protected Holdout. Empty dates/folds retained; no label-driven refolding or exposed fallback. Train target end < test_start, no random row split. Features before new labels, timestamp max <= anchor.

Save actual support, precision/recall/F1 including all registered zero-support states, accuracy/balanced accuracy/macro F1, row-count and date-equal logloss and sum-multiclass Brier, top-label ECE ten fixed buckets, per-class reliability, DOWN probability vs actual DOWN rate. Undefined denominators NA (macro fixed-class aggregate uses0, disclosed). Dangerous FP is actual DOWN among argmax predicted UP, not DOWN recall. Report overall/each fold/date/security/current Primary/path length1–4, numerator/denominator/rate/date-cluster CI. V3 risk17.70/12.78/14.26/13.86% compared without claiming identical cohorts.

## Controls and global bootstrap

TRUE NULL: deterministic whole-label/provenance permutation within task/date/security/session, SHA256 seed prefix2026100402; features and folds fixed. Singleton/identity permutations disclosed. SHIFT60 exact inherited continuous bridge and targets, dependence/regime stress not alone proof of leak. REAL/control comparisons are matched keys. User V4 section12 explicitly strengthens V3 warning-only rule: for R2–R4 primary calibrated CONTEXT_REVERSAL, TRUE_NULL date-equal logloss <= matched REAL (+1e-12 numerical equality), OR TRUE_NULL positive logloss gain versus R1 >=90% of positive REAL gain, is the predeclared equivalent-or-better control integrity failure and BLOCKED_V4_INTEGRITY. This statistical control failure is NOT claimed as proven future leakage; secondary or SHIFT60 warnings alone are not integrity proof. No rule relaxation after results.

Generate exactly1000 global date-cluster vectors once, seed2026100403 across the101 fixed outer test dates including empty dates. Reuse same indices for all models/metrics/subsets; empty denominators yield NA, never redraw. Independent checker draws0/fits0. Percentile95% descriptive intervals; inherited adjusted lower bound tail .05/(2*6) for six candidate class precision claims. Repeated anchors overlap, clusters are dates rather than independent trades.

## Promotion gates and final status

Primary baseline R2. Integrity and independent audit PASS, core OOF dates>=8 and folds>=2, actual DOWN>=100 and UP>=100, R2 dangerous FP lower than R1 with positive95% date-cluster lower improvement, and at least one of DOWN F1/UP F1/macro F1 improves (positive adjusted lower bound, improvement in >=2folds). Candidate predicted support>=100 for the class claim. Date-equal calibrated logloss AND Brier <=1.05 times R1, and DOWN recall not lower by>.02; these inherit V3 probability/recall guard rather than overlooking calibration. TRUE_NULL must pass. Gross positive reduction in dangerous errors and class-correctness gains each maximum single-date/security share<=.5; no one-day or one-security promotion. No result-driven change. R3/R4 must also satisfy the same incremental gates versus R2. Anatomy descriptive support N>=100/dates>=8/securities>=3; never an Entry/EXIT rule. Record every failed gate.

A STATE_REVERSAL_INTELLIGENCE_DEV_CANDIDATE_READY_FOR_ENTRY_RESEARCH only qualifying model(s); B STATE_REVERSAL_INTELLIGENCE_MEASURED_NO_PROMOTABLE_SIGNAL adequate measured sample no promotion; C STATE_REVERSAL_INTELLIGENCE_LIMITED_SAMPLE integrityPASS but core support/date/fold insufficient; D BLOCKED_V4_INTEGRITY leakage/contamination/precommit/unreconciled mismatch/compute breach or above user-explicit control integrity failure. Low accuracy or poor calibration alone never D. A authorizes handoff to Hybrid Entry research only, no automatic Entry execution.

## Budget, audit, boundaries and delivery

BUDGET_START_V4 finite caps:318 new proposals,408 completed pairs,110000 new frozen steps,2200 actual provider HTTP,2 isolated Actions runs/fanout1,1200 append-before-fit operations,4tasks/5models/3controls/3folds,1000 global generated vectors exactly once. Preserve V1 3000/cap1000 breach, V2 four-fit ledger gap, V3 limits/history, old16FAIL/88workflow incident; no reset or invented zero outside consumption. Independent recomputation from saved features/targets/splits/OOF/fits/buckets/anatomy/controls/draws uses separate logic and no helper imports/newfits/draws/kernel reruns. Only mismatch-local repair, no full semantic re-audit. Explicit local implementation repairs may correct failures without altering targets/features/model math or rerunning successful fits; record every attempt.

Dedicated branch only, no main merge/forcepush. C0/C1/C2/C3/C4/C5/C6 include JST, status, parent/current actual HEAD, contract and scope hashes, next action. Public repo code/contracts/aggregate only; private feature/trace/label/OOF/fit files in one complete ZIP including original parent ZIP. Holdout/Protected/Fresh/OOS/Prospective/Entry/EXIT/profit/Capital/Portfolio/order/externalAI=0. Deliver one ZIP regardless size now and future; graphs are static validated PNG/SVG in ZIP, never source/model modifications.
'''
(R/'PREDICTIVENESS_V4_CONTRACT.md').write_text(contract)
frozen=['PREDICTIVENESS_V4_CONTRACT.md','DATA_SCOPE_V4.json','SPLIT_PLAN_V4.json','FEATURE_SCHEMA_V4.json','REVERSAL_TARGET_SCHEMA.json','FROZEN_IDENTITY_RECEIPT.json','BUDGET_START_V4.json','INHERITANCE_V4.json']
save('PREDICTIVENESS_V4_PRECOMMIT.json',{'JST':now(),'document':scope['document'],'hashes':{n:sha(R/n) for n in frozen},'new_evaluation_labels_seen':0,'new_model_fits':0,'bootstrap_generated':0,'post_result_changes_allowed':False,'model_math_source_SHA256':sha(P/'FIT_V3.py'),'target_anatomy_source_SHA256':sha(P/'BUILD_V3.py'),'calibration_method':'inherited train-only temperature grid','TRUE_NULL_user_V4_strict_rule_fixed':True,'null_seed_prefix':2026100402,'bootstrap_seed':2026100403})
for c,status,nxt in [('C0','INHERITANCE_VERIFIED','C2 contract fixed then approved Development acquisition'),('C2','V4_PRECOMMIT_FIXED_BEFORE_NEW_LABELS','Push isolated fixed-scope acquisition and prepare evaluation lane')]:
 save('CHECKPOINTS/'+c+'.json',{'JST':now(),'current_status':status,'parent_HEAD':PARENT,'current_HEAD':PARENT,'contract_SHA256':sha(R/'PREDICTIVENESS_V4_CONTRACT.md'),'data_scope_SHA256':sha(R/'DATA_SCOPE_V4.json'),'precommit_SHA256':sha(R/'PREDICTIVENESS_V4_PRECOMMIT.json'),'next_action':nxt})
shutil.copytree(P/'runner',R/'runner',ignore=shutil.ignore_patterns('__pycache__','config.json','export_completion.py','ACQUISITION_COMPLETION_PRECOMMIT.json'))
cfg=json.loads((P/'runner/config.json').read_text());cfg['acquisition_session_scope']=links;cfg['maxrequests']=2200
save('runner/config.json',cfg)
for n in frozen+['PREDICTIVENESS_V4_PRECOMMIT.json']:
 shutil.copyfile(R/n,R/'runner'/n)
save('runner/ACQUISITION_EXPANSION_PRECOMMIT.json',{'JST':now(),'date_links':links,'selection_source_SHA256':sha(V2/'BUILD_EXPANSION.py'),'metadata_only_selection':True,'proposal_cap':318,'steps_cap':110000,'raw_requests_before_universe_fixed':0,'V4_precommit_SHA256':sha(R/'PREDICTIVENESS_V4_PRECOMMIT.json'),'contract_SHA256':sha(R/'PREDICTIVENESS_V4_CONTRACT.md')})
save('DELIVERY_PREFERENCE.json',{'language':'ja','one_complete_zip':True,'split_archives':False,'size_priority':'completeness over size','applies_future_deliveries':True,'source':'User request: 一つのzipにして。容量多くてもいいから。これからもそうして'})
print(json.dumps({'phase':'C0_C2','new_links':len(links),'blocks':[len(x) for x in blocks],'old_exposed_dates':len(exposed),'contract_SHA256':sha(R/'PREDICTIVENESS_V4_CONTRACT.md'),'scope_SHA256':sha(R/'DATA_SCOPE_V4.json'),'precommit_SHA256':sha(R/'PREDICTIVENESS_V4_PRECOMMIT.json')}))
