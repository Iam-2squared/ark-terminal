import test from "node:test";
import assert from "node:assert/strict";

import {
  createModelPerformanceViewModel,
} from "../analysis/model-performance-ui-v1.js";

test("Part4 creates a truthful empty UI state without invented metrics", () => {
  const view = createModelPerformanceViewModel();

  assert.equal(view.hasData, false);
  assert.equal(view.productionVersion, null);
  assert.equal(view.candidateVersion, null);
  assert.equal(view.productionMetrics.accuracy, null);
  assert.equal(view.candidateMetrics.accuracy, null);
  assert.ok(view.warnings.includes("PRODUCTION_BASELINE_NOT_AVAILABLE"));
  assert.ok(view.warnings.includes("CANDIDATE_VALIDATION_NOT_AVAILABLE"));
  assert.equal(view.safety.productionUpdateAllowed, false);
  assert.equal(view.safety.brokerExecutionAllowed, false);
  assert.equal(view.safety.humanApprovalRequired, true);
});

test("Part4 exposes Production and selected Candidate metrics with validation gates", () => {
  const view = createModelPerformanceViewModel({
    baseline: {
      productionModelVersion: "production-v1",
      overall: {
        accuracy: 55,
        profitFactor: 1.2,
        sharpe: 0.8,
        maxDrawdown: 12,
        averageReturn: 0.4,
        count: 120,
      },
    },
    validation: {
      candidateVersion: "candidate-v2",
      status: "PROMOTABLE_REQUIRES_HUMAN_APPROVAL",
      futureLeakChecked: true,
      outOfSample: true,
      candidateMetrics: {
        accuracy: 61,
        profitFactor: 1.6,
        sharpe: 1.2,
        maxDrawdown: 9,
        averageReturn: 0.9,
        sampleSize: 160,
      },
      warnings: [],
    },
    selection: {
      status: "CANDIDATE_SELECTED_REQUIRES_HUMAN_APPROVAL",
      selectedCandidate: {
        version: "candidate-v2",
        metrics: { accuracy: 61 },
      },
      safety: {
        humanApprovalRequired: true,
        productionUpdateAllowed: false,
        brokerExecutionAllowed: false,
      },
    },
  });

  assert.equal(view.hasData, true);
  assert.equal(view.productionVersion, "production-v1");
  assert.equal(view.candidateVersion, "candidate-v2");
  assert.equal(view.productionMetrics.accuracy, 55);
  assert.equal(view.productionMetrics.sampleSize, 120);
  assert.equal(view.candidateMetrics.accuracy, 61);
  assert.equal(view.candidateMetrics.sampleSize, 160);
  assert.equal(view.futureLeakChecked, true);
  assert.equal(view.outOfSample, true);
  assert.equal(view.selectionStatus, "CANDIDATE_SELECTED_REQUIRES_HUMAN_APPROVAL");
  assert.equal(view.safety.productionUpdateAllowed, false);
  assert.equal(view.safety.brokerExecutionAllowed, false);
});

test("Part4 never treats missing safety fields as permission", () => {
  const view = createModelPerformanceViewModel({
    selection: {
      selectedCandidate: { version: "candidate-v3" },
      safety: {},
    },
  });

  assert.equal(view.safety.productionUpdateAllowed, false);
  assert.equal(view.safety.brokerExecutionAllowed, false);
  assert.equal(view.safety.humanApprovalRequired, true);
});
