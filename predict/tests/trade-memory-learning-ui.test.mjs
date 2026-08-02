import assert from "node:assert/strict";
import test from "node:test";

import {
  createTradeMemoryLearningViewModel,
} from "../learning/trade-memory-learning-ui.js";

function resolvedRecord(
  index,
  overrides = {},
) {
  return {
    id:
      `record-${index}`,

    status:
      "resolved",

    decision:
      "approve",

    evaluation: {
      hit: true,

      actualReturnPercent:
        5,

      maximumFavorableMovePercent:
        8,

      maximumAdverseMovePercent:
        -2,
    },

    intraday: {
      volumeRatio:
        1.5,

      setupStrengthScore:
        82,

      dataQualityScore:
        95,
    },

    daily: {
      marketRegime:
        "bullish",

      indicators: {
        currentPrice:
          110,

        rsi:
          52,

        movingAverages: {
          ma25:
            100,

          ma75:
            90,
        },

        macd: {
          histogram:
            5,
        },

        adx:
          28,
      },
    },

    ...overrides,
  };
}

function records(count) {
  return Array.from(
    {
      length: count,
    },

    (_, index) =>
      resolvedRecord(index),
  );
}

test(
  "学習UI用の集計モデルを生成する",
  () => {
    const result =
      createTradeMemoryLearningViewModel(
        records(20),
        {
          rsi: 1,
          macd: 1,
          volume: 1,
        },
      );

    assert.equal(
      result.resolvedApprovalCount,
      20,
    );

    assert.equal(
      result.totalSignalCount,
      8,
    );

    assert.ok(
      result.rows.length > 0,
    );
  },
);

test(
  "十分な学習件数では引き上げ候補を表示する",
  () => {
    const result =
      createTradeMemoryLearningViewModel(
        records(50),
        {
          rsi: 1,
        },
      );

    const rsi =
      result.rows.find(
        (row) =>
          row.key === "rsi",
      );

    assert.equal(
      rsi.enoughData,
      true,
    );

    assert.equal(
      rsi.direction,
      "up",
    );

    assert.ok(
      rsi.suggestedWeight >
      rsi.baseWeight,
    );
  },
);

test(
  "件数不足ではデータ不足として表示する",
  () => {
    const result =
      createTradeMemoryLearningViewModel(
        records(5),
        {
          rsi: 1,
        },
      );

    const rsi =
      result.rows.find(
        (row) =>
          row.key === "rsi",
      );

    assert.equal(
      rsi.enoughData,
      false,
    );

    assert.equal(
      rsi.direction,
      "insufficient",
    );

    assert.equal(
      rsi.suggestedWeight,
      rsi.baseWeight,
    );
  },
);