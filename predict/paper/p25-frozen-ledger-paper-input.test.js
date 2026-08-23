import test from 'node:test';
import assert from 'node:assert/strict';
import { buildP25ResearchPaperInputs } from './p25-frozen-ledger-paper-input.js';

function ledger(overrides = {}) {
  return {
    frozenTrades: [{
      symbol: '7203.T',
      sessionDate: '2026-08-24',
      entryTimestamp: '2026-08-24T00:10:00.000Z',
      featureCutoff: '2026-08-24T00:10:00.000Z',
      direction: 'LONG',
      signalDirection: 1,
      modelId: 'phase57-p25-frozen',
      confidence: 0.7,
      probability: 0.7,
      selectedFeatureFamily: 'MOMENTUM',
      baseHorizonBars: 12,
      artifactSha256: 'artifact',
      selectedThreshold: 0.6,
      variantMemberships: ['DYNAMIC_30','DYNAMIC_40','DYNAMIC_50'],
      frozenBeforeOutcome: true,
      currentOutcomeUsed: false,
      ...overrides,
    }],
  };
}

const bars = {
  '7203.T': [
    { timestamp:'2026-08-24T00:05:00.000Z', close:2500 },
    { timestamp:'2026-08-24T00:10:00.000Z', close:2510 },
    { timestamp:'2026-08-24T00:15:00.000Z', close:9999 },
  ],
};

test('exports frozen outcome-free trade with point-in-time reference price only', () => {
  const out = buildP25ResearchPaperInputs({ frozenLedger:ledger(), sessionBarsBySymbol:bars, lineageHeadSha256:'lineage' });
  assert.equal(out.mode, 'research_offline_only');
  assert.equal(out.executable, false);
  assert.equal(out.rows[0].referencePrice, 2510);
  assert.equal(out.rows[0].referenceTimestamp, '2026-08-24T00:10:00.000Z');
  assert.equal(out.rows[0].signal.direction, 'UP');
  assert.equal(out.rows[0].signal.metadata.currentOutcomeUsed, false);
  assert.equal(out.methodology.futureBarSelectionAllowed, false);
  for (const value of Object.values(out.safety)) assert.equal(value, false);
});

test('SHORT becomes DOWN research observation rather than a long', () => {
  const out = buildP25ResearchPaperInputs({ frozenLedger:ledger({ direction:'SHORT', signalDirection:-1 }), sessionBarsBySymbol:bars, lineageHeadSha256:'lineage' });
  assert.equal(out.rows[0].signal.direction, 'DOWN');
});

test('rejects outcome-contaminated trades and missing point-in-time bars', () => {
  assert.throws(() => buildP25ResearchPaperInputs({ frozenLedger:ledger({ currentOutcomeUsed:true }), sessionBarsBySymbol:bars, lineageHeadSha256:'lineage' }), /outcome-free/);
  assert.throws(() => buildP25ResearchPaperInputs({ frozenLedger:ledger(), sessionBarsBySymbol:{'7203.T':[{timestamp:'2026-08-24T00:15:00.000Z',close:2520}]}, lineageHeadSha256:'lineage' }), /no point-in-time reference bar/);
});

test('supports nested capture bars shape and never selects a future bar', () => {
  const nested = {'7203.T':{bars:[{time:'2026-08-24T00:05:00.000Z',c:2495},{time:'2026-08-24T00:15:00.000Z',c:2600}]}};
  const out = buildP25ResearchPaperInputs({ frozenLedger:ledger(), sessionBarsBySymbol:nested, lineageHeadSha256:'lineage' });
  assert.equal(out.rows[0].referencePrice, 2495);
  assert.equal(out.rows[0].referenceTimestamp, '2026-08-24T00:05:00.000Z');
});
