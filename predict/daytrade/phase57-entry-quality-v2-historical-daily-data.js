import { createHash } from 'node:crypto';
import {
  ENTRY_V2_DAILY_HISTORY_POLICY,
  sliceEntryV2DailyArchivePriorToAsOf,
  buildEntryV2PriorDailyHistoryFeed,
} from './phase57-entry-quality-v2-daily-history-feed.js';
import {
  PHASE57_ENTRY_QUALITY_V2_SAFETY,
  buildEntryV2DailyContext,
} from './phase57-entry-quality-v2-research.js';
import { ENTRY_V2_SOURCE_CLASS } from './phase57-entry-quality-v2-candidate-inventory.js';

export const ENTRY_V2_HISTORICAL_DAILY_POLICY = Object.freeze({
  phase: '57.entry-quality-v2.historical-daily-reconstruction',
  mode: 'ENTRY_V2_HISTORICAL_DAILY_RECONSTRUCTION_READ_ONLY',
  provider: 'YAHOO_FINANCE_CHART',
  acceptedFeedSource: 'YAHOO_CHART',
  interval: '1d',
  defaultRange: '2y',
  retentionTargetBars: ENTRY_V2_DAILY_HISTORY_POLICY.retentionTargetBars,
  requiredBarsForPhase1Features: 101,
  featureWindows: Object.freeze([1, 5, 20, 50, 100]),
  sourceClass: ENTRY_V2_SOURCE_CLASS.historicalReconstructionLaterFetched,
  datasetRole: 'DEVELOPMENT_ONLY',
  prospective: false,
  formalOos: false,
  sameSessionDailyAllowed: false,
  adjustedCloseUsedAsFeature: false,
  missingDailyBarsMayBeFabricated: false,
});

export const ENTRY_V2_HISTORICAL_DAILY_SAFETY = Object.freeze({
  ...PHASE57_ENTRY_QUALITY_V2_SAFETY,
  phase: ENTRY_V2_HISTORICAL_DAILY_POLICY.phase,
  mode: 'READ_ONLY_OFFLINE_HISTORICAL_DAILY_RESEARCH',
  researchOnly: true,
  prospective: false,
  formalOos: false,
  freshHoldoutConsumed: false,
});

const FALSE_KEYS = Object.freeze([
  'executionAllowed',
  'brokerWriteAllowed',
  'excelOrderWriteAllowed',
  'rssOrderFunctionAllowed',
  'liveTradingAllowed',
  'paperTradingAllowed',
  'automaticPromotionAllowed',
  'productionUpdateAllowed',
  'transmitted',
]);

const sha256 = value => createHash('sha256')
  .update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value))
  .digest('hex');
const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const symbolOf = value => String(value ?? '').trim().toUpperCase();

function assertSafety() {
  for (const key of FALSE_KEYS) {
    if (ENTRY_V2_HISTORICAL_DAILY_SAFETY[key] !== false) {
      throw new Error(`ENTRY_V2_HISTORICAL_DAILY_UNSAFE_${key}`);
    }
  }
}

function jstSessionDate(value) {
  const timestamp = Date.parse(String(value ?? ''));
  if (!Number.isFinite(timestamp)) throw new Error('ENTRY_V2_HISTORICAL_DAILY_TIMESTAMP_INVALID');
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(timestamp)).map(part => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function buildYahooDailyChartUrl({ symbol, range = '2y', host = 1 } = {}) {
  const normalized = symbolOf(symbol);
  if (!normalized) throw new Error('ENTRY_V2_YAHOO_DAILY_SYMBOL_REQUIRED');
  if (!['1', '2', 1, 2].includes(host) || !/^\d+(?:d|mo|y)$/.test(String(range))) {
    throw new Error('ENTRY_V2_YAHOO_DAILY_QUERY_INVALID');
  }
  const query = new URLSearchParams({
    range: String(range),
    interval: ENTRY_V2_HISTORICAL_DAILY_POLICY.interval,
    includePrePost: 'false',
    events: 'div,splits',
  });
  return `https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(normalized)}?${query.toString()}`;
}

export function normalizeYahooDailyChartPayload({
  payload,
  symbol,
  universeEntry = {},
  retrievedAt,
  queryRange = ENTRY_V2_HISTORICAL_DAILY_POLICY.defaultRange,
} = {}) {
  assertSafety();
  const normalizedSymbol = symbolOf(symbol);
  const retrievedAtIso = new Date(retrievedAt ?? '').toISOString();
  if (!normalizedSymbol || (universeEntry?.symbol && symbolOf(universeEntry.symbol) !== normalizedSymbol)) {
    throw new Error('ENTRY_V2_YAHOO_DAILY_REQUEST_SYMBOL_INVALID');
  }
  if (payload?.chart?.error) {
    throw new Error(`ENTRY_V2_YAHOO_DAILY_PROVIDER_ERROR:${payload.chart.error.description ?? 'UNKNOWN'}`);
  }
  const results = Array.isArray(payload?.chart?.result) ? payload.chart.result : [];
  if (results.length !== 1) throw new Error('ENTRY_V2_YAHOO_DAILY_SINGLE_RESULT_REQUIRED');
  const response = results[0];
  const responseSymbol = symbolOf(response?.meta?.symbol);
  if (responseSymbol && responseSymbol !== normalizedSymbol) {
    throw new Error('ENTRY_V2_YAHOO_DAILY_RESPONSE_SYMBOL_MISMATCH');
  }
  const timestamps = Array.isArray(response?.timestamp) ? response.timestamp : [];
  const quote = response?.indicators?.quote?.[0];
  if (!quote || !timestamps.length) throw new Error('ENTRY_V2_YAHOO_DAILY_MISSING_OR_EMPTY_SERIES');
  for (const field of ['open', 'high', 'low', 'close', 'volume']) {
    if (!Array.isArray(quote[field]) || quote[field].length !== timestamps.length) {
      throw new Error(`ENTRY_V2_YAHOO_DAILY_FULL_OHLCV_REQUIRED_${field}`);
    }
  }
  const adjusted = response?.indicators?.adjclose?.[0]?.adjclose;
  if (adjusted !== undefined && (!Array.isArray(adjusted) || adjusted.length !== timestamps.length)) {
    throw new Error('ENTRY_V2_YAHOO_DAILY_ADJUSTED_CLOSE_ALIGNMENT_INVALID');
  }
  const records = [];
  for (let index = 0; index < timestamps.length; index += 1) {
    const epoch = Number(timestamps[index]);
    const values = [quote.open[index], quote.high[index], quote.low[index], quote.close[index]];
    const volume = quote.volume[index];
    if (!Number.isFinite(epoch) || values.some(value => !finite(value)) || !finite(volume)) continue;
    const [open, high, low, close] = values.map(Number);
    const normalizedVolume = Number(volume);
    if (Math.min(open, high, low, close) <= 0 || high < Math.max(open, close)
      || low > Math.min(open, close) || normalizedVolume < 0) continue;
    const rawProviderTimestamp = new Date(epoch * 1000).toISOString();
    records.push(Object.freeze({
      symbol: normalizedSymbol,
      kind: 'OHLCV',
      source: ENTRY_V2_HISTORICAL_DAILY_POLICY.acceptedFeedSource,
      sessionDate: jstSessionDate(rawProviderTimestamp),
      rawProviderTimestampEpochSeconds: epoch,
      rawProviderTimestamp,
      open,
      high,
      low,
      close,
      volume: normalizedVolume,
      adjustedClose: finite(adjusted?.[index]) && Number(adjusted[index]) > 0 ? Number(adjusted[index]) : null,
      currency: String(response?.meta?.currency ?? 'JPY'),
    }));
  }
  records.sort((left, right) => left.sessionDate.localeCompare(right.sessionDate));
  if (!records.length || new Set(records.map(record => record.sessionDate)).size !== records.length) {
    throw new Error(records.length
      ? 'ENTRY_V2_YAHOO_DAILY_DUPLICATE_SESSION_DATE'
      : 'ENTRY_V2_YAHOO_DAILY_NO_VALID_RECORDS');
  }
  const eventCounts = Object.fromEntries(Object.entries(response?.events ?? {}).map(([key, value]) => (
    [key, value && typeof value === 'object' ? Object.keys(value).length : 0]
  )));
  return Object.freeze({
    phase: ENTRY_V2_HISTORICAL_DAILY_POLICY.phase,
    status: 'ENTRY_V2_YAHOO_DAILY_SERIES_READY',
    sourceClass: ENTRY_V2_HISTORICAL_DAILY_POLICY.sourceClass,
    datasetRole: 'DEVELOPMENT_ONLY',
    prospective: false,
    formalOos: false,
    retrievedAt: retrievedAtIso,
    queryRange,
    interval: '1d',
    series: Object.freeze({
      symbol: normalizedSymbol,
      code: String(universeEntry?.code ?? normalizedSymbol.replace(/\.T$/i, '')),
      name: String(universeEntry?.name ?? normalizedSymbol),
      sector: String(universeEntry?.sector ?? '未分類'),
      market: universeEntry?.market ?? null,
      records: Object.freeze(records),
      providerMeta: Object.freeze({
        exchangeName: response?.meta?.exchangeName ?? null,
        exchangeTimezoneName: response?.meta?.exchangeTimezoneName ?? null,
        dataGranularity: response?.meta?.dataGranularity ?? null,
        currency: response?.meta?.currency ?? null,
        instrumentType: response?.meta?.instrumentType ?? null,
      }),
      corporateActionEventCounts: Object.freeze(eventCounts),
    }),
    rawPayloadSha256: sha256(payload),
    methodology: Object.freeze({
      laterFetchedHistoricalReconstruction: true,
      priorSessionSlicingDeferredUntilEachDecisionTimestamp: true,
      providerTimestampPreserved: true,
      providerQuoteOhlcvUsedAsRawFeatureBasis: true,
      adjustedCloseStoredForAuditOnly: true,
      adjustedCloseUsedAsFeature: false,
      providerQuoteCorporateActionSemanticsResolved: false,
      missingDailyBarsInterpolatedOrFabricated: false,
    }),
    safety: ENTRY_V2_HISTORICAL_DAILY_SAFETY,
  });
}

export function buildEntryV2HistoricalDailyContext({
  symbol,
  decisionTimestamp,
  records = [],
  retentionBars = ENTRY_V2_HISTORICAL_DAILY_POLICY.retentionTargetBars,
  requiredBars = ENTRY_V2_HISTORICAL_DAILY_POLICY.requiredBarsForPhase1Features,
} = {}) {
  assertSafety();
  const normalizedSymbol = symbolOf(symbol);
  const decisionSessionDate = jstSessionDate(decisionTimestamp);
  const required = Number(requiredBars);
  if (!normalizedSymbol || !Number.isInteger(required) || required < 1) {
    throw new Error('ENTRY_V2_HISTORICAL_DAILY_CONTEXT_ARGUMENT_INVALID');
  }
  const sliced = sliceEntryV2DailyArchivePriorToAsOf({
    symbol: normalizedSymbol,
    asOf: decisionTimestamp,
    records,
  });
  const feed = buildEntryV2PriorDailyHistoryFeed({
    symbol: normalizedSymbol,
    asOf: decisionTimestamp,
    records: sliced.records,
    retentionBars,
  });
  const featureWindowsAvailable = Object.freeze({
    return1d: feed.bars.length >= 2,
    return5d: feed.bars.length >= 6,
    return20d: feed.bars.length >= 21,
    ma20: feed.bars.length >= 21,
    ma50: feed.bars.length >= 51,
    ma100: feed.bars.length >= 101,
    atr20: feed.bars.length >= 20,
    volatility20: feed.bars.length >= 20,
    volumeRegime20: feed.bars.length >= 21,
  });
  const enough = feed.bars.length >= required;
  const context = enough ? buildEntryV2DailyContext({ dailyBars: feed.bars, asOf: decisionTimestamp }) : null;
  if (context && jstSessionDate(context.latestBarTimestamp) >= decisionSessionDate) {
    throw new Error('ENTRY_V2_HISTORICAL_DAILY_CONTEXT_SAME_OR_FUTURE_SESSION');
  }
  return Object.freeze({
    status: enough
      ? 'ENTRY_V2_HISTORICAL_PRIOR_DAILY_CONTEXT_READY'
      : 'ENTRY_V2_HISTORICAL_PRIOR_DAILY_CONTEXT_INSUFFICIENT',
    available: enough,
    sourceClass: ENTRY_V2_HISTORICAL_DAILY_POLICY.sourceClass,
    datasetRole: 'DEVELOPMENT_ONLY',
    prospective: false,
    formalOos: false,
    symbol: normalizedSymbol,
    decisionTimestamp: new Date(decisionTimestamp).toISOString(),
    decisionSessionDate,
    availablePriorSessions: feed.lineage.availablePriorSessions,
    retainedPriorSessions: feed.lineage.retainedSessions,
    requiredPriorSessions: required,
    featureWindowsAvailable,
    context,
    lineage: Object.freeze({
      ...feed.lineage,
      archiveSlice: sliced.lineage,
      sourceFingerprintSha256: feed.sourceFingerprintSha256,
      retainedBarsFingerprintSha256: feed.retainedBarsFingerprintSha256,
      sameSessionDailyUsed: false,
      adjustedCloseUsedAsFeature: false,
      missingDailyBarsFabricated: false,
    }),
    safety: ENTRY_V2_HISTORICAL_DAILY_SAFETY,
  });
}

export default {
  ENTRY_V2_HISTORICAL_DAILY_POLICY,
  ENTRY_V2_HISTORICAL_DAILY_SAFETY,
  buildYahooDailyChartUrl,
  normalizeYahooDailyChartPayload,
  buildEntryV2HistoricalDailyContext,
};
