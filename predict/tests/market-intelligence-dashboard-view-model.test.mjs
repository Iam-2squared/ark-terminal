import assert from "node:assert/strict";
import test from "node:test";

import { buildMarketIntelligenceDashboardViewModel } from "../analysis/market-intelligence-dashboard-view-model.js";

const HORIZONS = [1, 3, 5, 10, 20];

function detail(score, source) {
  return {
    score,
    confidence: 84,
    coverage: 90,
    available: true,
    source,
  };
}

function runtimeReport() {
  const timestamp = "2026-08-02T06:00:00.000Z";

  return {
    status: "ready",
    enabled: true,
    selectedHorizon: 5,
    featureStatus: "ready",
    featureConfidence: 84,
    featureCoverage: 90,
    predictions: HORIZONS.map((horizon) => ({
      horizon,
      direction: horizon < 10 ? "上昇" : "中立",
      score: horizon < 10 ? 63 : 52,
      confidence: 82,
      status: "ready",
      executionAllowed: false,
    })),
    result: {
      status: "ready",
      timestamp,
      features: {
        status: "ready",
        timestamp,
        confidence: 84,
        coverage: 90,
        details: {
          marketScore: detail(65, "market-snapshot"),
          breadth: detail(61, "market-breadth"),
          liquidity: detail(58, "liquidity"),
          newsScore: detail(55, "news-intelligence"),
          sectorStrength: detail(66, "sector-strength"),
          compositeAI: detail(63, "prediction-features"),
        },
      },
      breadth: {
        score: 61,
        confidence: 84,
        coverage: 90,
        availableCount: 90,
        requestedCount: 100,
        advancers: 55,
        decliners: 30,
        unchanged: 5,
        advanceDeclineRatio: 1.833,
        timestamp,
      },
      sectorStrength: {
        score: 66,
        confidence: 82,
        coverage: 88,
        sectorCount: 4,
        positiveSectors: 3,
        negativeSectors: 1,
        leaders: [
          {
            sector: "半導体",
            score: 78,
            confidence: 84,
            averageChangePercent: 1.25,
          },
        ],
        laggards: [
          {
            sector: "電力",
            score: 41,
            confidence: 76,
            averageChangePercent: -0.72,
          },
        ],
      },
      newsIntelligence: {
        score: 55,
        confidence: 80,
        coverage: 75,
      },
      liquidity: {
        score: 58,
        confidence: 83,
        coverage: 88,
      },
      compositeMarket: {
        score: 65,
        confidence: 84,
        coverage: 90,
      },
    },
    executionAllowed: false,
  };
}

function analysisState() {
  return {
    symbol: "285A",
    marketBreadthSource: {
      source: "ark-screener",
      status: "available",
      availableCount: 90,
      expectedObservationCount: 100,
      coverage: 90,
      timestamp: "2026-08-02T06:00:00.000Z",
    },
    marketEnvironment: {
      availableCount: 12,
      requestedCount: 14,
      series: [{ timestamp: "2026-08-02T05:59:00.000Z" }],
    },
    context: {
      providers: {
        news: "Finnhub",
        disclosures: "J-Quants TDnet",
      },
      status: { news: "available", disclosures: "available" },
      news: [{ publishedAt: "2026-08-02T05:00:00.000Z" }],
      disclosures: [{ publishedAt: "2026-08-02T04:00:00.000Z" }],
    },
  };
}

test("ViewModel exposes six features, five horizons and provider health", () => {
  const view = buildMarketIntelligenceDashboardViewModel({
    report: runtimeReport(),
    state: analysisState(),
  });

  assert.equal(view.status.key, "ready");
  assert.equal(view.symbol, "285A");
  assert.equal(view.metrics.length, 6);
  assert.deepEqual(
    view.metrics.map((metric) => metric.key),
    [
      "marketScore",
      "breadth",
      "liquidity",
      "newsScore",
      "sectorStrength",
      "compositeAI",
    ],
  );
  assert.equal(view.compositeScore, 63);
  assert.equal(view.predictions.length, 5);
  assert.equal(view.predictions.find((item) => item.selected).horizon, 5);
  assert.equal(view.breadth.advancers, 55);
  assert.equal(view.sectors.leaders[0].name, "半導体");
  assert.equal(view.providers.length, 4);
  assert.equal(view.providers[0].statusLabel, "接続済み");
  assert.equal(view.executionAllowed, false);
  assert.match(view.notice, /保証しません/);
});

test("Missing reports remain unavailable instead of becoming zero scores", () => {
  const view = buildMarketIntelligenceDashboardViewModel({
    state: { symbol: "TEST" },
    phase: "unavailable",
  });

  assert.equal(view.status.key, "unavailable");
  assert.equal(view.compositeScore, null);
  assert.equal(view.featureConfidence, null);
  assert.equal(view.metrics.every((metric) => metric.score === null), true);
  assert.equal(view.metrics.every((metric) => metric.confidence === null), true);
  assert.equal(view.predictions.every((item) => item.score === null), true);
  assert.equal(view.breadth.advancers, null);
  assert.equal(view.sectors.sectorCount, null);
});

test("Explicit lifecycle phases keep loading and errors presentable", () => {
  const loading = buildMarketIntelligenceDashboardViewModel({
    state: analysisState(),
    phase: "loading",
  });
  const failed = buildMarketIntelligenceDashboardViewModel({
    state: analysisState(),
    phase: "error",
    error: new Error("provider failed"),
  });

  assert.equal(loading.status.label, "計算中");
  assert.equal(failed.status.key, "error");
  assert.equal(failed.errorMessage, "provider failed");
  assert.equal(failed.executionAllowed, false);
});
