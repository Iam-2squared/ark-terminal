import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {
  SAFETY,
  classifyResidual,
  deterministicEntryDecision,
  evaluateEntryReconstructionEvidence,
  validateTier2Draft,
} from '../../scripts/lib/phase57-stage1f-residual-audit.mjs';

const audit = JSON.parse(fs.readFileSync(new URL('../research/phase57-exit-v4-jquants-stage1f-residual-audit-v1.json', import.meta.url)));
const draft = JSON.parse(fs.readFileSync(new URL('../research/phase57-exit-v4-tier2-reconstruction-contract-draft-v1.json', import.meta.url)));

test('Golden-missing is blocked evidence and never a mismatch', () => {
  assert.deepEqual(classifyResidual({goldenAvailable:false, independentlyComparable:false, equal:false}), {
    status:'NOT_RECOVERABLE', mismatch:0, reason:'GOLDEN_REFERENCE_INCOMPLETE',
  });
  assert.equal(audit.hybridResidualConclusion.materialComparableMismatch, 0);
});
test('Entry decision is deterministic and threshold is strictly greater than 0.60', () => {
  assert.equal(deterministicEntryDecision({longProbability:0.60, shortProbability:0.40}).action, 'WATCH');
  assert.deepEqual(deterministicEntryDecision({longProbability:0.6000000001, shortProbability:0.40}), {
    action:'ENTER', direction:'LONG', probability:0.6000000001, reason:'ABOVE_SINGLE_THRESHOLD',
  });
  assert.equal(deterministicEntryDecision({longProbability:0.40, shortProbability:0.6000000001}).direction, 'SHORT');
  assert.equal(deterministicEntryDecision({longProbability:0.70, shortProbability:0.70}).reason, 'DIRECTION_TIE');
});

test('terminal state, blocked features and chronology remain fail closed', () => {
  assert.equal(deterministicEntryDecision({longProbability:0.9, shortProbability:0.1, stateBefore:'ENTERED'}).action, 'NO_ACTION');
  assert.equal(deterministicEntryDecision({longProbability:0.9, shortProbability:0.1, featureStatus:'NO_FINALIZED_BAR'}).reason, 'BLOCKED_FEATURES');
  assert.equal(audit.hybridLayers.find((row) => row.layer === 'H_DUPLICATE_RESELECTION_SEMANTICS').mismatch, 0);
  assert.equal(audit.sourceSemantics.pitViolations, 0);
});

test('complete hash-verified candidate bytes are required for empirical reconstruction', () => {
  assert.equal(evaluateEntryReconstructionEvidence({
    featureParityExact:true,
    stateParityExact:true,
    candidateIdentityPinned:true,
    candidateModelBytesAvailable:false,
    candidateModelBytesHashVerified:false,
  }), 'ALGORITHM_DETERMINISTIC_EMPIRICAL_RECONSTRUCTION_BLOCKED_PINNED_MODEL_BYTES_REQUIRED');
  assert.equal(audit.entryReconstruction.entryEventReconstructionExecuted, false);
});

test('Tier2 draft cannot self-activate and corporate-action conflicts block', () => {
  assert.deepEqual(validateTier2Draft(draft), {automaticActivationAllowed:false, status:'DRAFT_VALID_NOT_ACTIVE'});
  assert(draft.blockingConditions.includes('UNRESOLVED_CORPORATE_ACTION_CONFLICT'));
  assert.equal(draft.corporateActions.unresolvedConflictTreatment, 'BLOCK_SYMBOL_SESSION');
});

test('no outcome, protected, fresh or new raw access and safety stays false', () => {
  for (const key of ['newRawDownloads','newSealedSessions','protected180To282','freshValidationOrOos','exitOutcome','futureLabels','exitInvocations']) {
    assert.equal(audit.accessLedger[key], 0, key);
  }
  assert.deepEqual(audit.safety, SAFETY);
  assert(Object.values(draft.safety).every((value) => value === false));
  assert.equal(audit.eligibility.confirmedTier2Sessions, 0);
  assert.equal(audit.eligibility.stage2AllocationAllowed, false);
  assert.equal(audit.hardStop, 'ACTIVE');
});
