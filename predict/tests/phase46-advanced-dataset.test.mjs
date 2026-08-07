import assert from "node:assert/strict";
import test from "node:test";
import {
  PHASE46_ADVANCED_SAFETY,
  auditAdvancedDataset,
  buildDatasetLineage,
  generateExtendedFeatures,
  splitDatasetByTime,
} from "../features/phase46-advanced-dataset.js";

function sampleRecords(count = 120) {
  const rows = [];
  const start = Date.UTC(2026, 0, 1);
  for (let i = 0; i < count; i += 1) {
    const close = 100 + i + Math.sin(i / 4) * 2;
    rows.push({
      symbol: "7203.T",
      sessionDate: new Date(start + i * 86400000).toISOString().slice(0, 10),
      open: close - 0.8,
      high: close + 2,
      low: close - 2,
      close,
      volume: 1000 + (i * 10),
    });
  }
  return rows;
}

test("generates Phase48.1 alpha/regime interaction point-in-time rows", () => {
  const rows = generateExtendedFeatures(sampleRecords());
  assert.ok(rows.length > 0);
  assert.equal(rows.length, 44);
  assert.equal(rows[0].futureDataUsed, false);
  assert.equal(rows[0].featureCutoff, rows[0].sessionDate);
  assert.ok(rows[0].labelAvailableAt > rows[0].sessionDate);
  assert.ok([0, 1].includes(rows[0].label));
  assert.ok(Number.isFinite(rows[0].actualReturn));
  for (const key of ["rsi14", "atr14", "vwapGap20", "ma5Gap", "ma25Gap", "ma75Gap", "macd", "macdHistogram", "stochastic14", "adx14Approx", "return1", "return20", "gapOpenPrevClose", "rangePosition52w", "closePosition20", "closePosition60", "breakoutUp20", "breakdownDown20", "regimeTrend", "regimeVolatility", "regimeCode", "trendReturn5Interaction", "trendReturn20Interaction", "trendBreakoutInteraction", "trendBreakdownInteraction", "highVolBreakoutInteraction", "highVolVolumeInteraction", "highVolMomentumInteraction", "trendVolatilityInteraction"]) {
    assert.ok(Number.isFinite(rows[0].features[key]), `${key} should be finite`);
  }
});

test("chart structure uses only information available at the feature cutoff", () => {
  const records = sampleRecords();
  const rows = generateExtendedFeatures(records);
  const first = rows[0];
  const currentIndex = 75;
  const currentClose = records[currentIndex].close;
  const prior20 = records.slice(currentIndex - 20, currentIndex);
  const priorHigh = Math.max(...prior20.map((row) => row.high));
  const expectedBreakout = Math.max(0, currentClose / priorHigh - 1);
  assert.equal(first.breakoutUp20, expectedBreakout);
  assert.equal(first.futureDataUsed, false);
});

test("regime interaction features are deterministic and algebraically tied to point-in-time inputs", () => {
  const first = generateExtendedFeatures(sampleRecords(160));
  const second = generateExtendedFeatures(sampleRecords(160));
  assert.equal(first.length, second.length);
  for (let i = 0; i < first.length; i += 1) {
    assert.equal(first[i].regimeTrend, second[i].regimeTrend);
    assert.equal(first[i].regimeVolatility, second[i].regimeVolatility);
    assert.equal(first[i].regimeCode, second[i].regimeCode);
    assert.equal(first[i].trendReturn5Interaction, first[i].regimeTrend * first[i].return5);
    assert.equal(first[i].trendReturn20Interaction, first[i].regimeTrend * first[i].return20);
    assert.equal(first[i].trendBreakoutInteraction, first[i].regimeTrend * first[i].breakoutUp20);
    assert.equal(first[i].highVolBreakoutInteraction, first[i].regimeVolatility * first[i].breakoutUp20);
    assert.ok([-1, 0, 1].includes(first[i].regimeTrend));
    assert.ok([0, 1].includes(first[i].regimeVolatility));
  }
});

test("labels use the next same-symbol observation only", () => {
  const records = sampleRecords();
  const rows = generateExtendedFeatures(records);
  const first = rows[0];
  const current = records[75];
  const next = records[76];
  const expectedReturn = (next.close / current.close) - 1;
  assert.equal(first.actualReturn, expectedReturn);
  assert.equal(first.label, expectedReturn > 0 ? 1 : 0);
  assert.equal(first.labelAvailableAt, next.sessionDate);
});

test("drops rows whose future outcome is not yet available", () => {
  const records = sampleRecords(77);
  const rows = generateExtendedFeatures(records);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].sessionDate, records[75].sessionDate);
});

test("splits dataset in temporal order", () => {
  const rows = generateExtendedFeatures(sampleRecords(160));
  const split = splitDatasetByTime(rows);
  assert.equal(split.status, "VALID");
  assert.equal(split.temporalOrderValid, true);
  assert.ok(split.train.at(-1).sessionDate <= split.validation[0].sessionDate);
  assert.ok(split.validation.at(-1).sessionDate <= split.test[0].sessionDate);
});

test("builds Phase48.1 lineage and passes audit", () => {
  const rows = generateExtendedFeatures(sampleRecords(160));
  const split = splitDatasetByTime(rows);
  const lineage = buildDatasetLineage({
    datasetVersion: "phase48-test-v2",
    sourceManifestChecksum: "abc123",
    rows,
  });
  const audit = auditAdvancedDataset({ rows, split, lineage });
  assert.equal(audit.status, "VALID");
  assert.equal(lineage.featureVersion, "phase48-alpha-regime-v2");
  assert.equal(lineage.lineageChecksum.length, 64);
});

test("blocks invalid Phase47 contract rows", () => {
  const rows = generateExtendedFeatures(sampleRecords(160));
  const bad = [{ ...rows[0], label: undefined, features: {} }];
  const audit = auditAdvancedDataset({ rows: bad, split: { temporalOrderValid: true }, lineage: { lineageChecksum: "x" } });
  assert.equal(audit.status, "BLOCKED");
  assert.ok(audit.blockers.includes("LABEL_INVALID"));
  assert.ok(audit.blockers.includes("FEATURES_MISSING"));
});

test("blocks duplicate rows and future data flags", () => {
  const rows = generateExtendedFeatures(sampleRecords(160));
  const bad = [{ ...rows[0], futureDataUsed: true }, rows[0]];
  const audit = auditAdvancedDataset({ rows: bad, split: { temporalOrderValid: true }, lineage: { lineageChecksum: "x" } });
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
