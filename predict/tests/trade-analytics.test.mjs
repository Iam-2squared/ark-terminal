import test from "node:test";
import assert from "node:assert/strict";

import {
  calculateTradeExcursion,
  groupTradesByExitReason,
  normalizeTradeAnalyticsRow,
  summarizeTradeAnalytics,
} from "../trading/trade-analytics.js";

test(
  "LONGのMFEとMAEを計算",
  () => {
    const result =
      calculateTradeExcursion({
        side: "long",
        entryPrice: 100,
        highestPrice: 110,
        lowestPrice: 95,
      });

    assert.equal(
      result.mfePercent,
      10,
    );

    assert.equal(
      result.maePercent,
      -5,
    );
  },
);

test(
  "SHORTのMFEとMAEを計算",
  () => {
    const result =
      calculateTradeExcursion({
        side: "short",
        entryPrice: 100,
        highestPrice: 105,
        lowestPrice: 90,
      });

    assert.equal(
      result.mfePercent,
      10,
    );

    assert.equal(
      result.maePercent,
      -5,
    );
  },
);

test(
  "取引行を正規化",
  () => {
    const row =
      normalizeTradeAnalyticsRow({
        side: "long",
        entryPrice: 100,
        exitPrice: 105,
        highestPrice: 108,
        lowestPrice: 98,
        netPnl: 500,
        tradingCost: 40,
        barsHeld: 4,
        reason: "second_target",
      });

    assert.equal(
      row.returnPercent,
      5,
    );

    assert.equal(
      row.mfePercent,
      8,
    );

    assert.equal(
      row.maePercent,
      -2,
    );

    assert.equal(
      row.totalTradingCost,
      40,
    );

    assert.equal(
      row.holdingBars,
      4,
    );

    assert.equal(
      row.exitReason,
      "second_target",
    );
  },
);

test(
  "平均利益・平均損失・期待値・損益比を計算",
  () => {
    const summary =
      summarizeTradeAnalytics([
        {
          netPnl: 1_000,
          grossPnl: 1_100,
          totalTradingCost: 100,
          holdingBars: 4,
          mfePercent: 2,
          maePercent: -0.5,
          exitReason: "target",
        },
        {
          netPnl: 500,
          grossPnl: 550,
          totalTradingCost: 50,
          holdingBars: 6,
          mfePercent: 1.5,
          maePercent: -0.3,
          exitReason: "target",
        },
        {
          netPnl: -600,
          grossPnl: -500,
          totalTradingCost: 100,
          holdingBars: 3,
          mfePercent: 0.4,
          maePercent: -1.2,
          exitReason: "stop",
        },
        {
          netPnl: -400,
          grossPnl: -350,
          totalTradingCost: 50,
          holdingBars: 5,
          mfePercent: 0.2,
          maePercent: -0.8,
          exitReason: "stop",
        },
      ]);

    assert.equal(
      summary.tradeCount,
      4,
    );

    assert.equal(
      summary.winRate,
      50,
    );

    assert.equal(
      summary.averageWin,
      750,
    );

    assert.equal(
      summary.averageLoss,
      -500,
    );

    assert.equal(
      summary.payoffRatio,
      1.5,
    );

    assert.equal(
      summary.expectancy,
      125,
    );

    assert.equal(
      summary.profitFactor,
      1.5,
    );

    assert.equal(
      summary.totalTradingCost,
      300,
    );

    assert.equal(
      summary.grossPnlBeforeCosts,
      800,
    );

    assert.equal(
      summary.totalNetPnl,
      500,
    );
  },
);

test(
  "決済理由別に集計",
  () => {
    const grouped =
      groupTradesByExitReason([
        {
          netPnl: 500,
          exitReason: "target",
        },
        {
          netPnl: 300,
          exitReason: "target",
        },
        {
          netPnl: -200,
          exitReason: "stop",
        },
      ]);

    assert.equal(
      grouped.target.count,
      2,
    );

    assert.equal(
      grouped.target.winRate,
      100,
    );

    assert.equal(
      grouped.target.totalNetPnl,
      800,
    );

    assert.equal(
      grouped.stop.count,
      1,
    );

    assert.equal(
      grouped.stop.winRate,
      0,
    );

    assert.equal(
      grouped.stop.totalNetPnl,
      -200,
    );
  },
);

test(
  "空配列でも安全に集計",
  () => {
    const summary =
      summarizeTradeAnalytics([]);

    assert.equal(
      summary.tradeCount,
      0,
    );

    assert.equal(
      summary.winRate,
      null,
    );

    assert.equal(
      summary.expectancy,
      null,
    );

    assert.deepEqual(
      summary.byExitReason,
      {},
    );
  },
);
