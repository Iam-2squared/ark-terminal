import assert from "node:assert/strict";
import test from "node:test";

import {
  buildExplainabilityViewModel,
  mountAIExplainability,
  renderAIExplainabilityPanel,
} from "../analysis/ai-explainability-panel.js";

function sampleResult() {
  return {
    symbol: "7203.T",
    action: "BUY",
    score: 84,
    confidence: 88,
    agreementRate: 75,
    approved: true,
    executable: true,

    buyFactors: [
      "上昇トレンド",
      "AI評価が高い",
    ],

    riskFactors: [
      "決算接近",
    ],
  };
}

test(
  "Explainability view model",
  () => {
    const result =
      buildExplainabilityViewModel(
        sampleResult(),
      );

    assert.equal(
      result.symbol,
      "7203.T",
    );

    assert.equal(
      result.action,
      "BUY",
    );

    assert.equal(
      result.strengths.length,
      3,
    );

    assert.equal(
      result.buyFactors.length,
      2,
    );
  },
);

test(
  "Explainability HTML",
  () => {
    const html =
      renderAIExplainabilityPanel(
        sampleResult(),
      );

    assert.ok(
      html.includes(
        "EXPLAINABLE AI",
      ),
    );

    assert.ok(
      html.includes(
        "AI判断の根拠",
      ),
    );

    assert.ok(
      html.includes(
        "上昇トレンド",
      ),
    );

    assert.ok(
      html.includes(
        "決算接近",
      ),
    );
  },
);

test(
  "Explainability panel mounts",
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
      mountAIExplainability({
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
        .aiExplainabilityState,
      "ready",
    );

    assert.ok(
      container.innerHTML.includes(
        "EXPLAINABLE AI",
      ),
    );
  },
);

test(
  "Blocked result explains rejection",
  () => {
    const result =
      buildExplainabilityViewModel({
        approved: false,
        executable: false,
      });

    assert.ok(
      result.conclusion.includes(
        "除外",
      ),
    );
  },
);