import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ENTRY_V2_POINT_IN_TIME_POLICY,
  prepareEntryV2PriorDailyBars,
  prepareEntryV2ClosedIntradayPrefix,
  buildStrictPointInTimeEntryV2ResearchVector,
} from '../daytrade/phase57-entry-quality-v2-point-in-time.js';

const daily = (timestamp, close = 1000) => ({
  timestamp,
  open: close - 2,
  high: close + 5,
  low: close - 5,
  close,
  volume: 100000,
});

const intraday = (timestamp, close = 1000) => ({
  timestamp,
  open: close - 1,
  high: close + 2,
  low: close - 2,
  close,
  volume: 1000,
});

test('PIT policy requires prior-session daily bars and completed intraday prefix', () => {
  assert.equal(ENTRY_V2_POINT_IN_TIME_POLICY.requirePriorSessionDailyBars, true);
  assert.equal(ENTRY_V2_POINT_IN_TIME_POLICY.requireCompletedIntradayBars, true);
  assert.equal(ENTRY_V2_POINT_IN_TIME_POLICY.automaticPromotionAllowed, false);
});

test('same-session daily OHLCV is rejected even when its timestamp is before decision asOf', () => {
  const asOf = '2026-09-04T02:00:00.000Z'; // 11:00 JST
  const bars = [
    daily('2026-09-03T06:00:00.000Z', 1000),
    // Midnight-like/current-session timestamps can otherwise look causally earlier than asOf.
    daily('2026-09-04T00:00:00.000Z', 1010),
  ];
  assert.throws(
    () => prepareEntryV2PriorDailyBars({ dailyBars: bars, asOf }),
    /ENTRY_V2_DAILY_NOT_PRIOR_SESSION/,
  );
});

test('intraday bar is accepted only after its five-minute close', () => {
  const bars = [
    intraday('2026-09-04T01:00:00.000Z', 1000), // 10:00 JST, closes 10:05
    intraday('2026-09-04T01:05:00.000Z', 1001), // 10:05 JST, closes 10:10
  ];
  assert.throws(
    () => prepareEntryV2ClosedIntradayPrefix({
      intradayBars: bars,
      asOf: '2026-09-04T01:09:59.999Z',
    }),
    /ENTRY_V2_INTRADAY_BAR_NOT_CLOSED/,
  );

  const closed = prepareEntryV2ClosedIntradayPrefix({
    intradayBars: bars,
    asOf: '2026-09-04T01:10:00.000Z',
  });
  assert.equal(closed.length, 2);
});

test('intraday prefix rejects cross-session contamination', () => {
  assert.throws(
    () => prepareEntryV2ClosedIntradayPrefix({
      intradayBars: [
        intraday('2026-09-03T05:00:00.000Z', 999),
        intraday('2026-09-04T01:00:00.000Z', 1000),
      ],
      asOf: '2026-09-04T01:10:00.000Z',
    }),
    /ENTRY_V2_INTRADAY_CROSS_SESSION_BAR/,
  );
});

test('duplicate timestamps fail closed', () => {
  const row = intraday('2026-09-04T01:00:00.000Z', 1000);
  assert.throws(
    () => prepareEntryV2ClosedIntradayPrefix({
      intradayBars: [row, { ...row }],
      asOf: '2026-09-04T01:10:00.000Z',
    }),
    /ENTRY_V2_INTRADAY_DUPLICATE_TIMESTAMP/,
  );
});

test('formal market context requires point-in-time lineage', () => {
  const dailyBars = Array.from({ length: 120 }, (_, i) => daily(
    new Date(Date.UTC(2026, 0, 1 + i, 6, 0, 0)).toISOString(),
    900 + i,
  )).filter(bar => new Date(bar.timestamp) < new Date('2026-09-04T00:00:00.000Z'));
  const intradayBars = [
    intraday('2026-09-04T00:00:00.000Z', 1000),
    intraday('2026-09-04T00:05:00.000Z', 1001),
    intraday('2026-09-04T00:10:00.000Z', 1002),
    intraday('2026-09-04T00:15:00.000Z', 1003),
    intraday('2026-09-04T00:20:00.000Z', 1004),
    intraday('2026-09-04T00:25:00.000Z', 1005),
  ];

  assert.throws(
    () => buildStrictPointInTimeEntryV2ResearchVector({
      symbol: '336A.T',
      asOf: '2026-09-04T00:30:00.000Z',
      dailyBars,
      intradayBars,
      market: { topixReturnPct: 1.2 },
    }),
    /ENTRY_V2_MARKET_LINEAGE_REQUIRED/,
  );
});

test('strict vector remains feature-only and attests no future outcome use', () => {
  const dailyBars = Array.from({ length: 120 }, (_, i) => daily(
    new Date(Date.UTC(2026, 0, 1 + i, 6, 0, 0)).toISOString(),
    900 + i,
  )).filter(bar => new Date(bar.timestamp) < new Date('2026-09-04T00:00:00.000Z'));
  const intradayBars = Array.from({ length: 6 }, (_, i) => intraday(
    new Date(Date.UTC(2026, 8, 4, 0, i * 5, 0)).toISOString(),
    1000 + i,
  ));

  const vector = buildStrictPointInTimeEntryV2ResearchVector({
    symbol: '336A.T',
    asOf: '2026-09-04T00:30:00.000Z',
    dailyBars,
    intradayBars,
    market: {
      observedAt: '2026-09-04T00:29:00.000Z',
      topixReturnPct: -0.4,
      breadthUpRatio: 0.42,
    },
    universe: { tickSize: 1, averageTurnover: 500000000 },
  });

  assert.equal(vector.status, 'FEATURE_VECTOR_ONLY_NO_SIGNAL');
  assert.equal(vector.signalEligible, null);
  assert.equal(vector.direction, null);
  assert.equal(vector.pointInTime.strict, true);
  assert.equal(vector.pointInTime.dailyBarsArePriorSessionOnly, true);
  assert.equal(vector.pointInTime.intradayBarsAreCompletedPrefixOnly, true);
  assert.equal(vector.pointInTime.futureOutcomeUsed, false);
  assert.equal(vector.safety.executionAllowed, false);
});
