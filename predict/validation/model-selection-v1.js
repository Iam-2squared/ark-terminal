export const MODEL_SELECTION_V1_VERSION = "model-selection-v1";

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function normalizedMetrics(candidate = {}) {
  const source = candidate.validation?.candidateMetrics ?? candidate.metrics ?? candidate;
  return {
    accuracy: finite(source.accuracy),
    profitFactor: finite(source.profitFactor ?? source.pf),
    sharpe: finite(source.sharpe ?? source.sharpeRatio),
    maxDrawdown: finite(source.maxDrawdown ?? source.maximumDrawdown),
    averageReturn: finite(source.averageReturn ?? source.averageReturnPercent),
    sampleSize: finite(source.sampleSize ?? source.count),
  };
}

function score(metrics, weights) {
  const drawdown = metrics.maxDrawdown === null ? 0 : -Math.abs(metrics.maxDrawdown);
  return (
    (metrics.accuracy ?? 0) * weights.accuracy +
    (metrics.profitFactor ?? 0) * weights.profitFactor +
    (metrics.sharpe ?? 0) * weights.sharpe +
    drawdown * weights.maxDrawdown +
    (metrics.averageReturn ?? 0) * weights.averageReturn
  );
}

export function selectProductionCandidate({
  candidates = [],
  productionBaseline = null,
  weights = {},
  minimumSampleSize = 100,
} = {}) {
  const resolvedWeights = {
    accuracy: 1,
    profitFactor: 20,
    sharpe: 10,
    maxDrawdown: 1,
    averageReturn: 2,
    ...weights,
  };

  const ranked = (Array.isArray(candidates) ? candidates : []).map((candidate) => {
    const metrics = normalizedMetrics(candidate);
    const validation = candidate.validation ?? candidate;
    const eligible = Boolean(
      candidate.version &&
      validation.futureLeakChecked &&
      validation.outOfSample &&
      validation.comparison?.promotable &&
      (metrics.sampleSize ?? 0) >= minimumSampleSize
    );
    return {
      version: candidate.version ?? null,
      model: candidate,
      metrics,
      eligible,
      score: eligible ? score(metrics, resolvedWeights) : Number.NEGATIVE_INFINITY,
      reasons: [
        ...(!candidate.version ? ["MODEL_VERSION_REQUIRED"] : []),
        ...(!validation.futureLeakChecked ? ["FUTURE_LEAK_CHECK_REQUIRED"] : []),
        ...(!validation.outOfSample ? ["OUT_OF_SAMPLE_REQUIRED"] : []),
        ...(!validation.comparison?.promotable ? ["VALIDATION_THRESHOLDS_NOT_MET"] : []),
        ...((metrics.sampleSize ?? 0) < minimumSampleSize ? ["INSUFFICIENT_SAMPLE_SIZE"] : []),
      ],
    };
  }).sort((left, right) => right.score - left.score);

  const winner = ranked.find((item) => item.eligible) ?? null;
  return {
    version: MODEL_SELECTION_V1_VERSION,
    generatedAt: new Date().toISOString(),
    productionVersion: productionBaseline?.modelVersion ?? productionBaseline?.version ?? null,
    ranked: ranked.map(({ model, ...item }) => item),
    selectedCandidate: winner ? {
      version: winner.version,
      metrics: winner.metrics,
      score: winner.score,
      status: "READY_FOR_HUMAN_REVIEW",
    } : null,
    status: winner ? "CANDIDATE_SELECTED_REQUIRES_HUMAN_APPROVAL" : "NO_ELIGIBLE_CANDIDATE",
    safety: {
      humanApprovalRequired: true,
      productionUpdateAllowed: false,
      brokerExecutionAllowed: false,
    },
  };
}

export default selectProductionCandidate;
