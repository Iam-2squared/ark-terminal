export const RUNTIME_HEALTH_MONITOR_V2_VERSION =
  "runtime-health-monitor-v2";

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
      "Runtime health monitor timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function normalizeInput(
  input = {},
) {
  return {
    timestamp:
      normalizeTimestamp(
        input.timestamp,
      ),

    runtimeStatus:
      normalizeText(
        input.runtimeStatus,
        "UNKNOWN",
      ).toUpperCase(),

    schedulerStatus:
      normalizeText(
        input.schedulerStatus,
        "UNKNOWN",
      ).toUpperCase(),

    auditValid:
      input.auditValid !==
      false,

    consecutiveFailures:
      Math.max(
        0,
        Math.floor(
          finiteOrNull(
            input.consecutiveFailures,
          ) ??
          0,
        ),
      ),

    failureRate:
      Math.max(
        0,
        finiteOrNull(
          input.failureRate,
        ) ??
        0,
      ),

    latencyMs:
      Math.max(
        0,
        finiteOrNull(
          input.latencyMs,
        ) ??
        0,
      ),

    queueDepth:
      Math.max(
        0,
        Math.floor(
          finiteOrNull(
            input.queueDepth,
          ) ??
          0,
        ),
      ),

    staleForMs:
      Math.max(
        0,
        finiteOrNull(
          input.staleForMs,
        ) ??
        0,
      ),

    memoryUsagePercent:
      Math.max(
        0,
        finiteOrNull(
          input.memoryUsagePercent,
        ) ??
        0,
      ),

    cpuUsagePercent:
      Math.max(
        0,
        finiteOrNull(
          input.cpuUsagePercent,
        ) ??
        0,
      ),

    learningHealth:
      normalizeText(
        input.learningHealth,
        "HEALTHY",
      ).toUpperCase(),

    promotionBlocked:
      input.promotionBlocked ===
      true,

    rollbackRequired:
      input.rollbackRequired ===
      true,
  };
}

function normalizePolicy(
  policy = {},
) {
  return {
    warningFailureRate:
      finiteOrNull(
        policy.warningFailureRate,
      ) ??
      10,

    criticalFailureRate:
      finiteOrNull(
        policy.criticalFailureRate,
      ) ??
      30,

    warningLatencyMs:
      finiteOrNull(
        policy.warningLatencyMs,
      ) ??
      5_000,

    criticalLatencyMs:
      finiteOrNull(
        policy.criticalLatencyMs,
      ) ??
      15_000,

    warningQueueDepth:
      finiteOrNull(
        policy.warningQueueDepth,
      ) ??
      50,

    criticalQueueDepth:
      finiteOrNull(
        policy.criticalQueueDepth,
      ) ??
      200,

    warningStaleForMs:
      finiteOrNull(
        policy.warningStaleForMs,
      ) ??
      300_000,

    criticalStaleForMs:
      finiteOrNull(
        policy.criticalStaleForMs,
      ) ??
      900_000,

    warningResourcePercent:
      finiteOrNull(
        policy.warningResourcePercent,
      ) ??
      80,

    criticalResourcePercent:
      finiteOrNull(
        policy.criticalResourcePercent,
      ) ??
      95,

    criticalConsecutiveFailures:
      Math.max(
        1,
        Math.floor(
          finiteOrNull(
            policy.criticalConsecutiveFailures,
          ) ??
          3,
        ),
      ),
  };
}

function issue({
  severity,
  code,
  message,
  metric = null,
  value = null,
  threshold = null,
}) {
  return {
    severity,
    code,
    message,
    metric,
    value,
    threshold,
  };
}

export function evaluateRuntimeHealth({
  input = {},
  policy = {},
} = {}) {
  const normalized =
    normalizeInput(
      input,
    );

  const thresholds =
    normalizePolicy(
      policy,
    );

  const issues = [];

  if (
    normalized.runtimeStatus ===
    "FAILED"
  ) {
    issues.push(
      issue({
        severity:
          "CRITICAL",

        code:
          "RUNTIME_FAILED",

        message:
          "Learning runtime reported failure.",
      }),
    );
  }

  if (
    normalized.schedulerStatus ===
    "FAILED"
  ) {
    issues.push(
      issue({
        severity:
          "CRITICAL",

        code:
          "SCHEDULER_FAILED",

        message:
          "Adaptive scheduler reported failure.",
      }),
    );
  }

  if (!normalized.auditValid) {
    issues.push(
      issue({
        severity:
          "CRITICAL",

        code:
          "AUDIT_INVALID",

        message:
          "Runtime audit trail is invalid.",
      }),
    );
  }

  if (
    normalized.rollbackRequired
  ) {
    issues.push(
      issue({
        severity:
          "CRITICAL",

        code:
          "ROLLBACK_REQUIRED",

        message:
          "Learning state requires rollback.",
      }),
    );
  }

  if (
    normalized.consecutiveFailures >=
    thresholds
      .criticalConsecutiveFailures
  ) {
    issues.push(
      issue({
        severity:
          "CRITICAL",

        code:
          "CONSECUTIVE_FAILURE_LIMIT",

        message:
          "Consecutive runtime failures reached the limit.",

        metric:
          "consecutiveFailures",

        value:
          normalized.consecutiveFailures,

        threshold:
          thresholds
            .criticalConsecutiveFailures,
      }),
    );
  }

  const checks = [
    {
      metric:
        "failureRate",

      value:
        normalized.failureRate,

      warning:
        thresholds
          .warningFailureRate,

      critical:
        thresholds
          .criticalFailureRate,

      code:
        "FAILURE_RATE",
    },

    {
      metric:
        "latencyMs",

      value:
        normalized.latencyMs,

      warning:
        thresholds
          .warningLatencyMs,

      critical:
        thresholds
          .criticalLatencyMs,

      code:
        "LATENCY",
    },

    {
      metric:
        "queueDepth",

      value:
        normalized.queueDepth,

      warning:
        thresholds
          .warningQueueDepth,

      critical:
        thresholds
          .criticalQueueDepth,

      code:
        "QUEUE_DEPTH",
    },

    {
      metric:
        "staleForMs",

      value:
        normalized.staleForMs,

      warning:
        thresholds
          .warningStaleForMs,

      critical:
        thresholds
          .criticalStaleForMs,

      code:
        "STALE_RUNTIME",
    },

    {
      metric:
        "memoryUsagePercent",

      value:
        normalized
          .memoryUsagePercent,

      warning:
        thresholds
          .warningResourcePercent,

      critical:
        thresholds
          .criticalResourcePercent,

      code:
        "MEMORY_USAGE",
    },

    {
      metric:
        "cpuUsagePercent",

      value:
        normalized
          .cpuUsagePercent,

      warning:
        thresholds
          .warningResourcePercent,

      critical:
        thresholds
          .criticalResourcePercent,

      code:
        "CPU_USAGE",
    },
  ];

  for (const check of checks) {
    if (
      check.value >=
      check.critical
    ) {
      issues.push(
        issue({
          severity:
            "CRITICAL",

          code:
            `${check.code}_CRITICAL`,

          message:
            `${check.metric} exceeded the critical threshold.`,

          metric:
            check.metric,

          value:
            check.value,

          threshold:
            check.critical,
        }),
      );
    }
    else if (
      check.value >=
      check.warning
    ) {
      issues.push(
        issue({
          severity:
            "WARNING",

          code:
            `${check.code}_WARNING`,

          message:
            `${check.metric} exceeded the warning threshold.`,

          metric:
            check.metric,

          value:
            check.value,

          threshold:
            check.warning,
        }),
      );
    }
  }

  if (
    [
      "CRITICAL",
      "DEGRADED",
      "WATCH",
    ].includes(
      normalized.learningHealth,
    )
  ) {
    issues.push(
      issue({
        severity:
          normalized.learningHealth ===
          "CRITICAL"
            ? "CRITICAL"
            : "WARNING",

        code:
          `LEARNING_HEALTH_${normalized.learningHealth}`,

        message:
          `Learning health is ${normalized.learningHealth}.`,
      }),
    );
  }

  if (
    normalized.promotionBlocked
  ) {
    issues.push(
      issue({
        severity:
          "WARNING",

        code:
          "PROMOTION_BLOCKED",

        message:
          "Candidate promotion is currently blocked.",
      }),
    );
  }

  const criticalCount =
    issues.filter(
      (
        item,
      ) =>
        item.severity ===
        "CRITICAL",
    ).length;

  const warningCount =
    issues.filter(
      (
        item,
      ) =>
        item.severity ===
        "WARNING",
    ).length;

  let status =
    "HEALTHY";

  if (criticalCount > 0) {
    status =
      "CRITICAL";
  }
  else if (warningCount > 0) {
    status =
      "WATCH";
  }

  const score =
    Math.max(
      0,
      Math.min(
        100,
        100 -
        criticalCount *
          30 -
        warningCount *
          8,
      ),
    );

  return {
    version:
      RUNTIME_HEALTH_MONITOR_V2_VERSION,

    status,

    healthy:
      status ===
      "HEALTHY",

    score,

    issues,

    summary: {
      criticalCount,

      warningCount,

      issueCount:
        issues.length,
    },

    input:
      normalized,

    policy:
      thresholds,

    recommendation:
      status ===
      "CRITICAL"
        ? "STOP_RUNTIME_AND_REVIEW"
        : status ===
          "WATCH"
          ? "CONTINUE_WITH_MONITORING"
          : "CONTINUE_NORMAL_OPERATION",
  };
}

export function assertRuntimeHealthy(
  result,
) {
  if (
    !result ||
    typeof result !==
      "object"
  ) {
    throw new TypeError(
      "Runtime health result is required.",
    );
  }

  if (
    result.status ===
    "CRITICAL"
  ) {
    const error =
      new Error(
        "Runtime health is critical.",
      );

    error.code =
      "RUNTIME_HEALTH_CRITICAL";

    error.issues =
      result.issues ??
      [];

    throw error;
  }

  return result;
}

export class RuntimeHealthMonitorV2 {
  constructor({
    policy = {},
  } = {}) {
    this.policy = {
      ...policy,
    };

    this.history = [];
  }

  evaluate(input = {}) {
    const result =
      evaluateRuntimeHealth({
        input,

        policy:
          this.policy,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
  }

  assert(input = {}) {
    return assertRuntimeHealthy(
      this.evaluate(
        input,
      ),
    );
  }

  getHistory() {
    return clone(
      this.history,
    );
  }

  latest() {
    return clone(
      this.history.at(-1) ??
      null,
    );
  }

  reset() {
    this.history = [];

    return [];
  }
}

export const runtimeHealthMonitorV2 =
  new RuntimeHealthMonitorV2();

export default evaluateRuntimeHealth;