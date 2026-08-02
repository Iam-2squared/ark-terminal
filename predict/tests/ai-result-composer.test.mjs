import assert from "node:assert/strict";
import test from "node:test";

import {
  composeAIResult,
  runAIAnalysis,
} from "../analysis/ai-result-composer.js";

test(
  "Composer builds normalized result",
  () => {
    const result =
      composeAIResult({
        runtime: {
          status: "ready",

          normalized: {
            symbol: "7203.T",
          },

          consensus: {
            action: "BUY",
            score: 82,
            agreementRate: 75,
          },

          calibratedConfidence: {
            confidence: 84,
          },

          gatedDecision: {
            approved: true,
            action: "BUY",
            score: 82,
            confidence: 84,
            reasons: [],
          },

          tradePlan: {
            action: "BUY",
            executable: true,

            sizing: {
              shares: 100,
              estimatedCost: 100000,
            },

            levels: {
              entryPrice: 1000,
              stopPrice: 950,
              targetPrice: 1100,
            },
          },

          marketIntelligence: {
            enabled: true,
            status: "ready",
            participating: true,
            selectedHorizon: 5,
            predictions: [],
            executionAllowed: false,
          },

          marketIntelligenceSnapshot: {
            status: "captured",
            reference: {
              id: "market-intelligence-snapshot:7203.T:1",
            },
            executionAllowed: false,
          },
        },
      });

    assert.equal(
      result.symbol,
      "7203.T",
    );

    assert.equal(
      result.action,
      "BUY",
    );

    assert.equal(
      result.score,
      82,
    );

    assert.equal(
      result.confidence,
      84,
    );

    assert.equal(
      result.shares,
      100,
    );

    assert.equal(
      result.executable,
      true,
    );

    assert.equal(
      result.marketIntelligence
        .participating,
      true,
    );

    assert.equal(
      result.marketIntelligence
        .executionAllowed,
      false,
    );

    assert.equal(
      result.marketIntelligenceSnapshot
        .status,
      "captured",
    );
  },
);

test(
  "Composer handles empty input",
  () => {
    const result =
      composeAIResult({});

    assert.equal(
      result.action,
      "HOLD",
    );

    assert.equal(
      result.score,
      50,
    );

    assert.equal(
      result.executable,
      false,
    );
  },
);

test(
  "Full AI analysis executes",
  async () => {
    const result =
      await runAIAnalysis({
        symbol: "7203.T",

        engines: [
          {
            name: "technical",

            result: {
              action: "BUY",
              score: 82,
              confidence: 85,
            },
          },
        ],

        historicalAccuracy: 80,
        volatility: 20,

        portfolioRisk: {
          riskPercent: 2,
        },

        capital: 500000,
        allocation: 0.5,
        price: 1000,
        lotSize: 100,
      });

    assert.equal(
      result.symbol,
      "7203.T",
    );

    assert.equal(
      result.status,
      "ready",
    );

    assert.equal(
      typeof result.score,
      "number",
    );
  },
);
