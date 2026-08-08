import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE51_SAFETY,
  buildOrderCandidate,
  evaluatePreTradeRisk,
  createApprovalState,
  resolveApproval,
  simulateExecution,
  auditPhase51,
} from '../semi-auto/phase51-foundation.js';

function readiness(status = 'READY') {
  return { status };
}

test('Phase51.1 blocks candidate when readiness is not READY', () => {
  const c = buildOrderCandidate({ readiness: readiness('NOT_READY'), symbol: '7203.T', side: 'BUY', referencePrice: 3000, quantity: 1, confidence: 0.8 });
  assert.equal(c.status, 'BLOCKED');
  assert.ok(c.blockers.includes('READINESS_NOT_READY'));
  assert.equal(c.executable, false);
  assert.equal(c.transmitted, false);
});

test('Phase51.1 creates candidate without making it executable', () => {
  const c = buildOrderCandidate({ readiness: readiness(), symbol: '7203.T', side: 'BUY', referencePrice: 3000, quantity: 1, confidence: 0.8 });
  assert.equal(c.status, 'CANDIDATE');
  assert.equal(c.executable, false);
  assert.equal(c.transmitted, false);
  assert.equal(c.safety.executionAllowed, false);
});

test('Phase51.2 enforces pre-trade limits and kill switch', () => {
  const c = buildOrderCandidate({ readiness: readiness(), symbol: '7203.T', side: 'BUY', referencePrice: 3000, quantity: 1, confidence: 0.8 });
  assert.equal(evaluatePreTradeRisk({ candidate: c }).status, 'PASS');
  const blocked = evaluatePreTradeRisk({ candidate: c, killSwitch: true });
  assert.equal(blocked.status, 'BLOCKED');
  assert.ok(blocked.blockers.includes('KILL_SWITCH_ACTIVE'));
  assert.equal(blocked.executionAllowed, false);
});

test('Phase51.3 requires explicit human approval and expires safely', () => {
  const c = buildOrderCandidate({ readiness: readiness(), symbol: '7203.T', side: 'BUY', referencePrice: 3000, quantity: 1, confidence: 0.8 });
  const r = evaluatePreTradeRisk({ candidate: c });
  const a = createApprovalState({ candidate: c, risk: r, now: '2026-08-08T01:00:00Z', expiresAt: '2026-08-08T01:10:00Z' });
  assert.equal(a.status, 'PENDING_HUMAN_APPROVAL');
  const approved = resolveApproval({ approval: a, decision: 'APPROVE', actor: 'tester', now: '2026-08-08T01:05:00Z' });
  assert.equal(approved.status, 'APPROVED_DRY_RUN');
  assert.equal(approved.executionAllowed, false);
  const expired = resolveApproval({ approval: a, decision: 'APPROVE', actor: 'tester', now: '2026-08-08T01:20:00Z' });
  assert.equal(expired.status, 'EXPIRED');
});

test('Phase51.4 approved flow remains simulated only and performs zero writes', () => {
  const c = buildOrderCandidate({ readiness: readiness(), symbol: '7203.T', side: 'BUY', referencePrice: 3000, quantity: 1, confidence: 0.8 });
  const r = evaluatePreTradeRisk({ candidate: c });
  const a = createApprovalState({ candidate: c, risk: r });
  const approved = resolveApproval({ approval: a, decision: 'APPROVE' });
  const sim = simulateExecution({ candidate: c, approval: approved });
  assert.equal(sim.status, 'SIMULATED_ONLY');
  assert.equal(sim.transmittedOrderCount, 0);
  assert.equal(sim.brokerWriteCount, 0);
  assert.equal(sim.excelOrderWriteCount, 0);
  assert.equal(sim.rssOrderFunctionCallCount, 0);
  assert.equal(sim.liveOrderCount, 0);
  assert.equal(sim.executionAllowed, false);
  assert.equal(sim.transmitted, false);
  assert.equal(auditPhase51([c, r, a, approved, sim]).status, 'VALID');
});

test('Phase51.4 kill switch blocks even an approved dry-run', () => {
  const c = buildOrderCandidate({ readiness: readiness(), symbol: '7203.T', side: 'BUY', referencePrice: 3000, quantity: 1, confidence: 0.8 });
  const r = evaluatePreTradeRisk({ candidate: c });
  const a = createApprovalState({ candidate: c, risk: r });
  const approved = resolveApproval({ approval: a, decision: 'APPROVE' });
  const sim = simulateExecution({ candidate: c, approval: approved, killSwitch: true });
  assert.equal(sim.status, 'BLOCKED');
  assert.ok(sim.blockers.includes('KILL_SWITCH_ACTIVE'));
});

test('Phase51 safety contract forbids every live execution surface', () => {
  assert.deepEqual(PHASE51_SAFETY, {
    mode: 'DRY_RUN_ONLY',
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    killSwitchRequired: true,
  });
});
