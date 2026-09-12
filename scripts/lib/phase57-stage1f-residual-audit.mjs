import assert from 'node:assert/strict';

export const SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

export const RESIDUAL_TAXONOMY = Object.freeze([
  'GOLDEN_REFERENCE_INCOMPLETE',
  'HISTORICAL_UNIVERSE_PARTIAL',
  'SOURCE_INPUT_MISSING',
  'RANK_NOT_RETAINED',
  'MEMBERSHIP_NOT_RETAINED',
  'TIMESTAMP_NOT_RETAINED',
  'REPLAY_IMPLEMENTATION',
  'DATA_SEMANTICS',
  'MISSING_BAR',
  'CORPORATE_ACTION',
  'DUPLICATE_SEMANTICS',
  'UNKNOWN',
]);

export function classifyResidual({goldenAvailable, independentlyComparable, equal}) {
  if (!goldenAvailable) return {status: 'NOT_RECOVERABLE', mismatch: 0, reason: 'GOLDEN_REFERENCE_INCOMPLETE'};
  if (!independentlyComparable) return {status: 'PARTIAL', mismatch: 0, reason: 'SOURCE_INPUT_MISSING'};
  return equal
    ? {status: 'PASS', mismatch: 0, reason: null}
    : {status: 'FAIL', mismatch: 1, reason: 'DATA_SEMANTICS'};
}
function finiteProbability(value) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;
}

export function deterministicEntryDecision({
  longProbability,
  shortProbability,
  threshold = 0.60,
  stateBefore = 'WATCHING',
  featureStatus = 'READY',
}) {
  assert(finiteProbability(longProbability) && finiteProbability(shortProbability), 'INVALID_PROBABILITY');
  assert.equal(threshold, 0.60, 'FROZEN_THRESHOLD_CHANGED');
  if (stateBefore === 'ENTERED' || stateBefore === 'EXPIRED') return {action: 'NO_ACTION', direction: null, reason: stateBefore};
  assert.equal(stateBefore, 'WATCHING', 'INVALID_STATE');
  if (featureStatus !== 'READY') return {action: 'WATCH', direction: null, reason: 'BLOCKED_FEATURES'};
  if (longProbability === shortProbability) return {action: 'WATCH', direction: null, reason: 'DIRECTION_TIE'};
  const direction = longProbability > shortProbability ? 'LONG' : 'SHORT';
  const probability = Math.max(longProbability, shortProbability);
  return probability > threshold
    ? {action: 'ENTER', direction, probability, reason: 'ABOVE_SINGLE_THRESHOLD'}
    : {action: 'WATCH', direction: null, probability, reason: 'NOT_ABOVE_SINGLE_THRESHOLD'};
}

export function evaluateEntryReconstructionEvidence({
  featureParityExact,
  stateParityExact,
  candidateIdentityPinned,
  candidateModelBytesAvailable,
  candidateModelBytesHashVerified,
}) {
  if (!featureParityExact || !stateParityExact) return 'DETERMINISTIC_ENTRY_RECONSTRUCTION_FAIL';
  if (!candidateIdentityPinned || !candidateModelBytesAvailable || !candidateModelBytesHashVerified) {
    return 'ALGORITHM_DETERMINISTIC_EMPIRICAL_RECONSTRUCTION_BLOCKED_PINNED_MODEL_BYTES_REQUIRED';
  }
  return 'DETERMINISTIC_ENTRY_RECONSTRUCTION';
}

export function validateTier2Draft(contract) {
  assert.equal(contract.status, 'DRAFT_NOT_ACTIVE_BLOCKED');
  assert.equal(contract.activated, false);
  assert.equal(contract.tier2ConfirmedSessions, 0);
  assert.equal(contract.stage2AllocationAllowed, false);
  assert.deepEqual(contract.allocatedSessions, []);
  assert(Object.values(contract.safety).every((value) => value === false));
  return {automaticActivationAllowed: false, status: 'DRAFT_VALID_NOT_ACTIVE'};
}
