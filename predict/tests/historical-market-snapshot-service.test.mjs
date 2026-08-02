import assert from "node:assert/strict";
import test from "node:test";

import {
  HistoricalMarketSnapshotRepository,
} from "../market-intelligence/historical-market-snapshot-repository.js";
import {
  HistoricalMarketSnapshotService,
} from "../market-intelligence/historical-market-snapshot-service.js";

const AS_OF = "2026-08-02T12:00:00.000Z";

function marketIntelligence() {
  const features = {
    version: "market-intelligence-features-v1",
    timestamp: AS_OF,
    status: "ready",
    confidence: 88,
    coverage: 90,
    values: { marketScore: 78, compositeAI: 81 },
    details: {},
  };
  const predictions = [
    {
      horizon: 5,
      score: 81,
      direction: "上昇",
      status: "ready",
      executionAllowed: false,
    },
  ];

  return {
    version: "market-intelligence-runtime-v1",
    status: "ready",
    result: {
      version: "market-intelligence-orchestrator-v1",
      status: "ready",
      timestamp: AS_OF,
      features,
      predictions,
      prediction: {
        modelVersion: "market-prediction-v1",
        status: "ready",
        timestamp: AS_OF,
        features,
        predictions,
      },
    },
  };
}

test("Service captures runtime output and returns a stable reference", () => {
  const repository = new HistoricalMarketSnapshotRepository();
  const service = new HistoricalMarketSnapshotService({
    repository,
    now: () => Date.parse("2026-08-02T12:01:00Z"),
  });
  const input = {
    symbol: "7203.T",
    marketIntelligence: marketIntelligence(),
  };
  const first = service.capture(input);
  const second = service.capture(input);

  assert.equal(first.status, "captured");
  assert.equal(first.inserted, true);
  assert.equal(second.status, "duplicate");
  assert.equal(second.inserted, false);
  assert.equal(first.reference.id, second.reference.id);
  assert.equal(first.reference.executionAllowed, false);
  assert.equal(service.count(), 1);
  assert.equal(service.get(first.reference.id).asOf, AS_OF);
});

test("Safe capture isolates invalid historical input", () => {
  const service = new HistoricalMarketSnapshotService();
  const result = service.captureSafely({ symbol: "7203.T" });

  assert.equal(result.status, "error");
  assert.equal(result.inserted, false);
  assert.equal(result.reference, null);
  assert.match(result.error.message, /feature set is required/);
  assert.equal(result.executionAllowed, false);
});

test("Persistence failure leaves the in-memory archive unchanged", () => {
  const repository = new HistoricalMarketSnapshotRepository({
    storage: {
      getItem() {
        return null;
      },
      setItem() {
        throw new Error("storage quota exceeded");
      },
      removeItem() {},
    },
  });
  const service = new HistoricalMarketSnapshotService({
    repository,
    now: () => Date.parse("2026-08-02T12:01:00Z"),
  });
  const result = service.captureSafely({
    symbol: "7203.T",
    marketIntelligence: marketIntelligence(),
  });

  assert.equal(result.status, "error");
  assert.match(result.error.message, /quota exceeded/);
  assert.equal(repository.count(), 0);
});

test("Service exposes leakage-safe point-in-time lookup", () => {
  const service = new HistoricalMarketSnapshotService();
  service.capture({
    symbol: "7203.T",
    marketIntelligence: marketIntelligence(),
    capturedAt: AS_OF,
  });

  assert.equal(
    service.findAtOrBefore({
      symbol: "7203.T",
      timestamp: "2026-08-02T11:59:59Z",
    }),
    null,
  );
  assert.equal(
    service.findAtOrBefore({
      symbol: "7203.T",
      timestamp: "2026-08-02T12:00:00Z",
    }).asOf,
    AS_OF,
  );
});

test("Service validates replaceable dependencies", () => {
  assert.throws(
    () => new HistoricalMarketSnapshotService({ repository: {} }),
    /repository is invalid/,
  );
  assert.throws(
    () => new HistoricalMarketSnapshotService({ now: 1 }),
    /clock must be a function/,
  );
});
