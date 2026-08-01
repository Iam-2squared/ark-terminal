import assert from "node:assert/strict";
import test from "node:test";

import {
  CONTINUOUS_FEATURE_KEYS,
  extractContinuousFeatures,
  fitContinuousModel,
  predictContinuousScore,
} from "../learning/continuous-model.js";
import { BacktestInternals } from "../backtest/engine.js";

function syntheticRecord(label, signal, index = 0) {
  return {
    id: `${label}-${index}`,
    actualLabel: label,
    actualReturn: signal * 5,
    features: {
      schemaVersion: 1,
      values: {
        rsi: 50 + signal * 15 + index * 0.02,
        macdHistogram: signal * 2 + index * 0.001,
        ma25Deviation: signal * 3,
        volumeRatio: signal === 0 ? 1 : 1.7,
        atrPercent: 2,
        adx: signal === 0 ? 18 : 32,
        stochasticK: 50 + signal * 22,
        bollingerPercentB: 0.5 + signal * 0.25,
        distanceFrom52WeekHigh:
          signal > 0 ? -2 : signal < 0 ? -38 : -20,
      },
    },
  };
}

test("連続値モデルは上昇・中立・下落ラベルから学習できる", () => {
  const records = [
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("下落", -1, index),
    ),
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("中立", 0, index),
    ),
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("上昇", 1, index),
    ),
  ];

  const model = fitContinuousModel(records);
  const bullishScore = predictContinuousScore(
    model,
    syntheticRecord("上昇", 1, 100),
  );
  const neutralScore = predictContinuousScore(
    model,
    syntheticRecord("中立", 0, 100),
  );
  const bearishScore = predictContinuousScore(
    model,
    syntheticRecord("下落", -1, 100),
  );

  assert.equal(model.ready, true);
  assert.equal(model.sampleCount, 36);
  assert.equal(model.featureCount, CONTINUOUS_FEATURE_KEYS.length);
  assert.ok(bullishScore > neutralScore);
  assert.ok(neutralScore > bearishScore);
  assert.ok(bullishScore > 55);
  assert.ok(bearishScore < 45);
});

test("学習件数不足ではモデルを作らない", () => {
  const records = Array.from({ length: 10 }, (_value, index) =>
    syntheticRecord("上昇", 1, index),
  );
  const model = fitContinuousModel(records);

  assert.equal(model.ready, false);
  assert.equal(model.sampleCount, 10);
  assert.match(model.reason, /20件/);
});

test("特徴量抽出へ将来リターンを混ぜない", () => {
  const first = syntheticRecord("上昇", 1, 0);
  const second = {
    ...first,
    actualLabel: "下落",
    actualReturn: -999,
  };

  assert.deepEqual(
    extractContinuousFeatures(first),
    extractContinuousFeatures(second),
  );
});

test("欠損値があっても学習平均で補完して予測できる", () => {
  const records = [
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("下落", -1, index),
    ),
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("上昇", 1, index),
    ),
  ];
  const model = fitContinuousModel(records);
  const partial = syntheticRecord("上昇", 1, 0);

  partial.features.values.macdHistogram = null;
  partial.features.values.stochasticK = null;
  partial.features.values.bollingerPercentB = null;

  const score = predictContinuousScore(model, partial);

  assert.equal(model.ready, true);
  assert.ok(Number.isFinite(score));
});

test("連続値特徴量にはトレンド相互作用を含む", () => {
  const features = extractContinuousFeatures(
    syntheticRecord("上昇", 1, 0),
  );

  assert.ok(Number.isFinite(features.adxTrend));
  assert.ok(Number.isFinite(features.volumeTrend));
});

test("連続値モデルのスコアをATR評価へ接続できる", () => {
  const training = [
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("下落", -1, index),
    ),
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("上昇", 1, index),
    ),
  ];
  const model = fitContinuousModel(training);
  const record = {
    ...syntheticRecord("上昇", 1, 100),
    score: 50,
    actualReturn: 5,
    evaluationThreshold: 2,
    confidence: {
      score: 90,
    },
    dataQuality: {
      qualityScore: 100,
    },
    costAssumptions: {
      commissionBpsPerSide: 0,
      slippageBpsPerSide: 0,
    },
  };
  const evaluated = BacktestInternals.applyContinuousModelToRecord(
    record,
    model,
    {
      bullishThreshold: 55,
      bearishThreshold: 45,
      minimumConfidenceScore: 60,
    },
  );

  assert.equal(model.ready, true);
  assert.equal(evaluated.scoringModel.key, "continuous");
  assert.equal(evaluated.scoringModel.candidateId, "default");
  assert.equal(evaluated.ruleScore, 50);
  assert.ok(evaluated.score > 55);
  assert.equal(evaluated.direction, "強気");
  assert.equal(evaluated.actualLabel, "上昇");
  assert.equal(evaluated.hit, true);
});

test("v2はクラス数の偏りを学習重みで補正する", () => {
  const records = [
    ...Array.from({ length: 30 }, (_value, index) =>
      syntheticRecord("上昇", 1, index),
    ),
    ...Array.from({ length: 5 }, (_value, index) =>
      syntheticRecord("中立", 0, index),
    ),
    ...Array.from({ length: 5 }, (_value, index) =>
      syntheticRecord("下落", -1, index),
    ),
  ];

  const model = fitContinuousModel(records);

  assert.equal(model.ready, true);
  assert.equal(model.version, "continuous-robust-ridge-v2");
  assert.ok(model.classWeights["下落"] > model.classWeights["上昇"]);
  assert.ok(model.classWeights["中立"] > model.classWeights["上昇"]);
  assert.equal(model.lossFunction, "class-balanced-huber-ridge");
});

test("v2の中央値MAD標準化は巨大な外れ値へ引っ張られにくい", () => {
  const records = [
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("下落", -1, index),
    ),
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("上昇", 1, index),
    ),
  ];

  records[0].features.values.macdHistogram = 1000000000;

  const model = fitContinuousModel(records);
  const statistic = model.statistics.macdHistogram;

  assert.equal(model.ready, true);
  assert.equal(model.preprocessing, "median-mad-robust-scaling");
  assert.ok(Math.abs(statistic.center) < 10);
  assert.ok(statistic.scale < 100);
});

test("v2は複数の正則化・Huber候補を生成できる", async () => {
  const { fitContinuousModelCandidates } = await import(
    "../learning/continuous-model.js"
  );
  const records = [
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("下落", -1, index),
    ),
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("中立", 0, index),
    ),
    ...Array.from({ length: 12 }, (_value, index) =>
      syntheticRecord("上昇", 1, index),
    ),
  ];

  const candidates = fitContinuousModelCandidates(records);

  assert.equal(candidates.length, 6);
  assert.equal(candidates.every((model) => model.ready), true);
  assert.equal(
    new Set(candidates.map((model) => model.candidateId)).size,
    6,
  );
});