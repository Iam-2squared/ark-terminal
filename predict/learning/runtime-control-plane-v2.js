import {
  evaluateRuntimeHealth,
} from "./runtime-health-monitor-v2.js";

import {
  createRuntimeRecoveryPlan,
} from "./runtime-recovery-controller-v2.js";

import {
  evaluateCircuitBreaker,
} from "./runtime-circuit-breaker-v2.js";

import {
  evaluateRuntimeFailover,
} from "./runtime-failover-v2.js";

export const RUNTIME_CONTROL_PLANE_V2_VERSION =
  "runtime-control-plane-v2";

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
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
      "Runtime control plane timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

export function evaluateRuntimeControlPlane({
  healthInput = {},
  healthPolicy = {},
  recoveryInput = {},
  recoveryPolicy = {},
  circuitState,
  circuitPolicy = {},
  failoverState,
  failoverPolicy = {},
  now =
    new Date().toISOString(),
} = {}) {
  const timestamp =
    normalizeTimestamp(
      now,
    );

  const health =
    evaluateRuntimeHealth({
      input: {
        ...healthInput,

        timestamp:
          healthInput.timestamp ??
          timestamp,
      },

      policy:
        healthPolicy,
    });

  const recovery =
    createRuntimeRecoveryPlan({
      ...recoveryInput,

      health,

      now:
        timestamp,

      ...recoveryPolicy,
    });

  const circuit =
    circuitState
      ? evaluateCircuitBreaker({
          state:
            circuitState,

          now:
            timestamp,

          policy:
            circuitPolicy,
        })
      : null;

  const failover =
    failoverState
      ? evaluateRuntimeFailover({
          state:
            failoverState,

          now:
            timestamp,

          policy:
            failoverPolicy,
        })
      : null;

  const blockers = [];

  if (
    health.status ===
    "CRITICAL"
  ) {
    blockers.push(
      "CRITICAL_RUNTIME_HEALTH",
    );
  }

  if (
    circuit &&
    circuit.allowed !==
      true
  ) {
    blockers.push(
      "CIRCUIT_BREAKER_BLOCKED",
    );
  }

  if (
    failover?.action ===
    "STOP"
  ) {
    blockers.push(
      "NO_AVAILABLE_RUNTIME",
    );
  }

  const allowRuntime =
    blockers.length ===
    0;

  let action =
    "CONTINUE";

  if (
    failover?.action ===
    "FAILOVER"
  ) {
    action =
      "FAILOVER";
  }
  else if (
    failover?.action ===
    "FAILBACK"
  ) {
    action =
      "FAILBACK";
  }
  else if (
    recovery.primaryAction &&
    recovery.primaryAction !==
    "NONE"
  ) {
    action =
      recovery.primaryAction;
  }
  else if (!allowRuntime) {
    action =
      "STOP_RUNTIME";
  }

  return {
    version:
      RUNTIME_CONTROL_PLANE_V2_VERSION,

    evaluatedAt:
      timestamp,

    allowRuntime,

    action,

    blockers,

    health,

    recovery,

    circuit,

    failover,

    summary: {
      healthStatus:
        health.status,

      healthScore:
        health.score,

      recoveryStatus:
        recovery.status,

      recoveryAction:
        recovery.primaryAction,

      circuitState:
        circuit?.state
          ?.state ??
        null,

      circuitAllowed:
        circuit?.allowed ??
        null,

      failoverAction:
        failover?.action ??
        null,

      failoverTarget:
        failover?.targetRuntimeId ??
        null,
    },
  };
}

export class RuntimeControlPlaneV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  evaluate(input = {}) {
    const result =
      evaluateRuntimeControlPlane({
        ...this.config,
        ...input,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
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

export const runtimeControlPlaneV2 =
  new RuntimeControlPlaneV2();

export default evaluateRuntimeControlPlane;