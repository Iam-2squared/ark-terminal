import { simulateTradeManagementStateMachine } from './phase57-trade-management-state-machine.js';

export const PHASE57_P23_8_SAFETY = Object.freeze({
  mode: 'PHASE57_ENTRY_EXIT_QUALITY_EVALUATION_ONLY_RESEARCH',
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

export const P23_8_FORBIDDEN_DECISION_FEATURE_FRAGMENTS = Object.freeze([
  'future',
  'outcome',
  'mfe',
  'mae',
  'capture',
  'giveback',
  'entrylocalextrema',
  'exitfavorableextrema',
  'bottomtotop',
  'realizedextrema',
]);

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const mean = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

function quantile(values, q) {
  const rows = values.filter(Number.isFinite).slice().sort((a, b) => a - b);
  if (!rows.length) return null;
  if (rows.length === 1) return rows[0];
  const position = (rows.length - 1) * q;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return rows[lower];
  const weight = position - lower;
  return rows[lower] * (1 - weight) + rows[upper] * weight;
}

function distribution(values = []) {
  const rows = values.map(Number).filter(Number.isFinite);
  return Object.freeze({
    count: rows.length,
    mean: rows.length ? mean(rows) : null,
    p25: quantile(rows, 0.25),
    median: quantile(rows, 0.5),
    p75: quantile(rows, 0.75),
    min: rows.length ? Math.min(...rows) : null,
    max: rows.length ? Math.max(...rows) : null,
  });
}

function directionSign(direction) {
  if (direction === 1 || direction === 'LONG') return 1;
  if (direction === 0 || direction === -1 || direction === 'SHORT') return -1;
  throw new TypeError('signalDirection must be LONG/SHORT or 1/0');
}

function directionalReturnPct(entryPrice, price, sign) {
  return (Number(price) / Number(entryPrice) - 1) * 100 * sign;
}

function derivedExitPrice(entryPrice, grossReturnPct, sign) {
  return Number(entryPrice) * (1 + (Number(grossReturnPct) / 100) * sign);
}

function normalizeBar(raw) {
  const bar = {
    timestamp: new Date(raw?.timestamp ?? raw?.time ?? raw?.datetime).toISOString(),
    open: Number(raw?.open),
    high: Number(raw?.high),
    low: Number(raw?.low),
    close: Number(raw?.close),
  };
  if (![bar.open, bar.high, bar.low, bar.close].every(Number.isFinite)) throw new TypeError('quality bar OHLC must be finite');
  return Object.freeze(bar);
}

function fallbackExcursions(row, outcome, sign, exitPrice) {
  const entryPrice = Number(row.entryPrice);
  const outcomeAt = String(outcome?.outcomeAt ?? '');
  const bars = (Array.isArray(row?.futureBars) ? row.futureBars : [])
    .map(normalizeBar)
    .filter(bar => !outcomeAt || bar.timestamp <= outcomeAt)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));

  // For an intrabar stop we do not know whether that bar's high/low occurred before or after the fill.
  // Exclude the exit bar's extrema and include only the known exit price to avoid inventing path order.
  const excursionBars = outcome?.intrabarExit === true && outcomeAt
    ? bars.filter(bar => bar.timestamp < outcomeAt)
    : bars;
  const favorablePrices = [entryPrice, exitPrice, ...excursionBars.map(bar => sign === 1 ? bar.high : bar.low)];
  const adversePrices = [entryPrice, exitPrice, ...excursionBars.map(bar => sign === 1 ? bar.low : bar.high)];
  const favorable = sign === 1 ? Math.max(...favorablePrices) : Math.min(...favorablePrices);
  const adverse = sign === 1 ? Math.min(...adversePrices) : Math.max(...adversePrices);
  return Object.freeze({
    mfePct: Math.max(0, directionalReturnPct(entryPrice, favorable, sign)),
    maePct: Math.min(0, directionalReturnPct(entryPrice, adverse, sign)),
    intrabarExtremaConservative: outcome?.intrabarExit === true,
  });
}

export function assertNoEntryExitOutcomeLeakage(features = {}) {
  const keys = Object.keys(features ?? {});
  const violations = keys.filter(key => {
    const normalized = String(key).toLowerCase().replace(/[^a-z0-9]/g, '');
    return P23_8_FORBIDDEN_DECISION_FEATURE_FRAGMENTS.some(fragment => normalized.includes(fragment));
  });
  if (violations.length) throw new Error(`P23.8 evaluation-only leakage guard rejected feature keys: ${violations.join(',')}`);
  return true;
}

export function evaluateEntryExitQualityOutcome(row = {}, outcome = {}) {
  if (!finite(row?.entryPrice)) throw new TypeError('entryPrice is required');
  if (!finite(outcome?.grossReturnPct)) throw new TypeError('grossReturnPct is required');
  const sign = directionSign(row?.signalDirection);
  const entryPrice = Number(row.entryPrice);
  const grossReturnPct = Number(outcome.grossReturnPct);
  const exitPrice = finite(outcome?.exitPrice)
    ? Number(outcome.exitPrice)
    : derivedExitPrice(entryPrice, grossReturnPct, sign);
  const fallback = fallbackExcursions(row, outcome, sign, exitPrice);
  const mfePct = finite(outcome?.mfePct) ? Math.max(0, Number(outcome.mfePct)) : fallback.mfePct;
  const maePct = finite(outcome?.maePct) ? Math.min(0, Number(outcome.maePct)) : fallback.maePct;
  const entryLocalExtremaDistancePct = Math.max(0, -maePct);
  const profitGivebackPctPoints = Math.max(0, mfePct - grossReturnPct);
  const mfeCaptureRatio = mfePct > 0 ? grossReturnPct / mfePct : null;
  const idealTradeWindowRangePct = Math.max(0, mfePct - maePct);
  const bottomToTopCaptureRatio = idealTradeWindowRangePct > 0 ? grossReturnPct / idealTradeWindowRangePct : null;
  const entryRangeEfficiencyRatio = idealTradeWindowRangePct > 0 ? mfePct / idealTradeWindowRangePct : null;

  return Object.freeze({
    symbol: row?.symbol == null ? null : String(row.symbol),
    sessionDate: row?.sessionDate == null ? null : String(row.sessionDate),
    featureCutoff: row?.featureCutoff == null ? null : String(row.featureCutoff),
    direction: sign === 1 ? 'LONG' : 'SHORT',
    entryPrice,
    exitPrice,
    grossReturnPct,
    netReturnPct: finite(outcome?.netReturnPct) ? Number(outcome.netReturnPct) : null,
    barsHeld: finite(outcome?.barsHeld) ? Number(outcome.barsHeld) : null,
    exitReason: String(outcome?.exitReason ?? 'UNKNOWN'),
    outcomeAt: outcome?.outcomeAt == null ? null : String(outcome.outcomeAt),
    mfePct,
    maePct,
    entryLocalExtremaDistancePct,
    profitGivebackPctPoints,
    mfeCaptureRatio,
    idealTradeWindowRangePct,
    bottomToTopCaptureRatio,
    entryRangeEfficiencyRatio,
    intrabarExtremaConservative: fallback.intrabarExtremaConservative,
    evaluationOnly: true,
    futureExtremaUsedForDecision: false,
    eligibleForModelFeatures: false,
  });
}

function summarizeRecords(records = []) {
  const rows = Array.isArray(records) ? records : [];
  return Object.freeze({
    tradeCount: rows.length,
    mfePct: distribution(rows.map(row => row.mfePct)),
    maePct: distribution(rows.map(row => row.maePct)),
    entryLocalExtremaDistancePct: distribution(rows.map(row => row.entryLocalExtremaDistancePct)),
    profitGivebackPctPoints: distribution(rows.map(row => row.profitGivebackPctPoints)),
    mfeCaptureRatio: distribution(rows.map(row => row.mfeCaptureRatio)),
    bottomToTopCaptureRatio: distribution(rows.map(row => row.bottomToTopCaptureRatio)),
    entryRangeEfficiencyRatio: distribution(rows.map(row => row.entryRangeEfficiencyRatio)),
    grossReturnPct: distribution(rows.map(row => row.grossReturnPct)),
    netReturnPct: distribution(rows.map(row => row.netReturnPct)),
    averageHoldingBars: rows.length ? mean(rows.map(row => row.barsHeld).filter(Number.isFinite)) : null,
    positiveTradeFraction: rows.length ? rows.filter(row => Number(row.netReturnPct) > 0).length / rows.length : null,
  });
}

function groupedSummary(records, keyFn) {
  const groups = new Map();
  for (const record of records) {
    const key = String(keyFn(record));
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(record);
  }
  return Object.freeze(Object.fromEntries([...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([key, rows]) => [key, summarizeRecords(rows)])));
}

function stateMachineResult(nestedResult) {
  if (nestedResult?.outerOutcomes && nestedResult?.foldResults) return nestedResult;
  if (nestedResult?.stateMachine?.outerOutcomes && nestedResult?.stateMachine?.foldResults) return nestedResult.stateMachine;
  throw new Error('nested state-machine result with foldResults/outerOutcomes is required');
}

export function evaluateNestedEntryExitQuality({ rows = [], nestedResult } = {}) {
  const stateResult = stateMachineResult(nestedResult);
  const candidates = new Map((stateResult.candidateUniverse ?? []).map(candidate => [String(candidate.id), candidate.config]));
  const orderedRows = (Array.isArray(rows) ? rows : []).slice().sort((a, b) => {
    const dateCompare = String(a?.sessionDate ?? '').localeCompare(String(b?.sessionDate ?? ''));
    if (dateCompare) return dateCompare;
    const timeCompare = String(a?.featureCutoff ?? '').localeCompare(String(b?.featureCutoff ?? ''));
    if (timeCompare) return timeCompare;
    return String(a?.symbol ?? '').localeCompare(String(b?.symbol ?? ''));
  });
  const records = [];
  const foldDiagnostics = [];

  for (const fold of stateResult.foldResults ?? []) {
    if (!fold?.selectedCandidateId) continue;
    const config = candidates.get(String(fold.selectedCandidateId));
    if (!config) throw new Error(`missing selected candidate config: ${fold.selectedCandidateId}`);
    const testRows = orderedRows.filter(row => {
      const date = String(row?.sessionDate ?? '');
      return date >= String(fold.testStart) && date <= String(fold.testEnd);
    });
    const foldRecords = testRows.map(row => {
      const outcome = simulateTradeManagementStateMachine(row, { config });
      return Object.freeze({
        ...evaluateEntryExitQualityOutcome(row, outcome),
        outerFold: Number(fold.fold),
        candidateId: String(fold.selectedCandidateId),
      });
    });
    records.push(...foldRecords);
    foldDiagnostics.push(Object.freeze({
      outerFold: Number(fold.fold),
      candidateId: String(fold.selectedCandidateId),
      expectedSignalCount: Number(fold.testSignalCount ?? 0),
      replayedSignalCount: foldRecords.length,
      countMatches: Number(fold.testSignalCount ?? 0) === foldRecords.length,
      summary: summarizeRecords(foldRecords),
    }));
  }

  const expectedCount = Number(stateResult.outerOutcomes?.length ?? 0);
  const countReconciled = expectedCount === records.length && foldDiagnostics.every(fold => fold.countMatches);
  return Object.freeze({
    phase: '57.p23.8-entry-exit-quality',
    status: records.length ? 'ENTRY_EXIT_QUALITY_EVALUATED' : 'NO_ENTRY_EXIT_QUALITY_ROWS',
    expectedOuterOutcomeCount: expectedCount,
    evaluatedTradeCount: records.length,
    countReconciled,
    summary: summarizeRecords(records),
    bySymbol: groupedSummary(records, row => row.symbol ?? 'UNKNOWN'),
    byExitReason: groupedSummary(records, row => row.exitReason),
    byCandidate: groupedSummary(records, row => row.candidateId ?? 'UNKNOWN'),
    foldDiagnostics: Object.freeze(foldDiagnostics),
    records: Object.freeze(records),
    interpretation: Object.freeze({
      evaluationOnlyFutureExtrema: true,
      futureExtremaUsedForEntrySelection: false,
      futureExtremaUsedForExitSelection: false,
      futureExtremaEligibleAsModelFeatures: false,
      primaryPurpose: 'DIAGNOSE_ENTRY_LOCATION_AND_EXIT_PROFIT_CAPTURE',
      finalUntouchedOosEdgeClaimAllowed: false,
    }),
    edgeClaimAllowed: false,
    recommendationAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    paperTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    overnightHoldingAllowed: false,
    transmitted: false,
    safety: PHASE57_P23_8_SAFETY,
  });
}

export default {
  assertNoEntryExitOutcomeLeakage,
  evaluateEntryExitQualityOutcome,
  evaluateNestedEntryExitQuality,
};
