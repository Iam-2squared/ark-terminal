import test from 'node:test';
import assert from 'node:assert/strict';
import { buildAdaptiveHorizonOperationalView, PHASE53_1_SAFETY } from '../adaptive/phase53-operational-wiring.js';

function row(period, value, hit = value > 0) {
  return {
    status: 'resolved',
    partition: 'test',
    period,
    strategyReturn: value,
    actualReturn: value,
    hit,
    createdAt: '2026-08-01T00:00:00.000Z',
  };
}

test('exposes the selected horizon for evaluation only', () => {
  const records = [
    ...Array.from({ length: 10 }, (_, i) => row(1, i < 6 ? 0.1 : -0.1, i < 6)),
    ...Array.from({ length: 10 }, () => row(3, 2.0, true)),
    ...Array.from({ length: 10 }, (_, i) => row(5, i < 6 ? 0.2 : -0.2, i < 6)),
  ];
  const view = buildAdaptiveHorizonOperationalView(records, { minimumSamples: 10, minimumLead: 0.1 });
  assert.equal(view.status, 'ADAPTIVE_HORIZON_CANDIDATE');
  assert.equal(view.activeForEvaluation, true);
  assert.equal(view.selectedHorizon, 3);
  assert.equal(view.displayHorizon, 3);
  assert.equal(view.executionAllowed, false);
  assert.equal(view.liveTradingAllowed, false);
  assert.equal(view.transmitted, false);
});

test('fails closed when adaptive horizon gate is not ready', () => {
  const view = buildAdaptiveHorizonOperationalView([row(1, 1, true)], { minimumSamples: 10 });
  assert.equal(view.status, 'OBSERVE');
  assert.equal(view.activeForEvaluation, false);
  assert.equal(view.selectedHorizon, null);
  assert.equal(view.executionAllowed, false);
});

test('keeps all Phase53.1 operational boundaries read-only', () => {
  assert.deepEqual(PHASE53_1_SAFETY, {
    mode: 'ADAPTIVE_HORIZON_OPERATIONAL_WIRING_READ_ONLY',
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
