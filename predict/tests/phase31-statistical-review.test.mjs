import test from "node:test";
import assert from "node:assert/strict";

import {
  bootstrapCandidateAdvantage,
  evaluateRegimeStability,
  buildCandidateReviewDashboard,
  runPhase31StatisticalReview,
} from "../forward/phase31-statistical-review.js";

function pair(regime, championReturn, candidateReturn) {
  return {
    champion: { netReturn: championReturn, regime },
    candidate: { netReturn: candidateReturn, regime },
  };
}

const strongRun = {
  runId: "phase31-strong",
  pairs: [
    ...Array.from({ length: 12 }, () => pair("BULL", 0.001, 0.012)),
    ...Array.from({ length: 12 }, () => pair("BEAR", -0.012, -0.001)),
  ],
};

const comparison = {
  pairedSamples: 24,
  champion: { averageNetReturn: -0.0055 },
  candidate: { averageNetReturn: 0.0055 },
  deltas: { averageNetReturn: 0.011 },
  blockers: [],
};

test("bootstrap estimates candidate advantage without enabling promotion", () => {
  const result = bootstrapCandidateAdvantage(strongRun, { iterations: 500, seed: 7 });
  assert.equal(result.status, "READY");
  assert.equal(result.statisticallyPositive, true);
  assert.equal(result.safety.automaticPromotionAllowed, false);
});

test("regime review requires enough samples in every known regime", () => {
  const result = evaluateRegimeStability({ pairs: [pair("BULL", 0, 0.01)] }, { minSamplesPerRegime: 2 });
  assert.equal(result.status, "CONTINUE_FORWARD_TEST");
  assert.ok(result.blockers.includes("INSUFFICIENT_REGIME_SAMPLES"));
});

test("dashboard stops at human review even when every statistical gate passes", () => {
  const bootstrap = bootstrapCandidateAdvantage(strongRun, { iterations: 500, seed: 7 });
  const regimeStability = evaluateRegimeStability(strongRun, { minSamplesPerRegime: 10 });
  const dashboard = buildCandidateReviewDashboard({ run: strongRun, comparison, bootstrap, regimeStability });
  assert.equal(dashboard.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(dashboard.promotionAllowed, false);
  assert.equal(dashboard.productionUpdateAllowed, false);
  assert.equal(dashboard.humanApprovalRequired, true);
});

test("full statistical runner remains review-only with zero broker activity", () => {
  const result = runPhase31StatisticalReview({
    run: strongRun,
    comparison,
    options: {
      bootstrap: { iterations: 500, seed: 7 },
      regime: { minSamplesPerRegime: 10 },
    },
  });
  assert.equal(result.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.brokerWrites, 0);
  assert.equal(result.liveOrders, 0);
});
