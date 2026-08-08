import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE52_SAFETY,
  runEndToEndSafetyAudit,
  injectFailure,
  enforceIdempotency,
  validateRecovery,
  verifyBrokerBoundary,
  validateApprovalIntegrity,
  auditPhase52,
} from '../prelive/phase52-safety.js';

test('52.0 validates complete fail-closed E2E path', () => {
  const result = runEndToEndSafetyAudit({ stages: ['shadow','readiness','candidate','risk','approval','dry_run','audit'] });
  assert.equal(result.status, 'VALID');
  assert.equal(result.safety.liveTradingAllowed, false);
});

test('52.0 blocks incomplete path', () => {
  const result = runEndToEndSafetyAudit({ stages: ['shadow','readiness'] });
  assert.equal(result.status, 'BLOCKED');
  assert.ok(result.blockers.includes('MISSING_STAGE_CANDIDATE'));
});

test('52.1 every injected failure stays blocked', () => {
  for (const kind of ['MISSING_DATA','API_DOWN','STALE_PRICE','OUTLIER','DUPLICATE_RUN','TIMEOUT','CORRUPT_STATE']) {
    const result = injectFailure({ kind });
    assert.equal(result.status, 'BLOCKED');
    assert.equal(result.executionAllowed, false);
  }
});

test('52.2 blocks duplicate operation keys', () => {
  assert.equal(enforceIdempotency({ operationKey: 'x', priorKeys: ['x'] }).status, 'BLOCKED');
  assert.equal(enforceIdempotency({ operationKey: 'y', priorKeys: ['x'] }).status, 'UNIQUE');
});

test('52.3 validates deterministic recovery state', () => {
  const state = { cursor: 12, mode: 'DRY_RUN_ONLY' };
  assert.equal(validateRecovery({ checkpoint: { expectedState: state }, resumedState: state }).status, 'RECOVERABLE');
  assert.equal(validateRecovery({ checkpoint: { expectedState: state }, resumedState: { cursor: 13, mode: 'DRY_RUN_ONLY' } }).status, 'BLOCKED');
});

test('52.4 confirms read-only broker boundary', () => {
  const ok = verifyBrokerBoundary({ counters: {}, imports: ['market.read', 'account.read'] });
  assert.equal(ok.status, 'READ_ONLY_CONFIRMED');
  const bad = verifyBrokerBoundary({ counters: { brokerWriteCount: 1 }, imports: [] });
  assert.equal(bad.status, 'BLOCKED');
});

test('52.5 invalidates approval if candidate or risk changes', () => {
  const candidate = { candidateId: 'c1', symbol: '7203.T', quantity: 10 };
  const risk = { status: 'PASS', limit: 30000 };
  const approval = { status: 'APPROVED_DRY_RUN', candidateId: 'c1', expiresAt: '2030-01-01T00:00:00.000Z' };
  const valid = validateApprovalIntegrity({ candidate, risk, approval, currentCandidate: candidate, currentRisk: risk, now: '2026-08-08T00:00:00.000Z' });
  assert.equal(valid.status, 'VALID');
  const changed = validateApprovalIntegrity({ candidate, risk, approval, currentCandidate: { ...candidate, quantity: 11 }, currentRisk: risk, now: '2026-08-08T00:00:00.000Z' });
  assert.equal(changed.status, 'BLOCKED');
  assert.ok(changed.blockers.includes('CANDIDATE_CHANGED'));
});

test('Phase52 audit rejects any live execution opening', () => {
  const valid = auditPhase52([{ executionAllowed: false, transmitted: false, safety: PHASE52_SAFETY }]);
  assert.equal(valid.status, 'VALID');
  const badSafety = { ...PHASE52_SAFETY, liveTradingAllowed: true };
  assert.equal(auditPhase52([{ executionAllowed: false, transmitted: false, safety: badSafety }]).status, 'BLOCKED');
});
