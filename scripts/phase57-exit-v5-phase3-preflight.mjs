import fs from 'node:fs';
import assert from 'node:assert/strict';

const configPath = process.env.CONFIG ?? 'predict/research/phase57-exit-v5-phase3-development-v1.json';
const analysisPath = process.env.ANALYSIS ?? 'predict/research/phase57-exit-v5-phase3-exposed-evidence-analysis-v1.json';
const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const analysis = JSON.parse(fs.readFileSync(analysisPath, 'utf8'));

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

assert.equal(analysis.schemaId, 'PHASE57_EXIT_V5_PHASE3_EXPOSED_EVIDENCE_ANALYSIS_V1');
assert.equal(analysis.role, 'DEVELOPMENT_ONLY_EXPOSED_EVIDENCE');
assert.equal(analysis.provenance.old20.artifactId, 10178728601);
assert.equal(analysis.provenance.blockA.artifactId, 10265532613);
assert.equal(analysis.finding1HardExit.decision, 'REJECT_HARD_FIRST_BAR_EXIT');
assert.equal(analysis.phase3Decision.hardExit, 'NO_GO');
assert.equal(analysis.phase3Decision.singleFeatureRouter, 'NO_FREEZE');
assert.equal(analysis.phase3Decision.threeFeatureRouter, 'CONTINUE_DEVELOPMENT');
assert.equal(analysis.phase3Decision.newUnseenOutcomeAccess, 'DO_NOT_OPEN');
assert.match(analysis.finding2ManagementRouter.threeFeatureDevelopmentCandidate.status, /NOT_FROZEN$/);
assert.equal(analysis.finding2ManagementRouter.threeFeatureDevelopmentCandidate.old20LeaveOneDivergentSwitchOutMinDeltaPctPoints > 0, true);
assert.equal(analysis.finding2ManagementRouter.threeFeatureDevelopmentCandidate.blockALeaveOneDivergentSwitchOutMinDeltaPctPoints > 0, true);

for (const [k, v] of Object.entries(cfg.safety)) {
  assert.equal(v, false, `SAFETY_FLAG_NOT_FALSE:${k}`);
}
for (const [k, v] of Object.entries(analysis.safety)) {
  assert.equal(v, false, `ANALYSIS_SAFETY_FLAG_NOT_FALSE:${k}`);
}

const forbidden = new Set(cfg.notDecisionFeatures);
for (const name of primary) assert.equal(forbidden.has(name), false);

console.log(JSON.stringify({
  status: 'PHASE57_EXIT_V5_PHASE3_PREFLIGHT_PASS',
  primaryFeatures: primary,
  maxFreeThresholds: cfg.developmentConstraints.maxFreeThresholds,
  hardExit: analysis.phase3Decision.hardExit,
  router: analysis.phase3Decision.threeFeatureRouter,
  candidateFrozen: false,
  unseenStillSealed: !cfg.nextUnseenPolicy.openBeforeCandidateFreeze && analysis.phase3Decision.newUnseenOutcomeAccess === 'DO_NOT_OPEN',
  safety: 'ALL_FALSE'
}));
