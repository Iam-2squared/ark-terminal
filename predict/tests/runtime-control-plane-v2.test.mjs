import test from "node:test";
import assert from "node:assert/strict";

import {
  RuntimeControlPlaneV2,
  evaluateRuntimeControlPlane,
} from "../learning/runtime-control-plane-v2.js";

import {
  createCircuitBreakerState,
} from "../learning/runtime-circuit-breaker-v2.js";

import {
  createRuntimeFailoverState,
} from "../learning/runtime-failover-v2.js";

const NOW =
  "2026-08-04T00:00:00.000Z";

function healthyFailoverState() {
  return createRuntimeFailoverState({
    primary: {
      id:
        "primary",

      healthy:
        true,

      available:
        true,

      revision:
        2,

      state: {
        revision:
          2,
      },
    },

    secondary: {
      id:
        "secondary",

      healthy:
        true,

      available:
        true,

      revision:
        2,

      state: {
        revision:
          2,
      },
    },

    now:
      NOW,
  });
}

test(
  "Control plane allows healthy runtime",
  () => {
    const result =
      evaluateRuntimeControlPlane({
        healthInput: {
          runtimeStatus:
            "EXECUTED",

          schedulerStatus:
            "EXECUTED",

          auditValid:
            true,

          latencyMs:
            100,

          failureRate:
            0,
        },

        circuitState:
          createCircuitBreakerState({
            now:
              NOW,
          }),

        failoverState:
          healthyFailoverState(),

        now:
          NOW,
      });

    assert.equal(
      result.allowRuntime,
      true,
    );

    assert.equal(
      result.action,
      "CONTINUE",
    );

    assert.equal(
      result.health.status,
      "HEALTHY",
    );
  },
);

test(
  "Control plane blocks critical runtime",
  () => {
    const result =
      evaluateRuntimeControlPlane({
        healthInput: {
          runtimeStatus:
            "FAILED",

          auditValid:
            true,
        },

        circuitState:
          createCircuitBreakerState({
            now:
              NOW,
          }),

        failoverState:
          healthyFailoverState(),

        now:
          NOW,
      });

    assert.equal(
      result.allowRuntime,
      false,
    );

    assert.ok(
      result.blockers.includes(
        "CRITICAL_RUNTIME_HEALTH",
      ),
    );

    assert.equal(
      result.recovery.primaryAction,
      "RESTART_RUNTIME",
    );
  },
);

test(
  "Control plane detects open circuit",
  () => {
    const circuitState = {
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
      evaluateRuntimeControlPlane({
        healthInput: {
          runtimeStatus:
            "EXECUTED",
        },

        circuitState,

        circuitPolicy: {
          resetTimeoutMs:
            300000,
        },

        failoverState:
          healthyFailoverState(),

        now:
          "2026-08-04T00:01:00.000Z",
      });

    assert.equal(
      result.allowRuntime,
      false,
    );

    assert.ok(
      result.blockers.includes(
        "CIRCUIT_BREAKER_BLOCKED",
      ),
    );
  },
);

test(
  "Control plane requests failover",
  () => {
    const failoverState =
      healthyFailoverState();

    failoverState.primary.healthy =
      false;

    const result =
      evaluateRuntimeControlPlane({
        healthInput: {
          runtimeStatus:
            "EXECUTED",
        },

        circuitState:
          createCircuitBreakerState({
            now:
              NOW,
          }),

        failoverState,

        now:
          NOW,
      });

    assert.equal(
      result.action,
      "FAILOVER",
    );

    assert.equal(
      result.failover
        .targetRuntimeId,
      "secondary",
    );
  },
);

test(
  "Control plane stops when no runtime is healthy",
  () => {
    const failoverState =
      healthyFailoverState();

    failoverState.primary.healthy =
      false;

    failoverState.secondary.healthy =
      false;

    const result =
      evaluateRuntimeControlPlane({
        healthInput: {
          runtimeStatus:
            "EXECUTED",
        },

        failoverState,

        now:
          NOW,
      });

    assert.equal(
      result.allowRuntime,
      false,
    );

    assert.ok(
      result.blockers.includes(
        "NO_AVAILABLE_RUNTIME",
      ),
    );
  },
);

test(
  "Control plane class stores history",
  () => {
    const controlPlane =
      new RuntimeControlPlaneV2();

    controlPlane.evaluate({
      healthInput: {
        runtimeStatus:
          "EXECUTED",
      },

      now:
        NOW,
    });

    assert.equal(
      controlPlane
        .getHistory()
        .length,
      1,
    );

    assert.equal(
      controlPlane.latest()
        .health.status,
      "HEALTHY",
    );

    controlPlane.reset();

    assert.equal(
      controlPlane
        .getHistory()
        .length,
      0,
    );
  },
);

test(
  "Control plane validates timestamp",
  () => {
    assert.throws(
      () =>
        evaluateRuntimeControlPlane({
          now:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);