import { createHash } from 'node:crypto';
import { PHASE57_ENTRY_QUALITY_V2_SAFETY } from './phase57-entry-quality-v2-research.js';

export const PHASE57_ENTRY_QUALITY_V2_EVIDENCE_POLICY = Object.freeze({
  mode: 'PHASE57_ENTRY_QUALITY_V2_FROZEN_EVIDENCE_READ_ONLY',
  acceptedBaseline: 'PHASE57_P21_FROZEN_ENTRY',
  requireFrozenBeforeOutcome: true,
  requireCurrentOutcomeUnused: true,
  requireContextBars: true,
  requireSelectorLineage: true,
  allowPostHocUniverseExclusion: false,
  emitNewSignal: false,
  automaticPromotionAllowed: false,
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

function assertSafety() {
  for (const key of FALSE_KEYS) {
    if (PHASE57_ENTRY_QUALITY_V2_SAFETY[key] !== false) {
      throw new Error(`ENTRY_V2_EVIDENCE_UNSAFE_${key}`);
    }
  }
}

function iso(value, label) {
  const ms = Date.parse(String(value ?? ''));
  if (!Number.isFinite(ms)) throw new Error(`ENTRY_V2_EVIDENCE_INVALID_${label}`);
  return new Date(ms).toISOString();
}

function sym(value) {
  return String(value ?? '').trim().toUpperCase();
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  }
  return value;
}

function sha256(value) {
  return createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');
}

function normalizeContextBars(entry) {
  if (!Array.isArray(entry?.contextBars) || !entry.contextBars.length) {
    throw new Error('ENTRY_V2_EVIDENCE_CONTEXT_BARS_REQUIRED');
  }
  const atMs = Date.parse(String(entry.entryTimestamp ?? ''));
  return Object.freeze(entry.contextBars.map((bar, index) => {
    const timestamp = iso(bar?.timestamp, `CONTEXT_BAR_${index}_TIMESTAMP`);
    const normalized = Object.freeze({
      timestamp,
      open: Number(bar?.open),
      high: Number(bar?.high),
      low: Number(bar?.low),
      close: Number(bar?.close),
      volume: Number(bar?.volume ?? 0),
    });
    if (![normalized.open, normalized.high, normalized.low, normalized.close, normalized.volume].every(Number.isFinite)) {
      throw new Error('ENTRY_V2_EVIDENCE_INVALID_CONTEXT_BAR');
    }
    if (normalized.open <= 0 || normalized.close <= 0 || normalized.high < normalized.low || normalized.volume < 0) {
      throw new Error('ENTRY_V2_EVIDENCE_INVALID_CONTEXT_BAR');
    }
    // Realtime Lane Y convention: timestamp is bar start; only a fully closed 5m bar is causal.
    if (Date.parse(timestamp) + 5 * 60_000 > atMs) {
      throw new Error('ENTRY_V2_EVIDENCE_UNCLOSED_CONTEXT_BAR');
    }
    return normalized;
  }).sort((a, b) => a.timestamp.localeCompare(b.timestamp)));
}

function validateBaselineEntry(entry) {
  if (!entry || entry.entryAccepted !== true) throw new Error('ENTRY_V2_EVIDENCE_ACCEPTED_BASELINE_REQUIRED');
  if (entry.frozenBeforeOutcome !== true || entry.currentOutcomeUsed !== false) {
    throw new Error('ENTRY_V2_EVIDENCE_BASELINE_CAUSAL_ATTESTATION_FAILED');
  }
  if (!['LONG', 'SHORT'].includes(String(entry.direction))) throw new Error('ENTRY_V2_EVIDENCE_DIRECTION_REQUIRED');
  if (!(Number(entry.entryPrice) > 0)) throw new Error('ENTRY_V2_EVIDENCE_ENTRY_PRICE_REQUIRED');
  if (!sym(entry.symbol)) throw new Error('ENTRY_V2_EVIDENCE_SYMBOL_REQUIRED');
  iso(entry.entryTimestamp, 'ENTRY_TIMESTAMP');
  const selectionTimestamp = iso(entry.selectionLineage?.selectionTimestamp, 'SELECTION_TIMESTAMP');
  if (selectionTimestamp !== iso(entry.entryTimestamp, 'ENTRY_TIMESTAMP')) {
    throw new Error('ENTRY_V2_EVIDENCE_SELECTION_TIMESTAMP_MISMATCH');
  }
  if (!String(entry.selectionLineage?.variant ?? '').trim() || !String(entry.selectionLineage?.selectorCandidateId ?? '').trim()) {
    throw new Error('ENTRY_V2_EVIDENCE_SELECTOR_LINEAGE_REQUIRED');
  }
}

function entrySetsFromEvidence(evidence) {
  if (Array.isArray(evidence)) return [evidence];
  if (Array.isArray(evidence?.frozenEntries)) return [evidence.frozenEntries];
  if (Array.isArray(evidence?.entry?.latest)) return [evidence.entry.latest];
  if (Array.isArray(evidence?.entry?.history)) {
    return evidence.entry.history.map(point => {
      if (!Array.isArray(point?.frozenEntries)) throw new Error('ENTRY_V2_EVIDENCE_HISTORY_POINT_MALFORMED');
      return point.frozenEntries;
    });
  }
  throw new Error('ENTRY_V2_EVIDENCE_FROZEN_ENTRY_SET_REQUIRED');
}

export function extractEntryQualityV2FrozenEvidence(evidence, { sourceId = null } = {}) {
  assertSafety();
  const rawEntries = entrySetsFromEvidence(evidence).flat();
  if (!rawEntries.length) {
    return Object.freeze({
      policy: PHASE57_ENTRY_QUALITY_V2_EVIDENCE_POLICY,
      safety: PHASE57_ENTRY_QUALITY_V2_SAFETY,
      sourceId,
      evidenceSha256: sha256(evidence),
      entryCount: 0,
      entries: Object.freeze([]),
      status: 'VALID_FROZEN_EVIDENCE_NO_ENTRIES',
    });
  }

  const seen = new Set();
  const entries = rawEntries.map(entry => {
    validateBaselineEntry(entry);
    const contextBars = normalizeContextBars(entry);
    const symbol = sym(entry.symbol);
    const entryTimestamp = iso(entry.entryTimestamp, 'ENTRY_TIMESTAMP');
    const candidateId = String(entry.candidateId ?? '').trim();
    if (!candidateId) throw new Error('ENTRY_V2_EVIDENCE_CANDIDATE_ID_REQUIRED');
    if (seen.has(candidateId)) throw new Error('ENTRY_V2_EVIDENCE_DUPLICATE_CANDIDATE');
    seen.add(candidateId);

    return Object.freeze({
      baselineEntry: entry,
      candidateId,
      symbol,
      sessionDate: String(entry.sessionDate ?? ''),
      entryTimestamp,
      entryPrice: Number(entry.entryPrice),
      direction: String(entry.direction),
      selector: Object.freeze({
        variant: String(entry.selectionLineage.variant),
        variantId: entry.selectionLineage.variantId ?? null,
        selectionTimestamp: iso(entry.selectionLineage.selectionTimestamp, 'SELECTION_TIMESTAMP'),
        sourceAsOf: entry.selectionLineage.sourceAsOf ?? null,
        selectorCandidateId: String(entry.selectionLineage.selectorCandidateId),
        opportunityScore: entry.selectionLineage.opportunityScore ?? null,
        v2Score: entry.selectionLineage.v2Score ?? null,
      }),
      contextBars,
      contextBarsSha256: sha256(contextBars),
      universeExcluded: false,
      newSignalEmitted: false,
    });
  });

  return Object.freeze({
    policy: PHASE57_ENTRY_QUALITY_V2_EVIDENCE_POLICY,
    safety: PHASE57_ENTRY_QUALITY_V2_SAFETY,
    sourceId,
    evidenceSha256: sha256(evidence),
    entryCount: entries.length,
    entries: Object.freeze(entries),
    status: 'VALID_FROZEN_EVIDENCE_READ_ONLY',
  });
}

export default {
  PHASE57_ENTRY_QUALITY_V2_EVIDENCE_POLICY,
  extractEntryQualityV2FrozenEvidence,
};
