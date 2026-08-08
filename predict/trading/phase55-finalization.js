import { evaluatePhase55IntradayRobustness } from './phase55-intraday-oos-robustness.js';

export const PHASE55_X_SAFETY = Object.freeze({
  mode: 'INTRADAY_OOS_FINAL_REVIEW_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  paperTradingAllowed: false,
  humanApprovalRequired: true,
});

export const DEFAULT_PHASE55_X_POLICY = Object.freeze({
  minimumPassingFolds: 3,
  minimumUsableFolds: 3,
  maximumFailingStressScenarios: 1,
  requireBenchmark: true,
});

export function evaluatePhase55Finalization({ rows = [], benchmarkReturns = [], threshold = 0.55, costPolicy = {}, robustnessPolicy = {}, finalPolicy = {} } = {}) {
  const resolved = { ...DEFAULT_PHASE55_X_POLICY, ...(finalPolicy || {}) };
  const robustness = evaluatePhase55IntradayRobustness({
    rows,
    benchmarkReturns,
    threshold,
    costPolicy,
    policy: robustnessPolicy,
  });

  const blockers = [...(robustness.blockers || [])];
  if (robustness.status !== 'ROBUSTNESS_REVIEW_CANDIDATE') blockers.push('ROBUSTNESS_NOT_PROVEN');
  if (robustness.usableFolds < Number(resolved.minimumUsableFolds)) blockers.push('INSUFFICIENT_USABLE_FOLDS');
  if (robustness.passingFolds < Number(resolved.minimumPassingFolds)) blockers.push('INSUFFICIENT_PASSING_FOLDS');
  if (robustness.failingStressScenarios > Number(resolved.maximumFailingStressScenarios)) blockers.push('COST_STRESS_NOT_ACCEPTABLE');
  if (resolved.requireBenchmark && (!Array.isArray(benchmarkReturns) || benchmarkReturns.length !== rows.length)) blockers.push('BENCHMARK_REQUIRED');

  const uniqueBlockers = [...new Set(blockers)];
  return Object.freeze({
    phase: '55.x',
    status: uniqueBlockers.length ? 'OBSERVE' : 'PHASE55_REVIEW_CANDIDATE',
    blockers: Object.freeze(uniqueBlockers),
    robustness,
    handoff: Object.freeze({
      nextPhase: '56',
      nextFocus: 'CHART_INTELLIGENCE_CORE',
      paperTradingAllowed: false,
      reason: 'Chart and entry intelligence must be validated before paper trading.',
    }),
    reviewOnly: true,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    paperTradingAllowed: false,
    humanApprovalRequired: true,
    transmitted: false,
    safety: PHASE55_X_SAFETY,
  });
}
