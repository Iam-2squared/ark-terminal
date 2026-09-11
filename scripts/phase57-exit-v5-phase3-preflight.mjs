import fs from 'node:fs';
import assert from 'node:assert/strict';

const path = process.env.CONFIG ?? 'predict/research/phase57-exit-v5-phase3-development-v1.json';
const cfg = JSON.parse(fs.readFileSync(path, 'utf8'));

assert.equal(cfg.schemaId, 'PHASE57_EXIT_V5_PHASE3_DEVELOPMENT_V1');
assert.equal(cfg.role, 'DEVELOPMENT_ONLY_AFTER_BLOCK_A_REPLICATION');
assert.equal(cfg.evidenceBasis.blockAFinalDecision, 'BLOCK_A_PARTIAL');
assert.equal(cfg.evidenceBasis.blockASessions, 30);
assert.equal(cfg.evidenceBasis.blockAPairedTrades, 54);
assert.equal(cfg.evidenceBasis.blockAImmediateAdverseCompleteN, 29);
assert.equal(cfg.evidenceBasis.blockARecoveredN, 15);
assert.equal(cfg.evidenceBasis.blockAFailureN, 14);

const primary = cfg.frozenPrimaryFeatures.map(x => x.name);
assert.deepEqual(primary, [
  'firstBarDirectionalCloseReturnPct',
  'firstBarMfePct',
  'firstBarMaePct'
]);
assert.equal(cfg.developmentConstraints.maxPrimaryDecisionFeatures, 3);
assert.ok(cfg.developmentConstraints.maxFreeThresholds <= 3);
assert.equal(cfg.developmentConstraints.interactionTermsAllowed, false);
assert.equal(cfg.developmentConstraints.blackBoxModelAllowed, false);
assert.equal(cfg.developmentConstraints.logisticRegressionAllowed, false);
assert.equal(cfg.developmentConstraints.neuralNetworkAllowed, false);
assert.equal(cfg.developmentConstraints.thresholdFittingAllowedOnFutureUnseenValidation, false);
assert.equal(cfg.nextUnseenPolicy.openBeforeCandidateFreeze, false);
assert.equal(cfg.nextUnseenPolicy.thresholdChangesAfterOpening, false);
assert.equal(cfg.nextUnseenPolicy.featureChangesAfterOpening, false);
assert.equal(cfg.guards.doNotReuseBlockAAsValidation, true);
assert.equal(cfg.guards.doNotOpenNewUnseenUntilCandidateFreeze, true);
assert.equal(cfg.guards.mainIntegrationAllowed, false);
assert.equal(cfg.guards.mergeAllowed, false);

for (const [k, v] of Object.entries(cfg.safety)) {
  assert.equal(v, false, `SAFETY_FLAG_NOT_FALSE:${k}`);
}

const forbidden = new Set(cfg.notDecisionFeatures);
for (const name of primary) assert.equal(forbidden.has(name), false);

console.log(JSON.stringify({
  status: 'PHASE57_EXIT_V5_PHASE3_PREFLIGHT_PASS',
  primaryFeatures: primary,
  maxFreeThresholds: cfg.developmentConstraints.maxFreeThresholds,
  unseenStillSealed: !cfg.nextUnseenPolicy.openBeforeCandidateFreeze,
  safety: 'ALL_FALSE'
}));
