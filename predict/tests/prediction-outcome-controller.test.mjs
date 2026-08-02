import assert from "node:assert/strict";
import test from "node:test";

import { PredictionOutcomeController } from "../analysis/prediction-outcome-controller.js";

function eventTarget() {
  const listeners = new Map();
  const events = [];

  return {
    events,
    addEventListener(name, handler) {
      listeners.set(name, [...(listeners.get(name) ?? []), handler]);
    },
    removeEventListener(name, handler) {
      listeners.set(
        name,
        (listeners.get(name) ?? []).filter((item) => item !== handler),
      );
    },
    dispatchEvent(event) {
      events.push(event);
    },
    count(name) {
      return (listeners.get(name) ?? []).length;
    },
  };
}

test("Controller persists changed outcomes and emits one refresh event", async () => {
  const target = eventTarget();
  let written = null;
  const controller = new PredictionOutcomeController({
    eventTarget: target,
    intervalMs: 0,
    throttleMs: 0,
    recordProvider: async () => [{ id: "pending" }],
    recordWriter(records) {
      written = records;
    },
    historyProvider: async () => ({ candles: [] }),
    refresher: async ({ records }) => ({
      status: "ready",
      changed: true,
      records: records.map((item) => ({ ...item, status: "resolved" })),
      executionAllowed: false,
    }),
  });

  const started = controller.start();
  const report = await started.refresh;

  assert.equal(report.changed, true);
  assert.equal(written[0].status, "resolved");
  assert.equal(target.events[0].type, "ark:prediction-outcomes-updated");
  assert.equal(target.count("focus"), 1);
  assert.equal(target.count("online"), 1);

  controller.stop();
  assert.equal(target.count("focus"), 0);
  assert.equal(target.count("online"), 0);
});

test("Controller coalesces concurrent refreshes and throttles wake checks", async () => {
  let now = 1000;
  let calls = 0;
  let release;
  const waiting = new Promise((resolve) => {
    release = resolve;
  });
  const controller = new PredictionOutcomeController({
    eventTarget: eventTarget(),
    intervalMs: 0,
    throttleMs: 100,
    now: () => now,
    recordProvider: async () => [],
    recordWriter() {},
    historyProvider: async () => ({ candles: [] }),
    async refresher() {
      calls += 1;
      await waiting;
      return { status: "ready", changed: false, records: [] };
    },
  });

  const first = controller.refresh({ force: true });
  const second = controller.refresh({ force: true });
  assert.equal(first, second);
  release();
  await first;
  assert.equal(calls, 1);

  const throttled = await controller.refresh();
  assert.equal(throttled.status, "throttled");
  now += 101;
  await controller.refresh();
  assert.equal(calls, 2);
});
