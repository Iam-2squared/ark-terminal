export const PHASE57_P22_3_SAFETY = Object.freeze({
  mode: 'PHASE57_RSS_MICROSTRUCTURE_DURABILITY_READ_ONLY',
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

export const P22_3_DURABLE_EVENT_TYPES = Object.freeze([
  'RSS_MICROSTRUCTURE_CAPTURE_META',
  'RSS_MARKET_SNAPSHOT_EVENT',
  'RSS_TICK_EVENT',
]);

const READ_ONLY_MODE = 'MARKETSPEED_II_RSS_READ_ONLY';
const SAFETY_FALSE_KEYS = Object.freeze([
  'executionAllowed',
  'brokerWriteAllowed',
  'excelOrderWriteAllowed',
  'rssOrderFunctionAllowed',
  'liveTradingAllowed',
  'paperTradingAllowed',
  'automaticPromotionAllowed',
  'productionUpdateAllowed',
]);

function parseIso(value, label) {
  const parsed = Date.parse(value ?? '');
  if (!Number.isFinite(parsed)) throw new TypeError(`${label} must be a valid absolute timestamp`);
  return new Date(parsed).toISOString();
}

function safeText(value, label) {
  const text = String(value ?? '').trim();
  if (!text) throw new TypeError(`${label} is required`);
  return text;
}

function finiteNonNegative(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : fallback;
}

function finitePositive(value, label) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) throw new TypeError(`${label} must be a finite positive number`);
  return number;
}

function jstDate(iso) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(parseIso(iso, 'timestamp')));
  const fields = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${fields.year}-${fields.month}-${fields.day}`;
}

function jstMinuteOfDay(iso) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Tokyo', hour12: false, hour: '2-digit', minute: '2-digit',
  }).formatToParts(new Date(parseIso(iso, 'timestamp')));
  const fields = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return Number(fields.hour) * 60 + Number(fields.minute);
}

function parseClock(text, label) {
  const match = String(text ?? '').match(/^(\d{2}):(\d{2})$/);
  if (!match) throw new TypeError(`${label} must be HH:MM`);
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  if (hour > 23 || minute > 59) throw new TypeError(`${label} must be a valid HH:MM`);
  return hour * 60 + minute;
}

export function normalizeActiveWindowsJst(activeWindowsJst = null) {
  if (activeWindowsJst === null || activeWindowsJst === undefined) return null;
  if (!Array.isArray(activeWindowsJst)) throw new TypeError('activeWindowsJst must be an array or null');
  const windows = activeWindowsJst.map((window, index) => {
    if (!window || typeof window !== 'object' || Array.isArray(window)) throw new TypeError(`activeWindowsJst[${index}] must be an object`);
    const startMinute = parseClock(window.start, `activeWindowsJst[${index}].start`);
    const endMinute = parseClock(window.end, `activeWindowsJst[${index}].end`);
    if (endMinute <= startMinute) throw new Error(`activeWindowsJst[${index}] end must be after start on the same JST date`);
    return Object.freeze({
      index,
      label: String(window.label ?? `window-${index + 1}`),
      start: window.start,
      end: window.end,
      startMinute,
      endMinute,
    });
  }).sort((a, b) => a.startMinute - b.startMinute);
  for (let index = 1; index < windows.length; index += 1) {
    if (windows[index].startMinute < windows[index - 1].endMinute) throw new Error('activeWindowsJst windows must not overlap');
  }
  return Object.freeze(windows);
}

function activeWindowIndex(iso, activeWindows) {
  if (!activeWindows) return 0;
  const minute = jstMinuteOfDay(iso);
  return activeWindows.findIndex(window => minute >= window.startMinute && minute < window.endMinute);
}

function assertBundleSafety(bundle) {
  if (!bundle || typeof bundle !== 'object') throw new TypeError('P22.2 capture bundle is required');
  if (!bundle.market || bundle.market.type !== 'RSS_MARKET_MICROSTRUCTURE_SNAPSHOT') throw new TypeError('P22.2 market snapshot is required');
  if (!bundle.ticks || bundle.ticks.type !== 'RSS_TICKLIST_MICROSTRUCTURE_WINDOW') throw new TypeError('P22.2 tick window is required');
  if (bundle.market.sourceMode !== READ_ONLY_MODE || bundle.ticks.sourceMode !== READ_ONLY_MODE) throw new Error('P22.3 accepts only MARKETSPEED II RSS READ ONLY captures');
  if (bundle.market.sourceFunction !== 'RssMarket' || bundle.ticks.sourceFunction !== 'RssTickList') throw new Error('P22.3 accepts only RssMarket + RssTickList capture sources');
  if (bundle.excelReadOnly !== true || bundle.market.excelReadOnly !== true || bundle.ticks.excelReadOnly !== true) throw new Error('P22.3 requires explicit Excel READ ONLY provenance');
  if (bundle.transmitted !== false || bundle.market.transmitted !== false || bundle.ticks.transmitted !== false) throw new Error('P22.3 rejects transmitted capture objects');
  for (const key of SAFETY_FALSE_KEYS) {
    if (bundle[key] !== false) throw new Error(`P22.3 requires bundle.${key} === false`);
    if (bundle.safety?.[key] !== false) throw new Error(`P22.3 requires bundle.safety.${key} === false`);
  }
  const symbol = safeText(bundle.symbol, 'bundle.symbol');
  const sessionDate = safeText(bundle.sessionDate, 'bundle.sessionDate');
  const capturedAt = parseIso(bundle.capturedAt, 'bundle.capturedAt');
  if (bundle.market.symbol !== symbol || bundle.ticks.symbol !== symbol) throw new Error('P22.3 bundle symbol mismatch');
  if (bundle.market.sessionDate !== sessionDate || bundle.ticks.sessionDate !== sessionDate) throw new Error('P22.3 bundle sessionDate mismatch');
  if (parseIso(bundle.market.capturedAt, 'market.capturedAt') !== capturedAt || parseIso(bundle.ticks.capturedAt, 'ticks.capturedAt') !== capturedAt) throw new Error('P22.3 bundle capturedAt mismatch');
  return { symbol, sessionDate, capturedAt };
}

function freezeEvent(event) {
  return Object.freeze({ ...event, safety: PHASE57_P22_3_SAFETY });
}

export function buildDurableMicrostructureEvents(bundle) {
  const { symbol, sessionDate, capturedAt } = assertBundleSafety(bundle);
  const captureKey = `${symbol}|${sessionDate}|${capturedAt}`;
  const ticks = Array.isArray(bundle.ticks.newTicks) ? bundle.ticks.newTicks : [];
  const meta = freezeEvent({
    phase: '57.p22.3',
    eventType: 'RSS_MICROSTRUCTURE_CAPTURE_META',
    eventId: `CAPTURE_META|${captureKey}`,
    captureKey,
    symbol,
    sessionDate,
    capturedAt,
    sourceMode: READ_ONLY_MODE,
    sourceFunctions: Object.freeze(['RssMarket', 'RssTickList']),
    captureStatus: bundle.status,
    continuityStatus: bundle.ticks.continuityStatus ?? null,
    replayEligible: bundle.ticks.replayEligible === true,
    reviewRequired: bundle.ticks.replayEligible !== true,
    previousWindowSize: finiteNonNegative(bundle.ticks.previousWindowSize),
    currentWindowSize: finiteNonNegative(bundle.ticks.currentWindowSize),
    overlapLength: finiteNonNegative(bundle.ticks.overlapLength),
    newTickCount: finiteNonNegative(bundle.ticks.newTickCount),
    persistenceMode: 'RESEARCH_EVENT_ONLY',
    transmitted: false,
  });
  const market = freezeEvent({
    phase: '57.p22.3',
    eventType: 'RSS_MARKET_SNAPSHOT_EVENT',
    eventId: `MARKET|${captureKey}`,
    captureKey,
    symbol,
    sessionDate,
    capturedAt,
    timestamp: parseIso(bundle.market.timestamp ?? capturedAt, 'market.timestamp'),
    sourceMode: READ_ONLY_MODE,
    sourceFunction: 'RssMarket',
    payload: bundle.market,
    transmitted: false,
  });
  const tickEvents = ticks.map((tick, index) => {
    const captureId = safeText(tick.captureId, `ticks.newTicks[${index}].captureId`);
    const ordinal = Number(tick.tickOrdinalWithinCapture);
    if (!Number.isInteger(ordinal) || ordinal < 0) throw new Error(`ticks.newTicks[${index}].tickOrdinalWithinCapture must be a non-negative integer`);
    const timestamp = parseIso(tick.timestamp, `ticks.newTicks[${index}].timestamp`);
    const price = finitePositive(tick.price, `ticks.newTicks[${index}].price`);
    const volume = finiteNonNegative(tick.volume ?? tick.size, NaN);
    if (!Number.isFinite(volume)) throw new TypeError(`ticks.newTicks[${index}].volume must be a finite non-negative number`);
    return freezeEvent({
      phase: '57.p22.3',
      eventType: 'RSS_TICK_EVENT',
      eventId: `TICK|${captureId}|${ordinal}`,
      captureKey,
      symbol,
      sessionDate,
      capturedAt,
      timestamp,
      price,
      volume,
      size: volume,
      captureId,
      tickOrdinalWithinCapture: ordinal,
      sourceMode: READ_ONLY_MODE,
      sourceFunction: 'RssTickList',
      transmitted: false,
    });
  });
  return Object.freeze([meta, market, ...tickEvents]);
}

function assertDurableEvent(event, label = 'event') {
  if (!event || typeof event !== 'object') throw new TypeError(`${label} must be an object`);
  if (!P22_3_DURABLE_EVENT_TYPES.includes(event.eventType)) throw new Error(`${label}.eventType is not a P22.3 durable event type`);
  safeText(event.eventId, `${label}.eventId`);
  safeText(event.captureKey, `${label}.captureKey`);
  safeText(event.symbol, `${label}.symbol`);
  safeText(event.sessionDate, `${label}.sessionDate`);
  parseIso(event.capturedAt, `${label}.capturedAt`);
  if (event.sourceMode !== READ_ONLY_MODE) throw new Error(`${label} must retain READ ONLY sourceMode`);
  if (event.transmitted !== false) throw new Error(`${label}.transmitted must remain false`);
  for (const key of SAFETY_FALSE_KEYS) {
    if (event.safety?.[key] !== false) throw new Error(`${label}.safety.${key} must remain false`);
  }
  return event;
}

function eventFingerprint(event) {
  return JSON.stringify(event);
}

function eventSortOrder(event) {
  if (event.eventType === 'RSS_MICROSTRUCTURE_CAPTURE_META') return 0;
  if (event.eventType === 'RSS_MARKET_SNAPSHOT_EVENT') return 1;
  return 2;
}

function compareEvents(a, b) {
  return Date.parse(a.capturedAt) - Date.parse(b.capturedAt)
    || a.symbol.localeCompare(b.symbol)
    || eventSortOrder(a) - eventSortOrder(b)
    || finiteNonNegative(a.tickOrdinalWithinCapture) - finiteNonNegative(b.tickOrdinalWithinCapture)
    || a.eventId.localeCompare(b.eventId);
}

export function appendMicrostructureEventsIdempotently(existingEvents = [], incomingEvents = []) {
  if (!Array.isArray(existingEvents) || !Array.isArray(incomingEvents)) throw new TypeError('existingEvents and incomingEvents must be arrays');
  const ledger = new Map();
  let existingDuplicatesCollapsed = 0;
  let replayedDuplicates = 0;
  const inserted = [];

  const insert = (event, origin, index) => {
    assertDurableEvent(event, `${origin}[${index}]`);
    const prior = ledger.get(event.eventId);
    if (!prior) {
      ledger.set(event.eventId, event);
      if (origin === 'incomingEvents') inserted.push(event);
      return;
    }
    if (eventFingerprint(prior) !== eventFingerprint(event)) throw new Error(`EVENT_ID_CONFLICT:${event.eventId}`);
    if (origin === 'existingEvents') existingDuplicatesCollapsed += 1;
    else replayedDuplicates += 1;
  };

  existingEvents.forEach((event, index) => insert(event, 'existingEvents', index));
  incomingEvents.forEach((event, index) => insert(event, 'incomingEvents', index));
  const events = [...ledger.values()].sort(compareEvents);
  return Object.freeze({
    phase: '57.p22.3',
    status: 'MICROSTRUCTURE_EVENT_APPEND_READY',
    events: Object.freeze(events),
    inserted: Object.freeze(inserted.slice().sort(compareEvents)),
    insertedCount: inserted.length,
    replayedDuplicates,
    existingDuplicatesCollapsed,
    identityMode: 'EVENT_ID_ONLY_NEVER_TIMESTAMP_PRICE_VOLUME_DEDUP',
    multiplicityPreserved: true,
    persistenceWritePerformed: false,
    transmitted: false,
    safety: PHASE57_P22_3_SAFETY,
  });
}

function captureMetaEvents(events) {
  return events.filter(event => event?.eventType === 'RSS_MICROSTRUCTURE_CAPTURE_META')
    .map((event, index) => assertDurableEvent(event, `events[meta:${index}]`));
}

export function auditMicrostructureCaptureGaps(events = [], {
  expectedIntervalMs = 5000,
  maxGapMultiplier = 3,
  activeWindowsJst = null,
} = {}) {
  if (!Array.isArray(events)) throw new TypeError('events must be an array');
  const expected = finitePositive(expectedIntervalMs, 'expectedIntervalMs');
  const multiplier = finitePositive(maxGapMultiplier, 'maxGapMultiplier');
  const thresholdMs = expected * multiplier;
  const activeWindows = normalizeActiveWindowsJst(activeWindowsJst);
  const meta = captureMetaEvents(events);
  const groups = new Map();
  for (const event of meta) {
    const key = `${event.symbol}|${event.sessionDate}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(event);
  }

  const largeGaps = [];
  const continuityBreaks = [];
  const ambiguousCaptures = [];
  let ignoredInactiveWindowTransitions = 0;
  for (const event of meta) {
    if (event.replayEligible !== true || event.continuityStatus === 'AMBIGUOUS_FULL_300_ROW_WINDOW_NO_SEQUENCE') ambiguousCaptures.push(event.eventId);
    if (event.previousWindowSize > 0 && event.currentWindowSize > 0 && event.overlapLength === 0) continuityBreaks.push(event.eventId);
  }

  for (const [groupKey, captures] of groups) {
    const ordered = captures.slice().sort((a, b) => Date.parse(a.capturedAt) - Date.parse(b.capturedAt) || a.eventId.localeCompare(b.eventId));
    for (let index = 1; index < ordered.length; index += 1) {
      const previous = ordered[index - 1];
      const current = ordered[index];
      const previousWindow = activeWindowIndex(previous.capturedAt, activeWindows);
      const currentWindow = activeWindowIndex(current.capturedAt, activeWindows);
      if (activeWindows && (previousWindow < 0 || currentWindow < 0 || previousWindow !== currentWindow)) {
        ignoredInactiveWindowTransitions += 1;
        continue;
      }
      const gapMs = Date.parse(current.capturedAt) - Date.parse(previous.capturedAt);
      if (gapMs > thresholdMs) {
        largeGaps.push(Object.freeze({
          groupKey,
          previousEventId: previous.eventId,
          currentEventId: current.eventId,
          previousCapturedAt: previous.capturedAt,
          currentCapturedAt: current.capturedAt,
          gapMs,
          thresholdMs,
        }));
      }
    }
  }

  const healthy = largeGaps.length === 0 && continuityBreaks.length === 0 && ambiguousCaptures.length === 0;
  return Object.freeze({
    phase: '57.p22.3',
    status: healthy ? 'MICROSTRUCTURE_GAP_AUDIT_CLEAR' : 'MICROSTRUCTURE_GAP_AUDIT_BLOCKED',
    captureCount: meta.length,
    symbolSessionCount: groups.size,
    thresholdMs,
    largeGaps: Object.freeze(largeGaps),
    continuityBreaks: Object.freeze(continuityBreaks),
    ambiguousCaptures: Object.freeze(ambiguousCaptures),
    ignoredInactiveWindowTransitions,
    activeWindowsConfigured: Boolean(activeWindows),
    replayEligible: healthy,
    transmitted: false,
    safety: PHASE57_P22_3_SAFETY,
  });
}

export function assessMicrostructureRuntimeHealth(events = [], {
  asOf,
  expectedIntervalMs = 5000,
  staleAfterMs = 30000,
  maxGapMultiplier = 3,
  activeWindowsJst = null,
} = {}) {
  if (!Array.isArray(events)) throw new TypeError('events must be an array');
  const now = parseIso(asOf, 'asOf');
  const staleThreshold = finitePositive(staleAfterMs, 'staleAfterMs');
  const activeWindows = normalizeActiveWindowsJst(activeWindowsJst);
  const gapAudit = auditMicrostructureCaptureGaps(events, { expectedIntervalMs, maxGapMultiplier, activeWindowsJst });
  const meta = captureMetaEvents(events);
  const bySymbol = new Map();
  for (const event of meta) {
    if (!bySymbol.has(event.symbol)) bySymbol.set(event.symbol, []);
    bySymbol.get(event.symbol).push(event);
  }

  const nowWindow = activeWindowIndex(now, activeWindows);
  const runtimeExpectedActive = !activeWindows || nowWindow >= 0;
  const symbolHealth = {};
  const staleSymbols = [];
  for (const [symbol, captures] of bySymbol) {
    const latest = captures.slice().sort((a, b) => Date.parse(a.capturedAt) - Date.parse(b.capturedAt)).at(-1);
    const ageMs = Math.max(0, Date.parse(now) - Date.parse(latest.capturedAt));
    const latestWindow = activeWindowIndex(latest.capturedAt, activeWindows);
    let stale = false;
    if (runtimeExpectedActive) {
      if (jstDate(now) !== latest.sessionDate) stale = true;
      else if (activeWindows && latestWindow !== nowWindow) stale = true;
      else stale = ageMs > staleThreshold;
    }
    if (stale) staleSymbols.push(symbol);
    symbolHealth[symbol] = Object.freeze({
      latestCapturedAt: latest.capturedAt,
      ageMs,
      stale,
      latestWindowIndex: latestWindow,
      runtimeExpectedActive,
      pausedByConfiguredWindow: !runtimeExpectedActive,
    });
  }

  const blockers = [];
  if (meta.length === 0) blockers.push('NO_MICROSTRUCTURE_CAPTURE');
  if (staleSymbols.length) blockers.push('STALE_MICROSTRUCTURE_CAPTURE');
  if (gapAudit.largeGaps.length) blockers.push('MICROSTRUCTURE_CAPTURE_GAPS');
  if (gapAudit.continuityBreaks.length) blockers.push('RSS_TICK_WINDOW_CONTINUITY_BREAK');
  if (gapAudit.ambiguousCaptures.length) blockers.push('AMBIGUOUS_FULL_300_ROW_WINDOW');
  return Object.freeze({
    phase: '57.p22.3',
    status: blockers.length ? 'MICROSTRUCTURE_RUNTIME_HEALTH_BLOCKED' : 'MICROSTRUCTURE_RUNTIME_HEALTHY',
    asOf: now,
    runtimeExpectedActive,
    captureCount: meta.length,
    symbolCount: bySymbol.size,
    staleSymbols: Object.freeze(staleSymbols.sort()),
    blockers: Object.freeze(blockers),
    symbols: Object.freeze(symbolHealth),
    gapAudit,
    replayEligible: blockers.length === 0,
    edgeClaimAllowed: false,
    transmitted: false,
    safety: PHASE57_P22_3_SAFETY,
  });
}

export function planMicrostructureRetention(events = [], {
  asOf,
  retentionDays = 30,
  maxCapturesPerSymbolSession = 10000,
  preserveReviewEvidence = true,
} = {}) {
  if (!Array.isArray(events)) throw new TypeError('events must be an array');
  const now = parseIso(asOf, 'asOf');
  const days = finitePositive(retentionDays, 'retentionDays');
  const maxCaptures = finitePositive(maxCapturesPerSymbolSession, 'maxCapturesPerSymbolSession');
  if (!Number.isInteger(maxCaptures)) throw new TypeError('maxCapturesPerSymbolSession must be an integer');
  events.forEach((event, index) => assertDurableEvent(event, `events[${index}]`));
  const cutoffMs = Date.parse(now) - days * 86400000;
  const groups = new Map();
  for (const event of events) {
    if (!groups.has(event.captureKey)) groups.set(event.captureKey, []);
    groups.get(event.captureKey).push(event);
  }
  const captureInfo = [...groups.entries()].map(([captureKey, captureEvents]) => {
    const meta = captureEvents.find(event => event.eventType === 'RSS_MICROSTRUCTURE_CAPTURE_META') ?? null;
    const sample = meta ?? captureEvents[0];
    const capturedAt = parseIso(sample.capturedAt, `capture ${captureKey} capturedAt`);
    return {
      captureKey,
      events: captureEvents,
      symbol: sample.symbol,
      sessionDate: sample.sessionDate,
      capturedAt,
      reviewEvidence: Boolean(meta && meta.replayEligible !== true),
    };
  });

  const protectedCaptureKeys = new Set(captureInfo.filter(info => preserveReviewEvidence && info.reviewEvidence).map(info => info.captureKey));
  const expiredCaptureKeys = new Set(captureInfo.filter(info => Date.parse(info.capturedAt) < cutoffMs && !protectedCaptureKeys.has(info.captureKey)).map(info => info.captureKey));
  const overflowCaptureKeys = new Set();
  const eligible = captureInfo.filter(info => !expiredCaptureKeys.has(info.captureKey) && !protectedCaptureKeys.has(info.captureKey));
  const bySymbolSession = new Map();
  for (const info of eligible) {
    const key = `${info.symbol}|${info.sessionDate}`;
    if (!bySymbolSession.has(key)) bySymbolSession.set(key, []);
    bySymbolSession.get(key).push(info);
  }
  for (const infos of bySymbolSession.values()) {
    const ordered = infos.slice().sort((a, b) => Date.parse(b.capturedAt) - Date.parse(a.capturedAt) || b.captureKey.localeCompare(a.captureKey));
    ordered.slice(maxCaptures).forEach(info => overflowCaptureKeys.add(info.captureKey));
  }

  const archiveKeys = new Set([...expiredCaptureKeys, ...overflowCaptureKeys]);
  const retainedEvents = events.filter(event => !archiveKeys.has(event.captureKey));
  const archiveCandidates = events.filter(event => archiveKeys.has(event.captureKey));
  return Object.freeze({
    phase: '57.p22.3',
    status: 'MICROSTRUCTURE_RETENTION_PLAN_READY',
    asOf: now,
    retentionDays: days,
    maxCapturesPerSymbolSession: maxCaptures,
    preserveReviewEvidence: Boolean(preserveReviewEvidence),
    retainedEvents: Object.freeze(retainedEvents.slice().sort(compareEvents)),
    archiveCandidates: Object.freeze(archiveCandidates.slice().sort(compareEvents)),
    retainedEventCount: retainedEvents.length,
    archiveCandidateCount: archiveCandidates.length,
    expiredCaptureKeys: Object.freeze([...expiredCaptureKeys].sort()),
    overflowCaptureKeys: Object.freeze([...overflowCaptureKeys].sort()),
    protectedCaptureKeys: Object.freeze([...protectedCaptureKeys].sort()),
    deletionPerformed: false,
    persistenceWritePerformed: false,
    automaticRetentionMutationAllowed: false,
    transmitted: false,
    safety: PHASE57_P22_3_SAFETY,
  });
}

export function buildMicrostructureDurabilityCycle({
  bundle,
  existingEvents = [],
  asOf,
  expectedIntervalMs = 5000,
  staleAfterMs = 30000,
  maxGapMultiplier = 3,
  activeWindowsJst = null,
  retentionDays = 30,
  maxCapturesPerSymbolSession = 10000,
} = {}) {
  const incomingEvents = buildDurableMicrostructureEvents(bundle);
  const append = appendMicrostructureEventsIdempotently(existingEvents, incomingEvents);
  const health = assessMicrostructureRuntimeHealth(append.events, {
    asOf: asOf ?? bundle?.capturedAt,
    expectedIntervalMs,
    staleAfterMs,
    maxGapMultiplier,
    activeWindowsJst,
  });
  const retention = planMicrostructureRetention(append.events, {
    asOf: asOf ?? bundle?.capturedAt,
    retentionDays,
    maxCapturesPerSymbolSession,
  });
  const ready = health.replayEligible && bundle?.ticks?.replayEligible === true;
  return Object.freeze({
    phase: '57.p22.3',
    status: ready ? 'MICROSTRUCTURE_DURABILITY_READY' : 'MICROSTRUCTURE_DURABILITY_BLOCKED',
    incomingEvents,
    append,
    health,
    retention,
    researchReplayEligible: ready,
    edgeClaimAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    paperTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    persistenceWritePerformed: false,
    transmitted: false,
    safety: PHASE57_P22_3_SAFETY,
  });
}

export default {
  normalizeActiveWindowsJst,
  buildDurableMicrostructureEvents,
  appendMicrostructureEventsIdempotently,
  auditMicrostructureCaptureGaps,
  assessMicrostructureRuntimeHealth,
  planMicrostructureRetention,
  buildMicrostructureDurabilityCycle,
};
