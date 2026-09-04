import { createHash } from 'node:crypto';

export const ENTRY_V2_CANDIDATE_INVENTORY_POLICY = Object.freeze({
  mode: 'ENTRY_V2_DURABLE_FROZEN_ENTRY_INVENTORY_READ_ONLY',
  acceptedRoute: 'Dynamic 5m Selection -> Frozen Entry -> EXIT v3',
  acceptedBaseline: 'PHASE57_P21_FROZEN_ENTRY',
  selectorChangesAllowed: false,
  exitChangesAllowed: false,
  capitalAllocationChangesAllowed: false,
  automaticPromotionAllowed: false,
  executionAllowed: false,
});

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

function normalizeEntry(pair, sessionDate) {
  const entry = pair?.entry;
  if (!entry || typeof entry !== 'object') throw new Error('ENTRY_V2_INVENTORY_ENTRY_REQUIRED');
  const symbol = String(entry.symbol ?? pair?.symbol ?? '').trim().toUpperCase();
  const entryTimestamp = String(entry.entryTimestamp ?? '');
  const selectionObservedAt = String(entry.selectionObservedAt ?? '');
  const direction = String(entry.direction ?? '').toUpperCase();
  const entryPrice = Number(entry.entryPrice);

  if (!symbol) throw new Error('ENTRY_V2_INVENTORY_SYMBOL_REQUIRED');
  if (!Number.isFinite(Date.parse(entryTimestamp))) throw new Error('ENTRY_V2_INVENTORY_ENTRY_TIMESTAMP_REQUIRED');
  if (!Number.isFinite(Date.parse(selectionObservedAt))) throw new Error('ENTRY_V2_INVENTORY_SELECTION_TIMESTAMP_REQUIRED');
  if (entryTimestamp !== selectionObservedAt) throw new Error('ENTRY_V2_INVENTORY_SELECTION_ENTRY_TIMESTAMP_MISMATCH');
  if (!['LONG', 'SHORT'].includes(direction)) throw new Error('ENTRY_V2_INVENTORY_DIRECTION_INVALID');
  if (!(entryPrice > 0)) throw new Error('ENTRY_V2_INVENTORY_ENTRY_PRICE_INVALID');
  if (entry.entryAccepted !== true) throw new Error('ENTRY_V2_INVENTORY_ENTRY_NOT_ACCEPTED');
  if (entry.frozenBeforeOutcome !== true) throw new Error('ENTRY_V2_INVENTORY_NOT_FROZEN_BEFORE_OUTCOME');
  if (entry.currentOutcomeUsed !== false) throw new Error('ENTRY_V2_INVENTORY_CURRENT_OUTCOME_USED');
  if (!Array.isArray(entry.variantMemberships) || !entry.variantMemberships.includes('DYNAMIC_5M')) {
    throw new Error('ENTRY_V2_INVENTORY_DYNAMIC5M_LINEAGE_REQUIRED');
  }

  return Object.freeze({
    candidateId: String(entry.key ?? pair?.key ?? `${sessionDate}|${entryTimestamp}|${symbol}`),
    sessionDate,
    symbol,
    entryTimestamp,
    selectionObservedAt,
    featureCutoff: String(entry.featureCutoff ?? ''),
    direction,
    signalDirection: Number(entry.signalDirection),
    entryPrice,
    confidence: Number.isFinite(Number(entry.confidence)) ? Number(entry.confidence) : null,
    probability: Number.isFinite(Number(entry.probability)) ? Number(entry.probability) : null,
    selectedFeatureFamily: entry.selectedFeatureFamily ?? null,
    selectedModelType: entry.selectedModelType ?? null,
    selectedConfigId: entry.selectedConfigId ?? null,
    selectedThreshold: Number.isFinite(Number(entry.selectedThreshold)) ? Number(entry.selectedThreshold) : null,
    baseHorizonBars: Number.isFinite(Number(entry.baseHorizonBars)) ? Number(entry.baseHorizonBars) : null,
    sector: String(entry.sector ?? 'UNKNOWN'),
    selectionOpportunityScore: Number.isFinite(Number(entry.selectionOpportunityScore)) ? Number(entry.selectionOpportunityScore) : null,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    baseline: ENTRY_V2_CANDIDATE_INVENTORY_POLICY.acceptedBaseline,
  });
}

export function buildEntryV2CandidateInventory({ artifacts = [] } = {}) {
  if (!Array.isArray(artifacts) || !artifacts.length) throw new Error('ENTRY_V2_INVENTORY_ARTIFACTS_REQUIRED');
  const rows = [];
  const seen = new Set();
  const sessions = [];

  for (const artifact of artifacts) {
    const sessionDate = String(artifact?.sessionDate ?? '');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)) throw new Error('ENTRY_V2_INVENTORY_SESSION_DATE_INVALID');
    if (artifact?.status !== 'P25_DYNAMIC5M_BD_DAILY_EVALUATED') throw new Error('ENTRY_V2_INVENTORY_ARTIFACT_STATUS_INVALID');
    if (artifact?.B?.route !== ENTRY_V2_CANDIDATE_INVENTORY_POLICY.acceptedRoute) throw new Error('ENTRY_V2_INVENTORY_ROUTE_MISMATCH');
    const pairs = Array.isArray(artifact?.B?.pairs) ? artifact.B.pairs : [];
    if (Number(artifact?.B?.resolvedCount) !== pairs.length) throw new Error('ENTRY_V2_INVENTORY_RESOLVED_COUNT_MISMATCH');

    let sessionRows = 0;
    for (const pair of pairs) {
      const row = normalizeEntry(pair, sessionDate);
      if (seen.has(row.candidateId)) throw new Error('ENTRY_V2_INVENTORY_DUPLICATE_CANDIDATE');
      seen.add(row.candidateId);
      rows.push(row);
      sessionRows += 1;
    }

    sessions.push(Object.freeze({
      sessionDate,
      candidateCount: sessionRows,
      pointCount: Number(artifact?.B?.pointCount ?? 0),
      expectedPointCount: Number(artifact?.B?.expectedPointCount ?? 0),
      missingExpectedBucketCount: Number(artifact?.B?.missingExpectedBucketCount ?? 0),
      freshCompleteDay: artifact?.freshCompleteDay === true,
      formalOos: artifact?.classification?.formalOos === true,
      promotionEligible: artifact?.classification?.promotionEligible === true,
    }));
  }

  rows.sort((a, b) => a.entryTimestamp.localeCompare(b.entryTimestamp) || a.symbol.localeCompare(b.symbol));
  const countsBySymbol = {};
  const countsByDirection = { LONG: 0, SHORT: 0 };
  const countsBySession = {};
  for (const row of rows) {
    countsBySymbol[row.symbol] = (countsBySymbol[row.symbol] ?? 0) + 1;
    countsByDirection[row.direction] += 1;
    countsBySession[row.sessionDate] = (countsBySession[row.sessionDate] ?? 0) + 1;
  }

  return Object.freeze({
    policy: ENTRY_V2_CANDIDATE_INVENTORY_POLICY,
    rowCount: rows.length,
    rows: Object.freeze(rows),
    sessions: Object.freeze(sessions),
    countsBySymbol: Object.freeze(countsBySymbol),
    countsByDirection: Object.freeze(countsByDirection),
    countsBySession: Object.freeze(countsBySession),
    inventorySha256: fingerprint(rows),
    classification: Object.freeze({
      allRowsFrozenBeforeOutcome: rows.every(row => row.frozenBeforeOutcome === true),
      allRowsCurrentOutcomeUnused: rows.every(row => row.currentOutcomeUsed === false),
      allSessionsFormalOos: sessions.every(row => row.formalOos === true),
      allSessionsComplete: sessions.every(row => row.freshCompleteDay === true),
      promotionEligible: false,
      note: 'Inventory is research evidence only. Incomplete/non-formal sessions remain diagnostic and must not be promoted.',
    }),
    status: 'ENTRY_V2_DURABLE_FROZEN_ENTRY_INVENTORY_READY',
  });
}

export default { ENTRY_V2_CANDIDATE_INVENTORY_POLICY, buildEntryV2CandidateInventory };
