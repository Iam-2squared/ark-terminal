export const PREDICTION_LAB_FINAL_V1 = "prediction-lab-final-v1";

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function metric(source, ...keys) {
  for (const key of keys) {
    const value = finite(source?.[key]);
    if (value !== null) return value;
  }
  return null;
}

export function createPredictionLabFinalViewModel({
  analysis = {},
  baseline = null,
  candidate = null,
  loading = false,
  error = null,
} = {}) {
  const productionMetrics = baseline?.metrics ?? baseline ?? null;
  const candidateMetrics = candidate?.metrics ?? candidate ?? null;

  return {
    version: PREDICTION_LAB_FINAL_V1,
    state: error ? "error" : loading ? "loading" : "ready",
    message: error
      ? String(error?.message ?? error)
      : loading
        ? "AI分析を実行しています。"
        : null,
    summary: {
      score: metric(analysis, "aiScore", "score", "totalScore"),
      confidence: metric(analysis, "confidence", "confidenceScore"),
      risk: analysis.risk ?? analysis.riskLabel ?? "不明",
      direction: analysis.direction ?? analysis.action ?? "NO_TRADE",
    },
    production: productionMetrics
      ? {
          accuracy: metric(productionMetrics, "accuracy", "predictionAccuracy"),
          profitFactor: metric(productionMetrics, "profitFactor", "pf"),
          sharpe: metric(productionMetrics, "sharpe", "sharpeRatio"),
          maxDrawdown: metric(productionMetrics, "maxDrawdown", "maximumDrawdown"),
          sampleSize: metric(productionMetrics, "sampleSize", "count", "trades"),
        }
      : null,
    candidate: candidateMetrics
      ? {
          accuracy: metric(candidateMetrics, "accuracy", "predictionAccuracy"),
          profitFactor: metric(candidateMetrics, "profitFactor", "pf"),
          sharpe: metric(candidateMetrics, "sharpe", "sharpeRatio"),
          maxDrawdown: metric(candidateMetrics, "maxDrawdown", "maximumDrawdown"),
          sampleSize: metric(candidateMetrics, "sampleSize", "count", "trades"),
          outOfSample: candidate?.outOfSample === true,
          futureLeakChecked: candidate?.futureLeakChecked === true,
          humanApprovalRequired: true,
          productionUpdateAllowed: false,
        }
      : null,
    hasComparison: Boolean(productionMetrics && candidateMetrics),
    mobileReady: true,
  };
}
