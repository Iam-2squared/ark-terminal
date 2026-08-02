function collectSignals(input = {}) {
  const signals = [];

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

  const brokerStatus =
    input.broker?.status ||
    "ready";

  signals.push({
    source: "ai",
    name: "decision",
    value: aiAction,
  });

  signals.push({
    source: "market",
    name: "regime",
    value: marketRegime,
  });

  signals.push({
    source: "portfolio",
    name: "risk",
    value: portfolioRisk,
  });

  signals.push({
    source: "broker",
    name: "status",
    value: brokerStatus,
  });

  return signals;
}

module.exports = {
  collectSignals,
};