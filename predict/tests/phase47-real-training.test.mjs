import test from "node:test";
import assert from "node:assert/strict";
import { MODEL_TYPES, PHASE47_SAFETY, evaluateModel, trainModel } from "../models/phase47-real-training.js";
import {
  DEFAULT_PROMOTION_GATE,
  DEFAULT_THRESHOLD_GRID,
  auditPhase47Candidate,
  buildEqualWeightBenchmark,
  buildPhase47RegistryCandidate,
  buildPortfolioOosMetrics,
  evaluatePromotionGate,
  runWalkForward,
} from "../models/phase47-walk-forward.js";

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

function multiAssetRows(sessionCount = 140) {
  const base = rows(sessionCount);
  return base.flatMap((row, index) => [
    row,
    {
      ...row,
      id: `6758.T:${index}`,
      symbol: "6758.T",
      label: index % 3 ? row.label : 1 - row.label,
      actualReturn: index % 3 ? row.actualReturn * 0.8 : -row.actualReturn * 0.6,
      features: { ...row.features, momentum5: row.features.momentum5 * 0.7 },
    },
  ]);
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

test("multi-asset portfolio evaluator keeps symbol positions independent and compounds once per session", () => {
  const predictions = [
    { id: "A:1", symbol: "A", sessionDate: "2026-01-05", probability: 0.9, actualReturn: 0.10 },
    { id: "B:1", symbol: "B", sessionDate: "2026-01-05", probability: 0.1, actualReturn: -0.20 },
    { id: "A:2", symbol: "A", sessionDate: "2026-01-06", probability: 0.9, actualReturn: 0.10 },
    { id: "B:2", symbol: "B", sessionDate: "2026-01-06", probability: 0.9, actualReturn: 0.10 },
  ];
  const metrics = buildPortfolioOosMetrics(predictions, { entryThreshold: 0.55, costRate: 0 });
  assert.equal(metrics.sampleCount, 4);
  assert.equal(metrics.portfolioDays, 2);
  assert.equal(metrics.positionChanges, 2);
  assert.equal(metrics.exposure, 0.75);
  assert.deepEqual(metrics.dailyReturns, [0.05, 0.10]);
  assert.ok(Math.abs(metrics.netReturn - 0.155) < 1e-12);
});

test("multi-asset transaction cost is charged only on per-symbol position changes", () => {
  const predictions = [
    { id: "A:1", symbol: "A", sessionDate: "2026-01-05", probability: 0.9, actualReturn: 0 },
    { id: "B:1", symbol: "B", sessionDate: "2026-01-05", probability: 0.1, actualReturn: 0 },
    { id: "A:2", symbol: "A", sessionDate: "2026-01-06", probability: 0.9, actualReturn: 0 },
    { id: "B:2", symbol: "B", sessionDate: "2026-01-06", probability: 0.9, actualReturn: 0 },
  ];
  const metrics = buildPortfolioOosMetrics(predictions, { entryThreshold: 0.55, costRate: 0.01 });
  assert.equal(metrics.positionChanges, 2);
  assert.deepEqual(metrics.dailyReturns, [-0.005, -0.005]);
  assert.ok(Math.abs(metrics.transactionCostSum - 0.01) < 1e-12);
});

test("equal-weight benchmark aggregates symbols by session before compounding", () => {
  const benchmark = buildEqualWeightBenchmark([
    { id: "A:1", symbol: "A", sessionDate: "2026-01-05", probability: 0.5, actualReturn: 0.10 },
    { id: "B:1", symbol: "B", sessionDate: "2026-01-05", probability: 0.5, actualReturn: -0.10 },
    { id: "A:2", symbol: "A", sessionDate: "2026-01-06", probability: 0.5, actualReturn: 0.02 },
    { id: "B:2", symbol: "B", sessionDate: "2026-01-06", probability: 0.5, actualReturn: 0.04 },
  ]);
  assert.equal(benchmark.sampleCount, 4);
  assert.equal(benchmark.portfolioDays, 2);
  assert.deepEqual(benchmark.dailyReturns, [0, 0.03]);
  assert.ok(Math.abs(benchmark.netReturn - 0.03) < 1e-12);
});

test("walk-forward uses session-date folds and nested inner validation only", () => {
  const result = runWalkForward({ rows: multiAssetRows(140), options: { minTrain: 60, validationSize: 20, step: 20, innerValidationSize: 15 } });
  assert.equal(result.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(result.phase, 47.2);
  assert.equal(result.ranked.length, 3);
  assert.ok(result.folds >= 2);
  assert.equal(result.thresholdSelectionMode, "NESTED_INNER_VALIDATION");
  assert.equal(result.portfolioEvaluationMode, "SESSION_DATE_EQUAL_WEIGHT_MULTI_ASSET");
  assert.equal(result.automaticPromotionAllowed, false);
  for (const model of result.ranked) {
    for (const fold of model.folds) {
      assert.ok(fold.trainEnd < fold.testStart);
      assert.equal(fold.testSessionCount, 20);
      assert.equal(fold.testCount, 40);
      assert.equal(fold.thresholdSelection.status, "SELECTED_ON_INNER_VALIDATION");
      assert.ok(fold.thresholdSelection.innerTrainEnd < fold.thresholdSelection.validationStart);
      assert.ok(fold.thresholdSelection.validationEnd < fold.testStart);
      assert.ok(DEFAULT_THRESHOLD_GRID.includes(fold.selectedThreshold));
    }
    assert.ok(model.aggregate.oos.sampleCount >= 40);
    assert.ok(model.aggregate.oos.portfolioDays >= 20);
    assert.ok(model.aggregate.oos.exposure >= 0 && model.aggregate.oos.exposure <= 1);
    assert.ok(model.aggregate.oos.maxDrawdown >= 0);
    assert.ok(Number.isFinite(model.aggregate.oos.netReturn));
    assert.equal(model.aggregate.benchmark.sampleCount, model.aggregate.oos.sampleCount);
    assert.equal(model.aggregate.thresholdSweep.length, DEFAULT_THRESHOLD_GRID.length);
    assert.equal(model.aggregate.thresholdSweepDiagnosticsOnly, true);
    assert.equal(model.aggregate.confidenceBuckets.length, 6);
    assert.equal(model.aggregate.thresholdHistory.length, model.folds.length);
    assert.ok(model.aggregate.promotionGate.status);
    assert.equal(model.aggregate.promotionGate.automaticPromotionAllowed, false);
  }
});

test("outer OOS is not used to choose thresholds", () => {
  const options = { minTrain: 60, validationSize: 20, step: 20, innerValidationSize: 10 };
  const first = runWalkForward({ rows: rows(120), modelTypes: ["LOGISTIC_REGRESSION"], thresholdGrid: [0.52, 0.6], options });
  const history = first.ranked[0].aggregate.thresholdHistory;
  for (const item of history) {
    assert.ok(item.validationEnd < item.outerTestStart);
    assert.ok([0.52, 0.6].includes(item.selectedThreshold));
    assert.ok(item.validationSamples > 0);
  }
});

test("walk-forward OOS evaluator supports a no-trade zone", () => {
  const result = runWalkForward({ rows: rows(140), modelTypes: ["LOGISTIC_REGRESSION"], entryThreshold: 0.999, thresholdGrid: [0.999], options: { minTrain: 60, validationSize: 20, step: 20 } });
  const oos = result.ranked[0].aggregate.oos;
  assert.equal(oos.entryThreshold, 0.999);
  assert.ok(oos.activeDays <= oos.sampleCount);
  assert.ok(oos.positionChanges <= oos.sampleCount);
});

test("threshold sweep remains diagnostics-only and deterministic", () => {
  const options = { minTrain: 60, validationSize: 20, step: 20 };
  const first = runWalkForward({ rows: rows(180), modelTypes: ["GRADIENT_BOOSTING"], thresholdGrid: [0.52, 0.55, 0.6], options });
  const second = runWalkForward({ rows: rows(180), modelTypes: ["GRADIENT_BOOSTING"], thresholdGrid: [0.52, 0.55, 0.6], options });
  assert.deepEqual(first.ranked[0].aggregate.thresholdSweep, second.ranked[0].aggregate.thresholdSweep);
  assert.deepEqual(first.ranked[0].aggregate.confidenceBuckets, second.ranked[0].aggregate.confidenceBuckets);
  assert.deepEqual(first.ranked[0].aggregate.thresholdHistory, second.ranked[0].aggregate.thresholdHistory);
  assert.equal(first.ranked[0].aggregate.thresholdSweepDiagnosticsOnly, true);
});

test("promotion gate blocks weak real-world metrics", () => {
  const aggregate = {
    auc: 0.51,
    oos: { profitFactor: 0.9, sharpe: -0.2, maxDrawdown: 0.5, sampleCount: 1000, positionChanges: 100, exposure: 0.2, netReturn: -0.1 },
    benchmark: { netReturn: 0.05 },
  };
  const gate = evaluatePromotionGate(aggregate);
  assert.equal(gate.status, "BLOCKED_FOR_PROMOTION");
  for (const expected of ["AUC_BELOW_MINIMUM", "PROFIT_FACTOR_BELOW_MINIMUM", "SHARPE_BELOW_MINIMUM", "MAX_DRAWDOWN_ABOVE_LIMIT", "NET_RETURN_NOT_POSITIVE", "BENCHMARK_NOT_OUTPERFORMED"]) assert.ok(gate.failures.includes(expected));
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

test("registry candidate is Phase47.2 review-only and checksum protected", () => {
  const dataset = rows(140);
  const walkForward = runWalkForward({ rows: dataset, options: { minTrain: 60, validationSize: 20, step: 20 } });
  const candidate = buildPhase47RegistryCandidate({ rows: dataset, walkForwardResult: walkForward, datasetLineage: { datasetVersion: "phase46-v3", checksum: "fixture" }, generatedAt: "2026-08-06T00:00:00.000Z" });
  assert.equal(candidate.phase, 47.2);
  assert.equal(candidate.schemaVersion, 2);
  assert.equal(candidate.thresholdSelectionMode, "NESTED_INNER_VALIDATION");
  assert.ok(candidate.thresholdHistory.length >= 2);
  assert.equal(auditPhase47Candidate(candidate).status, "READY_FOR_HUMAN_REVIEW");
  assert.ok(candidate.walkForward.oos.sampleCount >= 20);
  assert.ok(candidate.promotionStatus);
  const tampered = { ...candidate, automaticPromotionAllowed: true };
  const audit = auditPhase47Candidate(tampered);
  assert.equal(audit.status, "BLOCKED");
  assert.ok(audit.blockers.includes("AUTOMATIC_PROMOTION_MUST_BE_FALSE"));
  assert.ok(audit.blockers.includes("CHECKSUM_MISMATCH"));
});

test("Phase47 safety remains fully read-only and audit reports zero writes", () => {
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
  const candidate = { automaticPromotionAllowed: false, productionUpdateAllowed: false, humanApprovalRequired: true, thresholdSelectionMode: "NESTED_INNER_VALIDATION" };
  const audit = auditPhase47Candidate(candidate);
  assert.equal(audit.brokerWrites, 0);
  assert.equal(audit.excelOrderWrites, 0);
  assert.equal(audit.rssOrderCalls, 0);
  assert.equal(audit.liveOrders, 0);
});
