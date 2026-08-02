import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAIResultViewModel,
  mountAIResult,
  renderAIResult,
  renderAIResultError,
} from "../analysis/ai-result-presenter.js";

function sampleResult() {
  return {
    symbol:
      "7203.T",

    action:
      "BUY",

    score:
      84,

    confidence:
      88,

    agreementRate:
      75,

    executable:
      true,

    shares:
      100,

    entryPrice:
      1000,

    stopPrice:
      950,

    targetPrice:
      1100,

    estimatedCost:
      100000,

    buyFactors: [
      "Trend strong",
    ],

    riskFactors: [
      "Earnings approaching",
    ],

    marketIntelligence: {
      enabled: true,
      status: "ready",
      participating: true,
      selectedHorizon: 5,
      featureCoverage: 90,
      predictions: [1, 3, 5, 10, 20].map((horizon) => ({
        horizon,
        direction: "上昇",
        score: 82,
        confidence: 88,
        status: "ready",
      })),
    },
  };
}

test(
  "AI result view model",
  () => {
    const view =
      buildAIResultViewModel(
        sampleResult(),
      );

    assert.equal(
      view.symbol,
      "7203.T",
    );

    assert.equal(
      view.action,
      "BUY",
    );

    assert.equal(
      view.shares,
      100,
    );

    assert.equal(
      view.executable,
      true,
    );

    assert.equal(
      view.marketIntelligence
        .predictions
        .length,
      5,
    );
  },
);

test(
  "AI result HTML",
  () => {
    const html =
      renderAIResult(
        sampleResult(),
      );

    assert.ok(
      html.includes(
        "AI ANALYSIS RESULT",
      ),
    );

    assert.ok(
      html.includes(
        "7203.T",
      ),
    );

    assert.ok(
      html.includes(
        "Trend strong",
      ),
    );

    assert.ok(
      html.includes(
        "推奨株数",
      ),
    );

    assert.ok(
      html.includes(
        "MARKET INTELLIGENCE",
      ),
    );

    assert.ok(
      html.includes(
        "20日先",
      ),
    );
  },
);

test(
  "AI result error HTML",
  () => {
    const html =
      renderAIResultError({
        message:
          "network error",
      });

    assert.ok(
      html.includes(
        "network error",
      ),
    );

    assert.ok(
      html.includes(
        "AI分析に失敗しました",
      ),
    );
  },
);

test(
  "AI result mounts",
  () => {
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
      mountAIResult({
        result:
          sampleResult(),

        documentRef,
      });

    assert.equal(
      result.mounted,
      true,
    );

    assert.equal(
      container.dataset
        .aiResultState,
      "ready",
    );

    assert.ok(
      container.innerHTML.includes(
        "AI ANALYSIS RESULT",
      ),
    );
  },
);
