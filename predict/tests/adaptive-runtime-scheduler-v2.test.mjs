import test from "node:test";
import assert from "node:assert/strict";

import {
  AdaptiveRuntimeSchedulerV2,
  calculateAdaptiveRuntimeSchedule,
  runScheduledLearningRuntime,
} from "../learning/adaptive-runtime-scheduler-v2.js";

const NOW =
  "2026-08-04T00:00:00.000Z";

test(
  "Scheduler runs when due and data exists",
  () => {
    const result =
      calculateAdaptiveRuntimeSchedule({
        now:
          NOW,

        lastRunAt:
          "2026-08-03T22:00:00.000Z",

        pendingPredictionCount:
          1,

        availableOutcomeCount:
          1,

        policy: {
          defaultIntervalMs:
            3_600_000,
        },
      });

    assert.equal(
      result.shouldRun,
      true,
    );

    assert.equal(
      result.due,
      true,
    );

    assert.equal(
      result.blockedReasons.length,
      0,
    );
  },
);

test(
  "Scheduler skips without learning data",
  () => {
    const result =
      calculateAdaptiveRuntimeSchedule({
        now:
          NOW,

        lastRunAt:
          "2026-08-03T22:00:00.000Z",

        pendingPredictionCount:
          0,

        availableOutcomeCount:
          0,
      });

    assert.equal(
      result.shouldRun,
      false,
    );

    assert.ok(
      result.blockedReasons.includes(
        "NO_LEARNING_DATA",
      ),
    );
  },
);

test(
  "Scheduler skips when not due",
  () => {
    const result =
      calculateAdaptiveRuntimeSchedule({
        now:
          NOW,

        lastRunAt:
          "2026-08-03T23:45:00.000Z",

        pendingPredictionCount:
          1,

        availableOutcomeCount:
          1,

        policy: {
          defaultIntervalMs:
            3_600_000,
        },
      });

    assert.equal(
      result.shouldRun,
      false,
    );

    assert.ok(
      result.blockedReasons.includes(
        "NOT_DUE",
      ),
    );
  },
);

test(
  "Scheduler accelerates during high volatility",
  () => {
    const result =
      calculateAdaptiveRuntimeSchedule({
        now:
          NOW,

        lastRunAt:
          "2026-08-03T23:50:00.000Z",

        pendingPredictionCount:
          1,

        availableOutcomeCount:
          1,

        marketVolatility:
          5,

        policy: {
          highVolatilityIntervalMs:
            300_000,

          volatilityHighThreshold:
            3,
        },
      });

    assert.equal(
      result.reason,
      "HIGH_VOLATILITY",
    );

    assert.equal(
      result.intervalMs,
      300_000,
    );

    assert.equal(
      result.shouldRun,
      true,
    );
  },
);

test(
  "Scheduler slows during low volatility",
  () => {
    const result =
      calculateAdaptiveRuntimeSchedule({
        now:
          NOW,

        lastRunAt:
          "2026-08-03T23:00:00.000Z",

        pendingPredictionCount:
          1,

        availableOutcomeCount:
          1,

        marketVolatility:
          0.5,

        policy: {
          lowVolatilityIntervalMs:
            7_200_000,

          volatilityLowThreshold:
            1,
        },
      });

    assert.equal(
      result.reason,
      "LOW_VOLATILITY",
    );

    assert.equal(
      result.shouldRun,
      false,
    );
  },
);

test(
  "Scheduler uses failure cooldown",
  () => {
    const result =
      calculateAdaptiveRuntimeSchedule({
        now:
          NOW,

        lastRunAt:
          "2026-08-03T23:00:00.000Z",

        pendingPredictionCount:
          1,

        availableOutcomeCount:
          1,

        consecutiveFailures:
          3,

        policy: {
          maximumConsecutiveFailures:
            3,

          cooldownAfterFailureMs:
            7_200_000,
        },
      });

    assert.equal(
      result.reason,
      "FAILURE_COOLDOWN",
    );

    assert.equal(
      result.intervalMs,
      7_200_000,
    );
  },
);

test(
  "Scheduler supports forced run",
  () => {
    const result =
      calculateAdaptiveRuntimeSchedule({
        now:
          NOW,

        pendingPredictionCount:
          0,

        availableOutcomeCount:
          0,

        force:
          true,
      });

    assert.equal(
      result.shouldRun,
      true,
    );

    assert.equal(
      result.reason,
      "FORCED_RUN",
    );
  },
);

test(
  "Scheduled runtime skips safely",
  () => {
    const result =
      runScheduledLearningRuntime({
        scheduler: {
          now:
            NOW,

          pendingPredictionCount:
            0,

          availableOutcomeCount:
            0,
        },
      });

    assert.equal(
      result.status,
      "SKIPPED",
    );

    assert.equal(
      result.executed,
      false,
    );

    assert.equal(
      result.runtimeResult,
      null,
    );
  },
);

test(
  "Scheduled runtime executes learning runtime",
  () => {
    const result =
      runScheduledLearningRuntime({
        scheduler: {
          now:
            NOW,

          force:
            true,
        },

        runtime: {
          predictions:
            [],

          outcomes:
            [],

          modelId:
            "ark-learning",
        },
      });

    assert.equal(
      result.status,
      "EXECUTED",
    );

    assert.equal(
      result.executed,
      true,
    );

    assert.equal(
      result.runtimeResult
        .status,
      "NO_DATA",
    );
  },
);

test(
  "Scheduler class stores state and history",
  () => {
    const scheduler =
      new AdaptiveRuntimeSchedulerV2();

    scheduler.run({
      scheduler: {
        now:
          NOW,

        force:
          true,
      },

      runtime: {
        predictions:
          [],

        outcomes:
          [],

        modelId:
          "ark-learning",
      },
    });

    const state =
      scheduler.getState();

    assert.equal(
      state.runCount,
      1,
    );

    assert.equal(
      state.successCount,
      1,
    );

    assert.equal(
      scheduler
        .getHistory()
        .length,
      1,
    );

    scheduler.reset();

    assert.equal(
      scheduler
        .getHistory()
        .length,
      0,
    );
  },
);

test(
  "Scheduler validates timestamp",
  () => {
    assert.throws(
      () =>
        calculateAdaptiveRuntimeSchedule({
          now:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);