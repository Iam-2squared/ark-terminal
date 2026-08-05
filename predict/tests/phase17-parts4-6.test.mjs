import test from "node:test";
import assert from "node:assert/strict";

import { analyzeWeaknessV1 } from "../validation/weakness-analysis-v1.js";
import { optimizeCandidatesV1 } from "../optimization/candidate-optimizer-v1.js";
import { buildValidationReleaseV1 } from "../release/validation-release-v1.js";

test("weakness analysis finds weak segments and overconfidence", () => {
  const records = Array.from({ length: 10 }, (_, index) => ({
    correct: index < 4,
    confidence: 80,
    symbol: "7203.T",
    sector: "AUTO",
    regime: "BEAR",
    action: index < 2 ? "NO_TRADE" : "BUY",
  }));
  const result = analyzeWeaknessV1({ records });
  assert.equal(result.status, "READY");
  assert.ok(result.weakSegments.length > 0);
  assert.ok(result.overconfidentBands.length > 0);
  assert.equal(result.productionUpdateAllowed, false);
});

test("candidate optimizer rejects overfit and keeps approval gate", () => {
  const result = optimizeCandidatesV1({
    production: { accuracy: 0.55, profitFactor: 1.1, sharpe: 0.7, expectedValue: 0.002, maxDrawdown: 0.12, calibrationError: 0.12 },
    candidates: [
      {
        id: "candidate-a",
        parameters: { threshold: 0.65 },
        inSample: { accuracy: 0.62, profitFactor: 1.4, sharpe: 1.1, expectedValue: 0.006, maxDrawdown: 0.09, calibrationError: 0.08 },
        outOfSample: { accuracy: 0.6, profitFactor: 1.3, sharpe: 1.0, expectedValue: 0.005, maxDrawdown: 0.1, calibrationError: 0.09, sampleSize: 150 },
      },
      {
        id: "overfit",
        inSample: { accuracy: 0.9, profitFactor: 3, sharpe: 3, expectedValue: 0.05, maxDrawdown: 0.02 },
        outOfSample: { accuracy: 0.45, profitFactor: 0.8, sharpe: 0.2, expectedValue: -0.01, maxDrawdown: 0.25, sampleSize: 40 },
      },
    ],
  });
  assert.equal(result.bestCandidate.id, "candidate-a");
  assert.ok(result.candidates.find((row) => row.id === "overfit").overfitRisk);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.humanApprovalRequired, true);
});

test("validation release requires all checks and approval gate", () => {
  const result = buildValidationReleaseV1({
    historical: { status: "READY", metadata: { rowCount: 1000, symbolCount: 10, futureLeakDetected: false } },
    backtest: { status: "READY", futureLeakDetected: false, overall: { sampleSize: 200 } },
    benchmark: { status: "READY", classification: { accuracy: 0.58 } },
    weakness: { status: "READY", weakSegments: [] },
    optimization: {
      status: "READY",
      bestCandidate: { id: "candidate-a" },
      automaticPromotionAllowed: false,
      humanApprovalRequired: true,
    },
  });
  assert.equal(result.status, "READY_FOR_REVIEW");
  assert.equal(result.blockers.length, 0);
  assert.equal(result.productionUpdateAllowed, false);
});
