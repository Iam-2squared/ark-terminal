import test from "node:test";
import assert from "node:assert/strict";

import { runBacktestForwardValidation } from "../validation/backtest-forward-validation-v1.js";
import { selectProductionCandidate } from "../validation/model-selection-v1.js";

function records(count = 180) {
  return Array.from({ length: count }, (_, index) => ({
    timestamp: new Date(Date.UTC(2020, 0, index + 1)).toISOString(),
    value: index,
  }));
}

const productionBaseline = {
  modelVersion: "production-v1",
  overall: {
    accuracy: 55,
    winRate: 55,
    profitFactor: 1.2,
    sharpe: 0.8,
    maxDrawdown: 12,
    cagr: 8,
    averageReturn: 0.4,
    sampleSize: 120,
  },
};

test("Part2 integrates walk-forward and forward metrics without production updates", async () => {
  const result = await runBacktestForwardValidation({
    records: records(),
    candidateModel: { version: "candidate-v2" },
    productionBaseline,
    futureLeakChecked: true,
    splitterOptions: {
      trainingSize: 100,
      validationSize: 20,
      testSize: 20,
      stepSize: 20,
    },
    evaluator: ({ test: testRows }) => ({
      futureLeakChecked: true,
      metrics: {
        accuracy: 60,
        winRate: 60,
        profitFactor: 1.5,
        sharpe: 1.1,
        maxDrawdown: 10,
        cagr: 11,
        averageReturn: 0.8,
        sampleSize: testRows.length,
      },
    }),
    forwardMetrics: {
      accuracy: 61,
      winRate: 61,
      profitFactor: 1.6,
      sharpe: 1.2,
      maxDrawdown: 9,
      cagr: 12,
      averageReturn: 0.9,
      sampleSize: 80,
    },
    thresholds: { minimumSampleSize: 100 },
  });

  const diagnostic = JSON.stringify({
    windowCount: result.windowCount,
    futureLeakChecked: result.futureLeakChecked,
    outOfSample: result.outOfSample,
    candidateMetrics: result.candidateMetrics,
    productionMetrics: result.productionMetrics,
    comparison: result.comparison,
    warnings: result.warnings,
  });
  assert.ok(result.windowCount > 0, diagnostic);
  assert.equal(result.futureLeakChecked, true, diagnostic);
  assert.equal(result.outOfSample, true, diagnostic);
  assert.equal(result.comparison.promotable, true, diagnostic);
  assert.equal(result.status, "PROMOTABLE_REQUIRES_HUMAN_APPROVAL", diagnostic);
  assert.equal(result.safety.productionUpdateAllowed, false);
  assert.equal(result.safety.humanApprovalRequired, true);
});

test("Part2 blocks candidate when future leak validation is missing", async () => {
  const result = await runBacktestForwardValidation({
    records: records(),
    candidateModel: { version: "candidate-v3" },
    productionBaseline,
    futureLeakChecked: false,
    splitterOptions: { trainingSize: 100, validationSize: 20, testSize: 20, stepSize: 20 },
    evaluator: () => ({
      metrics: {
        accuracy: 70,
        profitFactor: 2,
        sharpe: 2,
        maxDrawdown: 5,
        sampleSize: 120,
      },
    }),
  });

  assert.equal(result.status, "NOT_PROMOTABLE");
  assert.ok(result.warnings.includes("FUTURE_LEAK_CHECK_REQUIRED"));
});

test("Part3 selects the best eligible candidate and still requires human approval", () => {
  const candidateA = {
    version: "candidate-a",
    validation: {
      futureLeakChecked: true,
      outOfSample: true,
      comparison: { promotable: true },
      candidateMetrics: {
        accuracy: 60,
        profitFactor: 1.5,
        sharpe: 1.1,
        maxDrawdown: 10,
        averageReturn: 0.8,
        sampleSize: 150,
      },
    },
  };
  const candidateB = {
    version: "candidate-b",
    validation: {
      futureLeakChecked: true,
      outOfSample: true,
      comparison: { promotable: true },
      candidateMetrics: {
        accuracy: 63,
        profitFactor: 1.7,
        sharpe: 1.3,
        maxDrawdown: 8,
        averageReturn: 1.0,
        sampleSize: 160,
      },
    },
  };
  const rejected = {
    version: "candidate-leaky",
    validation: {
      futureLeakChecked: false,
      outOfSample: true,
      comparison: { promotable: true },
      candidateMetrics: {
        accuracy: 90,
        profitFactor: 4,
        sharpe: 4,
        maxDrawdown: 2,
        averageReturn: 4,
        sampleSize: 500,
      },
    },
  };

  const result = selectProductionCandidate({
    candidates: [candidateA, rejected, candidateB],
    productionBaseline,
  });

  assert.equal(result.selectedCandidate.version, "candidate-b");
  assert.equal(result.status, "CANDIDATE_SELECTED_REQUIRES_HUMAN_APPROVAL");
  assert.equal(result.safety.productionUpdateAllowed, false);
  assert.equal(result.safety.humanApprovalRequired, true);
  assert.ok(result.ranked.find((item) => item.version === "candidate-leaky").reasons.includes("FUTURE_LEAK_CHECK_REQUIRED"));
});

test("Part3 returns no candidate when validation conditions fail", () => {
  const result = selectProductionCandidate({
    candidates: [{
      version: "candidate-small",
      validation: {
        futureLeakChecked: true,
        outOfSample: true,
        comparison: { promotable: true },
        candidateMetrics: { accuracy: 80, sampleSize: 20 },
      },
    }],
    productionBaseline,
  });

  assert.equal(result.selectedCandidate, null);
  assert.equal(result.status, "NO_ELIGIBLE_CANDIDATE");
});
