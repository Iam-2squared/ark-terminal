import test from "node:test";
import assert from "node:assert/strict";

import {
  buildPhase32CandidateSpecification,
  buildPhase32RevalidationPlan,
  buildPhase32RevalidationDashboard,
  applyPhase32HumanReviewGate,
  runPhase32CandidateRevalidation,
} from "../learning/phase32-candidate-revalidation.js";

const proposal = {
  type: "REVIEW_CONFIDENCE_CALIBRATION",
  scope: "CONFIDENCE_BIN",
  target: "0.8-1",
  rationale: "calibrationGap=0.220",
  candidatePatchCreated: false,
  productionChangeAllowed: false,
  humanReviewRequired: true,
};

const forwardContract = {
  outOfSample: true,
  paperOnly: true,
  futureLeakCheckPassed: true,
  sameDataContract: true,
  sameCostContract: true,
  sameHoldingPeriodContract: true,
};

const phase31Result = {
  status: "READY_FOR_HUMAN_REVIEW",
  comparison: {
    pairedSamples: 50,
    champion: { averageNetReturn: 0.01 },
    candidate: { averageNetReturn: 0.015 },
    deltas: { averageNetReturn: 0.005 },
    blockers: [],
  },
  statisticalReview: {
    blockers: [],
    bootstrap: { probabilityCandidateBetter: 0.91 },
    regimeStability: { status: "STABLE" },
  },
};

test("builds specification only and never creates candidate code", () => {
  const spec = buildPhase32CandidateSpecification({ proposal, metadata: { specificationId: "spec-1" } });
  assert.equal(spec.specificationId, "spec-1");
  assert.equal(spec.status, "SPECIFICATION_ONLY");
  assert.equal(spec.candidateCodeCreated, false);
  assert.equal(spec.candidateModelCreated, false);
  assert.equal(spec.productionChangeAllowed, false);
  assert.equal(spec.safety.liveTradingAllowed, false);
});

test("blocks unsafe prebuilt patch proposal", () => {
  assert.throws(() => buildPhase32CandidateSpecification({
    proposal: { ...proposal, candidatePatchCreated: true },
  }), /BLOCKED_PREBUILT_CANDIDATE_PATCH/);
});

test("requires strict Phase31 forward contract", () => {
  const spec = buildPhase32CandidateSpecification({ proposal });
  const plan = buildPhase32RevalidationPlan({
    specification: spec,
    forwardContract: { ...forwardContract, outOfSample: false },
  });
  assert.equal(plan.status, "BLOCKED");
  assert.ok(plan.blockers.includes("FORWARD_CONTRACT_OUTOFSAMPLE_REQUIRED"));
});

test("dashboard reaches human review only after clean Phase31 result", () => {
  const spec = buildPhase32CandidateSpecification({ proposal });
  const plan = buildPhase32RevalidationPlan({ specification: spec, forwardContract });
  const dashboard = buildPhase32RevalidationDashboard({ specification: spec, plan, phase31Result });
  assert.equal(dashboard.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(dashboard.promotionAllowed, false);
  assert.equal(dashboard.productionUpdateAllowed, false);
});

test("human gate blocks absent approval", () => {
  const spec = buildPhase32CandidateSpecification({ proposal });
  const plan = buildPhase32RevalidationPlan({ specification: spec, forwardContract });
  const dashboard = buildPhase32RevalidationDashboard({ specification: spec, plan, phase31Result });
  const gate = applyPhase32HumanReviewGate({ dashboard, approval: { reviewed: false, approved: false } });
  assert.equal(gate.status, "BLOCKED");
  assert.equal(gate.automaticPromotionAllowed, false);
});

test("full runner remains manual registration only with zero broker activity", () => {
  const result = runPhase32CandidateRevalidation({
    proposal,
    forwardContract,
    phase31Result,
    approval: { reviewed: true, approved: true },
  });
  assert.equal(result.status, "APPROVED_FOR_MANUAL_CANDIDATE_REGISTRATION");
  assert.equal(result.automaticCandidateCreationAllowed, false);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.brokerWrites, 0);
  assert.equal(result.liveOrders, 0);
});
