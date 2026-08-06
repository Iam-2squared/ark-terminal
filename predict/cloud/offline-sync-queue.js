export const OFFLINE_SYNC_QUEUE_VERSION = "offline-sync-queue-v1";
export const DEFAULT_OFFLINE_SYNC_QUEUE_KEY = "ark.offline-sync-queue.v1";

const ALLOWED_COLLECTIONS = new Set([
  "predictions",
  "prediction_outcomes",
  "learning_reports",
  "candidate_models",
  "model_versions",
  "forward_test_results",
]);

const FORBIDDEN_KEYS = new Set([
  "password",
  "passphrase",
  "secret",
  "clientsecret",
  "apikey",
  "accesstoken",
  "refreshtoken",
  "authorization",
  "cookie",
  "accountnumber",
  "loginid",
  "rsspassword",
  "brokerpassword",
  "privatekey",
]);

function normalizedKey(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

function assertSafeValue(value, seen = new WeakSet()) {
  if (value === null || value === undefined || typeof value !== "object") return;
  if (seen.has(value)) throw new Error("OFFLINE_QUEUE_CYCLIC_DATA_REJECTED");
  seen.add(value);

  if (Array.isArray(value)) {
    value.forEach((item) => assertSafeValue(item, seen));
    seen.delete(value);
    return;
  }

  for (const [key, nested] of Object.entries(value)) {
    if (FORBIDDEN_KEYS.has(normalizedKey(key))) {
      throw new Error("OFFLINE_QUEUE_SENSITIVE_FIELD_REJECTED");
    }
    assertSafeValue(nested, seen);
  }

  seen.delete(value);
}

function cloneJson(value) {
  assertSafeValue(value);
  return JSON.parse(JSON.stringify(value));
}

function safeId(value) {
  const id = String(value ?? "")
    .trim()
    .replace(/[^A-Za-z0-9._:-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^[-._:]+/, "")
    .slice(0, 160);

  if (!/^[A-Za-z0-9]/.test(id)) {
    throw new Error("OFFLINE_QUEUE_RECORD_ID_REQUIRED");
  }

  return id;
}

function loadQueue(storage, storageKey) {
  try {
    const raw = storage?.getItem?.(storageKey);
    const parsed = raw ? JSON.parse(raw) : null;
    return Array.isArray(parsed?.items) ? parsed.items : [];
  } catch {
    return [];
  }
}

function persistQueue(storage, storageKey, items) {
  storage?.setItem?.(
    storageKey,
    JSON.stringify({
      version: OFFLINE_SYNC_QUEUE_VERSION,
      updatedAt: new Date().toISOString(),
      items,
    }),
  );
}

export class OfflineSyncQueue {
  constructor({
    storage = globalThis.localStorage ?? null,
    storageKey = DEFAULT_OFFLINE_SYNC_QUEUE_KEY,
    sender,
    now = () => new Date(),
    maximumItems = 500,
  } = {}) {
    if (typeof sender !== "function") {
      throw new TypeError("Offline sync sender is required.");
    }

    this.storage = storage;
    this.storageKey = storageKey;
    this.sender = sender;
    this.now = now;
    this.maximumItems = Math.max(1, Number(maximumItems) || 500);
    this.items = loadQueue(storage, storageKey);
    this.flushing = null;
  }

  list() {
    return cloneJson(this.items);
  }

  count() {
    return this.items.length;
  }

  enqueue({ collection, id, data } = {}) {
    const safeCollection = String(collection ?? "").trim();
    if (!ALLOWED_COLLECTIONS.has(safeCollection)) {
      throw new Error("OFFLINE_QUEUE_COLLECTION_NOT_ALLOWED");
    }

    const safeRecordId = safeId(id);
    const safeData = cloneJson(data ?? {});
    const dedupeKey = `${safeCollection}:${safeRecordId}`;
    const queuedAt = this.now().toISOString();
    const existingIndex = this.items.findIndex((item) => item.dedupeKey === dedupeKey);
    const next = {
      version: OFFLINE_SYNC_QUEUE_VERSION,
      queueId: `${dedupeKey}:${queuedAt}`,
      dedupeKey,
      collection: safeCollection,
      id: safeRecordId,
      data: safeData,
      queuedAt,
      attempts: 0,
      lastAttemptAt: null,
      lastError: null,
    };

    if (existingIndex >= 0) {
      this.items.splice(existingIndex, 1, next);
    } else {
      this.items.push(next);
    }

    this.items = this.items.slice(-this.maximumItems);
    persistQueue(this.storage, this.storageKey, this.items);
    return cloneJson(next);
  }

  remove(queueId) {
    const before = this.items.length;
    this.items = this.items.filter((item) => item.queueId !== queueId);
    persistQueue(this.storage, this.storageKey, this.items);
    return before !== this.items.length;
  }

  clear() {
    const removed = this.items.length;
    this.items = [];
    persistQueue(this.storage, this.storageKey, this.items);
    return removed;
  }

  async flush() {
    if (this.flushing) return this.flushing;

    this.flushing = Promise.resolve().then(async () => {
      let sent = 0;
      let failed = 0;

      for (const item of [...this.items]) {
        const attemptAt = this.now().toISOString();
        try {
          await this.sender({
            collection: item.collection,
            id: item.id,
            data: item.data,
          });
          this.remove(item.queueId);
          sent += 1;
        } catch (error) {
          const current = this.items.find((entry) => entry.queueId === item.queueId);
          if (current) {
            current.attempts = Number(current.attempts || 0) + 1;
            current.lastAttemptAt = attemptAt;
            current.lastError = String(error?.code ?? error?.message ?? "SYNC_FAILED").slice(0, 160);
          }
          failed += 1;
          persistQueue(this.storage, this.storageKey, this.items);
        }
      }

      return {
        sent,
        failed,
        remaining: this.items.length,
      };
    }).finally(() => {
      this.flushing = null;
    });

    return this.flushing;
  }
}

export const OfflineSyncQueueInternals = Object.freeze({
  ALLOWED_COLLECTIONS,
  FORBIDDEN_KEYS,
  assertSafeValue,
  cloneJson,
  loadQueue,
  normalizedKey,
  persistQueue,
  safeId,
});

export default OfflineSyncQueue;
