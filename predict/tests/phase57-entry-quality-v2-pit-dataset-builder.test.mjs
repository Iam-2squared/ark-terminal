import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ENTRY_V2_PIT_DATASET_POLICY,
  buildEntryV2StrictPitPairedDataset,
} from '../daytrade/phase57-entry-quality-v2-pit-dataset-builder.js';

const daily = Array.from({ length: 120 }, (_, i) => {
  const date = new Date(Date.UTC(2026, 3, 1 + i, 6, 0, 0));
  const base = 1000 + i;
  return {
    timestamp: date.toISOString(),
    open: base - 2,
    high: base + 5,
    low: base - 5,
    close: base,
    volume: 100000 + i * 1000,
  };
}).filter(bar => Date.parse(bar.timestamp) < Date.parse('2026-09-04T00:00:00.000Z'));

function bar(startMinute, close) {
  return {
    timestamp: new Date(Date.UTC(2026, 8, 4, 0, startMinute, 0)).toISOString(),
    open: close - 1,
    high: close + 2,
    low: close - 2,
    close,
    volume: 1000 + startMinute * 10,
  };
}

const contextBars = [0, 5, 10, 15, 20, 25, 30].map((minute, i) => bar(minute, 1000 + i));
const futureBars = [35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90].map((minute, i) => bar(minute, 1008 + i));
const entryTimestamp = '2026-09-04T00:35:00.000Z';

const baselineEntry = {
  candidateId: '2026-09-04|2026-09-04T00:35:00.000Z|DYNAMIC5M_V1|336A.T',
  batchEntryKey: '2026-09-04|2026-09-04T00:35:00.000Z|336A.T',
  entryAccepted: true,
  symbol: '336A.T',
  sessionDate: '2026-09-04',
  entryTimestamp,
  direction: 'LONG',
  entryPrice: 1006,
  confidence: 0.72,
  probability: 0.72,
  baseHorizonBars: 6,
  selectedFeatureFamily: 'TEST',
  selectedModelType: 'TEST_MODEL',
  selectedConfigId: 'TEST_CONFIG',
  selectedThreshold: 0.7,
  contextBars,
  frozenBeforeOutcome: true,
  currentOutcomeUsed: false,
  selectionLineage: {
    variant: 'V1',
    selectorCandidateId: 'selector-v1-0035',
    selectionTimestamp: entryTimestamp,
    sourceAsOf: entryTimestamp,
    opportunityScore: 0.9,
    v2Score: null,
  },
};

const baseArgs = {
  baselineEntries: [baselineEntry],
  dailyBarsBySymbol: { '336A.T': daily },
  futureBarsBySymbol: { '336A.T': futureBars },
  marketByEntryTimestamp: {
    [entryTimestamp]: {
      observedAt: entryTimestamp,
      topixReturnPct: -0.5,
      nikkeiReturnPct: -0.7,
      breadthUpRatio: 0.4,
    },
  },
  universeBySymbol: {
    '336A.T': { tickSize: 1, averageTurnover: 500000000 },
  },
  fixedExitId: 'EXIT_V3',
  fixedCapitalAllocationId: 'MAX4',
  costAssumptions: { roundTripCostBps: 20 },
  roundTripCostBps: 20,
};

test('builder freezes OLD/NEW on the exact baseline intraday prefix and emits no NEW signal', () => {
  const dataset = buildEntryV2StrictPitPairedDataset(baseArgs);
  assert.equal(dataset.builderPolicy, ENTRY_V2_PIT_DATASET_POLICY);
  assert.equal(dataset.rowCount, 1);
  assert.equal(dataset.status, 'STRICT_PIT_PAIRED_RESEARCH_DATASET_NO_NEW_SIGNAL');

  const row = dataset.rows[0];
  assert.equal(row.entryTimestamp, entryTimestamp);
  assert.equal(row.entryReferencePrice, baselineEntry.entryPrice);
  assert.equal(row.newResearch.signalEligible, null);
  assert.equal(row.newResearch.direction, null);
  assert.equal(row.lineage.baselineIntradayContextIsCanonical, true);
  assert.equal(row.lineage.baselineContextBarCount, contextBars.length);
  assert.equal(row.lineage.featureFrozenBeforeOfflineLabels, true);
  assert.equal(row.experimentControls.fixedExitId, 'EXIT_V3');
  assert.equal(row.experimentControls.fixedCapitalAllocationId, 'MAX4');
});

test('builder rejects a same-session daily bar before constructing labels', () => {
  const contaminatedDaily = [...daily, {
    timestamp: '2026-09-04T06:00:00.000Z',
    open: 1100,
    high: 1110,
    low: 1090,
    close: 1105,
    volume: 999999,
  }];

  assert.throws(
    () => buildEntryV2StrictPitPairedDataset({
      ...baseArgs,
      dailyBarsBySymbol: { '336A.T': contaminatedDaily },
    }),
    /ENTRY_V2_DAILY_NOT_PRIOR_SESSION/,
  );
});

test('builder rejects an unclosed baseline intraday bar', () => {
  const contaminatedEntry = {
    ...baselineEntry,
    contextBars: [...contextBars, bar(35, 1007)],
  };

  assert.throws(
    () => buildEntryV2StrictPitPairedDataset({
      ...baseArgs,
      baselineEntries: [contaminatedEntry],
    }),
    /ENTRY_V2_INTRADAY_BAR_NOT_CLOSED/,
  );
});

test('builder requires fixed paired controls and cannot silently vary EXIT/allocation', () => {
  assert.throws(
    () => buildEntryV2StrictPitPairedDataset({ ...baseArgs, fixedExitId: null }),
    /ENTRY_V2_BUILDER_FIXED_EXPERIMENT_IDS_REQUIRED/,
  );
  assert.equal(ENTRY_V2_PIT_DATASET_POLICY.selectorChangesAllowed, false);
  assert.equal(ENTRY_V2_PIT_DATASET_POLICY.exitChangesAllowed, false);
  assert.equal(ENTRY_V2_PIT_DATASET_POLICY.capitalAllocationChangesAllowed, false);
  assert.equal(ENTRY_V2_PIT_DATASET_POLICY.automaticPromotionAllowed, false);
});

test('same-symbol variants at one timestamp share one previous state while a later entry sees the prior timestamp', () => {
  const v2Entry = {
    ...baselineEntry,
    candidateId: '2026-09-04|2026-09-04T00:35:00.000Z|DYNAMIC5M_V2|336A.T',
    selectionLineage: {
      ...baselineEntry.selectionLineage,
      variant: 'V2',
      selectorCandidateId: 'selector-v2-0035',
      v2Score: 0.8,
    },
  };
  const laterTimestamp = '2026-09-04T00:45:00.000Z';
  const laterEntry = {
    ...baselineEntry,
    candidateId: '2026-09-04|2026-09-04T00:45:00.000Z|DYNAMIC5M_V1|336A.T',
    batchEntryKey: '2026-09-04|2026-09-04T00:45:00.000Z|336A.T',
    entryTimestamp: laterTimestamp,
    entryPrice: 1008,
    contextBars: [...contextBars, bar(35, 1007), bar(40, 1008)],
    selectionLineage: {
      ...baselineEntry.selectionLineage,
      selectionTimestamp: laterTimestamp,
      sourceAsOf: laterTimestamp,
      selectorCandidateId: 'selector-v1-0045',
    },
  };
  const sourceLineage = { sourceId: 'immutable-marketwide-snapshot' };
  const result = buildEntryV2StrictPitPairedDataset({
    ...baseArgs,
    baselineEntries: [v2Entry, laterEntry, baselineEntry],
    marketByEntryTimestamp: {
      ...baseArgs.marketByEntryTimestamp,
      [laterTimestamp]: {
        observedAt: laterTimestamp,
        topixReturnPct: -0.3,
        nikkeiReturnPct: -0.4,
        breadthUpRatio: 0.45,
      },
    },
    sourceLineageByEntry: {
      [baselineEntry.candidateId]: sourceLineage,
    },
  });

  const firstV1 = result.rows.find(row => row.baseline.candidateId === baselineEntry.candidateId);
  const firstV2 = result.rows.find(row => row.baseline.candidateId === v2Entry.candidateId);
  const later = result.rows.find(row => row.baseline.candidateId === laterEntry.candidateId);
  assert.equal(firstV1.newResearch.featureSha256, firstV2.newResearch.featureSha256);
  assert.equal(firstV1.newResearch.features.novelty.hasPreviousState, false);
  assert.equal(firstV2.newResearch.features.novelty.hasPreviousState, false);
  assert.equal(later.newResearch.features.novelty.hasPreviousState, true);
  assert.deepEqual(firstV1.lineage.sourceLineage, sourceLineage);
  assert.equal(firstV2.lineage.sourceLineage, null);
});
