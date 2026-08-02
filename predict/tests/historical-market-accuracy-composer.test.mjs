import assert from "node:assert/strict";
import test from "node:test";

import { composeHistoricalMarketAccuracy } from "../market-intelligence/historical-market-accuracy-composer.js";
import { evaluateHistoricalMarketSnapshot } from "../market-intelligence/historical-market-accuracy-engine.js";
import {
  createHistoricalAccuracyHistory,
  createHistoricalAccuracySnapshot,
  historicalAccuracyEvaluationTime,
} from "./historical-market-accuracy-fixture.mjs";

function resolvedReport() {
  return evaluateHistoricalMarketSnapshot({
    snapshot: createHistoricalAccuracySnapshot(),
    history: createHistoricalAccuracyHistory(),
    evaluatedAt: historicalAccuracyEvaluationTime(),
  });
}

test("Composer feeds one resolved evidence set to all learning consumers", () => {
  const report = resolvedReport();
  const generatedAt = historicalAccuracyEvaluationTime();
  const result = composeHistoricalMarketAccuracy({
    evaluationReports: [report],
    generatedAt,
  });

  assert.equal(result.status, "ready");
  assert.equal(result.records.length, 5);
  assert.equal(result.dashboard.summary.total, 5);
  assert.equal(result.walkForward.summary.total, 5);
  assert.equal(result.performance.sampleCount, 5);
  assert.equal(result.weightMetrics.sampleSize, 5);
  assert.equal(result.learningDataset.rows.length, 5);
  assert.equal(
    result.learningDataset.rows[0].audit.historicalMarketSnapshot.id,
    report.snapshot.id,
  );
  assert.equal(result.audit.futureInformationIncluded, false);
  assert.equal(result.executionAllowed, false);
});

test("Composer deduplicates retries and rejects conflicting lineage", () => {
  const report = resolvedReport();
  const duplicate = composeHistoricalMarketAccuracy({
    evaluationReports: [report, report],
    generatedAt: historicalAccuracyEvaluationTime(),
  });

  assert.equal(duplicate.records.length, 5);

  const conflictingRecord = {
    ...report.records[0],
    marketIntelligenceSnapshot: {
      ...report.records[0].marketIntelligenceSnapshot,
      contentFingerprint: "fnv1a32:deadbeef",
    },
  };

  assert.throws(
    () =>
      composeHistoricalMarketAccuracy({
        evaluationReports: [
          report,
          { records: [conflictingRecord] },
        ],
        generatedAt: historicalAccuracyEvaluationTime(),
      }),
    /conflicts with its snapshot fingerprint/,
  );
});

test("Composer cannot reuse outcomes resolved after its cutoff", () => {
  const complete = resolvedReport();
  const snapshot = createHistoricalAccuracySnapshot();
  const cutoff = historicalAccuracyEvaluationTime(4);
  const partial = evaluateHistoricalMarketSnapshot({
    snapshot,
    history: createHistoricalAccuracyHistory(),
    evaluatedAt: cutoff,
  });
  const result = composeHistoricalMarketAccuracy({
    evaluationReports: [partial],
    existingRecords: complete.records,
    generatedAt: cutoff,
  });

  assert.equal(result.resolvedRecords.length, 2);
  assert.equal(result.pendingRecords.length, 3);
  assert.equal(result.audit.excludedFutureRecordCount, 3);
  assert.equal(result.audit.futureInformationIncluded, false);
});
