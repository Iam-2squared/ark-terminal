import test from "node:test";
import assert from "node:assert/strict";

import {
  analyzePaperAiPerformance,
} from "../paper/paper-ai-performance-analyzer.js";

test(
  "Paper取引成績を集計",
  () => {
    const result =
      analyzePaperAiPerformance({
        account: {
          initialCash:
            1_000_000,

          totalReturnPercent:
            1.5,

          tradeHistory: [
            {
              symbol:
                "7203.T",
              realizedPnl:
                20_000,
            },
            {
              symbol:
                "7203.T",
              realizedPnl:
                -10_000,
            },
            {
              symbol:
                "6758.T",
              realizedPnl:
                5_000,
            },
          ],
        },

        equityHistory: [
          1_000_000,
          1_020_000,
          1_010_000,
          1_015_000,
        ],
      });

    assert.equal(
      result.metrics.tradeCount,
      3,
    );

    assert.equal(
      result.metrics.winCount,
      2,
    );

    assert.equal(
      result.metrics.lossCount,
      1,
    );

    assert.equal(
      result.metrics.totalPnl,
      15_000,
    );

    assert.equal(
      result.metrics.profitFactor,
      2.5,
    );

    assert.equal(
      result.symbols.length,
      2,
    );
  },
);

test(
  "最大ドローダウンを計算",
  () => {
    const result =
      analyzePaperAiPerformance({
        account: {
          initialCash:
            1_000_000,
          tradeHistory: [],
        },

        equityHistory: [
          1_000_000,
          1_100_000,
          990_000,
        ],
      });

    assert.equal(
      result.metrics
        .maximumDrawdownAmount,
      110_000,
    );

    assert.equal(
      result.metrics
        .maximumDrawdownPercent,
      10,
    );
  },
);

test(
  "少数サンプルを警告",
  () => {
    const result =
      analyzePaperAiPerformance({
        account: {
          initialCash:
            1_000_000,
          tradeHistory: [],
        },
      });

    assert.equal(
      result.dataStatus,
      "insufficient",
    );

    assert.ok(
      result.warnings.includes(
        "sample_size_too_small",
      ),
    );
  },
);