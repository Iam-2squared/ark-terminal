import assert from "node:assert/strict";
import test from "node:test";

import { createPredictionOutput } from "../analysis/prediction-output.js";
import { summarizePerformance } from "../backtest/engine.js";
import {
  classifyActualReturn,
  deriveEvaluationThreshold,
  deriveTradeDecision,
  evaluateResolvedPrediction,
  MODEL_VERSION,
} from "../learning/evaluation-policy.js";

test("ATRと予測期間から正解ラベルの閾値を作る", () => {
  const threshold = deriveEvaluationThreshold({
    atrPercent: 2,
    period: 4,
  });

  assert.equal(threshold, 4);
  assert.equal(
    classifyActualReturn({ actualReturn: 5, threshold }),
    "上昇",
  );
  assert.equal(
    classifyActualReturn({ actualReturn: 2, threshold }),
    "中立",
  );
  assert.equal(
    classifyActualReturn({ actualReturn: -5, threshold }),
    "下落",
  );
});

test("低信頼または低品質の予測は見送る", () => {
  const lowConfidence = deriveTradeDecision({
    direction: "強気",
    confidenceScore: 59,
    dataQualityScore: 95,
  });
  const highConfidence = deriveTradeDecision({
    direction: "強気",
    confidenceScore: 75,
    dataQualityScore: 95,
  });

  assert.equal(lowConfidence.action, "見送り");
  assert.equal(lowConfidence.isActionable, false);
  assert.equal(highConfidence.action, "採用");
  assert.equal(highConfidence.isActionable, true);
});

test("見送り予測は勝率と損益集計から除外する", () => {
  const adopted = evaluateResolvedPrediction({
    direction: "強気",
    actualReturn: 5,
    threshold: 4,
    decision: { action: "採用", isActionable: true },
    costs: {
      commissionBpsPerSide: 5,
      slippageBpsPerSide: 10,
    },
  });
  const abstained = evaluateResolvedPrediction({
    direction: "強気",
    actualReturn: -5,
    threshold: 4,
    decision: { action: "見送り", isActionable: false },
    costs: {
      commissionBpsPerSide: 5,
      slippageBpsPerSide: 10,
    },
  });
  const metrics = summarizePerformance([
    {
      status: "resolved",
      actualReturn: 5,
      resolvedAt: "2026-01-01T00:00:00Z",
      period: 5,
      ...adopted,
    },
    {
      status: "resolved",
      actualReturn: -5,
      resolvedAt: "2026-01-02T00:00:00Z",
      period: 5,
      ...abstained,
    },
  ]);

  assert.equal(metrics.resolvedCount, 2);
  assert.equal(metrics.sampleCount, 1);
  assert.equal(metrics.abstainCount, 1);
  assert.equal(metrics.coverageRate, 50);
  assert.equal(metrics.winRate, 100);
});

test("Prediction Outputにモデル版・判定閾値・採否を含める", () => {
  const output = createPredictionOutput({
    analysis: {
      totalScore: 70,
      factors: [
        {
          available: true,
          category: "trend",
          score: 70,
        },
      ],
    },
    indicators: {
      candleCount: 504,
      atr: { percent: 2 },
    },
    quality: {
      canScore: true,
      qualityScore: 95,
      missingRate: 0,
    },
    period: 4,
    records: [],
    symbol: "7203.T",
    marketEnvironment: null,
  });

  assert.equal(output.modelVersion, MODEL_VERSION);
  assert.equal(output.evaluationThreshold, 4);
  assert.equal(output.decision.action, "採用");
});
