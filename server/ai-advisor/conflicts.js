function detectConflicts(input = {}) {
  const conflicts = [];

  const aiAction =
    input.ai?.decision?.action ||
    "HOLD";

  const marketRegime =
    input.market?.regime?.regime ||
    input.market?.regime ||
    "sideways";

  const portfolioRisk =
    input.portfolio?.risk?.level ||
    input.portfolio?.risk ||
    "low";

  if (
    aiAction === "WATCH_BUY" &&
    ["bear", "risk_off"].includes(
      marketRegime
    )
  ) {
    conflicts.push(
      "buy_signal_vs_weak_market"
    );
  }

  if (
    aiAction === "WATCH_BUY" &&
    ["high", "critical"].includes(
      portfolioRisk
    )
  ) {
    conflicts.push(
      "buy_signal_vs_portfolio_risk"
    );
  }

  if (
    aiAction === "WATCH_SELL" &&
    marketRegime === "bull"
  ) {
    conflicts.push(
      "sell_signal_vs_bull_market"
    );
  }

  return {
    hasConflict:
      conflicts.length > 0,

    conflicts,
  };
}

module.exports = {
  detectConflicts,
};