import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P22_SAFETY,
  MARKETSPEED_II_P22_READ_ONLY_CONTRACT,
  buildMicrostructureIntelligence,
} from '../daytrade/phase57-microstructure-intelligence.js';

const q = (timestamp, bestBid, bestAsk, bidSize = 100, askSize = 100) => ({ timestamp, bestBid, bestAsk, bidSize, askSize });

test('P22 computes spread, microprice, top-book and depth imbalance from READ ONLY quote data', () => {
  const result = buildMicrostructureIntelligence({
    snapshot: {
      timestamp: '2026-08-10T00:00:10.000Z',
      bestBid: 100,
      bestAsk: 101,
      bidSize: 300,
      askSize: 100,
      bidPrice1: 99.5,
      bidSize1: 500,
      askPrice1: 101.5,
      askSize1: 100,
      bidPrice2: 99,
      bidSize2: 300,
      askPrice2: 102,
      askSize2: 100,
    },
  });
  assert.equal(result.status, 'MICROSTRUCTURE_INTELLIGENCE_READY');
  assert.equal(result.features.spread, 1);
  assert.ok(result.features.spreadBps > 99 && result.features.spreadBps < 100);
  assert.equal(result.features.topBookImbalance, 0.5);
  assert.equal(result.features.depthImbalance, 0.6);
  assert.ok(result.features.weightedDepthImbalance > 0.6);
  assert.equal(result.features.microprice, 100.75);
  assert.ok(result.features.micropriceEdgeBps > 0);
});

test('P22 accepts official Japanese RssMarket field labels including ten-level depth', () => {
  const result = buildMicrostructureIntelligence({
    snapshot: {
      capturedAt: '2026-08-10T00:00:10.000Z',
      '最良売気配値': 100.5,
      '最良買気配値': 100,
      '最良売気配数量': 120,
      '最良買気配数量': 240,
      '最良売気配値1': 101,
      '最良売気配数量1': 80,
      '最良買気配値1': 99.5,
      '最良買気配数量1': 160,
      'OVER気配数量': 1000,
      'UNDER気配数量': 1500,
    },
  });
  assert.equal(result.features.bestAsk, 100.5);
  assert.equal(result.features.bestBid, 100);
  assert.equal(result.features.askDepth, 80);
  assert.equal(result.features.bidDepth, 160);
  assert.equal(result.features.overUnderImbalance, 0.2);
});

test('trade aggressor inference never uses a quote snapshot from the future', () => {
  const first = q('2026-08-10T00:00:00.000Z', 100, 101, 100, 100);
  const future = q('2026-08-10T00:00:10.000Z', 101, 102, 100, 100);
  const result = buildMicrostructureIntelligence({
    snapshot: future,
    quoteSnapshots: [first, future],
    ticks: [{ timestamp: '2026-08-10T00:00:05.000Z', price: 101, size: 50 }],
  });
  assert.equal(result.classifiedTicks[0].side, 1);
  assert.equal(result.classifiedTicks[0].method, 'CAUSAL_QUOTE_ASK');
  assert.equal(result.classifiedTicks[0].quoteTimestamp, first.timestamp);
  assert.equal(result.dataQuality.futureQuoteAssignments, 0);
  assert.equal(result.dataQuality.causalQuoteMatching, true);
});

test('RssTickList has no native aggressor side, so P22 falls back to a causal tick rule when quotes are unavailable', () => {
  const result = buildMicrostructureIntelligence({
    ticks: [
      { timestamp: '2026-08-10T00:00:00.000Z', price: 100, volume: 20 },
      { timestamp: '2026-08-10T00:00:01.000Z', price: 101, volume: 30 },
      { timestamp: '2026-08-10T00:00:02.000Z', price: 100, volume: 10 },
    ],
  });
  assert.equal(result.classifiedTicks[0].side, 0);
  assert.equal(result.classifiedTicks[1].side, 1);
  assert.equal(result.classifiedTicks[1].method, 'TICK_RULE_UP');
  assert.equal(result.classifiedTicks[2].side, -1);
  assert.equal(result.features.buyVolume, 30);
  assert.equal(result.features.sellVolume, 10);
  assert.equal(result.features.aggressiveBuyRatio, 0.75);
  assert.equal(result.dataQuality.nativeAggressorSideAssumed, false);
});

test('P22 reports quote/tick staleness and quote update intensity without transmitting anything', () => {
  const result = buildMicrostructureIntelligence({
    snapshot: q('2026-08-10T00:00:10.000Z', 100, 100.5),
    quoteSnapshots: [q('2026-08-10T00:00:00.000Z', 100, 100.5), q('2026-08-10T00:00:10.000Z', 100, 100.5)],
    ticks: [{ timestamp: '2026-08-10T00:00:08.000Z', price: 100.5, size: 20 }],
    asOf: '2026-08-10T00:00:20.000Z',
  });
  assert.equal(result.features.quoteStalenessMs, 10000);
  assert.equal(result.features.tickStalenessMs, 12000);
  assert.equal(result.features.quoteUpdateRatePerSecond, 0.1);
  assert.equal(result.transmitted, false);
});

test('P22 contract records official RssTickList limitations instead of inventing unavailable side data', () => {
  assert.deepEqual(MARKETSPEED_II_P22_READ_ONLY_CONTRACT.RssTickList.officialFields, ['時刻', '出来高', '約定値']);
  assert.equal(MARKETSPEED_II_P22_READ_ONLY_CONTRACT.RssTickList.maxRows, 300);
  assert.equal(MARKETSPEED_II_P22_READ_ONLY_CONTRACT.RssTickList.nativeAggressorSideAvailable, false);
  assert.equal(MARKETSPEED_II_P22_READ_ONLY_CONTRACT.orderFunctionsUsed, false);
});

test('P22 keeps every execution/write/paper/live path disabled', () => {
  const result = buildMicrostructureIntelligence({ snapshot: q('2026-08-10T00:00:00.000Z', 100, 101) });
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
  ]) {
    assert.equal(PHASE57_P22_SAFETY[key], false);
    assert.equal(result[key], false);
  }
  assert.equal(PHASE57_P22_SAFETY.overnightHoldingAllowed, false);
});
