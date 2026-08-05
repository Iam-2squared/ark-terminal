export const AI_CONTROL_CENTER_V1_VERSION = "ai-control-center-v1";

function health(status, fallback = "UNKNOWN") {
  const value = String(status ?? fallback).toUpperCase();
  return ["READY", "HEALTHY", "OK", "SUCCESS", "RUNNING", "SAFE"].includes(value)
    ? "HEALTHY"
    : ["BLOCKED", "FAILED", "ERROR", "UNSAFE"].includes(value)
      ? "BLOCKED"
      : "DEGRADED";
}

export function buildAiControlCenter({
  prediction = {},
  discovery = {},
  marketIntelligence = {},
  paperTrading = {},
  portfolio = {},
  accuracy = {},
  learning = {},
  runtime = {},
  safety = {},
  releaseAudit = {},
  ci = {},
  versions = {},
} = {}) {
  const modules = {
    prediction: health(prediction.status ?? prediction.health),
    discovery: health(discovery.status ?? discovery.health),
    marketIntelligence: health(marketIntelligence.status ?? marketIntelligence.health),
    paperTrading: health(paperTrading.status ?? paperTrading.health),
    portfolio: health(portfolio.status ?? portfolio.health),
    accuracy: health(accuracy.status ?? accuracy.health),
    learning: health(learning.status ?? learning.health),
    runtime: health(runtime.status ?? runtime.health),
    releaseAudit: health(releaseAudit.status ?? (releaseAudit.ready ? "READY" : null)),
    ci: ci.predictTests === true && ci.discoveryTests === true ? "HEALTHY" : "DEGRADED",
  };

  const blockers = Object.entries(modules)
    .filter(([, status]) => status === "BLOCKED")
    .map(([name]) => name);
  const degraded = Object.entries(modules)
    .filter(([, status]) => status === "DEGRADED")
    .map(([name]) => name);
  const liveExecutionAllowed = safety.liveExecutionAllowed === true;
  const brokerConnected = safety.brokerConnected === true;
  const automaticPromotionAllowed = safety.automaticPromotionAllowed === true;
  const safetyBlockers = [
    ...(liveExecutionAllowed ? ["LIVE_EXECUTION_MUST_REMAIN_DISABLED"] : []),
    ...(brokerConnected ? ["BROKER_CONNECTION_MUST_REMAIN_DISABLED"] : []),
    ...(automaticPromotionAllowed ? ["AUTOMATIC_PROMOTION_MUST_REMAIN_DISABLED"] : []),
  ];

  return {
    version: AI_CONTROL_CENTER_V1_VERSION,
    generatedAt: new Date().toISOString(),
    overallStatus: blockers.length || safetyBlockers.length
      ? "BLOCKED"
      : degraded.length
        ? "DEGRADED"
        : "HEALTHY",
    modules,
    blockers: [...blockers, ...safetyBlockers],
    degraded,
    killSwitchActive: safety.killSwitchActive === true,
    safety: {
      liveExecutionAllowed: false,
      brokerConnected: false,
      automaticPromotionAllowed: false,
      humanApprovalRequired: true,
    },
    versions: { ...versions },
    snapshots: {
      prediction,
      discovery,
      marketIntelligence,
      paperTrading,
      portfolio,
      accuracy,
      learning,
      runtime,
      releaseAudit,
    },
  };
}

export default buildAiControlCenter;
