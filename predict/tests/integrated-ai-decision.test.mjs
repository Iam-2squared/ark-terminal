import assert from "node:assert/strict";
import test from "node:test";

import {
  buildIntegratedAiDecision,
  buildIntegratedDecisionCard,
} from "../analysis/integrated-ai-decision.js";

function strongState() {
  return {
    symbol: "2410.T",

    analysis: {
      technicalScore: 88,
      totalScore: 90,
      dataQualityScore: 95,
    },

    prediction: {
      confidence: 86,
    },

    indicators: {
      rsi: 62,

      adx: {
        value: 32,
      },

      atr: {
        percent: 2,
      },
    },
  };
}

test(
  "Strong environment produces buy recommendation",
  () => {
    const result =
      buildIntegratedAiDecision({
        state:
          strongState(),

        macroInput: {
          nikkei: 1.2,
          nasdaq: 1.8,
          sox: 2.4,
          vix: 17,
          bondYield: 4,
          oil: 75,
        },

        marketInput: {
          trendScore: 85,
          volatility: 15,
          adx: 32,
          rsi: 62,
          vix: 17,
        },

        portfolioPlan: {
          risk: {
            riskPercent: 2,
          },
        },
      });

    assert.ok(
      [
        "BUY",
        "STRONG BUY",
      ].includes(
        result.recommendation.action,
      ),
    );

    assert.equal(
      result.regime.regime,
      "BULL",
    );

    assert.equal(
      result.macro.sentiment,
      "BULLISH",
    );

    assert.ok(
      result.buyFactors.length >
      0,
    );
  },
);

test(
  "Weak environment produces defensive recommendation",
  () => {
    const result =
      buildIntegratedAiDecision({
        state: {
          analysis: {
            technicalScore: 25,
            totalScore: 30,
            dataQualityScore: 60,
          },

          prediction: {
            confidence: 40,
          },

          indicators: {
            rsi: 35,

            adx: {
              value: 30,
            },

            atr: {
              percent: 8,
            },
          },
        },

        macroInput: {
          nikkei: -2,
          nasdaq: -3,
          sox: -4,
          vix: 38,
          bondYield: 5,
          oil: 100,
        },

        marketInput: {
          trendScore: 20,
          volatility: 45,
          adx: 30,
          rsi: 35,
          vix: 38,
        },

        portfolioPlan: {
          risk: {
            riskPercent: 10,
          },
        },
      });

    assert.ok(
      [
        "SELL",
        "REDUCE",
      ].includes(
        result.recommendation.action,
      ),
    );

    assert.ok(
      result.riskFactors.length >
      0,
    );
  },
);

test(
  "Integrated decision card exposes UI fields",
  () => {
    const decision =
      buildIntegratedAiDecision({
        state:
          strongState(),

        macroInput: {
          nikkei: 1,
          nasdaq: 1,
          sox: 1,
          vix: 18,
        },
      });

    const card =
      buildIntegratedDecisionCard(
        decision,
      );

    assert.equal(
      typeof card.score,
      "number",
    );

    assert.equal(
      typeof card.confidence,
      "number",
    );

    assert.ok(
      Array.isArray(
        card.buyFactors,
      ),
    );

    assert.ok(
      Array.isArray(
        card.riskFactors,
      ),
    );
  },
);