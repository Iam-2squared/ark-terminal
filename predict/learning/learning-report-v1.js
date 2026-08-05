export const LEARNING_REPORT_V1_VERSION = "learning-report-v1";

const DEFAULT_STORAGE_KEY = "ark.phase10.learningReports.v1";

function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function metric(source, ...keys) {
  for (const key of keys) {
    const value = finiteNumber(source?.[key]);
    if (value !== null) return value;
  }
  return null;
}

function topFeatures(weightOptimization, limit = 10) {
  const items = Array.isArray(weightOptimization?.featureImportance)
    ? weightOptimization.featureImportance
    : [];
  return items
    .filter((item) => item && typeof item.feature === "string")
    .slice()
    .sort((a, b) => (finiteNumber(b.score) ?? 0) - (finiteNumber(a.score) ?? 0))
    .slice(0, Math.max(1, Math.floor(limit)))
    .map((item) => ({
      feature: item.feature,
      score: finiteNumber(item.score) ?? 0,
      sampleSize: finiteNumber(item.sampleSize),
    }));
}

function compareModels(candidate = null, production = null) {
  if (!candidate || !production) {
    return {
      available: false,
      candidateVersion: candidate?.version ?? null,
      productionVersion: production?.version ?? null,
      deltas: null,
      recommendation: "INSUFFICIENT_MODEL_COMPARISON_DATA",
      promotionAllowed: false,
    };
  }

  const candidateMetrics = candidate.metrics ?? candidate;
  const productionMetrics = production.metrics ?? production;
  const keys = ["accuracy", "profitFactor", "sharpe", "maxDrawdown", "averageReturn"];
  const deltas = Object.fromEntries(keys.map((key) => {
    const candidateValue = finiteNumber(candidateMetrics[key]);
    const productionValue = finiteNumber(productionMetrics[key]);
    return [key, candidateValue === null || productionValue === null ? null : candidateValue - productionValue];
  }));

  const improvementSignals = [deltas.accuracy, deltas.profitFactor, deltas.sharpe, deltas.averageReturn]
    .filter((value) => value !== null);
  const drawdownImproved = deltas.maxDrawdown === null || deltas.maxDrawdown <= 0;
  const improved = improvementSignals.length > 0 && improvementSignals.every((value) => value >= 0) && drawdownImproved;

  return {
    available: true,
    candidateVersion: candidate.version ?? null,
    productionVersion: production.version ?? null,
    candidateMetrics,
    productionMetrics,
    deltas,
    recommendation: improved ? "REVIEW_CANDIDATE_FOR_HUMAN_APPROVAL" : "KEEP_PRODUCTION_AND_REVIEW_CANDIDATE",
    promotionAllowed: false,
  };
}

function buildRecommendations({ learningIntelligence, weightOptimization, calibration, drift, modelComparison }) {
  const recommendations = [];
  if ((learningIntelligence?.sample?.count ?? 0) < 30) recommendations.push("COLLECT_MORE_CLOSED_PAPER_TRADES");
  if (weightOptimization?.outOfSampleRequired) recommendations.push("RUN_OUT_OF_SAMPLE_VALIDATION");
  if ((calibration?.expectedCalibrationError ?? 0) > 0.1) recommendations.push("RECALIBRATE_CONFIDENCE");
  if (drift?.driftDetected) recommendations.push("REVIEW_DRIFT_BEFORE_NEXT_CANDIDATE");
  if (modelComparison?.available) recommendations.push(modelComparison.recommendation);
  if (recommendations.length === 0) recommendations.push("NO_CRITICAL_LEARNING_ACTION");
  return [...new Set(recommendations)];
}

export function generateLearningReport({
  generatedAt = new Date().toISOString(),
  periods = {},
  accuracy = {},
  performance = {},
  learningIntelligence = {},
  weightOptimization = {},
  confidenceCalibration = {},
  driftDetection = {},
  candidateModel = null,
  productionModel = null,
  modelVersion = null,
} = {}) {
  const modelComparison = compareModels(candidateModel, productionModel);
  const metrics = {
    accuracy: metric(accuracy, "accuracy", "predictionAccuracy"),
    tradeWinRate: metric(accuracy, "tradeWinRate", "winRate"),
    buyWinRate: metric(accuracy, "buyWinRate"),
    sellWinRate: metric(accuracy, "sellWinRate"),
    profitFactor: metric(performance, "profitFactor", "pf"),
    sharpe: metric(performance, "sharpe", "sharpeRatio"),
    maxDrawdown: metric(performance, "maxDrawdown", "maximumDrawdown"),
    averageReturn: metric(performance, "averageReturn", "averageReturnPercent"),
    pending: metric(accuracy, "pending"),
    noTrade: metric(accuracy, "noTrade", "noTradeCount"),
  };

  const report = {
    id: `learning-report-${generatedAt}`,
    version: LEARNING_REPORT_V1_VERSION,
    generatedAt,
    modelVersion: modelVersion ?? productionModel?.version ?? null,
    periods: {
      day7: periods.day7 ?? null,
      day30: periods.day30 ?? null,
      day90: periods.day90 ?? null,
    },
    metrics,
    sample: learningIntelligence?.sample ?? null,
    featureImportanceTop10: topFeatures(weightOptimization, 10),
    calibration: {
      sampleSize: finiteNumber(confidenceCalibration?.sampleSize),
      expectedCalibrationError: finiteNumber(confidenceCalibration?.expectedCalibrationError),
      brierScore: finiteNumber(confidenceCalibration?.brierScore),
      warnings: Array.isArray(confidenceCalibration?.warnings) ? confidenceCalibration.warnings : [],
    },
    drift: {
      detected: Boolean(driftDetection?.driftDetected),
      driftedFeatures: Array.isArray(driftDetection?.driftedFeatures) ? driftDetection.driftedFeatures : [],
      regime: driftDetection?.regime ?? null,
      action: driftDetection?.action ?? null,
    },
    candidateComparison: modelComparison,
    recommendations: [],
    safety: {
      productionUpdateAllowed: false,
      humanApprovalRequired: true,
      brokerExecutionAllowed: false,
    },
  };

  report.recommendations = buildRecommendations({
    learningIntelligence,
    weightOptimization,
    calibration: confidenceCalibration,
    drift: driftDetection,
    modelComparison,
  });
  return report;
}

function parseStored(raw) {
  try {
    const parsed = JSON.parse(raw ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export class LearningReportStoreV1 {
  constructor({ storage = globalThis?.localStorage ?? null, key = DEFAULT_STORAGE_KEY, maxReports = 100 } = {}) {
    this.storage = storage;
    this.key = key;
    this.maxReports = Math.max(1, Math.floor(Number(maxReports) || 100));
  }

  list() {
    if (!this.storage?.getItem) return [];
    return parseStored(this.storage.getItem(this.key));
  }

  save(report) {
    if (!report || typeof report !== "object") throw new TypeError("report must be an object");
    const existing = this.list().filter((item) => item?.id !== report.id);
    const next = [report, ...existing].slice(0, this.maxReports);
    if (this.storage?.setItem) this.storage.setItem(this.key, JSON.stringify(next));
    return report;
  }

  latest() {
    return this.list()[0] ?? null;
  }

  clear() {
    if (this.storage?.removeItem) this.storage.removeItem(this.key);
  }
}

export default generateLearningReport;
