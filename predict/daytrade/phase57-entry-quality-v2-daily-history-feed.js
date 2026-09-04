import { createHash } from 'node:crypto';

export const ENTRY_V2_DAILY_HISTORY_POLICY = Object.freeze({
  mode: 'ENTRY_V2_DAILY_HISTORY_RESEARCH_ONLY',
  acceptedSources: Object.freeze(['YAHOO_CHART']),
  priorSessionOnly: true,
  retentionTargetBars: 250,
  useAdjustedCloseAsFeature: false,
  automaticPromotionAllowed: false,
});

function sym(value) {
  return String(value ?? '').trim().toUpperCase();
}

function jstSessionDate(value) {
  const ms = Date.parse(String(value ?? ''));
  if (!Number.isFinite(ms)) throw new Error('ENTRY_V2_DAILY_FEED_INVALID_AS_OF');
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date(ms));
  const map = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${map.year}-${map.month}-${map.day}`;
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  }
  return value;
}

function fingerprint(value) {
  return createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');
}

function validateSessionDate(value) {
  const sessionDate = String(value ?? '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)) {
    throw new Error('ENTRY_V2_DAILY_FEED_INVALID_SESSION_DATE');
  }
  return sessionDate;
}

function canonicalTimestampForSession(sessionDate) {
  // 15:00 JST on the named session date. The strict PIT decision is made on a later
  // session, so this timestamp is lineage metadata only and never makes a same-day
  // daily bar eligible intraday.
  return new Date(`${sessionDate}T15:00:00+09:00`).toISOString();
}

function normalizeRecord(record, expectedSymbol) {
  const symbol = sym(record?.symbol);
  if (!symbol || symbol !== expectedSymbol) throw new Error('ENTRY_V2_DAILY_FEED_SYMBOL_MISMATCH');
  if (record?.kind !== 'OHLCV') throw new Error('ENTRY_V2_DAILY_FEED_OHLCV_REQUIRED');
  if (!ENTRY_V2_DAILY_HISTORY_POLICY.acceptedSources.includes(String(record?.source ?? ''))) {
    throw new Error('ENTRY_V2_DAILY_FEED_SOURCE_NOT_ALLOWED');
  }

  const sessionDate = validateSessionDate(record?.sessionDate);
  const open = Number(record?.open);
  const high = Number(record?.high);
  const low = Number(record?.low);
  const close = Number(record?.close);
  const volume = Number(record?.volume ?? 0);
  const adjustedClose = Number(record?.adjustedClose);

  if (![open, high, low, close, volume].every(Number.isFinite)) {
    throw new Error('ENTRY_V2_DAILY_FEED_INVALID_OHLCV');
  }
  if (!(open > 0) || !(close > 0) || high < low || volume < 0) {
    throw new Error('ENTRY_V2_DAILY_FEED_INVALID_OHLCV');
  }

  return Object.freeze({
    timestamp: canonicalTimestampForSession(sessionDate),
    sessionDate,
    open,
    high,
    low,
    close,
    volume,
    adjustedClose: Number.isFinite(adjustedClose) && adjustedClose > 0 ? adjustedClose : null,
    source: String(record.source),
    sourceKind: String(record.kind),
    currency: String(record.currency ?? 'JPY'),
  });
}

/**
 * Convert persisted Phase50/Phase45 daily OHLCV records into the strict Entry-v2
 * daily prefix consumed by the PIT builder. The feed is fail-closed: any same-session
 * or future session record blocks the entire feed instead of being silently filtered.
 *
 * Raw OHLCV is retained for Phase 1. adjustedClose is carried only as lineage/audit
 * metadata and is explicitly not used as a feature here because mixing adjusted close
 * with unadjusted OHLC would create an inconsistent price basis around corporate actions.
 */
export function buildEntryV2PriorDailyHistoryFeed({
  symbol,
  asOf,
  records = [],
  retentionBars = ENTRY_V2_DAILY_HISTORY_POLICY.retentionTargetBars,
} = {}) {
  const expectedSymbol = sym(symbol);
  if (!expectedSymbol) throw new Error('ENTRY_V2_DAILY_FEED_SYMBOL_REQUIRED');
  if (!Array.isArray(records) || !records.length) throw new Error('ENTRY_V2_DAILY_FEED_RECORDS_REQUIRED');

  const decisionSessionDate = jstSessionDate(asOf);
  const limit = Number(retentionBars);
  if (!Number.isInteger(limit) || limit <= 0) throw new Error('ENTRY_V2_DAILY_FEED_INVALID_RETENTION');

  const normalized = records
    .map(record => normalizeRecord(record, expectedSymbol))
    .sort((a, b) => a.sessionDate.localeCompare(b.sessionDate));

  for (let i = 0; i < normalized.length; i += 1) {
    if (normalized[i].sessionDate >= decisionSessionDate) {
      throw new Error('ENTRY_V2_DAILY_FEED_NOT_PRIOR_SESSION');
    }
    if (i > 0 && normalized[i - 1].sessionDate === normalized[i].sessionDate) {
      throw new Error('ENTRY_V2_DAILY_FEED_DUPLICATE_SESSION');
    }
  }

  const bars = Object.freeze(normalized.slice(-limit).map(row => Object.freeze({
    timestamp: row.timestamp,
    open: row.open,
    high: row.high,
    low: row.low,
    close: row.close,
    volume: row.volume,
  })));

  const lineage = Object.freeze({
    symbol: expectedSymbol,
    decisionSessionDate,
    source: normalized[0].source,
    sourceKind: normalized[0].sourceKind,
    availablePriorSessions: normalized.length,
    retainedSessions: bars.length,
    firstRetainedSessionDate: normalized.slice(-limit)[0]?.sessionDate ?? null,
    lastRetainedSessionDate: normalized.at(-1)?.sessionDate ?? null,
    rawOhlcvFeatureBasis: true,
    adjustedCloseFeatureBasis: false,
    adjustedCloseAuditAvailable: normalized.some(row => row.adjustedClose !== null),
    pointInTimeStrict: true,
    sameSessionDailyBarRejected: true,
  });

  return Object.freeze({
    policy: ENTRY_V2_DAILY_HISTORY_POLICY,
    symbol: expectedSymbol,
    asOf: new Date(asOf).toISOString(),
    bars,
    lineage,
    sourceFingerprintSha256: fingerprint(normalized),
    retainedBarsFingerprintSha256: fingerprint(bars),
    status: 'ENTRY_V2_PRIOR_DAILY_HISTORY_READY',
  });
}

export default {
  ENTRY_V2_DAILY_HISTORY_POLICY,
  buildEntryV2PriorDailyHistoryFeed,
};
