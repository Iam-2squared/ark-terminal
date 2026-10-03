import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ENTRY_V2_HISTORICAL_DAILY_POLICY,
  ENTRY_V2_HISTORICAL_DAILY_SAFETY,
  buildYahooDailyChartUrl,
  normalizeYahooDailyChartPayload,
  buildEntryV2HistoricalDailyContext,
} from '../daytrade/phase57-entry-quality-v2-historical-daily-data.js';

const epoch = value => Date.parse(value) / 1000;
const allFalse = object => [
  'executionAllowed',
  'brokerWriteAllowed',
  'excelOrderWriteAllowed',
  'rssOrderFunctionAllowed',
  'liveTradingAllowed',
  'paperTradingAllowed',
  'automaticPromotionAllowed',
  'productionUpdateAllowed',
  'transmitted',
].every(key => object[key] === false);

function payload() {
  return {
    chart: {
      error: null,
      result: [{
        meta: { symbol: '7203.T', currency: 'JPY', dataGranularity: '1d', exchangeTimezoneName: 'Asia/Tokyo' },
        timestamp: [epoch('2026-08-11T00:00:00.000Z'), epoch('2026-08-12T00:00:00.000Z')],
        indicators: {
          quote: [{
            open: [100, 102], high: [103, 105], low: [99, 101], close: [102, 104], volume: [1000, 1200],
          }],
          adjclose: [{ adjclose: [101.5, 103.5] }],
        },
        events: { dividends: { one: { amount: 1 } } },
      }],
    },
  };
}

function dailyRecords(count = 110) {
  const first = Date.parse('2026-04-25T00:00:00.000Z');
  return Array.from({ length: count }, (_, index) => {
    const sessionDate = new Date(first + index * 86_400_000).toISOString().slice(0, 10);
    const close = 100 + index;
    return {
      symbol: '7203.T', kind: 'OHLCV', source: 'YAHOO_CHART', sessionDate,
      open: close - 1, high: close + 2, low: close - 2, close, volume: 1000 + index,
      adjustedClose: close - 0.25, currency: 'JPY',
    };
  });
}

test('daily URL and policy are read-only later-fetched Development only', () => {
  const url = new URL(buildYahooDailyChartUrl({ symbol: '7203.t', range: '2y', host: 2 }));
  assert.equal(url.host, 'query2.finance.yahoo.com');
  assert.equal(url.pathname, '/v8/finance/chart/7203.T');
  assert.equal(url.searchParams.get('range'), '2y');
  assert.equal(url.searchParams.get('interval'), '1d');
  assert.equal(ENTRY_V2_HISTORICAL_DAILY_POLICY.sourceClass, 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED');
  assert.equal(ENTRY_V2_HISTORICAL_DAILY_POLICY.adjustedCloseUsedAsFeature, false);
  assert.equal(allFalse(ENTRY_V2_HISTORICAL_DAILY_SAFETY), true);
});

test('daily normalizer preserves provider timestamps and adjusted close for audit only', () => {
  const normalized = normalizeYahooDailyChartPayload({
    payload: payload(), symbol: '7203.T', universeEntry: { symbol: '7203.T', sector: '輸送用機器' },
    retrievedAt: '2026-09-05T00:00:00.000Z', queryRange: '2y',
  });
  assert.equal(normalized.series.records.length, 2);
  assert.equal(normalized.series.records[0].sessionDate, '2026-08-11');
  assert.equal(normalized.series.records[0].adjustedClose, 101.5);
  assert.equal(normalized.methodology.adjustedCloseStoredForAuditOnly, true);
  assert.equal(normalized.methodology.adjustedCloseUsedAsFeature, false);
  assert.equal(normalized.methodology.providerQuoteCorporateActionSemanticsResolved, false);
  assert.equal(normalized.series.corporateActionEventCounts.dividends, 1);
});

test('daily context slices at each decision, requires full Phase 1 warm-up, and uses prior-session close', () => {
  const records = dailyRecords();
  records.push({
    symbol: '7203.T', kind: 'OHLCV', source: 'YAHOO_CHART', sessionDate: '2026-08-13',
    open: 999, high: 1000, low: 998, close: 999, volume: 9999,
  });
  const built = buildEntryV2HistoricalDailyContext({
    symbol: '7203.T', decisionTimestamp: '2026-08-13T01:00:00.000Z', records,
  });
  assert.equal(built.available, true);
  assert.equal(built.lineage.sameSessionDailyUsed, false);
  assert.equal(built.lineage.archiveSlice.excludedSameOrFutureRecordCount, 1);
  assert.equal(built.context.priorClose, dailyRecords().at(-1).close);
  assert.equal(built.context.latestBarTimestamp, '2026-08-12T06:00:00.000Z');
  assert.equal(built.featureWindowsAvailable.ma100, true);
  assert.equal(built.safety.executionAllowed, false);

  const insufficient = buildEntryV2HistoricalDailyContext({
    symbol: '7203.T', decisionTimestamp: '2026-08-13T01:00:00.000Z', records: dailyRecords(80),
  });
  assert.equal(insufficient.available, false);
  assert.equal(insufficient.context, null);
  assert.equal(insufficient.featureWindowsAvailable.ma100, false);
});
