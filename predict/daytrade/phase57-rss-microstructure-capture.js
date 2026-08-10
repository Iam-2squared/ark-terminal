export const PHASE57_P22_2_SAFETY = Object.freeze({
  mode: 'PHASE57_RSS_MICROSTRUCTURE_CAPTURE_READ_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  humanApprovalRequired: true,
});

export const P22_2_ALLOWED_RSS_FUNCTIONS = Object.freeze(['RssMarket', 'RssTickList']);
export const P22_2_MAX_RSS_TICK_ROWS = 300;

const ORDER_FUNCTION_PATTERN = /^Rss(?:StockOrder|MarginOpenOrder|MarginCloseOrder|ModifyOrder|CancelOrder|Future|Option)/i;
const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const numberOrNull = value => finite(value) ? Number(value) : null;

export function assertReadOnlyRssFunction(name) {
  const value = String(name ?? '').trim();
  if (ORDER_FUNCTION_PATTERN.test(value)) throw new Error(`RSS order function is forbidden in P22.2: ${value}`);
  if (!P22_2_ALLOWED_RSS_FUNCTIONS.includes(value)) throw new Error(`RSS function is not whitelisted for P22.2: ${value || '<empty>'}`);
  return value;
}

function assertSessionDate(sessionDate) {
  const value = String(sessionDate ?? '').trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new TypeError('sessionDate must be YYYY-MM-DD');
  const parsed = Date.parse(`${value}T00:00:00+09:00`);
  if (!Number.isFinite(parsed)) throw new TypeError('invalid sessionDate');
  return value;
}

function jstDate(iso) {
  const parsed = Date.parse(iso ?? '');
  if (!Number.isFinite(parsed)) return null;
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(parsed));
  const fields = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${fields.year}-${fields.month}-${fields.day}`;
}

function normalizeCapturedAt(capturedAt, sessionDate) {
  const parsed = Date.parse(capturedAt ?? '');
  if (!Number.isFinite(parsed)) throw new TypeError('capturedAt must be a valid absolute timestamp');
  const iso = new Date(parsed).toISOString();
  if (jstDate(iso) !== sessionDate) throw new Error(`capturedAt is outside sessionDate ${sessionDate} in JST`);
  return iso;
}

function excelFractionToTime(value) {
  const fraction = Number(value);
  if (!Number.isFinite(fraction) || fraction < 0 || fraction >= 1) return null;
  const totalMs = Math.round(fraction * 86400000);
  const hours = Math.floor(totalMs / 3600000) % 24;
  const minutes = Math.floor((totalMs % 3600000) / 60000);
  const seconds = Math.floor((totalMs % 60000) / 1000);
  const milliseconds = totalMs % 1000;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(milliseconds).padStart(3, '0')}`;
}

export function normalizeRssTimeOfDay(value, { sessionDate, capturedAt, field = 'RSS time' } = {}) {
  const session = assertSessionDate(sessionDate);
  const captureIso = normalizeCapturedAt(capturedAt, session);
  if (value === null || value === undefined || value === '') return null;

  let iso = null;
  if (typeof value === 'number') {
    const time = excelFractionToTime(value);
    if (!time) throw new TypeError(`${field} numeric value must be an Excel time fraction in [0,1)`);
    iso = new Date(Date.parse(`${session}T${time}+09:00`)).toISOString();
  } else {
    const text = String(value).trim();
    const timeMatch = text.match(/^(\d{1,2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?$/);
    if (timeMatch) {
      const hh = Number(timeMatch[1]);
      const mm = Number(timeMatch[2]);
      const ss = Number(timeMatch[3] ?? 0);
      const ms = Number(String(timeMatch[4] ?? '0').padEnd(3, '0'));
      if (hh > 23 || mm > 59 || ss > 59) throw new TypeError(`${field} has invalid time-of-day`);
      const time = `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}.${String(ms).padStart(3, '0')}`;
      iso = new Date(Date.parse(`${session}T${time}+09:00`)).toISOString();
    } else {
      const parsed = Date.parse(text);
      if (!Number.isFinite(parsed)) throw new TypeError(`${field} must be time-of-day or absolute timestamp`);
      iso = new Date(parsed).toISOString();
      if (jstDate(iso) !== session) throw new Error(`${field} is outside sessionDate ${session} in JST`);
    }
  }

  if (Date.parse(iso) > Date.parse(captureIso)) throw new Error(`${field} is in the future relative to capturedAt`);
  return iso;
}

function requireFieldMap(fieldMap, requiredKeys) {
  if (!fieldMap || typeof fieldMap !== 'object' || Array.isArray(fieldMap)) throw new TypeError('fieldMap must be an explicit configuration object');
  for (const key of requiredKeys) {
    if (typeof fieldMap[key] !== 'string' || !fieldMap[key].trim()) throw new Error(`fieldMap.${key} is required`);
  }
  return fieldMap;
}

function mapped(raw, fieldMap, canonical) {
  const sourceKey = fieldMap[canonical];
  if (!sourceKey) return null;
  return raw?.[sourceKey] ?? null;
}

function safeSymbol(symbol) {
  const value = String(symbol ?? '').trim();
  if (!value) throw new TypeError('symbol is required');
  return value;
}

function quoteSideTimestamp(raw, fieldMap, side, sessionDate, capturedAt) {
  const detailedKey = side === 'ask' ? 'bestAskDetailedTime' : 'bestBidDetailedTime';
  const basicKey = side === 'ask' ? 'bestAskTime' : 'bestBidTime';
  const value = mapped(raw, fieldMap, detailedKey) ?? mapped(raw, fieldMap, basicKey);
  return normalizeRssTimeOfDay(value, { sessionDate, capturedAt, field: detailedKey });
}

function latestIso(values) {
  const valid = values.filter(Boolean);
  if (!valid.length) return null;
  return valid.slice().sort((a, b) => Date.parse(a) - Date.parse(b)).at(-1);
}

export function captureConfiguredRssMarketSnapshot({
  symbol,
  sessionDate,
  capturedAt,
  sourceFunction = 'RssMarket',
  raw = {},
  fieldMap,
} = {}) {
  assertReadOnlyRssFunction(sourceFunction);
  if (sourceFunction !== 'RssMarket') throw new Error('captureConfiguredRssMarketSnapshot requires RssMarket');
  const session = assertSessionDate(sessionDate);
  const captureIso = normalizeCapturedAt(capturedAt, session);
  requireFieldMap(fieldMap, ['bestAsk', 'bestBid', 'bestAskSize', 'bestBidSize']);
  const quote = {
    bestAsk: numberOrNull(mapped(raw, fieldMap, 'bestAsk')),
    bestBid: numberOrNull(mapped(raw, fieldMap, 'bestBid')),
    askSize: numberOrNull(mapped(raw, fieldMap, 'bestAskSize')),
    bidSize: numberOrNull(mapped(raw, fieldMap, 'bestBidSize')),
    overSize: numberOrNull(mapped(raw, fieldMap, 'overSize')),
    underSize: numberOrNull(mapped(raw, fieldMap, 'underSize')),
  };
  if (!finite(quote.bestAsk) || !finite(quote.bestBid) || quote.bestAsk <= 0 || quote.bestBid <= 0) throw new Error('RssMarket best bid/ask must be finite positive values');
  if (quote.bestAsk < quote.bestBid) throw new Error('crossed RssMarket quote rejected');

  const askTimestamp = quoteSideTimestamp(raw, fieldMap, 'ask', session, captureIso);
  const bidTimestamp = quoteSideTimestamp(raw, fieldMap, 'bid', session, captureIso);
  const timestamp = latestIso([askTimestamp, bidTimestamp]) ?? captureIso;
  for (let level = 1; level <= 10; level += 1) {
    quote[`askPrice${level}`] = numberOrNull(mapped(raw, fieldMap, `askPrice${level}`));
    quote[`bidPrice${level}`] = numberOrNull(mapped(raw, fieldMap, `bidPrice${level}`));
    quote[`askSize${level}`] = numberOrNull(mapped(raw, fieldMap, `askSize${level}`));
    quote[`bidSize${level}`] = numberOrNull(mapped(raw, fieldMap, `bidSize${level}`));
  }

  return Object.freeze({
    phase: '57.p22.2',
    type: 'RSS_MARKET_MICROSTRUCTURE_SNAPSHOT',
    symbol: safeSymbol(symbol),
    sessionDate: session,
    capturedAt: captureIso,
    timestamp,
    bestAskDetailedTimestamp: askTimestamp,
    bestBidDetailedTimestamp: bidTimestamp,
    ...quote,
    sourceFunction: 'RssMarket',
    sourceMode: 'MARKETSPEED_II_RSS_READ_ONLY',
    fieldMapConfigured: true,
    excelReadOnly: true,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    transmitted: false,
    safety: PHASE57_P22_2_SAFETY,
  });
}

function normalizeTickRaw(row, fieldMap, sessionDate, capturedAt, sourceIndex) {
  const time = mapped(row, fieldMap, 'time');
  const timestamp = normalizeRssTimeOfDay(time, { sessionDate, capturedAt, field: `RssTickList[${sourceIndex}].time` });
  const volume = numberOrNull(mapped(row, fieldMap, 'volume'));
  const price = numberOrNull(mapped(row, fieldMap, 'price'));
  if (!timestamp || !finite(price) || price <= 0 || !finite(volume) || volume < 0) throw new Error(`invalid RssTickList row at index ${sourceIndex}`);
  return Object.freeze({ timestamp, price, volume, sourceIndex });
}

function tupleKey(tick) {
  return `${tick.timestamp}|${tick.price}|${tick.volume}`;
}

function canonicalPreviousWindow(previousWindow, sessionDate, capturedAt) {
  return (Array.isArray(previousWindow) ? previousWindow : []).map((tick, index) => {
    const timestamp = normalizeRssTimeOfDay(tick?.timestamp ?? tick?.time, {
      sessionDate,
      capturedAt,
      field: `previousWindow[${index}].timestamp`,
    });
    const price = numberOrNull(tick?.price ?? tick?.['約定値']);
    const volume = numberOrNull(tick?.volume ?? tick?.size ?? tick?.['出来高']);
    if (!timestamp || !finite(price) || price <= 0 || !finite(volume) || volume < 0) throw new Error(`invalid previousWindow row at index ${index}`);
    return Object.freeze({ timestamp, price, volume, sourceIndex: tick?.sourceIndex ?? index });
  }).sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp) || a.sourceIndex - b.sourceIndex);
}

export function longestRollingWindowOverlap(previousWindow = [], currentWindow = []) {
  const previous = Array.isArray(previousWindow) ? previousWindow : [];
  const current = Array.isArray(currentWindow) ? currentWindow : [];
  const limit = Math.min(previous.length, current.length);
  for (let length = limit; length > 0; length -= 1) {
    let matches = true;
    const previousStart = previous.length - length;
    for (let offset = 0; offset < length; offset += 1) {
      if (tupleKey(previous[previousStart + offset]) !== tupleKey(current[offset])) {
        matches = false;
        break;
      }
    }
    if (matches) return length;
  }
  return 0;
}

function duplicateMultiplicity(window) {
  const counts = new Map();
  for (const tick of window) counts.set(tupleKey(tick), (counts.get(tupleKey(tick)) || 0) + 1);
  return [...counts.values()].filter(count => count > 1).reduce((sum, count) => sum + count, 0);
}

export function ingestConfiguredRssTickListWindow({
  symbol,
  sessionDate,
  capturedAt,
  sourceFunction = 'RssTickList',
  rawRows = [],
  fieldMap,
  tickOrder,
  previousWindow = [],
} = {}) {
  assertReadOnlyRssFunction(sourceFunction);
  if (sourceFunction !== 'RssTickList') throw new Error('ingestConfiguredRssTickListWindow requires RssTickList');
  const session = assertSessionDate(sessionDate);
  const captureIso = normalizeCapturedAt(capturedAt, session);
  requireFieldMap(fieldMap, ['time', 'volume', 'price']);
  if (!['ASC', 'DESC'].includes(tickOrder)) throw new Error("tickOrder must be explicitly configured as 'ASC' or 'DESC'");
  if (!Array.isArray(rawRows)) throw new TypeError('rawRows must be an array');
  if (rawRows.length > P22_2_MAX_RSS_TICK_ROWS) throw new Error(`RssTickList cannot exceed ${P22_2_MAX_RSS_TICK_ROWS} rows`);

  const inSourceOrder = rawRows.map((row, index) => normalizeTickRaw(row, fieldMap, session, captureIso, index));
  const current = (tickOrder === 'DESC' ? inSourceOrder.slice().reverse() : inSourceOrder.slice())
    .map((tick, chronologicalIndex) => Object.freeze({ ...tick, chronologicalIndex }));
  for (let index = 1; index < current.length; index += 1) {
    if (Date.parse(current[index].timestamp) < Date.parse(current[index - 1].timestamp)) throw new Error(`tickOrder ${tickOrder} conflicts with RssTickList timestamps`);
  }

  const previous = canonicalPreviousWindow(previousWindow, session, captureIso);
  const overlapLength = longestRollingWindowOverlap(previous, current);
  const fullWindowAmbiguous = previous.length === P22_2_MAX_RSS_TICK_ROWS
    && current.length === P22_2_MAX_RSS_TICK_ROWS
    && overlapLength === current.length
    && previous.length > 0;
  const captureId = `${safeSymbol(symbol)}|${session}|${captureIso}|RssTickList`;
  const emitted = fullWindowAmbiguous ? [] : current.slice(overlapLength).map((tick, index) => Object.freeze({
    timestamp: tick.timestamp,
    price: tick.price,
    volume: tick.volume,
    size: tick.volume,
    captureId,
    tickOrdinalWithinCapture: overlapLength + index,
    sourceMode: 'MARKETSPEED_II_RSS_READ_ONLY',
    sourceFunction: 'RssTickList',
  }));

  return Object.freeze({
    phase: '57.p22.2',
    type: 'RSS_TICKLIST_MICROSTRUCTURE_WINDOW',
    symbol: safeSymbol(symbol),
    sessionDate: session,
    capturedAt: captureIso,
    tickOrder,
    window: Object.freeze(current.map(tick => Object.freeze({ timestamp: tick.timestamp, price: tick.price, volume: tick.volume, size: tick.volume }))),
    previousWindowSize: previous.length,
    currentWindowSize: current.length,
    overlapLength,
    newTicks: Object.freeze(emitted),
    newTickCount: emitted.length,
    duplicateTupleOccurrencesPreserved: duplicateMultiplicity(current),
    continuityStatus: fullWindowAmbiguous ? 'AMBIGUOUS_FULL_300_ROW_WINDOW_NO_SEQUENCE' : 'ROLLING_WINDOW_OVERLAP_RECONCILED',
    replayEligible: !fullWindowAmbiguous,
    ambiguityReason: fullWindowAmbiguous ? 'RssTickList exposes no sequence id; identical full 300-row windows cannot prove whether equal-valued prints rolled over' : null,
    sourceFunction: 'RssTickList',
    sourceMode: 'MARKETSPEED_II_RSS_READ_ONLY',
    officialNativeAggressorSideAvailable: false,
    fieldMapConfigured: true,
    excelReadOnly: true,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    transmitted: false,
    safety: PHASE57_P22_2_SAFETY,
  });
}

export function buildConfiguredMicrostructureCaptureBundle({ market, ticks } = {}) {
  if (!market || market.type !== 'RSS_MARKET_MICROSTRUCTURE_SNAPSHOT') throw new TypeError('market capture is required');
  if (!ticks || ticks.type !== 'RSS_TICKLIST_MICROSTRUCTURE_WINDOW') throw new TypeError('tick capture is required');
  if (market.symbol !== ticks.symbol || market.sessionDate !== ticks.sessionDate) throw new Error('market/tick capture symbol-session mismatch');
  if (Date.parse(market.capturedAt) !== Date.parse(ticks.capturedAt)) throw new Error('market/tick capture capturedAt mismatch');
  return Object.freeze({
    phase: '57.p22.2',
    status: ticks.replayEligible ? 'RSS_MICROSTRUCTURE_CAPTURE_READY' : 'RSS_MICROSTRUCTURE_CAPTURE_REVIEW_REQUIRED',
    symbol: market.symbol,
    sessionDate: market.sessionDate,
    capturedAt: market.capturedAt,
    market,
    ticks,
    intelligenceInput: Object.freeze({
      snapshot: market,
      ticks: ticks.newTicks,
      asOf: market.capturedAt,
    }),
    persistenceMode: 'RESEARCH_EVENT_ONLY',
    excelReadOnly: true,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    paperTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    safety: PHASE57_P22_2_SAFETY,
  });
}

export default {
  assertReadOnlyRssFunction,
  normalizeRssTimeOfDay,
  captureConfiguredRssMarketSnapshot,
  longestRollingWindowOverlap,
  ingestConfiguredRssTickListWindow,
  buildConfiguredMicrostructureCaptureBundle,
};
