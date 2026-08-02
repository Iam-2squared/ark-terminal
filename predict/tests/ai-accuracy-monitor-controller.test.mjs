import assert from "node:assert/strict";
import test from "node:test";

import { AIAccuracyMonitorController } from "../analysis/ai-accuracy-monitor-controller.js";

function createEventTarget() {
  const listeners = new Map();

  return {
    addEventListener(name, handler) {
      const handlers = listeners.get(name) ?? [];

      handlers.push(handler);
      listeners.set(name, handlers);
    },

    removeEventListener(name, handler) {
      listeners.set(
        name,
        (listeners.get(name) ?? []).filter((item) => item !== handler),
      );
    },

    dispatch(name) {
      for (const handler of listeners.get(name) ?? []) {
        handler({ type: name });
      }
    },

    listenerCount(name) {
      return (listeners.get(name) ?? []).length;
    },
  };
}

test("Controller mounts, refreshes on events and removes listeners", () => {
  const eventTarget = createEventTarget();
  const root = { dataset: {}, innerHTML: "" };
  let providerCalls = 0;
  let renderCalls = 0;

  const controller = new AIAccuracyMonitorController({
    eventTarget,
    documentRef: {},
    recordProvider() {
      providerCalls += 1;
      return [{ id: "a" }];
    },
    reportBuilder(records) {
      return { status: "ready", count: records.length };
    },
    viewModelBuilder(report) {
      return { status: { className: "ready" }, count: report.count };
    },
    mount() {
      return { mounted: true, root };
    },
    renderer(viewModel, container) {
      renderCalls += 1;
      container.count = viewModel.count;
      return { rendered: true };
    },
  });

  const started = controller.start();

  assert.equal(started.started, true);
  assert.equal(providerCalls, 1);
  assert.equal(renderCalls, 1);
  assert.equal(eventTarget.listenerCount("ark:analysis-ready"), 1);
  assert.equal(eventTarget.listenerCount("storage"), 1);
  assert.equal(
    eventTarget.listenerCount("ark:prediction-outcomes-updated"),
    1,
  );

  eventTarget.dispatch("ark:analysis-ready");
  eventTarget.dispatch("storage");

  assert.equal(providerCalls, 3);
  assert.equal(renderCalls, 3);

  controller.stop();

  assert.equal(eventTarget.listenerCount("ark:analysis-ready"), 0);
  assert.equal(eventTarget.listenerCount("storage"), 0);
  assert.equal(
    eventTarget.listenerCount("ark:prediction-outcomes-updated"),
    0,
  );
});

test("Controller hydrates the monitor from the durable archive", async () => {
  const root = { dataset: {}, innerHTML: "" };
  const renderedCounts = [];
  const controller = new AIAccuracyMonitorController({
    eventTarget: createEventTarget(),
    documentRef: {},
    recordProvider: () => [{ id: "local" }],
    archiveProvider: async () => [{ id: "local" }, { id: "archive" }],
    reportBuilder: (records) => ({ count: records.length }),
    viewModelBuilder: (report) => report,
    mount: () => ({ mounted: true, root }),
    renderer(viewModel) {
      renderedCounts.push(viewModel.count);
      return { rendered: true };
    },
  });

  const started = controller.start();
  await started.hydration;

  assert.deepEqual(renderedCounts, [1, 2]);
});

test("Controller renders a safe error state when storage fails", () => {
  const root = { dataset: {}, innerHTML: "" };
  let receivedError = null;
  let renderedView = null;

  const controller = new AIAccuracyMonitorController({
    eventTarget: createEventTarget(),
    documentRef: {},
    recordProvider() {
      throw new Error("storage unavailable");
    },
    viewModelBuilder(report, options = {}) {
      receivedError = options.error ?? null;
      return {
        status: { className: "unavailable" },
        error: Boolean(options.error),
      };
    },
    mount() {
      return { mounted: true, root };
    },
    renderer(viewModel) {
      renderedView = viewModel;
      return { rendered: true };
    },
  });

  const result = controller.start();

  assert.equal(result.started, true);
  assert.equal(result.refresh.rendered, true);
  assert.match(receivedError.message, /storage unavailable/);
  assert.equal(renderedView.error, true);
});

test("Controller fails closed when the dashboard cannot be mounted", () => {
  const eventTarget = createEventTarget();
  const controller = new AIAccuracyMonitorController({
    eventTarget,
    documentRef: {},
    mount() {
      return {
        mounted: false,
        reason: "dashboard_unavailable",
        root: null,
      };
    },
  });

  const result = controller.start();

  assert.equal(result.started, false);
  assert.equal(result.reason, "dashboard_unavailable");
  assert.equal(eventTarget.listenerCount("ark:analysis-ready"), 0);
});
