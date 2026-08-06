import assert from "node:assert/strict";
import test from "node:test";
import {
  PHASE46_ADVANCED_SAFETY,
  auditAdvancedDataset,
  buildDatasetLineage,
  generateExtendedFeatures,
  splitDatasetByTime,
} from "../features/phase46-advanced-dataset.js";

function sampleRecords(count = 40) {
  const rows = [];
  const start = Date.UTC(2026, 0, 1);
  for (let i = 0; i < count; i += 1) {
    const close = 100 + i;
    rows.push({
      symbol: "7203.T",
      sessionDate: new Date(start + i * 86400000).toISOString().slice(0, 10),
      open: close - 1,
      high: close + 2,
      low: close - 2,
      close,
      volume: 1000 + (i * 10),
    });
  }
  return rows;
}

test("generates extended point-in-time features", () => {
  const rows = generateExtendedFeatures(sampleRecords());
  assert.ok(rows.length > 0);
  assert.equal(rows[0].futureDataUsed, false);
  assert.equal(rows[0].featureCutoff, rows[0].sessionDate);
  assert.ok(Number.isFinite(rows[0].rsi14Approx));
  assert.ok(Number.isFinite(rows[0].vwap20));
});

test("splits dataset in temporal order", () => {
  const rows = generateExtendedFeatures(sampleRecords());
  const split = splitDatasetByTime(rows);
  assert.equal(split.status, "VALID");
  assert.equal(split.temporalOrderValid, true);
  assert.ok(split.train.at(-1).sessionDate <= split.validation[0].sessionDate);
  assert.ok(split.validation.at(-1).sessionDate <= split.test[0].sessionDate);
});

test("builds lineage and passes audit", () => {
  const rows = generateExtendedFeatures(sampleRecords());
  const split = splitDatasetByTime(rows);
  const lineage = buildDatasetLineage({
    datasetVersion: "phase46-test-v1",
    sourceManifestChecksum: "abc123",
    rows,
  });
  const audit = auditAdvancedDataset({ rows, split, lineage });
  assert.equal(audit.status, "VALID");
  assert.equal(lineage.lineageChecksum.length, 64);
});

test("blocks duplicate rows and future data flags", () => {
  const rows = generateExtendedFeatures(sampleRecords());
  const bad = [{ ...rows[0], futureDataUsed: true }, rows[0]];
  const audit = auditAdvancedDataset({
    rows: bad,
    split: { temporalOrderValid: true },
    lineage: { lineageChecksum: "x" },
  });
  assert.equal(audit.status, "BLOCKED");
  assert.ok(audit.blockers.includes("DUPLICATE_ROW"));
  assert.ok(audit.blockers.includes("FUTURE_DATA_FLAG"));
});

test("keeps all execution paths disabled", () => {
  assert.equal(PHASE46_ADVANCED_SAFETY.executionAllowed, false);
  assert.equal(PHASE46_ADVANCED_SAFETY.brokerWriteAllowed, false);
  assert.equal(PHASE46_ADVANCED_SAFETY.excelOrderWriteAllowed, false);
  assert.equal(PHASE46_ADVANCED_SAFETY.rssOrderFunctionAllowed, false);
  assert.equal(PHASE46_ADVANCED_SAFETY.liveTradingAllowed, false);
  assert.equal(PHASE46_ADVANCED_SAFETY.automaticPromotionAllowed, false);
  assert.equal(PHASE46_ADVANCED_SAFETY.productionUpdateAllowed, false);
  assert.equal(PHASE46_ADVANCED_SAFETY.humanApprovalRequired, true);
});
