import test from "node:test";
import assert from "node:assert/strict";

import { runRealDataValidation } from "../validation/real-data-validation-v1.js";

function makeRecords(count, symbol = "7203.T") {
  const start = Date.parse("2024-01-01T00:00:00.000Z");
  return Array.from({ length: count }, (_, index) => ({
    symbol,
    timestamp: new Date(start + index * 86_400_000).toISOString(),
    close: 100 + index * 0.2,
    volume: 1000 + index,
  }));
}

const evaluator = async ({ test: testRecords }) => ({
  metrics: {
    accuracy: 65,
    winRate: 62,
    profitFactor: 1.4,
    sharpe: 1.2,
    maxDrawdown: 10,
    cagr: 12,
    averageReturn: 1.1,
    sampleSize: testRecords.length,
  },
  futureLeakChecked: true,
});

test("real data validation produces per-symbol out-of-sample reports", async () => {
  const report = await runRealDataValidation({
    records: makeRecords(260),
    candidateModel: { version: "candidate-1" },
    productionBaseline: {
      modelVersion: "production-1",
      metrics: {
        accuracy: 60,
        winRate: 58,
        profitFactor: 1.1,
        sharpe: 0.8,
        maxDrawdown: 12,
        cagr: 8,
        averageReturn: 0.6,
        sampleSize: 100,
      },
    },
    evaluator,
    splitterOptions: {
      trainingSize: 120,
      validationSize: 20,
      testSize: 20,
      stepSize: 20,
    },
    thresholds: { minimumSampleSize: 20 },
    source: {
      provider: "fixture-provider",
      datasetId: "fixture-2024",
      retrievedAt: "2026-08-05T00:00:00.000Z",
      adjustedPrices: true,
    },
    futureLeakChecked: true,
  });

  assert.equal(report.version, "real-data-validation-v1");
  assert.equal(report.status, "VALIDATED");
  assert.equal(report.ready, true);
  assert.equal(report.dataset.validCount, 260);
  assert.equal(report.summary.evaluatedSymbols, 1);
  assert.equal(report.summary.outOfSampleSymbols, 1);
  assert.equal(report.symbols[0].validation.futureLeakChecked, true);
  assert.equal(report.safety.productionUpdateAllowed, false);
  assert.equal(report.safety.brokerExecutionAllowed, false);
});

test("real data validation blocks unverifiable or dirty datasets", async () => {
  const records = makeRecords(10);
  records.push({ ...records[0] });
  records.push({ symbol: "", timestamp: "invalid", close: -1 });

  const report = await runRealDataValidation({
    records,
    candidateModel: { version: "candidate-1" },
    productionBaseline: {},
    evaluator,
  });

  assert.equal(report.ready, false);
  assert.equal(report.status, "BLOCKED");
  assert.ok(report.blockers.includes("INSUFFICIENT_RECORDS"));
  assert.ok(report.blockers.includes("DUPLICATE_SYMBOL_TIMESTAMP"));
  assert.ok(report.blockers.includes("INVALID_RECORDS_PRESENT"));
  assert.ok(report.blockers.includes("SOURCE_PROVENANCE_REQUIRED"));
});
