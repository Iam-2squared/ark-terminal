import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";

import {
  OfflineSyncQueue,
} from "../cloud/offline-sync-queue.js";

import {
  buildSafeBackup,
  mergeRecordsByIdentity,
  validateSafeBackup,
} from "../cloud/safe-backup-repository.js";

import {
  saveCloudRecordOrQueue,
} from "../cloud/queued-cloud-writer.js";

import {
  AutomaticCloudSyncController,
} from "../cloud/automatic-cloud-sync.js";

function memoryStorage() {
  const map = new Map();
  return {
    getItem: (key) => map.has(key) ? map.get(key) : null,
    setItem: (key, value) => map.set(key, String(value)),
    removeItem: (key) => map.delete(key),
  };
}

function fixedClock(...timestamps) {
  let index = 0;
  return () => new Date(timestamps[Math.min(index++, timestamps.length - 1)]);
}

test("Part8B deduplicates queue items by collection and record id", () => {
  const storage = memoryStorage();
  const queue = new OfflineSyncQueue({
    storage,
    sender: async () => ({ saved: true }),
    now: fixedClock(
      "2026-08-06T00:00:00.000Z",
      "2026-08-06T00:01:00.000Z",
    ),
  });

  queue.enqueue({ collection: "predictions", id: "p1", data: { score: 50 } });
  queue.enqueue({ collection: "predictions", id: "p1", data: { score: 60 } });

  assert.equal(queue.count(), 1);
  assert.equal(queue.list()[0].data.score, 60);
});

test("Part8B keeps failed queue items and removes successful items", async () => {
  const storage = memoryStorage();
  const queue = new OfflineSyncQueue({
    storage,
    now: fixedClock(
      "2026-08-06T00:00:00.000Z",
      "2026-08-06T00:01:00.000Z",
      "2026-08-06T00:02:00.000Z",
      "2026-08-06T00:03:00.000Z",
    ),
    sender: async ({ id }) => {
      if (id === "fail") throw Object.assign(new Error("offline"), { code: "NETWORK_DOWN" });
      return { saved: true };
    },
  });

  queue.enqueue({ collection: "predictions", id: "ok", data: { value: 1 } });
  queue.enqueue({ collection: "predictions", id: "fail", data: { value: 2 } });

  const result = await queue.flush();
  assert.deepEqual(result, { sent: 1, failed: 1, remaining: 1 });
  assert.equal(queue.list()[0].id, "fail");
  assert.equal(queue.list()[0].attempts, 1);
  assert.equal(queue.list()[0].lastError, "NETWORK_DOWN");
});

test("Part8B rejects sensitive fields before storing queue data", () => {
  const queue = new OfflineSyncQueue({
    storage: memoryStorage(),
    sender: async () => ({ saved: true }),
  });

  assert.throws(
    () => queue.enqueue({
      collection: "predictions",
      id: "p1",
      data: { apiKey: "secret" },
    }),
    /OFFLINE_QUEUE_SENSITIVE_FIELD_REJECTED/,
  );
});

test("Queued cloud writer stores a safe fallback when cloud write fails", async () => {
  const queue = new OfflineSyncQueue({
    storage: memoryStorage(),
    sender: async () => ({ saved: true }),
  });

  const result = await saveCloudRecordOrQueue(
    { collection: "learning_reports", id: "r1", data: { executionAllowed: false } },
    {
      writer: async () => {
        throw Object.assign(new Error("down"), { code: "NETWORK_DOWN" });
      },
      queue,
    },
  );

  assert.equal(result.saved, false);
  assert.equal(result.queued, true);
  assert.equal(queue.count(), 1);
});

test("Part8D creates and validates a safe backup", () => {
  const backup = buildSafeBackup({
    predictions: [{ id: "p1", updatedAt: "2026-08-06T00:00:00Z" }],
    candidateModels: [{ id: "c1", status: "READY_FOR_REVIEW" }],
  });

  const validated = validateSafeBackup(backup);
  assert.equal(validated.counts.predictions, 1);
  assert.equal(validated.counts.candidate_models, 1);
  assert.equal(validated.safety.realAccountIncluded, false);
});

test("Part8D rejects credentials and real-account fields", () => {
  const unsafe = buildSafeBackup();
  unsafe.collections.predictions = [{ id: "p1", accountNumber: "123" }];

  assert.throws(
    () => validateSafeBackup(unsafe),
    /SAFE_BACKUP_SENSITIVE_FIELD_REJECTED/,
  );
});

test("Part8D merges records by identity and keeps the freshest record", () => {
  const merged = mergeRecordsByIdentity(
    [{ id: "p1", updatedAt: "2026-08-06T00:00:00Z", score: 50 }],
    [{ id: "p1", updatedAt: "2026-08-06T01:00:00Z", score: 70 }],
  );

  assert.equal(merged.length, 1);
  assert.equal(merged[0].score, 70);
});

test("Part8B automatic prediction sync queues records while cloud is not ready", async () => {
  const queued = [];
  const queue = {
    enqueue(record) {
      queued.push(record);
      return { queueId: `q-${queued.length}` };
    },
  };

  const controller = new AutomaticCloudSyncController({
    statusProvider: async () => ({
      configured: false,
      storageConfigured: false,
      authenticated: false,
    }),
    localProvider: async () => [],
    localWriter: () => {},
    cloudLoader: async () => ({ predictions: [] }),
    cloudBulkWriter: async () => ({}),
    predictionWriter: async () => ({ saved: true }),
    cloudRecordWriter: async () => ({ saved: true }),
    queue,
    queueFlusher: async () => ({ sent: 0, failed: 0, remaining: 0 }),
    eventTarget: null,
  });

  const result = await controller.mirrorPrediction({ id: "p1", score: 55 });
  assert.equal(result.queued, true);
  assert.equal(queued[0].collection, "predictions");
  assert.equal(queued[0].data.score, 55);
});

test("Part8A-C operations page includes status, queue, learning, and backup controls", async () => {
  const html = await fs.readFile(new URL("../operations.html", import.meta.url), "utf8");
  const script = await fs.readFile(new URL("../cloud/operations-page.js", import.meta.url), "utf8");

  for (const marker of [
    "Cloud Sync Status",
    "Offline Queue",
    "Learning Dashboard",
    "Safe Backup / Restore",
    "appliedToRuntime: false",
  ]) {
    assert.match(`${html}\n${script}`, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});

test("Part8 does not add a new API Function entrypoint", async () => {
  const files = await fs.readdir(new URL("../../api", import.meta.url));
  const functions = files.filter((name) => name.endsWith(".js"));
  assert.ok(functions.length <= 12);
});
