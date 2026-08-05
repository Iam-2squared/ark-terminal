export const ARK_TERMINAL_VERSION = "1.0.0";

export function buildV1ReleaseManifest({
  commit = null,
  buildId = null,
  deployedAt = null,
  environment = "production",
} = {}) {
  return {
    name: "Ark Terminal",
    version: ARK_TERMINAL_VERSION,
    channel: "stable",
    environment,
    commit,
    buildId,
    deployedAt,
    capabilities: [
      "AI_ANALYSIS",
      "DISCOVERY",
      "MARKET_INTELLIGENCE",
      "BACKTEST",
      "PAPER_TRADING",
      "TRADE_MEMORY",
      "ACCURACY_MONITOR",
      "SELF_LEARNING_CANDIDATE_PIPELINE",
      "AI_CONTROL_CENTER",
    ],
    safety: {
      liveTradingEnabled: false,
      brokerConnectionEnabled: false,
      automaticModelPromotionEnabled: false,
      humanApprovalRequired: true,
    },
  };
}

export default buildV1ReleaseManifest;
