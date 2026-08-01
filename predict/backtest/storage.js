import { STORAGE_KEYS } from "../config.js";

function finiteNumber(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function createId() {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }

  return `${Date.now()}-` + Math.random().toString(36).slice(2);
}

export function getPredictions() {
  try {
    const records = JSON.parse(localStorage.getItem(STORAGE_KEYS.predictions));

    return Array.isArray(records) ? records : [];
  } catch {
    return [];
  }
}

const DATABASE_NAME = "arkPredictionLab";
const DATABASE_VERSION = 1;
const RECORD_STORE = "predictions";

function openPredictionDatabase() {
  if (!globalThis.indexedDB) {
    return Promise.resolve(null);
  }

  return new Promise((resolve, reject) => {
    const request = globalThis.indexedDB.open(DATABASE_NAME, DATABASE_VERSION);

    request.onupgradeneeded = () => {
      const database = request.result;

      if (!database.objectStoreNames.contains(RECORD_STORE)) {
        const store = database.createObjectStore(RECORD_STORE, {
          keyPath: "id",
        });

        store.createIndex("createdAt", "createdAt");
        store.createIndex("status", "status");
        store.createIndex("symbol", "symbol");
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function persistRecords(records) {
  const database = await openPredictionDatabase();

  if (!database) return;

  await new Promise((resolve, reject) => {
    const transaction = database.transaction(RECORD_STORE, "readwrite");
    const store = transaction.objectStore(RECORD_STORE);

    records.forEach((record) => store.put(record));

    transaction.oncomplete = resolve;
    transaction.onerror = () => reject(transaction.error);
  });

  database.close();
}

async function indexedRecords() {
  const database = await openPredictionDatabase();

  if (!database) return [];

  const records = await new Promise((resolve, reject) => {
    const transaction = database.transaction(RECORD_STORE, "readonly");
    const request = transaction.objectStore(RECORD_STORE).getAll();

    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  });

  database.close();

  return records;
}

export function setPredictions(records) {
  const limited = records.slice(-2000);

  localStorage.setItem(STORAGE_KEYS.predictions, JSON.stringify(limited));
  void persistRecords(records).catch((error) =>
    console.warn("Prediction archive:", error),
  );

  return limited;
}

export async function getPredictionsAsync() {
  const localRecords = getPredictions();

  try {
    const archived = await indexedRecords();
    const merged = new Map();

    [...archived, ...localRecords].forEach((record) => {
      if (record?.id) merged.set(record.id, record);
    });

    const records = Array.from(merged.values()).sort(
      (first, second) =>
        new Date(first.createdAt) - new Date(second.createdAt),
    );

    if (archived.length < localRecords.length) {
      void persistRecords(localRecords);
    }

    return records;
  } catch (error) {
    console.warn("Prediction archive:", error);
    return localRecords;
  }
}

export function createPredictionRecord({
  symbol,
  companyName,
  industry,
  period,
  score,
  reasons,
  predictionPrice,
  analysisTime,
  factorScores,
  direction,
  expectedMoveRange,
  downsideRisk,
  confidence,
  expectedReturn,
  dataQuality,
  marketRegime,
  market,
  features,
  partition = null,
  costAssumptions = null,
  source = "live",
  modelVersion = null,
  evaluationPolicy = null,
  evaluationThreshold = null,
  decision = null,
  modelCalibration = null,
}) {
  return {
    id: createId(),
    createdAt: new Date().toISOString(),
    analysisTime: Number(analysisTime),
    symbol,
    companyName: companyName || symbol,
    industry: industry || "未分類",
    period: Number(period),
    score: Number(score),
    reasons: Array.isArray(reasons) ? reasons : [],
    predictionPrice: Number(predictionPrice),
    actualPrice: null,
    actualReturn: null,
    hit: null,
    outcome: "判定待ち",
    status: "pending",
    factorScores: factorScores || {},
    direction: direction || null,
    expectedMoveRange: expectedMoveRange || null,
    expectedReturn: finiteNumber(expectedReturn)
      ? Number(expectedReturn)
      : null,
    forecastError: null,
    absoluteForecastError: null,
    squaredForecastError: null,
    downsideRisk: downsideRisk ?? null,
    confidence: confidence || null,
    dataQuality: dataQuality || null,
    marketRegime: marketRegime || "未取得",
    market: market || "未取得",
    features: features || null,
    partition,
    costAssumptions,
    source,
    modelVersion,
    evaluationPolicy,
    modelCalibration,
    evaluationThreshold: finiteNumber(evaluationThreshold)
      ? Number(evaluationThreshold)
      : null,
    decision,
  };
}

export function savePrediction(record) {
  const records = getPredictions();

  records.push(record);

  setPredictions(records);

  return record;
}

export function clearBacktestRecords() {
  localStorage.removeItem(STORAGE_KEYS.predictions);

  void openPredictionDatabase().then((database) => {
    if (!database) return;

    const transaction = database.transaction(RECORD_STORE, "readwrite");

    transaction.objectStore(RECORD_STORE).clear();
    transaction.oncomplete = () => database.close();
  });
}

export function exportPredictions() {
  return JSON.stringify(getPredictions(), null, 2);
}

export async function exportPredictionsAsync() {
  return JSON.stringify(await getPredictionsAsync(), null, 2);
}

export const PredictionStorageInternals = {
  openPredictionDatabase,
  persistRecords,
};
