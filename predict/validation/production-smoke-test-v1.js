export const PRODUCTION_SMOKE_TEST_V1 = "production-smoke-test-v1";

function normalizeStatus(value) {
  const status = String(value ?? "UNKNOWN").toUpperCase();
  if (["READY", "HEALTHY", "OK", "SUCCESS"].includes(status)) return "PASS";
  if (["DEGRADED", "WARNING", "PARTIAL"].includes(status)) return "WARN";
  return "FAIL";
}

export function runProductionSmokeTest({
  surfaces = {},
  api = {},
  ui = {},
  runtime = {},
  safety = {},
} = {}) {
  const checks = [
    ["unified-dashboard", surfaces.unifiedDashboard],
    ["prediction-lab", surfaces.predictionLab],
    ["discovery", surfaces.discovery],
    ["ai-analysis", surfaces.aiAnalysis],
    ["paper-trading", surfaces.paperTrading],
    ["portfolio", surfaces.portfolio],
    ["accuracy-dashboard", surfaces.accuracyDashboard],
    ["learning-dashboard", surfaces.learningDashboard],
    ["ai-control-center", surfaces.aiControlCenter],
    ["api-health", api.health],
    ["openai-connection", api.openai],
    ["mobile-layout", ui.mobile],
    ["dark-mode", ui.darkMode],
    ["loading-state", ui.loading],
    ["error-state", ui.error],
    ["console-errors", runtime.consoleErrors === 0 ? "PASS" : "FAIL"],
    ["build-info", runtime.buildInfoPresent ? "PASS" : "FAIL"],
    ["live-trading-disabled", safety.liveExecutionAllowed === false ? "PASS" : "FAIL"],
    ["broker-disabled", safety.brokerConnected === false ? "PASS" : "FAIL"],
  ].map(([id, raw]) => {
    const result = raw === "PASS" || raw === "WARN" || raw === "FAIL" ? raw : normalizeStatus(raw);
    return { id, result, raw };
  });

  const blockers = checks.filter((check) => check.result === "FAIL").map((check) => check.id);
  const warnings = checks.filter((check) => check.result === "WARN").map((check) => check.id);

  return {
    version: PRODUCTION_SMOKE_TEST_V1,
    generatedAt: new Date().toISOString(),
    status: blockers.length ? "BLOCKED" : warnings.length ? "READY_WITH_WARNINGS" : "READY",
    passed: checks.filter((check) => check.result === "PASS").length,
    total: checks.length,
    blockers,
    warnings,
    checks,
    safety: {
      liveExecutionAllowed: false,
      brokerConnected: false,
    },
  };
}

export default runProductionSmokeTest;
