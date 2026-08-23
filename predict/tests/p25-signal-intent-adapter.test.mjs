import assert from 'node:assert/strict';
import test from 'node:test';

import {
  P25_SIGNAL_INTENT_SAFETY,
  createP25ResearchIntent,
  toPaperOrderResearchDraft,
} from '../paper/p25-signal-intent-adapter.js';

const base = {
  signalId: 'sig-2026-08-19-7203-up',
  evidenceDate: '2026-08-19',
  sourceTimestamp: '2026-08-19T05:00:00.000Z',
  symbol: '7203',
  direction: 'UP',
  universeVariant: 'Dynamic50',
  modelVersion: 'phase57-frozen',
  lineageHeadSha256: 'abc123',
  confidence: 0.81,
  score: 1.7,
  setup: 'Q4_HIGH',
};

test('P25 signal intent remains research-only with provenance', () => {
  const intent = createP25ResearchIntent(base);
  assert.equal(intent.symbol, '7203');
  assert.equal(intent.direction, 'UP');
  assert.equal(intent.disposition, 'paper_long_candidate');
  assert.equal(intent.executable, false);
  assert.equal(intent.brokerPayload, null);
  assert.equal(intent.paperOrderPayload, null);
  assert.equal(intent.lineageHeadSha256, 'abc123');
  for (const value of Object.values(P25_SIGNAL_INTENT_SAFETY)) assert.equal(value, false);
});

test('UP can produce a non-executable research paper-order draft', () => {
  const draft = toPaperOrderResearchDraft(createP25ResearchIntent(base), { quantity: 100 });
  assert.equal(draft.eligible, true);
  assert.equal(draft.executable, false);
  assert.deepEqual(
    { symbol: draft.orderInput.symbol, side: draft.orderInput.side, quantity: draft.orderInput.quantity },
    { symbol: '7203', side: 'buy', quantity: 100 },
  );
  assert.equal(draft.orderInput.metadata.researchOnly, true);
  assert.equal(draft.orderInput.metadata.universeVariant, 'Dynamic50');
});

test('DOWN remains observation-only because short is disabled', () => {
  const intent = createP25ResearchIntent({ ...base, signalId: 'sig-down', direction: 'DOWN' });
  assert.equal(intent.disposition, 'observe_down_only');
  const draft = toPaperOrderResearchDraft(intent);
  assert.deepEqual(draft, { eligible: false, reason: 'short_disabled', orderInput: null });
});

test('adapter fails closed for missing provenance and invalid lots', () => {
  assert.throws(() => createP25ResearchIntent({ ...base, lineageHeadSha256: '' }), /lineageHeadSha256 is required/);
  const intent = createP25ResearchIntent(base);
  assert.throws(() => toPaperOrderResearchDraft(intent, { quantity: 50 }), /100-share lot/);
});
