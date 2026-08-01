import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_MODEL_CALIBRATION,
  directionFromScore,
  generateCalibrationCandidates,
  normalizeModelCalibration,
  sameCalibration,
} from "../learning/model-calibration.js";
import { deriveTradeDecision } from "../learning/evaluation-policy.js";
import { WeightInternals } from "../analysis/weights.js";

test("判定境界から強気・中立・弱気を分ける", () => {
  const calibration = {
    bullishThreshold: 65,
    bearishThreshold: 35,
    minimumConfidenceScore: 70,
  };

  assert.equal(directionFromScore(65, calibration), "強気");
  assert.equal(directionFromScore(50, calibration), "中立");
  assert.equal(directionFromScore(35, calibration), "弱気");
});

test("境界候補は重複なしで生成する", () => {
  const candidates = generateCalibrationCandidates();

  assert.equal(candidates.length, 64);
  assert.ok(
    candidates.some((candidate) =>
      sameCalibration(candidate, DEFAULT_MODEL_CALIBRATION),
    ),
  );
});

test("最低信頼度を候補モデルごとに上書きできる", () => {
  const decision = deriveTradeDecision({
    direction: "強気",
    confidenceScore: 69,
    dataQualityScore: 95,
    policy: {
      minimumConfidenceScore: 70,
    },
  });

  assert.equal(decision.action, "見送り");
  assert.equal(decision.policy.minimumConfidenceScore, 70);
});

test("重み学習はATRラベルを優先する", () => {
  const evidence = WeightInternals.factorEvidence(
    [
      {
        factorScores: { rsi: 70 },
        actualReturn: 0.5,
        actualLabel: "中立",
      },
      {
        factorScores: { rsi: 70 },
        actualReturn: 5,
        actualLabel: "上昇",
      },
    ],
    "rsi",
  );

  assert.equal(evidence.sampleCount, 2);
  assert.equal(evidence.accuracy, 50);
});

test("境界値を安全な範囲へ正規化する", () => {
  assert.deepEqual(
    normalizeModelCalibration({
      bullishThreshold: 200,
      bearishThreshold: -10,
      minimumConfidenceScore: 110,
    }),
    {
      bullishThreshold: 90,
      bearishThreshold: 10,
      minimumConfidenceScore: 100,
    },
  );
});
