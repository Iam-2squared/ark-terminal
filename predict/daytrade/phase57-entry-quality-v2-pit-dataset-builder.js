import {
  buildStrictPointInTimeEntryV2ResearchVector,
} from './phase57-entry-quality-v2-point-in-time.js';
import {
  buildEntryQualityV2PathLabels,
} from './phase57-entry-quality-v2-labels.js';
import {
  buildEntryQualityV2PairedRow,
  buildEntryQualityV2PairedDataset,
} from './phase57-entry-quality-v2-paired-dataset.js';
import {
  buildEntryV2PriorDailyHistoryFeed,
} from './phase57-entry-quality-v2-daily-history-feed.js';

export const ENTRY_V2_PIT_DATASET_POLICY = Object.freeze({
  mode: 'ENTRY_V2_STRICT_PIT_PAIRED_DATASET_RESEARCH_ONLY',
  baselineIntradayContextIsCanonical: true,
  dailyMustBePriorSessionOnly: true,
  dailyHistoryResolvedPerEntryTimestamp: true,
  futureLabelsOfflineOnly: true,
  selectorChangesAllowed: false,
  exitChangesAllowed: false,
  capitalAllocationChangesAllowed: false,
  automaticPromotionAllowed: false,
});

function sym(value) {
  return String(value ?? '').trim().toUpperCase();
}

function sourceRows(source, symbol) {
  if (source instanceof Map) {
    return source.get(symbol) ?? source.get(symbol.replace(/\.T$/, '')) ?? [];
  }
  return source?.[symbol] ?? source?.[symbol.replace(/\.T$/, '')] ?? [];
}

function keyed(source, key, fallback = {}) {
  if (source instanceof Map) return source.get(key) ?? fallback;
  return source?.[key] ?? fallback;
}

function assertBaselineEntry(entry) {
  if (!entry || entry.entryAccepted !== true) throw new Error('ENTRY_V2_BUILDER_BASELINE_ENTRY_REQUIRED');
  if (!entry.entryTimestamp) throw new Error('ENTRY_V2_BUILDER_ENTRY_TIMESTAMP_REQUIRED');
  if (!Array.isArray(entry.contextBars) || !entry.contextBars.length) {
    throw new Error('ENTRY_V2_BUILDER_BASELINE_CONTEXT_BARS_REQUIRED');
  }
  if (entry.frozenBeforeOutcome !== true || entry.currentOutcomeUsed !== false) {
    throw new Error('ENTRY_V2_BUILDER_BASELINE_NOT_CAUSAL');
  }
}

function sortBaselineEntries(entries) {
  return [...entries].sort((a, b) => {
    const at = Date.parse(a.entryTimestamp) - Date.parse(b.entryTimestamp);
    if (at !== 0) return at;
    const symbolCompare = sym(a.symbol).localeCompare(sym(b.symbol));
    if (symbolCompare !== 0) return symbolCompare;
    return String(a.selectionLineage?.variant ?? '').localeCompare(String(b.selectionLineage?.variant ?? ''));
  });
}

function resolveDailyInput({ dailyBarsBySymbol, dailyRecordsBySymbol, symbol, asOf }) {
  const rawRecords = sourceRows(dailyRecordsBySymbol, symbol);
  if (Array.isArray(rawRecords) && rawRecords.length) {
    const feed = buildEntryV2PriorDailyHistoryFeed({ symbol, asOf, records: rawRecords });
    return Object.freeze({
      bars: feed.bars,
      lineage: feed.lineage,
      sourceFingerprintSha256: feed.sourceFingerprintSha256,
      retainedBarsFingerprintSha256: feed.retainedBarsFingerprintSha256,
      mode: 'PERSISTED_DAILY_RECORDS_RESOLVED_PER_ENTRY',
    });
  }

  const bars = sourceRows(dailyBarsBySymbol, symbol);
  return Object.freeze({
    bars,
    lineage: null,
    sourceFingerprintSha256: null,
    retainedBarsFingerprintSha256: null,
    mode: 'PREBUILT_DAILY_BARS_COMPATIBILITY',
  });
}

/**
 * Build a leakage-separated paired research dataset from already-frozen P21 Entry candidates.
 *
 * Critical invariant: NEW research intraday features are built from baselineEntry.contextBars,
 * not from an independently fetched intraday series. This makes the OLD/NEW current market
 * data prefix identical by construction.
 *
 * Daily context may be supplied as persisted Phase50/Phase45 records. When records are supplied,
 * the prior-session prefix is resolved separately for every Entry timestamp, preventing a later
 * session's daily bar from leaking into an earlier candidate in a multi-day dataset. Prebuilt
 * dailyBarsBySymbol remains as a compatibility path and is still checked by the strict PIT layer.
 * Future bars are used only by the offline label builder after the feature vector is frozen.
 */
export function buildEntryV2StrictPitPairedDataset({
  baselineEntries = [],
  dailyBarsBySymbol = {},
  dailyRecordsBySymbol = {},
  futureBarsBySymbol = {},
  marketByEntryTimestamp = {},
  universeBySymbol = {},
  fixedExitId,
  fixedCapitalAllocationId,
  costAssumptions,
  roundTripCostBps = 0,
  horizonsBars = [1, 2, 3, 6, 12],
} = {}) {
  if (!Array.isArray(baselineEntries) || !baselineEntries.length) {
    throw new Error('ENTRY_V2_BUILDER_BASELINE_ENTRIES_REQUIRED');
  }
  if (!fixedExitId || !fixedCapitalAllocationId) {
    throw new Error('ENTRY_V2_BUILDER_FIXED_EXPERIMENT_IDS_REQUIRED');
  }
  if (!costAssumptions || typeof costAssumptions !== 'object') {
    throw new Error('ENTRY_V2_BUILDER_COST_ASSUMPTIONS_REQUIRED');
  }

  const previousIntradayBySymbol = new Map();
  const pairedRows = [];

  for (const baselineEntry of sortBaselineEntries(baselineEntries)) {
    assertBaselineEntry(baselineEntry);
    const symbol = sym(baselineEntry.symbol);
    if (!symbol) throw new Error('ENTRY_V2_BUILDER_SYMBOL_REQUIRED');

    const asOf = baselineEntry.entryTimestamp;
    const market = keyed(marketByEntryTimestamp, asOf, {});
    const universe = keyed(universeBySymbol, symbol, {});
    const dailyInput = resolveDailyInput({
      dailyBarsBySymbol,
      dailyRecordsBySymbol,
      symbol,
      asOf,
    });

    const researchVector = buildStrictPointInTimeEntryV2ResearchVector({
      symbol,
      asOf,
      dailyBars: dailyInput.bars,
      intradayBars: baselineEntry.contextBars,
      market,
      universe,
      previousIntradayContext: previousIntradayBySymbol.get(symbol) ?? null,
    });

    if (researchVector.pointInTime?.strict !== true || researchVector.pointInTime?.futureOutcomeUsed !== false) {
      throw new Error('ENTRY_V2_BUILDER_PIT_ATTESTATION_FAILED');
    }

    // Only after the current feature vector is frozen do we construct future path labels.
    const pathLabels = buildEntryQualityV2PathLabels({
      entryTimestamp: asOf,
      entryPrice: baselineEntry.entryPrice,
      futureBars: sourceRows(futureBarsBySymbol, symbol),
      horizonsBars,
      roundTripCostBps,
    });

    const pairedRow = buildEntryQualityV2PairedRow({
      baselineEntry,
      researchVector,
      pathLabels,
      costAssumptions,
      fixedExitId,
      fixedCapitalAllocationId,
    });

    pairedRows.push(Object.freeze({
      ...pairedRow,
      lineage: Object.freeze({
        baselineIntradayContextIsCanonical: true,
        baselineContextBarCount: baselineEntry.contextBars.length,
        dailySourceBars: dailyInput.bars.length,
        dailyResolutionMode: dailyInput.mode,
        dailyHistoryLineage: dailyInput.lineage,
        dailySourceFingerprintSha256: dailyInput.sourceFingerprintSha256,
        dailyRetainedBarsFingerprintSha256: dailyInput.retainedBarsFingerprintSha256,
        futureLabelSourceBars: sourceRows(futureBarsBySymbol, symbol).length,
        featureFrozenBeforeOfflineLabels: true,
      }),
    }));

    previousIntradayBySymbol.set(symbol, researchVector.intraday);
  }

  const dataset = buildEntryQualityV2PairedDataset(pairedRows);
  return Object.freeze({
    ...dataset,
    builderPolicy: ENTRY_V2_PIT_DATASET_POLICY,
    controls: Object.freeze({
      fixedExitId: String(fixedExitId),
      fixedCapitalAllocationId: String(fixedCapitalAllocationId),
      costAssumptions: Object.freeze({ ...costAssumptions }),
      roundTripCostBps: Number(roundTripCostBps),
      horizonsBars: Object.freeze([...horizonsBars]),
    }),
    status: 'STRICT_PIT_PAIRED_RESEARCH_DATASET_NO_NEW_SIGNAL',
  });
}

export default {
  ENTRY_V2_PIT_DATASET_POLICY,
  buildEntryV2StrictPitPairedDataset,
};
