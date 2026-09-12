import assert from 'node:assert/strict';
import crypto from 'node:crypto';

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

export const BLOCKING_REASONS = Object.freeze([
  'PIT_VIOLATION',
  'SOURCE_LINEAGE_MISSING',
  'TIMESTAMP_AMBIGUOUS',
  'FIVE_MIN_AGGREGATION_FAIL',
  'HISTORICAL_UNIVERSE_BLOCKED',
  'CORPORATE_ACTION_UNRESOLVED',
  'CRITICAL_MISSING_DATA',
  'HYBRID_MATERIAL_MISMATCH',
  'MSH_RECONSTRUCTION_FAIL',
  'ENTRY_EVENT_AMBIGUOUS',
  'REFERENCE_PRICE_AMBIGUOUS',
  'SESSION_INCOMPLETE',
  'UNKNOWN_CRITICAL',
]);

const RESTRICTED_INPUT_KEYS = /^(future(Label|Return|Price|Volume|Selection|State)|mfe|mae|exitOutcome|profit|pnl|winner|loser)$/i;

export function assertNoOutcomeOrFutureInput(value, path = '$') {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => assertNoOutcomeOrFutureInput(entry, `${path}[${index}]`));
    return;
  }
  if (!value || typeof value !== 'object') return;
  for (const [key, entry] of Object.entries(value)) {
    assert(!RESTRICTED_INPUT_KEYS.test(key), `PROHIBITED_INPUT_FIELD:${path}.${key}`);
    assertNoOutcomeOrFutureInput(entry, `${path}.${key}`);
  }
}

export function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export function canonicalSha256(value) {
  return crypto.createHash('sha256').update(canonicalJson(value)).digest('hex');
}

export function validateFrozenContract(contract, schema) {
  assert.equal(contract.contractId, 'PHASE57_EXIT_V4_TIER2_RECONSTRUCTION_CONTRACT_V1');
  assert.equal(contract.contractVersion, '1.0.0');
  assert.equal(contract.status, 'FROZEN_NOT_ACTIVATED');
  assert.equal(contract.classification.datasetClass, 'EXIT_DEVELOPMENT_SUBSTRATE');
  assert.equal(contract.classification.substrateTier, 'TIER2_RECONSTRUCTED_REPLAY');
  assert.equal(contract.classification.researchUse, 'DEVELOPMENT_ONLY');
  assert.equal(contract.classification.temporality, 'NON_PROSPECTIVE');
  for (const forbidden of ['FULL_REPLAY_ELIGIBLE', 'PROSPECTIVE', 'FORMAL_OOS']) {
    assert(contract.classification.forbiddenLabels.includes(forbidden));
  }
  assert.equal(contract.timestampContract.minuteMeaning, 'BAR_START');
  assert.deepEqual(contract.timestampContract.firstRegularBar.includedMinuteRows, ['09:00', '09:01', '09:02', '09:03', '09:04']);
  assert.equal(contract.timestampContract.decisionAvailabilityBound, 'barEnd');
  assert.equal(contract.pitContract.requiredViolationCount, 0);
  assert.equal(contract.frozenIdentifiers.entryThreshold, 'STRICTLY_GREATER_THAN_0.60');
  assert.equal(contract.frozenIdentifiers.entryCandidateSha256, 'f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a');
  assert.equal(contract.historicalUniverse.coverage, 'PARTIAL');
  assert.equal(contract.corporateActions.unresolvedCriticalConflictTreatment, 'BLOCK_OR_EXCLUDE_SYMBOL_SESSION');
  assert.equal(contract.missingSparseContract.unknownCanBeRelabelledNoTrade, false);
  assert.equal(contract.missingSparseContract.noFinalizedFiveMinuteBar.observation, 'NO_OBSERVATION');
  assert.equal(contract.missingSparseContract.noFinalizedFiveMinuteBar.reason, 'NO_FINALIZED_BAR');
  assert.equal(contract.stageHandoff.stage2AllocationDesignReady, true);
  assert.equal(contract.stageHandoff.outcomeAllowed, false);
  assert.equal(contract.activation.tier2Activated, false);
  assert.equal(contract.activation.developmentUnlocked, false);
  assert.equal(contract.activation.stage2AllocationExecuted, false);
  assert.deepEqual(contract.activation.allocatedSessions, []);
  assert.equal(contract.activation.selfActivationAllowed, false);
  assert.deepEqual(contract.safety, SAFETY);
  assert.deepEqual(schema.blockingReasons, BLOCKING_REASONS);
  assert.equal(schema.outcomeFieldsAllowed, false);
  assert.equal(schema.futureLabelFieldsAllowed, false);
  assert.deepEqual(schema.safety, SAFETY);
  return {status: 'FROZEN_VALID_NOT_ACTIVATED', automaticActivationAllowed: false};
}

export function evaluateTier2Eligibility(input, schema) {
  assertNoOutcomeOrFutureInput(input);
  const reasons = [];
  if ((input.pitViolations ?? 0) !== 0) reasons.push('PIT_VIOLATION');
  if (input.sourceLineage !== 'PASS') reasons.push('SOURCE_LINEAGE_MISSING');
  if (input.timestampContract !== 'PASS') reasons.push('TIMESTAMP_AMBIGUOUS');
  if (input.fiveMinuteAggregation !== 'PASS') reasons.push('FIVE_MIN_AGGREGATION_FAIL');
  if (input.historicalUniverse === 'BLOCKED') reasons.push('HISTORICAL_UNIVERSE_BLOCKED');
  if (input.corporateActionConflict === true) reasons.push('CORPORATE_ACTION_UNRESOLVED');
  if (input.criticalMissingData === true || input.missingHandling !== 'FAIL_CLOSED') reasons.push('CRITICAL_MISSING_DATA');
  if ((input.hybridMaterialMismatches ?? 0) !== 0) reasons.push('HYBRID_MATERIAL_MISMATCH');
  if (input.mshFeatureReconstruction !== 'PASS' || input.mshStateReconstruction !== 'PASS' || input.frozenIdentifiers !== 'PASS') reasons.push('MSH_RECONSTRUCTION_FAIL');
  if (input.entryEventClosure !== 'DETERMINISTIC_PASS') reasons.push('ENTRY_EVENT_AMBIGUOUS');
  if (input.referencePriceSemantics !== 'PASS') reasons.push('REFERENCE_PRICE_AMBIGUOUS');
  if (input.sessionComplete !== true) reasons.push('SESSION_INCOMPLETE');
  if (input.unknownCritical === true) reasons.push('UNKNOWN_CRITICAL');
  const uniqueReasons = [...new Set(reasons)];
  for (const reason of uniqueReasons) assert(schema.blockingReasons.includes(reason), `UNKNOWN_BLOCKING_REASON:${reason}`);
  return uniqueReasons.length === 0
    ? {status: 'ELIGIBLE_CANDIDATE_NOT_ACTIVATED', eligible: true, activated: false, reasons: []}
    : {status: 'EXCLUDED', eligible: false, activated: false, reasons: uniqueReasons};
}

export function assertAccessAndSafetyClosed(contract) {
  for (const value of Object.values(contract.accessLedger)) assert.equal(value, 0);
  assert.deepEqual(contract.safety, SAFETY);
  assert.equal(contract.activation.tier2Activated, false);
  assert.equal(contract.activation.developmentUnlocked, false);
  return true;
}
