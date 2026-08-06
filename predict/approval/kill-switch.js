export const KILL_SWITCH_VERSION = "phase27-kill-switch-v1";

const normalize = (value, fallback = "UNKNOWN") => String(value ?? fallback).trim().toUpperCase() || fallback;

export function evaluateKillSwitch(input = {}) {
  const reasons = [];
  if (input.manualStop === true) reasons.push("MANUAL_STOP");
  if (input.apiHealthy === false) reasons.push("API_UNHEALTHY");
  if (input.rssHealthy === false) reasons.push("RSS_UNHEALTHY");
  if (input.bridgeHealthy === false) reasons.push("BRIDGE_UNHEALTHY");
  if (input.dataQualityPassed === false) reasons.push("DATA_QUALITY_FAILED");
  if (input.priceFresh === false) reasons.push("STALE_PRICE");
  if (input.clockSynchronized === false) reasons.push("CLOCK_SKEW");
  if (Number(input.criticalIncidents ?? 0) > 0) reasons.push("CRITICAL_INCIDENT_PRESENT");
  if (normalize(input.recoveryMode, "MANUAL_ONLY") !== "MANUAL_ONLY") reasons.push("RECOVERY_MUST_BE_MANUAL");

  const halted = reasons.length > 0;
  return {
    version: KILL_SWITCH_VERSION,
    status: halted ? "HALTED" : "ARMED",
    reasons,
    controls: {
      newCandidatesAllowed: !halted,
      pendingApprovalsAllowed: !halted,
      finalConfirmationAllowed: !halted,
      dryRunAllowed: !halted,
      recoveryMode: "MANUAL_ONLY",
    },
    safety: {
      mode: halted ? "READ_ONLY" : "DRY_RUN_ONLY",
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
      orderCreationAllowed: false,
      orderCancellationAllowed: false,
      orderModificationAllowed: false,
      humanApprovalRequired: true,
    },
  };
}

export default evaluateKillSwitch;
