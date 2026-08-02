import test from "node:test";
import assert from "node:assert/strict";

import {
  createAccuracyDashboardViewModel,
} from "../analysis/accuracy-dashboard-view-model.js";

test("creates dashboard cards", () => {
  const vm = createAccuracyDashboardViewModel({
    summary:{
      accuracy:0.8,
      buy:{winRate:0.75},
      sell:{winRate:0.65},
    },
    tradePerformance:{
      profitFactor:1.8,
    },
    riskAdjusted:{
      sharpeRatio:1.2,
      sortinoRatio:1.6,
      calmarRatio:1.1,
      maxDrawdown:0.08,
    },
    health:{
      status:"healthy",
    },
  });

  assert.equal(vm.cards.length,8);
  assert.equal(vm.health.status,"healthy");
});
