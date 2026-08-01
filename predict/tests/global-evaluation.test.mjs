import assert from "node:assert/strict";
import test from "node:test";

import {
  buildGlobalEvaluationSummary,
  createGlobalEvaluationBatchId,
  deduplicateGlobalEvaluationRecords,
  mergeGlobalEvaluationRecords,
  parseGlobalEvaluationSymbols,
  runGlobalEvaluation,
} from "../global-evaluation.js";

function resolvedRecord(overrides = {}) {
  return {
    id: Math.random().toString(36),
    symbol: "7203.T",
    period: 5,
    analysisTime: 100,
    partition: "test",
    status: "resolved",
    actualReturn: 4,
    strategyReturn: 3.8,
    hit: true,
    ...overrides,
  };
}

test("銘柄コードを正規化して重複を除外する", () => {
  const parsed = parseGlobalEvaluationSymbols(
    "7203, 6758.T, 7203, AAPL, 6758.t",
  );

  assert.deepEqual(parsed.symbols, [
    "7203.T",
    "6758.T",
    "AAPL",
  ]);
  assert.deepEqual(parsed.duplicates, [
    "7203.T",
    "6758.T",
  ]);
  assert.deepEqual(parsed.invalid, []);
});

test("無効な銘柄と上限超過銘柄を分離する", () => {
  const parsed = parseGlobalEvaluationSymbols(
    "7203, ???, 6758, 9984",
    {
      maximumSymbols: 2,
    },
  );

  assert.deepEqual(parsed.symbols, [
    "7203.T",
    "6758.T",
  ]);
  assert.deepEqual(parsed.invalid, ["???"]);
  assert.deepEqual(parsed.omitted, ["9984.T"]);
  assert.equal(parsed.truncated, true);
});

test("バッチIDを再現可能な入力から生成できる", () => {
  const first = createGlobalEvaluationBatchId({
    now: 1000,
    random: 0.25,
  });
  const second = createGlobalEvaluationBatchId({
    now: 1000,
    random: 0.25,
  });

  assert.equal(first, second);
  assert.match(first, /^global-/);
});

test("総合成績は最終テストだけを集計し見送りを0%として扱う", () => {
  const summary = buildGlobalEvaluationSummary([
    resolvedRecord({
      analysisTime: 1,
      actualReturn: 4,
      strategyReturn: 3,
      hit: true,
    }),
    resolvedRecord({
      analysisTime: 2,
      actualReturn: -2,
      strategyReturn: -1,
      hit: false,
    }),
    resolvedRecord({
      analysisTime: 3,
      actualReturn: 5,
      strategyReturn: 0,
      hit: null,
    }),
    resolvedRecord({
      analysisTime: 4,
      partition: "training",
      actualReturn: 100,
      strategyReturn: 100,
      hit: true,
    }),
  ]);

  assert.equal(summary.sampleCount, 3);
  assert.equal(summary.adoptedCount, 2);
  assert.equal(summary.abstainCount, 1);
  assert.equal(summary.coverageRate, 2 / 3 * 100);
  assert.equal(summary.winRate, 50);
  assert.equal(summary.strategy.averageReturn, 2 / 3);
  assert.equal(summary.benchmark.averageReturn, 7 / 3);
  assert.ok(summary.warnings.length >= 1);
});

test("バッチが違っても同じ銘柄・期間・時点を重複排除する", () => {
  const first = resolvedRecord({
    batchId: "batch-1",
    strategyReturn: 1,
  });
  const second = {
    ...first,
    id: "replacement",
    batchId: "batch-2",
    strategyReturn: 2,
  };
  const result = deduplicateGlobalEvaluationRecords([
    first,
    second,
  ]);

  assert.equal(result.records.length, 1);
  assert.equal(result.duplicateCount, 1);
  assert.equal(result.records[0].strategyReturn, 2);
});

test("複数銘柄を順番に評価し失敗銘柄があっても継続する", async () => {
  const progress = [];

  const result = await runGlobalEvaluation({
    symbols: "7203, 6758, 9984",
    period: 5,
    weights: {
      rsi: 1,
    },
    batchId: "global-test",
    fetchBundle: async (symbol) => {
      if (symbol === "6758.T") {
        throw new Error("履歴取得失敗");
      }

      return {
        history: {
          candles: [{ time: 1, close: 100 }],
        },
        context: {
          company: {
            name: symbol,
            industry: "テスト",
          },
        },
      };
    },
    runBacktest: ({ symbol }) => ({
      records: [
        resolvedRecord({
          symbol,
          partition: "training",
          analysisTime: 1,
        }),
        resolvedRecord({
          symbol,
          partition: "validation",
          analysisTime: 2,
        }),
        resolvedRecord({
          symbol,
          partition: "test",
          analysisTime: 3,
        }),
      ],
      meta: {
        modelSelection: {
          selected: "rule",
          selectedCandidateId: null,
        },
      },
    }),
    onProgress: (item) => progress.push(item),
  });

  assert.equal(result.completedCount, 2);
  assert.equal(result.failedCount, 1);
  assert.equal(result.records.length, 2);
  assert.equal(
    result.records.every(
      (record) => record.partition === "test",
    ),
    true,
  );
  assert.equal(
    result.records.every(
      (record) => record.batchId === "global-test",
    ),
    true,
  );
  assert.equal(result.summary.symbolCount, 2);
  assert.equal(
    progress.filter((item) => item.status === "loading").length,
    3,
  );
});
test("新しい全銘柄評価で同じ時点の古い結果を置き換える", () => {
  const ordinary = resolvedRecord({
    id: "ordinary",
    source: "live",
    partition: null,
  });
  const oldGlobal = resolvedRecord({
    id: "old-global",
    batchId: "global-old",
    evaluationScope: "global",
    strategyReturn: -4,
  });
  const newGlobal = resolvedRecord({
    id: "new-global",
    batchId: "global-new",
    evaluationScope: "global",
    strategyReturn: 5,
  });
  const merged = mergeGlobalEvaluationRecords(
    [ordinary, oldGlobal],
    [newGlobal],
  );

  assert.equal(merged.records.length, 2);
  assert.equal(merged.duplicateCount, 1);
  assert.equal(
    merged.records.find(
      (record) => record.evaluationScope === "global",
    ).strategyReturn,
    5,
  );
});
