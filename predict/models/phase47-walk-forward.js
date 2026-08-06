import crypto from "node:crypto";
import { MODEL_TYPES, PHASE47_SAFETY, evaluateModel, normalizeTrainingRows, trainModel } from "./phase47-real-training.js";

const mean = (values) => values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
const stableHash = (value) => crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");

function foldBoundaries(length, { minTrain = 60, validationSize = 20, step = 20 } = {}) {
  if (length < minTrain + validationSize) throw new RangeError("insufficient rows for walk-forward validation");
  const folds = [];
  for (let trainEnd = minTrain; trainEnd + validationSize <= length; trainEnd += step) {
    folds.push({ trainStart: 0, trainEnd, testStart: trainEnd, testEnd: trainEnd + validationSize });
  }
  if (!folds.length) throw new RangeError("no walk-forward folds generated");
  return folds;
}

export function runWalkForward({ rows, modelTypes = MODEL_TYPES, options = {}, costRate = 0.001 } = {}) {
  const normalized = normalizeTrainingRows(rows);
  const boundaries = foldBoundaries(normalized.length, options);
  const results = [];

  for (const modelType of modelTypes) {
    const folds = boundaries.map((boundary, index) => {
      const trainRows = normalized.slice(boundary.trainStart, boundary.trainEnd);
      const testRows = normalized.slice(boundary.testStart, boundary.testEnd);
      const model = trainModel({ rows: trainRows, modelType, options: options[modelType] ?? {} });
      const metrics = evaluateModel({ model, rows: testRows, costRate });
      return Object.freeze({
        fold: index + 1,
        modelType,
        trainStart: trainRows[0].sessionDate,
        trainEnd: trainRows.at(-1).sessionDate,
        testStart: testRows[0].sessionDate,
        testEnd: testRows.at(-1).sessionDate,
        trainCount: trainRows.length,
        testCount: testRows.length,
        metrics,
      });
    });

    const aggregate = Object.freeze({
      modelType,
      foldCount: folds.length,
      accuracy: mean(folds.map((fold) => fold.metrics.accuracy)),
      precision: mean(folds.map((fold) => fold.metrics.precision)),
      recall: mean(folds.map((fold) => fold.metrics.recall)),
      auc: mean(folds.map((fold) => fold.metrics.auc)),
      profitFactor: mean(folds.map((fold) => Math.min(10, fold.metrics.profitFactor))),
      sharpe: mean(folds.map((fold) => fold.metrics.sharpe)),
      maxDrawdown: Math.max(...folds.map((fold) => fold.metrics.maxDrawdown)),
      cagr: mean(folds.map((fold) => fold.metrics.cagr)),
      tradeCount: folds.reduce((sum, fold) => sum + fold.metrics.tradeCount, 0),
      brierScore: mean(folds.map((fold) => fold.metrics.brierScore)),
    });
    results.push(Object.freeze({ modelType, folds: Object.freeze(folds), aggregate }));
  }

  const ranked = [...results].sort((a, b) => {
    const scoreA = a.aggregate.auc * 0.35 + a.aggregate.accuracy * 0.2 + Math.min(a.aggregate.profitFactor, 3) / 3 * 0.25 + Math.max(-1, Math.min(1, a.aggregate.sharpe / 2)) * 0.1 - a.aggregate.maxDrawdown * 0.1;
    const scoreB = b.aggregate.auc * 0.35 + b.aggregate.accuracy * 0.2 + Math.min(b.aggregate.profitFactor, 3) / 3 * 0.25 + Math.max(-1, Math.min(1, b.aggregate.sharpe / 2)) * 0.1 - b.aggregate.maxDrawdown * 0.1;
    return scoreB - scoreA || a.modelType.localeCompare(b.modelType);
  });

  return Object.freeze({
    status: "READY_FOR_HUMAN_REVIEW",
    folds: boundaries.length,
    ranked: Object.freeze(ranked),
    selectedModelType: ranked[0].modelType,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    safety: PHASE47_SAFETY,
  });
}

export function buildPhase47RegistryCandidate({ rows, walkForwardResult, datasetLineage = {}, generatedAt = new Date().toISOString() } = {}) {
  const normalized = normalizeTrainingRows(rows);
  if (!walkForwardResult?.selectedModelType) throw new TypeError("walkForwardResult is required");
  const selected = walkForwardResult.ranked.find((item) => item.modelType === walkForwardResult.selectedModelType);
  const finalModel = trainModel({ rows: normalized, modelType: selected.modelType });
  const payload = {
    schemaVersion: 1,
    phase: 47,
    modelId: finalModel.modelId,
    modelType: selected.modelType,
    status: "CANDIDATE_REVIEW_ONLY",
    generatedAt: new Date(generatedAt).toISOString(),
    trainingPeriod: { start: normalized[0].sessionDate, end: normalized.at(-1).sessionDate },
    trainingRows: normalized.length,
    walkForward: selected.aggregate,
    datasetLineage,
    featureNames: finalModel.names,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    safety: PHASE47_SAFETY,
  };
  return Object.freeze({ ...payload, checksum: stableHash(payload) });
}

export function auditPhase47Candidate(candidate) {
  const blockers = [];
  if (!candidate || typeof candidate !== "object") blockers.push("CANDIDATE_REQUIRED");
  if (candidate?.automaticPromotionAllowed !== false) blockers.push("AUTOMATIC_PROMOTION_MUST_BE_FALSE");
  if (candidate?.productionUpdateAllowed !== false) blockers.push("PRODUCTION_UPDATE_MUST_BE_FALSE");
  if (candidate?.humanApprovalRequired !== true) blockers.push("HUMAN_APPROVAL_REQUIRED");
  if ((candidate?.walkForward?.foldCount ?? 0) < 2) blockers.push("INSUFFICIENT_WALK_FORWARD_FOLDS");
  if ((candidate?.walkForward?.tradeCount ?? 0) < 20) blockers.push("INSUFFICIENT_TRADE_COUNT");
  if (candidate?.checksum) {
    const { checksum, ...payload } = candidate;
    if (stableHash(payload) !== checksum) blockers.push("CHECKSUM_MISMATCH");
  } else blockers.push("CHECKSUM_REQUIRED");
  return Object.freeze({
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    blockers: Object.freeze(blockers),
    brokerWrites: 0,
    liveOrders: 0,
    safety: PHASE47_SAFETY,
  });
}
