import assert from "node:assert/strict";
import test from "node:test";

import {
  buildLearningDashboardData,
  createSelfEvolutionViewModel,
  exportLearningDashboardJSON,
  buildAiRecommendation,
  buildAiSummaryCard,
  renderSelfEvolutionDashboard,
} from "../learning/self-evolution-ui.js";

function samplePlan() {
  return {
    cycle: {
      result: {
        promoted: true,
      },

      decision: {
        decision: {
          action: "PROMOTE",
        },
      },
    },

    validationReport: {
      comparison: {
        approved: true,
        improvementScore: 4.25,
      },

      weightChanges: [
        {
          indicator: "rsi",
        },
      ],
    },

    health: {
      healthy: true,
    },
  };
}

test(
  "Self evolution view model",
  () => {
    const view =
      createSelfEvolutionViewModel({
        plan: samplePlan(),

        auditHistory: [
          {
            id: "a",
            action: "PROMOTE",
            promoted: true,
            retraining: false,
            improvementScore: 4.25,
          },
        ],
      });

    assert.equal(
      view.action,
      "PROMOTE",
    );

    assert.equal(
      view.approvedByBacktest,
      true,
    );

    assert.equal(
      view.changedIndicators,
      1,
    );

    assert.equal(
      view.improvementLabel,
      "+4.25",
    );
  },
);

test(
  "Self evolution dashboard HTML",
  () => {
    const html =
      renderSelfEvolutionDashboard({
        plan: samplePlan(),
        auditHistory: [],
      });

    assert.ok(
  html.includes(
    "自己改善ステータス",
  ),
);

assert.ok(
  html.includes(
    "昇格候補",
  ),
);

assert.ok(
  html.includes(
    "バックテスト",
  ),
);
  },
);

test(
  "Learning dashboard data",
  () => {
    const data =
      buildLearningDashboardData({
        plan: samplePlan(),

        registry: [
          {},
          {},
        ],

        auditHistory: [
          {
            id: "1",
            action: "PROMOTE",
            promoted: true,
            retraining: false,
            improvementScore: 5,
          },
        ],
      });

    assert.equal(
      data.status,
      "PROMOTE",
    );

    assert.equal(
      data.registrySize,
      2,
    );
  },
);

test(
  "Learning dashboard JSON",
  () => {
    const json =
      exportLearningDashboardJSON({
        plan: samplePlan(),
      });

    const object =
      JSON.parse(json);

    assert.equal(
      object.status,
      "PROMOTE",
    );
  },
);
test("AI recommendation",()=>{

    const dashboard=

        buildLearningDashboardData({

            plan:samplePlan(),

            registry:[{}]

        });

    const result=

        buildAiRecommendation({

            dashboard

        });

    assert.ok(

        result.recommendation.length>=2

    );

});

test("AI summary card",()=>{

    const dashboard=

        buildLearningDashboardData({

            plan:samplePlan()

        });

    const card=

        buildAiSummaryCard({

            dashboard

        });

    assert.equal(

        card.title,

        "AI Learning Summary"

    );

});

