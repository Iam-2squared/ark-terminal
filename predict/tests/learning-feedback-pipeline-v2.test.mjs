import test from "node:test";
import assert from "node:assert/strict";

import {
  LearningFeedbackPipelineV2,
  buildLearningFeedback,
  mergeLearningFeedback,
} from "../learning/learning-feedback-pipeline-v2.js";

import {
  calculateLearningMetrics,
  updateLearningState,
} from "../learning/ai-learning-core-v2.js";

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

    family:
      "GENERAL",

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

    features: {
      rsi:
        55,

      macd:
        1.2,
    },

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

    transactionCostPercent:
      0.2,

    ...overrides,
  };
}

test(
  "Feedback pipeline creates learning record",
  () => {
    const result =
      buildLearningFeedback({
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
      result.ready,
      true,
    );

    assert.equal(
      result.records.length,
      1,
    );

    assert.equal(
      result.records[0].id,
      "feedback:prediction-1",
    );

    assert.equal(
      result.records[0].actualReturn,
      10,
    );

    assert.equal(
      result.records[0]
        .prediction
        .direction,
      "BUY",
    );
  },
);

test(
  "Feedback pipeline accepts explicit realized return",
  () => {
    const result =
      buildLearningFeedback({
        predictions: [
          prediction(),
        ],

        outcomes: [
          outcome({
            realizedReturn:
              4.5,

            realizedPrice:
              null,
          }),
        ],

        now:
          NOW,
      });

    assert.equal(
      result.records[0]
        .actualReturn,
      4.5,
    );
  },
);

test(
  "Feedback pipeline rejects duplicate records",
  () => {
    const result =
      buildLearningFeedback({
        predictions: [
          prediction(),
        ],

        outcomes: [
          outcome(),
        ],

        existingRecordIds: [
          "feedback:prediction-1",
        ],

        now:
          NOW,
      });

    assert.equal(
      result.records.length,
      0,
    );

    assert.equal(
      result.summary
        .duplicateCount,
      1,
    );
  },
);

test(
  "Feedback pipeline keeps incomplete horizon pending",
  () => {
    const result =
      buildLearningFeedback({
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

        now:
          NOW,
      });

    assert.equal(
      result.records.length,
      0,
    );

    assert.equal(
      result.pending[0].code,
      "HORIZON_NOT_COMPLETE",
    );
  },
);

test(
  "Feedback pipeline rejects future outcomes",
  () => {
    const result =
      buildLearningFeedback({
        predictions: [
          prediction(),
        ],

        outcomes: [
          outcome({
            observedAt:
              "2026-08-20T00:00:00.000Z",
          }),
        ],

        now:
          NOW,
      });

    assert.equal(
      result.records.length,
      0,
    );

    assert.ok(
      result.rejected.some(
        (
          item,
        ) =>
          item.code ===
          "FUTURE_OUTCOME",
      ),
    );
  },
);

test(
  "Feedback pipeline rejects neutral prediction",
  () => {
    const result =
      buildLearningFeedback({
        predictions: [
          prediction({
            direction:
              "NEUTRAL",
          }),
        ],

        outcomes: [
          outcome(),
        ],

        now:
          NOW,
      });

    assert.equal(
      result.records.length,
      0,
    );

    assert.equal(
      result.rejected[0].code,
      "NEUTRAL_PREDICTION",
    );
  },
);

test(
  "Feedback records are compatible with learning core",
  () => {
    const feedback =
      buildLearningFeedback({
        predictions: [
          prediction(),
        ],

        outcomes: [
          outcome(),
        ],

        now:
          NOW,
      });

    const metrics =
      calculateLearningMetrics(
        feedback.records,
      );

    const state =
      updateLearningState({
        records:
          feedback.records,

        updatedAt:
          "2026-08-10T00:00:00.000Z",
      });

    assert.equal(
      metrics.sampleCount,
      1,
    );

    assert.equal(
      metrics.accuracy,
      100,
    );

    assert.equal(
      state.revision,
      1,
    );

    assert.equal(
      state.history
        .recordCount,
      1,
    );
  },
);

test(
  "Feedback merge preserves unique records",
  () => {
    const first = {
      id:
        "feedback:one",
    };

    const second = {
      id:
        "feedback:two",
    };

    const result =
      mergeLearningFeedback({
        existingRecords: [
          first,
        ],

        feedback: {
          records: [
            first,
            second,
          ],
        },
      });

    assert.equal(
      result.totalCount,
      2,
    );

    assert.equal(
      result.addedCount,
      1,
    );
  },
);

test(
  "Feedback pipeline class prevents repeated ingestion",
  () => {
    const pipeline =
      new LearningFeedbackPipelineV2({
        now:
          NOW,
      });

    const first =
      pipeline.process({
        predictions: [
          prediction(),
        ],

        outcomes: [
          outcome(),
        ],
      });

    const second =
      pipeline.process({
        predictions: [
          prediction(),
        ],

        outcomes: [
          outcome(),
        ],
      });

    assert.equal(
      first.records.length,
      1,
    );

    assert.equal(
      second.records.length,
      0,
    );

    assert.equal(
      pipeline
        .getRecords()
        .length,
      1,
    );
  },
);

test(
  "Feedback pipeline validates arrays",
  () => {
    assert.throws(
      () =>
        buildLearningFeedback({
          predictions:
            "invalid",
        }),

      /predictions must be an array/,
    );

    assert.throws(
      () =>
        buildLearningFeedback({
          outcomes:
            "invalid",
        }),

      /outcomes must be an array/,
    );
  },
);