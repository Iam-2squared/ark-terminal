import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';
import {
  BLOCKING_REASONS,
  SAFETY,
  assertAccessAndSafetyClosed,
  assertNoOutcomeOrFutureInput,
  canonicalSha256,
  evaluateTier2Eligibility,
  validateFrozenContract,
} from '../../scripts/lib/phase57-stage1h-tier2-contract.mjs';

const contractUrl = new URL('../research/phase57-exit-v4-tier2-reconstruction-contract-v1.json', import.meta.url);
const schemaUrl = new URL('../research/phase57-exit-v4-tier2-eligibility-schema-v1.json', import.meta.url);
const contract = JSON.parse(fs.readFileSync(contractUrl, 'utf8'));
const schema = JSON.parse(fs.readFileSync(schemaUrl, 'utf8'));
const audit = JSON.parse(fs.readFileSync(new URL('../research/phase57-exit-v4-jquants-stage1h-tier2-contract-freeze-v1.json', import.meta.url), 'utf8'));

function eligible(overrides = {}) {
  return {
    pitViolations: 0,
    sourceLineage: 'PASS',
    timestampContract: 'PASS',
    fiveMinuteAggregation: 'PASS',
    historicalUniverse: 'PARTIAL_NOT_BLOCKED',
    corporateActionConflict: false,
    criticalMissingData: false,
    missingHandling: 'FAIL_CLOSED',
    hybridMaterialMismatches: 0,
    mshFeatureReconstruction: 'PASS',
    mshStateReconstruction: 'PASS',
    frozenIdentifiers: 'PASS',
    entryEventClosure: 'DETERMINISTIC_PASS',
    referencePriceSemantics: 'PASS',
    sessionComplete: true,
    unknownCritical: false,
    ...overrides,
  };
}

test('frozen contract validates and cannot equal FULL or PROSPECTIVE', () => {
  assert.deepEqual(validateFrozenContract(contract, schema), {status:'FROZEN_VALID_NOT_ACTIVATED', automaticActivationAllowed:false});
  assert.notEqual(contract.classification.substrateTier, 'FULL_REPLAY_ELIGIBLE');
  assert.notEqual(contract.classification.temporality, 'PROSPECTIVE');
  assert.equal(contract.aggregateWithFullOrProspectiveAsMainPerformanceAllowed, false);
});

test('eligible metadata remains candidate-only and cannot activate Development', () => {
  assert.deepEqual(evaluateTier2Eligibility(eligible(), schema), {
    status:'ELIGIBLE_CANDIDATE_NOT_ACTIVATED', eligible:true, activated:false, reasons:[],
  });
  assert.equal(contract.activation.tier2Activated, false);
  assert.equal(contract.activation.developmentUnlocked, false);
  assert.equal(contract.stageHandoff.stage2AllocationDesignReady, true);
});

test('PIT violation, missing lineage and timestamp or aggregation failure block', () => {
  const result = evaluateTier2Eligibility(eligible({pitViolations:1, sourceLineage:'FAIL', timestampContract:'FAIL', fiveMinuteAggregation:'FAIL'}), schema);
  assert.deepEqual(result.reasons, ['PIT_VIOLATION','SOURCE_LINEAGE_MISSING','TIMESTAMP_AMBIGUOUS','FIVE_MIN_AGGREGATION_FAIL']);
  assert.equal(result.status, 'EXCLUDED');
});

test('universe block and corporate-action uncertainty exclude', () => {
  const result = evaluateTier2Eligibility(eligible({historicalUniverse:'BLOCKED', corporateActionConflict:true}), schema);
  assert.deepEqual(result.reasons, ['HISTORICAL_UNIVERSE_BLOCKED','CORPORATE_ACTION_UNRESOLVED']);
});

test('missing handling is fail-closed and synthetic/fill behavior is prohibited', () => {
  assert.equal(contract.missingSparseContract.unknownCanBeRelabelledNoTrade, false);
  assert.equal(contract.missingSparseContract.forwardFill, false);
  assert.equal(contract.missingSparseContract.syntheticOhlcv, false);
  assert.equal(contract.missingSparseContract.noFinalizedFiveMinuteBar.advanceExitState, false);
  assert(evaluateTier2Eligibility(eligible({missingHandling:'ASSUME_NO_TRADE'}), schema).reasons.includes('CRITICAL_MISSING_DATA'));
});

test('Hybrid mismatch and MSH or Entry ambiguity block', () => {
  const result = evaluateTier2Eligibility(eligible({hybridMaterialMismatches:1, mshFeatureReconstruction:'FAIL', entryEventClosure:'UNKNOWN'}), schema);
  assert.deepEqual(result.reasons, ['HYBRID_MATERIAL_MISMATCH','MSH_RECONSTRUCTION_FAIL','ENTRY_EVENT_AMBIGUOUS']);
});

test('strict >0.60 and Frozen identifiers are pinned', () => {
  assert.equal(contract.frozenIdentifiers.entryThreshold, 'STRICTLY_GREATER_THAN_0.60');
  assert.equal(contract.frozenIdentifiers.selectorModelDigest, '444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2');
  assert.equal(contract.frozenIdentifiers.entryCandidateSha256, 'f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a');
});

test('blocking taxonomy is exact and reason counts are mandatory', () => {
  assert.deepEqual(schema.blockingReasons, BLOCKING_REASONS);
  assert.equal(schema.reasonCountsRequired, true);
});

test('canonical contract digest is deterministic and byte digest matches evidence', () => {
  assert.equal(canonicalSha256(contract), canonicalSha256(JSON.parse(JSON.stringify(contract))));
  const checksum = fs.readFileSync(new URL('../research/phase57-exit-v4-tier2-reconstruction-contract-v1.sha256', import.meta.url), 'utf8').trim().split(/\s+/)[0];
  const byteDigest = crypto.createHash('sha256').update(fs.readFileSync(contractUrl)).digest('hex');
  assert.equal(byteDigest, checksum);
});

test('outcome/future input, protected/fresh access and all safety enablement stay blocked', () => {
  assert.throws(() => assertNoOutcomeOrFutureInput({...eligible(), exitOutcome:12}), /PROHIBITED_INPUT_FIELD/);
  assert.equal(schema.outcomeFieldsAllowed, false);
  assert.equal(schema.futureLabelFieldsAllowed, false);
  assertAccessAndSafetyClosed(contract);
  assert.deepEqual(contract.safety, SAFETY);
  assert.equal(contract.accessLedger.protected180To282, 0);
  assert.equal(contract.accessLedger.freshValidationOrOos, 0);
  assert.equal(contract.accessLedger.exitInvocations, 0);
  const source = fs.readFileSync(new URL('../../scripts/lib/phase57-stage1h-tier2-contract.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /from\s+['\"][^'\"]*exit[^'\"]*['\"]/i);
});

test('Stage 1H closes only the contract freeze and hard-stops before Stage 2 execution', () => {
  assert.equal(audit.status, 'TIER2_RECONSTRUCTION_CONTRACT_FROZEN_STAGE2_READY');
  assert.equal(audit.contractFreeze.sha256, '2aa9fd80596c0f71f2359fb132288a15d563e3fab8e22ecbac54fda308a54a70');
  assert.equal(audit.contractFreeze.eligibilitySchemaSha256, 'f060c654f0d5af5f105f8ba20c47b78950ad433305b735d42f6cbd68f8e2823b');
  assert.equal(audit.classification.fullReplayConfirmedSessions, 0);
  assert.equal(audit.stageHandoff.tier2Activated, false);
  assert.equal(audit.stageHandoff.developmentUnlocked, false);
  assert.equal(audit.stageHandoff.stage2AllocationExecuted, false);
  assert.equal(audit.hardStop, 'ACTIVE');
  assert(Object.values(audit.accessLedger).every((value) => value === 0));
  assert.deepEqual(audit.safety, SAFETY);
});
