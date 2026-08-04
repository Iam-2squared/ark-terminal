import test from "node:test";
import assert from "node:assert/strict";

import {
  AILearningCoreV2,
  AI_LEARNING_CORE_V2_VERSION,
  buildLearningReport,
  calculateLearningMetrics,
  createInitialLearningState,
  createLearningPatch,
  evaluateLearningSafeguards,
  normalizeLearningRecord,
  normalizeLearningRecords,
  updateLearningState,
} from "../learning/ai-learning-core-v2.js";

function sampleRecords() {
  return [
    {
      id: "record-1",
      symbol: "285A",
      modelId: "ark-learning",
      modelVersion: "v1",
      regime: "TRENDING_BULL",
      horizon: 5,
      prediction: {
        direction: "BUY",
        confidence: 80,
        score: 82,
      },
      actualReturn: 2,
      timestamp:
        "2026-08-01T00:00:00.000Z",
    },
    {
      id: "record-2",
      symbol: "285A",
      modelId: "ark-learning",
      modelVersion: "v1",
      regime: "TRENDING_BULL",
      horizon: 5,
      prediction: {
        direction: "SELL",
        confidence: 70,
        score: 65,
      },
      actualReturn: 1,
      timestamp:
        "2026-08-02T00:00:00.000Z",
    },
  ];
}

test(
  "AI Learning Core exposes expected version",
  () => {
    assert.equal(
      AI_LEARNING_CORE_V2_VERSION,
      "ai-learning-core-v2",
    );
  },
);

test(
  "Learning record is normalized",
  () => {
    const record =
      normalizeLearningRecord(
        sampleRecords()[0],
        0,
      );

    assert.equal(
      record.symbol,
      "285A",
    );

    assert.equal(
      record.predictedDirectionLabel,
      "BUY",
    );

    assert.equal(
      record.correct,
      true,
    );

    assert.equal(
      record.actualReturn,
      2,
    );
  },
);

test(
  "Learning records are sorted by time",
  () => {
    const records =
      normalizeLearningRecords(
        sampleRecords().reverse(),
      );

    assert.equal(
      records[0].id,
      "record-1",
    );

    assert.equal(
      records[1].id,
      "record-2",
    );
  },
);

test(
  "Learning metrics calculate accuracy and returns",
  () => {
    const metrics =
      calculateLearningMetrics(
        sampleRecords(),
      );

    assert.equal(
      metrics.ready,
      true,
    );

    assert.equal(
      metrics.sampleCount,
      2,
    );

    assert.equal(
      metrics.winCount,
      1,
    );

    assert.equal(
      metrics.lossCount,
      1,
    );

    assert.equal(
      metrics.accuracy,
      50,
    );
  },
);

test(
  "Initial learning state is safe and empty",
  () => {
    const state =
      createInitialLearningState({
        modelId:
          "ark-learning",
      });

    assert.equal(
      state.modelId,
      "ark-learning",
    );

    assert.equal(
      state.revision,
      0,
    );

    assert.equal(
      state.metrics.ready,
      false,
    );

    assert.equal(
      state.safeguards
        .promotionAllowed,
      false,
    );
  },
);

test(
  "Learning update changes revision and metrics",
  () => {
    const state =
      updateLearningState({
        state:
          createInitialLearningState({
            modelId:
              "ark-learning",
          }),

        records:
          sampleRecords(),

        updatedAt:
          "2026-08-03T00:00:00.000Z",
      });

    assert.equal(
      state.revision,
      1,
    );

    assert.equal(
      state.metrics.sampleCount,
      2,
    );

    assert.equal(
      state.history.recordCount,
      2,
    );

    assert.equal(
      state.history.latestRecordId,
      "record-2",
    );
  },
);

test(
  "Learning update creates regime and horizon weights",
  () => {
    const state =
      updateLearningState({
        records:
          sampleRecords(),
      });

    assert.ok(
      Number.isFinite(
        state.weights
          .byRegime
          .TRENDING_BULL,
      ),
    );

    assert.ok(
      Number.isFinite(
        state.weights
          .byHorizon["5"],
      ),
    );
  },
);

test(
  "Safeguards freeze low accuracy model",
  () => {
    const safeguards =
      evaluateLearningSafeguards({
        metrics: {
          ready:
            true,

          sampleCount:
            50,

          accuracy:
            30,

          maximumDrawdown:
            10,

          calibrationError:
            10,

          streaks: {
            currentLossStreak:
              2,
          },
        },

        minimumAccuracy:
          45,
      });

    assert.equal(
      safeguards.frozen,
      true,
    );

    assert.ok(
      safeguards.blockers.includes(
        "LOW_ACCURACY",
      ),
    );
  },
);

test(
  "Learning patch exposes runtime weight",
  () => {
    const state =
      updateLearningState({
        records:
          sampleRecords(),
      });

    const patch =
      createLearningPatch(
        state,
      );

    assert.equal(
      patch.ready,
      true,
    );

    assert.equal(
      patch.revision,
      1,
    );

    assert.ok(
      Number.isFinite(
        patch.weight,
      ),
    );
  },
);

test(
  "Learning report groups records",
  () => {
    const records =
      sampleRecords();

    const state =
      updateLearningState({
        records,
      });

    const report =
      buildLearningReport({
        state,
        records,
      });

    assert.equal(
      report.ready,
      true,
    );

    assert.equal(
      report.diagnostics
        .recordCount,
      2,
    );

    assert.equal(
      report.diagnostics
        .regimeCount,
      1,
    );

    assert.equal(
      report.diagnostics
        .horizonCount,
      1,
    );
  },
);

test(
  "AI Learning Core class learns and resets",
  () => {
    const engine =
      new AILearningCoreV2({
        config: {
          modelId:
            "ark-learning",
        },
      });

    const learned =
      engine.learn(
        sampleRecords(),
        {
          updatedAt:
            "2026-08-03T00:00:00.000Z",
        },
      );

    assert.equal(
      learned.revision,
      1,
    );

    assert.equal(
      engine.getPatch()
        .ready,
      true,
    );

    const reset =
      engine.reset();

    assert.equal(
      reset.revision,
      0,
    );

    assert.equal(
      reset.metrics.ready,
      false,
    );
  },
);