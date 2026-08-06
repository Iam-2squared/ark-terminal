export const CHAMPION_CANDIDATE_FORWARD_VERSION = "phase25-champion-candidate-forward-v1";

const finite = (value) => Number.isFinite(Number(value));
const average = (values) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

function summarize(rows = []) {
  const resolved = rows.filter((row) => row?.status === "RESOLVED" && finite(row.netReturnPercent));
  const returns = resolved.map((row) => Number(row.netReturnPercent));
  const gains = returns.filter((value) => value > 0).reduce((sum, value) => sum + value, 0);
  const losses = Math.abs(returns.filter((value) => value < 0).reduce((sum, value) => sum + value, 0));
  return {
    sampleCount: resolved.length,
    averageNetReturn: average(returns),
    winRate: resolved.length ? returns.filter((value) => value > 0).length / resolved.length : null,
    profitFactor: losses > 0 ? gains / losses : gains > 0 ? Infinity : null,
  };
}

export function compareChampionCandidateForward({ champion = [], candidate = [], comparisonId = null } = {}) {
  const championSummary = summarize(champion);
  const candidateSummary = summarize(candidate);
  const blockers = [];

  if (championSummary.sampleCount === 0 || candidateSummary.sampleCount === 0) blockers.push("INSUFFICIENT_RESOLVED_SAMPLES");
  if (championSummary.sampleCount !== candidateSummary.sampleCount) blockers.push("SAMPLE_MISMATCH");

  const metrics = {
    averageNetReturnDelta: finite(championSummary.averageNetReturn) && finite(candidateSummary.averageNetReturn)
      ? candidateSummary.averageNetReturn - championSummary.averageNetReturn
      : null,
    winRateDelta: finite(championSummary.winRate) && finite(candidateSummary.winRate)
      ? candidateSummary.winRate - championSummary.winRate
      : null,
    profitFactorDelta: finite(championSummary.profitFactor) && finite(candidateSummary.profitFactor)
      ? candidateSummary.profitFactor - championSummary.profitFactor
      : null,
  };

  const candidateBetter = blockers.length === 0
    && [metrics.averageNetReturnDelta, metrics.winRateDelta, metrics.profitFactorDelta]
      .filter(finite)
      .every((value) => value >= 0)
    && metrics.averageNetReturnDelta > 0;

  return {
    version: CHAMPION_CANDIDATE_FORWARD_VERSION,
    comparisonId,
    champion: championSummary,
    candidate: candidateSummary,
    metrics,
    blockers,
    recommendation: blockers.length ? "BLOCKED" : candidateBetter ? "READY_FOR_HUMAN_REVIEW" : "KEEP_CHAMPION",
    promotionExecuted: false,
    safety: {
      paperOnly: true,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      humanApprovalRequired: true,
    },
  };
}

export default compareChampionCandidateForward;
