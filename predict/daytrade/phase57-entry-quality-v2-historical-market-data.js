import { createHash } from 'node:crypto';
import {
  buildIntradayDynamicUniverseTimeline,
  PHASE57_INTRADAY_UNIVERSE_POLICY,
} from './phase57-p25-intraday-dynamic-universe.js';
import {
  buildIntradayDynamicUniverseTimelineV2,
  PHASE57_INTRADAY_UNIVERSE_V2_POLICY,
} from './phase57-p25-intraday-dynamic-universe-v2.js';
import { ENTRY_V2_SOURCE_CLASS } from './phase57-entry-quality-v2-candidate-inventory.js';

export const ENTRY_V2_HISTORICAL_MARKET_POLICY = Object.freeze({
  mode: 'ENTRY_V2_ZERO_BASED_HISTORICAL_MARKET_RECONSTRUCTION',
  phase: '57.entry-quality-v2.historical-market-reconstruction',
  provider: 'YAHOO_FINANCE_CHART',
  interval: '5m',
  defaultRange: '30d',
  empiricallyAcceptedMaximumRange: '60d',
  maximumSymbolsPerRequest: 1,
  frozenP21HistoryEndSessionDate: '2026-08-12',
  earliestLeakageSafeReplaySessionDate: '2026-08-13',
  minimumMarketwideSymbols: 3000,
  cadenceMinutes: 5,
  minimumClosedPrefixBars: 6,
  sourceClass: ENTRY_V2_SOURCE_CLASS.historicalReconstructionLaterFetched,
  datasetRole: 'DEVELOPMENT_ONLY',
  prospective: false,
  formalOos: false,
  completedBarRule: 'bar.timestamp + 5 minutes <= decisionTimestamp',
  selectorCandidateId: PHASE57_INTRADAY_UNIVERSE_POLICY.candidateId,
  frozenEntryBaseline: 'PHASE57_P21_FROZEN_ENTRY',
});

export const ENTRY_V2_HISTORICAL_MARKET_SAFETY = Object.freeze({
  phase: ENTRY_V2_HISTORICAL_MARKET_POLICY.phase,
  mode: 'READ_ONLY_OFFLINE_HISTORICAL_MARKET_RESEARCH',
  researchOnly: true,
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
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

const JST = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Tokyo',
  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  hourCycle: 'h23',
});

const sha256 = value => createHash('sha256')
  .update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value))
  .digest('hex');

export function buildEntryV2SelectionScopeIdentity(scope = {}) {
  if (!scope || typeof scope !== 'object' || Array.isArray(scope)) {
    throw new Error('ENTRY_V2_SELECTION_SCOPE_OBJECT_REQUIRED');
  }
  const identity = structuredClone(scope);
  delete identity.selectionScopeContentSha256;
  delete identity.generatedAt;
  return Object.freeze(identity);
}

export function fingerprintEntryV2SelectionScope(scope = {}) {
  return sha256(Buffer.from(JSON.stringify(buildEntryV2SelectionScopeIdentity(scope))));
}

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const symbolOf = value => String(value ?? '').trim().toUpperCase();
const mean = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

function median(values) {
  if (!values.length) return null;
  const ordered = [...values].sort((left, right) => left - right);
  const middle = Math.floor(ordered.length / 2);
  return ordered.length % 2 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2;
}

function standardDeviation(values) {
  const average = mean(values);
  if (average === null || values.length < 2) return null;
  return Math.sqrt(values.reduce((sum, value) => sum + (value - average) ** 2, 0) / values.length);
}

function jstParts(value) {
  const timestamp = Date.parse(String(value ?? ''));
  if (!Number.isFinite(timestamp)) throw new Error('ENTRY_V2_HISTORICAL_MARKET_TIMESTAMP_INVALID');
  const parts = Object.fromEntries(JST.formatToParts(new Date(timestamp)).map(part => [part.type, part.value]));
  return {
    sessionDate: `${parts.year}-${parts.month}-${parts.day}`,
    hm: `${parts.hour}:${parts.minute}`,
    minuteOfDay: Number(parts.hour) * 60 + Number(parts.minute),
  };
}

function assertSafety(safety, label) {
  for (const key of FALSE_KEYS) {
    if (safety?.[key] !== false) throw new Error(`ENTRY_V2_HISTORICAL_MARKET_UNSAFE_${label}_${key}`);
  }
}

function validateSessionDate(value, label = 'SESSION_DATE') {
  const sessionDate = String(value ?? '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)) {
    throw new Error(`ENTRY_V2_HISTORICAL_MARKET_${label}_INVALID`);
  }
  return sessionDate;
}

function regularSessionBarStart(hm) {
  return (hm >= '09:00' && hm <= '11:30') || (hm >= '12:30' && hm <= '15:30');
}

export function buildYahooChartUrl({ symbol, range = '30d', interval = '5m', host = 1 } = {}) {
  const normalized = symbolOf(symbol);
  if (!normalized) throw new Error('ENTRY_V2_YAHOO_CHART_SYMBOL_REQUIRED');
  if (!['1', '2', 1, 2].includes(host)) throw new Error('ENTRY_V2_YAHOO_CHART_HOST_INVALID');
  if (!/^\d+d$/.test(String(range)) || !['1m', '2m', '5m', '15m', '30m', '60m', '1d'].includes(String(interval))) {
    throw new Error('ENTRY_V2_YAHOO_CHART_QUERY_INVALID');
  }
  const query = new URLSearchParams({
    range: String(range),
    interval: String(interval),
    includePrePost: 'false',
    events: 'div,splits',
  });
  return `https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(normalized)}?${query.toString()}`;
}

function normalizeBar({ timestamp, quote, index }) {
  const epoch = Number(timestamp);
  const values = [quote?.open?.[index], quote?.high?.[index], quote?.low?.[index], quote?.close?.[index]];
  const volume = quote?.volume?.[index];
  if (!Number.isFinite(epoch) || values.some(value => !finite(value)) || !finite(volume)) return null;
  const iso = new Date(epoch * 1000).toISOString();
  const parts = jstParts(iso);
  if (!regularSessionBarStart(parts.hm)) return null;
  const [open, high, low, close] = values.map(Number);
  const normalizedVolume = Number(volume);
  if (Math.min(open, high, low, close) <= 0 || high < Math.max(open, close)
    || low > Math.min(open, close) || normalizedVolume < 0) return null;
  return Object.freeze({
    timestamp: iso,
    rawProviderTimestampEpochSeconds: epoch,
    rawProviderTimestamp: iso,
    normalizedJstTimestamp: `${parts.sessionDate}T${parts.hm}:00+09:00`,
    sessionDate: parts.sessionDate,
    open,
    high,
    low,
    close,
    volume: normalizedVolume,
  });
}

export function normalizeYahooChartPayload({
  payload,
  symbol,
  universeEntry = {},
  retrievedAt,
  queryRange = '30d',
  interval = '5m',
} = {}) {
  const retrievedAtIso = new Date(retrievedAt ?? '').toISOString();
  const normalizedSymbol = symbolOf(symbol);
  if (!normalizedSymbol || symbolOf(universeEntry?.symbol) !== normalizedSymbol) {
    throw new Error('ENTRY_V2_YAHOO_CHART_REQUEST_SYMBOL_INVALID');
  }
  if (interval !== '5m') throw new Error('ENTRY_V2_YAHOO_CHART_5M_REQUIRED');
  if (payload?.chart?.error) throw new Error(`ENTRY_V2_YAHOO_CHART_PROVIDER_ERROR:${payload.chart.error.description ?? 'UNKNOWN'}`);
  const results = Array.isArray(payload?.chart?.result) ? payload.chart.result : [];
  if (results.length !== 1) throw new Error('ENTRY_V2_YAHOO_CHART_SINGLE_RESULT_REQUIRED');
  const response = results[0];
  const responseSymbol = symbolOf(response?.meta?.symbol);
  if (responseSymbol && responseSymbol !== normalizedSymbol) throw new Error('ENTRY_V2_YAHOO_CHART_RESPONSE_SYMBOL_MISMATCH');
  const timestamps = Array.isArray(response?.timestamp) ? response.timestamp : [];
  const quote = response?.indicators?.quote?.[0];
  if (!quote || !timestamps.length) throw new Error('ENTRY_V2_YAHOO_CHART_MISSING_OR_EMPTY_SERIES');
  for (const field of ['open', 'high', 'low', 'close', 'volume']) {
    if (!Array.isArray(quote[field]) || quote[field].length !== timestamps.length) {
      throw new Error(`ENTRY_V2_YAHOO_CHART_FULL_OHLCV_REQUIRED_${field}`);
    }
  }
  const bars = timestamps.map((timestamp, index) => normalizeBar({ timestamp, quote, index })).filter(Boolean)
    .sort((left, right) => left.timestamp.localeCompare(right.timestamp));
  if (!bars.length || new Set(bars.map(bar => bar.timestamp)).size !== bars.length) {
    throw new Error(bars.length ? 'ENTRY_V2_YAHOO_CHART_DUPLICATE_PROVIDER_TIMESTAMP' : 'ENTRY_V2_YAHOO_CHART_NO_VALID_REGULAR_SESSION_BARS');
  }
  const series = Object.freeze({
    symbol: normalizedSymbol,
    code: String(universeEntry.code ?? normalizedSymbol.replace(/\.T$/i, '')),
    name: String(universeEntry.name ?? normalizedSymbol),
    sector: String(universeEntry.sector ?? '未分類'),
    market: universeEntry.market ?? null,
    bars: Object.freeze(bars),
    providerMeta: Object.freeze({
      exchangeName: response?.meta?.exchangeName ?? null,
      exchangeTimezoneName: response?.meta?.exchangeTimezoneName ?? null,
      dataGranularity: response?.meta?.dataGranularity ?? null,
      currency: response?.meta?.currency ?? null,
      instrumentType: response?.meta?.instrumentType ?? null,
    }),
    sourceQuality: Object.freeze({
      sourceTimestampCount: timestamps.length,
      acceptedRegularSessionBarCount: bars.length,
      droppedRowCount: timestamps.length - bars.length,
      zeroVolumeBarCount: bars.filter(bar => bar.volume === 0).length,
    }),
  });

  return Object.freeze({
    phase: ENTRY_V2_HISTORICAL_MARKET_POLICY.phase,
    status: 'ENTRY_V2_YAHOO_CHART_SERIES_READY',
    sourceClass: ENTRY_V2_HISTORICAL_MARKET_POLICY.sourceClass,
    datasetRole: ENTRY_V2_HISTORICAL_MARKET_POLICY.datasetRole,
    prospective: false,
    formalOos: false,
    retrievedAt: retrievedAtIso,
    queryRange,
    interval,
    requestedSymbol: normalizedSymbol,
    series,
    rawPayloadSha256: sha256(payload),
    methodology: Object.freeze({
      marketDataCollectedBeforeSelectorReplay: true,
      selectedSymbolsDidNotDetermineAcquisition: true,
      providerTimestampPreservedWithoutShift: true,
      yahooSparkPriceOnlyResponseRejectedForMissingOhlcv: true,
      providerBarsNeverInterpolatedOrFabricated: true,
      laterFetchedNeverRepresentedAsArchivedPit: true,
    }),
    safety: ENTRY_V2_HISTORICAL_MARKET_SAFETY,
  });
}

export function partitionHistoricalSeriesBySession({ series = [], startSessionDate, endSessionDate } = {}) {
  const start = validateSessionDate(startSessionDate, 'START_SESSION_DATE');
  const end = validateSessionDate(endSessionDate, 'END_SESSION_DATE');
  if (end < start) throw new Error('ENTRY_V2_HISTORICAL_MARKET_SESSION_RANGE_INVALID');
  const sessions = new Map();
  for (const item of series) {
    const grouped = new Map();
    for (const bar of item?.bars ?? []) {
      const sessionDate = validateSessionDate(bar?.sessionDate ?? jstParts(bar?.timestamp).sessionDate);
      if (!grouped.has(sessionDate)) grouped.set(sessionDate, []);
      grouped.get(sessionDate).push(bar);
    }
    const dates = [...grouped.keys()].sort();
    for (const sessionDate of dates) {
      if (sessionDate < start || sessionDate > end) continue;
      const previousSessionDate = dates.filter(date => date < sessionDate).at(-1) ?? null;
      const priorBars = previousSessionDate ? grouped.get(previousSessionDate) : null;
      const previousClose = priorBars?.at(-1)?.close ?? null;
      if (!sessions.has(sessionDate)) sessions.set(sessionDate, []);
      sessions.get(sessionDate).push(Object.freeze({
        symbol: item.symbol,
        code: item.code,
        name: item.name,
        sector: item.sector,
        market: item.market,
        previousClose: finite(previousClose) && Number(previousClose) > 0 ? Number(previousClose) : null,
        previousCloseSessionDate: previousSessionDate,
        bars: Object.freeze([...grouped.get(sessionDate)].sort((a, b) => a.timestamp.localeCompare(b.timestamp))),
        providerMeta: item.providerMeta,
        sourceQuality: item.sourceQuality,
      }));
    }
  }
  return new Map([...sessions].sort(([left], [right]) => left.localeCompare(right))
    .map(([sessionDate, rows]) => [sessionDate, Object.freeze(rows.sort((a, b) => a.symbol.localeCompare(b.symbol)))]));
}

export function entryV2HistoricalDecisionTimestamps(sessionDate) {
  const date = validateSessionDate(sessionDate);
  const values = [];
  const add = (startMinutes, endMinutes) => {
    for (let minute = startMinutes; minute <= endMinutes; minute += 5) {
      const hour = String(Math.floor(minute / 60)).padStart(2, '0');
      const mins = String(minute % 60).padStart(2, '0');
      values.push(new Date(`${date}T${hour}:${mins}:00+09:00`).toISOString());
    }
  };
  add(9 * 60, 11 * 60 + 30);
  add(12 * 60 + 30, 15 * 60 + 30);
  return Object.freeze(values);
}

function snapshotRow({ item, prefix, observedAt }) {
  if (!prefix.length || !(Number(item.previousClose) > 0)) return null;
  const latest = prefix.at(-1);
  const volume = prefix.reduce((sum, bar) => sum + Number(bar.volume ?? 0), 0);
  if (!(latest.close > 0) || !(volume > 0)) return null;
  return Object.freeze({
    symbol: item.symbol,
    sector: item.sector,
    market: item.market,
    price: latest.close,
    volume,
    changePct: (latest.close / Number(item.previousClose) - 1) * 100,
    scannedAt: observedAt,
  });
}

export function buildEntryV2HistoricalMarketSnapshots({
  sessionDate,
  sessionSeries = [],
  universeSymbolCount,
  minimumMarketwideSymbols = ENTRY_V2_HISTORICAL_MARKET_POLICY.minimumMarketwideSymbols,
  sourceLineage = {},
} = {}) {
  const date = validateSessionDate(sessionDate);
  if (date < ENTRY_V2_HISTORICAL_MARKET_POLICY.earliestLeakageSafeReplaySessionDate) {
    throw new Error('ENTRY_V2_HISTORICAL_MARKET_PRE_FROZEN_HISTORY_REPLAY_FORBIDDEN');
  }
  const totalUniverse = Number(universeSymbolCount);
  const minimum = Number(minimumMarketwideSymbols);
  if (!Number.isInteger(totalUniverse) || totalUniverse < 1 || !Number.isInteger(minimum) || minimum < 1) {
    throw new Error('ENTRY_V2_HISTORICAL_MARKET_UNIVERSE_COUNT_INVALID');
  }
  assertSafety(ENTRY_V2_HISTORICAL_MARKET_SAFETY, 'POLICY');
  const seen = new Set();
  for (const item of sessionSeries) {
    if (!item?.symbol || seen.has(item.symbol)) throw new Error('ENTRY_V2_HISTORICAL_MARKET_SESSION_SYMBOL_INVALID_OR_DUPLICATE');
    seen.add(item.symbol);
    if ((item?.bars ?? []).some(bar => jstParts(bar.timestamp).sessionDate !== date)) {
      throw new Error('ENTRY_V2_HISTORICAL_MARKET_CROSS_SESSION_BAR');
    }
  }
  const allPoints = [];
  for (const observedAt of entryV2HistoricalDecisionTimestamps(date)) {
    const rows = [];
    for (const item of sessionSeries) {
      const prefix = (item.bars ?? []).filter(bar => Date.parse(bar.timestamp) + 5 * 60_000 <= Date.parse(observedAt));
      const row = snapshotRow({ item, prefix, observedAt });
      if (row) rows.push(row);
    }
    rows.sort((left, right) => left.symbol.localeCompare(right.symbol));
    const symbolCount = rows.length;
    const stateHash = sha256(JSON.stringify(rows));
    const ready = symbolCount >= minimum;
    allPoints.push(Object.freeze({
      phase: ENTRY_V2_HISTORICAL_MARKET_POLICY.phase,
      status: ready ? 'ENTRY_V2_HISTORICAL_MARKET_SNAPSHOT_READY' : 'ENTRY_V2_HISTORICAL_MARKET_SNAPSHOT_BLOCKED',
      reason: ready ? null : 'HISTORICAL_UNIVERSE_COVERAGE_INSUFFICIENT',
      sourceClass: ENTRY_V2_HISTORICAL_MARKET_POLICY.sourceClass,
      datasetRole: 'DEVELOPMENT_ONLY',
      prospective: false,
      formalOos: false,
      observedAt,
      bucket: observedAt,
      sessionDate: date,
      symbolCount,
      universeSymbolCount: totalUniverse,
      universeCoverage: symbolCount / totalUniverse,
      minimumMarketwideSymbols: minimum,
      rows: Object.freeze(rows),
      stateHash,
      sourceLineage: Object.freeze({
        ...sourceLineage,
        sourceClass: ENTRY_V2_HISTORICAL_MARKET_POLICY.sourceClass,
        reconstructionFetchedAfterDecision: true,
        archivedPointInTimeCapture: false,
      }),
      methodology: Object.freeze({
        pointInTimeOnly: true,
        marketDataBeforeSelector: true,
        currentDynamic5mSelectorFixed: true,
        frozenP21EntryFixed: true,
        completedBarRule: ENTRY_V2_HISTORICAL_MARKET_POLICY.completedBarRule,
        providerTimestampPreservedWithoutShift: true,
        futureBarsUsed: false,
        missingBarsInterpolated: false,
      }),
      safety: ENTRY_V2_HISTORICAL_MARKET_SAFETY,
    }));
  }
  const readyPoints = allPoints.filter(point => point.status === 'ENTRY_V2_HISTORICAL_MARKET_SNAPSHOT_READY');
  const blockedPoints = allPoints.filter(point => point.status !== 'ENTRY_V2_HISTORICAL_MARKET_SNAPSHOT_READY');
  return Object.freeze({
    phase: ENTRY_V2_HISTORICAL_MARKET_POLICY.phase,
    sessionDate: date,
    pointCount: allPoints.length,
    readyPointCount: readyPoints.length,
    blockedPointCount: blockedPoints.length,
    minimumSymbolCount: Math.min(...allPoints.map(point => point.symbolCount)),
    maximumSymbolCount: Math.max(...allPoints.map(point => point.symbolCount)),
    averageSymbolCount: allPoints.reduce((sum, point) => sum + point.symbolCount, 0) / allPoints.length,
    points: Object.freeze(allPoints),
    readyPoints: Object.freeze(readyPoints),
    blockedPoints: Object.freeze(blockedPoints),
    blockedReasonDistribution: Object.freeze(blockedPoints.reduce((counts, point) => {
      counts[point.reason] = (counts[point.reason] ?? 0) + 1;
      return counts;
    }, {})),
    pitViolationCount: 0,
    status: 'ENTRY_V2_HISTORICAL_MARKET_SESSION_SNAPSHOTS_AUDITED',
    safety: ENTRY_V2_HISTORICAL_MARKET_SAFETY,
  });
}

const mapV1 = row => Object.freeze({
  symbol: row.symbol,
  sector: row.sector,
  currentPrice: row.currentPrice,
  sourceScannedAt: row.sourceScannedAt,
  opportunityScore: row.opportunityScore,
  turnoverYen: row.turnoverYen,
});

const mapV2 = row => Object.freeze({ ...mapV1(row), v2Score: row.v2Score, components: row.components });

function selectorInput(snapshot) {
  return Object.freeze({
    asOf: snapshot.observedAt,
    entries: Object.freeze(snapshot.rows.map(row => Object.freeze({
      symbol: row.symbol,
      sector: row.sector,
      market: row.market,
      status: 'analyzed',
      currentPrice: row.price,
      volume: row.volume,
      dailyChangePercent: row.changePct,
      scannedAt: snapshot.observedAt,
    }))),
  });
}

export function buildEntryV2HistoricalSelectorMeasurements({ snapshots = [] } = {}) {
  if (!Array.isArray(snapshots) || !snapshots.length) throw new Error('ENTRY_V2_HISTORICAL_SELECTOR_SNAPSHOTS_REQUIRED');
  const sessionDates = new Set(snapshots.map(snapshot => snapshot.sessionDate));
  if (sessionDates.size !== 1) throw new Error('ENTRY_V2_HISTORICAL_SELECTOR_ONE_SESSION_REQUIRED');
  if (snapshots.some(snapshot => snapshot.status !== 'ENTRY_V2_HISTORICAL_MARKET_SNAPSHOT_READY')) {
    throw new Error('ENTRY_V2_HISTORICAL_SELECTOR_READY_SNAPSHOTS_ONLY');
  }
  const inputs = [...snapshots].sort((a, b) => a.observedAt.localeCompare(b.observedAt)).map(selectorInput);
  const v1 = buildIntradayDynamicUniverseTimeline({ snapshots: inputs });
  const v2 = buildIntradayDynamicUniverseTimelineV2({ snapshots: inputs, priorSelections: [] });
  const v2ByAsOf = new Map(v2.points.map(point => [point.asOf, point]));
  const snapshotByAsOf = new Map(snapshots.map(snapshot => [snapshot.observedAt, snapshot]));
  const measurements = v1.points.map(point => {
    const snapshot = snapshotByAsOf.get(point.asOf);
    const pointV2 = v2ByAsOf.get(point.asOf);
    if (!snapshot || !pointV2) throw new Error('ENTRY_V2_HISTORICAL_SELECTOR_POINT_ALIGNMENT_FAILED');
    return Object.freeze({
      schemaVersion: 3,
      phase: '57.entry-quality-v2.historical-current-dynamic5m-measurement',
      status: 'MARKETWIDE_DYNAMIC_5M_MEASUREMENT_READY',
      sourceClass: ENTRY_V2_HISTORICAL_MARKET_POLICY.sourceClass,
      datasetRole: 'DEVELOPMENT_ONLY',
      prospective: false,
      formalOos: false,
      observedAt: point.asOf,
      inputSymbols: snapshot.symbolCount,
      selectedSymbols: point.rawUniverse.length,
      selectedV2Symbols: pointV2.rawUniverse.length,
      policy: v1.policy,
      methodology: Object.freeze({
        ...v1.methodology,
        marketDataCollectedBeforeSelection: true,
        laterFetchedHistoricalReconstruction: true,
        currentDynamic5mSelectorFixed: true,
        oldSelectorMembershipReused: false,
      }),
      safety: v1.safety,
      selected: Object.freeze(point.rawUniverse.map(mapV1)),
      dynamic5mV2: Object.freeze({
        candidateId: v2.candidateId,
        policy: v2.policy,
        methodology: v2.methodology,
        safety: v2.safety,
      }),
      selectedV2: Object.freeze(pointV2.rawUniverse.map(mapV2)),
      rawSnapshotSha256: sha256(JSON.stringify(snapshot)),
    });
  });
  return Object.freeze({
    sessionDate: [...sessionDates][0],
    measurementCount: measurements.length,
    measurements: Object.freeze(measurements),
    v1SelectedMembershipCount: measurements.reduce((sum, row) => sum + row.selected.length, 0),
    v2SelectedMembershipCount: measurements.reduce((sum, row) => sum + row.selectedV2.length, 0),
    candidateId: PHASE57_INTRADAY_UNIVERSE_POLICY.candidateId,
    v2CandidateId: PHASE57_INTRADAY_UNIVERSE_V2_POLICY.candidateId,
    status: 'ENTRY_V2_HISTORICAL_CURRENT_DYNAMIC5M_MEASUREMENTS_READY',
  });
}

/**
 * Build only the market context that the reconstructed marketwide snapshot can
 * prove at the decision timestamp. Benchmark-index fields intentionally remain
 * null until their own point-in-time archives are connected.
 */
export function buildEntryV2HistoricalMarketContext({ snapshot, sector = null } = {}) {
  if (snapshot?.status !== 'ENTRY_V2_HISTORICAL_MARKET_SNAPSHOT_READY'
    || snapshot?.methodology?.pointInTimeOnly !== true
    || snapshot?.methodology?.futureBarsUsed !== false
    || !Array.isArray(snapshot?.rows) || !snapshot.rows.length) {
    throw new Error('ENTRY_V2_HISTORICAL_MARKET_CONTEXT_READY_PIT_SNAPSHOT_REQUIRED');
  }
  const returns = snapshot.rows.map(row => Number(row?.changePct)).filter(Number.isFinite);
  if (returns.length !== snapshot.rows.length) {
    throw new Error('ENTRY_V2_HISTORICAL_MARKET_CONTEXT_RETURN_COVERAGE_INCOMPLETE');
  }
  const requestedSector = sector == null ? null : String(sector);
  const sectorReturns = requestedSector === null
    ? []
    : snapshot.rows.filter(row => String(row?.sector ?? '') === requestedSector)
      .map(row => Number(row.changePct)).filter(Number.isFinite);
  const marketMean = mean(returns);
  const sectorMean = mean(sectorReturns);
  return Object.freeze({
    source: 'ENTRY_V2_HISTORICAL_MARKETWIDE_SNAPSHOT',
    observedAt: snapshot.observedAt,
    sourceClass: snapshot.sourceClass,
    prospective: false,
    formalOos: false,
    marketSymbolCount: snapshot.symbolCount,
    universeSymbolCount: snapshot.universeSymbolCount,
    universeCoverage: snapshot.universeCoverage,
    breadthUpRatio: returns.filter(value => value > 0).length / returns.length,
    breadthDownRatio: returns.filter(value => value < 0).length / returns.length,
    breadthUnchangedRatio: returns.filter(value => value === 0).length / returns.length,
    equalWeightMeanReturnPct: marketMean,
    equalWeightMedianReturnPct: median(returns),
    crossSectionalReturnVolatilityPct: standardDeviation(returns),
    requestedSector,
    sectorMemberCount: sectorReturns.length,
    sectorEqualWeightMeanReturnPct: sectorMean,
    sectorRelativeStrengthPct: sectorMean === null ? null : sectorMean - marketMean,
    topixReturnPct: null,
    nikkeiReturnPct: null,
    benchmarkIndexContextAvailable: false,
    marketBreadthContextAvailable: true,
    missingValuesFabricated: false,
    rawSnapshotSha256: sha256(JSON.stringify(snapshot)),
    sourceLineage: snapshot.sourceLineage,
  });
}

export function buildEntryV2HistoricalSessionBarArchive({
  sessionDate,
  sessionSeries = [],
  requiredSymbols = [],
  retrievedAt,
  sourceArtifact,
  sourceArtifactSha256,
  sourceManifestSha256 = null,
} = {}) {
  const date = validateSessionDate(sessionDate);
  const required = [...new Set(requiredSymbols.map(symbolOf).filter(Boolean))].sort();
  if (!required.length) throw new Error('ENTRY_V2_HISTORICAL_BAR_ARCHIVE_REQUIRED_SYMBOLS_EMPTY');
  const index = new Map(sessionSeries.map(item => [symbolOf(item.symbol), item]));
  const sessionBarsBySymbol = {};
  const missingSymbols = [];
  for (const symbol of required) {
    const bars = index.get(symbol)?.bars;
    if (!Array.isArray(bars) || !bars.length) missingSymbols.push(symbol);
    else sessionBarsBySymbol[symbol] = bars.map(({ timestamp, open, high, low, close, volume }) => (
      Object.freeze({ timestamp, open, high, low, close, volume })
    ));
  }
  const retrievedAtIso = new Date(retrievedAt ?? '').toISOString();
  const artifactSha = String(sourceArtifactSha256 ?? '').toLowerCase();
  if (!String(sourceArtifact ?? '').trim() || !/^[0-9a-f]{64}$/.test(artifactSha)) {
    throw new Error('ENTRY_V2_HISTORICAL_BAR_ARCHIVE_LINEAGE_INVALID');
  }
  return Object.freeze({
    schemaVersion: 2,
    phase: '57.entry-quality-v2.historical-market-session-bars',
    status: missingSymbols.length ? 'ENTRY_V2_HISTORICAL_SESSION_BAR_ARCHIVE_INCOMPLETE' : 'ENTRY_V2_HISTORICAL_SESSION_BAR_ARCHIVE_READY',
    sourceClass: ENTRY_V2_HISTORICAL_MARKET_POLICY.sourceClass,
    datasetRole: 'DEVELOPMENT_ONLY',
    prospective: false,
    formalOos: false,
    sessionDate: date,
    requiredSymbolCount: required.length,
    retainedSymbolCount: Object.keys(sessionBarsBySymbol).length,
    missingSymbols: Object.freeze(missingSymbols),
    sessionBarsBySymbol: Object.freeze(sessionBarsBySymbol),
    sourceLineage: Object.freeze({
      sourceClass: ENTRY_V2_HISTORICAL_MARKET_POLICY.sourceClass,
      sourceArtifact: String(sourceArtifact),
      sourceArtifactSha256: artifactSha,
      sourceArtifactHashScope: 'NORMALIZED_SESSION_SHARDS_AND_FETCH_MANIFEST',
      sourceManifestSha256,
      retrievedAt: retrievedAtIso,
      sessionDate: date,
      provider: ENTRY_V2_HISTORICAL_MARKET_POLICY.provider,
      sourceRef: 'ZERO_BASED_MARKET_FIRST_YAHOO_HISTORICAL_RECONSTRUCTION',
      archivedPointInTimeCapture: false,
      reconstructionFetchedAfterDecision: true,
    }),
    methodology: Object.freeze({
      marketDataAcquiredBeforeSelectorReplay: true,
      selectedSymbolsDidNotDetermineMarketAcquisition: true,
      missingBarsNeverInterpolatedOrFabricated: true,
      completedBarRule: ENTRY_V2_HISTORICAL_MARKET_POLICY.completedBarRule,
    }),
    safety: ENTRY_V2_HISTORICAL_MARKET_SAFETY,
  });
}

export default {
  ENTRY_V2_HISTORICAL_MARKET_POLICY,
  ENTRY_V2_HISTORICAL_MARKET_SAFETY,
  buildYahooChartUrl,
  normalizeYahooChartPayload,
  partitionHistoricalSeriesBySession,
  entryV2HistoricalDecisionTimestamps,
  buildEntryV2HistoricalMarketSnapshots,
  buildEntryV2HistoricalSelectorMeasurements,
  buildEntryV2HistoricalMarketContext,
  buildEntryV2HistoricalSessionBarArchive,
};
