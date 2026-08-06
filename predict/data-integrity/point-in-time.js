export const POINT_IN_TIME_VERSION = "point-in-time-v1";

function toMillis(value, name) {
  const time = new Date(value).getTime();
  if (!Number.isFinite(time)) throw new TypeError(`${name} must be a valid date`);
  return time;
}

export function selectPointInTimeRecords(records = [], asOf) {
  const asOfTime = toMillis(asOf, "asOf");
  const selected = new Map();
  const rejected = [];

  for (const [index, record] of records.entries()) {
    const availableAt = toMillis(record.availableAt ?? record.publishedAt ?? record.timestamp, "availableAt");
    const effectiveAt = toMillis(record.effectiveAt ?? record.date ?? record.timestamp, "effectiveAt");
    const key = String(record.key ?? record.id ?? `${record.symbol ?? "UNKNOWN"}:${record.field ?? index}`);

    if (availableAt > asOfTime) {
      rejected.push({ index, key, reason: "AVAILABLE_AFTER_AS_OF" });
      continue;
    }
    if (effectiveAt > asOfTime) {
      rejected.push({ index, key, reason: "EFFECTIVE_AFTER_AS_OF" });
      continue;
    }

    const previous = selected.get(key);
    if (!previous || availableAt > previous.__availableAt) {
      selected.set(key, { ...record, __availableAt: availableAt });
    }
  }

  const rows = [...selected.values()].map(({ __availableAt, ...record }) => record);
  return {
    version: POINT_IN_TIME_VERSION,
    asOf: new Date(asOfTime).toISOString(),
    rows,
    rejected,
    futureLeakDetected: rejected.length > 0,
    safety: {
      evaluationAllowed: rejected.length === 0,
      executionAllowed: false,
      brokerWriteAllowed: false,
      productionUpdateAllowed: false,
    },
  };
}

export function assertPointInTimeSafe(result) {
  if (!result || typeof result !== "object") throw new TypeError("result must be an object");
  if (result.futureLeakDetected || result.rejected?.length) {
    const error = new Error("POINT_IN_TIME_FUTURE_LEAK_DETECTED");
    error.code = "POINT_IN_TIME_FUTURE_LEAK_DETECTED";
    error.rejected = result.rejected ?? [];
    throw error;
  }
  return true;
}

export default selectPointInTimeRecords;
