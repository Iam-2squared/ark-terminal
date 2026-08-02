import assert from "node:assert/strict";
import test from "node:test";

import {
  executeRuntimeV3,
  executeRuntimeV3Sync,
  normalizeRuntimeV3Input,
  PredictionLabRuntimeV3,
} from "../analysis/runtime-v3.js";

function strongInput() {
  return {
    symbol: "7203.T",

    engines: [
      {
        name: "technical",
        weight: 2,

        result: {
          action: "BUY",
          score: 86,
          confidence: 88,
        },
      },

      {
        name: "macro",
        weight: 1,

        result: {
          action: "BUY",
          score: 80,
          confidence: 82,
        },
      },

      {
        name: "learning",
        weight: 1,

        result: {
          action: "STRONG BUY",
          score: 90,
          confidence: 90,
        },
      },
    ],

    historicalAccuracy: 82,
    volatility: 20,

    portfolioRisk: {
      riskPercent: 2,
    },

    limits: {
      maximumRiskPercent: 6,
      minimumConfidence: 55,
      minimumScore: 60,
    },

    capital: 500000,
    allocation: 0.5,
    price: 1000,
    lotSize: 100,
    stopPercent: 5,
    targetPercent: 10,

    macro: "BULLISH",
    regime: "BULL",

    learning: {
      score: 7,
      confidence: 0.85,
      trend: "UP",
    },
  };
}

test(
  "Runtime v3 input is normalized",
  () => {
    const result =
      normalizeRuntimeV3Input({
        capital: "500000",
        allocation: 2,
        lotSize: 0,
      });

    assert.equal(
      result.capital,
      500000,
    );

    assert.equal(
      result.allocation,
      1,
    );

    assert.equal(
      result.lotSize,
      100,
    );
  },
);

test(
  "Runtime v3 builds complete decision",
  () => {
    const result =
      executeRuntimeV3Sync(
        strongInput(),
      );

    assert.equal(
      result.status,
      "ready",
    );

    assert.equal(
      result.version,
      "prediction-lab-runtime-v3",
    );

    assert.equal(
      result.consensus.ready,
      true,
    );

    assert.ok(
      [
        "BUY",
        "STRONG BUY",
      ].includes(
        result.consensus.action,
      ),
    );

    assert.equal(
      result.tradePlan.executable,
      true,
    );

    assert.ok(
      result.tradePlan
        .sizing
        .shares >= 100,
    );

    assert.equal(
      result.dashboard.regime,
      "BULL",
    );
  },
);

test(
  "High portfolio risk blocks execution",
  () => {
    const result =
      executeRuntimeV3Sync({
        ...strongInput(),

        portfolioRisk: {
          riskPercent: 15,
        },
      });

    assert.equal(
      result.gatedDecision
        .approved,
      false,
    );

    assert.equal(
      result.tradePlan
        .executable,
      false,
    );

    assert.equal(
      result.tradePlan.action,
      "NO TRADE",
    );
  },
);

test(
  "Async runtime uses Runtime v2",
  async () => {
    const result =
      await executeRuntimeV3(
        strongInput(),
      );

    assert.equal(
      result.status,
      "ready",
    );

    assert.equal(
      result.normalized.symbol,
      "7203.T",
    );
  },
);

test(
  "Runtime v3 class API",
  () => {
    const runtime =
      new PredictionLabRuntimeV3();

    const result =
      runtime.executeSync(
        strongInput(),
      );

    const stats =
      runtime.stats();

    assert.equal(
      result.status,
      "ready",
    );

    assert.equal(
      typeof stats.version,
      "string",
    );
  },
);