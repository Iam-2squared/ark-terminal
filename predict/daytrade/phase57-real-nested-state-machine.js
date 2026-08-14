import { evaluateNestedTradeManagementStateMachine, P23_5_PRESET_CONFIGS } from './phase57-nested-trade-management-selection.js';
import { simulateTradeManagementStateMachine } from './phase57-trade-management-state-machine.js';
import { evaluateRealDynamicExitOos, P23_3_FROZEN_DYNAMIC_CONFIG } from './phase57-real-dynamic-exit-oos.js';

export const PHASE57_P23_6_SAFETY = Object.freeze({
  mode: 'PHASE57_REAL_NESTED_STATE_MACHINE_READ_ONLY_RESEARCH',
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

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const mean = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

function selectedFoldForRow(row, foldResults = []) {
  const sessionDate = String(row?.sessionDate ?? '');
  return foldResults.find(fold => fold?.selectedCandidateId
    && sessionDate >= String(fold.testStart)
    && sessionDate <= String(fold.testEnd)) ?? null;
}

function rowIsInSelectedOuterFold(row, foldResults = []) {
  return selectedFoldForRow(row, foldResults) !== null;
}

function delta(a, b) {
  return finite(a) && finite(b) ? Number(a) - Number(b) : null;
}

function summarizeStateOutcomes(outcomes = []) {
  const rows = Array.isArray(outcomes) ? outcomes : [];
  const n = rows.length;
  const positive = rows.filter(row => Number(row.netReturnPct) > 0).reduce((sum, row) => sum + Number(row.netReturnPct), 0);
  const negative = -rows.filter(row => Number(row.netReturnPct) < 0).reduce((sum, row) => sum + Number(row.netReturnPct), 0);
  return Object.freeze({
    signalCount: n,
    hitRate: n ? rows.filter(row => Number(row.netReturnPct) > 0).length / n : null,
    netAverageReturnPct: n ? mean(rows.map(row => Number(row.netReturnPct))) : null,
    grossAverageReturnPct: n ? mean(rows.map(row => Number(row.grossReturnPct))) : null,
    profitFactor: negative > 0 ? positive / negative : (positive > 0 ? Infinity : null),
    averageHoldingBars: n ? mean(rows.map(row => Number(row.barsHeld))) : null,
    averageHoldingMinutes: n ? mean(rows.map(row => Number(row.barsHeld) * 5)) : null,
  });
}

function buildMatchedStateOutcomes(rows, nested) {
  return rows.map(row => {
    const fold = selectedFoldForRow(row, nested.foldResults);
    if (!fold?.selection?.selectedConfig) return null;
    const outcome = simulateTradeManagementStateMachine(row, { config: fold.selection.selectedConfig });
    if (!outcome) return null;
    return Object.freeze({
      symbol: String(row.symbol),
      sessionDate: String(row.sessionDate),
      featureCutoff: String(row.featureCutoff),
      outerFold: Number(fold.fold),
      selectedCandidateId: String(fold.selectedCandidateId),
      netReturnPct: outcome.netReturnPct,
      grossReturnPct: outcome.grossReturnPct,
      barsHeld: outcome.barsHeld,
      exitReason: outcome.exitReason,
      outcomeAt: outcome.outcomeAt,
    });
  }).filter(Boolean);
}

function perSymbolDiagnostics(matchedRows, matchedStateOutcomes, roundTripCostPct) {
  const symbols = [...new Set(matchedRows.map(row => String(row.symbol)))].sort();
  const diagnostics = {};
  for (const symbol of symbols) {
    const symbolRows = matchedRows.filter(row => String(row.symbol) === symbol);
    const stateOutcomes = matchedStateOutcomes.filter(row => row.symbol === symbol);
    if (stateOutcomes.length !== symbolRows.length) {
      throw new Error(`per-symbol state row reconciliation failed for ${symbol}: outcomes=${stateOutcomes.length} rows=${symbolRows.length}`);
    }
    const comparator = evaluateRealDynamicExitOos(symbolRows, {
      dynamicConfig: P23_3_FROZEN_DYNAMIC_CONFIG,
      roundTripCostPct,
    });
    if (comparator.pairedSignalCount !== symbolRows.length) {
      throw new Error(`per-symbol comparator reconciliation failed for ${symbol}: pairs=${comparator.pairedSignalCount} rows=${symbolRows.length}`);
    }
    const stateSummary = summarizeStateOutcomes(stateOutcomes);
    diagnostics[symbol] = Object.freeze({
      stateMachine: stateSummary,
      p23_3Dynamic: comparator.dynamic,
      priorFixedHorizonBaseline: comparator.matchedFixedBaseline,
      deltas: Object.freeze({
        stateMachineVsP23_3DynamicNetAverageReturnPct: delta(stateSummary.netAverageReturnPct, comparator.dynamic.netAverageReturnPct),
        stateMachineVsFixedBaselineNetAverageReturnPct: delta(stateSummary.netAverageReturnPct, comparator.matchedFixedBaseline.netAverageReturnPct),
      }),
      selectedCandidateCounts: Object.freeze(stateOutcomes.reduce((counts, outcome) => {
        counts[outcome.selectedCandidateId] = (counts[outcome.selectedCandidateId] || 0) + 1;
        return counts;
      }, {})),
      comparatorRowsUsedForSelection: false,
    });
  }
  return Object.freeze(diagnostics);
}

export function evaluateRealNestedStateMachine(rows = [], options = {}) {
  if (options?.allowOuterOutcomeSelection === true) throw new Error('outer outcome selection is forbidden');
  const input = Array.isArray(rows) ? rows : [];
  const roundTripCostPct = Number(options?.roundTripCostPct ?? 0.05);
  const nested = evaluateNestedTradeManagementStateMachine(input, {
    candidates: options?.candidates ?? P23_5_PRESET_CONFIGS,
    outerTrainFraction: options?.outerTrainFraction ?? 0.6,
    outerTestFraction: options?.outerTestFraction ?? 0.1,
    outerMinTrainSessions: options?.outerMinTrainSessions ?? 10,
    innerTrainFraction: options?.innerTrainFraction ?? 0.6,
    innerTestFraction: options?.innerTestFraction ?? 0.2,
    innerMinTrainSessions: options?.innerMinTrainSessions ?? 6,
    minInnerSignals: options?.minInnerSignals ?? 8,
    minInnerSignalBearingFolds: options?.minInnerSignalBearingFolds ?? 1,
  });

  const matchedRows = input.filter(row => rowIsInSelectedOuterFold(row, nested.foldResults));
  if (matchedRows.length !== nested.outerOutcomes.length) {
    throw new Error(`nested outer row reconciliation failed: rows=${matchedRows.length} outcomes=${nested.outerOutcomes.length}`);
  }

  const matchedStateOutcomes = buildMatchedStateOutcomes(matchedRows, nested);
  if (matchedStateOutcomes.length !== matchedRows.length) {
    throw new Error(`matched state replay reconciliation failed: outcomes=${matchedStateOutcomes.length} rows=${matchedRows.length}`);
  }
  const replayedStateSummary = summarizeStateOutcomes(matchedStateOutcomes);
  if (finite(nested.summary.netAverageReturnPct) && Math.abs(Number(replayedStateSummary.netAverageReturnPct) - Number(nested.summary.netAverageReturnPct)) > 1e-12) {
    throw new Error('matched state replay net expectancy does not reconcile to nested outer summary');
  }

  const comparator = evaluateRealDynamicExitOos(matchedRows, {
    dynamicConfig: P23_3_FROZEN_DYNAMIC_CONFIG,
    roundTripCostPct,
  });
  if (comparator.pairedSignalCount !== matchedRows.length) {
    throw new Error(`matched comparator reconciliation failed: pairs=${comparator.pairedSignalCount} rows=${matchedRows.length}`);
  }

  const perSymbol = perSymbolDiagnostics(matchedRows, matchedStateOutcomes, roundTripCostPct);

  return Object.freeze({
    phase: '57.p23.6-real-nested-state-machine',
    status: nested.outerOutcomes.length ? 'REAL_5M_NESTED_STATE_MACHINE_DEVELOPMENT_OOS_EVALUATED' : 'NO_REAL_NESTED_STATE_MACHINE_OUTCOMES',
    inputRowCount: input.length,
    inputSymbolCount: new Set(input.map(row => String(row.symbol))).size,
    matchedOuterTestRowCount: matchedRows.length,
    matchedOuterTestSymbolCount: Object.keys(perSymbol).length,
    stateMachine: nested,
    replayedStateSummary,
    perSymbol,
    matchedComparators: Object.freeze({
      p23_3Dynamic: comparator.dynamic,
      priorFixedHorizonBaseline: comparator.matchedFixedBaseline,
      pairedSignalCount: comparator.pairedSignalCount,
    }),
    deltas: Object.freeze({
      stateMachineVsP23_3DynamicNetAverageReturnPct: delta(nested.summary.netAverageReturnPct, comparator.dynamic.netAverageReturnPct),
      stateMachineVsFixedBaselineNetAverageReturnPct: delta(nested.summary.netAverageReturnPct, comparator.matchedFixedBaseline.netAverageReturnPct),
      stateMachineVsP23_3DynamicProfitFactor: delta(nested.summary.profitFactor, comparator.dynamic.profitFactor),
      stateMachineVsFixedBaselineProfitFactor: delta(nested.summary.profitFactor, comparator.matchedFixedBaseline.profitFactor),
      stateMachineVsP23_3DynamicAverageHoldingBars: delta(nested.summary.averageHoldingBars, comparator.dynamic.averageHoldingBars),
      stateMachineVsFixedBaselineAverageHoldingBars: delta(nested.summary.averageHoldingBars, comparator.matchedFixedBaseline.averageHoldingBars),
    }),
    selectionIntegrity: Object.freeze({
      ...nested.selectionIntegrity,
      matchedStateReplayUsesExactNestedOuterRows: matchedStateOutcomes.length === nested.outerOutcomes.length,
      matchedComparatorUsesExactNestedOuterRows: comparator.pairedSignalCount === nested.outerOutcomes.length,
      perSymbolDiagnosticsUseOnlyAlreadySelectedOuterRows: true,
      perSymbolDiagnosticsUsedForStateMachineConfigSelection: false,
      comparatorsUsedForStateMachineConfigSelection: false,
      priorP23_3ResultsUsedToPostSelectP23_6OuterOutcomes: false,
    }),
    interpretation: Object.freeze({
      primaryObjective: 'NET_EXPECTANCY_AFTER_EXPLICIT_COST',
      developmentNestedEvidenceOnly: true,
      reusedRecentResearchWindow: true,
      pooledCrossSymbolSelectionPreferredOverPerSymbolExitTuning: true,
      finalUntouchedOosEdgeClaimAllowed: false,
      fixedElapsedTimeIsComparatorOnly: true,
      p23_3DynamicIsComparatorOnly: true,
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
    safety: PHASE57_P23_6_SAFETY,
  });
}

export default { evaluateRealNestedStateMachine };
