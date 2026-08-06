import assert from "node:assert/strict";
import test from "node:test";

import { validateStrategyStatistics } from "../strategy/statistical-validation.js";
import { evaluateCandidateRejection } from "../strategy/candidate-rejection.js";
import { buildStrategyEnsemble } from "../strategy/strategy-ensemble.js";

test("statistical validation passes deterministic positive out-of-sample returns", () => {
  const rows = Array.from({ length: 40 }, (_, index) => ({ netReturn: 0.4 + (index % 4) * 0.1 }));
  const result = validateStrategyStatistics(rows, {
    minimumSample: 30,
    bootstrapIterations: 200,
    seed: 24,
    outOfSample: true,
    walkForwardPassed: true,
    futureLeakChecked: true,
    trainingAverageReturn: 0.7,
    outOfSampleAverageReturn: 0.55,
  });
  assert.equal(result.status, "PASS");
  assert.deepEqual(result.blockers, []);
  assert.ok(result.bootstrap.lower > 0);
  assert.equal(result.safety.automaticPromotionAllowed, false);
});

test("statistical validation rejects weak and incomplete evidence", () => {
  const result = validateStrategyStatistics([{ netReturn: -1 }, { netReturn: 0.1 }], {
    minimumSample: 30,
    bootstrapIterations: 100,
    outOfSample: false,
    walkForwardPassed: false,
    futureLeakChecked: false,
  });
  assert.equal(result.status, "REJECT");
  assert.ok(result.blockers.includes("INSUFFICIENT_SAMPLE"));
  assert.ok(result.blockers.includes("OUT_OF_SAMPLE_REQUIRED"));
  assert.ok(result.blockers.includes("WALK_FORWARD_FAILED"));
  assert.ok(result.blockers.includes("FUTURE_LEAK_CHECK_REQUIRED"));
});

test("candidate gate only auto-rejects and never auto-promotes", () => {
  const kept = evaluateCandidateRejection({
    sampleCount: 200,
    profitFactor: 1.4,
    maxDrawdown: 7,
    calibrationError: 0.05,
    symbolConcentration: 0.2,
    industryConcentration: 0.25,
    futureLeakChecked: true,
    dataQualityPassed: true,
    outOfSamplePassed: true,
    walkForwardPassed: true,
  });
  assert.equal(kept.decision, "KEEP_FOR_HUMAN_REVIEW");
  assert.equal(kept.safety.automaticPromotionAllowed, false);
  assert.equal(kept.safety.humanApprovalRequired, true);

  const rejected = evaluateCandidateRejection({
    sampleCount: 20,
    profitFactor: 0.8,
    maxDrawdown: 15,
    calibrationError: 0.2,
    symbolConcentration: 0.8,
    industryConcentration: 0.7,
    futureLeakChecked: false,
    dataQualityStatus: "BLOCKED",
    outOfSamplePassed: false,
    walkForwardPassed: false,
  });
  assert.equal(rejected.decision, "REJECT");
  assert.ok(rejected.blockers.includes("DATA_QUALITY_BLOCKED"));
  assert.equal(rejected.safety.brokerWriteAllowed, false);
});

test("ensemble requires agreement confidence liquidity cost and risk gates", () => {
  const ready = buildStrategyEnsemble([
    { action: "BUY", confidence: 0.9, weight: 1 },
    { action: "BUY", confidence: 0.8, weight: 1 },
    { action: "SELL", confidence: 0.7, weight: 0.5 },
  ], {
    marketRegime: "BULL",
    marketRegimeSupported: true,
    liquidityStatus: "PASS",
    costStatus: "PASS",
    riskStatus: "PASS",
  }, { minimumAgreement: 0.6 });
  assert.equal(ready.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(ready.action, "BUY");
  assert.equal(ready.safety.executionAllowed, false);
  assert.equal(ready.safety.automaticPromotionAllowed, false);

  const blocked = buildStrategyEnsemble([
    { action: "BUY", confidence: 0.9 },
    { action: "BUY", confidence: 0.8 },
  ], {
    liquidityStatus: "BLOCKED",
    costStatus: "PASS",
    riskStatus: "PASS",
  });
  assert.equal(blocked.status, "BLOCKED");
  assert.equal(blocked.action, "HOLD");
  assert.ok(blocked.blockers.includes("LIQUIDITY_NOT_PASSED"));
});
