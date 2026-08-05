import test from "node:test";
import assert from "node:assert/strict";

import {
  auditPhase11Release,
} from "../validation/phase11-release-audit-v1.js";

function validArtifacts() {
  return {
    baseline: {
      version: "model-performance-baseline-v1",
      overall: { sampleSize: 120 },
    },
    validation: {
      version: "backtest-forward-validation-v2",
      outOfSample: true,
      futureLeakChecked: true,
      comparison: { promotable: true },
      safety: {
        humanApprovalRequired: true,
        productionUpdateAllowed: false,
        brokerExecutionAllowed: false,
      },
    },
    selection: {
      version: "model-selection-v1",
      status: "CANDIDATE_SELECTED_REQUIRES_HUMAN_APPROVAL",
      selectedCandidate: { version: "candidate-v2" },
      safety: {
        humanApprovalRequired: true,
        productionUpdateAllowed: false,
        brokerExecutionAllowed: false,
      },
    },
    ui: {
      version: "model-performance-ui-v1",
      safety: {
        humanApprovalRequired: true,
        productionUpdateAllowed: false,
        brokerExecutionAllowed: false,
      },
    },
  };
}

test("Part5 marks a complete and safety-locked Phase11 bundle release ready", () => {
  const report = auditPhase11Release(validArtifacts());

  assert.equal(report.status, "RELEASE_READY");
  assert.equal(report.releaseReady, true);
  assert.equal(report.modelPromotionEligible, true);
  assert.deepEqual(report.failedChecks, []);
  assert.equal(report.safety.humanApprovalRequired, true);
  assert.equal(report.safety.productionUpdateAllowed, false);
  assert.equal(report.safety.brokerExecutionAllowed, false);
});

test("Part5 blocks release when future-leak validation is missing", () => {
  const artifacts = validArtifacts();
  artifacts.validation.futureLeakChecked = false;

  const report = auditPhase11Release(artifacts);

  assert.equal(report.status, "RELEASE_BLOCKED");
  assert.equal(report.releaseReady, false);
  assert.equal(report.modelPromotionEligible, false);
  assert.ok(report.failedChecks.includes("FUTURE_LEAK_CHECK_CONFIRMED"));
});

test("Part5 blocks release when any layer enables Production or broker execution", () => {
  const artifacts = validArtifacts();
  artifacts.selection.safety.productionUpdateAllowed = true;
  artifacts.ui.safety.brokerExecutionAllowed = true;

  const report = auditPhase11Release(artifacts);

  assert.equal(report.releaseReady, false);
  assert.ok(report.failedChecks.includes("SELECTION_PRODUCTION_UPDATE_DISABLED"));
  assert.ok(report.failedChecks.includes("UI_BROKER_EXECUTION_DISABLED"));
  assert.equal(report.safety.productionUpdateAllowed, false);
  assert.equal(report.safety.brokerExecutionAllowed, false);
});

test("Part5 separates feature release readiness from model promotion", () => {
  const artifacts = validArtifacts();
  artifacts.validation.comparison.promotable = false;
  artifacts.selection.selectedCandidate = null;
  artifacts.selection.status = "NO_ELIGIBLE_CANDIDATE";

  const report = auditPhase11Release(artifacts);

  assert.equal(report.releaseReady, true);
  assert.equal(report.modelPromotionEligible, false);
  assert.equal(report.status, "RELEASE_READY");
});

test("Part5 fails closed when artifacts are absent", () => {
  const report = auditPhase11Release();

  assert.equal(report.releaseReady, false);
  assert.equal(report.modelPromotionEligible, false);
  assert.ok(report.failedChecks.includes("BASELINE_REPORT_PRESENT"));
  assert.ok(report.failedChecks.includes("VALIDATION_REPORT_PRESENT"));
  assert.ok(report.failedChecks.includes("SELECTION_REPORT_PRESENT"));
  assert.ok(report.failedChecks.includes("UI_CONTRACT_PRESENT"));
});
