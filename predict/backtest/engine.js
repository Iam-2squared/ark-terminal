import { calculateIndicators } from "../analysis/indicators.js";

import { scoreAnalysis } from "../analysis/scoring.js";

import { createPredictionRecord } from "./storage.js";

function finite(value) {
  return Number.isFinite(Number(value));
}

function determineHit(score, actualReturn) {
  if (score >= 55) {
    return actualReturn > 0;
  }

  if (score <= 45) {
    return actualReturn < 0;
  }

  return Math.abs(actualReturn) < 2;
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

    if (startIndex < 0) {
      return record;
    }

    const targetIndex = startIndex + Number(record.period);

    if (targetIndex >= ordered.length) {
      return record;
    }

    const actualPrice = Number(ordered[targetIndex].close);

    const predictionPrice = Number(record.predictionPrice);

    if (
      !finite(actualPrice) ||
      !finite(predictionPrice) ||
      predictionPrice === 0
    ) {
      return record;
    }

    const actualReturn =
      ((actualPrice - predictionPrice) / predictionPrice) * 100;

    const hit = determineHit(Number(record.score), actualReturn);

    changed = true;

    return {
      ...record,
      actualPrice,
      actualReturn,
      hit,
      outcome: hit ? "的中" : "外れ",
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

export function runWalkForwardBacktest({
  candles,
  symbol,
  companyName,
  industry,
  period,
  weights,
  maximumSamples = 120,
}) {
  const horizon = Number(period);

  const minimumHistory = 200;

  if (candles.length < minimumHistory + horizon + 1) {
    throw new Error("バックテストには200営業日以上の履歴が必要です。");
  }

  const finalStart = candles.length - horizon;

  const firstStart = Math.max(minimumHistory, finalStart - maximumSamples);

  const records = [];

  for (let index = firstStart; index < finalStart; index += 1) {
    const visibleCandles = candles.slice(0, index + 1);

    const indicators = calculateIndicators(visibleCandles);

    const analysis = scoreAnalysis({
      indicators,
      context: {},
      weights,
    });

    const predictionPrice = Number(candles[index].close);

    const actualPrice = Number(candles[index + horizon].close);

    const actualReturn =
      ((actualPrice - predictionPrice) / predictionPrice) * 100;

    const hit = determineHit(analysis.totalScore, actualReturn);

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
      source: "walk-forward",
    });

    records.push({
      ...record,
      actualPrice,
      actualReturn,
      hit,
      outcome: hit ? "的中" : "外れ",
      status: "resolved",
      resolvedAt: new Date(candles[index + horizon].time * 1000).toISOString(),
    });
  }

  return records;
}

function average(values) {
  return values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length
    : null;
}

function standardDeviation(values) {
  if (values.length < 2) {
    return null;
  }

  const valueAverage = average(values);

  const variance = average(values.map((value) => (value - valueAverage) ** 2));

  return Math.sqrt(variance);
}

function streaks(records) {
  let currentType = null;
  let currentLength = 0;
  let maximumWins = 0;
  let maximumLosses = 0;

  records.forEach((record) => {
    const type = record.hit ? "win" : "loss";

    if (type === currentType) {
      currentLength += 1;
    } else {
      currentType = type;
      currentLength = 1;
    }

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

  const losses = records.filter((record) => !record.hit);

  const returns = records.map((record) => Number(record.actualReturn));

  const positiveReturns = returns.filter((value) => value > 0);

  const negativeReturns = returns.filter((value) => value < 0);

  const deviation = standardDeviation(returns);

  const averagePeriod =
    average(records.map((record) => Number(record.period) || 1)) || 1;

  const sharpe =
    deviation && deviation !== 0
      ? (average(returns) / deviation) * Math.sqrt(252 / averagePeriod)
      : null;

  return {
    sampleCount: records.length,
    winRate: records.length ? (wins.length / records.length) * 100 : null,
    averageReturn: average(returns),
    averageProfit: average(positiveReturns),
    averageLoss: average(negativeReturns),
    sharpe,
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
};
