import test from "node:test";
import assert from "node:assert/strict";

import { buildPointInTimeUniverse, assertSymbolInUniverse } from "../data-integrity/survivorship-universe.js";
import { evaluateDataQuality, assertDataQuality } from "../data-integrity/data-quality-gate.js";
import { buildDatasetVersionManifest } from "../data-integrity/dataset-version.js";
import { buildReproducibilityFingerprint, compareReproducibility, assertReproducible } from "../data-integrity/reproducibility.js";

test("builds a historical universe without survivorship bias", () => {
  const universe = buildPointInTimeUniverse({
    asOf: "2024-06-01T00:00:00Z",
    records: [
      { symbol: "1111.T", listedAt: "2020-01-01T00:00:00Z" },
      { symbol: "2222.T", listedAt: "2020-01-01T00:00:00Z", delistedAt: "2024-05-01T00:00:00Z" },
      { symbol: "3333.T", listedAt: "2025-01-01T00:00:00Z" },
    ],
  });
  assert.deepEqual(universe.symbols, ["1111.T"]);
  assert.equal(universe.diagnostics.excludedDelisted, 1);
  assert.equal(universe.diagnostics.excludedFutureListings, 1);
  assert.equal(assertSymbolInUniverse("1111.t", universe), true);
  assert.throws(() => assertSymbolInUniverse("2222.T", universe), /SYMBOL_NOT_IN_POINT_IN_TIME_UNIVERSE/);
});

test("blocks invalid, duplicate and cross-symbol rows", () => {
  const now = Date.parse("2026-08-06T05:00:00Z");
  const result = evaluateDataQuality({
    expectedSymbol: "7203.T",
    now,
    rows: [
      { symbol: "7203.T", time: "2026-08-06T04:59:00Z", close: 3000, volume: 100 },
      { symbol: "6758.T", time: "2026-08-06T04:59:00Z", close: -1, volume: -5 },
      { symbol: "7203.T", time: "2026-08-06T04:59:00Z", close: 3000, volume: 100 },
    ],
  });
  assert.equal(result.status, "BLOCKED");
  assert.equal(result.blocked, true);
  assert.ok(result.issues.some((issue) => issue.code === "CROSS_SYMBOL_ROW"));
  assert.ok(result.issues.some((issue) => issue.code === "INVALID_PRICE"));
  assert.ok(result.issues.some((issue) => issue.code === "INVALID_VOLUME"));
  assert.ok(result.issues.some((issue) => issue.code === "DUPLICATE_ROW"));
  assert.throws(() => assertDataQuality(result), /DATA_QUALITY_BLOCKED/);
});

test("creates deterministic dataset hashes and reproducibility fingerprints", () => {
  const input = {
    datasetId: "phase23-demo",
    generatedAt: "2026-08-06T05:00:00Z",
    period: { from: "2024-01-01", to: "2024-12-31" },
    symbols: ["7203.T", "6758.T", "7203.T"],
    featureVersion: "features-v3",
    labelVersion: "labels-v2",
    sourceVersion: "source-v1",
    metadata: { b: 2, a: 1 },
  };
  const first = buildDatasetVersionManifest(input);
  const second = buildDatasetVersionManifest({ ...input, metadata: { a: 1, b: 2 } });
  assert.equal(first.datasetHash, second.datasetHash);
  assert.deepEqual(first.symbols, ["6758.T", "7203.T"]);

  const fp1 = buildReproducibilityFingerprint({ datasetManifest: first, modelVersion: "model-v1", config: { threshold: 0.7 }, output: { score: 80 } });
  const fp2 = buildReproducibilityFingerprint({ datasetManifest: second, modelVersion: "model-v1", config: { threshold: 0.7 }, output: { score: 80 } });
  const comparison = compareReproducibility(fp1, fp2);
  assert.equal(comparison.status, "PASS");
  assert.equal(assertReproducible(comparison), true);
});
