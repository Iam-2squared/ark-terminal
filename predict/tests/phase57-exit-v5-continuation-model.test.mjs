import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PHASE57_EXIT_V5_MODEL_POLICY,
  buildExitV5ResearchEvidence,
  evaluateExitV5Predictions,
  freezeExitV5ModelSpec,
  scoreExitV5Continuation,
} from '../daytrade/phase57-exit-v5-continuation-model.js';

test('v5.0 model spec can only be frozen from development choices', () => {
  const spec = freezeExitV5ModelSpec({ lambda: 0.75 });
  assert.equal(spec.selectedOn, 'development');
  assert.equal(spec.primaryHorizonBars, 3);
  assert.equal(spec.decisionThresholdPct, 0);
  assert.equal(spec.frozen, true);
  assert.throws(() => freezeExitV5ModelSpec({ lambda: 1, selectedOn: 'validation' }), /development/);
  assert.throws(() => freezeExitV5ModelSpec({ lambda: 1, primaryHorizonBars: 6 }), /frozen at 3 bars/);
  assert.equal(PHASE57_EXIT_V5_MODEL_POLICY.outerOosRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_MODEL_POLICY.prospectiveRetuningAllowed, false);
});

test('continuation score treats lower-tail quantile as positive loss magnitude', () => {
  const spec = freezeExitV5ModelSpec({ lambda: 1 });
  const mildTail = scoreExitV5Continuation({ meanIncrementalReturnPct: 0.4, q10IncrementalReturnPct: -0.1 }, spec);
  const severeTail = scoreExitV5Continuation({ meanIncrementalReturnPct: 0.4, q10IncrementalReturnPct: -0.8 }, spec);
  assert.equal(mildTail.downsideRiskPct, 0.1);
  assert.equal(severeTail.downsideRiskPct, 0.8);
  assert.ok(severeTail.continuationScorePct < mildTail.continuationScorePct);
  assert.equal(mildTail.decision, 'HOLD');
  assert.equal(severeTail.decision, 'EXIT');
});

test('incremental cost is differential only and can flip HOLD to EXIT', () => {
  const spec = freezeExitV5ModelSpec({ lambda: 0 });
  const withoutCost = scoreExitV5Continuation({ meanIncrementalReturnPct: 0.05, q10IncrementalReturnPct: 0 }, spec);
  const withCost = scoreExitV5Continuation({ meanIncrementalReturnPct: 0.05, q10IncrementalReturnPct: 0, incrementalCostPct: 0.06 }, spec);
  assert.equal(withoutCost.decision, 'HOLD');
  assert.equal(withCost.decision, 'EXIT');
});

test('forward realized outcomes stay evaluation-only', () => {
  const metrics = evaluateExitV5Predictions([
    { meanIncrementalReturnPct: 0.5, realizedIncrementalReturnPct: 0.4, continuationScorePct: 0.3, decision: 'HOLD' },
    { meanIncrementalReturnPct: -0.2, realizedIncrementalReturnPct: -0.6, continuationScorePct: -0.4, decision: 'EXIT' },
  ]);
  assert.equal(metrics.sampleCount, 2);
  assert.equal(metrics.holdCount, 1);
  assert.equal(metrics.exitCount, 1);
  assert.equal(metrics.meanRealizedContinuationWhenHeldPct, 0.4);
  assert.equal(metrics.meanAdditionalLossAvoidedWhenExitPct, 0.6);
  assert.equal(metrics.signAccuracy, 1);
});

test('research evidence cannot auto-promote or update production', () => {
  const spec = freezeExitV5ModelSpec({ lambda: 0.5 });
  const evidence = buildExitV5ResearchEvidence({
    splitName: 'oos',
    pairedAgainst: 'v4',
    metrics: { pairedNetDeltaPct: 0.1 },
    spec,
  });
  assert.equal(evidence.verdict, 'RESEARCH_EVIDENCE_ONLY');
  assert.equal(evidence.automaticPromotionAllowed, false);
  assert.equal(evidence.productionUpdateAllowed, false);
  assert.equal(evidence.transmitted, false);
});
