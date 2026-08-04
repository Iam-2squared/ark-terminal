import test from "node:test";
import assert from "node:assert/strict";

import {
  RuntimeCircuitBreakerV2,
  createCircuitBreakerState,
  evaluateCircuitBreaker,
  executeWithCircuitBreaker,
  recordCircuitFailure,
  recordCircuitSuccess,
} from "../learning/runtime-circuit-breaker-v2.js";

const NOW =
  "2026-08-04T00:00:00.000Z";

test(
  "Circuit breaker starts closed",
  () => {
    const state =
      createCircuitBreakerState({
        now:
          NOW,
      });

    assert.equal(
      state.state,
      "CLOSED",
    );

    assert.equal(
      state.failureCount,
      0,
    );
  },
);

test(
  "Closed circuit allows execution",
  () => {
    const result =
      evaluateCircuitBreaker({
        state:
          createCircuitBreakerState({
            now:
              NOW,
          }),

        now:
          NOW,
      });

    assert.equal(
      result.allowed,
      true,
    );

    assert.equal(
      result.reason,
      "CIRCUIT_CLOSED",
    );
  },
);

test(
  "Failure threshold opens circuit",
  () => {
    let state =
      createCircuitBreakerState({
        now:
          NOW,
      });

    state =
      recordCircuitFailure({
        state,
        now:
          NOW,

        policy: {
          failureThreshold:
            2,
        },
      });

    state =
      recordCircuitFailure({
        state,
        now:
          "2026-08-04T00:01:00.000Z",

        policy: {
          failureThreshold:
            2,
        },
      });

    assert.equal(
      state.state,
      "OPEN",
    );
  },
);

test(
  "Open circuit blocks execution",
  () => {
    const state = {
      ...createCircuitBreakerState({
        now:
          NOW,
      }),

      state:
        "OPEN",

      openedAt:
        NOW,
    };

    const result =
      evaluateCircuitBreaker({
        state,

        now:
          "2026-08-04T00:01:00.000Z",

        policy: {
          resetTimeoutMs:
            300_000,
        },
      });

    assert.equal(
      result.allowed,
      false,
    );

    assert.equal(
      result.reason,
      "CIRCUIT_OPEN",
    );
  },
);

test(
  "Open circuit becomes half open after timeout",
  () => {
    const state = {
      ...createCircuitBreakerState({
        now:
          NOW,
      }),

      state:
        "OPEN",

      openedAt:
        NOW,
    };

    const result =
      evaluateCircuitBreaker({
        state,

        now:
          "2026-08-04T00:10:00.000Z",

        policy: {
          resetTimeoutMs:
            300_000,
        },
      });

    assert.equal(
      result.allowed,
      true,
    );

    assert.equal(
      result.state.state,
      "HALF_OPEN",
    );

    assert.equal(
      result.reason,
      "HALF_OPEN_PROBE_ALLOWED",
    );
  },
);

test(
  "Half open success closes circuit",
  () => {
    const state = {
      ...createCircuitBreakerState({
        now:
          NOW,
      }),

      state:
        "HALF_OPEN",

      successCount:
        0,

      halfOpenCallCount:
        1,
    };

    const nextState =
      recordCircuitSuccess({
        state,

        now:
          "2026-08-04T00:10:00.000Z",

        policy: {
          successThreshold:
            1,
        },
      });

    assert.equal(
      nextState.state,
      "CLOSED",
    );
  },
);

test(
  "Half open failure reopens circuit",
  () => {
    const state = {
      ...createCircuitBreakerState({
        now:
          NOW,
      }),

      state:
        "HALF_OPEN",
    };

    const nextState =
      recordCircuitFailure({
        state,

        now:
          "2026-08-04T00:10:00.000Z",
      });

    assert.equal(
      nextState.state,
      "OPEN",
    );
  },
);

test(
  "Circuit breaker executes successful operation",
  async () => {
    const result =
      await executeWithCircuitBreaker({
        state:
          createCircuitBreakerState({
            now:
              NOW,
          }),

        now:
          NOW,

        operation:
          async () => ({
            ok:
              true,
          }),
      });

    assert.equal(
      result.executed,
      true,
    );

    assert.equal(
      result.success,
      true,
    );

    assert.equal(
      result.value.ok,
      true,
    );
  },
);

test(
  "Circuit breaker records failed operation",
  async () => {
    const result =
      await executeWithCircuitBreaker({
        state:
          createCircuitBreakerState({
            now:
              NOW,
          }),

        now:
          NOW,

        policy: {
          failureThreshold:
            1,
        },

        operation:
          async () => {
            throw new Error(
              "runtime failed",
            );
          },
      });

    assert.equal(
      result.success,
      false,
    );

    assert.equal(
      result.state.state,
      "OPEN",
    );

    assert.equal(
      result.error.message,
      "runtime failed",
    );
  },
);

test(
  "Circuit breaker class stores history",
  async () => {
    const breaker =
      new RuntimeCircuitBreakerV2({
        policy: {
          failureThreshold:
            1,
        },
      });

    await breaker.execute({
      now:
        NOW,

      operation:
        async () =>
          "ok",
    });

    assert.equal(
      breaker
        .getHistory()
        .length,
      1,
    );

    assert.equal(
      breaker
        .getState()
        .state,
      "CLOSED",
    );

    breaker.reset({
      now:
        NOW,
    });

    assert.equal(
      breaker
        .getHistory()
        .length,
      0,
    );
  },
);

test(
  "Circuit breaker validates timestamp",
  () => {
    assert.throws(
      () =>
        createCircuitBreakerState({
          now:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);