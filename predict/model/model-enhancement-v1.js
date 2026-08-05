export const MODEL_ENHANCEMENT_V1 = "model-enhancement-v1";

function finite(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function normalizeWeights(models = []) {
  const positive = models.map((model) => Math.max(0, finite(model.weight, 1) ?? 1));
  const total = positive.reduce((sum, value) => sum + value, 0) || models.length || 1;
  return positive.map((value) => value / total);
}

function calibrationError(points = []) {
  const valid = points.filter((point) => finite(point.confidence) !== null && finite(point.outcome) !== null);
  if (!valid.length) return null;
  return valid.reduce((sum, point) => {
    const confidence = Math.min(1, Math.max(0, finite(point.confidence) > 1 ? finite(point.confidence) / 100 : finite(point.confidence)));
    return sum + Math.abs(confidence - finite(point.outcome));
  }, 0) / valid.length;
}

export function enhanceModelDecision({
  models = [],
  calibration = [],
  featureImportance = {},
  candidateMetrics = {},
  productionMetrics = {},
  minimumModels = 2,
} = {}) {
  const usable = models.filter((model) => finite(model.score) !== null && finite(model.confidence) !== null);
  const weights = normalizeWeights(usable);
  const ensembleScore = usable.length
    ? usable.reduce((sum, model, index) => sum + finite(model.score, 0) * weights[index], 0)
    : null;
  const ensembleConfidence = usable.length
    ? usable.reduce((sum, model, index) => sum + finite(model.confidence, 0) * weights[index], 0)
    : null;
  const disagreement = usable.length && ensembleScore !== null
    ? Math.sqrt(usable.reduce((sum, model) => sum + (finite(model.score, 0) - ensembleScore) ** 2, 0) / usable.length)
    : null;
  const uncertainty = disagreement === null ? null : Math.min(100, disagreement);
  const ece = calibrationError(calibration);
  const candidateDelta = {
    accuracy: (finite(candidateMetrics.accuracy, 0) ?? 0) - (finite(productionMetrics.accuracy, 0) ?? 0),
    profitFactor: (finite(candidateMetrics.profitFactor, 0) ?? 0) - (finite(productionMetrics.profitFactor, 0) ?? 0),
    expectedValue: (finite(candidateMetrics.expectedValue, 0) ?? 0) - (finite(productionMetrics.expectedValue, 0) ?? 0),
  };
  const rankedFeatures = Object.entries(featureImportance)
    .map(([feature, importance]) => ({ feature, importance: finite(importance, 0) }))
    .sort((a, b) => b.importance - a.importance);
  const blockers = [
    ...(usable.length < minimumModels ? ["INSUFFICIENT_MODELS"] : []),
    ...(ensembleScore === null ? ["NO_ENSEMBLE_SCORE"] : []),
  ];

  return {
    version: MODEL_ENHANCEMENT_V1,
    generatedAt: new Date().toISOString(),
    status: blockers.length ? "BLOCKED" : "READY",
    ensemble: {
      score: ensembleScore,
      confidence: ensembleConfidence,
      uncertainty,
      modelCount: usable.length,
      members: usable.map((model, index) => ({ ...model, normalizedWeight: weights[index] })),
    },
    calibration: {
      error: ece,
      status: ece === null ? "UNKNOWN" : ece <= 0.1 ? "GOOD" : ece <= 0.2 ? "WATCH" : "POOR",
    },
    featureImportance: rankedFeatures,
    comparison: {
      candidate: { ...candidateMetrics },
      production: { ...productionMetrics },
      delta: candidateDelta,
      reviewRecommended: Object.values(candidateDelta).every((value) => value >= 0),
    },
    blockers,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  };
}

export default enhanceModelDecision;
