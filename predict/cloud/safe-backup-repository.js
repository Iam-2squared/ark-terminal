export const SAFE_BACKUP_VERSION = "ark-safe-backup-v1";

export const SAFE_BACKUP_COLLECTIONS = Object.freeze([
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
  "setcookie",
  "brokercredentials",
  "accountnumber",
  "loginid",
  "rsspassword",
  "brokerpassword",
  "privatekey",
  "buyingpower",
  "marketvalue",
  "unrealizedpnl",
  "realizedpnl",
]);

function normalizedKey(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

export function assertSafeBackupValue(value, path = "data", seen = new WeakSet()) {
  if (value === null || value === undefined || typeof value !== "object") return;
  if (seen.has(value)) throw new Error("SAFE_BACKUP_CYCLIC_DATA_REJECTED");
  seen.add(value);

  if (Array.isArray(value)) {
    value.forEach((item, index) => assertSafeBackupValue(item, `${path}[${index}]`, seen));
    seen.delete(value);
    return;
  }

  for (const [key, nested] of Object.entries(value)) {
    if (FORBIDDEN_KEYS.has(normalizedKey(key))) {
      throw new Error(`SAFE_BACKUP_SENSITIVE_FIELD_REJECTED:${path}.${key}`);
    }
    assertSafeBackupValue(nested, `${path}.${key}`, seen);
  }

  seen.delete(value);
}

function cloneJson(value) {
  assertSafeBackupValue(value);
  return JSON.parse(JSON.stringify(value));
}

function safeRecords(records) {
  return (Array.isArray(records) ? records : [])
    .filter((record) => record && typeof record === "object" && !Array.isArray(record))
    .map(cloneJson);
}

export function buildSafeBackup({
  predictions = [],
  predictionOutcomes = [],
  learningReports = [],
  candidateModels = [],
  modelVersions = [],
  forwardTestResults = [],
  createdAt = new Date().toISOString(),
} = {}) {
  const collections = {
    predictions: safeRecords(predictions),
    prediction_outcomes: safeRecords(predictionOutcomes),
    learning_reports: safeRecords(learningReports),
    candidate_models: safeRecords(candidateModels),
    model_versions: safeRecords(modelVersions),
    forward_test_results: safeRecords(forwardTestResults),
  };

  return {
    version: SAFE_BACKUP_VERSION,
    createdAt,
    safety: {
      realAccountIncluded: false,
      credentialsIncluded: false,
      brokerWriteAllowed: false,
      productionUpdateAllowed: false,
    },
    collections,
    counts: Object.fromEntries(
      Object.entries(collections).map(([name, records]) => [name, records.length]),
    ),
  };
}

export function validateSafeBackup(backup) {
  if (!backup || typeof backup !== "object" || Array.isArray(backup)) {
    throw new Error("SAFE_BACKUP_OBJECT_REQUIRED");
  }

  if (backup.version !== SAFE_BACKUP_VERSION) {
    throw new Error("SAFE_BACKUP_VERSION_UNSUPPORTED");
  }

  if (
    backup?.safety?.realAccountIncluded !== false ||
    backup?.safety?.credentialsIncluded !== false ||
    backup?.safety?.brokerWriteAllowed !== false ||
    backup?.safety?.productionUpdateAllowed !== false
  ) {
    throw new Error("SAFE_BACKUP_SAFETY_CONTRACT_REQUIRED");
  }

  assertSafeBackupValue(backup);

  const collections = {};
  for (const name of SAFE_BACKUP_COLLECTIONS) {
    collections[name] = safeRecords(backup?.collections?.[name]);
  }

  return {
    version: SAFE_BACKUP_VERSION,
    createdAt: String(backup.createdAt ?? ""),
    safety: cloneJson(backup.safety),
    collections,
    counts: Object.fromEntries(
      Object.entries(collections).map(([name, records]) => [name, records.length]),
    ),
  };
}

export function mergeRecordsByIdentity(localRecords = [], importedRecords = []) {
  const map = new Map();

  const identity = (record, index) => String(
    record?.id ??
    record?.predictionId ??
    record?.proposalId ??
    record?.version ??
    `record-${index}`,
  );

  const freshness = (record) => Date.parse(
    record?.updatedAt ??
    record?.resolvedAt ??
    record?.completedAt ??
    record?.generatedAt ??
    record?.createdAt ??
    0,
  ) || 0;

  [...safeRecords(localRecords), ...safeRecords(importedRecords)]
    .forEach((record, index) => {
      const key = identity(record, index);
      const existing = map.get(key);
      if (!existing || freshness(record) >= freshness(existing)) {
        map.set(key, record);
      }
    });

  return [...map.values()];
}

export const SafeBackupInternals = Object.freeze({
  FORBIDDEN_KEYS,
  cloneJson,
  normalizedKey,
  safeRecords,
});

export default buildSafeBackup;
