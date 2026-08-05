export const ARK_TERMINAL_STABLE_VERSION = "1.0.1";
export const PHASE15_RELEASE_AUDIT_V1 = "phase15-release-audit-v1";

function check(id, passed, severity = "BLOCKER") {
  return { id, passed: passed === true, severity };
}

export function auditV101StableRelease({
  smokeTest = {},
  historicalValidation = {},
  forwardTest = {},
  calibration = {},
  ci = {},
  deployment = {},
  build = {},
} = {}) {
  const checks = [
    check("production-smoke-test", ["READY", "READY_WITH_WARNINGS"].includes(smokeTest.status)),
    check("historical-validation", historicalValidation.status === "READY" && historicalValidation.dataQuality?.futureLeakDetected === false),
    check("forward-test-paper-only", forwardTest.liveExecutionAllowed === false && forwardTest.brokerConnected === false),
    check("forward-test-kill-switch", typeof forwardTest.killSwitchActive === "boolean"),
    check("calibration-approval-gate", calibration.humanApprovalRequired === true && calibration.productionUpdateAllowed === false),
    check("ci-predict", ci.predictTests === true),
    check("ci-discovery", ci.discoveryTests === true),
    check("vercel-ready", deployment.vercelReady === true, "WARNING"),
    check("build-version", build.version === ARK_TERMINAL_STABLE_VERSION),
  ];
  const blockers = checks.filter((entry) => !entry.passed && entry.severity === "BLOCKER").map((entry) => entry.id);
  const warnings = checks.filter((entry) => !entry.passed && entry.severity === "WARNING").map((entry) => entry.id);

  return {
    version: PHASE15_RELEASE_AUDIT_V1,
    releaseVersion: ARK_TERMINAL_STABLE_VERSION,
    generatedAt: new Date().toISOString(),
    status: blockers.length ? "BLOCKED" : warnings.length ? "READY_WITH_WARNINGS" : "READY",
    ready: blockers.length === 0,
    checks,
    blockers,
    warnings,
    build: { ...build },
    deployment: { ...deployment },
    safety: {
      liveTradingEnabled: false,
      brokerConnectionEnabled: false,
      automaticModelPromotionEnabled: false,
      humanApprovalRequired: true,
    },
  };
}

export function buildV101StableManifest({ commit = null, buildId = null, deployedAt = null } = {}) {
  return {
    name: "Ark Terminal",
    version: ARK_TERMINAL_STABLE_VERSION,
    channel: "stable",
    commit,
    buildId,
    deployedAt,
    release: {
      phase: 15,
      historicalValidation: true,
      forwardTestAutomation: true,
      calibrationReview: true,
    },
    safety: {
      liveTradingEnabled: false,
      brokerConnectionEnabled: false,
      automaticModelPromotionEnabled: false,
      humanApprovalRequired: true,
    },
  };
}

export default buildV101StableManifest;
