import {
  DEFAULT_STATE_MACHINE_CONFIG,
  PHASE57_P23_4_SAFETY,
  simulateTradeManagementStateMachine,
} from './phase57-trade-management-state-machine.js';

export const PHASE57_P23_5_SAFETY = Object.freeze({
  ...PHASE57_P23_4_SAFETY,
  mode: 'PHASE57_NESTED_TRADE_MANAGEMENT_SELECTION_READ_ONLY_RESEARCH',
});

export const P23_5_PRESET_CONFIGS = Object.freeze([
  Object.freeze({
    id: 'STATE_BALANCED_V1',
    config: Object.freeze({ ...DEFAULT_STATE_MACHINE_CONFIG }),
  }),
  Object.freeze({
    id: 'STATE_PATIENT_TREND_V1',
    config: Object.freeze({
      ...DEFAULT_STATE_MACHINE_CONFIG,
      cautionExitDamageVotes: 5,
      cautionConfirmBars: 3,
      severeBreakdownConfirmBars: 2,
      minBarsBeforeStateExit: 3,
      healthyPullbackAtr: 1.75,
      profitProtectGivebackAtrStrong: 1.75,
      profitProtectGivebackAtrHold: 1.5,
      profitProtectGivebackAtrCaution: 1.0,
    }),
  }),
  Object.freeze({
    id: 'STATE_STRUCTURE_FIRST_V1',
    config: Object.freeze({
      ...DEFAULT_STATE_MACHINE_CONFIG,
      swingBars: 5,
      cautionEnterDamageVotes: 3,
      cautionExitDamageVotes: 5,
      cautionConfirmBars: 2,
      severeBreakdownDamageVotes: 4,
      severeBreakdownConfirmBars: 2,
      recoveryHealthyVotes: 5,
      healthyPullbackAtr: 2.0,
      minBarsBeforeStateExit: 3,
    }),
  }),
]);

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const mean = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

function normalizeCandidate(candidate, index) {
  const id = String(candidate?.id ?? `CANDIDATE_${index + 1}`).trim();
  if (!id) throw new Error('candidate id is required');
  return Object.freeze({
    id,
    config: Object.freeze({ ...DEFAULT_STATE_MACHINE_CONFIG, ...(candidate?.config ?? {}) }),
  });
}

function normalizeCandidates(candidates = P23_5_PRESET_CONFIGS) {
  const normalized = (Array.isArray(candidates) ? candidates : []).map(normalizeCandidate);
  if (!normalized.length) throw new Error('at least one trade-management candidate is required');
  const ids = normalized.map(candidate => candidate.id);
  if (new Set(ids).size !== ids.length) throw new Error('candidate ids must be unique');
  return Object.freeze(normalized);
}

function rowSessionDate(row) {
  if (row?.sessionDate == null) throw new Error('sessionDate is required for nested trade-management selection');
  return String(row.sessionDate);
}

function orderedRows(rows = []) {
  return (Array.isArray(rows) ? rows : []).slice().sort((a, b) => {
    const sessionCompare = rowSessionDate(a).localeCompare(rowSessionDate(b));
    if (sessionCompare) return sessionCompare;
    return String(a?.featureCutoff ?? '').localeCompare(String(b?.featureCutoff ?? ''));
  });
}

function uniqueSessions(rows = []) {
  return [...new Set(orderedRows(rows).map(rowSessionDate))].sort();
}

export function buildChronologicalSessionFolds(rows = [], options = {}) {
  const sessions = uniqueSessions(rows);
  const trainFraction = Math.min(0.9, Math.max(0.1, Number(options.trainFraction ?? 0.6)));
  const testFraction = Math.min(0.5, Math.max(0.05, Number(options.testFraction ?? 0.15)));
  const minTrainSessions = Math.max(1, Number(options.minTrainSessions ?? 6));
  if (sessions.length <= minTrainSessions) return Object.freeze([]);

  const initialTrain = Math.max(minTrainSessions, Math.floor(sessions.length * trainFraction));
  const testSize = Math.max(1, Math.floor(sessions.length * testFraction));
  const folds = [];
  let fold = 0;
  for (let testStart = initialTrain; testStart < sessions.length; testStart += testSize) {
    const trainSessions = sessions.slice(0, testStart);
    const testSessions = sessions.slice(testStart, Math.min(sessions.length, testStart + testSize));
    if (!testSessions.length) continue;
    if (trainSessions.at(-1) >= testSessions[0]) throw new Error('chronological session separation failed');
    folds.push(Object.freeze({
      fold,
      trainSessions: Object.freeze(trainSessions),
      testSessions: Object.freeze(testSessions),
      trainStart: trainSessions[0],
      trainEnd: trainSessions.at(-1),
      testStart: testSessions[0],
      testEnd: testSessions.at(-1),
    }));
    fold += 1;
  }
  return Object.freeze(folds);
}

function rowsForSessions(rows, sessions) {
  const allowed = new Set(sessions);
  return orderedRows(rows).filter(row => allowed.has(rowSessionDate(row)));
}

function outcomeSummary(outcomes = []) {
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
  });
}

function simulateRows(rows, candidate) {
  return orderedRows(rows).map(row => {
    const outcome = simulateTradeManagementStateMachine(row, { config: candidate.config });
    if (!outcome) return null;
    return Object.freeze({
      candidateId: candidate.id,
      sessionDate: rowSessionDate(row),
      featureCutoff: row?.featureCutoff == null ? null : String(row.featureCutoff),
      netReturnPct: outcome.netReturnPct,
      grossReturnPct: outcome.grossReturnPct,
      barsHeld: outcome.barsHeld,
      exitReason: outcome.exitReason,
      outcomeAt: outcome.outcomeAt,
    });
  }).filter(Boolean);
}

function compareCandidateScores(a, b) {
  const netA = finite(a?.summary?.netAverageReturnPct) ? Number(a.summary.netAverageReturnPct) : -Infinity;
  const netB = finite(b?.summary?.netAverageReturnPct) ? Number(b.summary.netAverageReturnPct) : -Infinity;
  if (netA !== netB) return netB - netA;
  const pfA = finite(a?.summary?.profitFactor) ? Number(a.summary.profitFactor) : -Infinity;
  const pfB = finite(b?.summary?.profitFactor) ? Number(b.summary.profitFactor) : -Infinity;
  if (pfA !== pfB) return pfB - pfA;
  return String(a.candidateId).localeCompare(String(b.candidateId));
}

export function selectTradeManagementConfigInner(outerTrainRows = [], candidates = P23_5_PRESET_CONFIGS, options = {}) {
  const normalizedCandidates = normalizeCandidates(candidates);
  const innerFolds = buildChronologicalSessionFolds(outerTrainRows, {
    trainFraction: options.innerTrainFraction ?? 0.6,
    testFraction: options.innerTestFraction ?? 0.2,
    minTrainSessions: options.innerMinTrainSessions ?? 6,
  });
  const minSignals = Math.max(1, Number(options.minInnerSignals ?? 8));
  const minSignalBearingFolds = Math.max(1, Number(options.minInnerSignalBearingFolds ?? 1));

  const candidateScores = normalizedCandidates.map(candidate => {
    const outcomes = [];
    let signalBearingFolds = 0;
    const validationFolds = [];
    for (const fold of innerFolds) {
      const validationRows = rowsForSessions(outerTrainRows, fold.testSessions);
      const foldOutcomes = simulateRows(validationRows, candidate);
      if (foldOutcomes.length) signalBearingFolds += 1;
      outcomes.push(...foldOutcomes);
      validationFolds.push(Object.freeze({
        fold: fold.fold,
        trainEnd: fold.trainEnd,
        validationStart: fold.testStart,
        validationEnd: fold.testEnd,
        signalCount: foldOutcomes.length,
        summary: outcomeSummary(foldOutcomes),
      }));
    }
    const summary = outcomeSummary(outcomes);
    const eligible = outcomes.length >= minSignals && signalBearingFolds >= minSignalBearingFolds;
    return Object.freeze({
      candidateId: candidate.id,
      config: candidate.config,
      eligible,
      signalBearingFolds,
      summary,
      validationFolds: Object.freeze(validationFolds),
    });
  });

  const eligible = candidateScores.filter(score => score.eligible).sort(compareCandidateScores);
  const selected = eligible[0] ?? null;
  return Object.freeze({
    phase: '57.p23.5-inner-selection',
    status: selected ? 'INNER_STATE_MACHINE_CONFIG_SELECTED' : 'NO_ELIGIBLE_INNER_STATE_MACHINE_CONFIG',
    selectedCandidateId: selected?.candidateId ?? null,
    selectedConfig: selected?.config ?? null,
    innerFoldCount: innerFolds.length,
    candidateScores: Object.freeze(candidateScores),
    objective: 'NET_EXPECTANCY_AFTER_EXPLICIT_COST',
    outerRowsUsedForSelection: false,
    edgeClaimAllowed: false,
    recommendationAllowed: false,
    executionAllowed: false,
    safety: PHASE57_P23_5_SAFETY,
  });
}

export function evaluateNestedTradeManagementStateMachine(rows = [], options = {}) {
  if (options?.allowOuterOutcomeSelection === true) throw new Error('outer outcome selection is forbidden');
  const normalizedCandidates = normalizeCandidates(options?.candidates ?? P23_5_PRESET_CONFIGS);
  const ordered = orderedRows(rows);
  const outerFolds = buildChronologicalSessionFolds(ordered, {
    trainFraction: options.outerTrainFraction ?? 0.6,
    testFraction: options.outerTestFraction ?? 0.1,
    minTrainSessions: options.outerMinTrainSessions ?? 10,
  });
  const foldResults = [];
  const outerOutcomes = [];
  const selectedCandidateCounts = {};

  for (const fold of outerFolds) {
    const outerTrainRows = rowsForSessions(ordered, fold.trainSessions);
    const outerTestRows = rowsForSessions(ordered, fold.testSessions);
    const selection = selectTradeManagementConfigInner(outerTrainRows, normalizedCandidates, options);
    if (!selection.selectedCandidateId || !selection.selectedConfig) {
      foldResults.push(Object.freeze({
        fold: fold.fold,
        trainEnd: fold.trainEnd,
        testStart: fold.testStart,
        testEnd: fold.testEnd,
        selectedCandidateId: null,
        testSignalCount: 0,
        summary: outcomeSummary([]),
        selection,
        outerOutcomesUsedForSelection: false,
      }));
      continue;
    }
    selectedCandidateCounts[selection.selectedCandidateId] = (selectedCandidateCounts[selection.selectedCandidateId] || 0) + 1;
    const candidate = Object.freeze({ id: selection.selectedCandidateId, config: selection.selectedConfig });
    const testOutcomes = simulateRows(outerTestRows, candidate).map(outcome => Object.freeze({ ...outcome, outerFold: fold.fold }));
    outerOutcomes.push(...testOutcomes);
    foldResults.push(Object.freeze({
      fold: fold.fold,
      trainStart: fold.trainStart,
      trainEnd: fold.trainEnd,
      testStart: fold.testStart,
      testEnd: fold.testEnd,
      selectedCandidateId: selection.selectedCandidateId,
      testSignalCount: testOutcomes.length,
      summary: outcomeSummary(testOutcomes),
      selection,
      outerOutcomesUsedForSelection: false,
    }));
  }

  const summary = outcomeSummary(outerOutcomes);
  const signalBearingFolds = foldResults.filter(fold => fold.testSignalCount > 0);
  const positiveFoldFraction = signalBearingFolds.length
    ? signalBearingFolds.filter(fold => Number(fold.summary.netAverageReturnPct) > 0).length / signalBearingFolds.length
    : null;

  return Object.freeze({
    phase: '57.p23.5-nested-state-machine-selection',
    status: outerOutcomes.length ? 'NESTED_STATE_MACHINE_OUTER_EVALUATED' : 'NO_NESTED_STATE_MACHINE_OUTER_OUTCOMES',
    rowCount: ordered.length,
    sessionCount: uniqueSessions(ordered).length,
    candidateUniverse: Object.freeze(normalizedCandidates.map(candidate => Object.freeze({ id: candidate.id, config: candidate.config }))),
    outerFoldCount: outerFolds.length,
    signalBearingOuterFoldCount: signalBearingFolds.length,
    selectedCandidateCounts: Object.freeze(selectedCandidateCounts),
    summary,
    positiveOuterFoldFraction: positiveFoldFraction,
    foldResults: Object.freeze(foldResults),
    outerOutcomes: Object.freeze(outerOutcomes),
    objective: 'NET_EXPECTANCY_AFTER_EXPLICIT_COST',
    selectionIntegrity: Object.freeze({
      sessionSeparatedChronologically: true,
      innerValidationUsesOnlyOuterTrainSessions: true,
      outerTestSessionsStrictlyAfterOuterTrainSessions: outerFolds.every(fold => fold.trainEnd < fold.testStart),
      outerOutcomesUsedForConfigSelection: false,
      postSelectionAcrossOuterResultsAllowed: false,
      candidateUniverseFrozenBeforeOuterEvaluation: true,
    }),
    interpretation: Object.freeze({
      developmentNestedEvidenceOnly: true,
      finalUntouchedOosEdgeClaimAllowed: false,
      primaryObjective: 'NET_EXPECTANCY_AFTER_EXPLICIT_COST',
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
    safety: PHASE57_P23_5_SAFETY,
  });
}

export default {
  P23_5_PRESET_CONFIGS,
  buildChronologicalSessionFolds,
  selectTradeManagementConfigInner,
  evaluateNestedTradeManagementStateMachine,
};
