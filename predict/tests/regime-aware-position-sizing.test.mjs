import assert from "node:assert/strict";
import test from "node:test";

import {
  buildRegimeAwarePositionPlan,
  calculateRegimeAdjustedAllocation,
  compareRegimePositionPlans,
} from "../analysis/regime-aware-position-sizing.js";

test(
  "Bull market increases adjusted allocation",
  () => {
    const result =
      calculateRegimeAdjustedAllocation({
        baseAllocation: 0.4,

        regime: {
          riskMultiplier: 1.2,
        },

        confidence: 100,
      });

    assert.equal(
      result.adjustedAllocation,
      0.48,
    );
  },
);

test(
  "Bear market reduces position size",
  () => {
    const bull =
      buildRegimeAwarePositionPlan({
        capital: 1000000,
        price: 1000,
        baseAllocation: 0.5,
        confidence: 90,
        riskLevel: 20,
        lotSize: 100,

        market: {
          trendScore: 90,
          momentum: 85,
          breadth: 80,
          volatility: 20,
          vix: 15,
        },
      });

    const bear =
      buildRegimeAwarePositionPlan({
        capital: 1000000,
        price: 1000,
        baseAllocation: 0.5,
        confidence: 90,
        riskLevel: 20,
        lotSize: 100,

        market: {
          trendScore: 20,
          momentum: 25,
          breadth: 30,
          volatility: 55,
          vix: 30,
        },
      });

    assert.equal(
      bull.regime.regime,
      "BULL",
    );

    assert.equal(
      bear.regime.regime,
      "BEAR",
    );

    assert.ok(
      bull.sizing.executableShares >
      bear.sizing.executableShares,
    );
  },
);

test(
  "Position uses whole lots",
  () => {
    const result =
      buildRegimeAwarePositionPlan({
        capital: 500000,
        price: 800,
        baseAllocation: 0.5,
        confidence: 90,
        riskLevel: 20,
        lotSize: 100,

        market: {
          trendScore: 90,
          momentum: 85,
          breadth: 80,
          vix: 15,
        },
      });

    assert.equal(
      result.sizing.executableShares %
      100,
      0,
    );

    assert.ok(
      result.sizing.estimatedCost <=
      500000,
    );
  },
);

test(
  "Scenario comparison returns all regimes",
  () => {
    const result =
      compareRegimePositionPlans({
        capital: 1000000,
        price: 1000,
        baseAllocation: 0.4,
        confidence: 90,
        riskLevel: 20,
      });

    assert.equal(
      result.bull.regime.regime,
      "BULL",
    );

    assert.equal(
      result.bear.regime.regime,
      "BEAR",
    );

    assert.equal(
      result.highVolatility
        .regime
        .regime,
      "HIGH_VOLATILITY",
    );

    assert.ok(
      result.bull.allocation
        .adjustedAllocation >
      result.bear.allocation
        .adjustedAllocation,
    );
  },
);