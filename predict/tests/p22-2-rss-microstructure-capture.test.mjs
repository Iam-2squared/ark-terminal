import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P22_2_SAFETY,
  P22_2_ALLOWED_RSS_FUNCTIONS,
  P22_2_MAX_RSS_TICK_ROWS,
  assertReadOnlyRssFunction,
  normalizeRssTimeOfDay,
  captureConfiguredRssMarketSnapshot,
  ingestConfiguredRssTickListWindow,
  buildConfiguredMicrostructureCaptureBundle,
} from '../daytrade/phase57-rss-microstructure-capture.js';

const sessionDate = '2026-08-10';
const capturedAt = '2026-08-10T00:30:00.000Z'; // 09:30 JST
const tickMap = { time: '時刻', volume: '出来高', price: '約定値' };
const marketMap = {
  bestAsk: 'C55',
  bestBid: 'C56',
  bestAskSize: 'C57',
  bestBidSize: 'C58',
  bestAskDetailedTime: 'C61',
  bestBidDetailedTime: 'C62',
  askPrice1: 'C86',
  bidPrice1: 'C96',
  askSize1: 'C106',
  bidSize1: 'C116',
  overSize: 'C128',
  underSize: 'C129',
};

const tick = (time, price, volume) => ({ '時刻': time, '約定値': price, '出来高': volume });

test('P22.2 whitelists only RssMarket and RssTickList and rejects order or unknown RSS functions', () => {
  assert.deepEqual(P22_2_ALLOWED_RSS_FUNCTIONS, ['RssMarket', 'RssTickList']);
  assert.equal(assertReadOnlyRssFunction('RssMarket'), 'RssMarket');
  assert.equal(assertReadOnlyRssFunction('RssTickList'), 'RssTickList');
  for (const name of ['RssStockOrder', 'RssMarginOpenOrder', 'RssMarginCloseOrder', 'RssModifyOrder', 'RssCancelOrder', 'RssFutureOrder', 'RssOptionOrder']) {
    assert.throws(() => assertReadOnlyRssFunction(name), /forbidden/);
  }
  assert.throws(() => assertReadOnlyRssFunction('RssBuyingPower'), /not whitelisted/);
  assert.throws(() => assertReadOnlyRssFunction('AnythingElse'), /not whitelisted/);
});

test('configured RssMarket mapping captures official quote/depth values without hardcoded Excel cell locations', () => {
  const raw = {
    C55: 100.5, C56: 100.0, C57: 120, C58: 240,
    C61: '09:29:59.500', C62: '09:29:59.300',
    C86: 101.0, C96: 99.5, C106: 80, C116: 160,
    C128: 1000, C129: 1500,
  };
  const result = captureConfiguredRssMarketSnapshot({ symbol: '8035.T', sessionDate, capturedAt, raw, fieldMap: marketMap });
  assert.equal(result.bestAsk, 100.5);
  assert.equal(result.bestBid, 100.0);
  assert.equal(result.askSize, 120);
  assert.equal(result.bidSize, 240);
  assert.equal(result.askPrice1, 101.0);
  assert.equal(result.bidPrice1, 99.5);
  assert.equal(result.askSize1, 80);
  assert.equal(result.bidSize1, 160);
  assert.equal(result.overSize, 1000);
  assert.equal(result.underSize, 1500);
  assert.equal(result.timestamp, '2026-08-10T00:29:59.500Z');
  assert.equal(result.fieldMapConfigured, true);
  assert.equal(result.sourceFunction, 'RssMarket');
  assert.equal(result.transmitted, false);
});

test('P22.2 converts RSS time-of-day in JST and rejects future or cross-session timestamps', () => {
  assert.equal(
    normalizeRssTimeOfDay('09:29:59.250', { sessionDate, capturedAt }),
    '2026-08-10T00:29:59.250Z',
  );
  assert.equal(
    normalizeRssTimeOfDay((9 * 3600 + 29 * 60 + 59) / 86400, { sessionDate, capturedAt }),
    '2026-08-10T00:29:59.000Z',
  );
  assert.throws(
    () => normalizeRssTimeOfDay('09:31:00', { sessionDate, capturedAt }),
    /future/,
  );
  assert.throws(
    () => normalizeRssTimeOfDay('2026-08-09T00:29:59.000Z', { sessionDate, capturedAt }),
    /outside sessionDate/,
  );
  assert.throws(
    () => normalizeRssTimeOfDay('09:29:59', { sessionDate, capturedAt: '2026-08-09T14:59:00.000Z' }),
    /capturedAt is outside sessionDate/,
  );
});

test('rolling overlap emits only new ticks while preserving genuine repeated identical prints by multiplicity', () => {
  const previousWindow = [
    { timestamp: '2026-08-10T00:29:50.000Z', price: 100, volume: 10 },
    { timestamp: '2026-08-10T00:29:51.000Z', price: 101, volume: 20 },
    { timestamp: '2026-08-10T00:29:51.000Z', price: 101, volume: 20 },
  ];
  const rawRows = [
    tick('09:29:51', 101, 20),
    tick('09:29:51', 101, 20),
    tick('09:29:52', 101, 20),
    tick('09:29:52', 101, 20),
  ];
  const result = ingestConfiguredRssTickListWindow({
    symbol: '8035.T', sessionDate, capturedAt, rawRows, fieldMap: tickMap, tickOrder: 'ASC', previousWindow,
  });
  assert.equal(result.overlapLength, 2);
  assert.equal(result.newTickCount, 2);
  assert.deepEqual(result.newTicks.map(row => [row.timestamp, row.price, row.volume]), [
    ['2026-08-10T00:29:52.000Z', 101, 20],
    ['2026-08-10T00:29:52.000Z', 101, 20],
  ]);
  assert.equal(result.duplicateTupleOccurrencesPreserved, 4);
  assert.notEqual(result.newTicks[0].tickOrdinalWithinCapture, result.newTicks[1].tickOrdinalWithinCapture);
  assert.equal(result.continuityStatus, 'ROLLING_WINDOW_OVERLAP_RECONCILED');
  assert.equal(result.replayEligible, true);
});

test('DESC RssTickList source order is explicitly normalized to chronological order before overlap reconciliation', () => {
  const result = ingestConfiguredRssTickListWindow({
    symbol: '6758.T', sessionDate, capturedAt,
    rawRows: [tick('09:29:59', 103, 30), tick('09:29:58', 102, 20), tick('09:29:57', 101, 10)],
    fieldMap: tickMap,
    tickOrder: 'DESC',
  });
  assert.deepEqual(result.window.map(row => row.timestamp), [
    '2026-08-10T00:29:57.000Z',
    '2026-08-10T00:29:58.000Z',
    '2026-08-10T00:29:59.000Z',
  ]);
  assert.equal(result.newTickCount, 3);
});

test('tick ordering must be explicitly configured and timestamps must agree with it', () => {
  assert.throws(() => ingestConfiguredRssTickListWindow({
    symbol: '7203.T', sessionDate, capturedAt,
    rawRows: [tick('09:29:58', 100, 10)], fieldMap: tickMap,
  }), /tickOrder/);
  assert.throws(() => ingestConfiguredRssTickListWindow({
    symbol: '7203.T', sessionDate, capturedAt,
    rawRows: [tick('09:29:59', 101, 10), tick('09:29:58', 100, 10)], fieldMap: tickMap, tickOrder: 'ASC',
  }), /conflicts/);
});

test('a fully identical 300-row rolling window is quarantined because RSS exposes no sequence id', () => {
  const previousWindow = Array.from({ length: P22_2_MAX_RSS_TICK_ROWS }, () => ({
    timestamp: '2026-08-10T00:29:59.000Z', price: 100, volume: 10,
  }));
  const rawRows = Array.from({ length: P22_2_MAX_RSS_TICK_ROWS }, () => tick('09:29:59', 100, 10));
  const result = ingestConfiguredRssTickListWindow({
    symbol: '9984.T', sessionDate, capturedAt, rawRows, fieldMap: tickMap, tickOrder: 'ASC', previousWindow,
  });
  assert.equal(result.overlapLength, P22_2_MAX_RSS_TICK_ROWS);
  assert.equal(result.newTickCount, 0);
  assert.equal(result.replayEligible, false);
  assert.equal(result.continuityStatus, 'AMBIGUOUS_FULL_300_ROW_WINDOW_NO_SEQUENCE');
  assert.match(result.ambiguityReason, /no sequence id/);
});

test('configured capture bundle remains READ ONLY and rejects symbol/session mismatch', () => {
  const market = captureConfiguredRssMarketSnapshot({
    symbol: '8035.T', sessionDate, capturedAt,
    raw: { C55: 100.5, C56: 100.0, C57: 120, C58: 240 },
    fieldMap: marketMap,
  });
  const ticks = ingestConfiguredRssTickListWindow({
    symbol: '8035.T', sessionDate, capturedAt,
    rawRows: [tick('09:29:59', 100.5, 20)], fieldMap: tickMap, tickOrder: 'ASC',
  });
  const bundle = buildConfiguredMicrostructureCaptureBundle({ market, ticks });
  assert.equal(bundle.status, 'RSS_MICROSTRUCTURE_CAPTURE_READY');
  assert.equal(bundle.persistenceMode, 'RESEARCH_EVENT_ONLY');
  assert.equal(bundle.intelligenceInput.ticks.length, 1);
  assert.equal(bundle.transmitted, false);
  assert.throws(() => buildConfiguredMicrostructureCaptureBundle({ market, ticks: { ...ticks, symbol: '7203.T' } }), /mismatch/);
});

test('P22.2 requires explicit field maps and never enables execution, writes, paper/live trading or promotion', () => {
  assert.throws(() => captureConfiguredRssMarketSnapshot({
    symbol: '8035.T', sessionDate, capturedAt,
    raw: { bestAsk: 101, bestBid: 100, askSize: 10, bidSize: 10 },
  }), /fieldMap/);
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
  ]) assert.equal(PHASE57_P22_2_SAFETY[key], false);
  assert.equal(PHASE57_P22_2_SAFETY.overnightHoldingAllowed, false);
});
