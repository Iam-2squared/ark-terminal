import { STORAGE_KEYS } from "../config.js";

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

export function setPredictions(records) {
  const limited = records.slice(-2000);

  localStorage.setItem(STORAGE_KEYS.predictions, JSON.stringify(limited));

  return limited;
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
  source = "live",
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
    source,
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
}

export function exportPredictions() {
  return JSON.stringify(getPredictions(), null, 2);
}
