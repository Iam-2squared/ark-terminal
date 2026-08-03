import test from "node:test";
import assert from "node:assert/strict";

import {
  LearningRuntimeIntegrationV2,
  runLearningRuntimeIntegration,
} from "../learning/learning-runtime-integration-v2.js";

function createModels() {
  return [
    {
      id:
        "trend-model",

      version:
        "3.0.0",

      family:
        "TREND",

      weight:
        0.5,

      prediction: {
        direction:
          "BUY",

        confidence:
          80,
      },
    },

    {
      id:
        "mean-model",

      version:
        "2.0.0",

      family:
        "MEAN_REVERSION",

      weight:
        0.5,

      prediction: {
        direction:
          "SELL",

        confidence:
          55,
      },
    },
  ];
}

function createLearningRecords() {
  const records = [];

  for (
    let index = 0;
    index < 30;
    index += 1
  ) {
    records.push({
      modelId:
        "trend-model",

      family:
        "TREND",

      regime:
        "TRENDING_BULL",

      prediction: {
        direction:
          index < 25
            ? "BUY"
            : "SELL",

        confidence:
          80,
      },

      actualReturn:
        1.5,

      timestamp:
        new Date(
          Date.parse(
            "2026-01-01T00:00:00.000Z",
          ) +
          index *
          86400000,
        ).toISOString(),
    });

    records.push({
      modelId:
        "mean-model",

      family:
        "MEAN_REVERSION",

      regime:
        "TRENDING_BULL",

      prediction: {
        direction:
          index < 10
            ? "BUY"
            : "SELL",

        confidence:
          65,
      },

      actualReturn:
        1.5,

      timestamp:
        new Date(
          Date.parse(
            "2026-01-01T00:00:00.000Z",
          ) +
          index *
          86400000,
        ).toISOString(),
    });
  }

  return records;
}

function createDriftRecords() {
  const records = [];

  for (
    const modelId
    of [
      "trend-model",
      "mean-model",
    ]
  ) {
    for (
      let index = 0;
      index < 80;
      index += 1
    ) {
      records.push({
        modelId,

        prediction: {
          direction:
            index % 5 === 0
              ? "SELL"
              : "BUY",

          confidence:
            70,
        },

        actualReturn:
          index % 5 === 0
            ? -1
            : 1,

        timestamp:
          new Date(
            Date.parse(
              "2025-01-01T00:00:00.000Z",
            ) +
            index *
            86400000,
          ).toISOString(),

        features: {
          rsi:
            50 +
            index % 3,

          volatility:
            2,
        },
      });
    }
  }

  return records;
}

function healthyInput() {
  const learningRecords =
    createLearningRecords();

  return {
    models:
      createModels(),

    learningRecords,

    outcomes:
      learningRecords,

    driftRecords:
      createDriftRecords(),

    regime:
      "TRENDING_BULL",

    marketContext: {
      returns: [
        0.5,
        0.8,
        1,
        0.6,
      ],

      trendScore:
        35,

      adx:
        30,

      movingAverageSlope:
        0.8,
    },

    learningConfig: {
      minimumSamples:
        10,
    },

    weightConfig: {
      minimumSamples:
        10,

      learningRate:
        0.3,
    },

    driftConfig: {
      baselineWindow:
        40,

      recentWindow:
        20,

      minimumSamples:
        40,
    },

    ensembleConfig: {
      minimumConfidence:
        20,

      minimumAgreement:
        20,
    },
  };
}

test(
  "Learning runtime integrates Phase3 learning engines",
  () => {
    const result =
      runLearningRuntimeIntegration(
        healthyInput(),
      );

    assert.equal(
      result.version,
      "learning-runtime-integration-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.models.length,
      2,
    );

    assert.equal(
      result.learning.ready,
      true,
    );

    assert.equal(
      result.weightUpdate.ready,
      true,
    );

    assert.equal(
      result.drift.modelCount,
      2,
    );

    assert.equal(
      result.ensemble.ready,
      true,
    );
  },
);

test(
  "Learning runtime increases strong model weight",
  () => {
    const result =
      runLearningRuntimeIntegration(
        healthyInput(),
      );

    const trend =
      result.models.find(
        (
          model,
        ) =>
          model.id ===
          "trend-model",
      );

    const mean =
      result.models.find(
        (
          model,
        ) =>
          model.id ===
          "mean-model",
      );

    assert.ok(
      trend.weight >
      mean.weight,
    );

    assert.ok(
      trend.historicalAccuracy >
      mean.historicalAccuracy,
    );
  },
);

test(
  "Learning runtime produces bullish ensemble",
  () => {
    const result =
      runLearningRuntimeIntegration(
        healthyInput(),
      );

    assert.equal(
      result.ensemble.direction,
      "BUY",
    );

    assert.ok(
      result.ensemble.confidence >
      0,
    );
  },
);

test(
  "Learning runtime handles no models",
  () => {
    const result =
      runLearningRuntimeIntegration({
        models:
          [],
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.reason,
      "NO_MODELS",
    );

    assert.equal(
      result.action,
      "HOLD",
    );
  },
);

test(
  "Learning runtime rejects invalid models",
  () => {
    assert.throws(
      () =>
        runLearningRuntimeIntegration({
          models:
            "invalid",
        }),

      /models must be an array/,
    );
  },
);

test(
  "Learning runtime integrates promotion evaluation",
  () => {
    const input =
      healthyInput();

    input.candidateModel = {
      id:
        "trend-model",

      version:
        "3.0.0",

      family:
        "TREND",
    };

    input.promotionMetrics = {
      accuracy:
        72,

      confidenceCalibrationError:
        8,

      profitFactor:
        1.6,

      maximumDrawdown:
        8,

      averageReturn:
        1.4,

      sampleCount:
        500,

      stabilityScore:
        75,

      monteCarloSuccessRate:
        70,
    };

    input.benchmarkMetrics = {
      accuracy:
        68,

      averageReturn:
        1.1,

      maximumDrawdown:
        10,
    };

    input.promotionConfig = {
      requireHumanApproval:
        false,

      minimumPromotionScore:
        75,
    };

    const result =
      runLearningRuntimeIntegration(
        input,
      );

    assert.ok(
      result.promotion,
    );

    assert.equal(
      result.promotion.candidate.id,
      "trend-model",
    );
  },
);

test(
  "Learning runtime class is deterministic for core results",
  () => {
    const engine =
      new LearningRuntimeIntegrationV2();

    const input =
      healthyInput();

    const first =
      engine.run(input);

    const second =
      engine.run(input);

    assert.deepEqual(
      first.models,
      second.models,
    );

    assert.deepEqual(
      first.ensemble,
      second.ensemble,
    );

    assert.deepEqual(
      first.summary,
      second.summary,
    );
  },
);