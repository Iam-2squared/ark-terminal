import test from "node:test";
import assert from "node:assert/strict";

import {
  createPhase40BatchPlan,
  runPhase40BatchBacktest,
  buildPhase40ResumeCheckpoint,
} from "../backtest/phase40-batch-runner.js";

function task(symbol, period = 5, taskId = `${symbol}:${period}`) {
  return {
    taskId,
    symbol,
    period,
    candles: [{ time: 1, open: 1, high: 1, low: 1, close: 1, volume: 1 }],
  };
}

test("creates a resumable plan and skips completed tasks", () => {
  const plan = createPhase40BatchPlan({
    tasks: [task("7203.T"), task("6758.T")],
    options: { planId: "plan-1", concurrency: 4 },
    checkpoint: { completedTaskIds: ["7203.T:5"], failedTaskIds: [] },
  });
  assert.equal(plan.planId, "plan-1");
  assert.equal(plan.concurrency, 4);
  assert.equal(plan.pendingTasks.length, 1);
  assert.equal(plan.pendingTasks[0].symbol, "6758.T");
  assert.equal(plan.safety.brokerWriteAllowed, false);
});

test("isolates failed tasks while completing successful tasks", async () => {
  const result = await runPhase40BatchBacktest({
    tasks: [task("7203.T"), task("FAIL.T")],
    options: { concurrency: 2, updatedAt: "2026-08-06T00:00:00.000Z" },
    runner: async (input) => {
      if (input.symbol === "FAIL.T") throw new Error("synthetic failure");
      return { metrics: { profitFactor: 1.2 } };
    },
  });
  assert.equal(result.status, "COMPLETED_WITH_FAILURES");
  assert.equal(result.completed.length, 1);
  assert.equal(result.failed.length, 1);
  assert.match(result.failed[0].error, /synthetic failure/);
  assert.equal(result.brokerWrites, 0);
  assert.equal(result.liveOrders, 0);
});

test("resume checkpoint prevents rerunning completed tasks", async () => {
  const first = await runPhase40BatchBacktest({
    tasks: [task("7203.T"), task("6758.T")],
    options: { concurrency: 1 },
    runner: async (input) => ({ metrics: { symbol: input.symbol } }),
  });
  const checkpoint = buildPhase40ResumeCheckpoint(first);
  let calls = 0;
  const resumed = await runPhase40BatchBacktest({
    tasks: [task("7203.T"), task("6758.T"), task("9984.T")],
    checkpoint,
    runner: async () => {
      calls += 1;
      return { metrics: {} };
    },
  });
  assert.equal(calls, 1);
  assert.equal(resumed.completed.length, 3);
  assert.ok(resumed.checkpoint.completedTaskIds.includes("9984.T:5"));
});

test("failed tasks remain skipped unless retryFailed is enabled", () => {
  const tasks = [task("7203.T"), task("6758.T")];
  const checkpoint = { completedTaskIds: [], failedTaskIds: ["6758.T:5"] };
  const skipped = createPhase40BatchPlan({ tasks, checkpoint });
  const retried = createPhase40BatchPlan({ tasks, checkpoint, options: { retryFailed: true } });
  assert.equal(skipped.pendingTasks.length, 1);
  assert.equal(skipped.skippedFailed, 1);
  assert.equal(retried.pendingTasks.length, 2);
});

test("safety contract remains historical-only", async () => {
  const result = await runPhase40BatchBacktest({
    tasks: [task("7203.T")],
    runner: async () => ({ metrics: {} }),
  });
  assert.equal(result.safety.mode, "HISTORICAL_BACKTEST_ONLY");
  assert.equal(result.safety.liveTradingAllowed, false);
  assert.equal(result.safety.orderCreationAllowed, false);
  assert.equal(result.safety.orderTransmissionAllowed, false);
  assert.equal(result.safety.orderCancellationAllowed, false);
  assert.equal(result.safety.orderModificationAllowed, false);
  assert.equal(result.safety.excelOrderWriteAllowed, false);
  assert.equal(result.safety.orderTriggerWriteAllowed, false);
  assert.equal(result.safety.automaticPromotionAllowed, false);
  assert.equal(result.safety.productionUpdateAllowed, false);
});
