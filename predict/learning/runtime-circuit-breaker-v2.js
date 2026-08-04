export const RUNTIME_CIRCUIT_BREAKER_V2_VERSION =
  "runtime-circuit-breaker-v2";

const VALID_STATES =
  new Set([
    "CLOSED",
    "OPEN",
    "HALF_OPEN",
  ]);

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
      "Runtime circuit breaker timestamp is invalid.",
    );
  }

  return milliseconds;
}

function normalizePolicy(
  policy = {},
) {
  return {
    failureThreshold:
      Math.max(
        1,
        Math.floor(
          finiteNumber(
            policy.failureThreshold,
            3,
          ),
        ),
      ),

    successThreshold:
      Math.max(
        1,
        Math.floor(
          finiteNumber(
            policy.successThreshold,
            2,
          ),
        ),
      ),

    resetTimeoutMs:
      Math.max(
        1_000,
        Math.floor(
          finiteNumber(
            policy.resetTimeoutMs,
            300_000,
          ),
        ),
      ),

    maximumHalfOpenCalls:
      Math.max(
        1,
        Math.floor(
          finiteNumber(
            policy.maximumHalfOpenCalls,
            1,
          ),
        ),
      ),

    enabled:
      policy.enabled !== false,
  };
}

export function createCircuitBreakerState({
  now =
    new Date().toISOString(),
} = {}) {
  const timestamp =
    normalizeTimestamp(
      now,
    );

  return {
    version:
      RUNTIME_CIRCUIT_BREAKER_V2_VERSION,

    state:
      "CLOSED",

    failureCount:
      0,

    successCount:
      0,

    halfOpenCallCount:
      0,

    openedAt:
      null,

    lastFailureAt:
      null,

    lastSuccessAt:
      null,

    updatedAt:
      new Date(
        timestamp,
      ).toISOString(),

    transitionCount:
      0,
  };
}

function validateState(state) {
  if (
    !state ||
    typeof state !== "object" ||
    Array.isArray(state)
  ) {
    throw new TypeError(
      "Circuit breaker state is required.",
    );
  }

  if (
    !VALID_STATES.has(
      state.state,
    )
  ) {
    throw new TypeError(
      `Unsupported circuit breaker state: ${state.state}`,
    );
  }
}

function transitionState({
  state,
  targetState,
  timestamp,
}) {
  if (
    state.state ===
    targetState
  ) {
    return {
      ...clone(state),

      updatedAt:
        new Date(
          timestamp,
        ).toISOString(),
    };
  }

  return {
    ...clone(state),

    state:
      targetState,

    updatedAt:
      new Date(
        timestamp,
      ).toISOString(),

    transitionCount:
      (
        state.transitionCount ??
        0
      ) +
      1,
  };
}

export function evaluateCircuitBreaker({
  state =
    createCircuitBreakerState(),
  now =
    new Date().toISOString(),
  policy = {},
} = {}) {
  validateState(
    state,
  );

  const timestamp =
    normalizeTimestamp(
      now,
    );

  const normalizedPolicy =
    normalizePolicy(
      policy,
    );

  if (
    normalizedPolicy.enabled !==
    true
  ) {
    return {
      allowed:
        true,

      reason:
        "CIRCUIT_BREAKER_DISABLED",

      state:
        clone(state),

      policy:
        normalizedPolicy,
    };
  }

  let nextState =
    clone(state);

  if (
    state.state ===
      "OPEN" &&
    state.openedAt
  ) {
    const openedAt =
      normalizeTimestamp(
        state.openedAt,
      );

    if (
      timestamp -
        openedAt >=
      normalizedPolicy
        .resetTimeoutMs
    ) {
      nextState =
        transitionState({
          state,

          targetState:
            "HALF_OPEN",

          timestamp,
        });

      nextState.failureCount =
        0;

      nextState.successCount =
        0;

      nextState.halfOpenCallCount =
        0;
    }
  }

  if (
    nextState.state ===
    "OPEN"
  ) {
    return {
      allowed:
        false,

      reason:
        "CIRCUIT_OPEN",

      state:
        nextState,

      policy:
        normalizedPolicy,
    };
  }

  if (
    nextState.state ===
    "HALF_OPEN"
  ) {
    const currentCalls =
      Math.max(
        0,
        Math.floor(
          finiteNumber(
            nextState
              .halfOpenCallCount,
            0,
          ),
        ),
      );

    if (
      currentCalls >=
      normalizedPolicy
        .maximumHalfOpenCalls
    ) {
      return {
        allowed:
          false,

        reason:
          "HALF_OPEN_LIMIT_REACHED",

        state:
          nextState,

        policy:
          normalizedPolicy,
      };
    }

    nextState.halfOpenCallCount =
      currentCalls +
      1;

    nextState.updatedAt =
      new Date(
        timestamp,
      ).toISOString();

    return {
      allowed:
        true,

      reason:
        "HALF_OPEN_PROBE_ALLOWED",

      state:
        nextState,

      policy:
        normalizedPolicy,
    };
  }

  return {
    allowed:
      true,

    reason:
      "CIRCUIT_CLOSED",

    state:
      nextState,

    policy:
      normalizedPolicy,
  };
}

export function recordCircuitSuccess({
  state,
  now =
    new Date().toISOString(),
  policy = {},
} = {}) {
  validateState(
    state,
  );

  const timestamp =
    normalizeTimestamp(
      now,
    );

  const normalizedPolicy =
    normalizePolicy(
      policy,
    );

  let nextState = {
    ...clone(state),

    successCount:
      (
        state.successCount ??
        0
      ) +
      1,

    failureCount:
      0,

    lastSuccessAt:
      new Date(
        timestamp,
      ).toISOString(),

    updatedAt:
      new Date(
        timestamp,
      ).toISOString(),
  };

  if (
    state.state ===
      "HALF_OPEN" &&
    nextState.successCount >=
      normalizedPolicy
        .successThreshold
  ) {
    nextState =
      transitionState({
        state:
          nextState,

        targetState:
          "CLOSED",

        timestamp,
      });

    nextState.failureCount =
      0;

    nextState.successCount =
      0;

    nextState.halfOpenCallCount =
      0;

    nextState.openedAt =
      null;
  }

  return nextState;
}

export function recordCircuitFailure({
  state,
  now =
    new Date().toISOString(),
  policy = {},
} = {}) {
  validateState(
    state,
  );

  const timestamp =
    normalizeTimestamp(
      now,
    );

  const normalizedPolicy =
    normalizePolicy(
      policy,
    );

  let nextState = {
    ...clone(state),

    failureCount:
      (
        state.failureCount ??
        0
      ) +
      1,

    successCount:
      0,

    lastFailureAt:
      new Date(
        timestamp,
      ).toISOString(),

    updatedAt:
      new Date(
        timestamp,
      ).toISOString(),
  };

  const shouldOpen =
    state.state ===
      "HALF_OPEN" ||
    nextState.failureCount >=
      normalizedPolicy
        .failureThreshold;

  if (shouldOpen) {
    nextState =
      transitionState({
        state:
          nextState,

        targetState:
          "OPEN",

        timestamp,
      });

    nextState.openedAt =
      new Date(
        timestamp,
      ).toISOString();

    nextState.halfOpenCallCount =
      0;
  }

  return nextState;
}

export async function executeWithCircuitBreaker({
  state =
    createCircuitBreakerState(),
  operation,
  now =
    new Date().toISOString(),
  policy = {},
} = {}) {
  if (
    typeof operation !==
    "function"
  ) {
    throw new TypeError(
      "Circuit breaker operation is required.",
    );
  }

  const evaluation =
    evaluateCircuitBreaker({
      state,
      now,
      policy,
    });

  if (!evaluation.allowed) {
    return {
      executed:
        false,

      success:
        false,

      reason:
        evaluation.reason,

      state:
        evaluation.state,

      value:
        null,

      error:
        null,
    };
  }

  try {
    const value =
      await operation();

    const nextState =
      recordCircuitSuccess({
        state:
          evaluation.state,

        now,

        policy,
      });

    return {
      executed:
        true,

      success:
        true,

      reason:
        "OPERATION_SUCCEEDED",

      state:
        nextState,

      value:
        clone(value),

      error:
        null,
    };
  }
  catch (error) {
    const nextState =
      recordCircuitFailure({
        state:
          evaluation.state,

        now,

        policy,
      });

    return {
      executed:
        true,

      success:
        false,

      reason:
        "OPERATION_FAILED",

      state:
        nextState,

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

export class RuntimeCircuitBreakerV2 {
  constructor({
    policy = {},
    state = null,
  } = {}) {
    this.policy =
      normalizePolicy(
        policy,
      );

    this.state =
      state
        ? clone(state)
        : createCircuitBreakerState();

    this.history = [];
  }

  evaluate(input = {}) {
    const result =
      evaluateCircuitBreaker({
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

  success(input = {}) {
    this.state =
      recordCircuitSuccess({
        state:
          this.state,

        policy:
          this.policy,

        ...input,
      });

    return clone(
      this.state,
    );
  }

  failure(input = {}) {
    this.state =
      recordCircuitFailure({
        state:
          this.state,

        policy:
          this.policy,

        ...input,
      });

    return clone(
      this.state,
    );
  }

  async execute({
    operation,
    now,
  } = {}) {
    const result =
      await executeWithCircuitBreaker({
        state:
          this.state,

        operation,

        now,

        policy:
          this.policy,
      });

    this.state =
      clone(
        result.state,
      );

    this.history.push({
      timestamp:
        this.state.updatedAt,

      executed:
        result.executed,

      success:
        result.success,

      reason:
        result.reason,

      state:
        this.state.state,
    });

    return clone(result);
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

  reset({
    now =
      new Date().toISOString(),
  } = {}) {
    this.state =
      createCircuitBreakerState({
        now,
      });

    this.history = [];

    return this.getState();
  }
}

export const runtimeCircuitBreakerV2 =
  new RuntimeCircuitBreakerV2();

export default evaluateCircuitBreaker;