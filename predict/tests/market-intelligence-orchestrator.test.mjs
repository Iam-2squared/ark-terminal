import assert from "node:assert/strict";
import test from "node:test";

import {
  MARKET_DATA_DEFINITIONS,
  createMarketDataPoint,
} from "../market-intelligence/market-data-model.js";
import {
  MarketIntelligenceOrchestrator,
} from "../market-intelligence/market-intelligence-orchestrator.js";

const NOW = Date.parse("2026-08-02T12:00:00Z");
const SOURCE_TIME = "2026-08-02T10:00:00Z";

function marketPoint(symbol) {
  const isVix = symbol === "VIX";

  return createMarketDataPoint({
    symbol,
    price: isVix ? 16 : 100,
    change: isVix ? -1 : 1.5,
    changePercent: isVix ? -5 : 1.5,
    timestamp: SOURCE_TIME,
    source: "test-provider",
    confidence: 100,
  });
}

function marketData() {
  return MARKET_DATA_DEFINITIONS.map(({ symbol }) =>
    marketPoint(symbol),
  );
}

function observation(symbol, sector, changePercent) {
  return {
    symbol,
    sector,
    changePercent,
    volume: 1_000_000,
    volumeRatio: 1.4,
    turnoverRatio: 1.2,
    aboveMa20: true,
    aboveMa50: true,
    newHigh: changePercent > 0,
    newLow: false,
    timestamp: SOURCE_TIME,
    source: "test-breadth",
    confidence: 100,
  };
}

function input() {
  return {
    marketData: marketData(),
    observations: [
      observation("A", "AUTO", 2),
      observation("B", "AUTO", 1),
      observation("C", "AUTO", 1.5),
      observation("D", "TECH", 2.5),
      observation("E", "TECH", 1.2),
      observation("F", "TECH", 0.8),
    ],
    newsItems: [
      {
        id: "news-1",
        title: "最高益、上方修正を発表",
        summary: "業績予想を引き上げました。",
        publishedAt: SOURCE_TIME,
        source: "TDnet",
        symbol: "7203.T",
        importance: 90,
        confidence: 100,
      },
    ],
    momentum: {
      score: 85,
      confidence: 100,
      coverage: 100,
      timestamp: SOURCE_TIME,
    },
    technical: {
      atrPercent: 2,
    },
  };
}

test("Orchestrator connects Bundles 1-5 into one prediction result", async () => {
  const orchestrator = new MarketIntelligenceOrchestrator({ now: () => NOW });
  const result = await orchestrator.analyze(input());

  assert.equal(result.version, "market-intelligence-orchestrator-v1");
  assert.equal(result.status, "ready");
  assert.equal(result.marketSnapshot.timestamp, "2026-08-02T12:00:00.000Z");
  assert.equal(result.marketSnapshot.indexes.availableCount, 8);
  assert.equal(result.breadth.advancers, 6);
  assert.equal(result.liquidity.activeVolumePercent, 100);
  assert.equal(result.sectorStrength.sectorCount, 2);
  assert.equal(result.newsIntelligence.items.length, 1);
  assert.deepEqual(result.horizons, [1, 3, 5, 10, 20]);
  assert.equal(result.predictions.length, 5);
  assert.equal(result.executionAllowed, false);
});

test("Orchestrator can load Bundle 1 through an injected data service", async () => {
  const calls = [];
  const controller = new AbortController();
  const orchestrator = new MarketIntelligenceOrchestrator({ now: () => NOW });
  const result = await orchestrator.analyze(
    {
      marketDataService: {
        async getAll(options) {
          calls.push(options);
          return marketData();
        },
      },
    },
    {
      forceRefresh: true,
      signal: controller.signal,
    },
  );

  assert.deepEqual(calls, [
    { forceRefresh: true, signal: controller.signal },
  ]);
  assert.equal(result.marketSnapshot.indexes.availableCount, 8);
  assert.equal(result.executionAllowed, false);
});

test("Grouped Bundle 4 collections are analyzed rather than mistaken for reports", async () => {
  const orchestrator = new MarketIntelligenceOrchestrator({ now: () => NOW });
  const result = await orchestrator.analyze({
    news: {
      earnings: [
        {
          id: "earnings-grouped",
          title: "EPSは市場予想を上回る",
          publishedAt: SOURCE_TIME,
          source: "TDnet",
          actual: 120,
          consensus: 100,
          metric: "EPS",
          confidence: 100,
        },
      ],
    },
  });

  assert.equal(result.newsIntelligence.items.length, 1);
  assert.equal(result.newsIntelligence.items[0].type, "earnings");
  assert.equal(typeof result.newsIntelligence.score, "number");
});

test("Missing sources stay unavailable without neutral placeholder data", async () => {
  const orchestrator = new MarketIntelligenceOrchestrator({ now: () => NOW });
  const result = await orchestrator.analyze({});

  assert.equal(result.status, "unavailable");
  assert.equal(result.marketSnapshot, null);
  assert.equal(result.newsIntelligence, null);
  assert.equal(result.features.compositeAI, null);
  assert.equal(
    result.predictions.every((prediction) => prediction.score === null),
    true,
  );
});

test("Raw sources later than the analysis timestamp are rejected", async () => {
  const orchestrator = new MarketIntelligenceOrchestrator({ now: () => NOW });

  await assert.rejects(
    () =>
      orchestrator.analyze({
        newsItems: [
          {
            title: "future item",
            publishedAt: "2026-08-02T13:00:00Z",
            source: "test",
          },
        ],
      }),
    /later than the analysis timestamp/,
  );
});

test("Orchestrator validates input and replaceable module contracts", async () => {
  const orchestrator = new MarketIntelligenceOrchestrator({ now: () => NOW });

  await assert.rejects(() => orchestrator.analyze([]), /must be an object/);
  assert.throws(
    () => new MarketIntelligenceOrchestrator({ breadthEngine: {} }),
    /breadth engine is invalid/,
  );
  assert.throws(
    () => new MarketIntelligenceOrchestrator({ now: NOW }),
    /clock must be a function/,
  );
});
