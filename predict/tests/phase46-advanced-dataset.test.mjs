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

test("generates Phase47-compatible point-in-time rows", () => {
  const rows = generateExtendedFeatures(sampleRecords());
  assert.ok(rows.length > 0);
  assert.equal(rows.length, 20);
  assert.equal(rows[0].futureDataUsed, false);
  assert.equal(rows[0].featureCutoff, rows[0].sessionDate);
  assert.ok(rows[0].labelAvailableAt > rows[0].sessionDate);
  assert.ok([0, 1].includes(rows[0].label));
  assert.ok(Number.isFinite(rows[0].actualReturn));
  assert.ok(Number.isFinite(rows[0].features.rsi14Approx));
  assert.ok(Number.isFinite(rows[0].features.vwap20));
});

test("labels use the next same-symbol observation only", () => {
  const records = sampleRecords();
  const rows = generateExtendedFeatures(records);
  const first = rows[0];
  const current = records[19];
  const next = records[20];
  const expectedReturn = (next.close / current.close) - 1;
  assert.equal(first.actualReturn, expectedReturn);
  assert.equal(first.label, expectedReturn > 0 ? 1 : 0);
  assert.equal(first.labelAvailableAt, next.sessionDate);
});

test("drops rows whose future outcome is not yet available", () => {
  const records = sampleRecords(21);
  const rows = generateExtendedFeatures(records);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].sessionDate, records[19].sessionDate);
});

test("splits dataset in temporal order", () => {
  const rows = generateExtendedFeatures(sampleRecords(80));
  const split = splitDatasetByTime(rows);
  assert.equal(split.status, "VALID");
  assert.equal(split.temporalOrderValid, true);
  assert.ok(split.train.at(-1).sessionDate <= split.validation[0].sessionDate);
  assert.ok(split.validation.at(-1).sessionDate <= split.test[0].sessionDate);
});

test("builds lineage and passes audit", () => {
  const rows = generateExtendedFeatures(sampleRecords(80));
  const split = splitDatasetByTime(rows);
  const lineage = buildDatasetLineage({
    datasetVersion: "phase46-test-v2",
    sourceManifestChecksum: "abc123",
    rows,
  });
  const audit = auditAdvancedDataset({ rows, split, lineage });
  assert.equal(audit.status, "VALID");
  assert.equal(lineage.featureVersion, "phase46-advanced-v2");
  assert.equal(lineage.lineageChecksum.length, 64);
});

test("blocks invalid Phase47 contract rows", () => {
  const rows = generateExtendedFeatures(sampleRecords(80));
  const bad = [{ ...rows[0], label: undefined, features: {} }];
  const audit = auditAdvancedDataset({
    rows: bad,
    split: { temporalOrderValid: true },
    lineage: { lineageChecksum: "x" },
  });
  assert.equal(audit.status, "BLOCKED");
  assert.ok(audit.blockers.includes("LABEL_INVALID"));
  assert.ok(audit.blockers.includes("FEATURES_MISSING"));
});

test("blocks duplicate rows and future data flags", () => {
  const rows = generateExtendedFeatures(sampleRecords(80));
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
