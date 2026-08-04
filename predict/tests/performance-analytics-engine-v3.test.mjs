import test from "node:test";
import assert from "node:assert/strict";

import {
  PerformanceAnalyticsEngineV3,
  analyzePerformance,
} from "../portfolio/performance-analytics-engine-v3.js";

const NOW =
  "2026-08-04T16:00:00.000Z";

function equityCurve() {
  return [
    {
      timestamp:
        "2026-01-01T00:00:00.000Z",

      equity:
        100000,
    },
    {
      timestamp:
        "2026-01-02T00:00:00.000Z",

      equity:
        105000,
    },
    {
      timestamp:
        "2026-01-03T00:00:00.000Z",

      equity:
        102000,
    },
    {
      timestamp:
        "2026-01-04T00:00:00.000Z",

      equity:
        110000,
    },
  ];
}

function trades() {
  return [
    {
      id:
        "T1",

      symbol:
        "7203.T",

      strategy:
        "SWING",

      pnl:
        5000,

      timestamp:
        "2026-01-02T00:00:00.000Z",
    },
    {
      id:
        "T2",

      symbol:
        "8306.T",

      strategy:
        "SWING",

      pnl:
        -3000,

      timestamp:
        "2026-01-03T00:00:00.000Z",
    },
    {
      id:
        "T3",

      symbol:
        "7203.T",

      strategy:
        "BREAKOUT",

      pnl:
        8000,

      timestamp:
        "2026-01-04T00:00:00.000Z",
    },
  ];
}

test(
  "Calculates total return",
  () => {
    const result =
      analyzePerformance({
        equityCurve:
          equityCurve(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.summary
        .totalReturnPercent,
      10,
    );

    assert.equal(
      result.summary
        .netProfit,
      10000,
    );
  },
);

test(
  "Calculates maximum drawdown",
  () => {
    const result =
      analyzePerformance({
        equityCurve:
          equityCurve(),

        timestamp:
          NOW,
      });

    assert.ok(
      result.summary
        .maximumDrawdownPercent >
      0,
    );

    assert.equal(
      result.summary
        .maximumDrawdownAmount,
      3000,
    );
  },
);

test(
  "Calculates trade win rate",
  () => {
    const result =
      analyzePerformance({
        equityCurve:
          equityCurve(),

        trades:
          trades(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.trades.tradeCount,
      3,
    );

    assert.equal(
      result.trades.winCount,
      2,
    );

    assert.equal(
      result.trades.lossCount,
      1,
    );

    assert.equal(
      result.trades.winRate,
      66.666667,
    );
  },
);

test(
  "Calculates profit factor",
  () => {
    const result =
      analyzePerformance({
        equityCurve:
          equityCurve(),

        trades:
          trades(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.trades
        .profitFactor,
      4.333333,
    );
  },
);

test(
  "Calculates expectancy",
  () => {
    const result =
      analyzePerformance({
        equityCurve:
          equityCurve(),

        trades:
          trades(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.trades.expectancy,
      3333.333333,
    );
  },
);

test(
  "Calculates symbol breakdown",
  () => {
    const result =
      analyzePerformance({
        equityCurve:
          equityCurve(),

        trades:
          trades(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.breakdown
        .bySymbol["7203.T"]
        .tradeCount,
      2,
    );

    assert.equal(
      result.breakdown
        .bySymbol["7203.T"]
        .netPnl,
      13000,
    );
  },
);

test(
  "Calculates strategy breakdown",
  () => {
    const result =
      analyzePerformance({
        equityCurve:
          equityCurve(),

        trades:
          trades(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.breakdown
        .byStrategy.SWING
        .netPnl,
      2000,
    );

    assert.equal(
      result.breakdown
        .byStrategy.BREAKOUT
        .netPnl,
      8000,
    );
  },
);

test(
  "Compares benchmark performance",
  () => {
    const result =
      analyzePerformance({
        equityCurve:
          equityCurve(),

        benchmarkCurve: [
          {
            timestamp:
              "2026-01-01T00:00:00.000Z",

            equity:
              100000,
          },
          {
            timestamp:
              "2026-01-04T00:00:00.000Z",

            equity:
              105000,
          },
        ],

        timestamp:
          NOW,
      });

    assert.equal(
      result.benchmark
        .totalReturnPercent,
      5,
    );

    assert.equal(
      result.benchmark
        .excessReturnPercent,
      5,
    );

    assert.equal(
      result.benchmark
        .outperformed,
      true,
    );
  },
);

test(
  "Returns daily, weekly and monthly returns",
  () => {
    const result =
      analyzePerformance({
        equityCurve:
          equityCurve(),

        timestamp:
          NOW,
      });

    assert.ok(
      result.periodReturns
        .daily,
    );

    assert.ok(
      result.periodReturns
        .weekly,
    );

    assert.ok(
      result.periodReturns
        .monthly,
    );
  },
);

test(
  "Calculates Sharpe and Sortino ratios",
  () => {
    const result =
      analyzePerformance({
        equityCurve:
          equityCurve(),

        timestamp:
          NOW,
      });

    assert.ok(
      Number.isFinite(
        result.summary
          .sharpeRatio,
      ),
    );

    assert.ok(
      result.summary
        .sortinoRatio !==
      null,
    );
  },
);

test(
  "Engine stores equity points",
  () => {
    const engine =
      new PerformanceAnalyticsEngineV3();

    for (
      const point of
      equityCurve()
    ) {
      engine.addEquityPoint(
        point,
      );
    }

    assert.equal(
      engine.snapshot()
        .equityCurve
        .length,
      4,
    );
  },
);

test(
  "Engine stores trades",
  () => {
    const engine =
      new PerformanceAnalyticsEngineV3();

    for (
      const trade of
      trades()
    ) {
      engine.addTrade(
        trade,
      );
    }

    assert.equal(
      engine.snapshot()
        .trades
        .length,
      3,
    );
  },
);

test(
  "Engine analyzes and stores history",
  () => {
    const engine =
      new PerformanceAnalyticsEngineV3();

    for (
      const point of
      equityCurve()
    ) {
      engine.addEquityPoint(
        point,
      );
    }

    const result =
      engine.analyze({
        timestamp:
          NOW,
      });

    assert.equal(
      result.summary
        .totalReturnPercent,
      10,
    );

    assert.equal(
      engine.getHistory().length,
      1,
    );

    assert.ok(
      engine.latest(),
    );
  },
);

test(
  "Snapshot restore is deterministic",
  () => {
    const original =
      new PerformanceAnalyticsEngineV3();

    for (
      const point of
      equityCurve()
    ) {
      original.addEquityPoint(
        point,
      );
    }

    for (
      const trade of
      trades()
    ) {
      original.addTrade(
        trade,
      );
    }

    const snapshot =
      original.snapshot();

    const restored =
      new PerformanceAnalyticsEngineV3();

    restored.restore(
      snapshot,
    );

    assert.deepEqual(
      restored.snapshot(),
      snapshot,
    );
  },
);

test(
  "Reset clears engine state",
  () => {
    const engine =
      new PerformanceAnalyticsEngineV3();

    for (
      const point of
      equityCurve()
    ) {
      engine.addEquityPoint(
        point,
      );
    }

    engine.reset();

    assert.equal(
      engine.snapshot()
        .equityCurve
        .length,
      0,
    );

    assert.equal(
      engine.getHistory().length,
      0,
    );
  },
);

test(
  "Rejects empty equity curve",
  () => {
    assert.throws(
      () =>
        analyzePerformance({
          equityCurve: [],

          timestamp:
            NOW,
        }),

      /Equity curve is required/,
    );
  },
);

test(
  "Validates timestamp",
  () => {
    assert.throws(
      () =>
        analyzePerformance({
          equityCurve:
            equityCurve(),

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);