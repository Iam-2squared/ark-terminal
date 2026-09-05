import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ENTRY_V2_HISTORICAL_MARKET_POLICY,
  ENTRY_V2_HISTORICAL_MARKET_SAFETY,
  buildYahooChartUrl,
  normalizeYahooChartPayload,
  partitionHistoricalSeriesBySession,
  entryV2HistoricalDecisionTimestamps,
  buildEntryV2HistoricalMarketSnapshots,
  buildEntryV2HistoricalMarketContext,
  buildEntryV2HistoricalSelectorMeasurements,
  buildEntryV2HistoricalSessionBarArchive,
} from '../daytrade/phase57-entry-quality-v2-historical-market-data.js';

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

function chartPayload() {
  const timestamp = [
    epoch('2026-08-12T06:30:00.000Z'),
    epoch('2026-08-13T00:00:00.000Z'),
    epoch('2026-08-13T00:05:00.000Z'),
    epoch('2026-08-13T00:10:00.000Z'),
  ];
  return {
    chart: {
      error: null,
      result: [{
        meta: {
          symbol: '7203.T',
          exchangeName: 'JPX',
          exchangeTimezoneName: 'Asia/Tokyo',
          dataGranularity: '5m',
          currency: 'JPY',
          instrumentType: 'EQUITY',
        },
        timestamp,
        indicators: {
          quote: [{
            open: [100, 101, 102, 103],
            high: [101, 102, 103, 104],
            low: [99, 100, 101, 102],
            close: [100, 101, 102, 103],
            volume: [1000, 1100, 1200, 1300],
          }],
        },
      }],
    },
  };
}

test('Yahoo Chart URL is read-only, single-symbol, five-minute historical data', () => {
  const url = new URL(buildYahooChartUrl({ symbol: '7203.t', range: '30d', interval: '5m', host: 2 }));
  assert.equal(url.host, 'query2.finance.yahoo.com');
  assert.equal(url.pathname, '/v8/finance/chart/7203.T');
  assert.equal(url.searchParams.get('range'), '30d');
  assert.equal(url.searchParams.get('interval'), '5m');
  assert.equal(url.searchParams.get('includePrePost'), 'false');
  assert.equal(allFalse(ENTRY_V2_HISTORICAL_MARKET_SAFETY), true);
  assert.equal(ENTRY_V2_HISTORICAL_MARKET_POLICY.sourceClass, 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED');
  assert.equal(ENTRY_V2_HISTORICAL_MARKET_POLICY.prospective, false);
});

test('Yahoo payload keeps provider timestamps and requires complete OHLCV arrays', () => {
  const normalized = normalizeYahooChartPayload({
    payload: chartPayload(),
    symbol: '7203.T',
    universeEntry: { symbol: '7203.T', code: '7203', name: 'Toyota', sector: '輸送用機器', market: 'プライム' },
    retrievedAt: '2026-09-05T00:00:00.000Z',
  });
  assert.equal(normalized.status, 'ENTRY_V2_YAHOO_CHART_SERIES_READY');
  assert.equal(normalized.series.bars.length, 4);
  assert.equal(normalized.series.bars[1].timestamp, '2026-08-13T00:00:00.000Z');
  assert.equal(normalized.series.bars[1].rawProviderTimestamp, '2026-08-13T00:00:00.000Z');
  assert.equal(normalized.series.bars[1].normalizedJstTimestamp, '2026-08-13T09:00:00+09:00');
  assert.equal(normalized.methodology.providerTimestampPreservedWithoutShift, true);

  const priceOnly = chartPayload();
  delete priceOnly.chart.result[0].indicators.quote[0].volume;
  assert.throws(() => normalizeYahooChartPayload({
    payload: priceOnly,
    symbol: '7203.T',
    universeEntry: { symbol: '7203.T' },
    retrievedAt: '2026-09-05T00:00:00.000Z',
  }), /FULL_OHLCV_REQUIRED_volume/);
});

test('session partition uses only the preceding available session close', () => {
  const normalized = normalizeYahooChartPayload({
    payload: chartPayload(),
    symbol: '7203.T',
    universeEntry: { symbol: '7203.T' },
    retrievedAt: '2026-09-05T00:00:00.000Z',
  });
  const sessions = partitionHistoricalSeriesBySession({
    series: [normalized.series],
    startSessionDate: '2026-08-13',
    endSessionDate: '2026-08-13',
  });
  const row = sessions.get('2026-08-13')[0];
  assert.equal(row.previousClose, 100);
  assert.equal(row.previousCloseSessionDate, '2026-08-12');
  assert.equal(row.bars.length, 3);
});

test('market snapshots use completed bars only and cover all 68 frozen five-minute points', () => {
  const sessionSeries = Array.from({ length: 3000 }, (_, index) => ({
    symbol: `${String(index + 1000).padStart(4, '0')}.T`,
    sector: `S${index % 20}`,
    market: 'TEST',
    previousClose: 100,
    previousCloseSessionDate: '2026-08-12',
    bars: [
      { timestamp: '2026-08-13T00:00:00.000Z', sessionDate: '2026-08-13', open: 100, high: 102, low: 99, close: 101 + index / 10000, volume: 1000 + index },
      { timestamp: '2026-08-13T00:05:00.000Z', sessionDate: '2026-08-13', open: 101, high: 999, low: 100, close: 999, volume: 500 },
    ],
  }));
  assert.equal(entryV2HistoricalDecisionTimestamps('2026-08-13').length, 68);
  const built = buildEntryV2HistoricalMarketSnapshots({
    sessionDate: '2026-08-13',
    sessionSeries,
    universeSymbolCount: 3000,
    minimumMarketwideSymbols: 3000,
    sourceLineage: { reconstructionFetchedAfterDecision: true, archivedPointInTimeCapture: false },
  });
  assert.equal(built.points[0].observedAt, '2026-08-13T00:00:00.000Z');
  assert.equal(built.points[0].symbolCount, 0);
  assert.equal(built.points[1].observedAt, '2026-08-13T00:05:00.000Z');
  assert.equal(built.points[1].symbolCount, 3000);
  assert.ok(built.points[1].rows[0].price < 999);
  assert.equal(built.points[2].rows[0].price, 999);
  assert.equal(built.pitViolationCount, 0);
  assert.equal(built.points[1].methodology.futureBarsUsed, false);

  const measurements = buildEntryV2HistoricalSelectorMeasurements({ snapshots: built.readyPoints.slice(0, 2) });
  assert.equal(measurements.measurementCount, 2);
  assert.equal(measurements.candidateId, 'INTRADAY_DYNAMIC_5M_UNIVERSE_V1');
  assert.ok(measurements.v1SelectedMembershipCount > 0);
});

test('pre-frozen-history replay and ambiguous later-fetched bar lineage fail closed', () => {
  assert.throws(() => buildEntryV2HistoricalMarketSnapshots({
    sessionDate: '2026-08-12', sessionSeries: [], universeSymbolCount: 3000,
  }), /PRE_FROZEN_HISTORY_REPLAY_FORBIDDEN/);

  const archive = buildEntryV2HistoricalSessionBarArchive({
    sessionDate: '2026-08-13',
    sessionSeries: [{
      symbol: '7203.T',
      bars: [{ timestamp: '2026-08-13T00:00:00.000Z', open: 100, high: 101, low: 99, close: 100, volume: 1000 }],
    }],
    requiredSymbols: ['7203.T'],
    retrievedAt: '2026-09-05T00:00:00.000Z',
    sourceArtifact: 'session-2026-08-13.ndjson.gz',
    sourceArtifactSha256: 'a'.repeat(64),
    sourceManifestSha256: 'b'.repeat(64),
  });
  assert.equal(archive.status, 'ENTRY_V2_HISTORICAL_SESSION_BAR_ARCHIVE_READY');
  assert.equal(archive.sourceLineage.archivedPointInTimeCapture, false);
  assert.equal(archive.sourceLineage.reconstructionFetchedAfterDecision, true);
  assert.equal(allFalse(archive.safety), true);
});

test('market context uses the same PIT snapshot and never fabricates missing index values', () => {
  const rows = Array.from({ length: 3000 }, (_, index) => ({
    symbol: `${String(index + 1000).padStart(4, '0')}.T`,
    sector: index < 100 ? 'TEST_SECTOR' : 'OTHER',
    previousClose: 100,
    bars: [{
      timestamp: '2026-08-13T00:00:00.000Z', sessionDate: '2026-08-13',
      open: 100, high: 102, low: 99, close: index % 2 ? 101 : 99, volume: 1000,
    }],
  }));
  const snapshots = buildEntryV2HistoricalMarketSnapshots({
    sessionDate: '2026-08-13',
    sessionSeries: rows,
    universeSymbolCount: 3000,
    minimumMarketwideSymbols: 3000,
  });
  const context = buildEntryV2HistoricalMarketContext({
    snapshot: snapshots.readyPoints[0],
    sector: 'TEST_SECTOR',
  });
  assert.equal(context.observedAt, '2026-08-13T00:05:00.000Z');
  assert.equal(context.breadthUpRatio, 0.5);
  assert.equal(context.breadthDownRatio, 0.5);
  assert.equal(context.marketBreadthContextAvailable, true);
  assert.equal(context.benchmarkIndexContextAvailable, false);
  assert.equal(context.topixReturnPct, null);
  assert.equal(context.nikkeiReturnPct, null);
  assert.equal(context.missingValuesFabricated, false);
});
