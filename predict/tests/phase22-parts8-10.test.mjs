import assert from "node:assert/strict";
import test from "node:test";

import { buildCandidateReview } from "../analysis/candidate-review.js";
import { assessModelHealth } from "../analysis/model-health.js";
import { runPaperForwardCycle } from "../forward/paper-forward-orchestrator.js";

test("Phase22 Part8 candidate review blocks unsafe promotion and never executes it", () => {
  const review = buildCandidateReview({
    champion: {
      version: "champion-v1",
      sampleCount: 500,
      profitFactor: 1.25,
      maxDrawdown: 8,
      calibrationError: 0.05,
      sharpe: 1.1,
    },
    candidate: {
      version: "candidate-v2",
      sampleCount: 120,
      profitFactor: 1.4,
      maxDrawdown: 7,
      calibrationError: 0.04,
      sharpe: 1.3,
      forwardSessions: 20,
      futureLeakChecked: false,
      dataQualityPassed: true,
      driftStatus: "HEALTHY",
    },
  });

  assert.equal(review.recommendation, "REJECT");
  assert.ok(review.blockers.includes("FUTURE_LEAK_NOT_VERIFIED"));
  assert.ok(review.blockers.includes("INSUFFICIENT_SAMPLE"));
  assert.equal(review.promotionExecuted, false);
  assert.equal(review.safety.automaticPromotionAllowed, false);
  assert.equal(review.safety.brokerWriteAllowed, false);
});

test("Phase22 Part8 can mark a candidate for human review without promotion", () => {
  const review = buildCandidateReview({
    champion: {
      version: "champion-v1",
      sampleCount: 500,
      profitFactor: 1.25,
      maxDrawdown: 8,
      calibrationError: 0.05,
      sharpe: 1.1,
    },
    candidate: {
      version: "candidate-v2",
      sampleCount: 420,
      profitFactor: 1.5,
      maxDrawdown: 7,
      calibrationError: 0.04,
      sharpe: 1.3,
      forwardSessions: 80,
      futureLeakChecked: true,
      dataQualityPassed: true,
      driftStatus: "HEALTHY",
    },
  });

  assert.equal(review.recommendation, "PROMOTE_REVIEW");
  assert.equal(review.promotionReadyForHumanReview, true);
  assert.equal(review.promotionExecuted, false);
  assert.equal(review.safety.humanApprovalRequired, true);
});

test("Phase22 Part9 model health blocks missing future-leak and data-quality checks", () => {
  const health = assessModelHealth({
    metrics: {
      sampleCount: 500,
      profitFactor: 1.4,
      maxDrawdown: 5,
      calibrationError: 0.04,
    },
    diagnostics: {
      futureLeakChecked: false,
      dataQualityPassed: false,
      apiHealthy: true,
      rssHealthy: true,
      driftStatus: "HEALTHY",
    },
  });

  assert.equal(health.status, "BLOCKED");
  assert.equal(health.paperForwardTestAllowed, false);
  assert.equal(health.semiAutomaticTradingAllowed, false);
  assert.equal(health.automaticTradingAllowed, false);
});

test("Phase22 Part9 model health reports healthy verified paper operation", () => {
  const health = assessModelHealth({
    metrics: {
      sampleCount: 500,
      profitFactor: 1.4,
      maxDrawdown: 5,
      calibrationError: 0.04,
    },
    diagnostics: {
      futureLeakChecked: true,
      dataQualityPassed: true,
      apiHealthy: true,
      rssHealthy: true,
      driftStatus: "HEALTHY",
      pendingRatio: 0.1,
    },
  });

  assert.equal(health.status, "HEALTHY");
  assert.equal(health.paperForwardTestAllowed, true);
  assert.equal(health.safety.liveTradingAllowed, false);
});

test("Phase22 Part10 runs only injected paper dependencies and records zero broker writes", async () => {
  const calls = [];
  const dependencies = {
    async getMarketSnapshot(input) {
      calls.push(["snapshot", input.safety.mode]);
      return { source: "paper-market" };
    },
    async generatePredictions(input) {
      calls.push(["predict", input.safety.executionAllowed]);
      return [{ symbol: "7203.T", signal: "BUY" }];
    },
    async savePredictions(input) {
      calls.push(["save-predictions", input.predictions.length]);
      return { saved: 1 };
    },
    async resolveOutcomes(input) {
      calls.push(["resolve", input.horizons.join(",")]);
      return [];
    },
    async saveOutcomes(input) {
      calls.push(["save-outcomes", input.outcomes.length]);
      return { saved: 0 };
    },
    async refreshDashboard() {
      calls.push(["dashboard"]);
      return { version: "accuracy-dashboard-v6" };
    },
    async compareCandidate(input) {
      calls.push(["candidate", input.safety.automaticPromotionAllowed]);
      return { recommendation: "KEEP" };
    },
  };

  const result = await runPaperForwardCycle({
    marketDate: "2026-08-06",
    symbols: ["7203.t"],
    dependencies,
  });

  assert.equal(result.symbols[0], "7203.T");
  assert.deepEqual(result.horizons, [1, 3, 5, 10, 20]);
  assert.equal(result.sideEffects.brokerWrites, 0);
  assert.equal(result.sideEffects.liveOrders, 0);
  assert.equal(result.sideEffects.productionUpdates, 0);
  assert.equal(result.sideEffects.automaticPromotions, 0);
  assert.equal(result.safety.orderCreationAllowed, false);
  assert.deepEqual(calls.map(([name]) => name), [
    "snapshot",
    "predict",
    "save-predictions",
    "resolve",
    "save-outcomes",
    "dashboard",
    "candidate",
  ]);
});
