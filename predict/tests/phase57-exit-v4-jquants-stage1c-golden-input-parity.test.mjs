import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';

const evidenceUrl = new URL('../research/phase57-exit-v4-jquants-stage1c-golden-input-parity-v1.json', import.meta.url);
const digestUrl = new URL('../research/phase57-exit-v4-jquants-stage1c-golden-input-parity-v1.sha256', import.meta.url);
const bytes = fs.readFileSync(evidenceUrl);
const evidence = JSON.parse(bytes);
const expectedDigest = fs.readFileSync(digestUrl, 'utf8').trim().split(/\s+/)[0];

test('Stage 1C evidence is hash locked and stops when Golden A/B is not safely recoverable', () => {
  assert.equal(createHash('sha256').update(bytes).digest('hex'), expectedDigest);
  assert.equal(evidence.status, 'GOLDEN_PARITY_NOT_RECOVERABLE');
  assert.equal(evidence.hardStop, 'ACTIVE');
  assert.equal(evidence.scope, 'GOLDEN_RECOVERABILITY_ONLY_NO_PARITY_EXECUTION_NO_PROVIDER_ACCESS_NO_OUTCOME_ACCESS');
  assert.equal(evidence.eligibility.stage2AllocationAllowed, false);
});

test('only the three already exposed pilot sessions are named', () => {
  assert.deepEqual(evidence.pilotSessions, ['2025-08-27', '2025-10-09', '2025-11-25']);
  assert.deepEqual(evidence.goldenRecoverability.map((row) => row.sessionDate), evidence.pilotSessions);
  assert.ok(evidence.goldenRecoverability.every((row) => row.accessibleGoldenLevel === 'C'));
  assert.ok(evidence.goldenRecoverability.every((row) => row.candidateGoldenB.artifactDownloaded === false));
  assert.ok(evidence.goldenRecoverability.every((row) => row.candidateGoldenB.sessionsInArtifact > 1));
});

test('all six parity layers remain independently fail closed', () => {
  assert.deepEqual(evidence.parityLayers.map((row) => row.layer), [
    'DATA_BAR', 'HYBRID_INPUT', 'HYBRID_OUTPUT', 'MSH_FEATURE', 'MSH_STATE', 'ENTRY_EVENT',
  ]);
  assert.equal(evidence.parityLayers.find((row) => row.layer === 'DATA_BAR').status, 'PARTIAL');
  assert.ok(evidence.parityLayers.filter((row) => row.layer !== 'DATA_BAR').every((row) => row.status === 'NOT_RECOVERABLE'));
  assert.ok(evidence.parityLayers.every((row) => row.comparableRows === 0 && row.mismatch === 0));
});

test('all ten MSH features and frozen identifiers remain unchanged', () => {
  assert.equal(evidence.mshFeatureParity.length, 10);
  assert.equal(evidence.mshFeatureParityStatus, 'ALL_TEN_NOT_RECOVERABLE_ZERO_COMPARABLE_ROWS');
  assert.equal(evidence.frozenIdentifiers.entryThreshold, 'STRICTLY_GREATER_THAN_0.60');
  assert.equal(evidence.frozenIdentifiers.selectorModelDigest,
    '444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2');
  assert.equal(evidence.frozenIdentifiers.selectorFreezeSha256,
    'a744d599e430d23efe4dea6600e418d3410d8a18df5055b35e1cc71432bf64da');
});

test('no provider, raw, protected, fresh, outcome, label or EXIT access occurred', () => {
  assert.ok(Object.values(evidence.accessLedger).every((value) => value === 0));
  assert.equal(evidence.quality.pitViolations, 0);
  assert.equal(evidence.eligibility.fullReplayEligibleSessions, 0);
  assert.equal(evidence.eligibility.confirmedTier2Sessions, 0);
  assert.ok(Object.values(evidence.safety).every((value) => value === false));
});

test('a multi-session candidate bundle cannot be silently promoted to recoverable Golden B', () => {
  for (const row of evidence.goldenRecoverability) {
    assert.equal(row.candidateGoldenB.exists, true);
    assert.equal(row.candidateGoldenB.preOutcome, true);
    assert.equal(row.candidateGoldenB.labelsGenerated, false);
    assert.match(row.candidateGoldenB.isolationFailure, /OUT_OF_SCOPE_SESSIONS/);
    assert.match(row.verdict, /NOT_RECOVERABLE/);
  }
});
