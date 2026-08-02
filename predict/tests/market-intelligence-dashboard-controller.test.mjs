import assert from "node:assert/strict";
import test from "node:test";

import {
  MARKET_INTELLIGENCE_DASHBOARD_EVENT,
  MarketIntelligenceDashboardController,
} from "../analysis/market-intelligence-dashboard-controller.js";

function createEventTarget() {
  const listeners = new Map();
  const events = [];

  return {
    events,
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
    dispatchEvent(event) {
      events.push(event);
      for (const handler of listeners.get(event.type) ?? []) handler(event);
      return true;
    },
    listenerCount(name) {
      return (listeners.get(name) ?? []).length;
    },
  };
}

function report() {
  return {
    status: "ready",
    featureStatus: "ready",
    featureConfidence: 82,
    featureCoverage: 90,
    selectedHorizon: 5,
    predictions: [
      { horizon: 5, score: 63, confidence: 82, status: "ready" },
    ],
    result: {
      features: {
        status: "ready",
        confidence: 82,
        coverage: 90,
        details: {},
      },
    },
    executionAllowed: false,
  };
}

function simpleViewModel({ report: runtime, state, phase, error }) {
  return {
    version: "test-v1",
    symbol: state?.symbol ?? "--",
    status: {
      key: phase,
      className: phase,
      label: phase,
    },
    errorMessage: error?.message ?? runtime?.error?.message ?? null,
    executionAllowed: false,
  };
}

test("Controller refreshes on analysis events and publishes a safe report", async () => {
  const eventTarget = createEventTarget();
  const root = { dataset: {}, innerHTML: "" };
  const phases = [];
  let adapterCalls = 0;
  let captureSetting = null;
  const controller = new MarketIntelligenceDashboardController({
    stateProvider: () => ({ symbol: "285A" }),
    inputBuilder({ settings }) {
      captureSetting = settings.marketIntelligence.captureHistoricalSnapshots;
      return {
        predictionHorizon: 5,
        marketIntelligence: { observations: [{}] },
      };
    },
    runtimeAdapter: {
      async analyze(input) {
        adapterCalls += 1;
        assert.ok(input.signal);
        return report();
      },
    },
    viewModelBuilder: simpleViewModel,
    mount: () => ({ mounted: true, root, reused: true }),
    renderer(view) {
      phases.push(view.status.key);
      return { rendered: true };
    },
    eventTarget,
    documentRef: {},
  });

  const started = controller.start();
  await started.refresh;

  assert.deepEqual(phases, ["loading", "ready"]);
  assert.equal(adapterCalls, 1);
  assert.equal(captureSetting, false);
  assert.equal(eventTarget.listenerCount("ark:analysis-ready"), 1);
  const published = eventTarget.events.find(
    (event) => event.type === MARKET_INTELLIGENCE_DASHBOARD_EVENT,
  );
  assert.equal(published.detail.status, "ready");
  assert.equal(published.detail.executionAllowed, false);

  eventTarget.dispatch("ark:analysis-ready");
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(adapterCalls, 2);

  controller.stop();
  assert.equal(eventTarget.listenerCount("ark:analysis-ready"), 0);
});

test("Controller isolates adapter failures from the normal analysis", async () => {
  const phases = [];
  const controller = new MarketIntelligenceDashboardController({
    stateProvider: () => ({ symbol: "FAIL" }),
    inputBuilder: () => ({ marketIntelligence: { observations: [{}] } }),
    runtimeAdapter: {
      async analyze() {
        throw new Error("provider failed");
      },
    },
    viewModelBuilder: simpleViewModel,
    mount: () => ({ mounted: true, root: {} }),
    renderer(view) {
      phases.push(view.status.key);
      return { rendered: true };
    },
    eventTarget: createEventTarget(),
    documentRef: {},
  });

  const result = await controller.start().refresh;

  assert.deepEqual(phases, ["loading", "error"]);
  assert.match(result.error.message, /provider failed/);
  assert.equal(result.viewModel.executionAllowed, false);
});

test("Controller renders idle without invoking Market Intelligence", async () => {
  let adapterCalls = 0;
  const phases = [];
  const controller = new MarketIntelligenceDashboardController({
    stateProvider: () => null,
    runtimeAdapter: {
      async analyze() {
        adapterCalls += 1;
      },
    },
    viewModelBuilder: simpleViewModel,
    mount: () => ({ mounted: true, root: {} }),
    renderer(view) {
      phases.push(view.status.key);
      return { rendered: true };
    },
    eventTarget: createEventTarget(),
    documentRef: {},
  });

  await controller.start().refresh;

  assert.deepEqual(phases, ["idle"]);
  assert.equal(adapterCalls, 0);
});

test("A newer refresh supersedes an older in-flight result", async () => {
  const pending = [];
  const phases = [];
  const controller = new MarketIntelligenceDashboardController({
    stateProvider: () => ({ symbol: "RACE" }),
    inputBuilder: () => ({ marketIntelligence: { observations: [{}] } }),
    runtimeAdapter: {
      analyze() {
        return new Promise((resolve) => pending.push(resolve));
      },
    },
    viewModelBuilder: simpleViewModel,
    mount: () => ({ mounted: true, root: {} }),
    renderer(view) {
      phases.push(view.status.key);
      return { rendered: true };
    },
    eventTarget: createEventTarget(),
    documentRef: {},
  });

  const first = controller.start().refresh;
  const second = controller.refresh();
  pending[1](report());
  await second;
  pending[0](report());
  const stale = await first;

  assert.equal(stale.reason, "stale_request");
  assert.deepEqual(phases, ["loading", "loading", "ready"]);
});

test("Controller fails closed when the dashboard cannot be mounted", () => {
  const eventTarget = createEventTarget();
  const controller = new MarketIntelligenceDashboardController({
    stateProvider: () => null,
    mount: () => ({ mounted: false, reason: "dashboard_unavailable" }),
    eventTarget,
    documentRef: {},
  });

  const result = controller.start();

  assert.equal(result.started, false);
  assert.equal(result.reason, "dashboard_unavailable");
  assert.equal(eventTarget.listenerCount("ark:analysis-ready"), 0);
});
