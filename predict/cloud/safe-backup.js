import {
  getPredictions,
  setPredictions,
} from "../backtest/storage.js";

import {
  DEFAULT_OFFLINE_SYNC_QUEUE_KEY,
} from "./offline-sync-queue.js";

export const SAFE_BACKUP_VERSION = "ark-safe-backup-v1";

const FORBIDDEN_KEYS = new Set([
  "password",
  "passphrase",
  "secret",
  "apikey",
  "accesstoken",
  "refreshtoken",
  "authorization",
  "cookie",
  "setcookie",
  "accountnumber",
  "loginid",
  "brokercredentials",
  "rsspassword",
  "brokerpassword",
  "privatekey",
]);

const ALLOWED_SECTIONS = Object.freeze([
  "predictions",
  "learningReports",
  "candidates",
  "forwardTests",
  "modelVersions",
  "offlineQueue",
]);

function normalizedKey(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

export function assertBackupSafe(value, path = "backup", seen = new WeakSet()) {
  if (value === null || value === undefined || typeof value !== "object") return;
  if (seen.has(value)) throw new Error("BACKUP_CYCLIC_DATA_REJECTED");
  seen.add(value);

  if (Array.isArray(value)) {
    value.forEach((item, index) => assertBackupSafe(item, `${path}[${index}]`, seen));
    seen.delete(value);
    return;
  }

  for (const [key, nested] of Object.entries(value)) {
    if (FORBIDDEN_KEYS.has(normalizedKey(key))) {
      throw new Error(`BACKUP_SENSITIVE_FIELD_REJECTED:${path}.${key}`);
    }
    assertBackupSafe(nested, `${path}.${key}`, seen);
  }

  seen.delete(value);
}

function parseStoredArray(storage, key) {
  try {
    const parsed = JSON.parse(storage?.getItem?.(key) ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  }
  catch {
    return [];
  }
}

function writeStoredArray(storage, key, value) {
  storage?.setItem?.(key, JSON.stringify(Array.isArray(value) ? value : []));
}

function loadOfflineQueue(storage) {
  try {
    const parsed = JSON.parse(storage?.getItem?.(DEFAULT_OFFLINE_SYNC_QUEUE_KEY) ?? "null");
    return Array.isArray(parsed?.items) ? parsed.items : [];
  }
  catch {
    return [];
  }
}

function writeOfflineQueue(storage, items) {
  storage?.setItem?.(
    DEFAULT_OFFLINE_SYNC_QUEUE_KEY,
    JSON.stringify({
      version: "offline-sync-queue-v1",
      updatedAt: new Date().toISOString(),
      items: Array.isArray(items) ? items : [],
    }),
  );
}

const STORAGE_MAP = Object.freeze({
  learningReports: "ark.learning.reports.v1",
  candidates: "ark.learning.candidates.v1",
  forwardTests: "ark.learning.forward-tests.v1",
  modelVersions: "ark.learning.model-versions.v1",
});

export function createSafeBackup({
  storage = globalThis.localStorage,
  now = () => new Date(),
} = {}) {
  const data = {
    predictions: getPredictions(),
    learningReports: parseStoredArray(storage, STORAGE_MAP.learningReports),
    candidates: parseStoredArray(storage, STORAGE_MAP.candidates),
    forwardTests: parseStoredArray(storage, STORAGE_MAP.forwardTests),
    modelVersions: parseStoredArray(storage, STORAGE_MAP.modelVersions),
    offlineQueue: loadOfflineQueue(storage),
  };

  assertBackupSafe(data);

  return {
    version: SAFE_BACKUP_VERSION,
    createdAt: now().toISOString(),
    source: "ARK_TERMINAL_LOCAL_ONLY",
    safety: {
      realAccountIncluded: false,
      brokerCredentialsIncluded: false,
      apiKeysIncluded: false,
      cookiesIncluded: false,
      ordersIncluded: false,
    },
    data: clone(data),
  };
}

export function serializeSafeBackup(options = {}) {
  return JSON.stringify(createSafeBackup(options), null, 2);
}

export function validateSafeBackup(input) {
  const parsed = typeof input === "string" ? JSON.parse(input) : clone(input);
  if (parsed?.version !== SAFE_BACKUP_VERSION) throw new Error("UNSUPPORTED_BACKUP_VERSION");
  if (!parsed?.data || typeof parsed.data !== "object") throw new Error("BACKUP_DATA_REQUIRED");

  for (const key of Object.keys(parsed.data)) {
    if (!ALLOWED_SECTIONS.includes(key)) throw new Error(`BACKUP_SECTION_NOT_ALLOWED:${key}`);
  }

  assertBackupSafe(parsed);
  return parsed;
}

export function importSafeBackup(input, {
  storage = globalThis.localStorage,
  mode = "replace",
} = {}) {
  const backup = validateSafeBackup(input);
  const merge = mode === "merge";

  const predictions = Array.isArray(backup.data.predictions) ? backup.data.predictions : [];
  const nextPredictions = merge
    ? [
        ...getPredictions().filter((item) => !predictions.some((candidate) => candidate?.id === item?.id)),
        ...predictions,
      ]
    : predictions;
  setPredictions(nextPredictions);

  for (const [section, key] of Object.entries(STORAGE_MAP)) {
    const incoming = Array.isArray(backup.data[section]) ? backup.data[section] : [];
    const current = merge ? parseStoredArray(storage, key) : [];
    const merged = merge
      ? [
          ...current.filter((item) => !incoming.some((candidate) => candidate?.id === item?.id)),
          ...incoming,
        ]
      : incoming;
    writeStoredArray(storage, key, merged);
  }

  const incomingQueue = Array.isArray(backup.data.offlineQueue) ? backup.data.offlineQueue : [];
  const currentQueue = merge ? loadOfflineQueue(storage) : [];
  const queueByKey = new Map();
  [...currentQueue, ...incomingQueue].forEach((item) => {
    const key = item?.dedupeKey ?? item?.queueId;
    if (key) queueByKey.set(key, item);
  });
  writeOfflineQueue(storage, [...queueByKey.values()]);

  return {
    imported: true,
    mode: merge ? "merge" : "replace",
    predictionCount: nextPredictions.length,
    learningReportCount: parseStoredArray(storage, STORAGE_MAP.learningReports).length,
    candidateCount: parseStoredArray(storage, STORAGE_MAP.candidates).length,
    forwardTestCount: parseStoredArray(storage, STORAGE_MAP.forwardTests).length,
    modelVersionCount: parseStoredArray(storage, STORAGE_MAP.modelVersions).length,
    queueCount: loadOfflineQueue(storage).length,
  };
}

export const SafeBackupInternals = Object.freeze({
  ALLOWED_SECTIONS,
  FORBIDDEN_KEYS,
  STORAGE_MAP,
  clone,
  loadOfflineQueue,
  normalizedKey,
  parseStoredArray,
  writeOfflineQueue,
});
