import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAnalysisHistoryViewModel,
  mountAnalysisHistoryPanel,
  renderAnalysisHistoryPanel,
} from "../analysis/ai-analysis-history-panel.js";

function sampleHistory() {
  return [
    {
      id: "a",
      createdAt: "2026-08-02T00:00:00.000Z",
      symbol: "7203.T",
      action: "BUY",
      score: 84,
      confidence: 88,
      agreementRate: 75,
      executable: true,
      shares: 100,
      entryPrice: 1000,
    },
    {
      id: "b",
      createdAt: "2026-08-01T00:00:00.000Z",
      symbol: "9984.T",
      action: "HOLD",
      score: 60,
      confidence: 65,
      agreementRate: 50,
      executable: false,
      shares: 0,
      entryPrice: 0,
    },
  ];
}

test("History view model", () => {
  const result =
    buildAnalysisHistoryViewModel(
      sampleHistory(),
    );

  assert.equal(
    result.items.length,
    2,
  );

  assert.equal(
    result.summary.total,
    2,
  );

  assert.equal(
    result.summary.executableCount,
    1,
  );

  assert.equal(
    result.items[0].symbol,
    "7203.T",
  );
});

test("History panel HTML", () => {
  const html =
    renderAnalysisHistoryPanel(
      sampleHistory(),
    );

  assert.ok(
    html.includes(
      "AI ANALYSIS HISTORY",
    ),
  );

  assert.ok(
    html.includes(
      "分析履歴",
    ),
  );

  assert.ok(
    html.includes(
      "7203.T",
    ),
  );

  assert.ok(
    html.includes(
      "履歴を削除",
    ),
  );
});

test("Empty history is rendered", () => {
  const html =
    renderAnalysisHistoryPanel([]);

  assert.ok(
    html.includes(
      "まだAI分析履歴はありません",
    ),
  );
});

test("History panel mounts", () => {
  const container = {
    innerHTML: "",
    dataset: {},
  };

  const documentRef = {
    querySelector() {
      return container;
    },

    createElement() {
      return container;
    },

    body: {
      appendChild() {},
    },
  };

  const result =
    mountAnalysisHistoryPanel({
      history:
        sampleHistory(),

      documentRef,
    });

  assert.equal(
    result.mounted,
    true,
  );

  assert.equal(
    container.dataset
      .aiHistoryState,
    "ready",
  );

  assert.ok(
    container.innerHTML.includes(
      "7203.T",
    ),
  );
});