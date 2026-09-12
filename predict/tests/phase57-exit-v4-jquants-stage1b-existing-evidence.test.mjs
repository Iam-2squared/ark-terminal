import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';

const evidenceUrl = new URL('../research/phase57-exit-v4-jquants-stage1b-existing-tick-evidence-audit-v1.json', import.meta.url);
const digestUrl = new URL('../research/phase57-exit-v4-jquants-stage1b-existing-tick-evidence-audit-v1.sha256', import.meta.url);
const bytes = fs.readFileSync(evidenceUrl);
const evidence = JSON.parse(bytes);
const expectedDigest = fs.readFileSync(digestUrl, 'utf8').trim().split(/\s+/)[0];
const safetyKeys = [
  'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
  'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed',
  'productionUpdateAllowed', 'transmitted',
];

test('Stage 1B evidence is hash-locked and remains a partial existing-evidence gate', () => {
  assert.equal(createHash('sha256').update(bytes).digest('hex'), expectedDigest);
  assert.equal(evidence.status, 'EXISTING_EVIDENCE_PARTIALLY_SUFFICIENT');
  assert.equal(evidence.scope, 'EXISTING_EVIDENCE_DISCOVERY_ONLY_NO_NEW_PROVIDER_ACQUISITION_NO_OUTCOME_ACCESS');
  assert.equal(evidence.stage2AllocationAllowed, false);
  assert.equal(evidence.additionalSealedSessionRequired, false);
});

test('evidence classification and trust levels are explicit and bounded', () => {
  const allowedClasses = new Set([
    'DIRECT_TIMESTAMP_EVIDENCE', 'INDIRECT_TIMESTAMP_EVIDENCE', 'AVAILABLE_AT_EVIDENCE',
    '5M_AGGREGATION_PARITY', 'SESSION_BOUNDARY_EVIDENCE', 'MISSING_SEMANTICS_EVIDENCE',
    'ADJUSTMENT_EVIDENCE', 'NOT_USABLE',
  ]);
  assert.equal(evidence.evidenceInventory.length, evidence.search.relevantEvidenceClusters);
  assert.ok(evidence.evidenceInventory.every((row) => ['A', 'B', 'C', 'D'].includes(row.trustLevel)));
  assert.ok(evidence.evidenceInventory.every((row) => row.classification.every((value) => allowedClasses.has(value))));
  const direct = evidence.evidenceInventory.find((row) => row.id === 'E01');
  assert.equal(direct.trustLevel, 'B');
  assert.equal(direct.rawPresent, false);
  assert.ok(direct.classification.includes('DIRECT_TIMESTAMP_EVIDENCE'));
  assert.match(direct.finding, /61923 J-Quants Tick/);
});

test('timestamp and five-minute contract are causal without claiming provider publication time', () => {
  assert.equal(evidence.timestamp.minuteSemantics, 'PASS_BAR_START');
  assert.equal(evidence.timestamp.intervalClosure, 'LEFT_CLOSED_RIGHT_OPEN');
  assert.equal(evidence.timestamp.row0900Interval, '[09:00:00,09:01:00)');
  assert.deepEqual(evidence.fiveMinuteAggregation.firstRegularBar.includedSourceRows,
    ['09:00', '09:01', '09:02', '09:03', '09:04']);
  assert.equal(evidence.fiveMinuteAggregation.firstRegularBar.decisionTimestamp, '09:05:00_JST');
  assert.equal(evidence.availableAt.status, 'CONDITIONAL_INFERRED_BOUND');
  assert.equal(evidence.availableAt.providerExactAvailableAt, 'UNKNOWN');
  assert.match(evidence.availableAt.restriction, /DO_NOT_CLAIM/);
});

test('monthly Tick is not requested and remaining replay claims stay fail-closed', () => {
  assert.equal(evidence.monthlyTickDecision.requiredNow, false);
  assert.equal(evidence.monthlyTickDecision.requiredForTimestamp, false);
  assert.equal(evidence.monthlyTickDecision.requiredForFiveMinuteContract, false);
  assert.equal(evidence.replay.fullReplayEligibleSessions, 0);
  assert.equal(evidence.replay.confirmedTier2Sessions, 0);
  assert.equal(evidence.replay.goldenParity, 'NOT_RUN');
  assert.equal(evidence.dataSemantics.missingReason, 'FAIL_INCOMPLETE');
});

test('protected, fresh, raw and outcome access counters remain zero and safety remains false', () => {
  assert.ok(Object.values(evidence.accessLedger).every((value) => value === 0));
  assert.ok(safetyKeys.every((key) => evidence.safety[key] === false));
  assert.equal(evidence.frozenIdentifiers.entryThreshold, 'STRICTLY_GREATER_THAN_0.60');
  assert.equal(evidence.frozenIdentifiers.selectorModelDigest,
    '444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2');
});
