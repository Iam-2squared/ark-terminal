import test from 'node:test';
import assert from 'node:assert/strict';
import {
  P23_8C_EXIT_CANDIDATES,
  P23_8C_NEW_CANDIDATE_IDS,
  P23_8C_METHOD_POLICY,
  PHASE57_P23_8C_SAFETY,
} from '../daytrade/phase57-p23-8c-exit-candidates.js';

const safetyFalse = [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
];

test('P23.8C remains fail-closed and research-only', () => {
  for (const key of safetyFalse) assert.equal(PHASE57_P23_8C_SAFETY[key], false, key);
  assert.equal(PHASE57_P23_8C_SAFETY.humanApprovalRequired, true);
  assert.equal(P23_8C_METHOD_POLICY.finalUntouchedOosEdgeClaimAllowed, false);
  assert.equal(P23_8C_METHOD_POLICY.futureExtremaUsedForDecision, false);
  assert.equal(P23_8C_METHOD_POLICY.futureExtremaUsedForCandidateSelection, false);
  assert.equal(P23_8C_METHOD_POLICY.entryThresholdsChanged, false);
  assert.equal(P23_8C_METHOD_POLICY.roundTripCostChanged, false);
  assert.equal(P23_8C_METHOD_POLICY.p23_8DiagnosticsInformedCandidateDesign, true);
  assert.equal(P23_8C_METHOD_POLICY.reusedRecentDevelopmentWindow, true);
});

test('P23.8C candidate universe is frozen, unique and retains prior controls', () => {
  const ids = P23_8C_EXIT_CANDIDATES.map(candidate => candidate.id);
  assert.equal(new Set(ids).size, ids.length);
  for (const id of ['STATE_BALANCED_V1','STATE_PATIENT_TREND_V1','STATE_STRUCTURE_FIRST_V1']) assert.ok(ids.includes(id), id);
  for (const id of P23_8C_NEW_CANDIDATE_IDS) assert.ok(ids.includes(id), id);
  assert.deepEqual(P23_8C_NEW_CANDIDATE_IDS, [
    'STATE_PATIENT_PROFIT_CAPTURE_V2',
    'STATE_ASYMMETRIC_DEFENSE_V2',
    'STATE_STRUCTURE_RUNNER_V2',
  ]);
});

test('P23.8C new candidates encode patient mild-damage handling plus explicit risk defense', () => {
  const byId = Object.fromEntries(P23_8C_EXIT_CANDIDATES.map(candidate => [candidate.id, candidate.config]));
  const patient = byId.STATE_PATIENT_PROFIT_CAPTURE_V2;
  const defense = byId.STATE_ASYMMETRIC_DEFENSE_V2;
  const runner = byId.STATE_STRUCTURE_RUNNER_V2;

  assert.ok(patient.cautionConfirmBars >= 3);
  assert.ok(patient.cautionExitDamageVotes >= 5);
  assert.ok(patient.profitProtectActivationAtr <= 1.5);
  assert.ok(patient.profitProtectGivebackAtrCaution < patient.profitProtectGivebackAtrStrong);

  assert.ok(defense.hardStopAtr < 1.5);
  assert.equal(defense.severeBreakdownConfirmBars, 1);
  assert.ok(defense.profitProtectActivationAtr <= 1.5);

  assert.ok(runner.swingBars >= 5);
  assert.ok(runner.cautionConfirmBars >= 3);
  assert.equal(runner.severeBreakdownConfirmBars, 1);
});
