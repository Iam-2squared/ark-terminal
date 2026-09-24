import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {
  ENTRY_V2_SESSION_EXPANSION_POLICY,
  ENTRY_V2_SESSION_EXPANSION_SAFETY,
  assessHistoricalProvider,
  buildSessionCheckpointProjection,
  classifyHistoricalP21Replay,
  describeFrozenP21PriorDependency,
  validateOverlapPilotManifest,
} from '../daytrade/phase57-entry-quality-v2-session-regime-expansion.js';

const evidence = JSON.parse(fs.readFileSync(new URL(
  '../daytrade/phase57-entry-quality-v2-session-regime-expansion-2026-09-05.json', import.meta.url,
), 'utf8'));

const falseSafetyKeys = [
  'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
  'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted',
];

test('Frozen P21 dependency remains the exact policy and requires causal realized priors', () => {
  const dependency = describeFrozenP21PriorDependency();
  assert.equal(dependency.policyId, 'PHASE57_P24_COMBINED_PROSPECTIVE_V1');
  assert.deepEqual(dependency.historicalUniverse, ['7203.T', '6758.T', '9984.T', '8306.T', '8035.T']);
  assert.deepEqual(dependency.horizonsBars, [1, 3, 6, 12, 24]);
  assert.equal(dependency.selectionOptions.innerMinTrainRows, 200);
  assert.equal(dependency.selectionOptions.minInnerSignals, 50);
  assert.equal(dependency.methodologyFrozenNotParameterVector, true);
});

test('current frozen history cannot be projected backward and historical methodology stays a separate class', () => {
  const leaked = classifyHistoricalP21Replay({
    decisionSessionDate: '2026-07-01', historyEndSessionDate: '2026-08-12', usesCurrentFrozenHistoryPack: true,
  });
  assert.equal(leaked.eligible, false);
  assert.equal(leaked.pitViolationPrevented, true);

  const forward = classifyHistoricalP21Replay({
    decisionSessionDate: '2026-08-13', historyEndSessionDate: '2026-08-12', usesCurrentFrozenHistoryPack: true,
  });
  assert.equal(forward.researchClass, 'CURRENT_FROZEN_P21_BASELINE');

  const reconstructed = classifyHistoricalP21Replay({
    decisionSessionDate: '2025-06-02', historyEndSessionDate: '2025-05-30', historyBuiltOnlyFromDataAvailableBeforeDecision: true,
  });
  assert.equal(reconstructed.researchClass, 'HISTORICALLY_RECONSTRUCTED_P21_METHODOLOGY');
  assert.equal(reconstructed.sameAsCurrentFrozenBaseline, false);
});

test('provider adoption and overlap pilot fail closed until semantics and parity are proven', () => {
  const unpiloted = assessHistoricalProvider({
    providerId: 'JQUANTS_API_V2_MINUTE',
    timestampSemanticsDocumented: false,
    ohlcvSemanticsDocumented: true,
    rawFingerprintRetainable: true,
    sourceLineageRetainable: true,
    corporateActionSemanticsDocumented: false,
    historicalUniverseCoverageAuditable: true,
    intendedUseLicensed: false,
  });
  assert.equal(unpiloted.adoptionReady, false);
  assert.equal(unpiloted.pilotRequired, true);
  assert.ok(unpiloted.blockers.includes('timestampSemantics'));

  const manifest = validateOverlapPilotManifest(evidence.overlapPilot.manifest);
  assert.equal(manifest.valid, true);
  assert.equal(evidence.overlapPilot.executed, false);
  assert.equal(evidence.overlapPilot.blocker, 'JQUANTS_API_KEY_NOT_CONFIGURED_AND_USE_RIGHTS_NOT_CONFIRMED');
});

test('session checkpoints are planning estimates, never performance forecasts', () => {
  const projection = buildSessionCheckpointProjection({ currentSessions: 16, currentCandidates: 445, maximumAdditionalSessions: 470 });
  assert.equal(projection.checkpoints[30].reachableByProviderPeriod, true);
  assert.equal(projection.checkpoints[50].additionalSessionsRequired, 34);
  assert.equal(projection.checkpoints[100].performanceForecast, false);
});

test('evidence preserves Phase 0 NO-GO, no new sessions, and all safety boundaries', () => {
  assert.equal(evidence.status, 'SOURCE_FEASIBILITY_AUDIT_COMPLETE_PHASE0_NO_GO');
  assert.equal(evidence.datasetChange.newSessionsAdded, 0);
  assert.equal(evidence.datasetChange.pitViolations, 0);
  assert.equal(evidence.phase0Reaudit.decision, 'NO_GO');
  assert.equal(evidence.phase0Reaudit.modelFittingPerformed, false);
  assert.equal(evidence.providers.jquantsApiMinute.adoptionReady, false);
  assert.equal(evidence.providers.jpxFlexHistorical.adoptionReady, false);
  assert.equal(ENTRY_V2_SESSION_EXPANSION_POLICY.modelFittingAllowed, false);
  for (const key of falseSafetyKeys) assert.equal(evidence.safety[key], false, key);
  for (const key of falseSafetyKeys) assert.equal(ENTRY_V2_SESSION_EXPANSION_SAFETY[key], false, key);
});
