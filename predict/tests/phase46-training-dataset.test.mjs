import test from "node:test";
import assert from "node:assert/strict";
import {
  PHASE46_SAFETY,
  auditTrainingDataset,
  buildPointInTimeRows,
  buildTrainingDataset,
} from "../features/phase46-training-dataset.js";

function sampleRecords(count = 30) {
  return Array.from({ length: count }, (_, index) => {
    const close = 100 + index;
    const date = new Date(Date.UTC(2026, 0, index + 1)).toISOString().slice(0, 10);
    return {
      kind: "OHLCV",
      symbol: "7203.T",
      sessionDate: date,
      open: close - 1,
      high: close + 2,
      low: close - 2,
      close,
      adjustedClose: close,
      volume: 1000 + index * 10,
    };
  });
}

test("builds deterministic point-in-time rows", () => {
  const rows = buildPointInTimeRows(sampleRecords(), { horizon: 5, minHistory: 20 });
  assert.equal(rows.length, 6);
  assert.equal(rows[0].symbol, "7203.T");
  assert.equal(rows[0].pointInTime.futureDataUsedInFeatures, false);
  assert.ok(rows[0].pointInTime.featureCutoff < rows[0].pointInTime.labelAvailableAt);
  assert.equal(rows[0].label.direction, 1);
});

test("dataset checksum is reproducible", () => {
  const first = buildTrainingDataset({ records: sampleRecords(), datasetVersion: "fixture-v1" });
  const second = buildTrainingDataset({ records: sampleRecords(), datasetVersion: "fixture-v1" });
  assert.equal(first.checksum, second.checksum);
  assert.equal(auditTrainingDataset(first).status, "VALID");
});

test("audit blocks checksum tampering", () => {
  const dataset = buildTrainingDataset({ records: sampleRecords() });
  const tampered = { ...dataset, datasetVersion: "tampered" };
  const audit = auditTrainingDataset(tampered);
  assert.equal(audit.status, "BLOCKED");
  assert.ok(audit.blockers.includes("CHECKSUM_MISMATCH"));
});

test("safety remains read only", () => {
  assert.equal(PHASE46_SAFETY.executionAllowed, false);
  assert.equal(PHASE46_SAFETY.brokerWriteAllowed, false);
  assert.equal(PHASE46_SAFETY.excelOrderWriteAllowed, false);
  assert.equal(PHASE46_SAFETY.rssOrderFunctionAllowed, false);
  assert.equal(PHASE46_SAFETY.liveTradingAllowed, false);
  assert.equal(PHASE46_SAFETY.automaticPromotionAllowed, false);
  assert.equal(PHASE46_SAFETY.productionUpdateAllowed, false);
  assert.equal(PHASE46_SAFETY.humanApprovalRequired, true);
});
