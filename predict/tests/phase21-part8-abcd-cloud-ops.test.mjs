import test from "node:test";
import assert from "node:assert/strict";

import {
  loadCloudOperationsStatus,
  saveCloudOperationsStatus,
} from "../cloud/cloud-operations-store.js";

import {
  OfflineSyncQueue,
} from "../cloud/offline-sync-queue.js";

import {
  assertBackupSafe,
  createSafeBackup,
  importSafeBackup,
  validateSafeBackup,
} from "../cloud/safe-backup.js";

function memoryStorage() {
  const map = new Map();
  return {
    getItem: (key) => map.has(key) ? map.get(key) : null,
    setItem: (key, value) => map.set(key, String(value)),
    removeItem: (key) => map.delete(key),
    dump: () => Object.fromEntries(map),
  };
}

function responseRecord(id = "prediction-1") {
  return {
    collection: "predictions",
    id,
    data: {
      id,
      symbol: "7203.T",
      status: "OPEN",
      executionAllowed: false,
    },
  };
}

test("Part8A persists cloud status with last sync and latency", () => {
  const storage = memoryStorage();
  saveCloudOperationsStatus({
    state: "CONNECTED",
    configured: true,
    authenticated: true,
    storageConfigured: true,
    lastSyncAt: "2026-08-06T03:00:00.000Z",
    lastSuccessAt: "2026-08-06T03:00:00.000Z",
    latencyMs: 123,
  }, { storage, now: () => new Date("2026-08-06T03:00:01.000Z") });

  const status = loadCloudOperationsStatus({ storage });
  assert.equal(status.authenticated, true);
  assert.equal(status.storageConfigured, true);
  assert.equal(status.latencyMs, 123);
  assert.equal(status.lastSuccessAt, "2026-08-06T03:00:00.000Z");
});

test("Part8B queues cloud writes and retries them safely", async () => {
  const storage = memoryStorage();
  const sent = [];
  const queue = new OfflineSyncQueue({
    storage,
    sender: async (payload) => {
      sent.push(payload);
      return { saved: true };
    },
    now: () => new Date("2026-08-06T03:10:00.000Z"),
  });

  queue.enqueue(responseRecord());
  assert.equal(queue.count(), 1);

  const result = await queue.flush();
  assert.equal(result.sent, 1);
  assert.equal(result.failed, 0);
  assert.equal(result.remaining, 0);
  assert.equal(sent[0].collection, "predictions");
});

test("Part8B deduplicates queue items by collection and record id", () => {
  const storage = memoryStorage();
  const queue = new OfflineSyncQueue({ storage, sender: async () => ({ saved: true }) });
  queue.enqueue(responseRecord("same-id"));
  queue.enqueue({
    ...responseRecord("same-id"),
    data: { ...responseRecord("same-id").data, status: "RESOLVED" },
  });
  assert.equal(queue.count(), 1);
  assert.equal(queue.list()[0].data.status, "RESOLVED");
});

test("Part8D rejects sensitive fields during export and import", () => {
  assert.throws(
    () => assertBackupSafe({ nested: { apiKey: "secret-value" } }),
    /BACKUP_SENSITIVE_FIELD_REJECTED/,
  );

  assert.throws(
    () => validateSafeBackup({
      version: "ark-safe-backup-v1",
      data: {
        predictions: [],
        accountNumber: "123456",
      },
    }),
    /BACKUP_SECTION_NOT_ALLOWED|BACKUP_SENSITIVE_FIELD_REJECTED/,
  );
});

test("Part8D creates a local-only backup with explicit safety flags", () => {
  const storage = memoryStorage();
  const backup = createSafeBackup({
    storage,
    now: () => new Date("2026-08-06T03:20:00.000Z"),
  });
  assert.equal(backup.source, "ARK_TERMINAL_LOCAL_ONLY");
  assert.equal(backup.safety.realAccountIncluded, false);
  assert.equal(backup.safety.apiKeysIncluded, false);
  assert.deepEqual(backup.data.offlineQueue, []);
});

test("Part8D merges backup arrays by id and queue items by dedupe key", () => {
  const storage = memoryStorage();
  storage.setItem("ark.learning.candidates.v1", JSON.stringify([
    { id: "candidate-a", status: "CANDIDATE" },
  ]));
  storage.setItem("ark.offline-sync-queue.v1", JSON.stringify({
    version: "offline-sync-queue-v1",
    items: [
      {
        queueId: "old",
        dedupeKey: "predictions:p1",
        collection: "predictions",
        id: "p1",
        data: { id: "p1", status: "OPEN" },
      },
    ],
  }));

  const result = importSafeBackup({
    version: "ark-safe-backup-v1",
    createdAt: "2026-08-06T03:30:00.000Z",
    source: "ARK_TERMINAL_LOCAL_ONLY",
    safety: {
      realAccountIncluded: false,
      brokerCredentialsIncluded: false,
      apiKeysIncluded: false,
      cookiesIncluded: false,
      ordersIncluded: false,
    },
    data: {
      predictions: [],
      learningReports: [],
      candidates: [
        { id: "candidate-a", status: "READY_FOR_REVIEW" },
        { id: "candidate-b", status: "CANDIDATE" },
      ],
      forwardTests: [],
      modelVersions: [],
      offlineQueue: [
        {
          queueId: "new",
          dedupeKey: "predictions:p1",
          collection: "predictions",
          id: "p1",
          data: { id: "p1", status: "RESOLVED" },
        },
      ],
    },
  }, { storage, mode: "merge" });

  assert.equal(result.candidateCount, 2);
  assert.equal(result.queueCount, 1);

  const candidates = JSON.parse(storage.getItem("ark.learning.candidates.v1"));
  assert.equal(candidates.find((item) => item.id === "candidate-a").status, "READY_FOR_REVIEW");

  const queue = JSON.parse(storage.getItem("ark.offline-sync-queue.v1"));
  assert.equal(queue.items[0].data.status, "RESOLVED");
});
