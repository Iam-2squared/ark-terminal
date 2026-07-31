import assert from "node:assert/strict";
import test from "node:test";

import {
  finalizeScreenerBatch,
  planScreenerBatch,
} from "../../scripts/screener-progress.mjs";

function universe(count = 5) {
  return Array.from({ length: count }, (_value, index) => ({
    symbol: `${1000 + index}.T`,
  }));
}

test("全銘柄を先頭から指定件数だけ分割する", () => {
  const plan = planScreenerBatch({
    universe: universe(),
    batchSize: 2,
    now: "2026-07-31T00:00:00.000Z",
  });

  assert.deepEqual(
    plan.selected.map((entry) => entry.symbol),
    ["1000.T", "1001.T"],
  );

  const progress = finalizeScreenerBatch({
    plan,
    counts: {
      analyzed: 2,
    },
    completedAt: "2026-07-31T00:01:00.000Z",
  });

  assert.equal(progress.nextIndex, 2);
  assert.equal(progress.processedInCycle, 2);
  assert.equal(progress.cycleComplete, false);
});

test("保存した位置から再開し最終バッチでサイクルを完了する", () => {
  const firstPlan = planScreenerBatch({
    universe: universe(),
    batchSize: 2,
    now: "2026-07-31T00:00:00.000Z",
  });
  const firstProgress = finalizeScreenerBatch({
    plan: firstPlan,
    completedAt: "2026-07-31T00:01:00.000Z",
  });
  const secondPlan = planScreenerBatch({
    universe: universe(),
    progress: firstProgress,
    batchSize: 3,
    now: "2026-07-31T02:00:00.000Z",
  });

  assert.deepEqual(
    secondPlan.selected.map((entry) => entry.symbol),
    ["1002.T", "1003.T", "1004.T"],
  );

  const completed = finalizeScreenerBatch({
    plan: secondPlan,
    completedAt: "2026-07-31T02:01:00.000Z",
  });

  assert.equal(completed.processedInCycle, 5);
  assert.equal(completed.cycleComplete, true);
  assert.equal(completed.nextIndex, 0);
  assert.equal(completed.lastFullCycleAt, "2026-07-31T02:01:00.000Z");
});

test("完了後は次の更新サイクルを先頭から開始する", () => {
  const completedProgress = {
    ...finalizeScreenerBatch({
      plan: planScreenerBatch({
        universe: universe(2),
        batchSize: 2,
        now: "2026-07-31T00:00:00.000Z",
      }),
      completedAt: "2026-07-31T00:01:00.000Z",
    }),
    cycleNumber: 3,
  };
  const nextPlan = planScreenerBatch({
    universe: universe(2),
    progress: completedProgress,
    batchSize: 1,
    now: "2026-08-01T00:00:00.000Z",
  });

  assert.equal(nextPlan.cycleNumber, 4);
  assert.equal(nextPlan.startIndex, 0);
  assert.equal(nextPlan.processedBefore, 0);
});

test("JPX銘柄一覧が変わった場合は安全に先頭から再開する", () => {
  const originalPlan = planScreenerBatch({
    universe: universe(4),
    batchSize: 2,
  });
  const originalProgress = finalizeScreenerBatch({
    plan: originalPlan,
  });
  const changedPlan = planScreenerBatch({
    universe: universe(5),
    progress: originalProgress,
    batchSize: 2,
  });

  assert.equal(changedPlan.universeChanged, true);
  assert.equal(changedPlan.startIndex, 0);
  assert.equal(changedPlan.cycleNumber, 1);
});
