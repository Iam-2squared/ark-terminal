import assert from "node:assert/strict";
import test from "node:test";

import {
  createTradePlanViewModel,
  mountFinalTradePlan,
  renderFinalTradePlan,
} from "../analysis/final-trade-plan-ui.js";

function samplePlan() {
  return {
    symbol: "7203.T",

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
      riskRewardRatio: 2,
    },

    estimatedLoss: 5000,
    estimatedProfit: 10000,
    reasons: [],
  };
}

test(
  "Trade plan view model",
  () => {
    const view =
      createTradePlanViewModel(
        samplePlan(),
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
      view.labels.shares,
      "100株",
    );

    assert.equal(
      view.labels.riskRewardRatio,
      "1 : 2.00",
    );
  },
);

test(
  "Trade plan HTML",
  () => {
    const html =
      renderFinalTradePlan(
        samplePlan(),
      );

    assert.ok(
      html.includes(
        "FINAL TRADE PLAN",
      ),
    );

    assert.ok(
      html.includes(
        "推奨株数",
      ),
    );

    assert.ok(
      html.includes(
        "想定損失",
      ),
    );

    assert.ok(
      html.includes(
        "7203.T",
      ),
    );
  },
);

test(
  "No trade reasons are rendered",
  () => {
    const html =
      renderFinalTradePlan({
        ...samplePlan(),

        action:
          "NO TRADE",

        executable:
          false,

        reasons: [
          "confidence_below_minimum",
        ],
      });

    assert.ok(
      html.includes(
        "confidence_below_minimum",
      ),
    );
  },
);

test(
  "Trade plan mounts into document",
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
      mountFinalTradePlan({
        plan:
          samplePlan(),

        documentRef,
      });

    assert.equal(
      result.mounted,
      true,
    );

    assert.equal(
      container.dataset
        .finalTradePlanStatus,
      "ready",
    );

    assert.ok(
      container.innerHTML.includes(
        "FINAL TRADE PLAN",
      ),
    );
  },
);