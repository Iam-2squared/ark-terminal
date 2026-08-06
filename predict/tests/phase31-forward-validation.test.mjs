import test from "node:test";
import assert from "node:assert/strict";

import {
  createPhase31ForwardRun,
  validatePhase31RunIntegrity,
  comparePhase31ForwardPerformance,
  runPhase31ForwardValidation,
} from "../forward/phase31-forward-validation.js";

const context = {
  outOfSample: true,
  paperOnly: true,
  futureLeakCheckPassed: true,
  sameDataContract: true,
  sameCostContract: true,
  sameHoldingPeriodContract: true,
};

function row(signal, actualReturn, netReturn = actualReturn) {
  return {
    symbol: "7203.T",
    session: "2026-08-01",
    horizonDays: 5,
    signal,
    confidence: 0.8,
    predictedReturn: 0.03,
    actualReturn,
    netReturn,
    drawdown: 0.02,
  };
}

test("creates immutable paired run under strict OOS paper-only context", () => {
  const run = createPhase31ForwardRun({
    championRows: [row("BUY", 0.02)],
    candidateRows: [row("BUY", 0.02)],
    context,
    metadata: { runId: "run-1" },
  });
  assert.equal(run.runId, "run-1");
  assert.equal(run.pairs.length, 1);
  assert.equal(run.immutable, true);
  assert.equal(run.safety.brokerWriteAllowed, false);
});

test("blocks non OOS validation", () => {
  assert.throws(() => createPhase31ForwardRun({
    championRows: [row("BUY", 0.02)],
    candidateRows: [row("BUY", 0.02)],
    context: { ...context, outOfSample: false },
  }), /BLOCKED_NOT_OUT_OF_SAMPLE/);
});

test("blocks actual return mismatch", () => {
  assert.throws(() => createPhase31ForwardRun({
    championRows: [row("BUY", 0.02)],
    candidateRows: [row("BUY", 0.03)],
    context,
  }), /BLOCKED_ACTUAL_RETURN_MISMATCH/);
});

test("integrity rejects empty paired samples", () => {
  const result = validatePhase31RunIntegrity({ immutable: true, pairs: [] });
  assert.equal(result.status, "BLOCKED");
  assert.ok(result.blockers.includes("NO_PAIRED_SAMPLES"));
});

test("comparison continues forward test when samples are insufficient", () => {
  const run = createPhase31ForwardRun({
    championRows: [row("BUY", 0.02, 0.01)],
    candidateRows: [row("BUY", 0.02, 0.02)],
    context,
  });
  const comparison = comparePhase31ForwardPerformance(run, { minPairedSamples: 5 });
  assert.equal(comparison.status, "CONTINUE_FORWARD_TEST");
  assert.equal(comparison.promotionAllowed, false);
});

test("full runner stays review-only with zero broker activity", () => {
  const result = runPhase31ForwardValidation({
    championRows: [row("SELL", 0.02, -0.01)],
    candidateRows: [row("BUY", 0.02, 0.02)],
    context,
    options: { minPairedSamples: 1 },
  });
  assert.equal(result.status, "READY_FOR_STATISTICAL_REVIEW");
  assert.equal(result.comparison.deltas.accuracy, 1);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.brokerWrites, 0);
  assert.equal(result.liveOrders, 0);
});
