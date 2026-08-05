import test from "node:test";
import assert from "node:assert/strict";

import { createPredictionLabFinalViewModel } from "../analysis/prediction-lab-final-v1.js";

test("prediction lab final exposes analysis and safe candidate comparison", () => {
  const view = createPredictionLabFinalViewModel({
    analysis: {
      aiScore: 78,
      confidence: 84,
      risk: "中",
      direction: "BUY",
    },
    baseline: {
      metrics: {
        accuracy: 61,
        profitFactor: 1.12,
        sharpe: 0.8,
        maxDrawdown: 14,
        sampleSize: 120,
      },
    },
    candidate: {
      metrics: {
        accuracy: 65,
        profitFactor: 1.31,
        sharpe: 1.08,
        maxDrawdown: 12,
        sampleSize: 140,
      },
      outOfSample: true,
      futureLeakChecked: true,
    },
  });

  assert.equal(view.state, "ready");
  assert.equal(view.summary.score, 78);
  assert.equal(view.hasComparison, true);
  assert.equal(view.candidate.productionUpdateAllowed, false);
  assert.equal(view.candidate.humanApprovalRequired, true);
  assert.equal(view.mobileReady, true);
});

test("prediction lab final reports loading and error states", () => {
  assert.equal(createPredictionLabFinalViewModel({ loading: true }).state, "loading");
  assert.equal(createPredictionLabFinalViewModel({ error: new Error("failed") }).state, "error");
});
