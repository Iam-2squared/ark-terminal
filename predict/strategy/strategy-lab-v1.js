export const STRATEGY_LAB_V1 = "strategy-lab-v1";

function finite(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function score(metrics = {}) {
  const winRate = finite(metrics.winRate, 0) ?? 0;
  const profitFactor = finite(metrics.profitFactor, 0) ?? 0;
  const sharpe = finite(metrics.sharpe, 0) ?? 0;
  const expectedValue = finite(metrics.expectedValue, 0) ?? 0;
  const maxDrawdown = finite(metrics.maxDrawdown, 0) ?? 0;
  return winRate * 25 + Math.min(profitFactor, 3) * 15 + Math.min(sharpe, 3) * 12 + expectedValue * 100 - maxDrawdown * 0.8;
}

export function runStrategyLabV1({
  strategies = [],
  minimumSampleSize = 100,
  overfitThreshold = 0.2,
} = {}) {
  const results = strategies.map((strategy) => {
    const inSample = strategy?.inSample ?? {};
    const outOfSample = strategy?.outOfSample ?? {};
    const inScore = score(inSample);
    const outScore = score(outOfSample);
    const degradation = inScore === 0 ? 0 : (inScore - outScore) / Math.abs(inScore);
    const sampleSize = finite(outOfSample.sampleSize, 0) ?? 0;
    const overfitRisk = degradation > overfitThreshold || sampleSize < minimumSampleSize;
    return {
      id: strategy?.id ?? null,
      name: strategy?.name ?? strategy?.id ?? "Unnamed Strategy",
      parameters: { ...(strategy?.parameters ?? {}) },
      regime: strategy?.regime ?? "ALL",
      sector: strategy?.sector ?? "ALL",
      inSample,
      outOfSample,
      inScore,
      outScore,
      degradation,
      sampleSize,
      overfitRisk,
      candidateEligible: !overfitRisk,
    };
  }).sort((a, b) => b.outScore - a.outScore);

  const candidates = results.filter((row) => row.candidateEligible);
  return {
    version: STRATEGY_LAB_V1,
    generatedAt: new Date().toISOString(),
    status: results.length ? "READY" : "BLOCKED",
    strategies: results,
    bestStrategy: candidates[0] ?? null,
    rejectedStrategies: results.filter((row) => !row.candidateEligible),
    productionUpdateAllowed: false,
    automaticPromotionAllowed: false,
    humanApprovalRequired: true,
  };
}

export default runStrategyLabV1;
