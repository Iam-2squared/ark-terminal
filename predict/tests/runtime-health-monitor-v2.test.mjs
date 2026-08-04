import test from "node:test";
import assert from "node:assert/strict";

import {
  RuntimeHealthMonitorV2,
  assertRuntimeHealthy,
  evaluateRuntimeHealth,
} from "../learning/runtime-health-monitor-v2.js";

test(
  "Runtime health is healthy with normal metrics",
  () => {
    const result =
      evaluateRuntimeHealth({
        input: {
          timestamp:
            "2026-08-04T00:00:00.000Z",

          runtimeStatus:
            "EXECUTED",

          schedulerStatus:
            "EXECUTED",

          auditValid:
            true,

          latencyMs:
            500,

          queueDepth:
            2,

          failureRate:
            1,

          memoryUsagePercent:
            40,

          cpuUsagePercent:
            35,
        },
      });

    assert.equal(
      result.status,
      "HEALTHY",
    );

    assert.equal(
      result.healthy,
      true,
    );

    assert.equal(
      result.summary.issueCount,
      0,
    );
  },
);

test(
  "Runtime health warns on high latency",
  () => {
    const result =
      evaluateRuntimeHealth({
        input: {
          timestamp:
            "2026-08-04T00:00:00.000Z",

          latencyMs:
            6_000,
        },
      });

    assert.equal(
      result.status,
      "WATCH",
    );

    assert.ok(
      result.issues.some(
        (
          item,
        ) =>
          item.code ===
          "LATENCY_WARNING",
      ),
    );
  },
);

test(
  "Runtime health becomes critical on runtime failure",
  () => {
    const result =
      evaluateRuntimeHealth({
        input: {
          timestamp:
            "2026-08-04T00:00:00.000Z",

          runtimeStatus:
            "FAILED",
        },
      });

    assert.equal(
      result.status,
      "CRITICAL",
    );

    assert.ok(
      result.issues.some(
        (
          item,
        ) =>
          item.code ===
          "RUNTIME_FAILED",
      ),
    );
  },
);

test(
  "Runtime health detects invalid audit",
  () => {
    const result =
      evaluateRuntimeHealth({
        input: {
          timestamp:
            "2026-08-04T00:00:00.000Z",

          auditValid:
            false,
        },
      });

    assert.equal(
      result.status,
      "CRITICAL",
    );

    assert.ok(
      result.issues.some(
        (
          item,
        ) =>
          item.code ===
          "AUDIT_INVALID",
      ),
    );
  },
);

test(
  "Runtime health detects failure streak",
  () => {
    const result =
      evaluateRuntimeHealth({
        input: {
          timestamp:
            "2026-08-04T00:00:00.000Z",

          consecutiveFailures:
            3,
        },
      });

    assert.equal(
      result.status,
      "CRITICAL",
    );

    assert.ok(
      result.issues.some(
        (
          item,
        ) =>
          item.code ===
          "CONSECUTIVE_FAILURE_LIMIT",
      ),
    );
  },
);

test(
  "Runtime health assertion throws on critical state",
  () => {
    const result =
      evaluateRuntimeHealth({
        input: {
          timestamp:
            "2026-08-04T00:00:00.000Z",

          rollbackRequired:
            true,
        },
      });

    assert.throws(
      () =>
        assertRuntimeHealthy(
          result,
        ),

      (
        error,
      ) =>
        error.code ===
        "RUNTIME_HEALTH_CRITICAL",
    );
  },
);

test(
  "Runtime health class stores history",
  () => {
    const monitor =
      new RuntimeHealthMonitorV2();

    monitor.evaluate({
      timestamp:
        "2026-08-04T00:00:00.000Z",

      latencyMs:
        100,
    });

    assert.equal(
      monitor
        .getHistory()
        .length,
      1,
    );

    assert.equal(
      monitor.latest()
        .status,
      "HEALTHY",
    );

    monitor.reset();

    assert.equal(
      monitor
        .getHistory()
        .length,
      0,
    );
  },
);

test(
  "Runtime health validates timestamp",
  () => {
    assert.throws(
      () =>
        evaluateRuntimeHealth({
          input: {
            timestamp:
              "invalid-date",
          },
        }),

      /timestamp is invalid/,
    );
  },
);