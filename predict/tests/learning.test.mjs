import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  extractPredictionFeatures,
} from "../learning/feature-extractor.js";
import {
  combinationAccuracy,
  forecastErrorMetrics,
  indicatorAccuracy,
} from "../learning/analytics.js";
import {
  buildMachineLearningDataset,
} from "../learning/dataset.js";
import {
  filterPredictionHistory,
  paginatePredictionHistory,
} from "../performance-history.js";
import {
  recommendWeights,
} from "../analysis/weights.js";
import { DEFAULT_WEIGHTS } from "../config.js";

const performanceHtmlUrl = new URL("../performance.html", import.meta.url);

function condition(key, active = true) {
  return {
    key,
    label: key,
    active,
  };
}

function record(index, overrides = {}) {
  const createdAt = new Date(Date.UTC(2026, 0, index + 1)).toISOString();
  const actualReturn = index % 2 === 0 ? 4 : -2;

  return {
    id: `record-${index}`,
    symbol: index % 2 === 0 ? "7203.T" : "6758.T",
    companyName: "テスト",
    createdAt,
    resolvedAt: createdAt,
    analysisTime: Date.parse(createdAt) / 1000,
    status: "resolved",
    hit: actualReturn > 0,
    actualReturn,
    strategyReturn: actualReturn - 0.3,
    expectedReturn: 3,
    score: 70,
    period: 5,
    predictionPrice: 1_000,
    confidence: {
      score: 70,
    },
    downsideRisk: 3,
    industry: "半導体",
    market: "プライム",
    marketRegime: "Bull",
    factorScores: Object.fromEntries(
      Object.keys(DEFAULT_WEIGHTS).map((key) => [key, 65]),
    ),
    features: {
      schemaVersion: 1,
      values: {
        rsi: 28,
        volumeRatio: 1.8,
      },
      conditions: [
        condition("rsiBelow30"),
        condition("volumeSurge"),
      ],
    },
    ...overrides,
  };
}

test("予測時点のテクニカル条件を固定特徴量として保存できる", () => {
  const candles = Array.from({ length: 80 }, (_value, index) => ({
    time: 1_700_000_000 + index * 86_400,
    open: 180,
    high: 182,
    low: 179,
    close: 180,
    volume: 1_000,
  }));
  candles.at(-2).close = 178;
  candles.at(-1).low = 178.5;
  candles.at(-1).close = 181;

  const features = extractPredictionFeatures({
    candles,
    currentPrice: 181,
    rsi: 28,
    movingAverages: {
      ma25: 179,
      ma75: 180,
      previousMa25: 179,
    },
    macd: {
      previousValue: -1,
      previousSignal: 0,
      value: 1,
      signal: 0.5,
      histogram: 0.5,
    },
    volume: {
      ratio: 1.8,
    },
  });
  const active = features.conditions
    .filter((item) => item.active)
    .map((item) => item.key);

  assert.ok(active.includes("rsiBelow30"));
  assert.ok(active.includes("macdGoldenCross"));
  assert.ok(active.includes("ma25Bounce"));
  assert.ok(active.includes("ma75Breakout"));
  assert.ok(active.includes("volumeSurge"));
});

test("欠損した指標値を0として扱わない", () => {
  const features = extractPredictionFeatures({});

  assert.equal(features.values.rsi, null);
  assert.equal(features.values.volumeRatio, null);
  assert.deepEqual(
    features.conditions.filter((item) => item.active),
    [],
  );
});

test("指標別・組み合わせ別の成績を実リターンから集計する", () => {
  const records = [
    record(0, { actualReturn: 6, strategyReturn: 5.7, hit: true }),
    record(1, { actualReturn: -3, strategyReturn: -3.3, hit: false }),
    record(2, { actualReturn: 4, strategyReturn: 3.7, hit: true }),
  ];
  const indicators = indicatorAccuracy(records);
  const combinations = combinationAccuracy(records, {
    minimumSamples: 3,
  });
  const rsi = indicators.find((item) => item.key === "rsiBelow30");

  assert.equal(rsi.sampleCount, 3);
  assert.ok(Math.abs(rsi.winRate - 200 / 3) < 1e-10);
  assert.equal(rsi.maximumProfit, 5.7);
  assert.equal(rsi.maximumLoss, -3.3);
  assert.equal(combinations[0].sampleCount, 3);
  assert.match(combinations[0].label, /RSI30以下/);
  assert.match(combinations[0].label, /出来高急増/);
});

test("期待変動幅のMAE・RMSE・偏りを算出する", () => {
  const metrics = forecastErrorMetrics([
    record(0, { actualReturn: 5, expectedReturn: 3 }),
    record(1, { actualReturn: 1, expectedReturn: 3 }),
  ]);

  assert.equal(metrics.sampleCount, 2);
  assert.equal(metrics.mae, 2);
  assert.equal(metrics.rmse, 2);
  assert.equal(metrics.bias, 0);
});

test("期待変動幅が欠損した旧履歴を予測誤差へ混ぜない", () => {
  const metrics = forecastErrorMetrics([
    record(0, {
      expectedReturn: null,
    }),
  ]);

  assert.equal(metrics.sampleCount, 0);
  assert.equal(metrics.mae, null);
  assert.equal(metrics.rmse, null);
  assert.equal(metrics.bias, null);
});

test("履歴は結果・銘柄・日付で絞り込み、ページ分割できる", () => {
  const records = Array.from({ length: 80 }, (_value, index) => record(index));
  const filtered = filterPredictionHistory(records, {
    scope: "all",
    result: "success",
    symbol: "7203.T",
    dateFrom: "2026-01-01",
    dateTo: "2026-03-31",
  });
  const page = paginatePredictionHistory(filtered, 2, 10);

  assert.equal(filtered.length, 40);
  assert.equal(page.page, 2);
  assert.equal(page.rows.length, 10);
  assert.equal(page.start, 11);
  assert.equal(page.end, 20);
});

test("予測検証履歴は初期状態で閉じ、必要な絞り込みUIを持つ", async () => {
  const html = await readFile(performanceHtmlUrl, "utf8");
  const details = html.match(
    /<details id="predictionHistoryDetails"[\s\S]*?<\/details>/,
  )?.[0];

  assert.ok(details);
  assert.doesNotMatch(details.split(">")[0], /\sopen(?:\s|=|$)/);
  assert.match(details, /id="historyScope"/);
  assert.match(details, /value="recent30"/);
  assert.match(details, /value="all"/);
  assert.match(details, /value="success"/);
  assert.match(details, /value="failure"/);
  assert.match(details, /id="historySymbol"/);
  assert.match(details, /id="historyDateFrom"/);
  assert.match(details, /id="historyDateTo"/);
  assert.match(details, /id="historyPreviousButton"/);
  assert.match(details, /id="historyNextButton"/);
});

test("推奨重みは学習期間だけを使い、採用前の重みを変更しない", () => {
  const current = {
    ...DEFAULT_WEIGHTS,
  };
  const records = Array.from({ length: 24 }, (_value, index) =>
    record(index, {
      partition: "training",
      actualReturn: 4,
      strategyReturn: 3.7,
      hit: true,
      factorScores: Object.fromEntries(
        Object.keys(DEFAULT_WEIGHTS).map((key) => [
          key,
          key === "rsi" ? 70 : 50,
        ]),
      ),
    }),
  );
  const recommendation = recommendWeights(records, current);

  assert.equal(recommendation.ready, true);
  assert.equal(recommendation.trainingOnly, true);
  assert.ok(recommendation.recommended.rsi > current.rsi);
  assert.deepEqual(current, DEFAULT_WEIGHTS);
});

test("機械学習用データは特徴量と正解を分離し時系列順に分割する", () => {
  const records = Array.from({ length: 10 }, (_value, index) => record(index));
  const dataset = buildMachineLearningDataset(records);

  assert.equal(dataset.rows.length, 10);
  assert.equal(dataset.partitions.training.length, 6);
  assert.equal(dataset.partitions.validation.length, 2);
  assert.equal(dataset.partitions.test.length, 2);
  assert.equal(dataset.rows[0].features.indicatorValues.rsi, 28);
  assert.equal(dataset.rows[0].label.actualReturn, 4);
  assert.equal(dataset.rows[0].audit.futureInformationIncluded, false);
  assert.ok(
    dataset.rows.every(
      (row, index, rows) =>
        index === 0 ||
        new Date(row.featureTimestamp) >=
          new Date(rows[index - 1].featureTimestamp),
    ),
  );
});
