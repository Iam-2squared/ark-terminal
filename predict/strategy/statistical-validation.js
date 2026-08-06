export const STATISTICAL_VALIDATION_VERSION = "phase24-statistical-validation-v1";

const finite = (value) => Number.isFinite(Number(value));
const number = (value, fallback = null) => finite(value) ? Number(value) : fallback;

function mean(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function percentile(values, probability) {
  if (!values.length) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const index = Math.min(sorted.length - 1, Math.max(0, Math.floor(probability * sorted.length)));
  return sorted[index];
}

function seededGenerator(seed = 1) {
  let state = Math.abs(Math.trunc(number(seed, 1))) || 1;
  return () => {
    state = (state * 48271) % 2147483647;
    return state / 2147483647;
  };
}

function bootstrapMean(values, iterations, seed) {
  const random = seededGenerator(seed);
  const estimates = [];
  for (let iteration = 0; iteration < iterations; iteration += 1) {
    let total = 0;
    for (let index = 0; index < values.length; index += 1) {
      total += values[Math.floor(random() * values.length)];
    }
    estimates.push(total / values.length);
  }
  return estimates;
}

export function validateStrategyStatistics(rows = [], options = {}) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");
  const returns = rows
    .map((row) => number(row.netReturn ?? row.costAdjustedReturn ?? row.returnPercent ?? row.actualReturn))
    .filter((value) => value !== null);
  const minimumSample = Math.max(1, Math.trunc(number(options.minimumSample, 30)));
  const iterations = Math.max(100, Math.min(5000, Math.trunc(number(options.bootstrapIterations, 1000))));
  const confidenceLevel = Math.min(0.99, Math.max(0.5, number(options.confidenceLevel, 0.95)));
  const multipleTests = Math.max(1, Math.trunc(number(options.multipleTests, 1)));
  const alpha = 1 - confidenceLevel;
  const adjustedAlpha = alpha / multipleTests;
  const blockers = [];

  if (returns.length < minimumSample) blockers.push("INSUFFICIENT_SAMPLE");
  if (options.outOfSample === false) blockers.push("OUT_OF_SAMPLE_REQUIRED");
  if (options.walkForwardPassed === false) blockers.push("WALK_FORWARD_FAILED");
  if (options.futureLeakChecked !== true) blockers.push("FUTURE_LEAK_CHECK_REQUIRED");

  const estimates = returns.length ? bootstrapMean(returns, iterations, options.seed ?? 24) : [];
  const lower = percentile(estimates, adjustedAlpha / 2);
  const upper = percentile(estimates, 1 - adjustedAlpha / 2);
  if (lower !== null && lower <= 0) blockers.push("BOOTSTRAP_EDGE_NOT_CONFIRMED");

  const trainingReturn = number(options.trainingAverageReturn);
  const outOfSampleReturn = number(options.outOfSampleAverageReturn, mean(returns));
  const overfitRatio = trainingReturn !== null && trainingReturn !== 0 && outOfSampleReturn !== null
    ? outOfSampleReturn / trainingReturn
    : null;
  if (overfitRatio !== null && overfitRatio < number(options.minimumOverfitRatio, 0.5)) {
    blockers.push("OVERFIT_RISK");
  }

  return {
    version: STATISTICAL_VALIDATION_VERSION,
    status: blockers.length ? "REJECT" : "PASS",
    sampleCount: returns.length,
    averageReturn: mean(returns),
    bootstrap: {
      iterations,
      confidenceLevel,
      multipleTests,
      adjustedAlpha,
      lower,
      upper,
    },
    overfitRatio,
    blockers,
    safety: {
      evaluationOnly: true,
      executionAllowed: false,
      brokerWriteAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
    },
  };
}

export default validateStrategyStatistics;
