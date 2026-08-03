import test from "node:test";
import assert from "node:assert/strict";

import {
  RegimePerformanceLearningV2,
  createEnsembleLearningPatch,
  learnRegimePerformance,
  normalizeRegime,
} from "../learning/regime-performance-learning-v2.js";

function createRecords() {
  const records = [];

  for (
    let index = 0;
    index < 20;
    index += 1
  ) {
    records.push({
      id:
        `trend-${index}`,

      modelId:
        "trend-model",

      family:
        "TREND",

      regime:
        "TRENDING_BULL",

      prediction: {
        direction:
          index < 16
            ? "BUY"
            : "SELL",

        confidence:
          75,
      },

      actualReturn:
        1,

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

  for (
    let index = 0;
    index < 20;
    index += 1
  ) {
    records.push({
      id:
        `weak-${index}`,

      modelId:
        "weak-model",

      family:
        "GENERAL",

      regime:
        "TRENDING_BULL",

      prediction: {
        direction:
          index < 5
            ? "BUY"
            : "SELL",

        confidence:
          70,
      },

      actualReturn:
        1,

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

test(
  "Regime aliases are normalized",
  () => {
    assert.equal(
      normalizeRegime(
        "bullish",
      ),
      "TRENDING_BULL",
    );

    assert.equal(
      normalizeRegime(
        "sideways",
      ),
      "RANGE",
    );

    assert.equal(
      normalizeRegime(
        "high-vol",
      ),
      "HIGH_VOLATILITY",
    );
  },
);

test(
  "Regime performance learning summarizes models",
  () => {
    const result =
      learnRegimePerformance({
        records:
          createRecords(),

        minimumSamples:
          10,
      });

    assert.equal(
      result.version,
      "regime-performance-learning-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.modelCount,
      2,
    );

    assert.equal(
      result.recordCount,
      40,
    );
  },
);

test(
  "Strong model receives higher performance score",
  () => {
    const result =
      learnRegimePerformance({
        records:
          createRecords(),

        minimumSamples:
          10,
      });

    const strong =
      result.models.find(
        (
          model,
        ) =>
          model.modelId ===
          "trend-model",
      );

    const weak =
      result.models.find(
        (
          model,
        ) =>
          model.modelId ===
          "weak-model",
      );

    assert.ok(
      strong.overall
        .performanceScore >
      weak.overall
        .performanceScore,
    );

    assert.ok(
      strong.regimeMultipliers
        .TRENDING_BULL >
      weak.regimeMultipliers
        .TRENDING_BULL,
    );
  },
);

test(
  "Learning result produces ensemble patch",
  () => {
    const learning =
      learnRegimePerformance({
        records:
          createRecords(),

        minimumSamples:
          10,
      });

    const patch =
      createEnsembleLearningPatch(
        learning,
      );

    assert.equal(
      patch.ready,
      true,
    );

    assert.equal(
      patch.models.length,
      2,
    );

    const trend =
      patch.models.find(
        (
          model,
        ) =>
          model.id ===
          "trend-model",
      );

    assert.ok(
      Number.isFinite(
        trend.historicalAccuracy,
      ),
    );

    assert.ok(
      Number.isFinite(
        trend.regimePerformance
          .TRENDING_BULL,
      ),
    );
  },
);

test(
  "Insufficient samples result in hold recommendation",
  () => {
    const result =
      learnRegimePerformance({
        records: [
          {
            modelId:
              "small-model",

            regime:
              "RANGE",

            prediction: {
              direction:
                "BUY",

              confidence:
                90,
            },

            actualReturn:
              2,
          },
        ],

        minimumSamples:
          10,
      });

    assert.equal(
      result.models[0]
        .recommendation
        .action,
      "HOLD",
    );

    assert.equal(
      result.models[0]
        .recommendation
        .reason,
      "INSUFFICIENT_SAMPLES",
    );
  },
);

test(
  "Empty records return not ready",
  () => {
    const result =
      learnRegimePerformance({
        records:
          [],
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.modelCount,
      0,
    );

    assert.deepEqual(
      result.models,
      [],
    );
  },
);

test(
  "Invalid records input is rejected",
  () => {
    assert.throws(
      () =>
        learnRegimePerformance({
          records:
            "invalid",
        }),

      /records must be an array/,
    );
  },
);

test(
  "Learning engine is deterministic",
  () => {
    const engine =
      new RegimePerformanceLearningV2({
        minimumSamples:
          10,

        priorStrength:
          8,
      });

    const records =
      createRecords();

    assert.deepEqual(
      engine.learn(
        records,
      ),

      engine.learn(
        records,
      ),
    );
  },
);

test(
  "Recent outcomes receive more influence",
  () => {
    const records = [
      {
        modelId:
          "recency-model",

        regime:
          "TRENDING_BULL",

        prediction: {
          direction:
            "SELL",

          confidence:
            80,
        },

        actualReturn:
          1,

        timestamp:
          "2025-01-01T00:00:00.000Z",
      },

      {
        modelId:
          "recency-model",

        regime:
          "TRENDING_BULL",

        prediction: {
          direction:
            "BUY",

          confidence:
            80,
        },

        actualReturn:
          1,

        timestamp:
          "2026-01-01T00:00:00.000Z",
      },
    ];

    const result =
      learnRegimePerformance({
        records,

        minimumSamples:
          1,

        recencyHalfLifeDays:
          30,

        priorStrength:
          0,
      });

    assert.ok(
      result.models[0]
        .overall
        .weightedAccuracy >
      result.models[0]
        .overall
        .rawAccuracy,
    );
  },
);