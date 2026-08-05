export const PHASE11_RELEASE_AUDIT_V1_VERSION = "phase11-release-audit-v1";

function check(id, passed, detail) {
  return {
    id,
    passed: passed === true,
    detail,
  };
}

function versionOf(value) {
  return value?.version ?? value?.reportVersion ?? null;
}

export function auditPhase11Release({
  baseline = null,
  validation = null,
  selection = null,
  ui = null,
} = {}) {
  const checks = [
    check(
      "BASELINE_REPORT_PRESENT",
      Boolean(baseline),
      versionOf(baseline) ?? "missing",
    ),
    check(
      "BASELINE_VERSION_VALID",
      versionOf(baseline) === "model-performance-baseline-v1",
      versionOf(baseline) ?? "missing",
    ),
    check(
      "VALIDATION_REPORT_PRESENT",
      Boolean(validation),
      versionOf(validation) ?? "missing",
    ),
    check(
      "VALIDATION_VERSION_VALID",
      versionOf(validation) === "backtest-forward-validation-v2",
      versionOf(validation) ?? "missing",
    ),
    check(
      "OUT_OF_SAMPLE_CONFIRMED",
      validation?.outOfSample === true,
      validation?.outOfSample === true ? "confirmed" : "not confirmed",
    ),
    check(
      "FUTURE_LEAK_CHECK_CONFIRMED",
      validation?.futureLeakChecked === true,
      validation?.futureLeakChecked === true ? "confirmed" : "not confirmed",
    ),
    check(
      "VALIDATION_PRODUCTION_UPDATE_DISABLED",
      validation?.safety?.productionUpdateAllowed === false,
      String(validation?.safety?.productionUpdateAllowed),
    ),
    check(
      "VALIDATION_BROKER_EXECUTION_DISABLED",
      validation?.safety?.brokerExecutionAllowed === false,
      String(validation?.safety?.brokerExecutionAllowed),
    ),
    check(
      "SELECTION_REPORT_PRESENT",
      Boolean(selection),
      versionOf(selection) ?? selection?.status ?? "missing",
    ),
    check(
      "SELECTION_HUMAN_APPROVAL_REQUIRED",
      selection?.safety?.humanApprovalRequired === true,
      String(selection?.safety?.humanApprovalRequired),
    ),
    check(
      "SELECTION_PRODUCTION_UPDATE_DISABLED",
      selection?.safety?.productionUpdateAllowed === false,
      String(selection?.safety?.productionUpdateAllowed),
    ),
    check(
      "SELECTION_BROKER_EXECUTION_DISABLED",
      selection?.safety?.brokerExecutionAllowed === false,
      String(selection?.safety?.brokerExecutionAllowed),
    ),
    check(
      "UI_CONTRACT_PRESENT",
      versionOf(ui) === "model-performance-ui-v1",
      versionOf(ui) ?? "missing",
    ),
    check(
      "UI_PRODUCTION_UPDATE_DISABLED",
      ui?.safety?.productionUpdateAllowed === false,
      String(ui?.safety?.productionUpdateAllowed),
    ),
    check(
      "UI_BROKER_EXECUTION_DISABLED",
      ui?.safety?.brokerExecutionAllowed === false,
      String(ui?.safety?.brokerExecutionAllowed),
    ),
  ];

  const failedChecks = checks.filter((item) => !item.passed);
  const releaseReady = failedChecks.length === 0;
  const modelPromotionEligible =
    releaseReady &&
    validation?.comparison?.promotable === true &&
    selection?.selectedCandidate != null;

  return {
    version: PHASE11_RELEASE_AUDIT_V1_VERSION,
    generatedAt: new Date().toISOString(),
    phase: "Phase11",
    releaseReady,
    modelPromotionEligible,
    status: releaseReady ? "RELEASE_READY" : "RELEASE_BLOCKED",
    checks,
    failedChecks: failedChecks.map((item) => item.id),
    safety: {
      humanApprovalRequired: true,
      productionUpdateAllowed: false,
      brokerExecutionAllowed: false,
    },
    notes: [
      "Release readiness does not authorize a Production model update.",
      "Model promotion remains a separate human decision.",
      "Broker execution remains disabled.",
    ],
  };
}

export default auditPhase11Release;
