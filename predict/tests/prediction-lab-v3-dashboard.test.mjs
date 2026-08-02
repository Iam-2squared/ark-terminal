import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPredictionLabV3ViewModel,
  mountPredictionLabV3Dashboard,
  renderPredictionLabV3Dashboard,
} from "../analysis/prediction-lab-v3-dashboard.js";

function sampleInput() {
  return {
    analysis: {
      dashboard: {
        action: "BUY",
        score: 84,
        confidence: 88,
        macro: "BULLISH",
        regime: "BULL",
      },

      decision: {
        buyFactors: [
          "Trend strong",
        ],

        riskFactors: [
          "Earnings approaching",
        ],
      },
    },

    tradePlan: {
      action: "BUY",
      executable: true,

      sizing: {
        shares: 100,
        estimatedCost: 100000,
      },

      levels: {
        entryPrice: 1000,
        stopPrice: 950,
        targetPrice: 1100,
      },
    },

    alerts: {
      total: 3,
      unread: 2,
      highSeverity: 1,
    },

    runtime: {
      cache: 4,

      queue: {
        completed: 10,
      },

      performance: {
        average: 12.5,
      },
    },

    learning: {
      score: 6,
      confidence: 0.8,
      trend: "UP",
    },

    marketIntelligence: {
      enabled: true,
      status: "ready",
      participating: true,
      selectedHorizon: 5,
      featureConfidence: 88,
      featureCoverage: 92,
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
  "Prediction Lab v3 view model",
  () => {
    const result =
      buildPredictionLabV3ViewModel(
        sampleInput(),
      );

    assert.equal(
      result.action,
      "BUY",
    );

    assert.equal(
      result.score,
      84,
    );

    assert.equal(
      result.tradePlan.shares,
      100,
    );

    assert.equal(
      result.alerts.unread,
      2,
    );

    assert.equal(
      result.marketIntelligence
        .predictions
        .length,
      5,
    );

    assert.equal(
      result.marketIntelligence
        .selectedHorizon,
      5,
    );
  },
);

test(
  "Prediction Lab v3 HTML",
  () => {
    const html =
      renderPredictionLabV3Dashboard(
        sampleInput(),
      );

    assert.ok(
      html.includes(
        "Prediction Lab v3",
      ),
    );

    assert.ok(
      html.includes(
        "推奨株数",
      ),
    );

    assert.ok(
      html.includes(
        "未読アラート",
      ),
    );

    assert.ok(
      html.includes(
        "Trend strong",
      ),
    );

    assert.ok(
      html.includes(
        "MARKET INTELLIGENCE",
      ),
    );

    assert.ok(
      html.includes(
        "5日先",
      ),
    );
  },
);

test(
  "Prediction Lab v3 mounts",
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
      mountPredictionLabV3Dashboard({
        input:
          sampleInput(),

        documentRef,
      });

    assert.equal(
      result.mounted,
      true,
    );

    assert.equal(
      container.dataset
        .predictionLabV3Status,
      "ready",
    );

    assert.ok(
      container.innerHTML.includes(
        "Prediction Lab v3",
      ),
    );
  },
);
