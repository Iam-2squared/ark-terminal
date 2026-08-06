import {
  getCloudSyncStatus,
  listCloudRecords,
  saveCloudRecord,
  saveCloudRecords,
} from "./cloud-sync-client.js";

const PREDICTION_COLLECTION = "predictions";
const OUTCOME_COLLECTION = "prediction_outcomes";
const MAX_SYNC_RECORDS = 1_000;
const BATCH_SIZE = 50;

function jsonClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function isLivePrediction(record) {
  return Boolean(
    record?.id &&
    (!record.source || record.source === "live"),
  );
}

function isResolved(record) {
  return Boolean(
    record?.id &&
    (
      record.status === "resolved" ||
      record.hit === true ||
      record.hit === false ||
      Number.isFinite(Number(record.actualPrice))
    )
  );
}

function predictionData(record) {
  return jsonClone(record);
}

function outcomeData(record) {
  return {
    id: record.id,
    symbol: record.symbol,
    period: record.period,
    status: record.status,
    outcome: record.outcome,
    actualPrice: record.actualPrice,
    actualReturn: record.actualReturn,
    hit: record.hit,
    forecastError: record.forecastError,
    absoluteForecastError: record.absoluteForecastError,
    squaredForecastError: record.squaredForecastError,
    resolvedAt:
      record.resolvedAt ??
      record.updatedAt ??
      new Date().toISOString(),
  };
}

function unwrapRecords(payload) {
  return (Array.isArray(payload?.records)
    ? payload.records
    : [])
    .map((record) => record?.data)
    .filter(Boolean);
}

function chunks(values, size = BATCH_SIZE) {
  const result = [];

  for (let index = 0; index < values.length; index += size) {
    result.push(values.slice(index, index + size));
  }

  return result;
}

export function selectCloudPredictions(
  records = [],
  maximumRecords = MAX_SYNC_RECORDS,
) {
  return (Array.isArray(records) ? records : [])
    .filter(isLivePrediction)
    .sort((first, second) =>
      String(first.createdAt ?? "")
        .localeCompare(String(second.createdAt ?? "")),
    )
    .slice(-Math.max(1, Math.floor(Number(maximumRecords) || MAX_SYNC_RECORDS)));
}

export async function savePredictionToCloud(
  record,
  options = {},
) {
  if (!isLivePrediction(record)) {
    return {
      saved: false,
      reason: "not_cloud_eligible",
    };
  }

  await saveCloudRecord({
    collection: PREDICTION_COLLECTION,
    id: record.id,
    data: predictionData(record),
    ...options,
  });

  if (isResolved(record)) {
    await saveCloudRecord({
      collection: OUTCOME_COLLECTION,
      id: record.id,
      data: outcomeData(record),
      ...options,
    });
  }

  return {
    saved: true,
    id: record.id,
    outcomeSaved: isResolved(record),
  };
}

export async function mirrorPredictionToCloud(
  record,
  {
    statusProvider = getCloudSyncStatus,
    ...options
  } = {},
) {
  const status = await statusProvider(options);

  if (!status?.authenticated || !status?.storageConfigured) {
    return {
      saved: false,
      reason: status?.configured
        ? "not_authenticated"
        : "cloud_not_configured",
    };
  }

  return savePredictionToCloud(
    record,
    options,
  );
}

export async function syncPredictionRecordsToCloud(
  records = [],
  options = {},
) {
  const selected = selectCloudPredictions(records);
  const outcomes = selected.filter(isResolved);
  let savedPredictions = 0;
  let savedOutcomes = 0;

  for (const batch of chunks(selected)) {
    await saveCloudRecords({
      collection: PREDICTION_COLLECTION,
      records: batch.map((record) => ({
        id: record.id,
        data: predictionData(record),
      })),
      ...options,
    });

    savedPredictions += batch.length;
  }

  for (const batch of chunks(outcomes)) {
    await saveCloudRecords({
      collection: OUTCOME_COLLECTION,
      records: batch.map((record) => ({
        id: record.id,
        data: outcomeData(record),
      })),
      ...options,
    });

    savedOutcomes += batch.length;
  }

  return {
    savedPredictions,
    savedOutcomes,
  };
}

export function applyCloudOutcomes(
  predictions = [],
  outcomes = [],
) {
  const outcomeMap = new Map(
    (Array.isArray(outcomes) ? outcomes : [])
      .filter((outcome) => outcome?.id)
      .map((outcome) => [outcome.id, outcome]),
  );

  return (Array.isArray(predictions) ? predictions : [])
    .map((prediction) => {
      const outcome = outcomeMap.get(prediction?.id);

      return outcome
        ? {
            ...prediction,
            ...outcome,
            id: prediction.id,
          }
        : prediction;
    });
}

export function mergePredictionRecords(
  localRecords = [],
  cloudRecords = [],
) {
  const merged = new Map();

  for (const record of [
    ...(Array.isArray(cloudRecords) ? cloudRecords : []),
    ...(Array.isArray(localRecords) ? localRecords : []),
  ]) {
    if (!record?.id) continue;

    const existing = merged.get(record.id);

    if (!existing) {
      merged.set(record.id, record);
      continue;
    }

    const existingTime = Date.parse(
      existing.updatedAt ??
      existing.resolvedAt ??
      existing.createdAt ??
      0,
    );
    const incomingTime = Date.parse(
      record.updatedAt ??
      record.resolvedAt ??
      record.createdAt ??
      0,
    );

    if (
      !Number.isFinite(existingTime) ||
      !Number.isFinite(incomingTime) ||
      incomingTime >= existingTime
    ) {
      merged.set(record.id, {
        ...existing,
        ...record,
      });
    }
  }

  return Array.from(merged.values())
    .sort((first, second) =>
      String(first.createdAt ?? "")
        .localeCompare(String(second.createdAt ?? "")),
    );
}

export async function loadPredictionStateFromCloud(
  {
    limit = MAX_SYNC_RECORDS,
    ...options
  } = {},
) {
  const [predictionsPayload, outcomesPayload] = await Promise.all([
    listCloudRecords({
      collection: PREDICTION_COLLECTION,
      limit,
      ...options,
    }),
    listCloudRecords({
      collection: OUTCOME_COLLECTION,
      limit,
      ...options,
    }),
  ]);

  const predictions = unwrapRecords(predictionsPayload);
  const outcomes = unwrapRecords(outcomesPayload);

  return {
    predictions: applyCloudOutcomes(
      predictions,
      outcomes,
    ),
    outcomes,
  };
}

export const PredictionCloudRepositoryInternals = {
  BATCH_SIZE,
  MAX_SYNC_RECORDS,
  OUTCOME_COLLECTION,
  PREDICTION_COLLECTION,
  chunks,
  isLivePrediction,
  isResolved,
  outcomeData,
  predictionData,
  unwrapRecords,
};
