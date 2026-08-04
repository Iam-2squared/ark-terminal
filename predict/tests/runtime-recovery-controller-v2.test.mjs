import test from "node:test";
import assert from "node:assert/strict";

import {
  RuntimeRecoveryControllerV2,
  createRuntimeRecoveryPlan,
  executeRuntimeRecovery,
} from "../learning/runtime-recovery-controller-v2.js";

const NOW =
  "2026-08-04T00:00:00.000Z";

test(
  "Healthy runtime requires no recovery",
  () => {
    const plan =
      createRuntimeRecoveryPlan({
        health: {
          status:
            "HEALTHY",

          issues:
            [],
        },

        now:
          NOW,
      });

    assert.equal(
      plan.status,
      "NOT_REQUIRED",
    );

    assert.equal(
      plan.primaryAction,
      "NONE",
    );
  },
);

test(
  "Runtime failure creates restart plan",
  () => {
    const plan =
      createRuntimeRecoveryPlan({
        health: {
          status:
            "CRITICAL",

          issues: [
            {
              code:
                "RUNTIME_FAILED",
            },
          ],
        },

        runtimeState: {
          restartAttempts:
            0,
        },

        now:
          NOW,
      });

    assert.equal(
      plan.primaryAction,
      "RESTART_RUNTIME",
    );

    assert.ok(
      plan.actions.includes(
        "FREEZE_PROMOTION",
      ),
    );

    assert.ok(
      plan.actions.includes(
        "RESTART_RUNTIME",
      ),
    );
  },
);

test(
  "Restart limit forces runtime stop",
  () => {
    const plan =
      createRuntimeRecoveryPlan({
        health: {
          status:
            "CRITICAL",

          issues: [
            {
              code:
                "RUNTIME_FAILED",
            },
          ],
        },

        runtimeState: {
          restartAttempts:
            3,
        },

        maximumRestartAttempts:
          3,

        now:
          NOW,
      });

    assert.equal(
      plan.primaryAction,
      "STOP_RUNTIME",
    );
  },
);

test(
  "Rollback issue creates rollback action",
  () => {
    const plan =
      createRuntimeRecoveryPlan({
        health: {
          status:
            "CRITICAL",

          issues: [
            {
              code:
                "ROLLBACK_REQUIRED",
            },
          ],
        },

        now:
          NOW,
      });

    assert.ok(
      plan.actions.includes(
        "ROLLBACK_MODEL",
      ),
    );

    assert.equal(
      plan.primaryAction,
      "ROLLBACK_MODEL",
    );
  },
);

test(
  "Invalid audit forces runtime stop",
  () => {
    const plan =
      createRuntimeRecoveryPlan({
        health: {
          status:
            "CRITICAL",

          issues: [
            {
              code:
                "AUDIT_INVALID",
            },
          ],
        },

        now:
          NOW,
      });

    assert.equal(
      plan.primaryAction,
      "STOP_RUNTIME",
    );
  },
);

test(
  "Recovery executes registered handlers",
  () => {
    const plan =
      createRuntimeRecoveryPlan({
        health: {
          status:
            "CRITICAL",

          issues: [
            {
              code:
                "SCHEDULER_FAILED",
            },
          ],
        },

        now:
          NOW,
      });

    const result =
      executeRuntimeRecovery({
        plan,

        executedAt:
          NOW,

        handlers: {
          FREEZE_PROMOTION:
            () => ({
              frozen:
                true,
            }),

          RESTART_SCHEDULER:
            () => ({
              restarted:
                true,
            }),
        },
      });

    assert.equal(
      result.status,
      "RECOVERED",
    );

    assert.equal(
      result.summary.successCount,
      2,
    );
  },
);

test(
  "Missing handler causes partial failure",
  () => {
    const plan =
      createRuntimeRecoveryPlan({
        health: {
          status:
            "CRITICAL",

          issues: [
            {
              code:
                "RUNTIME_FAILED",
            },
          ],
        },

        now:
          NOW,
      });

    const result =
      executeRuntimeRecovery({
        plan,

        handlers: {},

        executedAt:
          NOW,
      });

    assert.equal(
      result.status,
      "PARTIAL_FAILURE",
    );

    assert.ok(
      result.summary.failureCount >
      0,
    );
  },
);

test(
  "Recovery controller stores history",
  () => {
    const controller =
      new RuntimeRecoveryControllerV2({
        handlers: {
          FREEZE_PROMOTION:
            () => true,

          RESTART_RUNTIME:
            () => true,
        },
      });

    const result =
      controller.recover({
        health: {
          status:
            "CRITICAL",

          issues: [
            {
              code:
                "RUNTIME_FAILED",
            },
          ],
        },

        now:
          NOW,
      });

    assert.equal(
      result.status,
      "RECOVERED",
    );

    assert.equal(
      controller
        .getHistory()
        .length,
      1,
    );

    assert.equal(
      controller.latest()
        .status,
      "RECOVERED",
    );

    controller.reset();

    assert.equal(
      controller
        .getHistory()
        .length,
      0,
    );
  },
);

test(
  "Recovery timestamp is validated",
  () => {
    assert.throws(
      () =>
        createRuntimeRecoveryPlan({
          now:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);