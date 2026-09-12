import fs from 'node:fs';
import assert from 'node:assert/strict';

const freezePath = 'predict/research/phase57-exit-v5-candidate-freeze-v1.json';
const robustPath = 'predict/research/phase57-exit-v5-phase3-robustness-ablation-v1.json';
const freeze = JSON.parse(fs.readFileSync(freezePath, 'utf8'));
const robust = JSON.parse(fs.readFileSync(robustPath, 'utf8'));

assert.equal(freeze.schemaId, 'PHASE57_EXIT_V5_CANDIDATE_FREEZE_V1');
assert.equal(freeze.status, 'FROZEN_FOR_UNSEEN_VALIDATION_NOT_PROMOTED');
assert.equal(freeze.architecture, 'FIRST_BAR_STATE_ROUTER_OVER_FROZEN_V3_V4');
assert.equal(freeze.decisionFeatures.length, 2);
assert.deepEqual(freeze.decisionFeatures.map(x => x.name), [
  'firstBarDirectionalCloseReturnBps',
  'firstBarMaeBps'
]);
assert.equal(freeze.router.decisionTimestamp, 'END_OF_FIRST_COMPLETED_POST_ENTRY_5M_BAR');
assert.equal(freeze.router.routeIsSticky, true);
assert.equal(freeze.router.midTradeRerouting, false);
assert.equal(freeze.managedPolicies.v3.modified, false);
assert.equal(freeze.managedPolicies.v4.modified, false);
assert.equal(freeze.unseenValidationContract.thresholdChangesAfterOpening, false);
assert.equal(freeze.unseenValidationContract.featureChangesAfterOpening, false);
assert.equal(freeze.unseenValidationContract.routerLogicChangesAfterOpening, false);
assert.equal(freeze.unseenValidationContract.overrideAdditionAfterOpening, false);
assert.equal(freeze.guards.newUnseenOpenedAtFreezeTime, false);
assert.equal(freeze.guards.mainIntegrationAllowed, false);
assert.equal(freeze.guards.mergeAllowed, false);
assert.equal(freeze.guards.readyForReviewAllowed, false);
assert.equal(freeze.guards.automaticPromotionAllowed, false);
for (const [k, v] of Object.entries(freeze.safety)) {
  assert.equal(v, false, `SAFETY_FLAG_NOT_FALSE:${k}`);
}

assert.equal(robust.schemaId, 'PHASE57_EXIT_V5_PHASE3_ROBUSTNESS_ABLATION_V1');
assert.equal(robust.decision.mfeAsDecisionFeature, 'REMOVE_AS_REDUNDANT_FOR_CANDIDATE');
assert.equal(robust.decision.winnerOverride, 'DO_NOT_FIT_BEFORE_UNSEEN');
assert.equal(robust.decision.hardFirstBarExit, 'REJECTED');
assert.equal(robust.decision.routerArchitecture, 'KEEP_MINIMAL_TWO_FEATURE');
assert.equal(robust.decision.candidateReadyToFreezeForNewUnseen, true);

const excluded = new Set(freeze.explicitlyExcludedFromCandidate);
assert(excluded.has('winner_continuation_override'));
assert(excluded.has('hard_first_bar_exit'));
assert(excluded.has('firstBarMfePct_as_router_feature'));

console.log(JSON.stringify({
  status: 'PHASE57_EXIT_V5_CANDIDATE_FREEZE_PREFLIGHT_PASS',
  features: freeze.decisionFeatures.map(x => x.name),
  routeToV3When: freeze.router.routeToV3When,
  unseenStillSealedAtFreeze: !freeze.guards.newUnseenOpenedAtFreezeTime,
  safety: 'ALL_FALSE'
}));
