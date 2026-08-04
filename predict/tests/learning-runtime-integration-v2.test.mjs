import test from "node:test";
import assert from "node:assert/strict";

import {
  LearningRuntimeIntegrationV2,
  runLearningRuntime,
} from "../learning/learning-runtime-integration-v2.js";

const NOW =
  "2026-08-04T00:00:00.000Z";

function prediction(
  overrides = {},
) {
  return {
    id:
      "prediction-1",

    symbol:
      "285A",

    modelId:
      "ark-learning",

    modelVersion:
      "v2",

    direction:
      "BUY",

    confidence:
      80,

    score:
      82,

    referencePrice:
      500,

    generatedAt:
      "2026-07-25T00:00:00.000Z",

    horizon:
      5,

    regime:
      "TRENDING_BULL",

    ...overrides,
  };
}

function outcome(
  overrides = {},
) {
  return {
    id:
      "outcome-1",

    predictionId:
      "prediction-1",

    symbol:
      "285A",

    observedAt:
      "2026-07-30T00:00:00.000Z",

    realizedPrice:
      550,

    ...overrides,
  };
}

test(
  "Learning runtime completes integrated cycle",
  () => {
    const result =
      runLearningRuntime({
        predictions: [
          prediction(),
        ],

        outcomes: [
          outcome(),
        ],

        modelId:
          "ark-learning",

        modelVersion:
          "v2",

        now:
          NOW,

        qualityConfig: {
          minimumSamples:
            1,
        },

        evaluationConfig: {
          minimumCandidateSamples:
            1,

          minimumEvaluationScore:
            0,

          minimumAverageReturn:
            -100,

          minimumProfitFactor:
            0,

          requireCandidateRevisionIncrease:
            true,
        },
      });

    assert.equal(
      result.version,
      "learning-runtime-integration-v2",
    );

    assert.equal(
      result.cycle.status,
      "COMPLETED",
    );

    assert.equal(
      result.applied,
      true,
    );

    assert.equal(
      result.report.generatedBy,
      "learning-runtime-v2",
    );

    assert.equal(
      result.audit.summary.valid,
      true,
    );

    assert.ok(
      result.audit.entries.length >=
      3,
    );
  },
);

test(
  "Learning runtime reports no data safely",
  () => {
    const result =
      runLearningRuntime({
        predictions:
          [],

        outcomes:
          [],

        modelId:
          "ark-learning",

        now:
          NOW,
      });

    assert.equal(
      result.status,
      "NO_DATA",
    );

    assert.equal(
      result.applied,
      false,
    );

    assert.equal(
      result.summary
        .candidateEvaluated,
      false,
    );

    assert.equal(
      result.audit.summary.valid,
      true,
    );
  },
);

test(
  "Learning runtime supports dry run",
  () => {
    const result =
      runLearningRuntime({
        predictions: [
          prediction(),
        ],

        outcomes: [
          outcome(),
        ],

        modelId:
          "ark-learning",

        now:
          NOW,

        dryRun:
          true,

        qualityConfig: {
          minimumSamples:
            1,
        },

        evaluationConfig: {
          minimumCandidateSamples:
            1,

          minimumEvaluationScore:
            0,

          minimumAverageReturn:
            -100,

          minimumProfitFactor:
            0,
        },
      });

    assert.equal(
      result.cycle.status,
      "DRY_RUN",
    );

    assert.equal(
      result.applied,
      false,
    );

    assert.equal(
      result.summary
        .candidateEvaluated,
      true,
    );
  },
);

test(
  "Learning runtime class stores history",
  () => {
    const runtime =
      new LearningRuntimeIntegrationV2({
        modelId:
          "ark-learning",

        now:
          NOW,
      });

    runtime.run({
      predictions:
        [],

      outcomes:
        [],
    });

    assert.equal(
      runtime
        .getHistory()
        .length,
      1,
    );

    runtime.resetHistory();

    assert.equal(
      runtime
        .getHistory()
        .length,
      0,
    );
  },
);

test(
  "Learning runtime validates timestamp",
  () => {
    assert.throws(
      () =>
        runLearningRuntime({
          now:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);