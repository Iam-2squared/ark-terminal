import { evaluateNestedTradeManagementStateMachine, P23_5_PRESET_CONFIGS } from './phase57-nested-trade-management-selection.js';
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

function rowIsInSelectedOuterFold(row, foldResults = []) {
  const sessionDate = String(row?.sessionDate ?? '');
  return foldResults.some(fold => fold?.selectedCandidateId
    && sessionDate >= String(fold.testStart)
    && sessionDate <= String(fold.testEnd));
}

function delta(a, b) {
  return finite(a) && finite(b) ? Number(a) - Number(b) : null;
}

export function evaluateRealNestedStateMachine(rows = [], options = {}) {
  if (options?.allowOuterOutcomeSelection === true) throw new Error('outer outcome selection is forbidden');
  const input = Array.isArray(rows) ? rows : [];
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

  const comparator = evaluateRealDynamicExitOos(matchedRows, {
    dynamicConfig: P23_3_FROZEN_DYNAMIC_CONFIG,
    roundTripCostPct: Number(options?.roundTripCostPct ?? 0.05),
  });
  if (comparator.pairedSignalCount !== matchedRows.length) {
    throw new Error(`matched comparator reconciliation failed: pairs=${comparator.pairedSignalCount} rows=${matchedRows.length}`);
  }

  return Object.freeze({
    phase: '57.p23.6-real-nested-state-machine',
    status: nested.outerOutcomes.length ? 'REAL_5M_NESTED_STATE_MACHINE_DEVELOPMENT_OOS_EVALUATED' : 'NO_REAL_NESTED_STATE_MACHINE_OUTCOMES',
    inputRowCount: input.length,
    matchedOuterTestRowCount: matchedRows.length,
    stateMachine: nested,
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
      matchedComparatorUsesExactNestedOuterRows: comparator.pairedSignalCount === nested.outerOutcomes.length,
      comparatorsUsedForStateMachineConfigSelection: false,
      priorP23_3ResultsUsedToPostSelectP23_6OuterOutcomes: false,
    }),
    interpretation: Object.freeze({
      primaryObjective: 'NET_EXPECTANCY_AFTER_EXPLICIT_COST',
      developmentNestedEvidenceOnly: true,
      reusedRecentResearchWindow: true,
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
