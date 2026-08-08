import {
  DEFAULT_PHASE55_COST_POLICY,
  evaluatePhase55IntradayOos,
} from './phase55-intraday-oos-cost-model.js';

export const PHASE55_2_SAFETY = Object.freeze({
  mode: 'INTRADAY_OOS_ROBUSTNESS_READ_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

export const DEFAULT_PHASE55_2_POLICY = Object.freeze({
  foldCount: 4,
  minimumRowsPerFold: 10,
  minimumPassingFolds: 3,
  maximumFailingStressScenarios: 1,
  stressMultipliers: Object.freeze([1, 1.5, 2]),
});

function finite(value) {
  return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
}

function sortRows(rows = []) {
  return [...rows].sort((a, b) => {
    const first = String(a?.sessionDate || a?.date || '');
    const second = String(b?.sessionDate || b?.date || '');
    return first.localeCompare(second) || String(a?.id || '').localeCompare(String(b?.id || ''));
  });
}

function splitChronological(rows, foldCount) {
  const sorted = sortRows(rows);
  const folds = [];
  const count = Math.max(1, Number(foldCount) || 4);
  for (let index = 0; index < count; index += 1) {
    const start = Math.floor((sorted.length * index) / count);
    const end = Math.floor((sorted.length * (index + 1)) / count);
    folds.push(sorted.slice(start, end));
  }
  return folds.filter((fold) => fold.length);
}

function stressedCostPolicy(basePolicy, multiplier) {
  const base = { ...DEFAULT_PHASE55_COST_POLICY, ...(basePolicy || {}) };
  return Object.freeze({
    ...base,
    spreadBps: Number(base.spreadBps) * multiplier,
    slippageBps: Number(base.slippageBps) * multiplier,
    latencyBps: Number(base.latencyBps) * multiplier,
    liquidityPenaltyBps: Number(base.liquidityPenaltyBps) * multiplier,
  });
}

function foldPass(result) {
  return Boolean(
    result?.benchmark &&
    result.strategy?.profitFactor > 1 &&
    result.strategy?.sharpe > 0 &&
    result.strategy?.maxDrawdown < 0.35 &&
    finite(result.benchmarkExcessReturn) &&
    Number(result.benchmarkExcessReturn) > 0
  );
}

export function evaluatePhase55IntradayRobustness({
  rows = [],
  threshold = 0.55,
  benchmarkReturns = [],
  costPolicy = {},
  policy = {},
} = {}) {
  const resolved = { ...DEFAULT_PHASE55_2_POLICY, ...(policy || {}) };
  const sortedRows = sortRows(rows);
  const sortedBenchmark = Array.isArray(benchmarkReturns) ? [...benchmarkReturns] : [];
  const folds = splitChronological(sortedRows, resolved.foldCount);
  const minimumRowsPerFold = Math.max(2, Number(resolved.minimumRowsPerFold) || 10);

  const foldResults = folds.map((fold, foldIndex) => {
    const start = sortedRows.indexOf(fold[0]);
    const benchmarkSlice = sortedBenchmark.length === sortedRows.length
      ? sortedBenchmark.slice(start, start + fold.length)
      : [];

    if (fold.length < minimumRowsPerFold) {
      return Object.freeze({
        fold: foldIndex + 1,
        rowCount: fold.length,
        status: 'INSUFFICIENT_ROWS',
        passed: false,
        result: null,
      });
    }

    const result = evaluatePhase55IntradayOos({
      rows: fold,
      threshold,
      costPolicy,
      benchmarkReturns: benchmarkSlice,
    });

    return Object.freeze({
      fold: foldIndex + 1,
      rowCount: fold.length,
      status: 'EVALUATED',
      passed: foldPass(result),
      result,
    });
  });

  const passingFolds = foldResults.filter((item) => item.passed).length;
  const usableFolds = foldResults.filter((item) => item.status === 'EVALUATED').length;

  const stressResults = (resolved.stressMultipliers || [1, 1.5, 2]).map((multiplier) => {
    const result = evaluatePhase55IntradayOos({
      rows: sortedRows,
      threshold,
      costPolicy: stressedCostPolicy(costPolicy, Number(multiplier)),
      benchmarkReturns: sortedBenchmark,
    });
    return Object.freeze({
      multiplier: Number(multiplier),
      passed: foldPass(result),
      result,
    });
  });

  const failingStressScenarios = stressResults.filter((item) => !item.passed).length;
  const blockers = [];

  if (usableFolds < Number(resolved.minimumPassingFolds)) blockers.push('INSUFFICIENT_USABLE_FOLDS');
  if (passingFolds < Number(resolved.minimumPassingFolds)) blockers.push('FOLD_STABILITY_NOT_PROVEN');
  if (failingStressScenarios > Number(resolved.maximumFailingStressScenarios)) blockers.push('COST_STRESS_FRAGILE');
  if (sortedBenchmark.length !== sortedRows.length) blockers.push('BENCHMARK_MISSING_OR_MISALIGNED');

  return Object.freeze({
    phase: '55.2',
    status: blockers.length ? 'OBSERVE' : 'ROBUSTNESS_REVIEW_CANDIDATE',
    foldCount: foldResults.length,
    usableFolds,
    passingFolds,
    failingStressScenarios,
    foldResults: Object.freeze(foldResults),
    stressResults: Object.freeze(stressResults),
    blockers: Object.freeze([...new Set(blockers)]),
    promotionEligible: blockers.length === 0,
    automaticPromotionAllowed: false,
    reviewOnly: true,
    transmitted: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    safety: PHASE55_2_SAFETY,
  });
}
