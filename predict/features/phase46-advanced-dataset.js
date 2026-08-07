import crypto from "node:crypto";

export const PHASE46_ADVANCED_SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function std(values) {
  if (values.length < 2) return 0;
  const avg = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + ((value - avg) ** 2), 0) / values.length);
}

function checksum(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

export function generateExtendedFeatures(records = []) {
  if (!Array.isArray(records)) throw new TypeError("records must be an array");
  const bySymbol = new Map();
  for (const row of records) {
    if (!row?.symbol || !row?.sessionDate) throw new TypeError("symbol and sessionDate are required");
    const rows = bySymbol.get(row.symbol) || [];
    rows.push(row);
    bySymbol.set(row.symbol, rows);
  }

  const output = [];
  for (const [symbol, rows] of bySymbol) {
    rows.sort((a, b) => String(a.sessionDate).localeCompare(String(b.sessionDate)));
    for (let index = 19; index < rows.length - 1; index += 1) {
      const window20 = rows.slice(index - 19, index + 1);
      const current = rows[index];
      const next = rows[index + 1];
      const currentClose = Number(current.close);
      const nextClose = Number(next.close);
      if (!Number.isFinite(currentClose) || !Number.isFinite(nextClose) || currentClose === 0) continue;

      const closes = window20.map((row) => Number(row.close));
      const volumes = window20.map((row) => Number(row.volume));
      const ranges = window20.map((row) => (Number(row.high) - Number(row.low)) / Number(row.close));
      const returns = closes.slice(1).map((value, i) => (value / closes[i]) - 1);
      const avgGain = mean(returns.map((value) => Math.max(value, 0)));
      const avgLoss = mean(returns.map((value) => Math.max(-value, 0)));
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      const rsi = avgLoss === 0 ? 100 : 100 - (100 / (1 + rs));
      const typicalPrice = window20.map((row) => (Number(row.high) + Number(row.low) + Number(row.close)) / 3);
      const volumeSum = volumes.reduce((sum, value) => sum + value, 0);
      const vwap = volumeSum === 0 ? currentClose : typicalPrice.reduce((sum, value, i) => sum + (value * volumes[i]), 0) / volumeSum;
      const sma20 = mean(closes);
      const sigma20 = std(closes);
      const featureValues = Object.freeze({
        rsi14Approx: rsi,
        atr20Approx: mean(ranges),
        vwap20: vwap,
        bollingerZ20: sigma20 === 0 ? 0 : (currentClose - sma20) / sigma20,
        volumeRatio20: mean(volumes) === 0 ? 0 : Number(current.volume) / mean(volumes),
        volatility20: std(returns),
      });
      const actualReturn = (nextClose / currentClose) - 1;

      output.push(Object.freeze({
        symbol,
        sessionDate: current.sessionDate,
        featureCutoff: current.sessionDate,
        labelAvailableAt: next.sessionDate,
        close: currentClose,
        label: actualReturn > 0 ? 1 : 0,
        actualReturn,
        features: featureValues,
        ...featureValues,
        futureDataUsed: false,
      }));
    }
  }
  return Object.freeze(output);
}

export function splitDatasetByTime(rows = [], { trainRatio = 0.6, validationRatio = 0.2 } = {}) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");
  if (trainRatio <= 0 || validationRatio <= 0 || trainRatio + validationRatio >= 1) {
    throw new RangeError("invalid split ratios");
  }
  const sorted = [...rows].sort((a, b) => String(a.sessionDate).localeCompare(String(b.sessionDate)));
  const trainEnd = Math.floor(sorted.length * trainRatio);
  const validationEnd = trainEnd + Math.floor(sorted.length * validationRatio);
  const train = sorted.slice(0, trainEnd);
  const validation = sorted.slice(trainEnd, validationEnd);
  const test = sorted.slice(validationEnd);

  const lastTrain = train.at(-1)?.sessionDate ?? null;
  const firstValidation = validation[0]?.sessionDate ?? null;
  const lastValidation = validation.at(-1)?.sessionDate ?? null;
  const firstTest = test[0]?.sessionDate ?? null;
  const temporalOrderValid = (!lastTrain || !firstValidation || lastTrain <= firstValidation)
    && (!lastValidation || !firstTest || lastValidation <= firstTest);

  return Object.freeze({
    status: temporalOrderValid ? "VALID" : "BLOCKED",
    train: Object.freeze(train),
    validation: Object.freeze(validation),
    test: Object.freeze(test),
    temporalOrderValid,
    safety: PHASE46_ADVANCED_SAFETY,
  });
}

export function buildDatasetLineage({ datasetVersion, sourceManifestChecksum, featureVersion = "phase46-advanced-v2", rows = [] } = {}) {
  if (!datasetVersion || !sourceManifestChecksum) throw new TypeError("datasetVersion and sourceManifestChecksum are required");
  const payload = {
    schemaVersion: 1,
    datasetVersion,
    sourceManifestChecksum,
    featureVersion,
    rowCount: rows.length,
    generatedAt: new Date().toISOString(),
  };
  return Object.freeze({ ...payload, lineageChecksum: checksum(payload), safety: PHASE46_ADVANCED_SAFETY });
}

export function auditAdvancedDataset({ rows = [], split = null, lineage = null } = {}) {
  const blockers = [];
  const keys = new Set();
  for (const row of rows) {
    const key = `${row.symbol}:${row.sessionDate}`;
    if (keys.has(key)) blockers.push("DUPLICATE_ROW");
    keys.add(key);
    if (row.futureDataUsed !== false) blockers.push("FUTURE_DATA_FLAG");
    if (row.featureCutoff && row.featureCutoff > row.sessionDate) blockers.push("FEATURE_CUTOFF_AFTER_SESSION");
    if (![0, 1].includes(Number(row.label))) blockers.push("LABEL_INVALID");
    if (!Number.isFinite(Number(row.actualReturn))) blockers.push("ACTUAL_RETURN_INVALID");
    if (!row.features || !Object.values(row.features).some((value) => Number.isFinite(Number(value)))) blockers.push("FEATURES_MISSING");
    if (row.labelAvailableAt && row.labelAvailableAt <= row.sessionDate) blockers.push("LABEL_AVAILABILITY_INVALID");
  }
  if (split && split.temporalOrderValid !== true) blockers.push("TEMPORAL_SPLIT_INVALID");
  if (!lineage?.lineageChecksum) blockers.push("LINEAGE_MISSING");
  return Object.freeze({
    status: blockers.length ? "BLOCKED" : "VALID",
    blockers: Object.freeze([...new Set(blockers)]),
    rowCount: rows.length,
    safety: PHASE46_ADVANCED_SAFETY,
  });
}
