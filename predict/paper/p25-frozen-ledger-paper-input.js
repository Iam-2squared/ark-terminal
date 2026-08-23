import { P25_SIGNAL_INTENT_SAFETY } from './p25-signal-intent-adapter.js';

export const P25_FROZEN_LEDGER_PAPER_INPUT_VERSION = 'p25-frozen-ledger-paper-input-v1';

function timestampOf(bar) {
  const value = bar?.timestamp ?? bar?.time ?? bar?.datetime ?? bar?.date ?? bar?.at ?? null;
  const ms = Date.parse(String(value ?? ''));
  return Number.isFinite(ms) ? ms : null;
}

function closeOf(bar) {
  const value = bar?.close ?? bar?.c ?? null;
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function normalizeBars(container, symbol) {
  const value = container?.[symbol] ?? container?.[String(symbol).toUpperCase()] ?? [];
  const bars = Array.isArray(value) ? value : Array.isArray(value?.bars) ? value.bars : [];
  return bars
    .map(bar => ({ bar, timestampMs: timestampOf(bar), close: closeOf(bar) }))
    .filter(row => row.timestampMs !== null && row.close !== null)
    .sort((a, b) => a.timestampMs - b.timestampMs);
}

function pointInTimeReferencePrice(bars, entryTimestamp) {
  const entryMs = Date.parse(String(entryTimestamp ?? ''));
  if (!Number.isFinite(entryMs)) throw new Error('entryTimestamp is invalid.');
  const eligible = bars.filter(row => row.timestampMs <= entryMs);
  if (!eligible.length) throw new Error('no point-in-time reference bar available at or before entryTimestamp.');
  const selected = eligible[eligible.length - 1];
  if (selected.timestampMs > entryMs) throw new Error('future bar selected for Paper reference price.');
  return Object.freeze({
    referencePrice: selected.close,
    referenceTimestamp: new Date(selected.timestampMs).toISOString(),
  });
}

function directionOf(row) {
  if (row?.direction === 'LONG' || Number(row?.signalDirection) === 1) return 'UP';
  if (row?.direction === 'SHORT' || Number(row?.signalDirection) === -1) return 'DOWN';
  throw new Error(`unsupported frozen trade direction for ${row?.symbol ?? 'UNKNOWN'}`);
}

export function buildP25ResearchPaperInputs({
  frozenLedger,
  sessionBarsBySymbol = {},
  lineageHeadSha256,
  universeVariant = 'PRECOMMITTED_FROZEN_LEDGER',
} = {}) {
  if (!frozenLedger || !Array.isArray(frozenLedger.frozenTrades)) throw new Error('frozenLedger.frozenTrades is required.');
  const lineage = String(lineageHeadSha256 ?? '').trim();
  if (!lineage) throw new Error('lineageHeadSha256 is required.');
  for (const [key, value] of Object.entries(P25_SIGNAL_INTENT_SAFETY)) {
    if (value !== false) throw new Error(`Paper input safety violation: ${key}`);
  }

  const rows = frozenLedger.frozenTrades.map((trade, index) => {
    if (trade?.frozenBeforeOutcome !== true || trade?.currentOutcomeUsed !== false) {
      throw new Error(`frozen outcome-free trade required at index ${index}`);
    }
    const symbol = String(trade.symbol ?? '').trim().toUpperCase();
    if (!symbol) throw new Error(`symbol missing at frozen trade index ${index}`);
    const entryTimestamp = String(trade.entryTimestamp ?? trade.featureCutoff ?? '').trim();
    const bars = normalizeBars(sessionBarsBySymbol, symbol);
    const reference = pointInTimeReferencePrice(bars, entryTimestamp);
    const signalId = `${trade.sessionDate ?? 'session'}|${entryTimestamp}|${symbol}`;
    return Object.freeze({
      signal: Object.freeze({
        signalId,
        evidenceDate: String(trade.sessionDate ?? ''),
        sourceTimestamp: entryTimestamp,
        symbol,
        direction: directionOf(trade),
        universeVariant: String(universeVariant),
        modelVersion: String(trade.modelId ?? 'frozen-p25'),
        lineageHeadSha256: lineage,
        confidence: trade.confidence ?? null,
        score: trade.probability ?? null,
        setup: trade.selectedFeatureFamily ?? null,
        metadata: Object.freeze({
          frozenBeforeOutcome: true,
          currentOutcomeUsed: false,
          variantMemberships: Object.freeze([...(trade.variantMemberships ?? [])]),
          baseHorizonBars: trade.baseHorizonBars ?? null,
          artifactSha256: trade.artifactSha256 ?? null,
          selectedThreshold: trade.selectedThreshold ?? null,
          referenceTimestamp: reference.referenceTimestamp,
        }),
      }),
      referencePrice: reference.referencePrice,
      referenceTimestamp: reference.referenceTimestamp,
    });
  });

  return Object.freeze({
    version: P25_FROZEN_LEDGER_PAPER_INPUT_VERSION,
    mode: 'research_offline_only',
    executable: false,
    inputCount: rows.length,
    rows: Object.freeze(rows),
    safety: P25_SIGNAL_INTENT_SAFETY,
    methodology: Object.freeze({
      sourceFrozenBeforeOutcome: true,
      currentOutcomeUsed: false,
      referencePricePointInTimeOnly: true,
      futureBarSelectionAllowed: false,
      modelOrEntrySelectionChanged: false,
      freshHoldoutConsumed: false,
    }),
  });
}

export const P25FrozenLedgerPaperInputInternals = Object.freeze({ timestampOf, closeOf, normalizeBars, pointInTimeReferencePrice, directionOf });
