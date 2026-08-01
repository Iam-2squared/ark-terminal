import {
  validateHistoryData,
  validateIndicatorCalculations,
} from "../analysis/data-quality.js";
import { calculateIndicators } from "../analysis/indicators.js";
import { createPredictionOutput } from "../analysis/prediction-output.js";
import { scoreAnalysis } from "../analysis/scoring.js";
import { deriveOptimizedWeights } from "../analysis/weights.js";
import { BACKTEST_COSTS, BACKTEST_SPLIT } from "../config.js";
import {
  deriveTradeDecision,
  evaluateResolvedPrediction,
} from "../learning/evaluation-policy.js";
import { extractPredictionFeatures } from "../learning/feature-extractor.js";
import {
  fitContinuousModelCandidates,
  predictContinuousScore,
} from "../learning/continuous-model.js";
import {
  DEFAULT_MODEL_CALIBRATION,
  directionFromScore,
  generateCalibrationCandidates,
  normalizeModelCalibration,
  sameCalibration,
} from "../learning/model-calibration.js";
import { createPredictionRecord } from "./storage.js";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function average(values) {
  return values.length
    ? values.reduce((sum, value) => sum + Number(value), 0) / values.length
    : null;
}

function median(values) {
  if (!values.length) {
    return null;
  }

  const ordered = [...values].sort((first, second) => first - second);
  const middle = Math.floor(ordered.length / 2);

  return ordered.length % 2
    ? ordered[middle]
    : (ordered[middle - 1] + ordered[middle]) / 2;
}

function standardDeviation(values) {
  if (values.length < 2) {
    return null;
  }

  const valueAverage = average(values);
  const variance = average(values.map((value) => (value - valueAverage) ** 2));

  return Math.sqrt(variance);
}

export function determineDirection(
  score,
  calibration = DEFAULT_MODEL_CALIBRATION,
) {
  return directionFromScore(score, calibration);
}

function determineHit(direction, actualReturn, strategyReturn = null) {
  if (direction !== "中立" && finite(strategyReturn)) {
    return Number(strategyReturn) > 0;
  }

  if (direction === "強気") {
    return actualReturn > 0;
  }

  if (direction === "弱気") {
    return actualReturn < 0;
  }

  return Math.abs(actualReturn) < 2;
}

function roundTripCostPercent(costs = BACKTEST_COSTS) {
  return (
    ((Number(costs.commissionBpsPerSide) || 0) +
      (Number(costs.slippageBpsPerSide) || 0)) *
    2 *
    0.01
  );
}

function outcomeFor({ score, actualReturn, costs = BACKTEST_COSTS }) {
  const direction = determineDirection(score);
  const grossStrategyReturn =
    direction === "強気"
      ? actualReturn
      : direction === "弱気"
        ? -actualReturn
        : 0;
  const tradingCost = direction === "中立" ? 0 : roundTripCostPercent(costs);
  const strategyReturn = grossStrategyReturn - tradingCost;
  const hit = determineHit(direction, actualReturn, strategyReturn);

  return {
    direction,
    grossStrategyReturn,
    tradingCost,
    strategyReturn,
    hit,
    outcome: hit ? "的中" : "外れ",
  };
}

function resolvedOutcomeFor(record, actualReturn) {
  if (finite(record.evaluationThreshold) && record.decision) {
    return evaluateResolvedPrediction({
      direction: record.direction || determineDirection(record.score),
      actualReturn,
      threshold: record.evaluationThreshold,
      decision: record.decision,
      costs: record.costAssumptions || BACKTEST_COSTS,
    });
  }

  return outcomeFor({
    score: record.score,
    actualReturn,
    costs: record.costAssumptions || BACKTEST_COSTS,
  });
}

export function resolvePredictions(records, symbol, candles) {
  const ordered = [...candles].sort(
    (first, second) => first.time - second.time,
  );
  let changed = false;

  const nextRecords = records.map((record) => {
    if (record.status !== "pending" || record.symbol !== symbol) {
      return record;
    }

    const startIndex = ordered.findIndex(
      (candle) => candle.time >= Number(record.analysisTime),
    );
    const targetIndex = startIndex + Number(record.period);

    if (
      startIndex < 0 ||
      targetIndex >= ordered.length ||
      !finite(record.predictionPrice) ||
      Number(record.predictionPrice) === 0
    ) {
      return record;
    }

    const actualPrice = Number(ordered[targetIndex].close);

    if (!finite(actualPrice)) {
      return record;
    }

    const actualReturn =
      ((actualPrice - Number(record.predictionPrice)) /
        Number(record.predictionPrice)) *
      100;
    const outcome = resolvedOutcomeFor(record, actualReturn);

    changed = true;
    const forecastError = finite(record.expectedReturn)
      ? actualReturn - Number(record.expectedReturn)
      : null;

    return {
      ...record,
      actualPrice,
      actualReturn,
      ...outcome,
      forecastError,
      absoluteForecastError: finite(forecastError)
        ? Math.abs(forecastError)
        : null,
      squaredForecastError: finite(forecastError)
        ? forecastError ** 2
        : null,
      status: "resolved",
      resolvedAt: new Date(ordered[targetIndex].time * 1000).toISOString(),
    };
  });

  return {
    records: nextRecords,
    changed,
  };
}

function createFactorScoreMap(factors) {
  return Object.fromEntries(
    factors
      .filter((factor) => factor.available)
      .map((factor) => [factor.key, factor.score]),
  );
}

function candidateIndexes(candleCount, horizon, maximumSamples) {
  const finalStart = candleCount - horizon;
  const spacing = Math.max(horizon, 5);
  const indexes = [];

  for (
    let index = BACKTEST_SPLIT.minimumHistory - 1;
    index < finalStart;
    index += spacing
  ) {
    indexes.push(index);
  }

  return indexes.slice(-maximumSamples);
}

function splitIndexes(indexes) {
  const minimum = BACKTEST_SPLIT.minimumPartitionSamples;

  if (indexes.length < minimum * 3) {
    throw new Error(
      `時系列分割には少なくとも${minimum * 3}件の非重複サンプルが必要です。`,
    );
  }

  let trainingEnd = Math.floor(indexes.length * BACKTEST_SPLIT.training);
  let validationEnd =
    trainingEnd + Math.floor(indexes.length * BACKTEST_SPLIT.validation);

  trainingEnd = Math.max(minimum, trainingEnd);
  validationEnd = Math.max(trainingEnd + minimum, validationEnd);
  validationEnd = Math.min(indexes.length - minimum, validationEnd);

  return {
    training: indexes.slice(0, trainingEnd),
    validation: indexes.slice(trainingEnd, validationEnd),
    test: indexes.slice(validationEnd),
  };
}

function makeRecord({
  candles,
  index,
  horizon,
  symbol,
  companyName,
  industry,
  weights,
  partition,
  costs,
  quality,
  calibration = DEFAULT_MODEL_CALIBRATION,
}) {
  const visibleCandles = candles.slice(0, index + 1);
  const indicators = calculateIndicators(visibleCandles, {
    validated: true,
  });
  const calculationValidation = validateIndicatorCalculations(
    indicators,
    visibleCandles,
  );

  if (!calculationValidation.canScore) {
    throw new Error(
      `指標再計算の検証に失敗しました: ${calculationValidation.blockingIssues
        .map((item) => item.message)
        .join(" / ")}`,
    );
  }

  const analysis = scoreAnalysis({
    indicators,
    context: {},
    weights,
  });
  const prediction = createPredictionOutput({
    analysis,
    indicators,
    quality,
    period: horizon,
    records: [],
    symbol,
    marketEnvironment: null,
    calibration,
  });
  const predictionPrice = Number(candles[index].close);
  const actualPrice = Number(candles[index + horizon].close);
  const actualReturn =
    ((actualPrice - predictionPrice) / predictionPrice) * 100;
  const outcome = evaluateResolvedPrediction({
    direction: prediction.direction,
    actualReturn,
    threshold: prediction.evaluationThreshold,
    decision: prediction.decision,
    costs,
  });
  const forecastError = finite(prediction.expectedReturn)
    ? actualReturn - prediction.expectedReturn
    : null;
  const record = createPredictionRecord({
    symbol,
    companyName,
    industry,
    period: horizon,
    score: analysis.totalScore,
    reasons: analysis.factors
      .filter((factor) => factor.available)
      .map((factor) => factor.reason),
    predictionPrice,
    analysisTime: candles[index].time,
    factorScores: createFactorScoreMap(analysis.factors),
    direction: prediction.direction,
    expectedReturn: prediction.expectedReturn,
    expectedMoveRange: prediction.expectedMoveRange,
    downsideRisk: prediction.downsideRisk,
    confidence: prediction.confidence,
    features: extractPredictionFeatures(indicators),
    dataQuality: {
      status: quality.status,
      qualityScore: quality.qualityScore,
      missingRate: quality.missingRate,
    },
    modelVersion: prediction.modelVersion,
    evaluationPolicy: prediction.evaluationPolicy,
    evaluationThreshold: prediction.evaluationThreshold,
    decision: prediction.decision,
    modelCalibration: prediction.modelCalibration,
    partition,
    costAssumptions: costs,
    source: "walk-forward",
  });

  return {
    ...record,
    actualPrice,
    actualReturn,
    ...outcome,
    forecastError,
    absoluteForecastError: finite(forecastError)
      ? Math.abs(forecastError)
      : null,
    squaredForecastError: finite(forecastError)
      ? forecastError ** 2
      : null,
    status: "resolved",
    resolvedAt: new Date(candles[index + horizon].time * 1000).toISOString(),
    audit: {
      featureEndTime: candles[index].time,
      outcomeTime: candles[index + horizon].time,
      sourceCandleCount: visibleCandles.length,
    },
  };
}

function buildPartitionRecords(
  options,
  indexes,
  weights,
  partition,
  calibration = DEFAULT_MODEL_CALIBRATION,
) {
  return indexes.map((index) =>
    makeRecord({
      ...options,
      index,
      weights,
      partition,
      calibration,
    }),
  );
}

function recalibrateRecord(
  record,
  calibration,
  costs = BACKTEST_COSTS,
) {
  const normalized = normalizeModelCalibration(calibration);
  const direction = directionFromScore(record.score, normalized);
  const decision = deriveTradeDecision({
    direction,
    confidenceScore: record.confidence?.score,
    dataQualityScore: record.dataQuality?.qualityScore,
    policy: {
      minimumConfidenceScore: normalized.minimumConfidenceScore,
    },
  });
  const outcome = evaluateResolvedPrediction({
    direction,
    actualReturn: record.actualReturn,
    threshold: record.evaluationThreshold,
    decision,
    costs: record.costAssumptions || costs,
  });

  return {
    ...record,
    direction,
    decision,
    evaluationPolicy: decision.policy,
    modelCalibration: normalized,
    ...outcome,
  };
}

function recalibrateRecords(records, calibration, costs) {
  return records.map((record) =>
    recalibrateRecord(record, calibration, costs),
  );
}

function applyContinuousModelToRecord(
  record,
  model,
  calibration,
  costs = BACKTEST_COSTS,
) {
  const score = predictContinuousScore(model, record);

  if (!finite(score)) {
    return null;
  }

  return recalibrateRecord(
    {
      ...record,
      ruleScore: finite(record.ruleScore)
        ? Number(record.ruleScore)
        : Number(record.score),
      score,
      scoringModel: {
        key: "continuous",
        version: model.version,
        candidateId: model.candidateId || null,
        trainingSampleCount: model.sampleCount,
      },
    },
    calibration,
    costs,
  );
}

function applyContinuousModelToRecords(
  records,
  model,
  calibration,
  costs = BACKTEST_COSTS,
) {
  return records
    .map((record) =>
      applyContinuousModelToRecord(
        record,
        model,
        calibration,
        costs,
      ),
    )
    .filter(Boolean);
}

function isBetterCandidate(candidate, current) {
  if (candidate.objective > current.objective + 1e-9) {
    return true;
  }

  if (Math.abs(candidate.objective - current.objective) > 1e-9) {
    return false;
  }

  const candidateWinRate = Number(candidate.metrics.winRate || 0);
  const currentWinRate = Number(current.metrics.winRate || 0);

  if (candidateWinRate !== currentWinRate) {
    return candidateWinRate > currentWinRate;
  }

  return (
    Number(candidate.metrics.coverageRate || 0) >
    Number(current.metrics.coverageRate || 0)
  );
}

function validationObjective(records) {
  const metrics = summarizePerformance(records);

  if (!finite(metrics.averageReturn)) {
    return Number.NEGATIVE_INFINITY;
  }

  return metrics.averageReturn - Math.abs(metrics.maximumDrawdown || 0) * 0.1;
}

export function runWalkForwardBacktest({
  candles,
  symbol,
  companyName,
  industry,
  period,
  weights,
  maximumSamples = 300,
  costs = BACKTEST_COSTS,
  historyMetadata = {},
  calibration = DEFAULT_MODEL_CALIBRATION,
}) {
  const horizon = Number(period);
  const quality = validateHistoryData(
    {
      ...historyMetadata,
      symbol,
      candles,
      sourceQuality: {
        ...historyMetadata.sourceQuality,
        sourceRowCount: candles.length,
        adjustedCloseCount: candles.filter(
          (candle) => candle.adjustedCloseProvided,
        ).length,
      },
    },
    {
      minimumHistory: BACKTEST_SPLIT.minimumHistory + horizon,
    },
  );

  if (!quality.canScore) {
    throw new Error(
      `バックテストを停止しました: ${quality.blockingIssues
        .map((item) => item.message)
        .join(" / ")}`,
    );
  }

  const ordered = quality.candles;
  const indexes = candidateIndexes(ordered.length, horizon, maximumSamples);
  const partitions = splitIndexes(indexes);
  const shared = {
    candles: ordered,
    horizon,
    symbol,
    companyName,
    industry,
    costs,
    quality,
  };
  const baselineCalibration = normalizeModelCalibration(calibration);
  const training = buildPartitionRecords(
    shared,
    partitions.training,
    weights,
    "training",
    baselineCalibration,
  );
  const optimizationRecords = training.filter(
    (record) => record.hit === true || record.hit === false,
  );
  const optimized = deriveOptimizedWeights(optimizationRecords, weights);
  const weightCandidates = [
    {
      key: "base",
      weights,
    },
  ];

  if (optimized.updated) {
    weightCandidates.push({
      key: "optimized",
      weights: optimized.weights,
    });
  }

  const calibrationCandidates =
    generateCalibrationCandidates(baselineCalibration);
  const validationBase = buildPartitionRecords(
    shared,
    partitions.validation,
    weights,
    "validation",
    baselineCalibration,
  );
  const validationBaseMetrics = summarizePerformance(validationBase);
  const validationBaseObjective = validationObjective(validationBase);
  const minimumCandidateCoverage =
    Number(validationBaseMetrics.coverageRate || 0) * 0.8;
  let selected = {
    modelKey: "rule",
    weightKey: "base",
    weights,
    calibration: baselineCalibration,
    records: validationBase,
    metrics: validationBaseMetrics,
    objective: validationBaseObjective,
  };

  weightCandidates.forEach((weightCandidate) => {
    const rawValidation =
      weightCandidate.key === "base"
        ? validationBase
        : buildPartitionRecords(
            shared,
            partitions.validation,
            weightCandidate.weights,
            "validation",
            baselineCalibration,
          );

    calibrationCandidates.forEach((candidateCalibration) => {
      const records = recalibrateRecords(
        rawValidation,
        candidateCalibration,
        costs,
      );
      const metrics = summarizePerformance(records);
      const objective = validationObjective(records);

      if (
        metrics.sampleCount < BACKTEST_SPLIT.minimumPartitionSamples ||
        Number(metrics.coverageRate || 0) < minimumCandidateCoverage ||
        !Number.isFinite(objective)
      ) {
        return;
      }

      const candidate = {
        modelKey: "rule",
        weightKey: weightCandidate.key,
        weights: weightCandidate.weights,
        calibration: candidateCalibration,
        records,
        metrics,
        objective,
      };

      if (isBetterCandidate(candidate, selected)) {
        selected = candidate;
      }
    });
  });

  const continuousModels = fitContinuousModelCandidates(training, {
    minimumSamples: Math.max(
      20,
      BACKTEST_SPLIT.minimumPartitionSamples * 2,
    ),
  });
  const readyContinuousModels = continuousModels.filter(
    (model) => model.ready,
  );

  readyContinuousModels.forEach((continuousModel) => {
    calibrationCandidates.forEach((candidateCalibration) => {
      const records = applyContinuousModelToRecords(
        validationBase,
        continuousModel,
        candidateCalibration,
        costs,
      );
      const metrics = summarizePerformance(records);
      const objective = validationObjective(records);

      if (
        metrics.sampleCount < BACKTEST_SPLIT.minimumPartitionSamples ||
        Number(metrics.coverageRate || 0) < minimumCandidateCoverage ||
        !Number.isFinite(objective)
      ) {
        return;
      }

      const candidate = {
        modelKey: "continuous",
        weightKey: "base",
        weights,
        calibration: candidateCalibration,
        records,
        metrics,
        objective,
        continuousModel,
      };

      if (isBetterCandidate(candidate, selected)) {
        selected = candidate;
      }
    });
  });
  const selectedWeights = selected.weights;
  const selectedCalibration = selected.calibration;
  const selectedModelKey = selected.modelKey || "rule";
  const selectedContinuousModel =
    selectedModelKey === "continuous"
      ? selected.continuousModel || null
      : null;
  const validation = selected.records;
  const acceptedOptimizedWeights = selected.weightKey === "optimized";
  const acceptedCalibration = !sameCalibration(
    selectedCalibration,
    baselineCalibration,
  );
  const ruleTest = buildPartitionRecords(
    shared,
    partitions.test,
    selectedWeights,
    "test",
    selectedCalibration,
  );
  const test =
    selectedModelKey === "continuous"
      ? applyContinuousModelToRecords(
          ruleTest,
          selectedContinuousModel,
          selectedCalibration,
          costs,
        )
      : ruleTest;

  return {
    records: [...training, ...validation, ...test],
    selectedWeights,
    selectedCalibration,
    meta: {
      method: "anchored-walk-forward",
      spacingSessions: Math.max(horizon, 5),
      chronological: true,
      featureLeakageGuard: "各評価時点以前のローソク足だけで指標を再計算",
      weightsFrozenAfterTraining: true,
      calibrationFrozenBeforeTest: true,
      scoringModelFrozenBeforeTest: true,
      optimizedWeightsAccepted: acceptedOptimizedWeights,
      optimizerMessage: optimized.message,
      calibration: {
        baseline: baselineCalibration,
        selected: selectedCalibration,
        accepted: acceptedCalibration,
        candidateCount: calibrationCandidates.length,
      },
      modelSelection: {
        baseline: "rule",
        selected: selectedModelKey,
        selectedLabel:
          selectedModelKey === "continuous"
            ? "連続値モデル"
            : "現行ルールモデル",
        continuousReady: readyContinuousModels.length > 0,
        continuousAccepted: selectedModelKey === "continuous",
        continuousVersion:
          selectedContinuousModel?.version ||
          readyContinuousModels[0]?.version ||
          continuousModels[0]?.version ||
          null,
        continuousCandidateCount: continuousModels.length,
        continuousReadyCandidateCount: readyContinuousModels.length,
        selectedCandidateId:
          selectedContinuousModel?.candidateId || null,
        trainingSampleCount:
          selectedContinuousModel?.sampleCount ||
          readyContinuousModels[0]?.sampleCount ||
          continuousModels[0]?.sampleCount ||
          0,
        trainingLoss:
          selectedContinuousModel?.trainingLoss ?? null,
        reason:
          readyContinuousModels.length > 0
            ? null
            : continuousModels[0]?.reason || null,
      },
      validationComparison: {
        baseline: validationBaseMetrics,
        selected: selected.metrics,
        baselineObjective: validationBaseObjective,
        selectedObjective: selected.objective,
      },
      costs: {
        ...costs,
        roundTripPercent: roundTripCostPercent(costs),
      },
      partitions: {
        training: training.length,
        validation: validation.length,
        test: test.length,
      },
      quality: {
        status: quality.status,
        qualityScore: quality.qualityScore,
        missingRate: quality.missingRate,
      },
    },
  };
}

function returnsFor(records) {
  return records.map((record) => {
    if (finite(record.strategyReturn)) {
      return Number(record.strategyReturn);
    }

    const actualReturn = Number(record.actualReturn);

    if (!finite(actualReturn)) {
      return null;
    }

    return outcomeFor({
      score: record.score,
      actualReturn,
      costs: record.costAssumptions || {
        commissionBpsPerSide: 0,
        slippageBpsPerSide: 0,
      },
    }).strategyReturn;
  });
}

function streaks(records) {
  let currentType = null;
  let currentLength = 0;
  let maximumWins = 0;
  let maximumLosses = 0;

  records.forEach((record) => {
    const type = record.hit ? "win" : "loss";

    currentLength = type === currentType ? currentLength + 1 : 1;
    currentType = type;

    if (type === "win") {
      maximumWins = Math.max(maximumWins, currentLength);
    } else {
      maximumLosses = Math.max(maximumLosses, currentLength);
    }
  });

  return {
    maximumWins,
    maximumLosses,
  };
}

function maximumDrawdown(returns) {
  let equity = 1;
  let peak = 1;
  let worst = 0;

  returns.forEach((value) => {
    equity *= Math.max(0, 1 + value / 100);
    peak = Math.max(peak, equity);
    worst = Math.min(worst, ((equity - peak) / peak) * 100);
  });

  return worst;
}

function wilsonInterval(wins, sampleCount, z = 1.96) {
  if (!sampleCount) {
    return {
      lower: null,
      upper: null,
      level: 95,
    };
  }

  const probability = wins / sampleCount;
  const denominator = 1 + (z * z) / sampleCount;
  const center = (probability + (z * z) / (2 * sampleCount)) / denominator;
  const margin =
    (z *
      Math.sqrt(
        (probability * (1 - probability)) / sampleCount +
          (z * z) / (4 * sampleCount * sampleCount),
      )) /
    denominator;

  return {
    lower: Math.max(0, (center - margin) * 100),
    upper: Math.min(100, (center + margin) * 100),
    level: 95,
  };
}

export function summarizePerformance(allRecords) {
  const resolved = allRecords
    .filter(
      (record) => record.status === "resolved" && finite(record.actualReturn),
    )
    .sort(
      (first, second) =>
        new Date(first.resolvedAt || first.createdAt) -
        new Date(second.resolvedAt || second.createdAt),
    );
  const records = resolved.filter(
    (record) => record.hit === true || record.hit === false,
  );
  const abstainCount = resolved.length - records.length;
  const wins = records.filter((record) => record.hit);
  const returns = returnsFor(records).filter(finite);
  const positiveReturns = returns.filter((value) => value > 0);
  const negativeReturns = returns.filter((value) => value < 0);
  const deviation = standardDeviation(returns);
  const averagePeriod =
    average(records.map((record) => Number(record.period) || 1)) || 1;
  const totalProfit = positiveReturns.reduce((sum, value) => sum + value, 0);
  const totalLoss = Math.abs(
    negativeReturns.reduce((sum, value) => sum + value, 0),
  );

  return {
    resolvedCount: resolved.length,
    sampleCount: records.length,
    abstainCount,
    coverageRate: resolved.length
      ? (records.length / resolved.length) * 100
      : null,
    winRate: records.length ? (wins.length / records.length) * 100 : null,
    winRateConfidenceInterval: wilsonInterval(wins.length, records.length),
    averageReturn: average(returns),
    medianReturn: median(returns),
    averageProfit: average(positiveReturns),
    averageLoss: average(negativeReturns),
    maximumDrawdown: returns.length ? maximumDrawdown(returns) : null,
    profitFactor:
      totalLoss > 0
        ? totalProfit / totalLoss
        : totalProfit > 0
          ? Infinity
          : null,
    totalTradingCost: records.reduce(
      (sum, record) => sum + (Number(record.tradingCost) || 0),
      0,
    ),
    sharpe:
      deviation && deviation !== 0
        ? (average(returns) / deviation) * Math.sqrt(252 / averagePeriod)
        : null,
    ...streaks(records),
  };
}

export function groupPerformance(records, keyResolver) {
  const groups = new Map();

  records
    .filter((record) => record.status === "resolved")
    .forEach((record) => {
      const key = keyResolver(record);

      if (!groups.has(key)) {
        groups.set(key, []);
      }

      groups.get(key).push(record);
    });

  return Array.from(groups.entries())
    .map(([key, items]) => ({
      key,
      ...summarizePerformance(items),
    }))
    .sort((first, second) => second.sampleCount - first.sampleCount);
}

export const BacktestInternals = {
  determineHit,
  outcomeFor,
  roundTripCostPercent,
  splitIndexes,
  candidateIndexes,
  maximumDrawdown,
  wilsonInterval,
  median,
  recalibrateRecord,
  recalibrateRecords,
  applyContinuousModelToRecord,
  applyContinuousModelToRecords,
  validationObjective,
  isBetterCandidate,
};
