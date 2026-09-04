import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ENTRY_V2_EVIDENCE_DATASET_POLICY,
  buildEntryV2DatasetFromFrozenEvidence,
} from '../daytrade/phase57-entry-quality-v2-evidence-dataset.js';

const entryTimestamp = '2026-09-04T01:30:00.000Z';

function baselineEntry(overrides = {}) {
  return {
    candidateId: `2026-09-04|${entryTimestamp}|DYNAMIC5M_V1|LOW.T`,
    batchEntryKey: `2026-09-04|${entryTimestamp}|LOW.T`,
    entryAccepted: true,
    symbol: 'LOW.T',
    sessionDate: '2026-09-04',
    entryTimestamp,
    direction: 'SHORT',
    entryPrice: 10,
    confidence: 0.71,
    probability: 0.29,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    contextBars: [
      { timestamp: '2026-09-04T01:15:00.000Z', open: 10, high: 11, low: 10, close: 10, volume: 12000 },
      { timestamp: '2026-09-04T01:20:00.000Z', open: 10, high: 10, low: 9, close: 10, volume: 14000 },
      { timestamp: '2026-09-04T01:25:00.000Z', open: 10, high: 10, low: 9, close: 10, volume: 15000 },
    ],
    selectionLineage: {
      variant: 'V1',
      variantId: 'DYNAMIC5M_V1',
      selectionTimestamp: entryTimestamp,
      sourceAsOf: entryTimestamp,
      selectorCandidateId: 'selector-low-v1-0130',
      opportunityScore: 0.67,
      v2Score: null,
    },
    ...overrides,
  };
}

function dailyRecord(sessionDate, close, overrides = {}) {
  return {
    symbol: 'LOW.T',
    sessionDate,
    kind: 'OHLCV',
    source: 'YAHOO_CHART',
    currency: 'JPY',
    open: close,
    high: close + 1,
    low: Math.max(1, close - 1),
    close,
    volume: 100000,
    adjustedClose: close,
    ...overrides,
  };
}

const priorDaily = [
  '2026-08-10', '2026-08-11', '2026-08-12', '2026-08-13', '2026-08-14',
  '2026-08-17', '2026-08-18', '2026-08-19', '2026-08-20', '2026-08-21',
  '2026-08-24', '2026-08-25', '2026-08-26', '2026-08-27', '2026-08-28',
  '2026-08-31', '2026-09-01', '2026-09-02', '2026-09-03',
].map((sessionDate, index) => dailyRecord(sessionDate, 10 + index * 0.1));

const futureBars = [
  { timestamp: '2026-09-04T01:35:00.000Z', high: 10.2, low: 9.7, close: 9.8 },
  { timestamp: '2026-09-04T01:40:00.000Z', high: 10.1, low: 9.5, close: 9.6 },
  { timestamp: '2026-09-04T01:45:00.000Z', high: 9.9, low: 9.3, close: 9.4 },
];

test('frozen evidence flows through strict prior-daily PIT pairing without emitting a NEW signal', () => {
  const sameSessionDaily = dailyRecord('2026-09-04', 999);
  const futureDaily = dailyRecord('2026-09-07', 999);
  const result = buildEntryV2DatasetFromFrozenEvidence({
    evidence: { frozenEntries: [baselineEntry()] },
    evidenceSourceId: 'synthetic-frozen-evidence',
    dailyRecordsBySymbol: {
      'LOW.T': [...priorDaily, sameSessionDaily, futureDaily],
    },
    futureBarsBySymbol: { 'LOW.T': futureBars },
    marketByEntryTimestamp: {
      [entryTimestamp]: {
        observedAt: entryTimestamp,
        topixReturnPct: -0.4,
        breadthUpRatio: 0.42,
      },
    },
    universeBySymbol: {
      'LOW.T': { tickSize: 1, averageTurnover: 10000000, spreadProxy: 1 },
    },
    fixedExitId: 'EXIT_V3_FROZEN',
    fixedCapitalAllocationId: 'CAPITAL_ALLOCATION_FROZEN',
    costAssumptions: { model: 'FROZEN_TEST_COSTS' },
    roundTripCostBps: 20,
    horizonsBars: [1, 3],
  });

  assert.equal(ENTRY_V2_EVIDENCE_DATASET_POLICY.postHocUniverseExclusionAllowed, false);
  assert.equal(ENTRY_V2_EVIDENCE_DATASET_POLICY.emitNewSignal, false);
  assert.equal(result.status, 'ENTRY_V2_FROZEN_EVIDENCE_STRICT_PIT_DATASET_READY_NO_NEW_SIGNAL');
  assert.equal(result.evidence.entryCount, 1);
  assert.equal(result.dataset.rowCount, 1);

  const row = result.dataset.rows[0];
  assert.equal(row.symbol, 'LOW.T');
  assert.equal(row.entryReferencePrice, 10);
  assert.equal(row.baseline.scorer, 'PHASE57_P21_FROZEN_ENTRY');
  assert.equal(row.newResearch.status, 'FEATURE_VECTOR_ONLY_NO_SIGNAL');
  assert.equal(row.newResearch.signalEligible, null);
  assert.equal(row.newResearch.direction, null);
  assert.equal(row.safety.executionAllowed, false);
  assert.equal(row.safety.brokerWriteAllowed, false);
  assert.equal(row.safety.automaticPromotionAllowed, false);
  assert.equal(row.lineage.baselineIntradayContextIsCanonical, true);
  assert.equal(row.lineage.dailyResolutionMode, 'PERSISTED_DAILY_ARCHIVE_RESOLVED_PER_ENTRY');
  assert.equal(row.lineage.dailyHistoryLineage.archiveSlice.excludedSameOrFutureRecordCount, 2);
  assert.equal(row.lineage.dailyHistoryLineage.lastRetainedSessionDate, '2026-09-03');
  assert.equal(row.newResearch.features.daily.priorClose, priorDaily.at(-2).close);
  assert.equal(row.newResearch.features.universe.price, 10);
  assert.equal(row.newResearch.features.universe.tickToPricePct, 10);
  assert.equal(row.newResearch.features.universe.hardEligibilityApplied, false);
  assert.equal(row.newResearch.pointInTime.marketLineageChecked, true);
  assert.equal(row.newResearch.features.market.observedAt, entryTimestamp);

  const h1 = row.offlineLabels.labels.find(label => label.horizonBars === 1);
  const h3 = row.offlineLabels.labels.find(label => label.horizonBars === 3);
  assert.equal(h1.complete, true);
  assert.equal(h3.complete, true);
  assert.ok(h3.short.grossReturnPct > 0);
  assert.ok(h3.short.mfePct > 0);
});

test('evidence dataset fails closed when no prior-session daily history exists', () => {
  assert.throws(
    () => buildEntryV2DatasetFromFrozenEvidence({
      evidence: { frozenEntries: [baselineEntry()] },
      dailyRecordsBySymbol: {
        'LOW.T': [dailyRecord('2026-09-04', 10)],
      },
      futureBarsBySymbol: { 'LOW.T': futureBars },
      fixedExitId: 'EXIT_V3_FROZEN',
      fixedCapitalAllocationId: 'CAPITAL_ALLOCATION_FROZEN',
      costAssumptions: { model: 'FROZEN_TEST_COSTS' },
    }),
    /ENTRY_V2_DAILY_FEED_NO_PRIOR_RECORDS/,
  );
});
