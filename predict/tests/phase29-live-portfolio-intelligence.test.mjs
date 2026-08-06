import test from "node:test";
import assert from "node:assert/strict";

import {
  analyzeLivePortfolioRisk,
  buildLivePortfolioAdvice,
  normalizeLivePortfolioSnapshot,
} from "../portfolio/live-portfolio-intelligence.js";

function snapshot(overrides = {}) {
  return {
    connection: { connected: true },
    readOnly: true,
    synchronized: true,
    synchronizedAt: "2026-08-06T08:00:00Z",
    source: "MARKETSPEED II RSS / Excel",
    sourceMode: "marketspeed-native-rss",
    account: {
      buyingPower: 2131,
      marketValue: 45280,
      unrealizedPnl: -9570,
      currency: "JPY",
    },
    positions: [
      {
        symbol: "408A",
        name: "iSベストAI",
        quantity: 160,
        availableQuantity: 160,
        averagePrice: 342.8125,
        marketPrice: 283,
        marketValue: 45280,
        unrealizedPnl: -9570,
        unrealizedPnlPercent: -17.447584,
        readOnly: true,
      },
    ],
    ...overrides,
  };
}

test("normalizes a healthy READ ONLY broker snapshot", () => {
  const portfolio = normalizeLivePortfolioSnapshot(snapshot(), {
    sectorBySymbol: { "408A": "AI" },
    aiBySymbol: { "408A": { score: 61, confidence: 0.72, signal: "SELL" } },
    now: "2026-08-06T08:10:00Z",
  });

  assert.equal(portfolio.positions[0].symbol, "408A");
  assert.equal(portfolio.positions[0].sector, "AI");
  assert.equal(portfolio.positions[0].aiSignal, "SELL");
  assert.equal(portfolio.totalMarketValue, 45280);
  assert.equal(portfolio.safety.brokerWriteAllowed, false);
  assert.equal(portfolio.safety.liveTradingAllowed, false);
});

test("rejects disconnected or writable snapshots", () => {
  assert.throws(
    () => normalizeLivePortfolioSnapshot(snapshot({ synchronized: false })),
    /disconnected|not synchronized/,
  );
  assert.throws(
    () => normalizeLivePortfolioSnapshot(snapshot({ readOnly: false })),
    /READ ONLY/,
  );
});

test("detects concentration and loss risk", () => {
  const portfolio = normalizeLivePortfolioSnapshot(snapshot(), {
    sectorBySymbol: { "408A": "AI" },
  });
  const report = analyzeLivePortfolioRisk(portfolio, {
    maxSinglePositionWeight: 0.35,
    maxSectorWeight: 0.5,
    warningLossPercent: -10,
  });

  assert.equal(report.status, "WARNING");
  assert.ok(report.blockers.includes("408A:POSITION_CONCENTRATION"));
  assert.ok(report.blockers.includes("408A:LOSS_THRESHOLD"));
  assert.ok(report.blockers.includes("AI:SECTOR_CONCENTRATION"));
  assert.equal(report.safety.orderCreationAllowed, false);
});

test("builds human-review-only advice without an order", () => {
  const portfolio = normalizeLivePortfolioSnapshot(snapshot(), {
    sectorBySymbol: { "408A": "AI" },
    aiBySymbol: { "408A": { score: 61, confidence: 0.72, signal: "SELL" } },
  });
  const risk = analyzeLivePortfolioRisk(portfolio);
  const advice = buildLivePortfolioAdvice(portfolio, risk);

  assert.equal(advice.status, "RISK_REVIEW_REQUIRED");
  assert.equal(advice.items[0].action, "REDUCE_REVIEW");
  assert.equal(advice.items[0].executable, false);
  assert.equal(advice.items[0].orderCandidateCreated, false);
  assert.equal(advice.executionAllowed, false);
  assert.equal(advice.safety.automaticExecutionAllowed, false);
});
