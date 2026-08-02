import assert from "node:assert/strict";
import test from "node:test";

import { DEFAULT_WEIGHTS } from "../config.js";
import { buildResolvedFeedback } from "../learning/resolved-feedback-service.js";

function record(index, { status = "resolved" } = {}) {
  return {
    id: `record-${index}`,
    symbol: "7203.T",
    status,
    createdAt: new Date(Date.UTC(2025, 0, index + 1)).toISOString(),
    analysisTime: Date.UTC(2025, 0, index + 1),
    resolvedAt: new Date(Date.UTC(2025, 0, index + 2)).toISOString(),
    period: 1,
    score: 80,
    predictionPrice: 100,
    actualReturn: 2,
    strategyReturn: 1.7,
    hit: true,
    actualLabel: "上昇",
    confidence: { score: 80 },
    factorScores: Object.fromEntries(
      Object.keys(DEFAULT_WEIGHTS).map((key) => [key, 80]),
    ),
  };
}

test("Resolved feedback creates learning rows and optimizer candidates", () => {
  const records = Array.from({ length: 60 }, (_, index) => record(index));
  const report = buildResolvedFeedback({
    records,
    currentWeights: DEFAULT_WEIGHTS,
    generatedAt: "2026-08-03T00:00:00.000Z",
  });

  assert.equal(report.status, "candidate_ready");
  assert.equal(report.learningDataset.rows.length, 60);
  assert.equal(report.weightCandidate.updated, true);
  assert.equal(report.weightCandidate.applied, false);
  assert.equal(report.weightCandidate.humanApprovalRequired, true);
  assert.equal(report.marketFeatureCandidate.applied, false);
  assert.equal(report.audit.futureInformationIncluded, false);
  assert.equal(report.audit.activeWeightsChanged, false);
  assert.equal(report.promotionGate.eligible, true);
  assert.equal(report.promotionGate.promotionAllowed, false);
  assert.equal(report.executionAllowed, false);
});

test("Small resolved sample is retained for learning without changing weights", () => {
  const report = buildResolvedFeedback({
    records: [record(0), record(1), record(2, { status: "pending" })],
    currentWeights: DEFAULT_WEIGHTS,
  });

  assert.equal(report.status, "collecting");
  assert.equal(report.learningDataset.rows.length, 2);
  assert.equal(report.weightCandidate.updated, false);
  assert.equal(report.weightCandidate.sampleCount, 2);
  assert.equal(report.weightCandidate.required, 60);
  assert.equal(report.promotionGate.eligible, false);
});

test("Resolved feedback identity is stable for the same evidence", () => {
  const records = [record(0), record(1)];
  const first = buildResolvedFeedback({ records, currentWeights: DEFAULT_WEIGHTS });
  const second = buildResolvedFeedback({ records, currentWeights: DEFAULT_WEIGHTS });
  assert.equal(first.id, second.id);
});
