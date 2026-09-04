import { createHash } from 'node:crypto';
import {
  PHASE57_ENTRY_QUALITY_V2_SAFETY,
  PHASE57_ENTRY_QUALITY_V2_POLICY,
} from './phase57-entry-quality-v2-research.js';
import { PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY } from './phase57-entry-quality-v2-labels.js';

export const PHASE57_ENTRY_QUALITY_V2_PAIRED_POLICY = Object.freeze({
  mode: 'PHASE57_ENTRY_QUALITY_V2_PAIRED_RESEARCH_ONLY',
  baseline: 'PHASE57_P21_FROZEN_ENTRY',
  sameSelectorRequired: true,
  sameSelectionTimestampRequired: true,
  sameEntryReferencePriceRequired: true,
  sameExitRequired: true,
  sameCapitalAllocationRequired: true,
  sameCostAssumptionsRequired: true,
  newSignalEmissionAllowed: false,
  automaticPromotionAllowed: false,
});

const FALSE_SAFETY_KEYS = Object.freeze([
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
  for (const key of FALSE_SAFETY_KEYS) {
    if (PHASE57_ENTRY_QUALITY_V2_SAFETY[key] !== false) {
      throw new Error(`ENTRY_V2_PAIRED_UNSAFE_${key}`);
    }
  }
}

function iso(value, label) {
  const ms = Date.parse(String(value ?? ''));
  if (!Number.isFinite(ms)) throw new Error(`ENTRY_V2_PAIRED_INVALID_${label}`);
  return new Date(ms).toISOString();
}

function symbol(value) {
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

function requireFrozenBaseline(entry) {
  if (!entry || entry.entryAccepted !== true) throw new Error('ENTRY_V2_PAIRED_BASELINE_ENTRY_REQUIRED');
  if (entry.frozenBeforeOutcome !== true || entry.currentOutcomeUsed !== false) {
    throw new Error('ENTRY_V2_PAIRED_BASELINE_NOT_FROZEN_BEFORE_OUTCOME');
  }
  if (!['LONG', 'SHORT'].includes(String(entry.direction))) {
    throw new Error('ENTRY_V2_PAIRED_BASELINE_DIRECTION_REQUIRED');
  }
  if (!(Number(entry.entryPrice) > 0)) throw new Error('ENTRY_V2_PAIRED_BASELINE_PRICE_REQUIRED');
}

function requireResearchVector(vector) {
  if (!vector || vector.status !== 'FEATURE_VECTOR_ONLY_NO_SIGNAL') {
    throw new Error('ENTRY_V2_PAIRED_RESEARCH_VECTOR_NOT_FEATURE_ONLY');
  }
  if (vector.signalEligible !== null || vector.direction !== null || vector.longQuality !== null || vector.shortQuality !== null) {
    throw new Error('ENTRY_V2_PAIRED_RESEARCH_VECTOR_EMITTED_SIGNAL');
  }
  if (vector.policy?.baseline !== PHASE57_ENTRY_QUALITY_V2_POLICY.baseline) {
    throw new Error('ENTRY_V2_PAIRED_BASELINE_POLICY_MISMATCH');
  }
}

function requireOfflineLabels(labels) {
  if (!labels || labels.policy?.mode !== 'OFFLINE_FUTURE_LABELS_ONLY') {
    throw new Error('ENTRY_V2_PAIRED_OFFLINE_LABELS_REQUIRED');
  }
  if (
    PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY.mayEnterCurrentFeatureVector !== false ||
    PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY.mayRunInRealtimeScorer !== false ||
    PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY.mayChangeExitBehavior !== false
  ) {
    throw new Error('ENTRY_V2_PAIRED_LABEL_BOUNDARY_BROKEN');
  }
}

export function buildEntryQualityV2PairedRow({
  baselineEntry,
  researchVector,
  pathLabels,
  costAssumptions,
  fixedExitId,
  fixedCapitalAllocationId,
} = {}) {
  assertSafety();
  requireFrozenBaseline(baselineEntry);
  requireResearchVector(researchVector);
  requireOfflineLabels(pathLabels);

  const baselineSymbol = symbol(baselineEntry.symbol);
  const vectorSymbol = symbol(researchVector.symbol);
  if (!baselineSymbol || baselineSymbol !== vectorSymbol) {
    throw new Error('ENTRY_V2_PAIRED_SYMBOL_MISMATCH');
  }

  const entryTimestamp = iso(baselineEntry.entryTimestamp, 'ENTRY_TIMESTAMP');
  const vectorAsOf = iso(researchVector.asOf, 'VECTOR_AS_OF');
  const labelEntryTimestamp = iso(pathLabels.entryTimestamp, 'LABEL_ENTRY_TIMESTAMP');
  const selectionTimestamp = iso(baselineEntry.selectionLineage?.selectionTimestamp, 'SELECTION_TIMESTAMP');

  if (entryTimestamp !== vectorAsOf || entryTimestamp !== labelEntryTimestamp || entryTimestamp !== selectionTimestamp) {
    throw new Error('ENTRY_V2_PAIRED_TIMESTAMP_MISMATCH');
  }

  const baselinePrice = Number(baselineEntry.entryPrice);
  if (Number(pathLabels.entryPrice) !== baselinePrice) {
    throw new Error('ENTRY_V2_PAIRED_ENTRY_PRICE_MISMATCH');
  }

  const selectorVariant = String(baselineEntry.selectionLineage?.variant ?? '').trim();
  const selectorCandidateId = String(baselineEntry.selectionLineage?.selectorCandidateId ?? '').trim();
  if (!selectorVariant || !selectorCandidateId) {
    throw new Error('ENTRY_V2_PAIRED_SELECTOR_LINEAGE_REQUIRED');
  }
  if (!costAssumptions || typeof costAssumptions !== 'object') {
    throw new Error('ENTRY_V2_PAIRED_COST_ASSUMPTIONS_REQUIRED');
  }
  if (!fixedExitId || !fixedCapitalAllocationId) {
    throw new Error('ENTRY_V2_PAIRED_FIXED_EXPERIMENT_IDS_REQUIRED');
  }

  const featurePayload = Object.freeze({
    market: researchVector.market,
    daily: researchVector.daily,
    intraday: researchVector.intraday,
    universe: researchVector.universe,
    novelty: researchVector.novelty,
  });

  const pairKey = `${baselineEntry.sessionDate}|${entryTimestamp}|${selectorVariant}|${baselineSymbol}`;

  return Object.freeze({
    policy: PHASE57_ENTRY_QUALITY_V2_PAIRED_POLICY,
    safety: PHASE57_ENTRY_QUALITY_V2_SAFETY,
    pairKey,
    sessionDate: baselineEntry.sessionDate,
    symbol: baselineSymbol,
    entryTimestamp,
    entryReferencePrice: baselinePrice,
    selector: Object.freeze({
      variant: selectorVariant,
      selectorCandidateId,
      sourceAsOf: baselineEntry.selectionLineage?.sourceAsOf ?? null,
      opportunityScore: baselineEntry.selectionLineage?.opportunityScore ?? null,
      v2Score: baselineEntry.selectionLineage?.v2Score ?? null,
    }),
    baseline: Object.freeze({
      scorer: PHASE57_ENTRY_QUALITY_V2_POLICY.baseline,
      candidateId: baselineEntry.candidateId,
      batchEntryKey: baselineEntry.batchEntryKey,
      direction: baselineEntry.direction,
      confidence: baselineEntry.confidence ?? null,
      probability: baselineEntry.probability ?? null,
      selectedHorizonBars: baselineEntry.baseHorizonBars ?? null,
      selectedFeatureFamily: baselineEntry.selectedFeatureFamily ?? null,
      selectedModelType: baselineEntry.selectedModelType ?? null,
      selectedConfigId: baselineEntry.selectedConfigId ?? null,
      selectedThreshold: baselineEntry.selectedThreshold ?? null,
    }),
    newResearch: Object.freeze({
      status: researchVector.status,
      featureSha256: sha256(featurePayload),
      features: featurePayload,
      signalEligible: null,
      direction: null,
      longQuality: null,
      shortQuality: null,
    }),
    offlineLabels: Object.freeze({
      labelSha256: sha256(pathLabels),
      labels: pathLabels.labels,
    }),
    experimentControls: Object.freeze({
      fixedExitId: String(fixedExitId),
      fixedCapitalAllocationId: String(fixedCapitalAllocationId),
      costAssumptions: Object.freeze({ ...costAssumptions }),
      selectorFrozen: true,
      marketDataTimestampFrozen: true,
      exitFrozen: true,
      capitalAllocationFrozen: true,
      costAssumptionsFrozen: true,
    }),
    status: 'PAIRED_RESEARCH_ROW_NO_NEW_SIGNAL',
  });
}

export function buildEntryQualityV2PairedDataset(rows = []) {
  assertSafety();
  if (!Array.isArray(rows) || !rows.length) throw new Error('ENTRY_V2_PAIRED_ROWS_REQUIRED');
  const keys = rows.map(row => row?.pairKey);
  if (keys.some(key => !key)) throw new Error('ENTRY_V2_PAIRED_ROW_KEY_REQUIRED');
  if (new Set(keys).size !== keys.length) throw new Error('ENTRY_V2_PAIRED_DUPLICATE_ROW');

  return Object.freeze({
    policy: PHASE57_ENTRY_QUALITY_V2_PAIRED_POLICY,
    rowCount: rows.length,
    datasetSha256: sha256(rows),
    rows: Object.freeze([...rows]),
    status: 'PAIRED_RESEARCH_DATASET_NO_NEW_SIGNAL',
  });
}

export default {
  PHASE57_ENTRY_QUALITY_V2_PAIRED_POLICY,
  buildEntryQualityV2PairedRow,
  buildEntryQualityV2PairedDataset,
};
