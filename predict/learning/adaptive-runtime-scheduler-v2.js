import {
  runLearningRuntime,
} from "./learning-runtime-integration-v2.js";

export const ADAPTIVE_RUNTIME_SCHEDULER_V2_VERSION =
  "adaptive-runtime-scheduler-v2";

function finiteOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function normalizeTimestamp(value) {
  const milliseconds =
    typeof value === "number"
      ? value
      : Date.parse(
          value ??
          new Date().toISOString(),
        );

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(
      "Adaptive runtime scheduler timestamp is invalid.",
    );
  }

  return milliseconds;
}

function normalizeText(
  value,
  fallback = "",
) {
  const text =
    String(
      value ??
      fallback,
    ).trim();

  return text || fallback;
}

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function clamp(
  value,
  minimum,
  maximum,
) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      value,
    ),
  );
}

function normalizePolicy(
  policy = {},
) {
  const minimumIntervalMs =
    Math.max(
      1_000,
      Math.floor(
        finiteOrNull(
          policy.minimumIntervalMs,
        ) ??
        60_000,
      ),
    );

  const maximumIntervalMs =
    Math.max(
      minimumIntervalMs,
      Math.floor(
        finiteOrNull(
          policy.maximumIntervalMs,
        ) ??
        86_400_000,
      ),
    );

  return {
    minimumIntervalMs,

    maximumIntervalMs,

    defaultIntervalMs:
      clamp(
        Math.floor(
          finiteOrNull(
            policy.defaultIntervalMs,
          ) ??
          3_600_000,
        ),
        minimumIntervalMs,
        maximumIntervalMs,
      ),

    highVolatilityIntervalMs:
      clamp(
        Math.floor(
          finiteOrNull(
            policy.highVolatilityIntervalMs,
          ) ??
          300_000,
        ),
        minimumIntervalMs,
        maximumIntervalMs,
      ),

    lowVolatilityIntervalMs:
      clamp(
        Math.floor(
          finiteOrNull(
            policy.lowVolatilityIntervalMs,
          ) ??
          7_200_000,
        ),
        minimumIntervalMs,
        maximumIntervalMs,
      ),

    degradedHealthIntervalMs:
      clamp(
        Math.floor(
          finiteOrNull(
            policy.degradedHealthIntervalMs,
          ) ??
          600_000,
        ),
        minimumIntervalMs,
        maximumIntervalMs,
      ),

    criticalHealthIntervalMs:
      clamp(
        Math.floor(
          finiteOrNull(
            policy.criticalHealthIntervalMs,
          ) ??
          120_000,
        ),
        minimumIntervalMs,
        maximumIntervalMs,
      ),

    minimumPendingPredictions:
      Math.max(
        0,
        Math.floor(
          finiteOrNull(
            policy.minimumPendingPredictions,
          ) ??
          1,
        ),
      ),

    volatilityHighThreshold:
      Math.max(
        0,
        finiteOrNull(
          policy.volatilityHighThreshold,
        ) ??
        3,
      ),

    volatilityLowThreshold:
      Math.max(
        0,
        finiteOrNull(
          policy.volatilityLowThreshold,
        ) ??
        1,
      ),

    maximumConsecutiveFailures:
      Math.max(
        1,
        Math.floor(
          finiteOrNull(
            policy.maximumConsecutiveFailures,
          ) ??
          3,
        ),
      ),

    cooldownAfterFailureMs:
      Math.max(
        0,
        Math.floor(
          finiteOrNull(
            policy.cooldownAfterFailureMs,
          ) ??
          300_000,
        ),
      ),

    enabled:
      policy.enabled !== false,
  };
}

export function calculateAdaptiveRuntimeSchedule({
  now = Date.now(),
  lastRunAt = null,
  nextRunAt = null,
  pendingPredictionCount = 0,
  availableOutcomeCount = 0,
  marketVolatility = null,
  health = "HEALTHY",
  consecutiveFailures = 0,
  force = false,
  policy = {},
} = {}) {
  const nowMs =
    normalizeTimestamp(
      now,
    );

  const normalizedPolicy =
    normalizePolicy(
      policy,
    );

  const normalizedHealth =
    normalizeText(
      health,
      "HEALTHY",
    ).toUpperCase();

  const normalizedFailures =
    Math.max(
      0,
      Math.floor(
        finiteOrNull(
          consecutiveFailures,
        ) ??
        0,
      ),
    );

  const normalizedPending =
    Math.max(
      0,
      Math.floor(
        finiteOrNull(
          pendingPredictionCount,
        ) ??
        0,
      ),
    );

  const normalizedOutcomes =
    Math.max(
      0,
      Math.floor(
        finiteOrNull(
          availableOutcomeCount,
        ) ??
        0,
      ),
    );

  const volatility =
    finiteOrNull(
      marketVolatility,
    );

  const lastRunMs =
    lastRunAt === null
      ? null
      : normalizeTimestamp(
          lastRunAt,
        );

  const explicitNextRunMs =
    nextRunAt === null
      ? null
      : normalizeTimestamp(
          nextRunAt,
        );

  let intervalMs =
    normalizedPolicy
      .defaultIntervalMs;

  let reason =
    "DEFAULT_INTERVAL";

  if (
    normalizedHealth ===
    "CRITICAL"
  ) {
    intervalMs =
      normalizedPolicy
        .criticalHealthIntervalMs;

    reason =
      "CRITICAL_HEALTH";
  }
  else if (
    [
      "WATCH",
      "DEGRADED",
    ].includes(
      normalizedHealth,
    )
  ) {
    intervalMs =
      normalizedPolicy
        .degradedHealthIntervalMs;

    reason =
      "DEGRADED_HEALTH";
  }
  else if (
    volatility !== null &&
    volatility >=
      normalizedPolicy
        .volatilityHighThreshold
  ) {
    intervalMs =
      normalizedPolicy
        .highVolatilityIntervalMs;

    reason =
      "HIGH_VOLATILITY";
  }
  else if (
    volatility !== null &&
    volatility <=
      normalizedPolicy
        .volatilityLowThreshold
  ) {
    intervalMs =
      normalizedPolicy
        .lowVolatilityIntervalMs;

    reason =
      "LOW_VOLATILITY";
  }

  if (
    normalizedFailures >=
    normalizedPolicy
      .maximumConsecutiveFailures
  ) {
    intervalMs =
      Math.max(
        intervalMs,
        normalizedPolicy
          .cooldownAfterFailureMs,
      );

    reason =
      "FAILURE_COOLDOWN";
  }

  intervalMs =
    clamp(
      intervalMs,
      normalizedPolicy
        .minimumIntervalMs,
      normalizedPolicy
        .maximumIntervalMs,
    );

  const calculatedNextRunMs =
    lastRunMs === null
      ? nowMs
      : lastRunMs +
        intervalMs;

  const effectiveNextRunMs =
    explicitNextRunMs ??
    calculatedNextRunMs;

  const hasLearningData =
    normalizedPending >=
      normalizedPolicy
        .minimumPendingPredictions &&
    normalizedOutcomes >
      0;

  const due =
    force === true ||
    nowMs >=
      effectiveNextRunMs;

  const blockedReasons = [];

  if (
    normalizedPolicy.enabled !==
    true
  ) {
    blockedReasons.push(
      "SCHEDULER_DISABLED",
    );
  }

  if (
    !hasLearningData &&
    force !== true
  ) {
    blockedReasons.push(
      "NO_LEARNING_DATA",
    );
  }

  if (
    !due &&
    force !== true
  ) {
    blockedReasons.push(
      "NOT_DUE",
    );
  }

  const shouldRun =
    force === true ||
    (
      normalizedPolicy.enabled ===
        true &&
      hasLearningData &&
      due
    );

  return {
    version:
      ADAPTIVE_RUNTIME_SCHEDULER_V2_VERSION,

    shouldRun,

    due,

    forced:
      force === true,

    reason:
      force === true
        ? "FORCED_RUN"
        : reason,

    blockedReasons,

    intervalMs,

    now:
      new Date(
        nowMs,
      ).toISOString(),

    lastRunAt:
      lastRunMs === null
        ? null
        : new Date(
            lastRunMs,
          ).toISOString(),

    nextRunAt:
      new Date(
        effectiveNextRunMs,
      ).toISOString(),

    data: {
      pendingPredictionCount:
        normalizedPending,

      availableOutcomeCount:
        normalizedOutcomes,

      hasLearningData,
    },

    health:
      normalizedHealth,

    marketVolatility:
      volatility,

    consecutiveFailures:
      normalizedFailures,

    policy:
      normalizedPolicy,
  };
}

export function runScheduledLearningRuntime({
  scheduler = {},
  runtime = {},
} = {}) {
  const schedule =
    calculateAdaptiveRuntimeSchedule(
      scheduler,
    );

  if (!schedule.shouldRun) {
    return {
      version:
        ADAPTIVE_RUNTIME_SCHEDULER_V2_VERSION,

      status:
        "SKIPPED",

      executed:
        false,

      schedule,

      runtimeResult:
        null,

      nextRunAt:
        schedule.nextRunAt,
    };
  }

  try {
    const runtimeResult =
      runLearningRuntime({
        ...runtime,

        now:
          scheduler.now ??
          runtime.now ??
          new Date().toISOString(),
      });

    const nextSchedule =
      calculateAdaptiveRuntimeSchedule({
        ...scheduler,

        force:
          false,

        lastRunAt:
          scheduler.now ??
          runtime.now ??
          new Date().toISOString(),

        nextRunAt:
          null,

        consecutiveFailures:
          0,

        health:
          runtimeResult.summary
            ?.health ??
          scheduler.health,
      });

    return {
      version:
        ADAPTIVE_RUNTIME_SCHEDULER_V2_VERSION,

      status:
        "EXECUTED",

      executed:
        true,

      schedule,

      runtimeResult,

      nextRunAt:
        nextSchedule.nextRunAt,

      nextSchedule,
    };
  }
  catch (error) {
    const failedSchedule =
      calculateAdaptiveRuntimeSchedule({
        ...scheduler,

        force:
          false,

        lastRunAt:
          scheduler.now ??
          new Date().toISOString(),

        nextRunAt:
          null,

        consecutiveFailures:
          (
            finiteOrNull(
              scheduler
                .consecutiveFailures,
            ) ??
            0
          ) +
          1,
      });

    return {
      version:
        ADAPTIVE_RUNTIME_SCHEDULER_V2_VERSION,

      status:
        "FAILED",

      executed:
        true,

      schedule,

      runtimeResult:
        null,

      error: {
        name:
          error.name,

        message:
          error.message,
      },

      nextRunAt:
        failedSchedule.nextRunAt,

      nextSchedule:
        failedSchedule,
    };
  }
}

export class AdaptiveRuntimeSchedulerV2 {
  constructor({
    policy = {},
    runtimeConfig = {},
  } = {}) {
    this.policy =
      normalizePolicy(
        policy,
      );

    this.runtimeConfig = {
      ...runtimeConfig,
    };

    this.state = {
      lastRunAt:
        null,

      nextRunAt:
        null,

      consecutiveFailures:
        0,

      runCount:
        0,

      successCount:
        0,

      failureCount:
        0,

      skipCount:
        0,
    };

    this.history = [];
  }

  plan(input = {}) {
    return calculateAdaptiveRuntimeSchedule({
      ...input,

      policy: {
        ...this.policy,
        ...(
          input.policy ??
          {}
        ),
      },

      lastRunAt:
        input.lastRunAt ??
        this.state.lastRunAt,

      nextRunAt:
        input.nextRunAt ??
        this.state.nextRunAt,

      consecutiveFailures:
        input.consecutiveFailures ??
        this.state
          .consecutiveFailures,
    });
  }

  run({
    scheduler = {},
    runtime = {},
  } = {}) {
    const result =
      runScheduledLearningRuntime({
        scheduler: {
          ...scheduler,

          policy: {
            ...this.policy,
            ...(
              scheduler.policy ??
              {}
            ),
          },

          lastRunAt:
            scheduler.lastRunAt ??
            this.state.lastRunAt,

          nextRunAt:
            scheduler.nextRunAt ??
            this.state.nextRunAt,

          consecutiveFailures:
            scheduler
              .consecutiveFailures ??
            this.state
              .consecutiveFailures,
        },

        runtime: {
          ...this.runtimeConfig,
          ...runtime,
        },
      });

    if (
      result.status ===
      "SKIPPED"
    ) {
      this.state.skipCount +=
        1;
    }
    else {
      this.state.runCount +=
        1;

      this.state.lastRunAt =
        result.schedule.now;

      this.state.nextRunAt =
        result.nextRunAt;

      if (
        result.status ===
        "EXECUTED"
      ) {
        this.state.successCount +=
          1;

        this.state
          .consecutiveFailures =
          0;
      }
      else {
        this.state.failureCount +=
          1;

        this.state
          .consecutiveFailures +=
          1;
      }
    }

    this.history.push({
      timestamp:
        result.schedule.now,

      status:
        result.status,

      executed:
        result.executed,

      reason:
        result.schedule.reason,

      nextRunAt:
        result.nextRunAt,
    });

    return clone(
      result,
    );
  }

  getState() {
    return clone(
      this.state,
    );
  }

  getHistory() {
    return clone(
      this.history,
    );
  }

  reset() {
    this.state = {
      lastRunAt:
        null,

      nextRunAt:
        null,

      consecutiveFailures:
        0,

      runCount:
        0,

      successCount:
        0,

      failureCount:
        0,

      skipCount:
        0,
    };

    this.history = [];

    return this.getState();
  }
}

export const adaptiveRuntimeSchedulerV2 =
  new AdaptiveRuntimeSchedulerV2();

export default calculateAdaptiveRuntimeSchedule;