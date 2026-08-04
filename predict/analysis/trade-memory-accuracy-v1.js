import { auditAccuracy } from "./accuracy-audit-v3.js";

export const TRADE_MEMORY_ACCURACY_V1_VERSION =
  "trade-memory-accuracy-v1";

function finiteOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function normalizeAction(record = {}) {
  const action = String(
    record.action ??
    record.decision ??
    record.signal ??
    "NO_TRADE",
  )
    .trim()
    .toUpperCase();

  if (["BUY", "SELL"].includes(action)) {
    return action;
  }

  if (["APPROVE", "WAIT", "REJECT", "HOLD", "BLOCK", "NO_TRADE"].includes(action)) {
    return "NO_TRADE";
  }

  return "NO_TRADE";
}

function resolveStatus(record = {}, returnPercent = null) {
  const explicit = String(
    record.status ??
    record.outcome ??
    "",
  )
    .trim()
    .toUpperCase();

  if (["WIN", "LOSS", "FLAT", "PENDING", "CANCELLED"].includes(explicit)) {
    return explicit;
  }

  if (
    explicit === "OPEN" ||
    explicit === "PENDING" ||
    record.evaluation?.evaluatedAt == null
  ) {
    return "PENDING";
  }

  if (record.evaluation?.hit === true) {
    return "WIN";
  }

  if (record.evaluation?.hit === false) {
    return "LOSS";
  }

  if (returnPercent === null) {
    return "PENDING";
  }

  if (returnPercent > 0) return "WIN";
  if (returnPercent < 0) return "LOSS";
  return "FLAT";
}

export function tradeMemoryRecordToAccuracyRecord(record = {}) {
  const returnPercent = finiteOrNull(
    record.evaluation?.actualReturnPercent ??
    record.returnPercent ??
    record.actualReturnPercent,
  );

  return {
    symbol: String(record.symbol ?? "UNKNOWN")
      .trim()
      .toUpperCase(),
    action: normalizeAction(record),
    status: resolveStatus(record, returnPercent),
    returnPercent: returnPercent ?? 0,
    confidence:
      finiteOrNull(
        record.confidence ??
        record.predictionConfidence,
      ) ?? 0,
    modelVersion:
      record.modelVersion ??
      record.model ??
      null,
    sourceRecordId:
      record.id ?? null,
  };
}

export function auditTradeMemoryAccuracy(records = []) {
  const source = Array.isArray(records) ? records : [];
  const normalized = source.map(
    tradeMemoryRecordToAccuracyRecord,
  );

  return {
    version: TRADE_MEMORY_ACCURACY_V1_VERSION,
    sourceCount: source.length,
    normalizedCount: normalized.length,
    audit: auditAccuracy(normalized),
    records: normalized,
  };
}

export default auditTradeMemoryAccuracy;
