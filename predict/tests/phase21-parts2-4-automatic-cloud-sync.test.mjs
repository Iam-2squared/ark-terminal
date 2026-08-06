import test from "node:test";
import assert from "node:assert/strict";

import {
  AutomaticCloudSyncController,
  AutomaticCloudSyncInternals,
} from "../cloud/automatic-cloud-sync.js";

function createEventTarget() {
  const listeners = new Map();
  const dispatched = [];

  return {
    dispatched,
    addEventListener(name, listener) {
      const values = listeners.get(name) ?? [];
      values.push(listener);
      listeners.set(name, values);
    },
    removeEventListener(name, listener) {
      const values = listeners.get(name) ?? [];
      listeners.set(
        name,
        values.filter((value) => value !== listener),
      );
    },
    dispatchEvent(event) {
      dispatched.push(event);
      for (const listener of listeners.get(event.type) ?? []) {
        listener(event);
      }
      return true;
    },
  };
}

function readyStatus() {
  return {
    configured: true,
    storageConfigured: true,
    authenticated: true,
  };
}

function prediction(overrides = {}) {
  return {
    id: "prediction-1",
    createdAt: "2026-08-01T00:00:00.000Z",
    symbol: "7203.T",
    source: "live",
    status: "pending",
    actualPrice: null,
    hit: null,
    executionAllowed: false,
    ...overrides,
  };
}

test("Automatic cloud sync is a safe no-op when cloud is unavailable", async () => {
  let cloudLoads = 0;
  let localWrites = 0;

  const controller = new AutomaticCloudSyncController({
    statusProvider: async () => ({
      configured: false,
      storageConfigured: false,
      authenticated: false,
    }),
    localProvider: async () => [],
    localWriter: () => {
      localWrites += 1;
    },
    cloudLoader: async () => {
      cloudLoads += 1;
      return { predictions: [] };
    },
    cloudBulkWriter: async () => ({}),
    predictionWriter: async () => ({ saved: true }),
    cloudRecordWriter: async () => ({ saved: true }),
    eventTarget: createEventTarget(),
  });

  const started = controller.start();
  const result = await started.ready;

  assert.equal(result.restored, false);
  assert.equal(result.reason, "cloud_not_ready");
  assert.equal(cloudLoads, 0);
  assert.equal(localWrites, 0);

  const mirrored = await controller.mirrorPrediction(prediction());
  assert.deepEqual(mirrored, {
    saved: false,
    reason: "cloud_not_ready",
  });
});

test("Automatic cloud sync restores and converges prediction history", async () => {
  const local = [prediction()];
  const cloud = [
    prediction({
      status: "resolved",
      actualPrice: 110,
      hit: true,
      resolvedAt: "2026-08-05T00:00:00.000Z",
    }),
    prediction({
      id: "prediction-2",
      symbol: "6758.T",
    }),
  ];
  let written = null;
  let mirrored = null;

  const controller = new AutomaticCloudSyncController({
    statusProvider: async () => readyStatus(),
    localProvider: async () => local,
    localWriter: (records) => {
      written = records;
    },
    cloudLoader: async () => ({ predictions: cloud }),
    cloudBulkWriter: async (records) => {
      mirrored = records;
      return {
        savedPredictions: records.length,
        savedOutcomes: records.filter((record) => record.status === "resolved").length,
      };
    },
    predictionWriter: async () => ({ saved: true }),
    cloudRecordWriter: async () => ({ saved: true }),
    eventTarget: createEventTarget(),
  });

  const result = await controller.start().ready;

  assert.equal(result.restored, true);
  assert.equal(result.changed, true);
  assert.equal(result.mergedCount, 2);
  assert.equal(written.length, 2);
  assert.equal(
    written.find((record) => record.id === "prediction-1").status,
    "resolved",
  );
  assert.equal(mirrored.length, 2);
});

test("Automatic cloud sync mirrors only newly resolved records", async () => {
  let mirrored = null;

  const controller = new AutomaticCloudSyncController({
    statusProvider: async () => readyStatus(),
    localProvider: async () => [],
    localWriter: () => {},
    cloudLoader: async () => ({ predictions: [] }),
    cloudBulkWriter: async (records) => {
      mirrored = records;
      return {
        savedPredictions: records.length,
        savedOutcomes: records.length,
      };
    },
    predictionWriter: async () => ({ saved: true }),
    cloudRecordWriter: async () => ({ saved: true }),
    eventTarget: createEventTarget(),
  });

  await controller.refreshStatus();

  const result = await controller.mirrorOutcomeReport({
    changed: true,
    resolvedIds: ["prediction-2"],
    records: [
      prediction({
        id: "prediction-1",
        status: "resolved",
        actualPrice: 101,
      }),
      prediction({
        id: "prediction-2",
        status: "resolved",
        actualPrice: 102,
      }),
    ],
  });

  assert.equal(result.savedOutcomes, 1);
  assert.deepEqual(
    mirrored.map((record) => record.id),
    ["prediction-2"],
  );
});

test("Automatic cloud sync stores advisory learning reports only", async () => {
  const saved = [];

  const controller = new AutomaticCloudSyncController({
    statusProvider: async () => readyStatus(),
    localProvider: async () => [],
    localWriter: () => {},
    cloudLoader: async () => ({ predictions: [] }),
    cloudBulkWriter: async () => ({
      savedPredictions: 0,
      savedOutcomes: 0,
    }),
    predictionWriter: async () => ({ saved: true }),
    cloudRecordWriter: async (payload) => {
      saved.push(payload);
      return { saved: true };
    },
    eventTarget: createEventTarget(),
  });

  await controller.refreshStatus();

  const rejected = await controller.mirrorLearningReport({
    id: "unsafe-report",
    executionAllowed: true,
  });
  assert.equal(rejected.saved, false);
  assert.equal(rejected.reason, "invalid_learning_report");

  const accepted = await controller.mirrorLearningReport({
    id: "resolved feedback 2026/08/05",
    version: "resolved-feedback-v1",
    executionAllowed: false,
    audit: { resolvedCount: 5 },
  });

  assert.equal(accepted.saved, true);
  assert.equal(saved.length, 1);
  assert.equal(saved[0].collection, "learning_reports");
  assert.equal(saved[0].id, "resolved-feedback-2026-08-05");
  assert.equal(saved[0].data.executionAllowed, false);
});

test("Automatic cloud sync event handlers mirror outcomes and learning", async () => {
  const eventTarget = createEventTarget();
  const calls = {
    outcomes: 0,
    learning: 0,
  };

  const controller = new AutomaticCloudSyncController({
    statusProvider: async () => readyStatus(),
    localProvider: async () => [],
    localWriter: () => {},
    cloudLoader: async () => ({ predictions: [] }),
    cloudBulkWriter: async (records) => {
      if (records.length) calls.outcomes += 1;
      return {
        savedPredictions: records.length,
        savedOutcomes: records.length,
      };
    },
    predictionWriter: async () => ({ saved: true }),
    cloudRecordWriter: async () => {
      calls.learning += 1;
      return { saved: true };
    },
    eventTarget,
  });

  await controller.start().ready;

  eventTarget.dispatchEvent({
    type: "ark:prediction-outcomes-updated",
    detail: {
      changed: true,
      resolvedIds: ["prediction-1"],
      records: [prediction({ status: "resolved", actualPrice: 100 })],
    },
  });
  eventTarget.dispatchEvent({
    type: "ark:learning-feedback-ready",
    detail: {
      report: {
        id: "learning-1",
        executionAllowed: false,
      },
    },
  });

  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(calls.outcomes, 1);
  assert.equal(calls.learning, 1);

  controller.stop();
});

test("Automatic cloud sync normalizes learning report ids", () => {
  assert.equal(
    AutomaticCloudSyncInternals.normalizedRecordId("  report / 1  "),
    "report-1",
  );
});
