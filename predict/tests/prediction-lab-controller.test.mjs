import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPredictionLabViewModel,
  normalizePredictionLabInput,
  renderPredictionLabV2,
} from "../analysis/prediction-lab-controller.js";

function strongInput() {
  return {
    state: {
      analysis: {
        technicalScore: 88,
        totalScore: 90,
        dataQualityScore: 95,
      },

      prediction: {
        confidence: 90,
      },

      indicators: {
        rsi: 64,

        adx: {
          value: 31,
        },

        atr: {
          percent: 2,
        },
      },
    },

    macroInput: {
      nikkei: 1,
      nasdaq: 2,
      sox: 3,
      vix: 18,
    },

    marketInput: {
      trendScore: 85,
      volatility: 15,
      adx: 31,
      rsi: 64,
      vix: 18,
    },

    history: [
      {
        return: 5,
      },

      {
        return: 3,
      },

      {
        return: -1,
      },

      {
        return: 4,
      },
    ],
  };
}

test(
  "Prediction Lab input is normalized",
  () => {
    const result =
      normalizePredictionLabInput(
        strongInput(),
      );

    assert.equal(
      result.history.length,
      4,
    );

    assert.equal(
      result.macroInput.sox,
      3,
    );
  },
);

test(
  "Prediction Lab view model is generated",
  () => {
    const result =
      buildPredictionLabViewModel(
        strongInput(),
      );

    assert.equal(
      result.version,
      "prediction-lab-v2",
    );

    assert.ok(
      result.score > 0,
    );

    assert.equal(
      typeof result.confidence,
      "number",
    );

    assert.ok(
      Array.isArray(
        result.buyFactors,
      ),
    );
  },
);

test(
  "Prediction Lab v2 HTML is rendered",
  () => {
    const html =
      renderPredictionLabV2(
        strongInput(),
      );

    assert.ok(
      html.includes(
        "PREDICTION LAB v2",
      ),
    );

    assert.ok(
      html.includes(
        "AI総合分析",
      ),
    );

    assert.ok(
      html.includes(
        "買い要因",
      ),
    );

    assert.ok(
      html.includes(
        "リスク要因",
      ),
    );
  },
);