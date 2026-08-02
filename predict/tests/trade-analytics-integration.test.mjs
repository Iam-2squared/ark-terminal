import test from "node:test";
import assert from "node:assert/strict";

import {
  IntradayBacktestModesInternals,
} from "../trading/intraday-backtest-modes.js";

test(
  "取引配列を複数の保存形式から解決できる",
  () => {
    const trades = [
      {
        netPnl: 100,
      },
    ];

    assert.equal(
      IntradayBacktestModesInternals
        .resolveTrades({
          trades,
        }),
      trades,
    );

    assert.equal(
      IntradayBacktestModesInternals
        .resolveTrades({
          tradeHistory:
            trades,
        }),
      trades,
    );

    assert.equal(
      IntradayBacktestModesInternals
        .resolveTrades({
          completedTrades:
            trades,
        }),
      trades,
    );
  },
);

test(
  "取引配列が存在しない場合は空配列",
  () => {
    assert.deepEqual(
      IntradayBacktestModesInternals
        .resolveTrades({}),
      [],
    );
  },
);

test(
  "バックテスト結果から詳細分析を生成",
  () => {
    const analytics =
      IntradayBacktestModesInternals
        .createAnalytics({
          trades: [
            {
              netPnl: 500,
              holdingBars: 4,
              mfePercent: 3,
              maePercent: -1,
              exitReason: "target",
            },
            {
              netPnl: -250,
              holdingBars: 2,
              mfePercent: 0.5,
              maePercent: -2,
              exitReason: "stop",
            },
          ],
        });

    assert.equal(
      analytics.tradeCount,
      2,
    );

    assert.equal(
      analytics.winRate,
      50,
    );

    assert.equal(
      analytics.averageWin,
      500,
    );

    assert.equal(
      analytics.averageLoss,
      -250,
    );

    assert.equal(
      analytics.payoffRatio,
      2,
    );

    assert.equal(
      analytics.expectancy,
      125,
    );

    assert.equal(
      analytics.averageMfePercent,
      1.75,
    );

    assert.equal(
      analytics.averageMaePercent,
      -1.5,
    );
  },
);

test(
  "空の結果でも詳細分析を安全に生成",
  () => {
    const analytics =
      IntradayBacktestModesInternals
        .createAnalytics({});

    assert.equal(
      analytics.tradeCount,
      0,
    );

    assert.equal(
      analytics.expectancy,
      null,
    );
  },
);