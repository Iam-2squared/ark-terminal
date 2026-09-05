import { createHash } from 'node:crypto';
import { buildEntryQualityV2PathLabels } from './phase57-entry-quality-v2-labels.js';
import { PHASE57_ENTRY_QUALITY_V2_SAFETY } from './phase57-entry-quality-v2-research.js';

export const ENTRY_V2_SOURCE_CLASS = Object.freeze({
  actualDurable: 'ACTUAL_DURABLE',
  historicalReplay: 'HISTORICAL_RETROSPECTIVE_REPLAY',
});

export const ENTRY_V2_CANDIDATE_INVENTORY_POLICY = Object.freeze({
  mode: 'ENTRY_V2_DURABLE_FROZEN_ENTRY_INVENTORY_READ_ONLY',
  acceptedRoute: 'Dynamic 5m Selection -> Frozen Entry -> EXIT v3',
  acceptedBaseline: 'PHASE57_P21_FROZEN_ENTRY',
  sourceClass: ENTRY_V2_SOURCE_CLASS.actualDurable,
  canonicalIntradaySource: 'P25_DYNAMIC5M_DAILY_BUNDLE',
  completedBarRule: 'bar.timestamp + 5 minutes <= decisionTimestamp',
  futureLabelsOfflineOnly: true,
  selectorChangesAllowed: false,
  exitChangesAllowed: false,
  capitalAllocationChangesAllowed: false,
  automaticPromotionAllowed: false,
  executionAllowed: false,
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

function iso(value, code) {
  const ms = Date.parse(String(value ?? ''));
  if (!Number.isFinite(ms)) throw new Error(`ENTRY_V2_INVENTORY_${code}_INVALID`);
  return new Date(ms).toISOString();
}

function jstSessionDate(value) {
  const ms = Date.parse(String(value ?? ''));
  if (!Number.isFinite(ms)) throw new Error('ENTRY_V2_INVENTORY_TIMESTAMP_INVALID');
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(ms));
  const fields = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${fields.year}-${fields.month}-${fields.day}`;
}

function assertSafety(safety, label) {
  for (const key of FALSE_KEYS) {
    if (safety?.[key] !== false) throw new Error(`ENTRY_V2_INVENTORY_UNSAFE_${label}_${key}`);
  }
}

function finite(value) {
  return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
}

function sameNumber(left, right) {
  return finite(left) && finite(right) && Math.abs(Number(left) - Number(right)) <= 1e-9;
}

function normalizeBars(bars, sessionDate) {
  if (!Array.isArray(bars) || !bars.length) throw new Error('ENTRY_V2_INVENTORY_SESSION_BARS_REQUIRED');
  let previousMs = -Infinity;
  return Object.freeze(bars.map((bar, index) => {
    const timestamp = iso(bar?.timestamp, `BAR_${index}_TIMESTAMP`);
    const ms = Date.parse(timestamp);
    const normalized = Object.freeze({
      timestamp,
      open: Number(bar?.open),
      high: Number(bar?.high),
      low: Number(bar?.low),
      close: Number(bar?.close),
      volume: Number(bar?.volume ?? 0),
    });
    if (ms <= previousMs) throw new Error('ENTRY_V2_INVENTORY_BARS_NOT_STRICTLY_ORDERED');
    previousMs = ms;
    if (![normalized.open, normalized.high, normalized.low, normalized.close, normalized.volume].every(Number.isFinite)
      || normalized.open <= 0 || normalized.close <= 0 || normalized.high < normalized.low || normalized.volume < 0) {
      throw new Error('ENTRY_V2_INVENTORY_BAR_INVALID');
    }
    if (jstSessionDate(timestamp) !== sessionDate) throw new Error('ENTRY_V2_INVENTORY_CROSS_SESSION_BAR');
    return normalized;
  }));
}

function normalizeEntry(pair, sessionDate) {
  const entry = pair?.entry;
  if (!entry || typeof entry !== 'object') throw new Error('ENTRY_V2_INVENTORY_ENTRY_REQUIRED');
  const symbol = String(entry.symbol ?? pair?.symbol ?? '').trim().toUpperCase();
  const entryTimestamp = iso(entry.entryTimestamp, 'ENTRY_TIMESTAMP');
  const selectionObservedAt = iso(entry.selectionObservedAt, 'SELECTION_TIMESTAMP');
  const featureCutoff = iso(entry.featureCutoff, 'FEATURE_CUTOFF');
  const direction = String(entry.direction ?? '').toUpperCase();
  const entryPrice = Number(entry.entryPrice);
  const candidateId = String(entry.key ?? '').trim();
  const eventId = `${sessionDate}|${entryTimestamp}|${symbol}`;

  if (!symbol) throw new Error('ENTRY_V2_INVENTORY_SYMBOL_REQUIRED');
  if (entryTimestamp !== selectionObservedAt) throw new Error('ENTRY_V2_INVENTORY_SELECTION_ENTRY_TIMESTAMP_MISMATCH');
  if (Date.parse(featureCutoff) > Date.parse(entryTimestamp)) throw new Error('ENTRY_V2_INVENTORY_FEATURE_CUTOFF_AFTER_ENTRY');
  if (jstSessionDate(entryTimestamp) !== sessionDate || jstSessionDate(featureCutoff) !== sessionDate) {
    throw new Error('ENTRY_V2_INVENTORY_ENTRY_SESSION_MISMATCH');
  }
  if (!['LONG', 'SHORT'].includes(direction)) throw new Error('ENTRY_V2_INVENTORY_DIRECTION_INVALID');
  if (!(entryPrice > 0)) throw new Error('ENTRY_V2_INVENTORY_ENTRY_PRICE_INVALID');
  if (!candidateId) throw new Error('ENTRY_V2_INVENTORY_CANDIDATE_KEY_REQUIRED');
  if (String(pair?.key ?? '') !== candidateId) throw new Error('ENTRY_V2_INVENTORY_PAIR_KEY_MISMATCH');
  if (String(pair?.sessionDate ?? '') !== sessionDate || String(entry.sessionDate ?? '') !== sessionDate) {
    throw new Error('ENTRY_V2_INVENTORY_PAIR_SESSION_MISMATCH');
  }
  if (String(pair?.symbol ?? '').trim().toUpperCase() !== symbol) throw new Error('ENTRY_V2_INVENTORY_PAIR_SYMBOL_MISMATCH');
  if (Number(entry.signalDirection) !== (direction === 'LONG' ? 1 : -1)) {
    throw new Error('ENTRY_V2_INVENTORY_SIGNAL_DIRECTION_MISMATCH');
  }
  if (entry.entryAccepted !== true) throw new Error('ENTRY_V2_INVENTORY_ENTRY_NOT_ACCEPTED');
  if (entry.frozenBeforeOutcome !== true) throw new Error('ENTRY_V2_INVENTORY_NOT_FROZEN_BEFORE_OUTCOME');
  if (entry.currentOutcomeUsed !== false) throw new Error('ENTRY_V2_INVENTORY_CURRENT_OUTCOME_USED');
  if (!Array.isArray(entry.variantMemberships) || !entry.variantMemberships.includes('DYNAMIC_5M')) {
    throw new Error('ENTRY_V2_INVENTORY_DYNAMIC5M_LINEAGE_REQUIRED');
  }

  return {
    candidateId,
    candidateEventId: eventId,
    sessionDate,
    symbol,
    entryTimestamp,
    selectionObservedAt,
    featureCutoff,
    direction,
    signalDirection: Number(entry.signalDirection),
    entryPrice,
    confidence: finite(entry.confidence) ? Number(entry.confidence) : null,
    probability: finite(entry.probability) ? Number(entry.probability) : null,
    selectedFeatureFamily: entry.selectedFeatureFamily ?? null,
    selectedModelType: entry.selectedModelType ?? null,
    selectedConfigId: entry.selectedConfigId ?? null,
    selectedThreshold: finite(entry.selectedThreshold) ? Number(entry.selectedThreshold) : null,
    selectedHorizonBars: finite(entry.baseHorizonBars) ? Number(entry.baseHorizonBars) : null,
    modelId: entry.modelId ?? null,
    artifactSha256: entry.artifactSha256 ?? null,
    sector: String(entry.sector ?? 'UNKNOWN'),
    selectionOpportunityScore: finite(entry.selectionOpportunityScore) ? Number(entry.selectionOpportunityScore) : null,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    baseline: ENTRY_V2_CANDIDATE_INVENTORY_POLICY.acceptedBaseline,
    sourceClass: ENTRY_V2_SOURCE_CLASS.actualDurable,
  };
}

function bundleIndex(dailyBundles) {
  const bundles = dailyBundles instanceof Map ? [...dailyBundles.values()] : dailyBundles;
  const index = new Map();
  for (const bundle of Array.isArray(bundles) ? bundles : []) {
    const sessionDate = String(bundle?.sessionDate ?? '');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)) throw new Error('ENTRY_V2_INVENTORY_BUNDLE_SESSION_DATE_INVALID');
    if (index.has(sessionDate)) throw new Error('ENTRY_V2_INVENTORY_DUPLICATE_DAILY_BUNDLE');
    if (bundle?.status !== 'P25_DYNAMIC5M_DAILY_BUNDLE_READY' || bundle?.barsReady !== true) {
      throw new Error('ENTRY_V2_INVENTORY_DAILY_BUNDLE_NOT_READY');
    }
    assertSafety(bundle.safety, 'DAILY_BUNDLE');
    index.set(sessionDate, bundle);
  }
  return index;
}

function enrichFromCanonicalBundle(row, bundle, { horizonsBars, roundTripCostBps }) {
  const matches = (bundle?.points ?? []).filter(point => iso(point?.observedAt, 'POINT_TIMESTAMP') === row.entryTimestamp);
  if (matches.length !== 1) throw new Error('ENTRY_V2_INVENTORY_SELECTION_POINT_NOT_UNIQUE');
  const point = matches[0];
  assertSafety(point.safety, 'SELECTION_POINT');
  const v1Rows = (point.selected ?? []).filter(item => String(item?.symbol ?? '').trim().toUpperCase() === row.symbol);
  if (v1Rows.length !== 1) throw new Error('ENTRY_V2_INVENTORY_V1_MEMBERSHIP_REQUIRED');
  const selected = v1Rows[0];
  if (iso(selected.sourceScannedAt, 'SOURCE_SCANNED_AT') !== row.entryTimestamp) {
    throw new Error('ENTRY_V2_INVENTORY_SELECTION_LINEAGE_MISMATCH');
  }
  if (!sameNumber(selected.currentPrice, row.entryPrice)) throw new Error('ENTRY_V2_INVENTORY_ENTRY_REFERENCE_PRICE_MISMATCH');
  if (row.selectionOpportunityScore !== null
    && !sameNumber(selected.opportunityScore, row.selectionOpportunityScore)) {
    throw new Error('ENTRY_V2_INVENTORY_OPPORTUNITY_SCORE_MISMATCH');
  }

  const selectorMemberships = [{
    variant: 'DYNAMIC5M_V1',
    selectorCandidateId: String(point?.policy?.candidateId ?? 'INTRADAY_DYNAMIC_5M_UNIVERSE_V1'),
    selectionTimestamp: row.entryTimestamp,
    opportunityScore: finite(selected.opportunityScore) ? Number(selected.opportunityScore) : null,
    v2Score: null,
  }];
  const v2Rows = (point.selectedV2 ?? []).filter(item => String(item?.symbol ?? '').trim().toUpperCase() === row.symbol);
  if (v2Rows.length > 1) throw new Error('ENTRY_V2_INVENTORY_DUPLICATE_V2_MEMBERSHIP');
  if (v2Rows.length === 1) {
    assertSafety(point?.dynamic5mV2?.safety, 'SELECTION_POINT_V2');
    selectorMemberships.push({
      variant: 'DYNAMIC5M_V2',
      selectorCandidateId: String(point?.dynamic5mV2?.candidateId ?? 'INTRADAY_DYNAMIC_5M_UNIVERSE_V2'),
      selectionTimestamp: row.entryTimestamp,
      opportunityScore: finite(v2Rows[0].opportunityScore) ? Number(v2Rows[0].opportunityScore) : null,
      v2Score: finite(v2Rows[0].v2Score) ? Number(v2Rows[0].v2Score) : null,
    });
  }

  const fullBars = normalizeBars(bundle?.sessionBarsBySymbol?.[row.symbol], row.sessionDate);
  const decisionMs = Date.parse(row.entryTimestamp);
  const contextBars = Object.freeze(fullBars.filter(bar => Date.parse(bar.timestamp) + 5 * 60_000 <= decisionMs));
  if (contextBars.length < 6) throw new Error('ENTRY_V2_INVENTORY_INSUFFICIENT_CLOSED_CONTEXT');
  if (contextBars.at(-1).timestamp !== row.featureCutoff) throw new Error('ENTRY_V2_INVENTORY_FEATURE_CUTOFF_LINEAGE_MISMATCH');
  if (contextBars.some(bar => Date.parse(bar.timestamp) + 5 * 60_000 > decisionMs)) {
    throw new Error('ENTRY_V2_INVENTORY_UNCLOSED_CONTEXT_BAR');
  }
  const futureBars = fullBars.filter(bar => Date.parse(bar.timestamp) > decisionMs);
  const pathLabels = buildEntryQualityV2PathLabels({
    entryTimestamp: row.entryTimestamp,
    entryPrice: row.entryPrice,
    futureBars,
    horizonsBars,
    roundTripCostBps,
  });

  const selectionLineage = Object.freeze({
    variant: 'DYNAMIC5M_V1',
    variantId: point?.policy?.candidateId ?? null,
    selectionTimestamp: row.entryTimestamp,
    sourceAsOf: selected.sourceScannedAt,
    selectorCandidateId: String(point?.policy?.candidateId ?? 'INTRADAY_DYNAMIC_5M_UNIVERSE_V1'),
    opportunityScore: finite(selected.opportunityScore) ? Number(selected.opportunityScore) : null,
    v2Score: v2Rows.length && finite(v2Rows[0].v2Score) ? Number(v2Rows[0].v2Score) : null,
  });

  return Object.freeze({
    ...row,
    selectorMemberships: Object.freeze(selectorMemberships.map(item => Object.freeze(item))),
    selectorMembershipCount: selectorMemberships.length,
    contextBars,
    contextBarCount: contextBars.length,
    contextBarsSha256: fingerprint(contextBars),
    availableFutureBars: pathLabels.availableFutureBars,
    qualityLabels: pathLabels.labels,
    labelCompleteness: Object.freeze(Object.fromEntries(pathLabels.labels.map(label => [label.horizonBars, label.complete]))),
    featureFrozenBeforeOfflineLabels: true,
    selectionLineage,
    baselineEntry: Object.freeze({
      candidateId: row.candidateId,
      entryAccepted: true,
      symbol: row.symbol,
      sessionDate: row.sessionDate,
      entryTimestamp: row.entryTimestamp,
      entryPrice: row.entryPrice,
      direction: row.direction,
      signalDirection: row.signalDirection,
      contextBars,
      selectionLineage,
      frozenBeforeOutcome: true,
      currentOutcomeUsed: false,
    }),
    canonicalBundleSha256: fingerprint(bundle),
    canonicalSelectionPointSha256: fingerprint(point),
    pointInTimeValid: true,
    pitViolationCount: 0,
  });
}

function reasonCounts(blocked) {
  const counts = {};
  for (const item of blocked) {
    const reason = String(item?.reason ?? item?.status ?? 'UNKNOWN');
    counts[reason] = (counts[reason] ?? 0) + 1;
  }
  return counts;
}

export function buildEntryV2CandidateInventory({
  artifacts = [],
  dailyBundles = [],
  requireCanonicalBars = false,
  horizonsBars = [1, 2, 3, 6, 12],
  roundTripCostBps = 0,
} = {}) {
  if (!Array.isArray(artifacts) || !artifacts.length) throw new Error('ENTRY_V2_INVENTORY_ARTIFACTS_REQUIRED');
  assertSafety(PHASE57_ENTRY_QUALITY_V2_SAFETY, 'ENTRY_V2_RESEARCH');
  const bundles = bundleIndex(dailyBundles);
  const rows = [];
  const seenCandidates = new Set();
  const seenEvents = new Set();
  const sessions = [];
  const sourceBlocked = [];

  for (const artifact of artifacts) {
    const sessionDate = String(artifact?.sessionDate ?? '');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)) throw new Error('ENTRY_V2_INVENTORY_SESSION_DATE_INVALID');
    if (artifact?.status !== 'P25_DYNAMIC5M_BD_DAILY_EVALUATED') throw new Error('ENTRY_V2_INVENTORY_ARTIFACT_STATUS_INVALID');
    assertSafety(artifact.safety, 'DURABLE_ARTIFACT');
    if (artifact?.B?.route !== ENTRY_V2_CANDIDATE_INVENTORY_POLICY.acceptedRoute) throw new Error('ENTRY_V2_INVENTORY_ROUTE_MISMATCH');
    const pairs = Array.isArray(artifact?.B?.pairs) ? artifact.B.pairs : [];
    const blocked = Array.isArray(artifact?.B?.blocked) ? artifact.B.blocked : [];
    if (Number(artifact?.B?.resolvedCount) !== pairs.length) throw new Error('ENTRY_V2_INVENTORY_RESOLVED_COUNT_MISMATCH');
    if (Number(artifact?.B?.blockedCount) !== blocked.length) throw new Error('ENTRY_V2_INVENTORY_BLOCKED_COUNT_MISMATCH');
    if (Number(artifact?.B?.frozenEntryCount) !== pairs.length + blocked.length) {
      throw new Error('ENTRY_V2_INVENTORY_FROZEN_ENTRY_COUNT_MISMATCH');
    }
    const bundle = bundles.get(sessionDate);
    if (requireCanonicalBars && !bundle) throw new Error('ENTRY_V2_INVENTORY_CANONICAL_DAILY_BUNDLE_REQUIRED');

    let sessionRows = 0;
    for (const pair of pairs) {
      const normalized = normalizeEntry(pair, sessionDate);
      if (seenCandidates.has(normalized.candidateId)) throw new Error('ENTRY_V2_INVENTORY_DUPLICATE_CANDIDATE');
      if (seenEvents.has(normalized.candidateEventId)) throw new Error('ENTRY_V2_INVENTORY_DUPLICATE_CANDIDATE_EVENT');
      seenCandidates.add(normalized.candidateId);
      seenEvents.add(normalized.candidateEventId);
      rows.push(bundle
        ? enrichFromCanonicalBundle(normalized, bundle, { horizonsBars, roundTripCostBps })
        : Object.freeze({
          ...normalized,
          selectorMemberships: Object.freeze([]),
          selectorMembershipCount: 0,
          contextBars: null,
          contextBarCount: null,
          contextBarsSha256: null,
          availableFutureBars: null,
          qualityLabels: null,
          labelCompleteness: null,
          featureFrozenBeforeOfflineLabels: null,
          selectionLineage: null,
          baselineEntry: null,
          canonicalBundleSha256: null,
          canonicalSelectionPointSha256: null,
          pointInTimeValid: null,
          pitViolationCount: null,
        }));
      sessionRows += 1;
    }
    sourceBlocked.push(...blocked.map(item => Object.freeze({ sessionDate, ...item })));

    sessions.push(Object.freeze({
      sourceClass: ENTRY_V2_SOURCE_CLASS.actualDurable,
      sessionDate,
      candidateCount: sessionRows,
      sourceBlockedCount: blocked.length,
      pointCount: Number(artifact?.B?.pointCount ?? 0),
      expectedPointCount: Number(artifact?.B?.expectedPointCount ?? 0),
      missingExpectedBucketCount: Number(artifact?.B?.missingExpectedBucketCount ?? 0),
      freshCompleteDay: artifact?.freshCompleteDay === true,
      formalOos: artifact?.classification?.formalOos === true,
      promotionEligible: artifact?.classification?.promotionEligible === true,
      prospectivePointInTimeSelection: artifact?.classification?.prospectivePointInTimeSelection === true,
      completeSessionEvidence: artifact?.classification?.completeSessionEvidence === true,
      sourceClassification: Object.freeze({ ...(artifact?.classification ?? {}) }),
      sourceArtifactSha256: fingerprint(artifact),
      canonicalBundleAudited: Boolean(bundle),
    }));
  }

  rows.sort((a, b) => a.entryTimestamp.localeCompare(b.entryTimestamp) || a.symbol.localeCompare(b.symbol));
  const countsBySymbol = {};
  const countsByDirection = { LONG: 0, SHORT: 0 };
  const countsBySession = {};
  const countsBySelectorMembership = { DYNAMIC5M_V1: 0, DYNAMIC5M_V2: 0 };
  const labelCompletenessByHorizon = Object.fromEntries([...new Set(horizonsBars.map(Number))].sort((a, b) => a - b)
    .map(horizon => [horizon, { complete: 0, incomplete: 0, total: rows.length }]));
  for (const row of rows) {
    countsBySymbol[row.symbol] = (countsBySymbol[row.symbol] ?? 0) + 1;
    countsByDirection[row.direction] += 1;
    countsBySession[row.sessionDate] = (countsBySession[row.sessionDate] ?? 0) + 1;
    for (const membership of row.selectorMemberships) {
      countsBySelectorMembership[membership.variant] = (countsBySelectorMembership[membership.variant] ?? 0) + 1;
    }
    for (const [horizon, stats] of Object.entries(labelCompletenessByHorizon)) {
      if (row.labelCompleteness?.[horizon] === true) stats.complete += 1;
      else stats.incomplete += 1;
    }
  }

  const canonicalDataAudited = rows.every(row => row.pointInTimeValid === true);
  return Object.freeze({
    policy: ENTRY_V2_CANDIDATE_INVENTORY_POLICY,
    safety: PHASE57_ENTRY_QUALITY_V2_SAFETY,
    sourceClass: ENTRY_V2_SOURCE_CLASS.actualDurable,
    rowCount: rows.length,
    totalCandidates: rows.length,
    uniqueCandidateEventCount: seenEvents.size,
    duplicateCandidateCount: 0,
    uniqueSymbolCount: Object.keys(countsBySymbol).length,
    sessionCount: sessions.length,
    selectorMembershipCount: rows.reduce((sum, row) => sum + row.selectorMembershipCount, 0),
    rows: Object.freeze(rows),
    sessions: Object.freeze(sessions),
    sourceBlocked: Object.freeze(sourceBlocked),
    sourceBlockedCount: sourceBlocked.length,
    blockedReasonDistribution: Object.freeze(reasonCounts(sourceBlocked)),
    countsBySymbol: Object.freeze(countsBySymbol),
    countsByDirection: Object.freeze(countsByDirection),
    countsBySession: Object.freeze(countsBySession),
    countsBySourceClass: Object.freeze({ [ENTRY_V2_SOURCE_CLASS.actualDurable]: rows.length }),
    countsBySelectorMembership: Object.freeze(countsBySelectorMembership),
    labelCompletenessByHorizon: Object.freeze(Object.fromEntries(Object.entries(labelCompletenessByHorizon)
      .map(([horizon, stats]) => [horizon, Object.freeze({ ...stats })]))),
    pitViolationCount: canonicalDataAudited ? rows.reduce((sum, row) => sum + row.pitViolationCount, 0) : null,
    canonicalDataAudited,
    inventorySha256: fingerprint(rows),
    classification: Object.freeze({
      sourceClass: ENTRY_V2_SOURCE_CLASS.actualDurable,
      historicalReplay: false,
      allRowsFrozenBeforeOutcome: rows.every(row => row.frozenBeforeOutcome === true),
      allRowsCurrentOutcomeUnused: rows.every(row => row.currentOutcomeUsed === false),
      allSessionsFormalOos: sessions.every(row => row.formalOos === true),
      allSessionsComplete: sessions.every(row => row.freshCompleteDay === true),
      promotionEligible: false,
      note: 'Actual Durable source classification is preserved. Incomplete/non-formal sessions remain diagnostic and are never upgraded.',
    }),
    status: canonicalDataAudited
      ? 'ENTRY_V2_ACTUAL_DURABLE_CANONICAL_INVENTORY_READY'
      : 'ENTRY_V2_DURABLE_FROZEN_ENTRY_INVENTORY_READY_METADATA_ONLY',
  });
}

export function buildEntryV2ActualDurableCandidateInventory(options = {}) {
  return buildEntryV2CandidateInventory({ ...options, requireCanonicalBars: true });
}

export default {
  ENTRY_V2_SOURCE_CLASS,
  ENTRY_V2_CANDIDATE_INVENTORY_POLICY,
  buildEntryV2CandidateInventory,
  buildEntryV2ActualDurableCandidateInventory,
};
