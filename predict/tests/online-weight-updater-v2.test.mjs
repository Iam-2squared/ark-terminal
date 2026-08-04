import test from "node:test";
import assert from "node:assert/strict";

import {
  OnlineWeightUpdaterV2,
  createWeightPatch,
  updateOnlineModelWeights,
} from "../learning/online-weight-updater-v2.js";

function createModels() {
  return [
    {
      id:
        "strong-model",

      family:
        "TREND",

      weight:
        0.5,

      minimumWeight:
        0.05,

      maximumWeight:
        0.8,
    },

    {
      id:
        "weak-model",

      family:
        "GENERAL",

      weight:
        0.5,

      minimumWeight:
        0.05,

      maximumWeight:
        0.8,
    },
  ];
}

function createOutcomes() {
  const outcomes = [];

  for (
    let index = 0;
    index < 20;
    index += 1
  ) {
    outcomes.push({
      modelId:
        "strong-model",

      regime:
        "TRENDING_BULL",

      prediction: {
        direction:
          index < 17
            ? "BUY"
            : "SELL",

        confidence:
          75,
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

    outcomes.push({
      modelId:
        "weak-model",

      regime:
        "TRENDING_BULL",

      prediction: {
        direction:
          index < 5
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
  }

  return outcomes;
}

test(
  "Online updater returns valid result",
  () => {
    const result =
      updateOnlineModelWeights({
        models:
          createModels(),

        outcomes:
          createOutcomes(),
      });

    assert.equal(
      result.version,
      "online-weight-updater-v2",
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
      result.outcomeCount,
      40,
    );
  },
);

test(
  "Strong model gains more weight than weak model",
  () => {
    const result =
      updateOnlineModelWeights({
        models:
          createModels(),

        outcomes:
          createOutcomes(),

        learningRate:
          0.4,
      });

    const strong =
      result.models.find(
        (
          model,
        ) =>
          model.id ===
          "strong-model",
      );

    const weak =
      result.models.find(
        (
          model,
        ) =>
          model.id ===
          "weak-model",
      );

    assert.ok(
      strong.weight >
      weak.weight,
    );

    assert.ok(
      strong.update.reward >
      weak.update.reward,
    );
  },
);

test(
  "Online updater normalizes weights",
  () => {
    const result =
      updateOnlineModelWeights({
        models:
          createModels(),

        outcomes:
          createOutcomes(),
      });

    assert.ok(
      Math.abs(
        result.diagnostics.totalWeight -
        1,
      ) <
      0.000001,
    );
  },
);

test(
  "Online updater respects weight bounds",
  () => {
    const models =
      createModels();

    models[0].maximumWeight =
      0.6;

    const outcomes =
      Array.from(
        {
          length:
            100,
        },
        (
          _,
          index,
        ) => ({
          modelId:
            "strong-model",

          regime:
            "TRENDING_BULL",

          prediction: {
            direction:
              "BUY",

            confidence:
              90,
          },

          actualReturn:
            4,

          timestamp:
            new Date(
              Date.parse(
                "2026-01-01T00:00:00.000Z",
              ) +
              index *
              86400000,
            ).toISOString(),
        }),
      );

    const result =
      updateOnlineModelWeights({
        models,

        outcomes,

        learningRate:
          1,

        maximumLearningRate:
          1,
      });

    const strong =
      result.models.find(
        (
          model,
        ) =>
          model.id ===
          "strong-model",
      );

    assert.ok(
      strong.weight <=
      0.600001,
    );
  },
);

test(
  "Online updater creates regime-specific weights",
  () => {
    const result =
      updateOnlineModelWeights({
        models:
          createModels(),

        outcomes:
          createOutcomes(),
      });

    const strong =
      result.models.find(
        (
          model,
        ) =>
          model.id ===
          "strong-model",
      );

    assert.ok(
      Number.isFinite(
        strong.regimeWeights
          .TRENDING_BULL,
      ),
    );
  },
);

test(
  "Online updater creates weight patch",
  () => {
    const result =
      updateOnlineModelWeights({
        models:
          createModels(),

        outcomes:
          createOutcomes(),
      });

    const patch =
      createWeightPatch(
        result,
      );

    assert.equal(
      patch.ready,
      true,
    );

    assert.equal(
      patch.models.length,
      2,
    );

    assert.ok(
      Number.isFinite(
        patch.models[0].weight,
      ),
    );
  },
);

test(
  "Online updater handles no outcomes",
  () => {
    const result =
      updateOnlineModelWeights({
        models:
          createModels(),

        outcomes:
          [],
      });

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.updated,
      false,
    );

    assert.equal(
      result.models[0]
        .update.reason,
      "NO_OUTCOMES",
    );
  },
);

test(
  "Online updater handles no models",
  () => {
    const result =
      updateOnlineModelWeights({
        models:
          [],

        outcomes:
          createOutcomes(),
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.reason,
      "NO_MODELS",
    );
  },
);

test(
  "Online updater rejects invalid input",
  () => {
    assert.throws(
      () =>
        updateOnlineModelWeights({
          models:
            "invalid",

          outcomes:
            [],
        }),

      /models must be an array/,
    );

    assert.throws(
      () =>
        updateOnlineModelWeights({
          models:
            [],

          outcomes:
            "invalid",
        }),

      /outcomes must be an array/,
    );
  },
);

test(
  "Online updater class is deterministic",
  () => {
    const engine =
      new OnlineWeightUpdaterV2({
        learningRate:
          0.25,

        minimumSamples:
          10,
      });

    const input = {
      models:
        createModels(),

      outcomes:
        createOutcomes(),
    };

    const first =
      engine.update(input);

    const second =
      engine.update(input);

    assert.deepEqual(
      first.models,
      second.models,
    );

    assert.deepEqual(
      first.diagnostics,
      second.diagnostics,
    );
  },
);