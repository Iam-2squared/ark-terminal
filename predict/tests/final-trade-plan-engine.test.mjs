import assert from "node:assert/strict";
import test from "node:test";

import {
  buildFinalTradePlan,
  buildTradePlanSummary,
  FinalTradePlanInternals,
} from "../analysis/final-trade-plan-engine.js";

test(
  "Approved decision creates executable lot",
  () => {
    const result =
      buildFinalTradePlan({
        symbol: "7203.T",

        decision: {
          action: "BUY",
          score: 82,
          confidence: 90,
        },

        portfolioRisk: {
          riskPercent: 2,
        },

        limits: {
          maximumRiskPercent: 6,
          minimumConfidence: 55,
          minimumScore: 60,
        },

        capital: 500000,
        allocation: 0.4,
        price: 1000,
        lotSize: 100,
        stopPercent: 5,
        targetPercent: 10,
      });

    assert.equal(
      result.executable,
      true,
    );

    assert.equal(
      result.action,
      "BUY",
    );

    assert.ok(
      result.sizing.shares >=
      100,
    );

    assert.equal(
      result.sizing.shares %
      100,
      0,
    );

    assert.equal(
      result.levels
        .riskRewardRatio,
      2,
    );
  },
);

test(
  "Blocked decision produces no trade",
  () => {
    const result =
      buildFinalTradePlan({
        decision: {
          action: "BUY",
          score: 80,
          confidence: 40,
        },

        portfolioRisk: {
          riskPercent: 12,
        },

        capital: 500000,
        allocation: 0.5,
        price: 1000,
      });

    assert.equal(
      result.executable,
      false,
    );

    assert.equal(
      result.action,
      "NO TRADE",
    );

    assert.equal(
      result.sizing.shares,
      0,
    );
  },
);

test(
  "Insufficient capital cannot buy one lot",
  () => {
    const result =
      buildFinalTradePlan({
        decision: {
          action: "BUY",
          score: 90,
          confidence: 95,
        },

        portfolioRisk: {
          riskPercent: 1,
        },

        capital: 30000,
        allocation: 1,
        price: 1000,
        lotSize: 100,
      });

    assert.equal(
      result.executable,
      false,
    );

    assert.equal(
      result.sizing.shares,
      0,
    );

    assert.ok(
      result.reasons.includes(
        "insufficient_capital_for_lot",
      ),
    );
  },
);

test(
  "Price levels are calculated",
  () => {
    const result =
      FinalTradePlanInternals
        .calculatePriceLevels({
          price: 1000,
          stopPercent: 4,
          targetPercent: 12,
        });

    assert.equal(
      result.stopPrice,
      960,
    );

    assert.equal(
      result.targetPrice,
      1120,
    );

    assert.equal(
      result.riskRewardRatio,
      3,
    );
  },
);

test(
  "Trade summary exposes execution fields",
  () => {
    const plan =
      buildFinalTradePlan({
        symbol: "AAA",

        decision: {
          action: "BUY",
          score: 85,
          confidence: 90,
        },

        portfolioRisk: {
          riskPercent: 2,
        },

        capital: 500000,
        allocation: 0.5,
        price: 500,
      });

    const summary =
      buildTradePlanSummary(
        plan,
      );

    assert.equal(
      summary.symbol,
      "AAA",
    );

    assert.equal(
      typeof summary.estimatedCost,
      "number",
    );

    assert.equal(
      typeof summary.estimatedLoss,
      "number",
    );
  },
);