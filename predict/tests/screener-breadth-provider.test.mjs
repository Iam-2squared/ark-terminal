import assert from "node:assert/strict";
import test from "node:test";

import { createScreenerBreadthPayload } from "../../api/providers/screener-breadth-provider.js";

function entry(symbol, changePercent, overrides = {}) {
  return {
    symbol,
    sector: "情報・通信業",
    dailyChangePercent: changePercent,
    volume: 1000,
    volumeRatio: 1.25,
    qualityScore: 80,
    scannedAt: "2026-08-01T06:00:00.000Z",
    status: "analyzed",
    source: "yahoo-finance",
    ...overrides,
  };
}

test("Screener provider converts real snapshot coverage into observations", () => {
  const payload = createScreenerBreadthPayload(
    {
      meta: {
        generatedAt: "2026-08-01T07:00:00.000Z",
        universeCount: 10,
        provider: "yahoo-finance",
        delivery: {
          sourceBranch: "automation/screener-data",
        },
      },
      entries: [
        entry("1111.T", 1.5),
        entry("2222.T", -0.75),
        entry("3333.T", 2, { status: "blocked" }),
      ],
    },
    {
      now: () => new Date("2026-08-02T00:00:00.000Z"),
    },
  );

  assert.equal(payload.status, "available");
  assert.equal(payload.availableCount, 2);
  assert.equal(payload.expectedObservationCount, 10);
  assert.equal(payload.coverage, 20);
  assert.equal(payload.observations[0].changePercent, 1.5);
  assert.equal(payload.observations[0].volumeRatio, 1.25);
  assert.equal(payload.observations[0].confidence, 80);
  assert.equal(payload.sourceBranch, "automation/screener-data");
  assert.equal(payload.executionAllowed, false);
});

test("Screener provider marks old data stale and lowers source confidence", () => {
  const payload = createScreenerBreadthPayload(
    {
      meta: {
        generatedAt: "2026-07-01T00:00:00.000Z",
        universeCount: 1,
      },
      entries: [entry("1111.T", 1, { qualityScore: 100 })],
    },
    {
      now: () => new Date("2026-08-02T00:00:00.000Z"),
    },
  );

  assert.equal(payload.status, "stale");
  assert.equal(payload.freshnessConfidence, 50);
  assert.equal(payload.observations[0].confidence, 50);
});

test("Screener provider keeps missing timestamps unavailable", () => {
  const payload = createScreenerBreadthPayload(
    {
      meta: {
        universeCount: 1,
      },
      entries: [entry("1111.T", 1, { scannedAt: null })],
    },
    {
      now: () => new Date("2026-08-02T00:00:00.000Z"),
    },
  );

  assert.equal(payload.generatedAt, null);
  assert.equal(payload.timestamp, null);
  assert.equal(payload.status, "partial");
});
