export const RUNTIME_FAILOVER_V2_VERSION =
  "runtime-failover-v2";

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function finiteNumber(
  value,
  fallback = 0,
) {
  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
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
      "Runtime failover timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function normalizeRuntime(
  runtime,
  fallbackId,
) {
  if (
    !runtime ||
    typeof runtime !== "object" ||
    Array.isArray(runtime)
  ) {
    return {
      id:
        fallbackId,

      healthy:
        false,

      available:
        false,

      priority:
        0,

      revision:
        0,

      state:
        null,
    };
  }

  return {
    id:
      normalizeText(
        runtime.id,
        fallbackId,
      ),

    healthy:
      runtime.healthy !== false,

    available:
      runtime.available !== false,

    priority:
      finiteNumber(
        runtime.priority,
        0,
      ),

    revision:
      Math.max(
        0,
        Math.floor(
          finiteNumber(
            runtime.revision,
            0,
          ),
        ),
      ),

    state:
      clone(
        runtime.state ??
        null,
      ),

    metadata:
      clone(
        runtime.metadata ??
        {},
      ),
  };
}

function normalizePolicy(
  policy = {},
) {
  return {
    automaticFailover:
      policy.automaticFailover !==
      false,

    automaticFailback:
      policy.automaticFailback !==
      false,

    requireStateSync:
      policy.requireStateSync !==
      false,

    maximumRetryAttempts:
      Math.max(
        0,
        Math.floor(
          finiteNumber(
            policy.maximumRetryAttempts,
            2,
          ),
        ),
      ),

    failbackCooldownMs:
      Math.max(
        0,
        Math.floor(
          finiteNumber(
            policy.failbackCooldownMs,
            300_000,
          ),
        ),
      ),
  };
}

export function createRuntimeFailoverState({
  primary,
  secondary,
  now =
    new Date().toISOString(),
} = {}) {
  const timestamp =
    normalizeTimestamp(
      now,
    );

  return {
    version:
      RUNTIME_FAILOVER_V2_VERSION,

    activeRuntimeId:
      normalizeRuntime(
        primary,
        "primary",
      ).id,

    primary:
      normalizeRuntime(
        primary,
        "primary",
      ),

    secondary:
      normalizeRuntime(
        secondary,
        "secondary",
      ),

    failoverCount:
      0,

    failbackCount:
      0,

    retryCount:
      0,

    lastFailoverAt:
      null,

    lastFailbackAt:
      null,

    updatedAt:
      timestamp,

    history: [],
  };
}

export function evaluateRuntimeFailover({
  state,
  now =
    new Date().toISOString(),
  policy = {},
} = {}) {
  if (
    !state ||
    typeof state !== "object"
  ) {
    throw new TypeError(
      "Runtime failover state is required.",
    );
  }

  const timestamp =
    normalizeTimestamp(
      now,
    );

  const normalizedPolicy =
    normalizePolicy(
      policy,
    );

  const primary =
    normalizeRuntime(
      state.primary,
      "primary",
    );

  const secondary =
    normalizeRuntime(
      state.secondary,
      "secondary",
    );

  const activeRuntimeId =
    normalizeText(
      state.activeRuntimeId,
      primary.id,
    );

  const primaryReady =
    primary.available &&
    primary.healthy;

  const secondaryReady =
    secondary.available &&
    secondary.healthy;

  let action =
    "NONE";

  let targetRuntimeId =
    activeRuntimeId;

  let reason =
    "ACTIVE_RUNTIME_HEALTHY";

  if (
    activeRuntimeId ===
      primary.id &&
    !primaryReady
  ) {
    if (
      normalizedPolicy
        .automaticFailover &&
      secondaryReady
    ) {
      action =
        "FAILOVER";

      targetRuntimeId =
        secondary.id;

      reason =
        "PRIMARY_UNAVAILABLE";
    }
    else {
      action =
        "STOP";

      reason =
        secondaryReady
          ? "AUTOMATIC_FAILOVER_DISABLED"
          : "NO_HEALTHY_RUNTIME";
    }
  }
  else if (
    activeRuntimeId ===
      secondary.id &&
    primaryReady &&
    normalizedPolicy
      .automaticFailback
  ) {
    const lastFailoverAt =
      state.lastFailoverAt
        ? Date.parse(
            state.lastFailoverAt,
          )
        : null;

    const nowMs =
      Date.parse(
        timestamp,
      );

    const cooldownComplete =
      lastFailoverAt ===
        null ||
      nowMs -
        lastFailoverAt >=
        normalizedPolicy
          .failbackCooldownMs;

    if (cooldownComplete) {
      action =
        "FAILBACK";

      targetRuntimeId =
        primary.id;

      reason =
        "PRIMARY_RECOVERED";
    }
    else {
      reason =
        "FAILBACK_COOLDOWN";
    }
  }

  const sourceRuntime =
    activeRuntimeId ===
      primary.id
      ? primary
      : secondary;

  const targetRuntime =
    targetRuntimeId ===
      primary.id
      ? primary
      : secondary;

  const stateSyncRequired =
    normalizedPolicy
      .requireStateSync &&
    [
      "FAILOVER",
      "FAILBACK",
    ].includes(
      action,
    );

  const stateSyncPossible =
    !stateSyncRequired ||
    (
      sourceRuntime.state !==
        null &&
      targetRuntime !==
        null
    );

  if (
    stateSyncRequired &&
    !stateSyncPossible
  ) {
    action =
      "STOP";

    reason =
      "STATE_SYNC_UNAVAILABLE";
  }

  return {
    version:
      RUNTIME_FAILOVER_V2_VERSION,

    action,

    reason,

    activeRuntimeId,

    targetRuntimeId,

    primaryReady,

    secondaryReady,

    stateSyncRequired,

    stateSyncPossible,

    policy:
      normalizedPolicy,

    evaluatedAt:
      timestamp,
  };
}

export function applyRuntimeFailover({
  state,
  evaluation,
  now =
    new Date().toISOString(),
} = {}) {
  if (
    !state ||
    typeof state !== "object"
  ) {
    throw new TypeError(
      "Runtime failover state is required.",
    );
  }

  if (
    !evaluation ||
    typeof evaluation !==
      "object"
  ) {
    throw new TypeError(
      "Runtime failover evaluation is required.",
    );
  }

  const timestamp =
    normalizeTimestamp(
      now,
    );

  const nextState =
    clone(
      state,
    );

  if (
    evaluation.action ===
    "FAILOVER"
  ) {
    nextState.activeRuntimeId =
      evaluation.targetRuntimeId;

    nextState.failoverCount =
      (
        nextState.failoverCount ??
        0
      ) +
      1;

    nextState.lastFailoverAt =
      timestamp;

    if (
      evaluation
        .stateSyncRequired
    ) {
      nextState.secondary.state =
        clone(
          nextState.primary.state,
        );

      nextState.secondary.revision =
        nextState.primary.revision;
    }
  }
  else if (
    evaluation.action ===
    "FAILBACK"
  ) {
    nextState.activeRuntimeId =
      evaluation.targetRuntimeId;

    nextState.failbackCount =
      (
        nextState.failbackCount ??
        0
      ) +
      1;

    nextState.lastFailbackAt =
      timestamp;

    if (
      evaluation
        .stateSyncRequired
    ) {
      nextState.primary.state =
        clone(
          nextState.secondary.state,
        );

      nextState.primary.revision =
        nextState.secondary.revision;
    }
  }

  nextState.updatedAt =
    timestamp;

  nextState.history = [
    ...(
      nextState.history ??
      []
    ),

    {
      action:
        evaluation.action,

      reason:
        evaluation.reason,

      sourceRuntimeId:
        evaluation.activeRuntimeId,

      targetRuntimeId:
        evaluation.targetRuntimeId,

      timestamp,
    },
  ];

  return nextState;
}

export async function executeRuntimeFailover({
  state,
  primaryOperation,
  secondaryOperation,
  now =
    new Date().toISOString(),
  policy = {},
} = {}) {
  const evaluation =
    evaluateRuntimeFailover({
      state,
      now,
      policy,
    });

  if (
    evaluation.action ===
    "STOP"
  ) {
    return {
      status:
        "STOPPED",

      executed:
        false,

      evaluation,

      state:
        applyRuntimeFailover({
          state,
          evaluation,
          now,
        }),

      value:
        null,

      error:
        null,
    };
  }

  const nextState =
    applyRuntimeFailover({
      state,
      evaluation,
      now,
    });

  const operation =
    nextState.activeRuntimeId ===
      nextState.primary.id
      ? primaryOperation
      : secondaryOperation;

  if (
    typeof operation !==
    "function"
  ) {
    throw new TypeError(
      "Active runtime operation is required.",
    );
  }

  try {
    const value =
      await operation({
        runtimeId:
          nextState
            .activeRuntimeId,

        state:
          clone(
            nextState,
          ),
      });

    return {
      status:
        "EXECUTED",

      executed:
        true,

      evaluation,

      state:
        nextState,

      value:
        clone(value),

      error:
        null,
    };
  }
  catch (error) {
    const failedState =
      clone(
        nextState,
      );

    failedState.retryCount =
      (
        failedState.retryCount ??
        0
      ) +
      1;

    return {
      status:
        "FAILED",

      executed:
        true,

      evaluation,

      state:
        failedState,

      value:
        null,

      error: {
        name:
          error.name,

        message:
          error.message,
      },
    };
  }
}

export class RuntimeFailoverV2 {
  constructor({
    primary,
    secondary,
    policy = {},
    now =
      new Date().toISOString(),
  } = {}) {
    this.policy =
      normalizePolicy(
        policy,
      );

    this.state =
      createRuntimeFailoverState({
        primary,
        secondary,
        now,
      });
  }

  evaluate(input = {}) {
    return evaluateRuntimeFailover({
      state:
        this.state,

      policy:
        this.policy,

      ...input,
    });
  }

  apply(input = {}) {
    const evaluation =
      input.evaluation ??
      this.evaluate(
        input,
      );

    this.state =
      applyRuntimeFailover({
        state:
          this.state,

        evaluation,

        now:
          input.now,
      });

    return clone(
      this.state,
    );
  }

  async execute(input = {}) {
    const result =
      await executeRuntimeFailover({
        state:
          this.state,

        policy:
          this.policy,

        ...input,
      });

    this.state =
      clone(
        result.state,
      );

    return clone(result);
  }

  updateRuntime(
    runtimeId,
    patch = {},
  ) {
    if (
      runtimeId ===
      this.state.primary.id
    ) {
      this.state.primary = {
        ...this.state.primary,
        ...clone(patch),
      };
    }
    else if (
      runtimeId ===
      this.state.secondary.id
    ) {
      this.state.secondary = {
        ...this.state.secondary,
        ...clone(patch),
      };
    }
    else {
      throw new Error(
        `Unknown runtime: ${runtimeId}`,
      );
    }

    return this.getState();
  }

  getState() {
    return clone(
      this.state,
    );
  }

  reset({
    primary,
    secondary,
    now =
      new Date().toISOString(),
  } = {}) {
    this.state =
      createRuntimeFailoverState({
        primary:
          primary ??
          this.state.primary,

        secondary:
          secondary ??
          this.state.secondary,

        now,
      });

    return this.getState();
  }
}

export const runtimeFailoverV2 =
  new RuntimeFailoverV2();

export default evaluateRuntimeFailover;