import test from "node:test";
import assert from "node:assert/strict";

import {
  LearningOrchestratorV2,
  runLearningCycle,
} from "../learning/learning-orchestrator-v2.js";

const NOW =
  Date.parse(
    "2026-08-10T00:00:00.000Z",
  );

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
      "2026-08-01T00:00:00.000Z",

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
      "2026-08-06T00:00:00.000Z",

    realizedPrice:
      550,

    ...overrides,
  };
}

function cycleInput(
  overrides = {},
) {
  return {
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

    ...overrides,
  };
}

test(
  "Learning orchestrator completes full learning cycle",
  () => {
    const result =
      runLearningCycle(
        cycleInput(),
      );

    assert.equal(
      result.status,
      "COMPLETED",
    );

    assert.equal(
      result.applied,
      true,
    );

    assert.equal(
      result.state.revision,
      1,
    );

    assert.equal(
      result.feedback
        .records
        .length,
      1,
    );

    assert.equal(
      result.quality.passed,
      true,
    );
  },
);

test(
  "Learning orchestrator supports dry run",
  () => {
    const result =
      runLearningCycle(
        cycleInput({
          dryRun:
            true,
        }),
      );

    assert.equal(
      result.status,
      "DRY_RUN",
    );

    assert.equal(
      result.applied,
      false,
    );

    assert.equal(
      result.state.revision,
      0,
    );

    assert.equal(
      result.candidateState
        .revision,
      1,
    );
  },
);

test(
  "Learning orchestrator returns no data for incomplete horizon",
  () => {
    const result =
      runLearningCycle(
        cycleInput({
          predictions: [
            prediction({
              generatedAt:
                "2026-08-09T00:00:00.000Z",

              horizon:
                5,
            }),
          ],

          outcomes:
            [],
        }),
      );

    assert.equal(
      result.status,
      "NO_DATA",
    );

    assert.equal(
      result.applied,
      false,
    );

    assert.equal(
      result.code,
      "NO_LEARNING_RECORDS",
    );
  },
);

test(
  "Learning orchestrator blocks poor quality dataset",
  () => {
    const result =
      runLearningCycle(
        cycleInput({
          outcomes: [
            outcome({
              realizedReturn:
                500,

              realizedPrice:
                null,
            }),
          ],

          qualityConfig: {
            minimumSamples:
              1,

            maximumAbsoluteReturn:
              100,
          },
        }),
      );

    assert.equal(
      result.status,
      "BLOCKED",
    );

    assert.equal(
      result.applied,
      false,
    );

    assert.equal(
      result.code,
      "QUALITY_GATE_BLOCKED",
    );
  },
);

test(
  "Learning orchestrator keeps audit trail",
  () => {
    const result =
      runLearningCycle(
        cycleInput(),
      );

    assert.ok(
      result.auditTrail.length >=
      4,
    );

    assert.equal(
      result.auditTrail[0]
        .stage,
      "INITIALIZATION",
    );

    assert.equal(
      result.auditTrail[
        result.auditTrail.length -
        1
      ].stage,
      "COMMIT",
    );
  },
);

test(
  "Learning orchestrator class persists state",
  () => {
    const orchestrator =
      new LearningOrchestratorV2({
        config: {
          modelId:
            "ark-learning",

          modelVersion:
            "v2",

          qualityConfig: {
            minimumSamples:
              1,
          },
        },
      });

    const first =
      orchestrator.run({
        predictions: [
          prediction(),
        ],

        outcomes: [
          outcome(),
        ],

        now:
          NOW,
      });

    assert.equal(
      first.applied,
      true,
    );

    assert.equal(
      orchestrator
        .getState()
        .revision,
      1,
    );

    assert.equal(
      orchestrator
        .getHistory()
        .length,
      1,
    );
  },
);

test(
  "Learning orchestrator class prevents duplicate feedback",
  () => {
    const orchestrator =
      new LearningOrchestratorV2({
        config: {
          modelId:
            "ark-learning",

          qualityConfig: {
            minimumSamples:
              1,
          },
        },
      });

    const first =
      orchestrator.run({
        predictions: [
          prediction(),
        ],

        outcomes: [
          outcome(),
        ],

        now:
          NOW,
      });

    const second =
      orchestrator.run({
        predictions: [
          prediction(),
        ],

        outcomes: [
          outcome(),
        ],

        now:
          NOW + 1000,
      });

    assert.equal(
      first.applied,
      true,
    );

    assert.equal(
      second.applied,
      false,
    );

    assert.equal(
      second.status,
      "NO_DATA",
    );

    assert.equal(
      orchestrator
        .getState()
        .revision,
      1,
    );
  },
);

test(
  "Learning orchestrator class resets state",
  () => {
    const orchestrator =
      new LearningOrchestratorV2({
        config: {
          modelId:
            "ark-learning",

          qualityConfig: {
            minimumSamples:
              1,
          },
        },
      });

    orchestrator.run({
      predictions: [
        prediction(),
      ],

      outcomes: [
        outcome(),
      ],

      now:
        NOW,
    });

    const reset =
      orchestrator.reset();

    assert.equal(
      reset.revision,
      0,
    );

    assert.equal(
      orchestrator
        .getHistory()
        .length,
      0,
    );
  },
);

test(
  "Learning orchestrator validates inputs",
  () => {
    assert.throws(
      () =>
        runLearningCycle({
          predictions:
            "invalid",
        }),

      /predictions must be an array/,
    );

    assert.throws(
      () =>
        runLearningCycle({
          outcomes:
            "invalid",
        }),

      /outcomes must be an array/,
    );
  },
);