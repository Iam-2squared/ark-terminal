export const CANDIDATE_OPTIMIZER_V1 = "candidate-optimizer-v1";

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function score(metrics = {}) {
  return finite(metrics.accuracy) * 30
    + Math.min(finite(metrics.profitFactor), 3) * 15
    + Math.min(finite(metrics.sharpe), 3) * 10
    + finite(metrics.expectedValue) * 100
    - finite(metrics.maxDrawdown) * 20
    - finite(metrics.calibrationError) * 15;
}

export function optimizeCandidatesV1({
  production = {},
  candidates = [],
  minimumSampleSize = 100,
  maximumDegradation = 0.2,
} = {}) {
  const productionScore = score(production.metrics ?? production);
  const evaluated = candidates.map((candidate) => {
    const inSampleScore = score(candidate.inSample ?? {});
    const outOfSampleScore = score(candidate.outOfSample ?? {});
    const degradation = inSampleScore === 0 ? 0 : (inSampleScore - outOfSampleScore) / Math.abs(inSampleScore);
    const sampleSize = finite(candidate.outOfSample?.sampleSize);
    const overfitRisk = degradation > maximumDegradation || sampleSize < minimumSampleSize;
    const improvement = outOfSampleScore - productionScore;
    return {
      id: candidate.id ?? null,
      parameters: { ...(candidate.parameters ?? {}) },
      featureSet: [...(candidate.featureSet ?? [])],
      weights: { ...(candidate.weights ?? {}) },
      inSampleScore,
      outOfSampleScore,
      degradation,
      sampleSize,
      improvement,
      overfitRisk,
      eligible: !overfitRisk && improvement > 0,
    };
  }).sort((a, b) => b.outOfSampleScore - a.outOfSampleScore);

  const bestCandidate = evaluated.find((row) => row.eligible) ?? null;
  return {
    version: CANDIDATE_OPTIMIZER_V1,
    generatedAt: new Date().toISOString(),
    status: evaluated.length ? "READY" : "BLOCKED",
    productionScore,
    candidates: evaluated,
    bestCandidate,
    promotionRecommended: Boolean(bestCandidate),
    productionUpdateAllowed: false,
    automaticPromotionAllowed: false,
    humanApprovalRequired: true,
  };
}

export default optimizeCandidatesV1;
