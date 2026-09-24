import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_ENTRY_QUALITY_V2_SAFETY,
  PHASE57_ENTRY_QUALITY_V2_POLICY,
  buildEntryV2DailyContext,
  buildEntryV2IntradayContext,
  buildEntryV2UniverseDiagnostics,
  buildEntryV2Novelty,
  buildEntryQualityV2ResearchVector,
} from '../daytrade/phase57-entry-quality-v2-research.js';

const day = n => {
  const d = new Date(Date.UTC(2026, 0, 1 + n, 6, 0, 0));
  const base = 1000 + n * 2;
  return {
    timestamp: d.toISOString(),
    open: base - 2,
    high: base + 8,
    low: base - 7,
    close: base,
    volume: 100000 + n * 1000,
  };
};

const intraday = (n, close = 1000 + n) => ({
  timestamp: new Date(Date.UTC(2026, 8, 4, 0, n * 5, 0)).toISOString(),
  open: close - 1,
  high: close + 2,
  low: close - 2,
  close,
  volume: 1000 + n * 100,
});

test('Entry v2 research safety is fail-closed and cannot auto-promote', () => {
  for (const key of [
    'executionAllowed',
    'brokerWriteAllowed',
    'excelOrderWriteAllowed',
    'rssOrderFunctionAllowed',
    'liveTradingAllowed',
    'paperTradingAllowed',
    'automaticPromotionAllowed',
    'productionUpdateAllowed',
    'transmitted',
  ]) {
    assert.equal(PHASE57_ENTRY_QUALITY_V2_SAFETY[key], false, key);
  }
  assert.equal(PHASE57_ENTRY_QUALITY_V2_POLICY.baseline, 'PHASE57_P21_FROZEN_ENTRY');
  assert.equal(PHASE57_ENTRY_QUALITY_V2_POLICY.integrationMode, 'ISOLATED_RESEARCH_ONLY');
});

test('daily context uses only bars at or before asOf and retains multi-window context', () => {
  const bars = Array.from({ length: 120 }, (_, i) => day(i));
  const asOf = bars.at(-1).timestamp;
  const context = buildEntryV2DailyContext({ dailyBars: bars, asOf });

  assert.equal(context.availableBars, 120);
  assert.equal(context.latestBarTimestamp, asOf);
  assert.ok(context.ma20DistancePct > 0);
  assert.ok(context.ma50DistancePct > 0);
  assert.ok(context.ma100DistancePct > 0);
  assert.ok(context.range20Position >= 0 && context.range20Position <= 1);
});

test('daily context rejects future bars instead of silently leaking them', () => {
  const bars = Array.from({ length: 30 }, (_, i) => day(i));
  const asOf = bars.at(-2).timestamp;
  assert.throws(
    () => buildEntryV2DailyContext({ dailyBars: bars, asOf }),
    /ENTRY_V2_FUTURE_BAR_REJECTED/,
  );
});

test('intraday context separates current state from state change', () => {
  const firstBars = Array.from({ length: 7 }, (_, i) => intraday(i));
  const secondBars = [...firstBars, intraday(7, 1015)];
  const first = buildEntryV2IntradayContext({
    intradayBars: firstBars,
    asOf: firstBars.at(-1).timestamp,
  });
  const second = buildEntryV2IntradayContext({
    intradayBars: secondBars,
    asOf: secondBars.at(-1).timestamp,
  });
  const novelty = buildEntryV2Novelty({ previous: first, current: second });

  assert.equal(novelty.hasPreviousState, true);
  assert.notEqual(novelty.momentumChangePct, 0);
  assert.notEqual(novelty.vwapDistanceChangePct, 0);
});

test('universe diagnostics measure microstructure without post-hoc low-price cutoff', () => {
  const lowPrice = buildEntryV2UniverseDiagnostics({
    price: 10,
    tickSize: 1,
    averageTurnover: 1000000,
    spreadProxy: 1,
  });

  assert.equal(lowPrice.tickToPricePct, 10);
  assert.equal(lowPrice.hardEligibilityApplied, false);
});

test('research vector cannot emit a trading signal', () => {
  const dailyBars = Array.from({ length: 120 }, (_, i) => day(i));
  const intradayBars = Array.from({ length: 8 }, (_, i) => intraday(i));
  const vector = buildEntryQualityV2ResearchVector({
    symbol: '336A.T',
    asOf: intradayBars.at(-1).timestamp,
    dailyBars: dailyBars.map((bar, i) => ({
      ...bar,
      timestamp: new Date(Date.UTC(2026, 4, 1 + i, 6, 0, 0)).toISOString(),
    })).filter(bar => new Date(bar.timestamp) <= new Date(intradayBars.at(-1).timestamp)),
    intradayBars,
    market: { topixReturnPct: -1.2, breadthUpRatio: 0.3 },
    universe: { tickSize: 1, averageTurnover: 500000000 },
  });

  assert.equal(vector.status, 'FEATURE_VECTOR_ONLY_NO_SIGNAL');
  assert.equal(vector.signalEligible, null);
  assert.equal(vector.direction, null);
  assert.equal(vector.longQuality, null);
  assert.equal(vector.shortQuality, null);
  assert.equal(vector.safety.executionAllowed, false);
});
