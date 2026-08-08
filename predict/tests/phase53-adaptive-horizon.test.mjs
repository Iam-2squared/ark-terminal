import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateAdaptiveHorizon, PHASE53_HORIZON_SAFETY } from '../adaptive/phase53-horizon-integration.js';

function row(period, value, hit = value > 0) {
  return {
    status: 'resolved',
    period,
    strategyReturn: value,
    actualReturn: value,
    hit,
    createdAt: '2026-08-01T00:00:00.000Z',
  };
}

test('selects only a sufficiently separated OOS horizon candidate', () => {
  const records = [
    ...Array.from({ length: 10 }, () => row(1, 0.1, true)),
    ...Array.from({ length: 10 }, () => row(3, 1.0, true)),
    ...Array.from({ length: 10 }, (_, i) => row(5, i < 6 ? 0.2 : -0.2, i < 6)),
  ];
  const result = evaluateAdaptiveHorizon(records, { minimumSamples: 10, minimumLead: 0.1 });
  assert.equal(result.status, 'ADAPTIVE_HORIZON_CANDIDATE');
  assert.equal(result.selectedHorizon, 3);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.liveTradingAllowed, false);
  assert.equal(result.transmitted, false);
});

test('fails closed when OOS evidence is insufficient', () => {
  const result = evaluateAdaptiveHorizon([row(1, 1, true)], { minimumSamples: 10 });
  assert.equal(result.status, 'OBSERVE');
  assert.equal(result.selectedHorizon, null);
  assert.ok(result.blockers.includes('INSUFFICIENT_HORIZON_OOS'));
});

test('fails closed when best and second best are too close', () => {
  const records = [
    ...Array.from({ length: 10 }, () => row(1, 0.5, true)),
    ...Array.from({ length: 10 }, () => row(3, 0.5, true)),
  ];
  const result = evaluateAdaptiveHorizon(records, { minimumSamples: 10, minimumLead: 0.5 });
  assert.equal(result.status, 'OBSERVE');
  assert.equal(result.selectedHorizon, null);
  assert.ok(result.blockers.includes('HORIZON_LEAD_TOO_SMALL'));
});

test('keeps all Phase53 safety boundaries disabled', () => {
  assert.deepEqual(PHASE53_HORIZON_SAFETY, {
    mode: 'ADAPTIVE_HORIZON_REVIEW_ONLY',
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  });
});
