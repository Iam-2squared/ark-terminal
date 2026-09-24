import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildEntryQualityV2PairedRow,
  buildEntryQualityV2PairedDataset,
} from '../daytrade/phase57-entry-quality-v2-paired-dataset.js';

const baselineEntry = Object.freeze({
  candidateId: '2026-09-04|2026-09-04T01:00:00.000Z|DYNAMIC5M_V1|336A.T',
  batchEntryKey: '2026-09-04|2026-09-04T01:00:00.000Z|336A.T',
  entryAccepted: true,
  symbol: '336A.T',
  sessionDate: '2026-09-04',
  entryTimestamp: '2026-09-04T01:00:00.000Z',
  direction: 'LONG',
  entryPrice: 100,
  confidence: 0.72,
  probability: 0.72,
  baseHorizonBars: 3,
  selectedFeatureFamily: 'TEST_FAMILY',
  selectedModelType: 'LOGISTIC',
  selectedConfigId: 'TEST_CONFIG',
  selectedThreshold: 0.7,
  frozenBeforeOutcome: true,
  currentOutcomeUsed: false,
  selectionLineage: Object.freeze({
    variant: 'V1',
    selectionTimestamp: '2026-09-04T01:00:00.000Z',
    sourceAsOf: '2026-09-04T01:00:00.000Z',
    selectorCandidateId: 'selector-v1-20260904-0100',
    opportunityScore: 1.25,
    v2Score: null,
  }),
});

const researchVector = Object.freeze({
  policy: Object.freeze({ baseline: 'PHASE57_P21_FROZEN_ENTRY' }),
  symbol: '336A.T',
  asOf: '2026-09-04T01:00:00.000Z',
  status: 'FEATURE_VECTOR_ONLY_NO_SIGNAL',
  signalEligible: null,
  direction: null,
  longQuality: null,
  shortQuality: null,
  market: Object.freeze({ topixReturnPct: 0.3 }),
  daily: Object.freeze({ return20dPct: 5.2 }),
  intraday: Object.freeze({ vwapDistancePct: 0.4 }),
  universe: Object.freeze({ tickToPricePct: 1 }),
  novelty: Object.freeze({ momentumChangePct: 0.1 }),
});

const pathLabels = Object.freeze({
  policy: Object.freeze({ mode: 'OFFLINE_FUTURE_LABELS_ONLY' }),
  entryTimestamp: '2026-09-04T01:00:00.000Z',
  entryPrice: 100,
  labels: Object.freeze([
    Object.freeze({ horizonBars: 1, complete: true, long: Object.freeze({ grossReturnPct: 1 }), short: Object.freeze({ grossReturnPct: -1 }) }),
  ]),
});

const controls = Object.freeze({
  costAssumptions: Object.freeze({ roundTripCostBps: 20 }),
  fixedExitId: 'EXIT_V3',
  fixedCapitalAllocationId: 'MAX4',
});

test('paired row freezes OLD baseline and NEW feature-only research at same timestamp', () => {
  const row = buildEntryQualityV2PairedRow({
    baselineEntry,
    researchVector,
    pathLabels,
    ...controls,
  });

  assert.equal(row.status, 'PAIRED_RESEARCH_ROW_NO_NEW_SIGNAL');
  assert.equal(row.symbol, '336A.T');
  assert.equal(row.entryReferencePrice, 100);
  assert.equal(row.baseline.scorer, 'PHASE57_P21_FROZEN_ENTRY');
  assert.equal(row.baseline.direction, 'LONG');
  assert.equal(row.newResearch.signalEligible, null);
  assert.equal(row.newResearch.direction, null);
  assert.equal(row.experimentControls.selectorFrozen, true);
  assert.equal(row.experimentControls.exitFrozen, true);
  assert.equal(row.experimentControls.capitalAllocationFrozen, true);
  assert.equal(row.experimentControls.costAssumptionsFrozen, true);
  assert.match(row.newResearch.featureSha256, /^[a-f0-9]{64}$/);
  assert.match(row.offlineLabels.labelSha256, /^[a-f0-9]{64}$/);
});

test('paired row rejects mismatched symbol or timestamp rather than silently aligning', () => {
  assert.throws(
    () => buildEntryQualityV2PairedRow({
      baselineEntry,
      researchVector: { ...researchVector, symbol: '338A.T' },
      pathLabels,
      ...controls,
    }),
    /ENTRY_V2_PAIRED_SYMBOL_MISMATCH/,
  );

  assert.throws(
    () => buildEntryQualityV2PairedRow({
      baselineEntry,
      researchVector: { ...researchVector, asOf: '2026-09-04T01:05:00.000Z' },
      pathLabels,
      ...controls,
    }),
    /ENTRY_V2_PAIRED_TIMESTAMP_MISMATCH/,
  );
});

test('paired row rejects future-label entry price drift and NEW signal emission', () => {
  assert.throws(
    () => buildEntryQualityV2PairedRow({
      baselineEntry,
      researchVector,
      pathLabels: { ...pathLabels, entryPrice: 101 },
      ...controls,
    }),
    /ENTRY_V2_PAIRED_ENTRY_PRICE_MISMATCH/,
  );

  assert.throws(
    () => buildEntryQualityV2PairedRow({
      baselineEntry,
      researchVector: { ...researchVector, signalEligible: true, direction: 'LONG' },
      pathLabels,
      ...controls,
    }),
    /ENTRY_V2_PAIRED_RESEARCH_VECTOR_EMITTED_SIGNAL/,
  );
});

test('paired dataset rejects duplicate pair keys', () => {
  const row = buildEntryQualityV2PairedRow({
    baselineEntry,
    researchVector,
    pathLabels,
    ...controls,
  });
  const dataset = buildEntryQualityV2PairedDataset([row]);
  assert.equal(dataset.rowCount, 1);
  assert.equal(dataset.status, 'PAIRED_RESEARCH_DATASET_NO_NEW_SIGNAL');
  assert.match(dataset.datasetSha256, /^[a-f0-9]{64}$/);

  assert.throws(
    () => buildEntryQualityV2PairedDataset([row, row]),
    /ENTRY_V2_PAIRED_DUPLICATE_ROW/,
  );
});
