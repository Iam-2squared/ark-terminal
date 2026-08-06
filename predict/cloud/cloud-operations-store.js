export const CLOUD_OPERATIONS_STORE_VERSION = "cloud-operations-store-v1";

const STATUS_KEY = "ark.cloud.operations.status.v1";
const QUEUE_KEY = "ark.cloud.operations.queue.v1";
const MAX_QUEUE_ITEMS = 500;

function parseJson(value, fallback) {
  try {
    const parsed = JSON.parse(String(value ?? ""));
    return parsed ?? fallback;
  }
  catch {
    return fallback;
  }
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function nowIso(now = () => new Date()) {
  return now().toISOString();
}

function safeStorage(storage = globalThis.localStorage) {
  return storage ?? null;
}

export function loadCloudOperationsStatus({ storage = safeStorage() } = {}) {
  const stored = parseJson(storage?.getItem?.(STATUS_KEY), {});
  return {
    version: CLOUD_OPERATIONS_STORE_VERSION,
    state: stored?.state ?? "DISABLED",
    configured: stored?.configured === true,
    authenticated: stored?.authenticated === true,
    storageConfigured: stored?.storageConfigured === true,
    syncing: stored?.syncing === true,
    online: stored?.online !== false,
    lastSyncAt: stored?.lastSyncAt ?? null,
    lastSuccessAt: stored?.lastSuccessAt ?? null,
    lastErrorAt: stored?.lastErrorAt ?? null,
    lastError: stored?.lastError ?? null,
    latencyMs: Number.isFinite(Number(stored?.latencyMs))
      ? Number(stored.latencyMs)
      : null,
    localCount: Number(stored?.localCount) || 0,
    cloudCount: Number(stored?.cloudCount) || 0,
    queueCount: Number(stored?.queueCount) || 0,
  };
}

export function saveCloudOperationsStatus(status = {}, {
  storage = safeStorage(),
  now = () => new Date(),
} = {}) {
  const current = loadCloudOperationsStatus({ storage });
  const queueCount = loadOfflineQueue({ storage }).length;
  const next = {
    ...current,
    ...status,
    version: CLOUD_OPERATIONS_STORE_VERSION,
    queueCount,
    updatedAt: nowIso(now),
  };
  storage?.setItem?.(STATUS_KEY, JSON.stringify(next));
  return clone(next);
}

export function loadOfflineQueue({ storage = safeStorage() } = {}) {
  const parsed = parseJson(storage?.getItem?.(QUEUE_KEY), []);
  return Array.isArray(parsed)
    ? parsed.filter((item) => item && item.id && item.kind && item.payload)
    : [];
}

export function enqueueOfflineOperation({
  kind,
  payload,
  id,
  now = () => new Date(),
} = {}, {
  storage = safeStorage(),
} = {}) {
  if (!kind || !payload || typeof payload !== "object") {
    throw new Error("OFFLINE_OPERATION_KIND_AND_PAYLOAD_REQUIRED");
  }

  const queue = loadOfflineQueue({ storage });
  const operationId = String(
    id ?? `${kind}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  ).slice(0, 180);
  const item = {
    id: operationId,
    kind: String(kind).slice(0, 80),
    payload: clone(payload),
    attempts: 0,
    createdAt: nowIso(now),
    updatedAt: nowIso(now),
    lastError: null,
  };

  const next = [
    ...queue.filter((entry) => entry.id !== operationId),
    item,
  ].slice(-MAX_QUEUE_ITEMS);

  storage?.setItem?.(QUEUE_KEY, JSON.stringify(next));
  saveCloudOperationsStatus({ queueCount: next.length }, { storage, now });
  return clone(item);
}

export function replaceOfflineQueue(queue = [], {
  storage = safeStorage(),
  now = () => new Date(),
} = {}) {
  const safeQueue = (Array.isArray(queue) ? queue : [])
    .filter((item) => item && item.id && item.kind && item.payload)
    .slice(-MAX_QUEUE_ITEMS);
  storage?.setItem?.(QUEUE_KEY, JSON.stringify(safeQueue));
  saveCloudOperationsStatus({ queueCount: safeQueue.length }, { storage, now });
  return clone(safeQueue);
}

export function clearOfflineQueue(options = {}) {
  return replaceOfflineQueue([], options);
}

export async function flushOfflineQueue({
  handlers = {},
  storage = safeStorage(),
  now = () => new Date(),
  onProgress,
} = {}) {
  const queue = loadOfflineQueue({ storage });
  const remaining = [];
  const completed = [];

  for (const item of queue) {
    const handler = handlers?.[item.kind];
    if (typeof handler !== "function") {
      remaining.push({
        ...item,
        attempts: Number(item.attempts) + 1,
        updatedAt: nowIso(now),
        lastError: "NO_QUEUE_HANDLER",
      });
      continue;
    }

    try {
      await handler(clone(item.payload), clone(item));
      completed.push(item.id);
      onProgress?.({ id: item.id, kind: item.kind, status: "completed" });
    }
    catch (error) {
      remaining.push({
        ...item,
        attempts: Number(item.attempts) + 1,
        updatedAt: nowIso(now),
        lastError: error?.code ?? error?.message ?? "QUEUE_RETRY_FAILED",
      });
      onProgress?.({
        id: item.id,
        kind: item.kind,
        status: "failed",
        error: error?.code ?? error?.message ?? "QUEUE_RETRY_FAILED",
      });
    }
  }

  replaceOfflineQueue(remaining, { storage, now });
  return {
    attempted: queue.length,
    completed: completed.length,
    remaining: remaining.length,
    completedIds: completed,
  };
}

export const CloudOperationsStoreInternals = Object.freeze({
  MAX_QUEUE_ITEMS,
  QUEUE_KEY,
  STATUS_KEY,
  clone,
  nowIso,
  parseJson,
});
