import assert from "node:assert/strict";
import test from "node:test";

import {
  HISTORICAL_MARKET_SNAPSHOT_VERSION,
  createHistoricalMarketSnapshot,
  createHistoricalMarketSnapshotReference,
  isHistoricalMarketSnapshot,
  restoreHistoricalMarketSnapshot,
} from "../market-intelligence/historical-market-snapshot-model.js";

const AS_OF = "2026-08-02T12:00:00.000Z";

function input(score = 80, capturedAt = "2026-08-02T12:01:00Z") {
  return {
    symbol: "7203.T",
    asOf: AS_OF,
    capturedAt,
    status: "ready",
    features: {
      version: "market-intelligence-features-v1",
      timestamp: AS_OF,
      status: "ready",
      confidence: 90,
      coverage: 100,
      values: { marketScore: score, compositeAI: score },
      details: {
        marketScore: {
          score,
          confidence: 90,
          coverage: 100,
          available: true,
          source: "test",
          sourceTimestamp: AS_OF,
        },
      },
    },
    predictions: [
      {
        horizon: 5,
        score,
        status: "ready",
        executionAllowed: true,
      },
    ],
  };
}

test("Historical snapshot identity is deterministic and deeply immutable", () => {
  const first = createHistoricalMarketSnapshot(input());
  const second = createHistoricalMarketSnapshot(
    input(80, "2026-08-02T12:05:00Z"),
  );

  assert.equal(first.version, HISTORICAL_MARKET_SNAPSHOT_VERSION);
  assert.equal(first.id, second.id);
  assert.equal(first.contentFingerprint, second.contentFingerprint);
  assert.equal(first.executionAllowed, false);
  assert.equal(first.predictions[0].executionAllowed, false);
  assert.equal(Object.isFrozen(first), true);
  assert.equal(Object.isFrozen(first.features.values), true);
  assert.throws(() => {
    first.features.values.marketScore = 1;
  }, TypeError);
});

test("Snapshot restore verifies identity and content fingerprint", () => {
  const snapshot = createHistoricalMarketSnapshot(input());
  const restored = restoreHistoricalMarketSnapshot(
    JSON.parse(JSON.stringify(snapshot)),
  );
  const tampered = JSON.parse(JSON.stringify(snapshot));
  tampered.features.values.marketScore = 1;
  const unsupported = JSON.parse(JSON.stringify(snapshot));
  unsupported.version = "historical-market-snapshot-v0";

  assert.equal(restored.contentFingerprint, snapshot.contentFingerprint);
  assert.equal(isHistoricalMarketSnapshot(restored), true);
  assert.equal(isHistoricalMarketSnapshot(tampered), false);
  assert.throws(
    () => restoreHistoricalMarketSnapshot(tampered),
    /fingerprint does not match/,
  );
  assert.throws(
    () => restoreHistoricalMarketSnapshot(unsupported),
    /version is unsupported/,
  );
});

test("Snapshot references expose identity without duplicating reports", () => {
  const snapshot = createHistoricalMarketSnapshot(input());
  const reference = createHistoricalMarketSnapshotReference(snapshot);

  assert.equal(reference.id, snapshot.id);
  assert.equal(reference.asOf, AS_OF);
  assert.equal(reference.contentFingerprint, snapshot.contentFingerprint);
  assert.equal(reference.features, undefined);
  assert.equal(reference.executionAllowed, false);
  assert.equal(Object.isFrozen(reference), true);
});
