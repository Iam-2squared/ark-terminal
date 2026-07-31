import {
  validateHistoryData,
  validateIndicatorCalculations,
} from "../analysis/data-quality.js";
import { calculateIndicators } from "../analysis/indicators.js";
import { deriveExpectedMove } from "../analysis/prediction-output.js";
import { scoreAnalysis } from "../analysis/scoring.js";
import { deriveOptimizedWeights } from "../analysis/weights.js";
import { BACKTEST_COSTS, BACKTEST_SPLIT } from "../config.js";
import { extractPredictionFeatures } from "../learning/feature-extractor.js";
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

export function determineDirection(score) {
  if (Number(score) >= 55) {
    return "強気";
  }

  if (Number(score) <= 45) {
    return "弱気";
  }

  return "中立";
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
    const outcome = outcomeFor({
      score: record.score,
      actualReturn,
      costs: record.costAssumptions || BACKTEST_COSTS,
    });

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
  const predictionPrice = Number(candles[index].close);
  const actualPrice = Number(candles[index + horizon].close);
  const actualReturn =
    ((actualPrice - predictionPrice) / predictionPrice) * 100;
  const outcome = outcomeFor({
    score: analysis.totalScore,
    actualReturn,
    costs,
  });
  const expectedMove = deriveExpectedMove({
    score: analysis.totalScore,
    atrPercent: indicators.atr?.percent,
    period: horizon,
  });
  const forecastError = finite(expectedMove.expectedReturn)
    ? actualReturn - expectedMove.expectedReturn
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
    direction: outcome.direction,
    expectedReturn: expectedMove.expectedReturn,
    expectedMoveRange: finite(expectedMove.lower)
      ? {
          lower: expectedMove.lower,
          upper: expectedMove.upper,
          amplitude: expectedMove.amplitude,
          center: expectedMove.expectedReturn,
          method: expectedMove.method,
        }
      : null,
    downsideRisk: finite(expectedMove.lower)
      ? Math.abs(Math.min(0, expectedMove.lower))
      : null,
    features: extractPredictionFeatures(indicators),
    dataQuality: {
      status: quality.status,
      qualityScore: quality.qualityScore,
      missingRate: quality.missingRate,
    },
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

function buildPartitionRecords(options, indexes, weights, partition) {
  return indexes.map((index) =>
    makeRecord({
      ...options,
      index,
      weights,
      partition,
    }),
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
  maximumSamples = 120,
  costs = BACKTEST_COSTS,
  historyMetadata = {},
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
  const training = buildPartitionRecords(
    shared,
    partitions.training,
    weights,
    "training",
  );
  const optimized = deriveOptimizedWeights(training, weights);
  const candidateWeights = optimized.updated ? optimized.weights : weights;
  const validationBase = buildPartitionRecords(
    shared,
    partitions.validation,
    weights,
    "validation",
  );
  const validationCandidate = buildPartitionRecords(
    shared,
    partitions.validation,
    candidateWeights,
    "validation",
  );
  const acceptedOptimizedWeights =
    optimized.updated &&
    validationObjective(validationCandidate) >=
      validationObjective(validationBase);
  const selectedWeights = acceptedOptimizedWeights ? candidateWeights : weights;
  const validation = acceptedOptimizedWeights
    ? validationCandidate
    : validationBase;
  const test = buildPartitionRecords(
    shared,
    partitions.test,
    selectedWeights,
    "test",
  );

  return {
    records: [...training, ...validation, ...test],
    selectedWeights,
    meta: {
      method: "anchored-walk-forward",
      spacingSessions: Math.max(horizon, 5),
      chronological: true,
      featureLeakageGuard: "各評価時点以前のローソク足だけで指標を再計算",
      weightsFrozenAfterTraining: true,
      optimizedWeightsAccepted: acceptedOptimizedWeights,
      optimizerMessage: optimized.message,
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
  const records = allRecords
    .filter(
      (record) => record.status === "resolved" && finite(record.actualReturn),
    )
    .sort(
      (first, second) =>
        new Date(first.resolvedAt || first.createdAt) -
        new Date(second.resolvedAt || second.createdAt),
    );
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
    sampleCount: records.length,
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
};
