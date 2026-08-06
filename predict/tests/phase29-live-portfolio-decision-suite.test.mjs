import test from "node:test";
import assert from "node:assert/strict";

import {
  applyMarketRegimeOverlay,
  buildLivePortfolioDashboard,
  buildPortfolioScenarios,
} from "../portfolio/live-portfolio-decision-suite.js";
import {
  analyzeLivePortfolioRisk,
  normalizeLivePortfolioSnapshot,
} from "../portfolio/live-portfolio-intelligence.js";

function snapshot() {
  return {
    readOnly: true,
    synchronized: true,
    synchronizedAt: "2026-08-06T08:30:00.000Z",
    source: "MARKETSPEED II RSS / Excel",
    sourceMode: "marketspeed-native-rss",
    connection: { connected: true, authenticated: true, readOnly: true },
    account: { buyingPower: 50000, marketValue: 100000, unrealizedPnl: -5000, currency: "JPY" },
    positions: [
      {
        symbol: "7203",
        name: "Toyota",
        quantity: 100,
        availableQuantity: 100,
        averagePrice: 1000,
        marketPrice: 900,
        marketValue: 90000,
        unrealizedPnl: -10000,
        unrealizedPnlPercent: -10,
        readOnly: true,
      },
      {
        symbol: "9432.T",
        name: "NTT",
        quantity: 100,
        availableQuantity: 100,
        averagePrice: 100,
        marketPrice: 100,
        marketValue: 10000,
        unrealizedPnl: 0,
        unrealizedPnlPercent: 0,
        readOnly: true,
      },
    ],
  };
}

const context = {
  sectorBySymbol: { "7203.T": "AUTO", "9432.T": "TELECOM" },
  aiBySymbol: {
    "7203.T": { signal: "SELL", score: 42, confidence: 0.8 },
    "9432.T": { signal: "BUY", score: 76, confidence: 0.75 },
  },
};

test("market overlay increases stress in high volatility", () => {
  const portfolio = normalizeLivePortfolioSnapshot(snapshot(), context);
  const overlay = applyMarketRegimeOverlay(portfolio, {
    regime: "HIGH_VOLATILITY",
    volatility: 0.42,
    breadth: 0.3,
    indexTrend: "DOWN",
  });

  assert.equal(overlay.status, "MARKET_CONTEXT_READY");
  assert.equal(overlay.regime, "HIGH_VOLATILITY");
  assert.ok(overlay.positionOverlays[0].stressMultiplier > 1.4);
  assert.equal(overlay.executionAllowed, false);
  assert.equal(overlay.safety.brokerWriteAllowed, false);
});

test("incomplete market context fails closed for review", () => {
  const portfolio = normalizeLivePortfolioSnapshot(snapshot(), context);
  const overlay = applyMarketRegimeOverlay(portfolio, { regime: "UNKNOWN" });

  assert.equal(overlay.status, "MARKET_CONTEXT_INCOMPLETE");
  assert.ok(overlay.blockers.includes("MARKET_REGIME_UNKNOWN"));
  assert.ok(overlay.blockers.includes("VOLATILITY_UNAVAILABLE"));
  assert.ok(overlay.blockers.includes("BREADTH_UNAVAILABLE"));
});

test("risk warning prefers defensive scenario", () => {
  const portfolio = normalizeLivePortfolioSnapshot(snapshot(), context);
  const risk = analyzeLivePortfolioRisk(portfolio, { maxSinglePositionWeight: 0.5 });
  const market = applyMarketRegimeOverlay(portfolio, {
    regime: "BEAR",
    volatility: 0.3,
    breadth: 0.25,
  });
  const result = buildPortfolioScenarios(portfolio, risk, market);

  assert.equal(result.recommendedScenarioId, "DEFENSIVE");
  assert.equal(result.executionAllowed, false);
  assert.ok(result.scenarios.every((item) => item.executable === false));
  assert.ok(result.scenarios.every((item) => item.orderCandidateCreated === false));
});

test("dashboard aggregates parts 1 through 6 without execution rights", () => {
  const dashboard = buildLivePortfolioDashboard(snapshot(), {
    ...context,
    limits: { maxSinglePositionWeight: 0.95, warningLossPercent: -20 },
    market: { regime: "BULL", volatility: 0.15, breadth: 0.7, indexTrend: "UP" },
  });

  assert.deepEqual(dashboard.parts, [1, 2, 3, 4, 5, 6]);
  assert.equal(dashboard.phase, 29);
  assert.equal(dashboard.controls.readOnly, true);
  assert.equal(dashboard.controls.brokerWriteAllowed, false);
  assert.equal(dashboard.controls.liveTradingAllowed, false);
  assert.equal(dashboard.controls.orderCreationAllowed, false);
  assert.equal(dashboard.controls.automaticExecutionAllowed, false);
  assert.equal(dashboard.safety.humanApprovalRequired, true);
});

test("dashboard rejects disconnected snapshots", () => {
  const bad = snapshot();
  bad.connection.connected = false;
  assert.throws(
    () => buildLivePortfolioDashboard(bad, context),
    /disconnected or not synchronized/,
  );
});
