import test from "node:test";
import assert from "node:assert/strict";

import {
  RuntimeFailoverV2,
  applyRuntimeFailover,
  createRuntimeFailoverState,
  evaluateRuntimeFailover,
  executeRuntimeFailover,
} from "../learning/runtime-failover-v2.js";

const NOW =
  "2026-08-04T00:00:00.000Z";

function primary(
  overrides = {},
) {
  return {
    id:
      "primary",

    healthy:
      true,

    available:
      true,

    revision:
      2,

    state: {
      modelRevision:
        2,
    },

    ...overrides,
  };
}

function secondary(
  overrides = {},
) {
  return {
    id:
      "secondary",

    healthy:
      true,

    available:
      true,

    revision:
      1,

    state: {
      modelRevision:
        1,
    },

    ...overrides,
  };
}

test(
  "Failover state starts on primary",
  () => {
    const state =
      createRuntimeFailoverState({
        primary:
          primary(),

        secondary:
          secondary(),

        now:
          NOW,
      });

    assert.equal(
      state.activeRuntimeId,
      "primary",
    );
  },
);

test(
  "Healthy primary requires no failover",
  () => {
    const state =
      createRuntimeFailoverState({
        primary:
          primary(),

        secondary:
          secondary(),

        now:
          NOW,
      });

    const result =
      evaluateRuntimeFailover({
        state,
        now:
          NOW,
      });

    assert.equal(
      result.action,
      "NONE",
    );
  },
);

test(
  "Unhealthy primary fails over to secondary",
  () => {
    const state =
      createRuntimeFailoverState({
        primary:
          primary({
            healthy:
              false,
          }),

        secondary:
          secondary(),

        now:
          NOW,
      });

    const result =
      evaluateRuntimeFailover({
        state,
        now:
          NOW,
      });

    assert.equal(
      result.action,
      "FAILOVER",
    );

    assert.equal(
      result.targetRuntimeId,
      "secondary",
    );
  },
);

test(
  "Failover synchronizes runtime state",
  () => {
    const state =
      createRuntimeFailoverState({
        primary:
          primary({
            healthy:
              false,
          }),

        secondary:
          secondary(),

        now:
          NOW,
      });

    const evaluation =
      evaluateRuntimeFailover({
        state,
        now:
          NOW,
      });

    const nextState =
      applyRuntimeFailover({
        state,
        evaluation,
        now:
          NOW,
      });

    assert.equal(
      nextState.activeRuntimeId,
      "secondary",
    );

    assert.equal(
      nextState.secondary.revision,
      2,
    );

    assert.equal(
      nextState.failoverCount,
      1,
    );
  },
);

test(
  "No healthy runtime stops execution",
  () => {
    const state =
      createRuntimeFailoverState({
        primary:
          primary({
            healthy:
              false,
          }),

        secondary:
          secondary({
            healthy:
              false,
          }),

        now:
          NOW,
      });

    const result =
      evaluateRuntimeFailover({
        state,
        now:
          NOW,
      });

    assert.equal(
      result.action,
      "STOP",
    );
  },
);

test(
  "Recovered primary fails back after cooldown",
  () => {
    const state =
      createRuntimeFailoverState({
        primary:
          primary(),

        secondary:
          secondary(),

        now:
          NOW,
      });

    state.activeRuntimeId =
      "secondary";

    state.lastFailoverAt =
      NOW;

    const result =
      evaluateRuntimeFailover({
        state,

        now:
          "2026-08-04T00:10:00.000Z",

        policy: {
          failbackCooldownMs:
            300_000,
        },
      });

    assert.equal(
      result.action,
      "FAILBACK",
    );

    assert.equal(
      result.targetRuntimeId,
      "primary",
    );
  },
);

test(
  "Failback waits during cooldown",
  () => {
    const state =
      createRuntimeFailoverState({
        primary:
          primary(),

        secondary:
          secondary(),

        now:
          NOW,
      });

    state.activeRuntimeId =
      "secondary";

    state.lastFailoverAt =
      NOW;

    const result =
      evaluateRuntimeFailover({
        state,

        now:
          "2026-08-04T00:01:00.000Z",

        policy: {
          failbackCooldownMs:
            300_000,
        },
      });

    assert.equal(
      result.action,
      "NONE",
    );

    assert.equal(
      result.reason,
      "FAILBACK_COOLDOWN",
    );
  },
);

test(
  "Failover executes secondary runtime",
  async () => {
    const state =
      createRuntimeFailoverState({
        primary:
          primary({
            healthy:
              false,
          }),

        secondary:
          secondary(),

        now:
          NOW,
      });

    const result =
      await executeRuntimeFailover({
        state,

        now:
          NOW,

        primaryOperation:
          async () =>
            "primary",

        secondaryOperation:
          async () =>
            "secondary",
      });

    assert.equal(
      result.status,
      "EXECUTED",
    );

    assert.equal(
      result.value,
      "secondary",
    );

    assert.equal(
      result.state
        .activeRuntimeId,
      "secondary",
    );
  },
);

test(
  "Runtime failure is recorded",
  async () => {
    const state =
      createRuntimeFailoverState({
        primary:
          primary(),

        secondary:
          secondary(),

        now:
          NOW,
      });

    const result =
      await executeRuntimeFailover({
        state,

        now:
          NOW,

        primaryOperation:
          async () => {
            throw new Error(
              "primary failed",
            );
          },

        secondaryOperation:
          async () =>
            "secondary",
      });

    assert.equal(
      result.status,
      "FAILED",
    );

    assert.equal(
      result.state.retryCount,
      1,
    );

    assert.equal(
      result.error.message,
      "primary failed",
    );
  },
);

test(
  "Runtime failover class updates health",
  () => {
    const failover =
      new RuntimeFailoverV2({
        primary:
          primary(),

        secondary:
          secondary(),

        now:
          NOW,
      });

    failover.updateRuntime(
      "primary",
      {
        healthy:
          false,
      },
    );

    const evaluation =
      failover.evaluate({
        now:
          NOW,
      });

    assert.equal(
      evaluation.action,
      "FAILOVER",
    );
  },
);

test(
  "Runtime failover validates timestamp",
  () => {
    assert.throws(
      () =>
        createRuntimeFailoverState({
          now:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);