import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_ENTRY_QUALITY_V2_EVIDENCE_POLICY,
  extractEntryQualityV2FrozenEvidence,
} from '../daytrade/phase57-entry-quality-v2-evidence-adapter.js';

function baselineEntry(overrides = {}) {
  return {
    candidateId: '2026-09-04|2026-09-04T01:30:00.000Z|DYNAMIC5M_V1|TEST.T',
    batchEntryKey: '2026-09-04|2026-09-04T01:30:00.000Z|TEST.T',
    entryAccepted: true,
    symbol: 'TEST.T',
    sessionDate: '2026-09-04',
    entryTimestamp: '2026-09-04T01:30:00.000Z',
    direction: 'LONG',
    entryPrice: 100,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    contextBars: [
      { timestamp: '2026-09-04T01:15:00.000Z', open: 98, high: 100, low: 97, close: 99, volume: 1000 },
      { timestamp: '2026-09-04T01:20:00.000Z', open: 99, high: 101, low: 98, close: 100, volume: 1100 },
      { timestamp: '2026-09-04T01:25:00.000Z', open: 100, high: 102, low: 99, close: 101, volume: 1200 },
    ],
    selectionLineage: {
      variant: 'V1',
      variantId: 'DYNAMIC5M_V1',
      selectionTimestamp: '2026-09-04T01:30:00.000Z',
      sourceAsOf: '2026-09-04T01:30:00.000Z',
      selectorCandidateId: 'selector-v1-0130',
      opportunityScore: 0.72,
      v2Score: null,
    },
    ...overrides,
  };
}

test('evidence adapter stays read-only and never applies a post-hoc universe exclusion', () => {
  const lowPrice = baselineEntry({ symbol: 'LOW.T', entryPrice: 10 });
  const result = extractEntryQualityV2FrozenEvidence({ frozenEntries: [lowPrice] }, { sourceId: 'synthetic' });

  assert.equal(PHASE57_ENTRY_QUALITY_V2_EVIDENCE_POLICY.allowPostHocUniverseExclusion, false);
  assert.equal(PHASE57_ENTRY_QUALITY_V2_EVIDENCE_POLICY.emitNewSignal, false);
  assert.equal(result.entryCount, 1);
  assert.equal(result.entries[0].entryPrice, 10);
  assert.equal(result.entries[0].universeExcluded, false);
  assert.equal(result.entries[0].newSignalEmitted, false);
  assert.equal(result.safety.executionAllowed, false);
  assert.equal(result.safety.automaticPromotionAllowed, false);
});

test('adapter accepts realtime session entry history and preserves selector lineage/context bars', () => {
  const entry = baselineEntry();
  const result = extractEntryQualityV2FrozenEvidence({
    entry: {
      history: [
        { at: entry.entryTimestamp, frozenEntries: [entry] },
      ],
    },
  });

  assert.equal(result.status, 'VALID_FROZEN_EVIDENCE_READ_ONLY');
  assert.equal(result.entryCount, 1);
  assert.equal(result.entries[0].selector.variant, 'V1');
  assert.equal(result.entries[0].selector.selectorCandidateId, 'selector-v1-0130');
  assert.equal(result.entries[0].contextBars.length, 3);
  assert.match(result.entries[0].contextBarsSha256, /^[a-f0-9]{64}$/);
});

test('adapter inventories all historical Frozen Entry points when latest and history coexist', () => {
  const latest = baselineEntry();
  const earlierTimestamp = '2026-09-04T01:25:00.000Z';
  const earlier = baselineEntry({
    candidateId: '2026-09-04|2026-09-04T01:25:00.000Z|DYNAMIC5M_V1|TEST.T',
    batchEntryKey: '2026-09-04|2026-09-04T01:25:00.000Z|TEST.T',
    entryTimestamp: earlierTimestamp,
    contextBars: baselineEntry().contextBars.slice(0, 2),
    selectionLineage: {
      ...baselineEntry().selectionLineage,
      selectionTimestamp: earlierTimestamp,
      sourceAsOf: earlierTimestamp,
      selectorCandidateId: 'selector-v1-0125',
    },
  });
  const result = extractEntryQualityV2FrozenEvidence({
    entry: {
      latest: [latest],
      history: [
        { at: earlier.entryTimestamp, frozenEntries: [earlier] },
        { at: latest.entryTimestamp, frozenEntries: [latest] },
      ],
    },
  });
  assert.equal(result.entryCount, 2);
  assert.deepEqual(result.entries.map(row => row.entryTimestamp), [earlierTimestamp, latest.entryTimestamp]);
});

test('adapter fails closed when baseline was not frozen before outcome', () => {
  assert.throws(
    () => extractEntryQualityV2FrozenEvidence([baselineEntry({ frozenBeforeOutcome: false })]),
    /ENTRY_V2_EVIDENCE_BASELINE_CAUSAL_ATTESTATION_FAILED/,
  );
});

test('adapter rejects an unclosed 5m context bar', () => {
  const entry = baselineEntry({
    contextBars: [
      { timestamp: '2026-09-04T01:30:00.000Z', open: 100, high: 101, low: 99, close: 100, volume: 1000 },
    ],
  });
  assert.throws(
    () => extractEntryQualityV2FrozenEvidence([entry]),
    /ENTRY_V2_EVIDENCE_UNCLOSED_CONTEXT_BAR/,
  );
});

test('adapter requires selector timestamp to equal entry timestamp', () => {
  const entry = baselineEntry({
    selectionLineage: {
      ...baselineEntry().selectionLineage,
      selectionTimestamp: '2026-09-04T01:25:00.000Z',
    },
  });
  assert.throws(
    () => extractEntryQualityV2FrozenEvidence([entry]),
    /ENTRY_V2_EVIDENCE_SELECTION_TIMESTAMP_MISMATCH/,
  );
});

test('adapter rejects duplicate candidate evidence rather than silently deduplicating', () => {
  const entry = baselineEntry();
  assert.throws(
    () => extractEntryQualityV2FrozenEvidence([entry, { ...entry }]),
    /ENTRY_V2_EVIDENCE_DUPLICATE_CANDIDATE/,
  );
});
