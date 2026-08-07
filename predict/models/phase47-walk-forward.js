import crypto from "node:crypto";
import { MODEL_TYPES, PHASE47_SAFETY, evaluateModel, normalizeTrainingRows, trainModel } from "./phase47-real-training.js";

const mean = (values) => values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
const std = (values) => {
  if (values.length < 2) return 0;
  const avg = mean(values);
  return Math.sqrt(mean(values.map((value) => (value - avg) ** 2)));
};
const stableHash = (value) => crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
const clamp = (value, lo, hi) => Math.max(lo, Math.min(hi, value));

export const DEFAULT_PROMOTION_GATE = Object.freeze({
  minAuc: 0.53,
  minProfitFactor: 1.2,
  minSharpe: 0.25,
  maxDrawdown: 0.25,
  minOosSamples: 500,
  minPositionChanges: 40,
  minExposure: 0.05,
  maxExposure: 0.85,
  requirePositiveNetReturn: true,
  requireBenchmarkOutperformance: true,
});

export const DEFAULT_THRESHOLD_GRID = Object.freeze([0.52, 0.54, 0.55, 0.56, 0.58, 0.6, 0.62, 0.65, 0.7]);

function foldBoundaries(length, { minTrain = 60, validationSize = 20, step = 20 } = {}) {
  if (length < minTrain + validationSize) throw new RangeError("insufficient rows for walk-forward validation");
  const folds = [];
  for (let trainEnd = minTrain; trainEnd + validationSize <= length; trainEnd += step) {
    folds.push({ trainStart: 0, trainEnd, testStart: trainEnd, testEnd: trainEnd + validationSize });
  }
  if (!folds.length) throw new RangeError("no walk-forward folds generated");
  return folds;
}

function dedupePredictions(predictions) {
  const sorted = [...predictions].sort((a, b) => a.sessionDate.localeCompare(b.sessionDate) || a.id.localeCompare(b.id));
  const deduped = [];
  const seen = new Set();
  for (const item of sorted) {
    if (seen.has(item.id)) continue;
    seen.add(item.id);
    deduped.push(item);
  }
  return deduped;
}

function buildOosMetrics(predictions, { entryThreshold = 0.55, costRate = 0.001 } = {}) {
  const deduped = dedupePredictions(predictions);
  let position = 0;
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  let trades = 0;
  const returns = [];
  const grossReturns = [];
  for (const item of deduped) {
    const nextPosition = item.probability >= entryThreshold ? 1 : 0;
    const turnover = Math.abs(nextPosition - position);
    const gross = nextPosition * item.actualReturn;
    const net = gross - turnover * costRate;
    if (turnover > 0) trades += 1;
    grossReturns.push(gross);
    returns.push(net);
    equity *= 1 + net;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak ? (peak - equity) / peak : 0);
    position = nextPosition;
  }
  const gains = returns.filter((value) => value > 0).reduce((sum, value) => sum + value, 0);
  const losses = Math.abs(returns.filter((value) => value < 0).reduce((sum, value) => sum + value, 0));
  const avg = mean(returns);
  const sigma = std(returns);
  const active = deduped.filter((item) => item.probability >= entryThreshold);
  const wins = active.filter((item) => item.actualReturn > 0).length;
  const sampleCount = deduped.length;
  const years = sampleCount / 252;
  return Object.freeze({
    entryThreshold,
    sampleCount,
    activeDays: active.length,
    exposure: sampleCount ? active.length / sampleCount : 0,
    positionChanges: trades,
    winRate: active.length ? wins / active.length : 0,
    profitFactor: losses ? gains / losses : gains > 0 ? 999 : 0,
    sharpe: sigma ? (avg / sigma) * Math.sqrt(252) : 0,
    maxDrawdown,
    cagr: years > 0 ? equity ** (1 / years) - 1 : 0,
    netReturn: equity - 1,
    averageDailyReturn: avg,
    grossReturnSum: grossReturns.reduce((sum, value) => sum + value, 0),
  });
}

function buildThresholdSweep(predictions, { thresholdGrid = DEFAULT_THRESHOLD_GRID, costRate = 0.001 } = {}) {
  return Object.freeze(thresholdGrid.map((threshold) => buildOosMetrics(predictions, { entryThreshold: threshold, costRate })));
}

function chooseThreshold(sweep) {
  const candidates = sweep.filter((m) => m.sampleCount >= 500 && m.positionChanges >= 40 && m.exposure >= 0.03 && m.exposure <= 0.85);
  const pool = candidates.length ? candidates : sweep;
  const score = (m) => (
    clamp(m.profitFactor, 0, 3) / 3 * 0.35
    + clamp((m.sharpe + 1) / 3, 0, 1) * 0.25
    + clamp((m.netReturn + 1) / 2, 0, 1) * 0.2
    - clamp(m.maxDrawdown, 0, 1) * 0.15
    + clamp(m.exposure / 0.25, 0, 1) * 0.05
  );
  return [...pool].sort((a, b) => score(b) - score(a) || a.entryThreshold - b.entryThreshold)[0];
}

function buildConfidenceBuckets(predictions) {
  const deduped = dedupePredictions(predictions);
  const bands = [
    [0.5, 0.55], [0.55, 0.6], [0.6, 0.65], [0.65, 0.7], [0.7, 0.8], [0.8, 1.0000001],
  ];
  return Object.freeze(bands.map(([min, max]) => {
    const items = deduped.filter((item) => item.probability >= min && item.probability < max);
    const returns = items.map((item) => item.actualReturn);
    const wins = returns.filter((r) => r > 0).length;
    return Object.freeze({
      minProbability: min,
      maxProbability: max > 1 ? 1 : max,
      sampleCount: items.length,
      winRate: items.length ? wins / items.length : 0,
      averageReturn: mean(returns),
      cumulativeReturnSum: returns.reduce((sum, r) => sum + r, 0),
    });
  }));
}

function buildBuyAndHoldBenchmark(predictions) {
  const sorted = dedupePredictions(predictions);
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  const returns = [];
  for (const item of sorted) {
    returns.push(item.actualReturn);
    equity *= 1 + item.actualReturn;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak ? (peak - equity) / peak : 0);
  }
  const sigma = std(returns);
  const avg = mean(returns);
  const years = sorted.length / 252;
  return Object.freeze({
    sampleCount: sorted.length,
    sharpe: sigma ? (avg / sigma) * Math.sqrt(252) : 0,
    maxDrawdown,
    cagr: years > 0 ? equity ** (1 / years) - 1 : 0,
    netReturn: equity - 1,
  });
}

export function evaluatePromotionGate(aggregate, gate = DEFAULT_PROMOTION_GATE) {
  const failures = [];
  const oos = aggregate?.oos ?? {};
  const benchmark = aggregate?.benchmark ?? {};
  if ((aggregate?.auc ?? 0) < gate.minAuc) failures.push("AUC_BELOW_MINIMUM");
  if ((oos.profitFactor ?? 0) < gate.minProfitFactor) failures.push("PROFIT_FACTOR_BELOW_MINIMUM");
  if ((oos.sharpe ?? -Infinity) < gate.minSharpe) failures.push("SHARPE_BELOW_MINIMUM");
  if ((oos.maxDrawdown ?? Infinity) > gate.maxDrawdown) failures.push("MAX_DRAWDOWN_ABOVE_LIMIT");
  if ((oos.sampleCount ?? 0) < gate.minOosSamples) failures.push("OOS_SAMPLE_COUNT_BELOW_MINIMUM");
  if ((oos.positionChanges ?? 0) < gate.minPositionChanges) failures.push("POSITION_CHANGES_BELOW_MINIMUM");
  if ((oos.exposure ?? 0) < gate.minExposure) failures.push("EXPOSURE_BELOW_MINIMUM");
  if ((oos.exposure ?? 1) > gate.maxExposure) failures.push("EXPOSURE_ABOVE_MAXIMUM");
  if (gate.requirePositiveNetReturn && !((oos.netReturn ?? -Infinity) > 0)) failures.push("NET_RETURN_NOT_POSITIVE");
  if (gate.requireBenchmarkOutperformance && !((oos.netReturn ?? -Infinity) > (benchmark.netReturn ?? Infinity))) failures.push("BENCHMARK_NOT_OUTPERFORMED");
  return Object.freeze({
    status: failures.length ? "BLOCKED_FOR_PROMOTION" : "ELIGIBLE_FOR_PROMOTION_REVIEW",
    failures: Object.freeze(failures),
    gate: Object.freeze({ ...gate }),
    automaticPromotionAllowed: false,
    humanApprovalRequired: true,
  });
}

export function runWalkForward({ rows, modelTypes = MODEL_TYPES, options = {}, costRate = 0.001, entryThreshold = 0.55, thresholdGrid = DEFAULT_THRESHOLD_GRID } = {}) {
  const normalized = normalizeTrainingRows(rows);
  const boundaries = foldBoundaries(normalized.length, options);
  const results = [];

  for (const modelType of modelTypes) {
    const oosPredictions = [];
    const folds = boundaries.map((boundary, index) => {
      const trainRows = normalized.slice(boundary.trainStart, boundary.trainEnd);
      const testRows = normalized.slice(boundary.testStart, boundary.testEnd);
      const model = trainModel({ rows: trainRows, modelType, options: options[modelType] ?? {} });
      const metrics = evaluateModel({ model, rows: testRows, costRate });
      testRows.forEach((row, rowIndex) => {
        oosPredictions.push(Object.freeze({
          id: row.id,
          symbol: row.symbol,
          sessionDate: row.sessionDate,
          probability: metrics.probabilities[rowIndex],
          label: row.label,
          actualReturn: row.actualReturn,
        }));
      });
      return Object.freeze({
        fold: index + 1,
        modelType,
        trainStart: trainRows[0].sessionDate,
        trainEnd: trainRows.at(-1).sessionDate,
        testStart: testRows[0].sessionDate,
        testEnd: testRows.at(-1).sessionDate,
        trainCount: trainRows.length,
        testCount: testRows.length,
        metrics,
      });
    });

    const thresholdSweep = buildThresholdSweep(oosPredictions, { thresholdGrid, costRate });
    const optimizedOos = chooseThreshold(thresholdSweep);
    const aggregateBase = {
      modelType,
      foldCount: folds.length,
      accuracy: mean(folds.map((fold) => fold.metrics.accuracy)),
      precision: mean(folds.map((fold) => fold.metrics.precision)),
      recall: mean(folds.map((fold) => fold.metrics.recall)),
      auc: mean(folds.map((fold) => fold.metrics.auc)),
      brierScore: mean(folds.map((fold) => fold.metrics.brierScore)),
      oos: optimizedOos,
      baselineOos: buildOosMetrics(oosPredictions, { entryThreshold, costRate }),
      thresholdSweep,
      confidenceBuckets: buildConfidenceBuckets(oosPredictions),
      benchmark: buildBuyAndHoldBenchmark(oosPredictions),
    };
    const aggregate = Object.freeze({ ...aggregateBase, promotionGate: evaluatePromotionGate(aggregateBase) });
    results.push(Object.freeze({ modelType, folds: Object.freeze(folds), aggregate }));
  }

  const ranked = [...results].sort((a, b) => {
    const score = (aggregate) => aggregate.auc * 0.2
      + aggregate.accuracy * 0.05
      + Math.min(aggregate.oos.profitFactor, 3) / 3 * 0.3
      + Math.max(-1, Math.min(1, aggregate.oos.sharpe / 2)) * 0.2
      - aggregate.oos.maxDrawdown * 0.15
      + Math.max(-1, Math.min(1, aggregate.oos.netReturn)) * 0.1;
    return score(b.aggregate) - score(a.aggregate) || a.modelType.localeCompare(b.modelType);
  });

  return Object.freeze({
    status: "READY_FOR_HUMAN_REVIEW",
    folds: boundaries.length,
    entryThreshold,
    thresholdOptimization: true,
    ranked: Object.freeze(ranked),
    selectedModelType: ranked[0].modelType,
    selectedPromotionStatus: ranked[0].aggregate.promotionGate.status,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    safety: PHASE47_SAFETY,
  });
}

export function buildPhase47RegistryCandidate({ rows, walkForwardResult, datasetLineage = {}, generatedAt = new Date().toISOString() } = {}) {
  const normalized = normalizeTrainingRows(rows);
  if (!walkForwardResult?.selectedModelType) throw new TypeError("walkForwardResult is required");
  const selected = walkForwardResult.ranked.find((item) => item.modelType === walkForwardResult.selectedModelType);
  const finalModel = trainModel({ rows: normalized, modelType: selected.modelType });
  const payload = {
    schemaVersion: 1,
    phase: 47.1,
    modelId: finalModel.modelId,
    modelType: selected.modelType,
    status: "CANDIDATE_REVIEW_ONLY",
    promotionStatus: selected.aggregate.promotionGate.status,
    promotionFailures: selected.aggregate.promotionGate.failures,
    selectedEntryThreshold: selected.aggregate.oos.entryThreshold,
    generatedAt: new Date(generatedAt).toISOString(),
    trainingPeriod: { start: normalized[0].sessionDate, end: normalized.at(-1).sessionDate },
    trainingRows: normalized.length,
    walkForward: selected.aggregate,
    datasetLineage,
    featureNames: finalModel.names,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    safety: PHASE47_SAFETY,
  };
  return Object.freeze({ ...payload, checksum: stableHash(payload) });
}

export function auditPhase47Candidate(candidate) {
  const blockers = [];
  if (!candidate || typeof candidate !== "object") blockers.push("CANDIDATE_REQUIRED");
  if (candidate?.automaticPromotionAllowed !== false) blockers.push("AUTOMATIC_PROMOTION_MUST_BE_FALSE");
  if (candidate?.productionUpdateAllowed !== false) blockers.push("PRODUCTION_UPDATE_MUST_BE_FALSE");
  if (candidate?.humanApprovalRequired !== true) blockers.push("HUMAN_APPROVAL_REQUIRED");
  if ((candidate?.walkForward?.foldCount ?? 0) < 2) blockers.push("INSUFFICIENT_WALK_FORWARD_FOLDS");
  if ((candidate?.walkForward?.oos?.sampleCount ?? 0) < 20) blockers.push("INSUFFICIENT_OOS_SAMPLE_COUNT");
  if (!candidate?.promotionStatus) blockers.push("PROMOTION_STATUS_REQUIRED");
  if (candidate?.checksum) {
    const { checksum, ...payload } = candidate;
    if (stableHash(payload) !== checksum) blockers.push("CHECKSUM_MISMATCH");
  } else blockers.push("CHECKSUM_REQUIRED");
  return Object.freeze({
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    blockers: Object.freeze(blockers),
    brokerWrites: 0,
    liveOrders: 0,
    safety: PHASE47_SAFETY,
  });
}
