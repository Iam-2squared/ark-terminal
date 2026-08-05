export const PHASE14_RELEASE_AUDIT_V1 = "phase14-release-audit-v1";

function check(id, passed, detail, severity = "BLOCKER") {
  return { id, passed: passed === true, detail, severity };
}

export function auditPhase14Release({
  unifiedDashboard,
  controlCenter,
  paperTrading,
  learning,
  dataValidation,
  uiState,
  cache,
  ci = {},
  environment = {},
  build = {},
} = {}) {
  const checks = [
    check("unified-dashboard", unifiedDashboard?.mobileReady === true, unifiedDashboard?.version ?? "missing"),
    check("control-center", controlCenter?.overallStatus !== "BLOCKED", controlCenter?.overallStatus ?? "missing"),
    check("paper-only", paperTrading?.liveExecutionAllowed === false && paperTrading?.brokerConnected === false, "live execution and broker connection must remain disabled"),
    check("kill-switch", paperTrading?.controls?.killSwitchActive !== undefined, "kill switch state must be observable"),
    check("human-approval", learning?.humanApprovalRequired === true && learning?.automaticPromotionAllowed === false, "candidate promotion requires explicit approval"),
    check("future-leak", dataValidation?.futureLeakDetected === false, dataValidation?.futureLeakDetected ?? "missing"),
    check("ui-states", uiState?.supports?.loading === true && uiState?.supports?.error === true && uiState?.supports?.empty === true, uiState?.version ?? "missing"),
    check("cache", cache?.deduplicationEnabled === true && cache?.ttlEnabled === true, cache?.version ?? "missing", "WARNING"),
    check("ci-predict", ci.predictTests === true, "predict tests"),
    check("ci-discovery", ci.discoveryTests === true, "discovery tests"),
    check("api-key", environment.openAiConfigured === true, "OpenAI configuration", "WARNING"),
    check("build-version", build.version === "1.0.0", build.version ?? "missing"),
  ];

  const blockers = checks.filter((entry) => !entry.passed && entry.severity === "BLOCKER");
  const warnings = checks.filter((entry) => !entry.passed && entry.severity === "WARNING");

  return {
    version: PHASE14_RELEASE_AUDIT_V1,
    generatedAt: new Date().toISOString(),
    releaseVersion: "1.0.0",
    status: blockers.length === 0 ? (warnings.length ? "READY_WITH_WARNINGS" : "READY") : "BLOCKED",
    ready: blockers.length === 0,
    passedCount: checks.filter((entry) => entry.passed).length,
    totalCount: checks.length,
    checks,
    blockers: blockers.map((entry) => entry.id),
    warnings: warnings.map((entry) => entry.id),
    safety: {
      liveTradingEnabled: false,
      brokerConnected: false,
      automaticModelPromotionEnabled: false,
      humanApprovalRequired: true,
    },
    build: { ...build },
  };
}

export default auditPhase14Release;
