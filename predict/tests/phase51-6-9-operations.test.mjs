import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildDailyDryRunRecord,
  mergeDailyDryRunHistory,
  evaluateOperationalStability,
  buildOperationsDashboard,
  evaluatePhase51Release,
  verifyPhase51Release,
} from '../semi-auto/phase51-6-9-operations.js';

function record(date, overrides = {}) {
  return buildDailyDryRunRecord({
    date,
    candidateCount: 3,
    simulatedCount: 2,
    auditStatus: 'VALID',
    shadowDivergence: 0.01,
    ...overrides,
  });
}

test('Phase51.6 daily record is dry-run only with zero writes', () => {
  const r = record('2026-08-01');
  assert.equal(r.mode, 'DRY_RUN_ONLY');
  assert.equal(r.executionAllowed, false);
  assert.equal(r.brokerWriteCount, 0);
  assert.equal(r.excelOrderWriteCount, 0);
  assert.equal(r.rssOrderFunctionCallCount, 0);
  assert.equal(r.liveOrderCount, 0);
});

test('Phase51.6 history deduplicates by date', () => {
  const a = record('2026-08-01', { simulatedCount: 1 });
  const b = record('2026-08-01', { simulatedCount: 4 });
  const h = mergeDailyDryRunHistory([a], b);
  assert.equal(h.length, 1);
  assert.equal(h[0].simulatedCount, 4);
});

test('Phase51.7 becomes stable only with enough clean days', () => {
  const history = Array.from({ length: 20 }, (_, i) => record(`2026-08-${String(i + 1).padStart(2, '0')}`));
  const s = evaluateOperationalStability(history);
  assert.equal(s.status, 'STABLE');
  assert.equal(s.executionAllowed, false);
});

test('Phase51.7 blocks unstable audit or divergence', () => {
  const history = Array.from({ length: 20 }, (_, i) => record(`2026-08-${String(i + 1).padStart(2, '0')}`));
  history[3] = record('2026-08-04', { auditStatus: 'BLOCKED' });
  history[5] = record('2026-08-06', { shadowDivergence: 0.08 });
  const s = evaluateOperationalStability(history);
  assert.equal(s.status, 'NOT_STABLE');
  assert.ok(s.blockers.includes('AUDIT_FAILURE_RATE_ABOVE_GATE'));
  assert.ok(s.blockers.includes('SHADOW_DIVERGENCE_ABOVE_GATE'));
});

test('Phase51.8 dashboard raises review-only alerts', () => {
  const history = [record('2026-08-01', { killSwitchCount: 1 })];
  const stability = evaluateOperationalStability(history, { minDays: 1 });
  const d = buildOperationsDashboard({ history, stability });
  assert.equal(d.executionAllowed, false);
  assert.equal(d.humanReviewRequired, true);
});

test('Phase51.9 can be release-ready only for dry-run', () => {
  const history = Array.from({ length: 20 }, (_, i) => record(`2026-08-${String(i + 1).padStart(2, '0')}`));
  const stability = evaluateOperationalStability(history);
  const dashboard = buildOperationsDashboard({ history, stability });
  const release = evaluatePhase51Release({ foundationAudit: { status: 'VALID' }, stability, dashboard });
  assert.equal(release.status, 'RELEASE_READY_FOR_DRY_RUN_ONLY');
  assert.equal(release.executionAllowed, false);
  assert.equal(release.liveTradingAllowed, false);
  assert.equal(release.automaticPromotionAllowed, false);
  assert.equal(release.productionUpdateAllowed, false);
  assert.equal(verifyPhase51Release(release).status, 'VALID');
});

test('Phase51.9 fails closed when stability is not ready', () => {
  const stability = evaluateOperationalStability([record('2026-08-01')]);
  const dashboard = buildOperationsDashboard({ history: [record('2026-08-01')], stability });
  const release = evaluatePhase51Release({ foundationAudit: { status: 'VALID' }, stability, dashboard });
  assert.equal(release.status, 'BLOCKED');
});
