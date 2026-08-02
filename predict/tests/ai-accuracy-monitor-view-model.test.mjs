import assert from "node:assert/strict";
import test from "node:test";

import { buildAIAccuracyMonitorReport } from "../analysis/ai-accuracy-monitor-engine.js";
import { buildAIAccuracyMonitorViewModel } from "../analysis/ai-accuracy-monitor-view-model.js";

function outcome({
  id,
  hit,
  source = "live",
  partition = null,
  period = 5,
  index = 0,
} = {}) {
  return {
    id,
    status: "resolved",
    hit,
    source,
    partition,
    period,
    actualReturn: hit ? 2 : -1,
    expectedReturn: 0.5,
    confidence: { score: 70 },
    resolvedAt: new Date(Date.UTC(2026, 0, index + 1)).toISOString(),
  };
}

test("No-data view model never renders fake zero-percent accuracy", () => {
  const report = buildAIAccuracyMonitorReport([], {
    generatedAt: 0,
  });
  const view = buildAIAccuracyMonitorViewModel(report);

  assert.equal(view.accuracy, "--");
  assert.equal(view.source.badge, "未算出");
  assert.equal(view.status.label, "データ待ち");
  assert.equal(view.horizons.length, 5);
  assert.equal(view.executionAllowed, false);
});

test("Walk Forward fallback is explicitly labelled as a validation value", () => {
  const report = buildAIAccuracyMonitorReport(
    [
      outcome({
        id: "a",
        index: 1,
        hit: true,
        source: "walk-forward",
        partition: "test",
      }),
      outcome({
        id: "b",
        index: 2,
        hit: false,
        source: "walk-forward",
        partition: "test",
      }),
    ],
    { generatedAt: 0 },
  );
  const view = buildAIAccuracyMonitorViewModel(report);

  assert.equal(view.accuracy, "50.0%");
  assert.equal(view.source.badge, "検証値");
  assert.match(view.source.label, /Walk Forward 最終テスト/);
  assert.match(view.intervalLabel, /95%信頼区間/);
});

test("Observed accuracy, horizon and forecast metrics are formatted", () => {
  const report = buildAIAccuracyMonitorReport(
    [
      outcome({ id: "a", index: 1, hit: true, period: 1 }),
      outcome({ id: "b", index: 2, hit: true, period: 5 }),
    ],
    { generatedAt: 0 },
  );
  const view = buildAIAccuracyMonitorViewModel(report);

  assert.equal(view.source.badge, "実績値");
  assert.equal(view.accuracy, "100.0%");
  assert.equal(view.horizons.find((item) => item.horizon === 1).accuracy, "100.0%");
  assert.equal(view.horizons.find((item) => item.horizon === 20).accuracy, "--");
  assert.match(view.metrics.find((item) => item.label.includes("MAE")).value, /pt$/);
  assert.match(view.notice, /保証しません/);
});

test("Read errors produce a safe unavailable view", () => {
  const view = buildAIAccuracyMonitorViewModel(null, {
    error: new Error("storage failed"),
  });

  assert.equal(view.status.label, "読込エラー");
  assert.equal(view.accuracy, "--");
  assert.match(view.message, /読み込めませんでした/);
});
