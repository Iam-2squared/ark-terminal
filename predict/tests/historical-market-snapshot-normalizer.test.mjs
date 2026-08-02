import assert from "node:assert/strict";
import test from "node:test";

import {
  HISTORICAL_MARKET_RETENTION_POLICY,
  normalizeHistoricalMarketSnapshotInput,
} from "../market-intelligence/historical-market-snapshot-normalizer.js";

const AS_OF = "2026-08-02T12:00:00.000Z";
const SOURCE_TIME = "2026-08-02T10:00:00.000Z";

function featureSet() {
  return {
    version: "market-intelligence-features-v1",
    timestamp: AS_OF,
    status: "ready",
    confidence: 90,
    coverage: 80,
    values: { marketScore: 82, compositeAI: 80 },
    details: {
      marketScore: {
        score: 82,
        confidence: 90,
        coverage: 100,
        available: true,
        source: "market-snapshot",
        sourceTimestamp: SOURCE_TIME,
      },
    },
  };
}

function marketIntelligence() {
  const features = featureSet();
  const predictions = [
    {
      horizon: 5,
      status: "ready",
      score: 81,
      direction: "上昇",
      executionAllowed: true,
    },
  ];

  return {
    version: "market-intelligence-orchestrator-v1",
    status: "ready",
    timestamp: AS_OF,
    marketSnapshot: { timestamp: SOURCE_TIME, score: 79 },
    newsIntelligence: {
      timestamp: AS_OF,
      score: 75,
      items: [
        {
          id: "news-1",
          title: "決算発表",
          body: "保存対象外の原文",
          publishedAt: SOURCE_TIME,
          source: "TDnet",
        },
      ],
    },
    features,
    predictions,
    prediction: {
      modelVersion: "market-prediction-v1",
      status: "ready",
      timestamp: AS_OF,
      features,
      predictions,
    },
  };
}

test("Runtime and orchestrator output normalize into one point-in-time record", () => {
  const source = marketIntelligence();
  const original = structuredClone(source);
  const result = normalizeHistoricalMarketSnapshotInput({
    symbol: "7203.t",
    marketIntelligence: {
      version: "market-intelligence-runtime-v1",
      result: source,
    },
    capturedAt: "2026-08-02T12:01:00Z",
  });

  assert.equal(result.symbol, "7203.T");
  assert.equal(result.asOf, AS_OF);
  assert.equal(result.versions.runtime, "market-intelligence-runtime-v1");
  assert.equal(
    result.versions.orchestrator,
    "market-intelligence-orchestrator-v1",
  );
  assert.equal(result.predictions[0].executionAllowed, false);
  assert.equal(result.lineage[0].sourceTimestamp, SOURCE_TIME);
  assert.equal(result.reports.newsIntelligence.items[0].body, undefined);
  assert.equal(
    result.reports.newsIntelligence.retentionPolicy,
    HISTORICAL_MARKET_RETENTION_POLICY,
  );
  assert.deepEqual(source, original);
});

test("A source later than the historical analysis time is rejected", () => {
  const source = marketIntelligence();
  source.newsIntelligence.items[0].publishedAt =
    "2026-08-02T13:00:00Z";

  assert.throws(
    () =>
      normalizeHistoricalMarketSnapshotInput({
        symbol: "7203.T",
        marketIntelligence: source,
        capturedAt: AS_OF,
      }),
    /later than the historical snapshot timestamp/,
  );
});

test("Historical snapshot normalization validates required contracts", () => {
  assert.throws(
    () => normalizeHistoricalMarketSnapshotInput([]),
    /input must be an object/,
  );
  assert.throws(
    () => normalizeHistoricalMarketSnapshotInput({ symbol: "7203.T" }),
    /feature set is required/,
  );
  assert.throws(
    () =>
      normalizeHistoricalMarketSnapshotInput({
        symbol: "",
        features: featureSet(),
      }),
    /symbol is required/,
  );
  assert.throws(
    () =>
      normalizeHistoricalMarketSnapshotInput(
        {
          symbol: "7203.T",
          features: featureSet(),
        },
        { now: AS_OF },
      ),
    /clock must be a function/,
  );
});

test("Feature and capture timestamps must align with historical analysis", () => {
  const source = marketIntelligence();
  source.features.timestamp = "2026-08-02T11:00:00Z";
  source.prediction.features.timestamp = "2026-08-02T11:00:00Z";

  assert.throws(
    () =>
      normalizeHistoricalMarketSnapshotInput({
        symbol: "7203.T",
        marketIntelligence: source,
      }),
    /feature timestamp must match/,
  );

  assert.throws(
    () =>
      normalizeHistoricalMarketSnapshotInput({
        symbol: "7203.T",
        marketIntelligence: marketIntelligence(),
        capturedAt: "2026-08-02T11:59:59Z",
      }),
    /capture timestamp cannot precede/,
  );
});
