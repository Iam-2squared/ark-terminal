import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';

const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const allFalse=x=>Object.values(x).every(value=>value===false);
const freezePath='predict/research/phase57-capital-allocation-integrated-candidate-freeze.json';
const precommitPath='predict/research/phase57-capital-allocation-future-integrated-oos-precommit.json';
const contractPath='predict/research/phase57-capital-allocation-validation-contract.json';

test('MAX_3 Main refreeze preserves honest historical selection lineage',()=>{
  const freeze=read(freezePath);
  assert.equal(freeze.status,'DEVELOPMENT_MAIN_MAX_3_FROZEN');
  assert.equal(freeze.candidate.budgetEnvelope,'MAX_3');
  assert.equal(freeze.candidate.slotBudgetFormula,'CURRENT_EQUITY_DIVIDED_BY_3');
  assert.equal(freeze.budgetRoles.MAX_3,'PRIMARY_INTEGRATED_DEVELOPMENT_CANDIDATE');
  assert.equal(freeze.budgetRoles.MAX_5,'CONSERVATIVE_INTEGRATED_SUB_CANDIDATE');
  assert.equal(freeze.budgetRoles.MAX_10,'LEGACY_BUDGET_BASELINE');
  assert.equal(freeze.selectionLineage[0].decision,'MAX_5_ORIGINALLY_SELECTED_AS_PRIMARY_AFTER_A_PLUS_B_BUDGET_ENVELOPE_DEVELOPMENT');
  assert.equal(freeze.selectionLineage[1].outcomesViewed,true);
  assert.equal(freeze.selectionLineage[1].oosEvidence,false);
  assert.equal(freeze.selectionLineage[2].decision,'USER_EXPLICITLY_PROMOTED_MAX_3_TO_MAIN_FROM_DEVELOPMENT_AND_EXPOSED_EVIDENCE');
  assert.equal(freeze.selectionBasis.oosSuperiorityClaim,false);
  assert.equal(freeze.developmentSearchClosure.closed,true);
  assert.equal(freeze.developmentSearchClosure.additionalMaxNForbidden,true);
  assert.equal(allFalse(freeze.claims),true);assert.equal(allFalse(freeze.safety),true);
});

test('future Integrated OOS is outcome-blind, 20-session, four-arm and hash-bound',()=>{
  const freeze=read(freezePath),precommit=read(precommitPath),contract=read(contractPath);
  assert.equal(precommit.status,'FUTURE_INTEGRATED_OOS_PRECOMMITTED_OOS_NOT_OPENED');
  assert.equal(precommit.candidateFreezeSha256,sha(freezePath));
  assert.equal(precommit.window.notBeforeSessionDate,'2026-10-22');
  assert.equal(precommit.window.targetEligibleMarketSessions,20);
  assert.equal(precommit.window.extensionOrShorteningFromPerformanceAllowed,false);
  assert.equal(precommit.eligibilityRule.outcomeMayInfluenceEligibility,false);
  assert.deepEqual(precommit.reservedBoundary.existingEntryFreshReservation,['2026-09-10','2026-10-21']);
  assert.equal(precommit.reservedBoundary.mayConsumeOrRepurpose,false);
  assert.deepEqual(Object.fromEntries(Object.entries(precommit.arms).map(([k,v])=>[k,[v.budgetDivisor,v.exit]])),{primary:[3,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'],conservativeSub:[5,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'],legacyBaseline:[10,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'],exitComparator:[3,'FROZEN_EXIT_V4']});
  assert.equal(precommit.dataAccessAttestation.future2026_10_22PlusFetched,false);assert.equal(precommit.dataAccessAttestation.future2026_10_22PlusOpened,false);assert.equal(precommit.dataAccessAttestation.future2026_10_22PlusMeasured,false);assert.equal(precommit.dataAccessAttestation.reserved2026_09_10Through2026_10_21Consumed,false);assert.deepEqual(precommit.dataAccessAttestation.sessionIds,[]);assert.equal(precommit.dataAccessAttestation.inputBundleSha256,null);
  assert.equal(contract.integratedCandidateFreezeSha256,sha(freezePath));assert.equal(contract.status,'FUTURE_INTEGRATED_OOS_PRECOMMITTED_NOT_OPENED');assert.equal(contract.validationOpened,false);assert.equal(contract.runnerExecutionUnlocked,false);
  assert.equal(contract.arms.primary,'V3_B_RISK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5__MAX_3');assert.equal(contract.arms.conservativeSub,'V3_B_RISK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5__MAX_5');assert.equal(contract.arms.exitComparator,'V3_B_RISK__FROZEN_EXIT_V4__MAX_3');
  assert.equal(allFalse(precommit.claims),true);assert.equal(allFalse(precommit.safety),true);assert.equal(allFalse(contract.safety),true);
});
