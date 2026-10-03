import {
  extractEntryQualityV2FrozenEvidence,
} from './phase57-entry-quality-v2-evidence-adapter.js';
import {
  buildEntryV2StrictPitPairedDataset,
} from './phase57-entry-quality-v2-pit-dataset-builder.js';

export const ENTRY_V2_EVIDENCE_DATASET_POLICY = Object.freeze({
  mode: 'ENTRY_V2_FROZEN_EVIDENCE_TO_STRICT_PIT_DATASET_READ_ONLY',
  acceptedBaseline: 'PHASE57_P21_FROZEN_ENTRY',
  selectorChangesAllowed: false,
  exitChangesAllowed: false,
  capitalAllocationChangesAllowed: false,
  automaticPromotionAllowed: false,
  emitNewSignal: false,
  postHocUniverseExclusionAllowed: false,
  dailyHistoryMustResolvePerEntryTimestamp: true,
  futureLabelsOfflineOnly: true,
});

/**
 * Read-only bridge from frozen P21 evidence into the strict Entry Quality v2 paired dataset.
 * The evidence adapter validates causal Frozen Entry lineage first. The paired builder then
 * reuses each baseline entry's exact contextBars, resolves persisted daily archives strictly
 * prior to each Entry session, and attaches future path labels only after feature freeze.
 */
export function buildEntryV2DatasetFromFrozenEvidence({
  evidence,
  evidenceSourceId = null,
  dailyRecordsBySymbol = {},
  dailyBarsBySymbol = {},
  futureBarsBySymbol = {},
  marketByEntryTimestamp = {},
  universeBySymbol = {},
  sourceLineageByEntry = {},
  fixedExitId,
  fixedCapitalAllocationId,
  costAssumptions,
  roundTripCostBps = 0,
  horizonsBars = [1, 2, 3, 6, 12],
} = {}) {
  const frozen = extractEntryQualityV2FrozenEvidence(evidence, { sourceId: evidenceSourceId });
  if (!frozen.entryCount) {
    return Object.freeze({
      policy: ENTRY_V2_EVIDENCE_DATASET_POLICY,
      evidence: Object.freeze({
        sourceId: frozen.sourceId,
        evidenceSha256: frozen.evidenceSha256,
        entryCount: 0,
      }),
      dataset: null,
      status: 'VALID_FROZEN_EVIDENCE_NO_PAIRED_ROWS',
    });
  }

  const baselineEntries = frozen.entries.map(row => row.baselineEntry);
  const dataset = buildEntryV2StrictPitPairedDataset({
    baselineEntries,
    dailyRecordsBySymbol,
    dailyBarsBySymbol,
    futureBarsBySymbol,
    marketByEntryTimestamp,
    universeBySymbol,
    sourceLineageByEntry,
    fixedExitId,
    fixedCapitalAllocationId,
    costAssumptions,
    roundTripCostBps,
    horizonsBars,
  });

  if (dataset.rowCount !== frozen.entryCount) {
    throw new Error('ENTRY_V2_EVIDENCE_DATASET_PAIR_COUNT_MISMATCH');
  }

  return Object.freeze({
    policy: ENTRY_V2_EVIDENCE_DATASET_POLICY,
    evidence: Object.freeze({
      sourceId: frozen.sourceId,
      evidenceSha256: frozen.evidenceSha256,
      entryCount: frozen.entryCount,
      candidateIds: Object.freeze(frozen.entries.map(row => row.candidateId)),
      contextBarsSha256: Object.freeze(frozen.entries.map(row => Object.freeze({
        candidateId: row.candidateId,
        sha256: row.contextBarsSha256,
      }))),
    }),
    dataset,
    status: 'ENTRY_V2_FROZEN_EVIDENCE_STRICT_PIT_DATASET_READY_NO_NEW_SIGNAL',
  });
}

export default {
  ENTRY_V2_EVIDENCE_DATASET_POLICY,
  buildEntryV2DatasetFromFrozenEvidence,
};
