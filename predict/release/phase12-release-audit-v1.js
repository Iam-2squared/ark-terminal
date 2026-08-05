export const PHASE12_RELEASE_AUDIT_V1 = "phase12-release-audit-v1";

function check(id, passed, detail) {
  return { id, passed: passed === true, detail };
}

export function auditPhase12Release({
  rankingAdapter,
  discoveryFinal,
  predictionLabFinal,
  paperTradingFinal,
  ci = {},
} = {}) {
  const checks = [
    check(
      "ranking-v2",
      rankingAdapter?.version === "discovery-ranking-adapter-v2",
      rankingAdapter?.version ?? "missing",
    ),
    check(
      "discovery-final",
      discoveryFinal?.version === "discovery-final-v1" && discoveryFinal?.mobileReady !== false,
      discoveryFinal?.version ?? "missing",
    ),
    check(
      "prediction-lab-final",
      predictionLabFinal?.version === "prediction-lab-final-v1" && predictionLabFinal?.mobileReady === true,
      predictionLabFinal?.version ?? "missing",
    ),
    check(
      "paper-trading-final",
      paperTradingFinal?.version === "paper-trading-final-v1" && paperTradingFinal?.mobileReady === true,
      paperTradingFinal?.version ?? "missing",
    ),
    check(
      "paper-only-safety",
      paperTradingFinal?.liveExecutionAllowed === false && paperTradingFinal?.brokerConnected === false,
      "live execution and broker connection must remain disabled",
    ),
    check(
      "human-approval-gate",
      predictionLabFinal?.candidate == null ||
        (predictionLabFinal.candidate.humanApprovalRequired === true &&
          predictionLabFinal.candidate.productionUpdateAllowed === false),
      "candidate promotion must require explicit human approval",
    ),
    check(
      "ci-predict",
      ci.predictTests === true,
      "predict test suite",
    ),
    check(
      "ci-discovery",
      ci.discoveryTests === true,
      "discovery test suite",
    ),
  ];

  const failed = checks.filter((entry) => !entry.passed);

  return {
    version: PHASE12_RELEASE_AUDIT_V1,
    status: failed.length === 0 ? "READY" : "BLOCKED",
    ready: failed.length === 0,
    passedCount: checks.length - failed.length,
    totalCount: checks.length,
    checks,
    blockers: failed.map((entry) => entry.id),
    releaseRules: {
      liveTradingEnabled: false,
      automaticModelPromotionEnabled: false,
      humanApprovalRequired: true,
    },
  };
}

export default auditPhase12Release;
