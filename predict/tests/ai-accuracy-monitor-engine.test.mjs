import assert from "node:assert/strict";
import test from "node:test";

import {
  AIAccuracyMonitorInternals,
  buildAIAccuracyMonitorReport,
} from "../analysis/ai-accuracy-monitor-engine.js";

const START = Date.parse("2026-01-01T00:00:00.000Z");

function record({
  id,
  index = 0,
  source = "live",
  partition = null,
  status = "resolved",
  hit = true,
  period = 1,
  actualReturn = hit === false ? -1 : 1,
  expectedReturn = 0,
  confidence = 70,
  evaluationScope = null,
} = {}) {
  return {
    id: id ?? `record-${index}`,
    source,
    partition,
    status,
    hit,
    period,
    actualReturn,
    expectedReturn,
    confidence: {
      score: confidence,
      isProbability: false,
    },
    evaluationScope,
    createdAt: new Date(START + index * 86_400_000).toISOString(),
    resolvedAt:
      status === "resolved"
        ? new Date(START + index * 86_400_000 + 3_600_000).toISOString()
        : null,
  };
}

test("Observed outcomes take priority over Walk Forward validation", () => {
  const report = buildAIAccuracyMonitorReport(
    [
      record({ index: 1, hit: true }),
      record({ index: 2, hit: false }),
      record({
        index: 3,
        source: "walk-forward",
        partition: "training",
        hit: true,
      }),
      record({
        index: 4,
        source: "walk-forward",
        partition: "validation",
        hit: true,
      }),
      record({
        index: 6,
        source: "legacy-evaluation",
        partition: "training",
        hit: true,
      }),
      record({
        index: 5,
        source: "walk-forward",
        partition: "test",
        hit: true,
      }),
    ],
    { generatedAt: START },
  );

  assert.equal(report.source, "observed");
  assert.equal(report.current.accuracy, 50);
  assert.equal(report.current.sampleCount, 2);
  assert.equal(report.evidence.validation.accuracy, 100);
  assert.equal(report.audit.excludedTrainingValidationCount, 3);
  assert.equal(report.executionAllowed, false);
});

test("Final-test evidence is the fallback and training data never becomes accuracy", () => {
  const report = buildAIAccuracyMonitorReport(
    [
      record({
        index: 1,
        source: "walk-forward",
        partition: "training",
        hit: true,
      }),
      record({
        index: 2,
        source: "walk-forward",
        partition: "validation",
        hit: true,
      }),
      record({
        index: 3,
        source: "walk-forward",
        partition: "test",
        hit: true,
      }),
      record({
        index: 4,
        source: "walk-forward",
        partition: "test",
        hit: false,
      }),
    ],
    { generatedAt: START },
  );

  assert.equal(report.source, "walk-forward-test");
  assert.equal(report.current.sampleCount, 2);
  assert.equal(report.current.accuracy, 50);
  assert.equal(report.evidence.observed.sampleCount, 0);
});

test("Global final-test records are validation evidence", () => {
  const report = buildAIAccuracyMonitorReport(
    [
      record({
        index: 1,
        source: "global-evaluation-v1",
        partition: "test",
        evaluationScope: "global",
        hit: true,
      }),
    ],
    { generatedAt: START },
  );

  assert.equal(report.source, "walk-forward-test");
  assert.equal(report.current.accuracy, 100);
});

test("Current accuracy uses only the latest resolved-record window", () => {
  const records = Array.from({ length: 35 }, (_, index) =>
    record({
      index,
      hit: index >= 5,
    }),
  );
  const report = buildAIAccuracyMonitorReport(records, {
    recentWindow: 30,
    generatedAt: START,
  });

  assert.equal(report.current.sampleCount, 30);
  assert.equal(report.current.accuracy, 100);
  assert.equal(report.allTime.sampleCount, 35);
  assert.ok(report.allTime.accuracy < 86);
  assert.equal(report.status, "ready");
});

test("No actionable evidence is unavailable instead of zero-percent accuracy", () => {
  const report = buildAIAccuracyMonitorReport(
    [
      record({
        index: 1,
        hit: null,
        actualReturn: 0.1,
      }),
    ],
    { generatedAt: START },
  );

  assert.equal(report.source, "none");
  assert.equal(report.current.accuracy, null);
  assert.equal(report.status, "unavailable");
  assert.equal(report.evidence.observed.resolvedCount, 1);
  assert.equal(report.evidence.observed.coverageRate, 0);
});

test("Horizon, forecast error, calibration, pending and deduplication are audited", () => {
  const pending = record({
    id: "duplicate",
    index: 1,
    status: "pending",
    hit: null,
    actualReturn: null,
  });
  const resolved = record({
    id: "duplicate",
    index: 2,
    period: 5,
    hit: true,
    actualReturn: 3,
    expectedReturn: 1,
    confidence: 80,
  });
  const second = record({
    id: "second",
    index: 3,
    period: 20,
    hit: false,
    actualReturn: -2,
    expectedReturn: -1,
    confidence: 60,
  });
  const pendingUnique = record({
    id: "pending",
    index: 4,
    status: "pending",
    hit: null,
    actualReturn: null,
  });
  const input = [pending, resolved, second, pendingUnique];
  const before = structuredClone(input);
  const report = buildAIAccuracyMonitorReport(input, {
    generatedAt: START,
  });

  assert.equal(report.audit.duplicateRecordCount, 1);
  assert.equal(report.audit.pendingCount, 1);
  assert.equal(report.horizons.find((item) => item.horizon === 5).accuracy, 100);
  assert.equal(report.horizons.find((item) => item.horizon === 20).accuracy, 0);
  assert.equal(report.forecastError.count, 2);
  assert.equal(report.forecastError.meanAbsoluteError, 1.5);
  assert.equal(report.calibration.count, 2);
  assert.equal(report.audit.futureInformationIncluded, false);
  assert.deepEqual(input, before);
});

test("Reliability levels depend on evaluated sample count", () => {
  assert.equal(AIAccuracyMonitorInternals.reliabilityFor(0).code, "no-data");
  assert.equal(AIAccuracyMonitorInternals.reliabilityFor(5).code, "very-low");
  assert.equal(AIAccuracyMonitorInternals.reliabilityFor(20).code, "low");
  assert.equal(AIAccuracyMonitorInternals.reliabilityFor(50).code, "medium");
  assert.equal(AIAccuracyMonitorInternals.reliabilityFor(100).code, "high");
});

test("Non-array accuracy input is rejected", () => {
  assert.throws(
    () => buildAIAccuracyMonitorReport(null),
    /must be an array/,
  );
});
