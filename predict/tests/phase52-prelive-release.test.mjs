import test from 'node:test';
import assert from 'node:assert/strict';
import {
  aggregateDryRunEvidence,
  evaluateAnomalyRate,
  evaluateSustainedSafety,
  evaluatePreLiveReleaseGate,
} from '../prelive/phase52-release-gate.js';

function safeRecord(overrides = {}) {
  return {
    mode: 'DRY_RUN_ONLY',
    status: 'SIMULATED_ONLY',
    anomalyCount: 0,
    executionAllowed: false,
    transmitted: false,
    brokerWriteCount: 0,
    excelOrderWriteCount: 0,
    rssOrderFunctionCallCount: 0,
    liveOrderCount: 0,
    ...overrides,
  };
}

test('52.6 aggregates valid dry-run evidence and preserves zero execution', () => {
  const evidence = aggregateDryRunEvidence(Array.from({ length: 20 }, () => safeRecord()));
  assert.equal(evidence.status, 'VALID');
  assert.equal(evidence.sampleCount, 20);
  assert.equal(evidence.executionAllowed, false);
  assert.equal(evidence.transmitted, false);
});

test('52.6 uses explicit simulatedCount instead of inferring a simulation from a valid day', () => {
  const evidence = aggregateDryRunEvidence([
    safeRecord({ simulatedCount: 0 }),
    safeRecord({ simulatedCount: 3 }),
  ]);
  assert.equal(evidence.sampleCount, 2);
  assert.equal(evidence.simulatedCount, 3);
});

test('52.6 blocks on any write/transmission violation', () => {
  const evidence = aggregateDryRunEvidence([safeRecord({ brokerWriteCount: 1 })]);
  assert.equal(evidence.status, 'BLOCKED');
  assert.equal(evidence.safetyViolationCount, 1);
});

test('52.7 requires enough samples and low anomaly/blocked rates', () => {
  const evidence = aggregateDryRunEvidence(Array.from({ length: 20 }, () => safeRecord()));
  const result = evaluateAnomalyRate({ evidence });
  assert.equal(result.status, 'PASS');
});

test('52.7 fails closed when evidence is too small', () => {
  const evidence = aggregateDryRunEvidence(Array.from({ length: 5 }, () => safeRecord()));
  const result = evaluateAnomalyRate({ evidence });
  assert.equal(result.status, 'NOT_READY');
  assert.ok(result.blockers.includes('INSUFFICIENT_SAMPLES'));
});

test('52.8 requires sustained safe days', () => {
  const evidence = aggregateDryRunEvidence(Array.from({ length: 20 }, () => safeRecord()));
  const anomalyEvaluation = evaluateAnomalyRate({ evidence });
  assert.equal(evaluateSustainedSafety({ evidence, anomalyEvaluation, consecutiveSafeDays: 10 }).status, 'STABLE');
  assert.equal(evaluateSustainedSafety({ evidence, anomalyEvaluation, consecutiveSafeDays: 9 }).status, 'NOT_READY');
});

test('52.9 can only become PRE_LIVE_REVIEW_READY, never executable', () => {
  const evidence = aggregateDryRunEvidence(Array.from({ length: 20 }, () => safeRecord()));
  const anomalyEvaluation = evaluateAnomalyRate({ evidence });
  const sustainedSafety = evaluateSustainedSafety({ evidence, anomalyEvaluation, consecutiveSafeDays: 10 });
  const gate = evaluatePreLiveReleaseGate({
    evidence,
    anomalyEvaluation,
    sustainedSafety,
    boundaryAudit: { status: 'VALID' },
    approvalIntegrity: { status: 'VALID' },
  });
  assert.equal(gate.status, 'PRE_LIVE_REVIEW_READY');
  assert.equal(gate.executionAllowed, false);
  assert.equal(gate.brokerWriteAllowed, false);
  assert.equal(gate.excelOrderWriteAllowed, false);
  assert.equal(gate.rssOrderFunctionAllowed, false);
  assert.equal(gate.liveTradingAllowed, false);
  assert.equal(gate.automaticPromotionAllowed, false);
  assert.equal(gate.productionUpdateAllowed, false);
  assert.equal(gate.humanApprovalRequired, true);
});

test('52.9 blocks if broker boundary or approval integrity is blocked', () => {
  const evidence = aggregateDryRunEvidence(Array.from({ length: 20 }, () => safeRecord()));
  const anomalyEvaluation = evaluateAnomalyRate({ evidence });
  const sustainedSafety = evaluateSustainedSafety({ evidence, anomalyEvaluation, consecutiveSafeDays: 10 });
  const gate = evaluatePreLiveReleaseGate({
    evidence,
    anomalyEvaluation,
    sustainedSafety,
    boundaryAudit: { status: 'BLOCKED' },
    approvalIntegrity: { status: 'VALID' },
  });
  assert.equal(gate.status, 'BLOCKED');
  assert.equal(gate.executionAllowed, false);
});
