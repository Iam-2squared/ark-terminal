import fs from 'node:fs';
import assert from 'node:assert/strict';
import { DYNAMIC_STATE_V1 } from './lib/phase57-exit-v5-dynamic-state.mjs';

const freeze = JSON.parse(fs.readFileSync('predict/research/phase57-exit-v5-dynamic-state-freeze-v1.json', 'utf8'));
const dev = JSON.parse(fs.readFileSync('predict/research/phase57-exit-v5-dynamic-state-development-v1.json', 'utf8'));

assert.equal(freeze.schemaId, 'PHASE57_EXIT_V5_DYNAMIC_STATE_FREEZE_V1');
assert.equal(freeze.status, 'FROZEN_FOR_NEXT_UNSEEN_VALIDATION_NOT_PROMOTED');
assert.equal(freeze.architecture, 'CAUSAL_DYNAMIC_STATE_OVER_FROZEN_V4_CONTINUATION');
assert.equal(freeze.stateMachine.observationHorizonBars, DYNAMIC_STATE_V1.observationHorizonBars);
assert.equal(freeze.stateMachine.transactionCostBps, DYNAMIC_STATE_V1.transactionCostBps);
assert.equal(freeze.stateMachine.freeReturnThresholds, 0);
assert.equal(DYNAMIC_STATE_V1.adverseBoundaryPct, 0);
assert.equal(DYNAMIC_STATE_V1.reclaimBoundaryPct, 0);
assert.equal(freeze.stateMachine.symbolSpecificRules, false);
assert.equal(freeze.stateMachine.longShortSpecificRules, false);

assert.equal(freeze.exposedReplayParity.blockA.dynamicNetPctPoints, dev.minimalDynamicCandidateDiagnostic.observationHorizonSensitivity.bar6.blockA.candidateNetPctPoints);
assert.equal(freeze.exposedReplayParity.blockA.v4NetPctPoints, dev.minimalDynamicCandidateDiagnostic.observationHorizonSensitivity.bar6.blockA.v4NetPctPoints);
assert.equal(freeze.exposedReplayParity.blockA.deltaVsV4PctPoints, dev.minimalDynamicCandidateDiagnostic.observationHorizonSensitivity.bar6.blockA.deltaVsV4PctPoints);
assert.equal(freeze.exposedReplayParity.blockB.dynamicNetPctPoints, dev.minimalDynamicCandidateDiagnostic.observationHorizonSensitivity.bar6.blockB.candidateNetPctPoints);
assert.equal(freeze.exposedReplayParity.blockB.v4NetPctPoints, dev.minimalDynamicCandidateDiagnostic.observationHorizonSensitivity.bar6.blockB.v4NetPctPoints);
assert.equal(freeze.exposedReplayParity.blockB.deltaVsV4PctPoints, dev.minimalDynamicCandidateDiagnostic.observationHorizonSensitivity.bar6.blockB.deltaVsV4PctPoints);
assert.equal(freeze.exposedReplayParity.blockA.parity, 'EXACT_MATCH_TO_DEVELOPMENT_DIAGNOSTIC');
assert.equal(freeze.exposedReplayParity.blockB.parity, 'EXACT_MATCH_TO_DEVELOPMENT_DIAGNOSTIC');

for (const [k, v] of Object.entries(freeze.nextUnseenContract)) {
  if (k === 'openOnlyAfterFreezeCommitAndGreenPreflight' || k === 'decisionMustRemainPairedAgainstFrozenV4') {
    assert.equal(v, true, `NEXT_UNSEEN_CONTRACT_NOT_TRUE:${k}`);
  } else {
    assert.equal(v, false, `NEXT_UNSEEN_MUTATION_NOT_FALSE:${k}`);
  }
}
assert.equal(freeze.guards.newUnseenOpenedAtFreezeTime, false);
assert.equal(freeze.guards.mainIntegrationAllowed, false);
assert.equal(freeze.guards.mergeAllowed, false);
assert.equal(freeze.guards.readyForReviewAllowed, false);
assert.equal(freeze.guards.automaticPromotionAllowed, false);
for (const [k, v] of Object.entries(freeze.safety)) {
  assert.equal(v, false, `SAFETY_FLAG_NOT_FALSE:${k}`);
}

console.log(JSON.stringify({
  status: 'PHASE57_EXIT_V5_DYNAMIC_STATE_FREEZE_PREFLIGHT_PASS',
  candidateId: freeze.candidateId,
  horizonBars: freeze.stateMachine.observationHorizonBars,
  freeReturnThresholds: freeze.stateMachine.freeReturnThresholds,
  blockAParity: freeze.exposedReplayParity.blockA.parity,
  blockBParity: freeze.exposedReplayParity.blockB.parity,
  unseenStillSealedAtFreeze: !freeze.guards.newUnseenOpenedAtFreezeTime,
  safety: 'ALL_FALSE'
}));
