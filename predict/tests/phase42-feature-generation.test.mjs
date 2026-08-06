import test from "node:test";
import assert from "node:assert/strict";

import { createDataLakeShard } from "../data/phase41-data-lake.js";
import {
  generateFeatureRecordsFromDataLake,
  buildFeatureIntegrationBundle,
} from "../features/phase42-feature-generation.js";

const rows = Array.from({ length: 90 }, (_, index) => ({
  kind: "OHLCV",
  symbol: "7203.T",
  sessionDate: new Date(Date.UTC(2026, 0, index + 1)).toISOString().slice(0, 10),
  source: "TEST",
  updatedAt: "2026-08-06T12:00:00.000Z",
  open: 2500 + index,
  high: 2520 + index,
  low: 2480 + index,
  close: 2510 + index,
  adjustedClose: 2510 + index,
  volume: 1000000 + (index * 1000),
}));

const dataLakeShard = createDataLakeShard({ records: rows });

test("generates deterministic feature records from Phase41 OHLCV", () => {
  const first = generateFeatureRecordsFromDataLake(dataLakeShard, { generatedAt: "2026-08-06T13:00:00.000Z" });
  const second = generateFeatureRecordsFromDataLake(dataLakeShard, { generatedAt: "2026-08-06T13:00:00.000Z" });
  assert.equal(first.length, 90);
  assert.equal(first[89].contentHash, second[89].contentHash);
  assert.equal(first[89].symbol, "7203.T");
  assert.ok(Number.isFinite(first[89].features.ma75));
  assert.ok(Number.isFinite(first[89].features.rsi14));
  assert.ok(Number.isFinite(first[89].features.macd));
  assert.ok(Number.isFinite(first[89].features.atr14));
  assert.ok(Number.isFinite(first[89].features.vwap20));
});

test("builds a read-only integration bundle", () => {
  const bundle = buildFeatureIntegrationBundle(dataLakeShard, {
    generatedAt: "2026-08-06T13:00:00.000Z",
  });
  assert.equal(bundle.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(bundle.dashboard.recordCount, 90);
  assert.equal(bundle.dashboard.canUseForTraining, true);
  assert.equal(bundle.dashboard.reviewRequired, true);
  assert.equal(bundle.integrations.predictionLab.enabled, true);
  assert.equal(bundle.integrations.backtest.enabled, true);
  assert.equal(bundle.integrations.candidateEvaluation.automaticPromotionAllowed, false);
  assert.equal(bundle.brokerWrites, 0);
  assert.equal(bundle.liveOrders, 0);
});

test("fails closed when the input data lake is empty", () => {
  const empty = createDataLakeShard({ records: [] });
  const bundle = buildFeatureIntegrationBundle(empty, {
    generatedAt: "2026-08-06T13:00:00.000Z",
  });
  assert.equal(bundle.status, "BLOCKED");
  assert.equal(bundle.dashboard.canUseForTraining, false);
  assert.equal(bundle.integrations.predictionLab.enabled, false);
  assert.equal(bundle.integrations.backtest.enabled, false);
});

test("keeps all trading paths disabled", () => {
  const bundle = buildFeatureIntegrationBundle(dataLakeShard, {
    generatedAt: "2026-08-06T13:00:00.000Z",
  });
  assert.equal(bundle.safety.brokerWriteAllowed, false);
  assert.equal(bundle.safety.liveTradingAllowed, false);
  assert.equal(bundle.safety.orderCreationAllowed, false);
  assert.equal(bundle.safety.orderTransmissionAllowed, false);
  assert.equal(bundle.safety.orderCancellationAllowed, false);
  assert.equal(bundle.safety.orderModificationAllowed, false);
  assert.equal(bundle.safety.excelOrderWriteAllowed, false);
  assert.equal(bundle.safety.orderTriggerWriteAllowed, false);
  assert.equal(bundle.safety.automaticPromotionAllowed, false);
  assert.equal(bundle.safety.productionUpdateAllowed, false);
});
