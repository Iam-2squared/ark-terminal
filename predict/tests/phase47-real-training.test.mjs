import test from "node:test";
import assert from "node:assert/strict";
import { MODEL_TYPES, PHASE47_SAFETY, evaluateModel, trainModel } from "../models/phase47-real-training.js";
import { DEFAULT_PROMOTION_GATE, auditPhase47Candidate, buildPhase47RegistryCandidate, evaluatePromotionGate, runWalkForward } from "../models/phase47-walk-forward.js";

function rows(count = 140) {
  const start = Date.UTC(2024, 0, 1);
  return Array.from({ length: count }, (_, index) => {
    const momentum = Math.sin(index / 5);
    const trend = (index % 17) / 17 - 0.5;
    const label = momentum + trend > 0 ? 1 : 0;
    return {
      id: `7203.T:${index}`,
      symbol: "7203.T",
      sessionDate: new Date(start + index * 86400000).toISOString().slice(0, 10),
      label,
      actualReturn: label ? 0.012 : -0.009,
      features: {
        momentum5: momentum,
        ma20Gap: trend,
        rsi14: 50 + momentum * 20,
        volumeRatio20: 1 + (index % 7) / 10,
        volatility20: 0.01 + (index % 5) / 1000,
      },
    };
  });
}

test("all three Phase47 models train and evaluate deterministically", () => {
  const dataset = rows(100);
  for (const modelType of MODEL_TYPES) {
    const first = trainModel({ rows: dataset.slice(0, 80), modelType });
    const second = trainModel({ rows: dataset.slice(0, 80), modelType });
    assert.equal(first.modelId, second.modelId);
    const metrics = evaluateModel({ model: first, rows: dataset.slice(80) });
    assert.equal(metrics.sampleCount, 20);
    assert.ok(metrics.accuracy >= 0 && metrics.accuracy <= 1);
    assert.ok(metrics.auc >= 0 && metrics.auc <= 1);
    assert.ok(Number.isFinite(metrics.profitFactor));
    assert.ok(Number.isFinite(metrics.sharpe));
    assert.ok(metrics.maxDrawdown >= 0);
  }
});

test("walk-forward compares models without future overlap", () => {
  const result = runWalkForward({ rows: rows(140), options: { minTrain: 60, validationSize: 20, step: 20 } });
  assert.equal(result.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(result.ranked.length, 3);
  assert.ok(result.folds >= 2);
  assert.equal(result.entryThreshold, 0.55);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.ok(["BLOCKED_FOR_PROMOTION", "ELIGIBLE_FOR_PROMOTION_REVIEW"].includes(result.selectedPromotionStatus));
  for (const model of result.ranked) {
    for (const fold of model.folds) {
      assert.ok(fold.trainEnd < fold.testStart);
      assert.equal(fold.testCount, 20);
    }
    assert.ok(model.aggregate.oos.sampleCount >= 20);
    assert.ok(model.aggregate.oos.exposure >= 0 && model.aggregate.oos.exposure <= 1);
    assert.ok(model.aggregate.oos.maxDrawdown >= 0);
    assert.ok(Number.isFinite(model.aggregate.oos.netReturn));
    assert.equal(model.aggregate.benchmark.sampleCount, model.aggregate.oos.sampleCount);
    assert.ok(model.aggregate.promotionGate.status);
    assert.equal(model.aggregate.promotionGate.automaticPromotionAllowed, false);
  }
});

test("walk-forward OOS evaluator supports a no-trade zone", () => {
  const result = runWalkForward({ rows: rows(140), modelTypes: ["LOGISTIC_REGRESSION"], entryThreshold: 0.999, options: { minTrain: 60, validationSize: 20, step: 20 } });
  const oos = result.ranked[0].aggregate.oos;
  assert.equal(oos.entryThreshold, 0.999);
  assert.ok(oos.activeDays <= oos.sampleCount);
  assert.ok(oos.positionChanges <= oos.sampleCount);
});

test("promotion gate blocks weak real-world metrics", () => {
  const aggregate = {
    auc: 0.51,
    oos: { profitFactor: 0.9, sharpe: -0.2, maxDrawdown: 0.5, sampleCount: 1000, positionChanges: 100, exposure: 0.2, netReturn: -0.1 },
    benchmark: { netReturn: 0.05 },
  };
  const gate = evaluatePromotionGate(aggregate);
  assert.equal(gate.status, "BLOCKED_FOR_PROMOTION");
  for (const expected of ["AUC_BELOW_MINIMUM", "PROFIT_FACTOR_BELOW_MINIMUM", "SHARPE_BELOW_MINIMUM", "MAX_DRAWDOWN_ABOVE_LIMIT", "NET_RETURN_NOT_POSITIVE", "BENCHMARK_NOT_OUTPERFORMED"]) {
    assert.ok(gate.failures.includes(expected));
  }
});

test("promotion gate can become review-eligible but never auto-promotes", () => {
  const aggregate = {
    auc: DEFAULT_PROMOTION_GATE.minAuc + 0.02,
    oos: { profitFactor: 1.5, sharpe: 0.8, maxDrawdown: 0.12, sampleCount: 2000, positionChanges: 120, exposure: 0.35, netReturn: 0.4 },
    benchmark: { netReturn: 0.2 },
  };
  const gate = evaluatePromotionGate(aggregate);
  assert.equal(gate.status, "ELIGIBLE_FOR_PROMOTION_REVIEW");
  assert.equal(gate.failures.length, 0);
  assert.equal(gate.automaticPromotionAllowed, false);
  assert.equal(gate.humanApprovalRequired, true);
});

test("registry candidate is review-only, promotion-aware and checksum protected", () => {
  const dataset = rows(140);
  const walkForward = runWalkForward({ rows: dataset, options: { minTrain: 60, validationSize: 20, step: 20 } });
  const candidate = buildPhase47RegistryCandidate({ rows: dataset, walkForwardResult: walkForward, datasetLineage: { datasetVersion: "phase46-v3", checksum: "fixture" }, generatedAt: "2026-08-06T00:00:00.000Z" });
  assert.equal(auditPhase47Candidate(candidate).status, "READY_FOR_HUMAN_REVIEW");
  assert.ok(candidate.walkForward.oos.sampleCount >= 20);
  assert.ok(candidate.promotionStatus);
  assert.ok(Array.isArray(candidate.promotionFailures));
  const tampered = { ...candidate, automaticPromotionAllowed: true };
  const audit = auditPhase47Candidate(tampered);
  assert.equal(audit.status, "BLOCKED");
  assert.ok(audit.blockers.includes("AUTOMATIC_PROMOTION_MUST_BE_FALSE"));
  assert.ok(audit.blockers.includes("CHECKSUM_MISMATCH"));
});

test("Phase47 safety remains fully read-only", () => {
  assert.deepEqual(PHASE47_SAFETY, {
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  });
});
