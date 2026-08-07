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

function sessionDates(rows) {
  return [...new Set(rows.map((row) => row.sessionDate))].sort();
}

function foldBoundaries(rows, { minTrain = 60, validationSize = 20, step = 20 } = {}) {
  const dates = sessionDates(rows);
  if (dates.length < minTrain + validationSize) throw new RangeError("insufficient session dates for walk-forward validation");
  const folds = [];
  for (let trainDateCount = minTrain; trainDateCount + validationSize <= dates.length; trainDateCount += step) {
    const trainDates = new Set(dates.slice(0, trainDateCount));
    const testDates = new Set(dates.slice(trainDateCount, trainDateCount + validationSize));
    const trainIndexes = rows.map((row, index) => trainDates.has(row.sessionDate) ? index : -1).filter((index) => index >= 0);
    const testIndexes = rows.map((row, index) => testDates.has(row.sessionDate) ? index : -1).filter((index) => index >= 0);
    folds.push({
      trainStart: trainIndexes[0],
      trainEnd: trainIndexes.at(-1) + 1,
      testStart: testIndexes[0],
      testEnd: testIndexes.at(-1) + 1,
      trainDates: Object.freeze([...trainDates]),
      testDates: Object.freeze([...testDates]),
    });
  }
  if (!folds.length) throw new RangeError("no walk-forward folds generated");
  return folds;
}

function rowsForDates(rows, dates) {
  const allowed = dates instanceof Set ? dates : new Set(dates);
  return rows.filter((row) => allowed.has(row.sessionDate));
}

function dedupePredictions(predictions) {
  const sorted = [...predictions].sort((a, b) => a.sessionDate.localeCompare(b.sessionDate) || a.symbol.localeCompare(b.symbol) || a.id.localeCompare(b.id));
  const deduped = [];
  const seen = new Set();
  for (const item of sorted) {
    if (seen.has(item.id)) continue;
    seen.add(item.id);
    deduped.push(item);
  }
  return deduped;
}

function groupBySessionDate(predictions) {
  const grouped = new Map();
  for (const item of dedupePredictions(predictions)) {
    if (!grouped.has(item.sessionDate)) grouped.set(item.sessionDate, []);
    grouped.get(item.sessionDate).push(item);
  }
  return [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b));
}

function thresholdFor(item, entryThreshold) {
  if (item.selectedThreshold !== null && item.selectedThreshold !== undefined && Number.isFinite(Number(item.selectedThreshold))) return Number(item.selectedThreshold);
  if (entryThreshold !== null && entryThreshold !== undefined && Number.isFinite(Number(entryThreshold))) return Number(entryThreshold);
  return 0.55;
}

export function buildPortfolioOosMetrics(predictions, { entryThreshold = 0.55, costRate = 0.001 } = {}) {
  const deduped = dedupePredictions(predictions);
  const groups = groupBySessionDate(deduped);
  const positions = new Map();
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  let positionChanges = 0;
  let activeSymbolDays = 0;
  let winningActiveSymbolDays = 0;
  let totalSymbolDays = 0;
  let transactionCostSum = 0;
  const dailyReturns = [];
  const dailyGrossReturns = [];
  const dailyTurnovers = [];
  const dailyExposures = [];

  for (const [, items] of groups) {
    const denominator = items.length || 1;
    let grossSum = 0;
    let turnoverSum = 0;
    let activeCount = 0;
    for (const item of items) {
      const previousPosition = positions.get(item.symbol) ?? 0;
      const nextPosition = item.probability >= thresholdFor(item, entryThreshold) ? 1 : 0;
      const turnover = Math.abs(nextPosition - previousPosition);
      if (turnover > 0) positionChanges += 1;
      if (nextPosition > 0) {
        activeCount += 1;
        activeSymbolDays += 1;
        if (item.actualReturn > 0) winningActiveSymbolDays += 1;
      }
      grossSum += nextPosition * item.actualReturn;
      turnoverSum += turnover;
      positions.set(item.symbol, nextPosition);
    }
    totalSymbolDays += items.length;
    const gross = grossSum / denominator;
    const turnover = turnoverSum / denominator;
    const cost = turnover * costRate;
    const net = gross - cost;
    transactionCostSum += cost;
    dailyGrossReturns.push(gross);
    dailyReturns.push(net);
    dailyTurnovers.push(turnover);
    dailyExposures.push(activeCount / denominator);
    equity *= 1 + net;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak ? (peak - equity) / peak : 0);
  }

  const gains = dailyReturns.filter((value) => value > 0).reduce((sum, value) => sum + value, 0);
  const losses = Math.abs(dailyReturns.filter((value) => value < 0).reduce((sum, value) => sum + value, 0));
  const avg = mean(dailyReturns);
  const sigma = std(dailyReturns);
  const portfolioDays = groups.length;
  const years = portfolioDays / 252;
  const thresholds = [...new Set(deduped.map((item) => thresholdFor(item, entryThreshold)))];
  const portfolioWinDays = dailyReturns.filter((value) => value > 0).length;

  return Object.freeze({
    entryThreshold: thresholds.length === 1 ? thresholds[0] : null,
    thresholdMode: thresholds.length === 1 ? "FIXED" : "NESTED_PER_FOLD",
    sampleCount: deduped.length,
    portfolioDays,
    activeDays: activeSymbolDays,
    activeSymbolDays,
    exposureDefinition: "active symbol-days / observed symbol-days",
    exposure: totalSymbolDays ? activeSymbolDays / totalSymbolDays : 0,
    averageGrossExposure: mean(dailyExposures),
    positionChanges,
    turnover: mean(dailyTurnovers),
    transactionCostSum,
    winRate: activeSymbolDays ? winningActiveSymbolDays / activeSymbolDays : 0,
    portfolioWinRate: portfolioDays ? portfolioWinDays / portfolioDays : 0,
    profitFactorDefinition: "portfolio daily net returns",
    profitFactor: losses ? gains / losses : gains > 0 ? 999 : 0,
    sharpe: sigma ? (avg / sigma) * Math.sqrt(252) : 0,
    maxDrawdown,
    cagr: years > 0 ? equity ** (1 / years) - 1 : 0,
    netReturn: equity - 1,
    averageDailyReturn: avg,
    grossReturnSum: dailyGrossReturns.reduce((sum, value) => sum + value, 0),
    dailyReturns: Object.freeze(dailyReturns),
  });
}

function buildThresholdSweep(predictions, { thresholdGrid = DEFAULT_THRESHOLD_GRID, costRate = 0.001 } = {}) {
  return Object.freeze(thresholdGrid.map((threshold) => buildPortfolioOosMetrics(
    predictions.map((item) => ({ ...item, selectedThreshold: undefined })),
    { entryThreshold: threshold, costRate },
  )));
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
      diagnosticsOnly: true,
    });
  }));
}

export function buildEqualWeightBenchmark(predictions) {
  const deduped = dedupePredictions(predictions);
  const groups = groupBySessionDate(deduped);
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  const returns = [];
  for (const [, items] of groups) {
    const dailyReturn = mean(items.map((item) => item.actualReturn));
    returns.push(dailyReturn);
    equity *= 1 + dailyReturn;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak ? (peak - equity) / peak : 0);
  }
  const sigma = std(returns);
  const avg = mean(returns);
  const years = groups.length / 252;
  return Object.freeze({
    type: "EQUAL_WEIGHT_BUY_AND_HOLD",
    sampleCount: deduped.length,
    portfolioDays: groups.length,
    sharpe: sigma ? (avg / sigma) * Math.sqrt(252) : 0,
    maxDrawdown,
    cagr: years > 0 ? equity ** (1 / years) - 1 : 0,
    netReturn: equity - 1,
    dailyReturns: Object.freeze(returns),
  });
}

function buildPredictions(model, rows, costRate) {
  const normalized = rows.length >= 20 ? null : rows;
  if (normalized) {
    const probabilities = normalized.map((row) => clamp(model.predict(row), 0.001, 0.999));
    const labels = normalized.map((row) => row.label);
    const predictions = normalized.map((row, rowIndex) => Object.freeze({
      id: row.id,
      symbol: row.symbol,
      sessionDate: row.sessionDate,
      probability: probabilities[rowIndex],
      label: row.label,
      actualReturn: row.actualReturn,
    }));
    let tp = 0; let fp = 0; let tn = 0; let fn = 0;
    labels.forEach((label, index) => {
      const predicted = probabilities[index] >= 0.5 ? 1 : 0;
      if (label === 1 && predicted === 1) tp += 1;
      else if (label === 0 && predicted === 1) fp += 1;
      else if (label === 0 && predicted === 0) tn += 1;
      else fn += 1;
    });
    const positives = labels.filter((label) => label === 1).length;
    const negatives = labels.length - positives;
    let auc = 0.5;
    if (positives && negatives) {
      const ranked = probabilities.map((probability, index) => ({ probability, label: labels[index] }))
        .sort((a, b) => a.probability - b.probability);
      let rankSum = 0;
      for (let i = 0; i < ranked.length;) {
        let j = i + 1;
        while (j < ranked.length && ranked[j].probability === ranked[i].probability) j += 1;
        const averageRank = (i + 1 + j) / 2;
        for (let k = i; k < j; k += 1) if (ranked[k].label === 1) rankSum += averageRank;
        i = j;
      }
      auc = (rankSum - positives * (positives + 1) / 2) / (positives * negatives);
    }
    const metrics = Object.freeze({
      accuracy: labels.length ? (tp + tn) / labels.length : 0,
      precision: tp + fp ? tp / (tp + fp) : 0,
      recall: tp + fn ? tp / (tp + fn) : 0,
      auc,
      brierScore: mean(probabilities.map((value, index) => (value - labels[index]) ** 2)),
      sampleCount: labels.length,
      probabilities: Object.freeze(probabilities),
      safety: PHASE47_SAFETY,
    });
    return { metrics, predictions };
  }
  const metrics = evaluateModel({ model, rows, costRate });
  const predictions = rows.map((row, rowIndex) => Object.freeze({
    id: row.id,
    symbol: row.symbol,
    sessionDate: row.sessionDate,
    probability: metrics.probabilities[rowIndex],
    label: row.label,
    actualReturn: row.actualReturn,
  }));
  return { metrics, predictions };
}

function selectNestedThreshold({ trainRows, modelType, thresholdGrid, costRate, entryThreshold, options }) {
  const dates = sessionDates(trainRows);
  const requested = Math.max(1, Number(options.innerValidationSize ?? Math.min(20, Math.max(5, Math.floor(dates.length * 0.25)))));
  let validationDateCount = Math.min(requested, Math.max(1, dates.length - 1));
  let innerTrainRows = [];
  let innerValidationRows = [];

  while (validationDateCount >= 1) {
    const split = dates.length - validationDateCount;
    innerTrainRows = rowsForDates(trainRows, dates.slice(0, split));
    innerValidationRows = rowsForDates(trainRows, dates.slice(split));
    if (innerTrainRows.length >= 20 && innerValidationRows.length > 0) break;
    validationDateCount -= 1;
  }

  if (innerTrainRows.length < 20 || !innerValidationRows.length) {
    return Object.freeze({
      status: "FALLBACK_INSUFFICIENT_INNER_DATA",
      selectedThreshold: entryThreshold,
      validation: null,
      sweep: Object.freeze([]),
      innerTrainStart: null,
      innerTrainEnd: null,
      validationStart: null,
      validationEnd: null,
    });
  }

  const innerModel = trainModel({ rows: innerTrainRows, modelType, options: options[modelType] ?? {} });
  const { predictions } = buildPredictions(innerModel, innerValidationRows, costRate);
  const sweep = buildThresholdSweep(predictions, { thresholdGrid, costRate });
  const selected = chooseThreshold(sweep);
  return Object.freeze({
    status: "SELECTED_ON_INNER_VALIDATION",
    selectedThreshold: selected.entryThreshold,
    validation: selected,
    sweep,
    innerTrainStart: innerTrainRows[0].sessionDate,
    innerTrainEnd: innerTrainRows.at(-1).sessionDate,
    validationStart: innerValidationRows[0].sessionDate,
    validationEnd: innerValidationRows.at(-1).sessionDate,
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
  const boundaries = foldBoundaries(normalized, options);
  const results = [];

  for (const modelType of modelTypes) {
    const oosPredictions = [];
    const folds = boundaries.map((boundary, index) => {
      const trainRows = rowsForDates(normalized, boundary.trainDates);
      const testRows = rowsForDates(normalized, boundary.testDates);
      const thresholdSelection = selectNestedThreshold({ trainRows, modelType, thresholdGrid, costRate, entryThreshold, options });
      const model = trainModel({ rows: trainRows, modelType, options: options[modelType] ?? {} });
      const { metrics, predictions } = buildPredictions(model, testRows, costRate);
      predictions.forEach((prediction) => {
        oosPredictions.push(Object.freeze({
          ...prediction,
          outerFold: index + 1,
          selectedThreshold: thresholdSelection.selectedThreshold,
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
        trainSessionCount: boundary.trainDates.length,
        testSessionCount: boundary.testDates.length,
        selectedThreshold: thresholdSelection.selectedThreshold,
        thresholdSelection,
        metrics,
      });
    });

    const nestedOos = buildPortfolioOosMetrics(oosPredictions, { entryThreshold: null, costRate });
    const diagnosticThresholdSweep = buildThresholdSweep(oosPredictions, { thresholdGrid, costRate });
    const aggregateBase = {
      modelType,
      foldCount: folds.length,
      accuracy: mean(folds.map((fold) => fold.metrics.accuracy)),
      precision: mean(folds.map((fold) => fold.metrics.precision)),
      recall: mean(folds.map((fold) => fold.metrics.recall)),
      auc: mean(folds.map((fold) => fold.metrics.auc)),
      brierScore: mean(folds.map((fold) => fold.metrics.brierScore)),
      oos: nestedOos,
      baselineOos: buildPortfolioOosMetrics(oosPredictions.map((item) => ({ ...item, selectedThreshold: undefined })), { entryThreshold, costRate }),
      thresholdSweep: diagnosticThresholdSweep,
      thresholdSweepDiagnosticsOnly: true,
      thresholdHistory: Object.freeze(folds.map((fold) => Object.freeze({
        fold: fold.fold,
        selectedThreshold: fold.selectedThreshold,
        selectionStatus: fold.thresholdSelection.status,
        validationProfitFactor: fold.thresholdSelection.validation?.profitFactor ?? null,
        validationSharpe: fold.thresholdSelection.validation?.sharpe ?? null,
        validationMaxDrawdown: fold.thresholdSelection.validation?.maxDrawdown ?? null,
        validationSamples: fold.thresholdSelection.validation?.sampleCount ?? 0,
        innerTrainEnd: fold.thresholdSelection.innerTrainEnd,
        validationStart: fold.thresholdSelection.validationStart,
        validationEnd: fold.thresholdSelection.validationEnd,
        outerTestStart: fold.testStart,
      }))),
      confidenceBuckets: buildConfidenceBuckets(oosPredictions),
      benchmark: buildEqualWeightBenchmark(oosPredictions),
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
    phase: 47.2,
    folds: boundaries.length,
    entryThreshold,
    thresholdOptimization: true,
    thresholdSelectionMode: "NESTED_INNER_VALIDATION",
    portfolioEvaluationMode: "SESSION_DATE_EQUAL_WEIGHT_MULTI_ASSET",
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
  const thresholds = selected.aggregate.thresholdHistory.map((item) => item.selectedThreshold).filter(Number.isFinite);
  const payload = {
    schemaVersion: 2,
    phase: 47.2,
    modelId: finalModel.modelId,
    modelType: selected.modelType,
    status: "CANDIDATE_REVIEW_ONLY",
    promotionStatus: selected.aggregate.promotionGate.status,
    promotionFailures: selected.aggregate.promotionGate.failures,
    selectedEntryThreshold: thresholds.length && thresholds.every((value) => value === thresholds[0]) ? thresholds[0] : null,
    thresholdSelectionMode: "NESTED_INNER_VALIDATION",
    thresholdHistory: selected.aggregate.thresholdHistory,
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
  if (candidate?.thresholdSelectionMode !== "NESTED_INNER_VALIDATION") blockers.push("NESTED_THRESHOLD_SELECTION_REQUIRED");
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
    excelOrderWrites: 0,
    rssOrderCalls: 0,
    liveOrders: 0,
    safety: PHASE47_SAFETY,
  });
}