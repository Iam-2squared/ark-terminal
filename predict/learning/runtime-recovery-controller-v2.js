export const RUNTIME_RECOVERY_CONTROLLER_V2_VERSION =
  "runtime-recovery-controller-v2";

const RECOVERY_ACTIONS =
  new Set([
    "NONE",
    "RESTART_SCHEDULER",
    "RESTART_RUNTIME",
    "FREEZE_PROMOTION",
    "ROLLBACK_MODEL",
    "STOP_RUNTIME",
  ]);

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
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
      "Runtime recovery timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function normalizeHealth(
  health = {},
) {
  return {
    status:
      normalizeText(
        health.status,
        "HEALTHY",
      ).toUpperCase(),

    score:
      Number.isFinite(
        Number(
          health.score,
        ),
      )
        ? Number(
            health.score,
          )
        : 100,

    issues:
      Array.isArray(
        health.issues,
      )
        ? clone(
            health.issues,
          )
        : [],

    recommendation:
      normalizeText(
        health.recommendation,
        "CONTINUE_NORMAL_OPERATION",
      ).toUpperCase(),
  };
}

function hasIssue(
  health,
  code,
) {
  return health.issues.some(
    (
      issue,
    ) =>
      issue?.code ===
      code,
  );
}

export function createRuntimeRecoveryPlan({
  health = {},
  schedulerState = {},
  runtimeState = {},
  modelState = {},
  now =
    new Date().toISOString(),
  automaticRollback = true,
  automaticRestart = true,
  maximumRestartAttempts = 3,
} = {}) {
  const timestamp =
    normalizeTimestamp(
      now,
    );

  const normalizedHealth =
    normalizeHealth(
      health,
    );

  const restartAttempts =
    Math.max(
      0,
      Math.floor(
        Number(
          runtimeState
            .restartAttempts ??
          0,
        ),
      ),
    );

  const actions = [];
  const reasons = [];

  if (
    normalizedHealth.status ===
    "HEALTHY"
  ) {
    actions.push(
      "NONE",
    );

    reasons.push(
      "RUNTIME_HEALTHY",
    );
  }
  else {
    actions.push(
      "FREEZE_PROMOTION",
    );

    reasons.push(
      "HEALTH_NOT_NORMAL",
    );
  }

  if (
    hasIssue(
      normalizedHealth,
      "AUDIT_INVALID",
    )
  ) {
    actions.push(
      "STOP_RUNTIME",
    );

    reasons.push(
      "AUDIT_INTEGRITY_FAILURE",
    );
  }

  if (
    hasIssue(
      normalizedHealth,
      "ROLLBACK_REQUIRED",
    ) ||
    modelState.rollbackRequired ===
      true
  ) {
    if (automaticRollback) {
      actions.push(
        "ROLLBACK_MODEL",
      );
    }

    reasons.push(
      "MODEL_ROLLBACK_REQUIRED",
    );
  }

  if (
    hasIssue(
      normalizedHealth,
      "SCHEDULER_FAILED",
    ) &&
    automaticRestart
  ) {
    actions.push(
      "RESTART_SCHEDULER",
    );

    reasons.push(
      "SCHEDULER_FAILURE",
    );
  }

  if (
    hasIssue(
      normalizedHealth,
      "RUNTIME_FAILED",
    ) ||
    hasIssue(
      normalizedHealth,
      "CONSECUTIVE_FAILURE_LIMIT",
    )
  ) {
    if (
      automaticRestart &&
      restartAttempts <
        maximumRestartAttempts
    ) {
      actions.push(
        "RESTART_RUNTIME",
      );

      reasons.push(
        "RUNTIME_RESTART_ALLOWED",
      );
    }
    else {
      actions.push(
        "STOP_RUNTIME",
      );

      reasons.push(
        "RESTART_LIMIT_REACHED",
      );
    }
  }

  const uniqueActions = [
    ...new Set(
      actions,
    ),
  ];

  for (const action of uniqueActions) {
    if (
      !RECOVERY_ACTIONS.has(
        action,
      )
    ) {
      throw new Error(
        `Unsupported recovery action: ${action}`,
      );
    }
  }

  const priority = [
    "STOP_RUNTIME",
    "ROLLBACK_MODEL",
    "RESTART_RUNTIME",
    "RESTART_SCHEDULER",
    "FREEZE_PROMOTION",
    "NONE",
  ];

  const primaryAction =
    priority.find(
      (
        action,
      ) =>
        uniqueActions.includes(
          action,
        ),
    ) ??
    "NONE";

  return {
    version:
      RUNTIME_RECOVERY_CONTROLLER_V2_VERSION,

    id:
      [
        "runtime-recovery",
        Date.parse(
          timestamp,
        ),
      ].join(":"),

    createdAt:
      timestamp,

    status:
      primaryAction ===
      "NONE"
        ? "NOT_REQUIRED"
        : "PLANNED",

    primaryAction,

    actions:
      uniqueActions,

    reasons: [
      ...new Set(
        reasons,
      ),
    ],

    health:
      normalizedHealth,

    schedulerState:
      clone(
        schedulerState,
      ),

    runtimeState:
      clone(
        runtimeState,
      ),

    modelState:
      clone(
        modelState,
      ),

    policy: {
      automaticRollback:
        automaticRollback ===
        true,

      automaticRestart:
        automaticRestart ===
        true,

      maximumRestartAttempts:
        Math.max(
          0,
          Math.floor(
            Number(
              maximumRestartAttempts,
            ),
          ),
        ),
    },
  };
}

export function executeRuntimeRecovery({
  plan,
  handlers = {},
  executedBy = "runtime-recovery-controller",
  executedAt =
    new Date().toISOString(),
} = {}) {
  if (
    !plan ||
    typeof plan !==
      "object"
  ) {
    throw new TypeError(
      "Runtime recovery plan is required.",
    );
  }

  const timestamp =
    normalizeTimestamp(
      executedAt,
    );

  if (
    plan.status ===
    "NOT_REQUIRED"
  ) {
    return {
      ...clone(plan),

      status:
        "SKIPPED",

      executedAt:
        timestamp,

      executedBy,

      results: [],
    };
  }

  const results = [];

  for (const action of plan.actions) {
    if (action === "NONE") {
      continue;
    }

    const handler =
      handlers[action];

    if (
      typeof handler !==
      "function"
    ) {
      results.push({
        action,

        success:
          false,

        skipped:
          true,

        message:
          "No handler registered.",
      });

      continue;
    }

    try {
      const value =
        handler({
          plan:
            clone(plan),

          action,
        });

      results.push({
        action,

        success:
          true,

        skipped:
          false,

        value:
          clone(value),
      });
    }
    catch (error) {
      results.push({
        action,

        success:
          false,

        skipped:
          false,

        error: {
          name:
            error.name,

          message:
            error.message,
        },
      });
    }
  }

  const failed =
    results.filter(
      (
        result,
      ) =>
        result.success !==
        true,
    );

  return {
    ...clone(plan),

    status:
      failed.length ===
      0
        ? "RECOVERED"
        : "PARTIAL_FAILURE",

    executedAt:
      timestamp,

    executedBy:
      normalizeText(
        executedBy,
        "runtime-recovery-controller",
      ),

    results,

    summary: {
      actionCount:
        results.length,

      successCount:
        results.filter(
          (
            result,
          ) =>
            result.success ===
            true,
        ).length,

      failureCount:
        failed.length,
    },
  };
}

export class RuntimeRecoveryControllerV2 {
  constructor({
    handlers = {},
    policy = {},
  } = {}) {
    this.handlers = {
      ...handlers,
    };

    this.policy = {
      ...policy,
    };

    this.history = [];
  }

  plan(input = {}) {
    return createRuntimeRecoveryPlan({
      ...this.policy,
      ...input,
    });
  }

  execute({
    plan,
    handlers = {},
    ...options
  } = {}) {
    const result =
      executeRuntimeRecovery({
        plan,

        handlers: {
          ...this.handlers,
          ...handlers,
        },

        ...options,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
  }

  recover(input = {}) {
    const plan =
      this.plan(
        input,
      );

    return this.execute({
      plan,

      executedAt:
        input.now,
    });
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

export const runtimeRecoveryControllerV2 =
  new RuntimeRecoveryControllerV2();

export default createRuntimeRecoveryPlan;