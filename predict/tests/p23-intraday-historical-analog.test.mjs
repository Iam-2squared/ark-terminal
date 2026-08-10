import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P23_SAFETY,
  selectCausalAnalogPool,
  fitCausalRobustScaler,
  summarizeIntradayAnalogs,
  findIntradayHistoricalAnalogs,
} from '../daytrade/phase57-intraday-historical-analog.js';

const featureKeys = ['ma5Distance', 'rsi14', 'spreadBps'];
const query = {
  symbol: '8035.T',
  sessionDate: '2026-08-10',
  asOf: '2026-08-10T00:30:00.000Z',
  featureCutoff: '2026-08-10T00:30:00.000Z',
  horizonBars: 3,
  features: { ma5Distance: 0.01, rsi14: 55, spreadBps: 2 },
  context: { timeBucket: 'OPEN', regime: 'TREND' },
};

function candidate({
  id,
  symbol = '8035.T',
  sessionDate = '2026-08-09',
  featureCutoff = '2026-08-09T00:10:00.000Z',
  outcomeAt = '2026-08-09T00:25:00.000Z',
  outcomeSessionDate = sessionDate,
  horizonBars = 3,
  features = { ma5Distance: 0.01, rsi14: 55, spreadBps: 2 },
  context = { timeBucket: 'OPEN', regime: 'TREND' },
  actualReturnPct = 1,
  absMovePct = Math.abs(actualReturnPct),
  mfePct = 1.4,
  maePct = -0.3,
  pointInTimeValid = true,
  intradayOnly = true,
} = {}) {
  return {
    id: id ?? `${symbol}-${sessionDate}-${featureCutoff}`,
    symbol,
    sessionDate,
    featureCutoff,
    outcomeAt,
    outcomeSessionDate,
    horizonBars,
    features,
    context,
    actualReturnPct,
    absMovePct,
    mfePct,
    maePct,
    pointInTimeValid,
    intradayOnly,
  };
}

test('P23 safety remains strictly research-only and fail-closed', () => {
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
    'overnightHoldingAllowed',
  ]) assert.equal(PHASE57_P23_SAFETY[key], false);
  assert.equal(PHASE57_P23_SAFETY.humanApprovalRequired, true);
});

test('P23 rejects outcome-derived feature names from similarity to prevent label leakage', () => {
  assert.throws(() => selectCausalAnalogPool({
    query,
    candidates: [],
    featureKeys: ['ma5Distance', 'actualReturnPct'],
  }), /outcome-derived feature is forbidden/);
  assert.throws(() => findIntradayHistoricalAnalogs({
    query,
    candidates: [],
    featureKeys: ['futureHigh'],
  }), /outcome-derived feature is forbidden/);
});

test('causal pool excludes future outcomes, current session by default, horizon mismatches and non point-in-time rows', () => {
  const rows = [
    candidate({ id: 'good' }),
    candidate({
      id: 'future',
      sessionDate: '2026-08-10',
      featureCutoff: '2026-08-10T00:20:00.000Z',
      outcomeAt: '2026-08-10T00:31:00.000Z',
    }),
    candidate({
      id: 'current-session-realized',
      sessionDate: '2026-08-10',
      featureCutoff: '2026-08-10T00:05:00.000Z',
      outcomeAt: '2026-08-10T00:20:00.000Z',
    }),
    candidate({ id: 'wrong-horizon', horizonBars: 6 }),
    candidate({ id: 'not-pit', pointInTimeValid: false }),
  ];
  const pool = selectCausalAnalogPool({ query, candidates: rows, featureKeys });
  assert.deepEqual(pool.causalCandidates.map(row => row.id), ['good']);
  assert.equal(pool.rejected.futureOutcome, 1);
  assert.equal(pool.rejected.currentSession, 1);
  assert.equal(pool.rejected.horizonMismatch, 1);
  assert.equal(pool.rejected.nonPointInTime, 1);
  assert.equal(pool.candidateOutcomesFullyRealizedBeforeQuery, true);
  assert.equal(pool.currentSessionExcluded, true);
});

test('same-session analogs are allowed only when explicitly enabled and their outcomes are already realized', () => {
  const rows = [
    candidate({
      id: 'realized-same-session',
      sessionDate: '2026-08-10',
      featureCutoff: '2026-08-10T00:05:00.000Z',
      outcomeAt: '2026-08-10T00:20:00.000Z',
    }),
    candidate({
      id: 'future-same-session',
      sessionDate: '2026-08-10',
      featureCutoff: '2026-08-10T00:20:00.000Z',
      outcomeAt: '2026-08-10T00:35:00.000Z',
    }),
  ];
  const pool = selectCausalAnalogPool({ query, candidates: rows, featureKeys, excludeCurrentSession: false });
  assert.deepEqual(pool.causalCandidates.map(row => row.id), ['realized-same-session']);
  assert.equal(pool.rejected.futureOutcome, 1);
  assert.equal(pool.currentSessionExcluded, false);
});

test('P23 excludes overnight outcomes even if other fields look usable', () => {
  const overnight = candidate({
    id: 'overnight',
    sessionDate: '2026-08-08',
    outcomeSessionDate: '2026-08-09',
    featureCutoff: '2026-08-08T05:55:00.000Z',
    outcomeAt: '2026-08-09T00:10:00.000Z',
  });
  const pool = selectCausalAnalogPool({ query, candidates: [overnight], featureKeys });
  assert.equal(pool.causalCandidateCount, 0);
  assert.equal(pool.rejected.invalid, 1);
  assert.equal(pool.intradayOnly, true);
});

test('robust scaler is fit only from the already-causal candidate pool', () => {
  const causal = [
    candidate({ id: 'a', features: { ma5Distance: 0, rsi14: 40, spreadBps: 1 } }),
    candidate({ id: 'b', sessionDate: '2026-08-08', featureCutoff: '2026-08-08T00:10:00Z', outcomeAt: '2026-08-08T00:25:00Z', features: { ma5Distance: 0.02, rsi14: 60, spreadBps: 3 } }),
  ];
  const pool = selectCausalAnalogPool({ query, candidates: causal, featureKeys });
  const scaler = fitCausalRobustScaler(pool.causalCandidates, pool.featureKeys);
  assert.equal(scaler.rsi14.sampleCount, 2);
  assert.equal(scaler.rsi14.median, 50);
  assert.ok(scaler.rsi14.scale > 0);
});

test('analog ranking depends on causal features, not on future outcome labels', () => {
  const near = candidate({ id: 'near', features: { ma5Distance: 0.011, rsi14: 55.5, spreadBps: 2.1 }, actualReturnPct: -5 });
  const far = candidate({ id: 'far', sessionDate: '2026-08-08', featureCutoff: '2026-08-08T00:10:00Z', outcomeAt: '2026-08-08T00:25:00Z', features: { ma5Distance: 0.04, rsi14: 75, spreadBps: 8 }, actualReturnPct: 5 });
  const first = findIntradayHistoricalAnalogs({ query, candidates: [near, far], featureKeys, topK: 2, minimumAnalogs: 1 });
  const swapped = findIntradayHistoricalAnalogs({
    query,
    candidates: [
      { ...near, actualReturnPct: 9, absMovePct: 9 },
      { ...far, actualReturnPct: -9, absMovePct: 9 },
    ],
    featureKeys,
    topK: 2,
    minimumAnalogs: 1,
  });
  assert.deepEqual(first.analogs.map(row => row.id), swapped.analogs.map(row => row.id));
  assert.equal(first.analogs[0].id, 'near');
  assert.equal(first.distanceUsesOutcomeLabels, false);
  assert.equal(first.outcomeDerivedFeaturesAllowed, false);
});

test('time/regime context penalties can favor a context-consistent analog without using labels', () => {
  const wrongContext = candidate({
    id: 'wrong-context',
    features: { ma5Distance: 0.01, rsi14: 55, spreadBps: 2 },
    context: { timeBucket: 'CLOSE', regime: 'RANGE' },
  });
  const rightContext = candidate({
    id: 'right-context',
    sessionDate: '2026-08-08',
    featureCutoff: '2026-08-08T00:10:00Z',
    outcomeAt: '2026-08-08T00:25:00Z',
    features: { ma5Distance: 0.011, rsi14: 55.2, spreadBps: 2.1 },
    context: { timeBucket: 'OPEN', regime: 'TREND' },
  });
  const result = findIntradayHistoricalAnalogs({
    query,
    candidates: [wrongContext, rightContext],
    featureKeys,
    topK: 2,
    minimumAnalogs: 1,
    contextPenalties: { timeBucket: 2, regime: 2 },
  });
  assert.equal(result.analogs[0].id, 'right-context');
});

test('analog outcome summary is magnitude-aware and cost-aware without becoming a recommendation', () => {
  const summary = summarizeIntradayAnalogs([
    { similarityWeight: 1, actualReturnPct: 1.5, absMovePct: 1.5, mfePct: 2, maePct: -0.4 },
    { similarityWeight: 1, actualReturnPct: -0.5, absMovePct: 0.5, mfePct: 0.7, maePct: -1 },
  ], { roundTripCostPct: 0.1 });
  assert.equal(summary.sampleCount, 2);
  assert.equal(summary.weightedMeanReturnPct, 0.5);
  assert.equal(summary.expectedNetLongReturnPctAfterCost, 0.4);
  assert.equal(summary.expectedNetShortReturnPctAfterCost, -0.6);
  assert.equal(summary.moveProbabilityByThresholdPct['0.5'], 1);
  assert.equal(summary.moveProbabilityByThresholdPct['1'], 0.5);
  assert.equal(summary.moveProbabilityByThresholdPct['2'], 0);
});

test('final P23 result exposes auditability and never enables trading or an edge claim', () => {
  const rows = Array.from({ length: 12 }, (_, index) => candidate({
    id: `row-${index}`,
    sessionDate: `2026-07-${String(20 + (index % 9)).padStart(2, '0')}`,
    featureCutoff: `2026-07-${String(20 + (index % 9)).padStart(2, '0')}T00:10:00.000Z`,
    outcomeAt: `2026-07-${String(20 + (index % 9)).padStart(2, '0')}T00:25:00.000Z`,
    features: { ma5Distance: 0.01 + index * 0.0001, rsi14: 54 + index * 0.1, spreadBps: 2 + index * 0.02 },
    actualReturnPct: index % 2 ? 0.8 : -0.3,
  }));
  const result = findIntradayHistoricalAnalogs({ query, candidates: rows, featureKeys, topK: 10, minimumAnalogs: 10 });
  assert.equal(result.status, 'INTRADAY_ANALOGS_READY');
  assert.equal(result.analogs.length, 10);
  assert.equal(result.featureScalerFitOnCausalCandidatePoolOnly, true);
  assert.equal(result.candidateAudit.candidateOutcomesFullyRealizedBeforeQuery, true);
  assert.equal(result.pointInTime, true);
  assert.equal(result.intradayOnly, true);
  assert.equal(result.edgeClaimAllowed, false);
  assert.equal(result.recommendationAllowed, false);
  assert.equal(result.paperTradingAllowed, false);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.transmitted, false);
});
