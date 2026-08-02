import assert from "node:assert/strict";
import test from "node:test";

import {
  executeRuntimeV3,
  executeRuntimeV3Sync,
  normalizeRuntimeV3Input,
  PredictionLabRuntimeV3,
} from "../analysis/runtime-v3.js";
import {
  historicalMarketSnapshotService,
} from "../market-intelligence/historical-market-snapshot-service.js";

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

function marketPredictionResult() {
  return {
    status: "ready",
    features: {
      status: "ready",
      confidence: 90,
      coverage: 100,
    },
    predictions: [1, 3, 5, 10, 20].map((horizon) => ({
      horizon,
      status: "ready",
      direction: "上昇",
      score: 84,
      confidence: {
        score: 90,
        coverage: 100,
        isProbability: false,
      },
      executionAllowed: false,
    })),
    executionAllowed: false,
  };
}

function report(score) {
  return {
    score,
    confidence: 100,
    coverage: 100,
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

    assert.equal(
      result.marketIntelligence
        .enabled,
      false,
    );

    assert.equal(
      result.consensus
        .engineCount,
      3,
    );
  },
);

test(
  "Runtime v3 sync adds a validated Market Intelligence vote",
  () => {
    const result =
      executeRuntimeV3Sync({
        ...strongInput(),
        symbol:
          "MI-SYNC",
        predictionHorizon:
          10,
        marketIntelligenceResult:
          marketPredictionResult(),
      });

    assert.equal(
      result.marketIntelligence
        .participating,
      true,
    );

    assert.equal(
      result.marketIntelligence
        .selectedHorizon,
      10,
    );

    assert.equal(
      result.consensus
        .engineCount,
      4,
    );

    assert.equal(
      result.marketIntelligence
        .executionAllowed,
      false,
    );
  },
);

test(
  "Async Runtime v3 executes the Market Intelligence pipeline",
  async () => {
    const result =
      await executeRuntimeV3({
        ...strongInput(),
        symbol:
          "MI-ASYNC",
        predictionHorizon:
          5,
        marketIntelligence: {
          marketSnapshot: {
            indexes:
              report(82),
            macro: {
              ...report(78),
              sentiment:
                "BULLISH",
              vixLevel:
                16,
              items: [
                {
                  symbol:
                    "VIX",
                  price:
                    16,
                  confidence:
                    100,
                  available:
                    true,
                },
              ],
            },
            regime: {
              regime:
                "BULL",
            },
          },
          breadth:
            report(84),
          liquidity:
            report(80),
          sectorStrength:
            report(82),
          newsIntelligence:
            report(86),
          momentum:
            report(83),
          technical: {
            atrPercent:
              2,
          },
        },
      });

    assert.equal(
      result.marketIntelligence
        .status,
      "ready",
    );

    assert.equal(
      result.marketIntelligence
        .participating,
      true,
    );

    assert.equal(
      result.consensus
        .engineCount,
      4,
    );

    assert.equal(
      result.dashboard
        .marketIntelligence
        .predictions
        .length,
      5,
    );
  },
);

test(
  "Market Intelligence errors do not stop the legacy Runtime v3 decision",
  async () => {
    const result =
      await executeRuntimeV3({
        ...strongInput(),
        symbol:
          "MI-ERROR",
        marketIntelligence:
          [],
      });

    assert.equal(
      result.status,
      "ready",
    );

    assert.equal(
      result.marketIntelligence
        .status,
      "error",
    );

    assert.equal(
      result.consensus
        .engineCount,
      3,
    );
  },
);

test(
  "Runtime archives Market Intelligence only when historical capture is enabled",
  async () => {
    historicalMarketSnapshotService.clear();

    const result =
      await executeRuntimeV3({
        ...strongInput(),
        symbol:
          "MI-HISTORY",
        forceMarketIntelligenceRefresh:
          true,
        captureMarketIntelligenceSnapshot:
          true,
        marketIntelligence: {
          compositeMarket:
            report(82),
          breadth:
            report(84),
          liquidity:
            report(80),
          sectorStrength:
            report(82),
          newsIntelligence:
            report(86),
          momentum:
            report(83),
          technical: {
            atrPercent:
              2,
          },
        },
      });

    assert.equal(
      result.marketIntelligenceSnapshot
        .status,
      "captured",
    );

    assert.equal(
      result.marketIntelligenceSnapshot
        .executionAllowed,
      false,
    );

    const archived =
      historicalMarketSnapshotService
        .get(
          result
            .marketIntelligenceSnapshot
            .reference
            .id,
        );

    assert.equal(
      archived.symbol,
      "MI-HISTORY",
    );

    assert.equal(
      archived.predictions.length,
      5,
    );

    historicalMarketSnapshotService.clear();
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
