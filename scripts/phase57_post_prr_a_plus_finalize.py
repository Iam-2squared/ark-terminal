"""Closure metadata for source-limited, append-only Phase A+ cycle."""
from __future__ import annotations
import datetime,hashlib,json,sys
from pathlib import Path
from scripts.phase57_post_prr_a_plus import OUT,BASE,ROOT,sha,write

def main():
 now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec='seconds')
 decisions={
  'minimumSupport':None,'unknownOutcomeTolerance':None,'tailTolerance':None,'interventionThreshold':None,'modelFamily':None,'fitBudget':None,'calibrationBudget':None,'stage1RegenerationBudget':None,'policyReplayBudget':None,'capitalReplayBudget':None,
  'scopeAllIntentVersusDefensive':'UNRESOLVED; E provisional IM370/R1339, DEFENSIVE E IM72/R186; do not choose by observed Δ',
  'sameMinuteOrdering':'UNRESOLVED_10_ROWS','unknownALLOWPrice':'UNMEASURABLE_80_PER_ARM_NO_NEW_RETRY',
  'teacherMissingness':'UNRESOLVED_MECHANISM_FOR_MODELING; exact reference absent after decision',
  'StateSignalAvailability':'BLOCKED_ROW_VALUES_KNOWNAT','nestedLineage':'UNPROVEN','futureIndependentEvaluation':'NOT_AUTHORIZED'}
 write('UNRESOLVED_DECISIONS.json',{'schema':'phase57-a-plus-decisions-v1','decisions':decisions,'postExposure':True,'noOutcomeTunedThreshold':True})
 write('NEXT_EXPERIMENT_PRECOMMIT_DRAFT.json',{'schema':'phase57-a-plus-next-precommit-draft-v1','status':'PROPOSED_NOT_AUTHORIZED_DRAFT_ONLY_NO_LAUNCH','question':'At CCMG first SELL_INTENT, can causal State/Signal distinguish ΔNetPP versus frozen R50?','riskSet':'I; E runtime independent; K outcome-side only','actions':{'ALLOW':'existing CCMG first-sale contract','ABSTAIN':'one-shot permanent frozen R50 delegation'},'primaryTeacher':'ΔNetPP','secondaryTeacher':'ΔJPY','inputSchemaStatus':'BLOCKED_SOURCE','nestedScoreStatus':'NESTED_LINEAGE_UNPROVEN','split':'session-forward with label maturity/purge proof','comparators':['frozen R50','frozen PRR','future candidate unimplemented'],'separateGates':['total JPY','mean Net%','winner 5–10 and ≥10','missingness','tail','session','cost stress','Capital later'],'unresolved':decisions,'budgetFormula':'B_stage1_if_required + B_stage2 + B_calibration + B_policy_replay + B_capital_replay; all terms null','experimentAuthorized':False,'selectedDevelopment':None,'adaptiveDevelopmentOnly':True,'productionReady':False})
 source=OUT/'UPSTREAM_STATIC_CODE_AUDIT.json'
 requirements={
 'R01':('VERIFIED_COMPLETE','START_AUDIT.json / SOURCE_MANIFEST.json / A_PLUS_PRECOMMIT.json'),
 'R02':('VERIFIED_COMPLETE','SCHEMA_MAP.json / REQUIREMENTS_MATRIX.json'),
 'R03':('VERIFIED_COMPLETE','INTENT_CENSUS.json / INTENT_UNIVERSE_ROWS.jsonl.gz / MISSINGNESS_AUDIT.json / UNKNOWN_FIRST_INTENT_ROWS.jsonl.gz'),
 'R04':('PARTIAL','INTENT_ORDER_AND_BRANCH_EQUIVALENCE.json; static contract yes, full row witness and ties unresolved'),
 'R05':('VERIFIED_COMPLETE','INVENTORY_FREEZE.json / ANALYSIS_SPEC.json (before new State association)'),
 'R06':('VERIFIED_COMPLETE','ACCOUNTING_AND_PRIMARY_DECOMPOSITION.json'),
 'R07':('PARTIAL','FINE_BUCKET_ROUTE_RESULTS.json.gz; initial/replacement original label not retrieved'),
 'R08':('VERIFIED_COMPLETE','TAIL_AND_LOO.json.gz / GROUP_CONTRIBUTIONS.jsonl.gz / GROUP_CONCENTRATION.json.gz'),
 'R09':('VERIFIED_COMPLETE','BOOTSTRAP_SPEC.json / SESSION_DRAWS.npz / CLUSTER_CI_RESULTS.json; 24 sessions, 10000 shared draws'),
 'R10':('VERIFIED_COMPLETE','RANK_DELTA_ANATOMY.json.gz (all/I/E, folds, deciles, unknown)'),
 'R11':('PARTIAL','PRIOR_STATE_SIGNAL_USAGE_AUDIT.json / UPSTREAM_STATIC_CODE_AUDIT.json; historical names and checkpoint hook only, all definition versions not retrieved'),
 'R12':('BLOCKED_SOURCE','STATE_SIGNAL_AVAILABILITY.json / CAUSAL_FEATURE_PLAN.json / CAUSAL_FEATURE_ROWS.jsonl.gz; only boolean presence, no values/knownAt'),
 'R13':('BLOCKED_SOURCE','STATE_SIGNAL_DELTA_RESULTS.json; feature values absent'),
 'R14':('PARTIAL','INTENT_FILL_ANATOMY.json / ARM_MATCHED_ANATOMY.json; time/exit/match available, Pτ absent'),
 'R15':('BLOCKED_SOURCE','REMAINING_UPSIDE_ANATOMY.json; post-intent path and label endpoint absent'),
 'R16':('PARTIAL','STAGE2_LINEAGE_AUDIT.json / SUPPORT_MATRIX.json; fold/score present, nested dependency unproven'),
 'R17':('VERIFIED_COMPLETE','OPTION_B_FEASIBILITY.json; design-only with experiment blocked'),
 'R18':('VERIFIED_COMPLETE','NEXT_EXPERIMENT_PRECOMMIT_DRAFT.md/.json / UNRESOLVED_DECISIONS.json'),
 'R19':('VERIFIED_COMPLETE','MISSING_EVIDENCE_REQUEST.json'),
 'R20':('PARTIAL','INDEPENDENT_AUDIT.json / EXPOSURE_LEDGER.json; saved rows recalculated, binary upstream/as-of tests blocked'),
 'R21':('VERIFIED_COMPLETE','REPORT-ja.md / figures / A_PLUS_CLOSURE.json / CONTROLLING_HANDOFF.md / MANIFEST.json'),
 'R22':('PENDING_SAVE_RECEIPT','commit and ZIP receipt recorded after immutable commit; artifact ZIP prepared separately')}
 write('REQUIREMENTS_MATRIX.json',{'schema':'phase57-a-plus-requirements-matrix-v1','originalWorkAndAddedRequirements':{k:{'status':v[0],'artifactOrReason':v[1]} for k,v in requirements.items()},'statusSemantics':'VERIFIED_COMPLETE applies to saved-row calculation or artifact accounting only; PARTIAL/BLOCKED_SOURCE is not PASS','source':'uploaded integrated Work §21; original Work requirements §4–16; Phase A preserved'})
 write('EXPOSURE_LEDGER.json',{'schema':'phase57-a-plus-exposure-v1','savedJst':now,'basisHead':'c70b981fd07128dfd9b18893b4aca3a387d17e3b','priorExposure':'Phase A A1 repeatedly viewed; this precommit does not restore independent validation','sequence':['latest PR/HEAD checked','Phase A member hashes verified','A+ precommit fixed','schema/availability inventory fixed','analysis spec hash fixed','known outcome group/tail/rank/CI viewed','no row-level State/Signal values available'],'firstIntentOutcomeUnknownRead':True,'newStateDeltaAssociationPerformed':False,'newFits':0,'newPolicyReplays':0,'newProviderRequests':0,'protectedOpenings':0,'externalLlmRequests':0,'orders':0,'mainMerges':0,'priorClosuresUnmodified':True})
 report=(OUT/'REPORT-ja.md').read_text()
 handoff=f'''# 🔒 Phase57 Phase A+ Controlling Handoff\n\nSaved JST: {now}\nBasis HEAD: `c70b981fd07128dfd9b18893b4aca3a387d17e3b`; Draft PR #587 remains open/unmerged at start check. Phase A original unchanged. This cycle is `A_PLUS_COMPLETE_WITH_BLOCKERS`; `selectedDevelopment=null`, `adaptiveDevelopmentOnly=true`, `productionReady=false`, `experimentAuthorized=false`.\n\n## Current findings\n\n- I/E_provisional/K: IM 376/370/728, R1 343/339/706. I∩K IM296/R1263; E∩K IM290/R1259. CCMG missing after first intent is exactly 80 each, all `MISSING_EXECUTION_REFERENCE`; post-intent cause, no fill/teacher imputation. Ties IM6/R14, R50-first 0 due recorded ceiling.\n- Same-mask ALL_100 component Δ: IM −¥254,400, mean −0.228 pp; R1 −¥168,700, mean −0.070 pp. Frozen route on K: IM +¥65,500, mean +0.035 pp; R1 −¥13,200, mean +0.044 pp. These are alternative Entry worlds, not a combined portfolio.\n- IM Primary quantity term −¥108,500; R1 +¥2,800; identity residual 0. R1 route 5–10% −¥41,500 and ≥10% −¥19,800. IM route ≥5% +¥38,300 but mean −0.029 pp.\n- Static trace/price contract read. State/signal values, Pτ, post-intent high/low, tie event ordering, full branch equivalence, and stage2 nested train dependency remain unproven or blocked. No new candidate outcome.\n\n## Next exact stage\n\nInspect only authorized existing Development binary trace and checkpoint State/Signal snapshots by pinned hash and restricted row ID, plus label endpoint and fold training receipts. Prove I/E membership without future fillStatus, feature knownAt and branch identity, then request an explicit finite experiment scope/Gate/budget. Do not start fit, new replay, provider, protected read, broker operation, or main merge. Continue with `MISSING_EVIDENCE_REQUEST.json` and `NEXT_EXPERIMENT_PRECOMMIT_DRAFT.md`; any source drift requires new receipt.\n\n## Verification and limits\n\nIndependent saved-row code PASS for 1,725 rows; source-level binary and causal future-suffix tests BLOCKED_SOURCE. Bootstrap is descriptive 24-session Development. GitHub CI on basis HEAD was not run (0 workflow runs); local offline audit is separate. Save receipt with result commit SHA follows this snapshot.\n'''
 (OUT/'CONTROLLING_HANDOFF.md').write_text(handoff)
 write('A_PLUS_CLOSURE.json',{'schema':'phase57-a-plus-closure-v1','savedJst':now,'cycleId':'cycle-20260929-01','basisHead':'c70b981fd07128dfd9b18893b4aca3a387d17e3b','sourceManifestSha256':sha(OUT/'SOURCE_MANIFEST.json'),'precommitSha256':sha(OUT/'A_PLUS_PRECOMMIT.json'),'analysisSpecSha256':sha(OUT/'ANALYSIS_SPEC.json'),'stageStatus':'A_PLUS_COMPLETE_WITH_BLOCKERS','numericAudit':'PASS_SAVED_ROWS_RECALCULATION_WITH_SOURCE_BLOCKERS','optionB':'DESIGN_ONLY_EXPERIMENT_BLOCKED','nextAction':'MISSING_EVIDENCE_REQUEST.json then resolve unapproved conditions in NEXT_EXPERIMENT_PRECOMMIT_DRAFT.md','selectedDevelopment':None,'adaptiveDevelopmentOnly':True,'productionReady':False,'experimentAuthorized':False,'exposureCounts':{'firstIntentIM':376,'firstIntentR1':343,'missingCCMGAtIntentIM':80,'missingCCMGAtIntentR1':80},'safetyFlags':{'newFits':0,'newPolicyReplays':0,'newProviderRequests':0,'protectedOpenings':0,'externalLlmRequests':0,'orders':0,'mainMerges':0}})
 files={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
 scripts={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'scripts').glob('phase57_post_prr_a_plus*.py'))}
 write('MANIFEST.json',{'schema':'phase57-a-plus-manifest-v1','basisHead':'c70b981fd07128dfd9b18893b4aca3a387d17e3b','cycleId':'cycle-20260929-01','savedJst':now,'fileCount':len(files),'fileSha256':files,'scriptSha256':scripts,'precommitSha256':sha(OUT/'A_PLUS_PRECOMMIT.json'),'analysisSpecSha256':sha(OUT/'ANALYSIS_SPEC.json'),'newFits':0,'newPolicyReplays':0,'providerRequests':0,'externalLlmRequests':0,'orders':0,'mainMerges':0})
 print('FINALIZED',len(files),sha(OUT/'MANIFEST.json'))
if __name__=='__main__':main()
