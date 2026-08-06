import {
  READ_ONLY_SAFETY,
  analyzeLivePortfolioRisk,
  buildLivePortfolioAdvice,
  normalizeLivePortfolioSnapshot,
} from "./live-portfolio-intelligence.js";

function finiteNumber(value, fallback = null) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function normalizedRegime(value) {
  const regime = String(value ?? "UNKNOWN").trim().toUpperCase();
  return ["BULL", "BEAR", "RANGE", "HIGH_VOLATILITY", "LOW_VOLATILITY"].includes(regime)
    ? regime
    : "UNKNOWN";
}

export function applyMarketRegimeOverlay(portfolio, market = {}) {
  const regime = normalizedRegime(market.regime);
  const volatility = finiteNumber(market.volatility, null);
  const breadth = finiteNumber(market.breadth, null);
  const indexTrend = String(market.indexTrend ?? "UNKNOWN").toUpperCase();
  const blockers = [];

  if (regime === "UNKNOWN") blockers.push("MARKET_REGIME_UNKNOWN");
  if (volatility == null) blockers.push("VOLATILITY_UNAVAILABLE");
  if (breadth == null) blockers.push("BREADTH_UNAVAILABLE");

  const positionOverlays = portfolio.positions.map((position) => {
    let stressMultiplier = 1;
    const reasons = [];

    if (regime === "BEAR") {
      stressMultiplier += 0.25;
      reasons.push("BEAR_REGIME");
    }
    if (regime === "HIGH_VOLATILITY") {
      stressMultiplier += 0.35;
      reasons.push("HIGH_VOLATILITY_REGIME");
    }
    if (breadth != null && breadth < 0.35) {
      stressMultiplier += 0.15;
      reasons.push("WEAK_MARKET_BREADTH");
    }
    if (position.aiSignal === "SELL") {
      stressMultiplier += 0.1;
      reasons.push("AI_SELL_SIGNAL");
    }

    return {
      symbol: position.symbol,
      stressMultiplier: Number(stressMultiplier.toFixed(4)),
      stressedMarketValue: Number((Math.max(0, position.marketValue) / stressMultiplier).toFixed(2)),
      reasons,
      executable: false,
    };
  });

  return {
    status: blockers.length ? "MARKET_CONTEXT_INCOMPLETE" : "MARKET_CONTEXT_READY",
    regime,
    volatility,
    breadth,
    indexTrend,
    blockers,
    positionOverlays,
    executionAllowed: false,
    safety: { ...READ_ONLY_SAFETY },
  };
}

export function buildPortfolioScenarios(portfolio, riskReport, marketOverlay) {
  const marketPenalty = marketOverlay.positionOverlays.reduce(
    (sum, item) => sum + Math.max(0, item.stressMultiplier - 1),
    0,
  );
  const riskPenalty = riskReport.blockers.length;
  const baseValue = Math.max(0, finiteNumber(portfolio.totalMarketValue, 0));

  const scenarios = [
    {
      id: "BASE",
      label: "現状維持",
      projectedValue: baseValue,
      reviewPriority: riskPenalty + marketPenalty,
    },
    {
      id: "DEFENSIVE",
      label: "防御優先",
      projectedValue: Number((baseValue * (1 - Math.min(0.2, 0.02 * riskPenalty + 0.01 * marketPenalty))).toFixed(2)),
      reviewPriority: Math.max(0, riskPenalty - 1),
    },
    {
      id: "RISK_ON_REVIEW",
      label: "強気条件再確認",
      projectedValue: Number((baseValue * (1 + Math.max(0, 0.01 * portfolio.positions.filter((item) => item.aiSignal === "BUY").length))).toFixed(2)),
      reviewPriority: riskPenalty + (marketOverlay.regime === "BULL" ? 0 : 2),
    },
  ].map((scenario) => ({
    ...scenario,
    executable: false,
    orderCandidateCreated: false,
    humanReviewRequired: true,
  }));

  return {
    status: "SCENARIOS_READY_FOR_HUMAN_REVIEW",
    scenarios,
    recommendedScenarioId:
      riskReport.status === "WARNING" || ["BEAR", "HIGH_VOLATILITY"].includes(marketOverlay.regime)
        ? "DEFENSIVE"
        : "BASE",
    executionAllowed: false,
    safety: { ...READ_ONLY_SAFETY },
  };
}

export function buildLivePortfolioDashboard(snapshot, context = {}) {
  const portfolio = normalizeLivePortfolioSnapshot(snapshot, context);
  const risk = analyzeLivePortfolioRisk(portfolio, context.limits);
  const advice = buildLivePortfolioAdvice(portfolio, risk, context.advice);
  const market = applyMarketRegimeOverlay(portfolio, context.market);
  const scenarios = buildPortfolioScenarios(portfolio, risk, market);

  return {
    phase: 29,
    parts: [1, 2, 3, 4, 5, 6],
    status:
      market.status === "MARKET_CONTEXT_READY" && risk.status === "HEALTHY"
        ? "READY_FOR_HUMAN_REVIEW"
        : "REVIEW_REQUIRED",
    summary: {
      positionCount: portfolio.positions.length,
      totalMarketValue: portfolio.totalMarketValue,
      buyingPower: portfolio.account.buyingPower,
      riskStatus: risk.status,
      marketRegime: market.regime,
      adviceCount: advice.items.length,
      recommendedScenarioId: scenarios.recommendedScenarioId,
    },
    portfolio,
    risk,
    advice,
    market,
    scenarios,
    controls: {
      readOnly: true,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
      orderCreationAllowed: false,
      automaticExecutionAllowed: false,
      humanReviewRequired: true,
    },
    safety: { ...READ_ONLY_SAFETY },
  };
}
