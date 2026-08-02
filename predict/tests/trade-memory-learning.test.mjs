import assert from "node:assert/strict";
import test from "node:test";

import {
  analyzeTradeMemoryLearning,
  applyLearningWeightsSafely,
} from "../learning/trade-memory-learning.js";

function resolvedRecord({
  id,
  hit,
  returnPercent,
  rsi = 52,
  macdHistogram = 5,
  volumeRatio = 1.5,
  adx = 28,
  marketRegime = "bullish",
}) {
  return {
    id,
    status: "resolved",
    decision: "approve",

    evaluation: {
      hit,

      actualReturnPercent:
        returnPercent,

      maximumFavorableMovePercent:
        Math.max(
          returnPercent,
          4,
        ),

      maximumAdverseMovePercent:
        returnPercent >= 0
          ? -2
          : returnPercent,
    },

    intraday: {
      volumeRatio,
      setupStrengthScore: 80,
      dataQualityScore: 95,
    },

    daily: {
      marketRegime,

      indicators: {
        currentPrice: 110,
        rsi,

        movingAverages: {
          ma25: 100,
          ma75: 90,
        },

        macd: {
          histogram:
            macdHistogram,
        },

        adx,
      },
    },
  };
}

function winningRecords(count = 12) {
  return Array.from(
    { length: count },
    (_, index) =>
      resolvedRecord({
        id:
          `win-${index}`,

        hit: true,

        returnPercent:
          4 + index * 0.1,
      }),
  );
}

test(
  "解決済みapproveだけを学習対象にする",
  () => {
    const records = [
      ...winningRecords(10),

      {
        id: "pending",
        status: "pending",
        decision: "approve",
      },

      {
        id: "wait",
        status: "resolved",
        decision: "wait",

        evaluation: {
          hit: true,
          actualReturnPercent: 10,
        },
      },
    ];

    const result =
      analyzeTradeMemoryLearning(
        records,
      );

    assert.equal(
      result.resolvedApprovalCount,
      10,
    );
  },
);

test(
  "最低サンプル数未満では重みを変更しない",
  () => {
    const result =
      analyzeTradeMemoryLearning(
        winningRecords(5),
        {
          rsi: 1,
        },
      );

    assert.equal(
      result.metrics.rsi
        .enoughData,
      false,
    );

    assert.equal(
      result.metrics.rsi
        .suggestedWeight,
      1,
    );

    assert.equal(
      result.readyForOptimization,
      false,
    );
  },
);

test(
  "勝率と平均利益が高い指標は重み候補が上がる",
  () => {
    const result =
      analyzeTradeMemoryLearning(
        winningRecords(50),
        {
          rsi: 1,
          macd: 1,
          volume: 1,
        },
      );

    assert.equal(
      result.readyForOptimization,
      true,
    );

    assert.ok(
      result.metrics.rsi
        .suggestedWeight > 1,
    );

    assert.ok(
      result.metrics.macd
        .suggestedWeight > 1,
    );

    assert.ok(
      result.metrics.volume
        .suggestedWeight > 1,
    );
  },
);

test(
  "重み変更幅は最大20パーセント以内",
  () => {
    const result =
      analyzeTradeMemoryLearning(
        winningRecords(100),
        {
          rsi: 2,
        },
      );

    assert.ok(
      result.metrics.rsi
        .suggestedWeight <= 2.4,
    );

    assert.ok(
      result.metrics.rsi
        .suggestedWeight >= 1.6,
    );
  },
);

test(
  "明示承認なしではウェイトを適用しない",
  () => {
    const learning =
      analyzeTradeMemoryLearning(
        winningRecords(50),
        {
          rsi: 1,
        },
      );

    const result =
      applyLearningWeightsSafely(
        {
          rsi: 1,
        },
        learning,
      );

    assert.equal(
      result.applied,
      false,
    );

    assert.equal(
      result.reason,
      "explicit_approval_required",
    );

    assert.equal(
      result.weights.rsi,
      1,
    );
  },
);

test(
  "明示承認ありなら十分なデータの指標だけ適用する",
  () => {
    const learning =
      analyzeTradeMemoryLearning(
        winningRecords(50),
        {
          rsi: 1,
          adx: 1,
        },
      );

    const result =
      applyLearningWeightsSafely(
        {
          rsi: 1,
          adx: 1,
        },
        learning,
        {
          allowApply: true,
        },
      );

    assert.equal(
      result.applied,
      true,
    );

    assert.ok(
      result.weights.rsi > 1,
    );

    assert.ok(
      result.weights.rsi <= 1.2,
    );
  },
);

test(
  "負けが多い指標は重み候補が下がる",
  () => {
    const records =
      Array.from(
        { length: 50 },
        (_, index) =>
          resolvedRecord({
            id:
              `loss-${index}`,

            hit: false,

            returnPercent:
              -4 - index * 0.02,
          }),
      );

    const result =
      analyzeTradeMemoryLearning(
        records,
        {
          rsi: 1,
        },
      );

    assert.ok(
      result.metrics.rsi
        .suggestedWeight < 1,
    );

    assert.ok(
      result.metrics.rsi
        .suggestedWeight >= 0.8,
    );
  },
);