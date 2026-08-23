import test from 'node:test';
import assert from 'node:assert/strict';
import { replayP25ResearchSignals } from './p25-offline-paper-replay.js';

function signal(overrides = {}) {
  return {
    signalId: 'sig-1', evidenceDate: '2026-08-24', sourceTimestamp: '2026-08-24T00:05:00.000Z',
    symbol: '7203.T', direction: 'UP', universeVariant: 'Dynamic50', modelVersion: 'frozen-p25',
    lineageHeadSha256: 'abc123', ...overrides,
  };
}

test('offline replay fills a research-only long and preserves safety/provenance', () => {
  const result = replayP25ResearchSignals({
    signals: [{ signal: signal(), referencePrice: 2500, markPrice: 2525 }],
    initialCash: 1_000_000, quantity: 100, commissionPerFill: 100, slippageBps: 10,
  });
  assert.equal(result.mode, 'research_offline_only');
  assert.equal(result.executable, false);
  assert.equal(result.events[0].status, 'simulated_fill');
  assert.equal(result.events[0].fillPrice, 2502.5);
  assert.equal(result.events[0].provenance.evidenceDate, '2026-08-24');
  assert.equal(result.account.positions['7203.T'].quantity, 100);
  assert.equal(result.account.positions['7203.T'].marketPrice, 2525);
  for (const value of Object.values(result.safety)) assert.equal(value, false);
});

test('DOWN remains observation-only and never creates a short', () => {
  const result = replayP25ResearchSignals({ signals: [{ signal: signal({ direction: 'DOWN' }), referencePrice: 2500 }] });
  assert.equal(result.events[0].status, 'observe_only');
  assert.equal(Object.keys(result.account.positions).length, 0);
});

test('risk rejection is recorded instead of bypassed', () => {
  const result = replayP25ResearchSignals({
    signals: [{ signal: signal(), referencePrice: 20000 }], initialCash: 100_000, quantity: 100,
  });
  assert.equal(result.events[0].status, 'risk_rejected');
  assert.equal(Object.keys(result.account.positions).length, 0);
});

test('invalid market inputs fail closed', () => {
  assert.throws(() => replayP25ResearchSignals({ signals: [{ signal: signal(), referencePrice: null }] }), /referencePrice/);
  assert.throws(() => replayP25ResearchSignals({ signals: [], slippageBps: -1 }), /slippageBps/);
});
