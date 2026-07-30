import assert from "node:assert/strict";
import test from "node:test";

import { HistoryInternals } from "../../api/history.js";
import {
  validateIndicatorCalculations,
  validateHistoryData,
} from "../analysis/data-quality.js";
import { calculateIndicators } from "../analysis/indicators.js";
import {
  BacktestInternals,
  runWalkForwardBacktest,
  summarizePerformance,
} from "../backtest/engine.js";
import { DEFAULT_WEIGHTS } from "../config.js";

function candles(count = 320) {
  return Array.from({ length: count }, (_value, index) => {
    const close = 100 + index;

    return {
      time: 1_700_000_000 + index * 86_400,
      open: close,
      high: close + 1,
      low: close - 1,
      close,
      volume: 1_000,
      rawClose: close,
      adjustedClose: close,
      adjustedCloseProvided: true,
      adjustmentFactor: 1,
      volumeAdjustmentFactor: 1,
    };
  });
}

function history(sourceCandles) {
  return {
    symbol: "TEST",
    adjustmentMethod: "test-adjusted",
    meta: {
      currency: "USD",
      priceUnit: "USD",
      volumeUnit: "shares",
    },
    sourceQuality: {
      sourceRowCount: sourceCandles.length,
      droppedRowCount: 0,
      adjustedCloseCount: sourceCandles.filter(
        (candle) => candle.adjustedCloseProvided,
      ).length,
      splitCount: 0,
    },
    candles: sourceCandles,
  };
}

test("adjusted close scales OHLC and split scales historical volume", () => {
  const result = {
    timestamp: [1, 2, 3, 4],
    indicators: {
      quote: [
        {
          open: [100, 102, 51, 52],
          high: [102, 104, 53, 54],
          low: [98, 100, 49, 50],
          close: [100, 102, 51, 52],
          volume: [10, 20, 30, 40],
        },
      ],
      adjclose: [{ adjclose: [50, 51, 51, 52] }],
    },
  };
  const split = [{ time: 3, numerator: 2, denominator: 1, ratio: 2 }];
  const adjusted = HistoryInternals.buildAdjustedCandles(result, split);

  assert.equal(adjusted.candles[0].close, 50);
  assert.equal(adjusted.candles[0].high, 51);
  assert.equal(adjusted.candles[0].volume, 20);
  assert.equal(adjusted.candles[1].volume, 40);
  assert.equal(adjusted.candles[2].volume, 30);
});

test("quality gate passes valid adjusted data and reports duplicate repair", () => {
  const source = candles();
  const report = validateHistoryData(
    history([...source, { ...source[100], close: source[100].close }]),
  );

  assert.equal(report.canScore, true);
  assert.equal(report.duplicateCount, 1);
  assert.equal(report.validRowCount, 320);
  assert.equal(report.audits.adjustedCloseCoverage, 100);
});

test("quality gate stops scoring for missing adjusted close", () => {
  const source = candles();

  source[10].adjustedCloseProvided = false;
  const report = validateHistoryData(history(source));

  assert.equal(report.canScore, false);
  assert.ok(
    report.blockingIssues.some(
      (item) => item.code === "missing-adjusted-close",
    ),
  );
});

test("quality gate stops scoring for extreme adjusted-price outlier", () => {
  const source = candles();

  source[200] = {
    ...source[200],
    open: 1_000,
    high: 1_010,
    low: 990,
    close: 1_000,
    adjustedClose: 1_000,
  };
  const report = validateHistoryData(history(source));

  assert.equal(report.canScore, false);
  assert.ok(
    report.blockingIssues.some((item) => item.code === "extreme-return"),
  );
});

test("MA, 52-week range and daily VWAP approximation are reproducible", () => {
  const source = candles(252);
  const quality = validateHistoryData(history(source));
  const indicators = calculateIndicators(quality.candles, {
    qualityReport: quality,
  });

  assert.equal(indicators.movingAverages.ma5, 349);
  assert.equal(indicators.movingAverages.ma25, 339);
  assert.equal(indicators.movingAverages.ma200, 251.5);
  assert.equal(indicators.high52Week, 352);
  assert.equal(indicators.low52Week, 99);
  assert.equal(indicators.vwap, 341.5);
  assert.equal(indicators.calculationAudit.week52Sessions, 252);
  assert.equal(
    validateIndicatorCalculations(indicators, quality.candles).canScore,
    true,
  );
});

test("calculation audit blocks mismatched MA, 52-week or VWAP results", () => {
  const source = candles(252);
  const quality = validateHistoryData(history(source));
  const indicators = calculateIndicators(quality.candles, {
    qualityReport: quality,
  });
  const report = validateIndicatorCalculations(
    {
      ...indicators,
      vwap: indicators.vwap + 1,
    },
    quality.candles,
  );

  assert.equal(report.canScore, false);
  assert.ok(
    report.blockingIssues.some((item) => item.code === "calculation-vwap"),
  );
});

test("walk-forward partitions are chronological, spaced and leakage-audited", () => {
  const source = candles(620);
  const result = runWalkForwardBacktest({
    candles: source,
    symbol: "TEST",
    companyName: "Test",
    industry: "Test",
    period: 5,
    weights: DEFAULT_WEIGHTS,
    maximumSamples: 60,
    historyMetadata: history(source),
  });
  const order = {
    training: 0,
    validation: 1,
    test: 2,
  };

  assert.ok(result.meta.partitions.training >= 3);
  assert.ok(result.meta.partitions.validation >= 3);
  assert.ok(result.meta.partitions.test >= 3);

  result.records.forEach((record, index) => {
    assert.ok(record.audit.featureEndTime < record.audit.outcomeTime);

    if (index > 0) {
      const previous = result.records[index - 1];

      assert.ok(record.analysisTime - previous.analysisTime >= 5 * 86_400);
      assert.ok(order[record.partition] >= order[previous.partition]);
    }
  });
});

test("performance metrics use cost-adjusted strategy returns", () => {
  const records = [10, -5, 5, -2].map((strategyReturn, index) => ({
    status: "resolved",
    actualReturn: strategyReturn,
    strategyReturn,
    tradingCost: 0.3,
    hit: strategyReturn > 0,
    period: 5,
    resolvedAt: new Date(2025, 0, index + 1).toISOString(),
  }));
  const metrics = summarizePerformance(records);

  assert.equal(metrics.averageReturn, 2);
  assert.equal(metrics.medianReturn, 1.5);
  assert.equal(metrics.profitFactor, 15 / 7);
  assert.equal(metrics.totalTradingCost, 1.2);
  assert.ok(metrics.maximumDrawdown < 0);
  assert.ok(metrics.winRateConfidenceInterval.lower < metrics.winRate);
  assert.ok(metrics.winRateConfidenceInterval.upper > metrics.winRate);
});

test("round-trip costs include commission and slippage on both sides", () => {
  assert.equal(
    BacktestInternals.roundTripCostPercent({
      commissionBpsPerSide: 5,
      slippageBpsPerSide: 10,
    }),
    0.3,
  );
});

test("a small directional gain below costs is not counted as a win", () => {
  const outcome = BacktestInternals.outcomeFor({
    score: 60,
    actualReturn: 0.1,
    costs: {
      commissionBpsPerSide: 5,
      slippageBpsPerSide: 10,
    },
  });

  assert.ok(Math.abs(outcome.strategyReturn + 0.2) < 1e-12);
  assert.equal(outcome.hit, false);
});
