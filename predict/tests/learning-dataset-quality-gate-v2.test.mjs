import test from "node:test";
import assert from "node:assert/strict";

import {
  LearningDatasetQualityGateV2,
  assertLearningDatasetQuality,
  evaluateLearningDatasetQuality,
} from "../learning/learning-dataset-quality-gate-v2.js";

import {
  buildLearningFeedback,
} from "../learning/learning-feedback-pipeline-v2.js";

import {
  updateLearningState,
} from "../learning/ai-learning-core-v2.js";

const NOW =
  Date.parse(
    "2026-08-10T00:00:00.000Z",
  );

function validRecord(
  overrides = {},
) {
  return {
    id:
      "feedback:prediction-1",

    symbol:
      "285A",

    modelId:
      "ark-learning",

    modelVersion:
      "v2",

    regime:
      "TRENDING_BULL",

    horizon:
      5,

    prediction: {
      direction:
        "BUY",

      confidence:
        80,

      score:
        82,
    },

    actualReturn:
      10,

    transactionCostPercent:
      0.2,

    timestamp:
      "2026-08-01T00:00:00.000Z",

    resolvedAt:
      "2026-08-06T00:00:00.000Z",

    features: {
      rsi:
        55,

      macd:
        1.2,
    },

    ...overrides,
  };
}

test(
  "Quality gate accepts valid dataset",
  () => {
    const result =
      evaluateLearningDatasetQuality({
        records: [
          validRecord(),
        ],

        now:
          NOW,

        minimumSamples:
          1,
      });

    assert.equal(
      result.passed,
      true,
    );

    assert.equal(
      result.summary
        .acceptedCount,
      1,
    );

    assert.equal(
      result.summary
        .rejectedCount,
      0,
    );
  },
);

test(
  "Quality gate rejects duplicate ids",
  () => {
    const result =
      evaluateLearningDatasetQuality({
        records: [
          validRecord(),
          validRecord(),
        ],

        now:
          NOW,

        minimumSamples:
          1,
      });

    assert.equal(
      result.passed,
      false,
    );

    assert.equal(
      result.summary
        .duplicateCount,
      1,
    );

    assert.ok(
      result.issues.some(
        (
          issue,
        ) =>
          issue.code ===
          "DUPLICATE_RECORD_ID",
      ),
    );
  },
);

test(
  "Quality gate rejects future outcome",
  () => {
    const result =
      evaluateLearningDatasetQuality({
        records: [
          validRecord({
            resolvedAt:
              "2026-08-20T00:00:00.000Z",
          }),
        ],

        now:
          NOW,

        minimumSamples:
          1,
      });

    assert.equal(
      result.passed,
      false,
    );

    assert.ok(
      result.issues.some(
        (
          issue,
        ) =>
          issue.code ===
          "FUTURE_OUTCOME_TIMESTAMP",
      ),
    );
  },
);

test(
  "Quality gate rejects outcome before prediction",
  () => {
    const result =
      evaluateLearningDatasetQuality({
        records: [
          validRecord({
            resolvedAt:
              "2026-07-31T00:00:00.000Z",
          }),
        ],

        now:
          NOW,

        minimumSamples:
          1,
      });

    assert.equal(
      result.passed,
      false,
    );

    assert.ok(
      result.issues.some(
        (
          issue,
        ) =>
          issue.code ===
          "OUTCOME_BEFORE_PREDICTION",
      ),
    );
  },
);

test(
  "Quality gate rejects extreme returns",
  () => {
    const result =
      evaluateLearningDatasetQuality({
        records: [
          validRecord({
            actualReturn:
              250,
          }),
        ],

        now:
          NOW,

        minimumSamples:
          1,

        maximumAbsoluteReturn:
          100,
      });

    assert.equal(
      result.passed,
      false,
    );

    assert.ok(
      result.issues.some(
        (
          issue,
        ) =>
          issue.code ===
          "EXTREME_RETURN",
      ),
    );
  },
);

test(
  "Quality gate warns on insufficient samples",
  () => {
    const result =
      evaluateLearningDatasetQuality({
        records: [
          validRecord(),
        ],

        now:
          NOW,

        minimumSamples:
          10,
      });

    assert.equal(
      result.passed,
      true,
    );

    assert.ok(
      result.issues.some(
        (
          issue,
        ) =>
          issue.code ===
          "INSUFFICIENT_SAMPLE_COUNT",
      ),
    );
  },
);

test(
  "Quality gate can reject warnings",
  () => {
    const result =
      evaluateLearningDatasetQuality({
        records: [
          validRecord(),
        ],

        now:
          NOW,

        minimumSamples:
          10,

        rejectWarnings:
          true,
      });

    assert.equal(
      result.passed,
      false,
    );
  },
);

test(
  "Quality gate detects symbol concentration",
  () => {
    const records =
      Array.from(
        {
          length:
            5,
        },
        (
          _,
          index,
        ) =>
          validRecord({
            id:
              `record-${index}`,

            timestamp:
              `2026-08-0${index + 1}T00:00:00.000Z`,

            resolvedAt:
              `2026-08-0${index + 2}T00:00:00.000Z`,
          }),
      );

    const result =
      evaluateLearningDatasetQuality({
        records,

        now:
          NOW,

        minimumSamples:
          1,

        maximumSingleSymbolSharePercent:
          60,
      });

    assert.ok(
      result.issues.some(
        (
          issue,
        ) =>
          issue.code ===
          "SYMBOL_CONCENTRATION",
      ),
    );
  },
);

test(
  "Quality gate assertion throws on failure",
  () => {
    const result =
      evaluateLearningDatasetQuality({
        records: [
          validRecord({
            actualReturn:
              null,
          }),
        ],

        now:
          NOW,

        minimumSamples:
          1,
      });

    assert.throws(
      () =>
        assertLearningDatasetQuality(
          result,
        ),

      (
        error,
      ) =>
        error.code ===
        "LEARNING_DATASET_QUALITY_FAILED",
    );
  },
);

test(
  "Quality gate output is compatible with learning core",
  () => {
    const feedback =
      buildLearningFeedback({
        predictions: [
          {
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
          },
        ],

        outcomes: [
          {
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
          },
        ],

        now:
          NOW,
      });

    const quality =
      evaluateLearningDatasetQuality({
        records:
          feedback.records,

        now:
          NOW,

        minimumSamples:
          1,
      });

    const state =
      updateLearningState({
        records:
          quality.acceptedRecords,

        updatedAt:
          "2026-08-10T00:00:00.000Z",
      });

    assert.equal(
      quality.passed,
      true,
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
  "Quality gate class evaluates and asserts",
  () => {
    const gate =
      new LearningDatasetQualityGateV2({
        now:
          NOW,

        minimumSamples:
          1,
      });

    const result =
      gate.evaluate({
        records: [
          validRecord(),
        ],
      });

    const accepted =
      gate.assert({
        records: [
          validRecord(),
        ],
      });

    assert.equal(
      result.passed,
      true,
    );

    assert.equal(
      accepted.length,
      1,
    );
  },
);