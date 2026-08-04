import test from "node:test";
import assert from "node:assert/strict";

import {
  RiskManagementEngineV3,
  calculatePositionSize,
  calculateValueAtRisk,
  evaluateOrderRisk,
  evaluatePortfolioRisk,
} from "../portfolio/risk-management-engine-v3.js";

const NOW =
  "2026-08-04T13:00:00.000Z";

function healthyPortfolio() {
  return {
    cash:
      70000,

    equity:
      100000,

    marketValue:
      30000,

    dailyReturnPercent:
      0.5,

    drawdownPercent:
      2,

    portfolioBeta:
      0.8,

    portfolioVolatility:
      18,

    positions: [
      {
        symbol:
          "7203.T",

        sector:
          "AUTO",

        quantity:
          10,

        averagePrice:
          1000,

        marketPrice:
          1100,

        beta:
          1,

        volatility:
          20,
      },

      {
        symbol:
          "8306.T",

        sector:
          "BANKS",

        quantity:
          100,

        averagePrice:
          100,

        marketPrice:
          110,

        beta:
          0.8,

        volatility:
          18,
      },
    ],
  };
}

test(
  "Calculates risk-based position size",
  () => {
    const result =
      calculatePositionSize({
        equity:
          100000,

        entryPrice:
          100,

        stopPrice:
          95,

        riskPerTradePercent:
          1,

        maximumPositionPercent:
          20,
      });

    assert.equal(
      result.quantity,
      200,
    );

    assert.equal(
      result.riskBudget,
      1000,
    );
  },
);

test(
  "Rounds position size to lot size",
  () => {
    const result =
      calculatePositionSize({
        equity:
          100000,

        entryPrice:
          110,

        stopPrice:
          100,

        riskPerTradePercent:
          1,

        maximumPositionPercent:
          20,

        lotSize:
          100,
      });

    assert.equal(
      result.quantity %
        100,
      0,
    );
  },
);

test(
  "Calculates value at risk",
  () => {
    const result =
      calculateValueAtRisk({
        equity:
          100000,

        volatilityPercent:
          2,

        confidenceMultiplier:
          1.65,
      });

    assert.equal(
      result.value,
      3300,
    );

    assert.equal(
      result.percent,
      3.3,
    );
  },
);

test(
  "Allows healthy portfolio",
  () => {
    const result =
      evaluatePortfolioRisk({
        portfolio:
          healthyPortfolio(),

        timestamp:
          NOW,
      });

    assert.notEqual(
      result.status,
      "BLOCKED",
    );

    assert.equal(
      result.decision,
      "ALLOW",
    );
  },
);

test(
  "Blocks excessive portfolio exposure",
  () => {
    const portfolio =
      healthyPortfolio();

    portfolio.cash = 0;
    portfolio.equity = 100000;
    portfolio.positions = [
      {
        symbol:
          "AAA",

        sector:
          "TECH",

        quantity:
          1000,

        averagePrice:
          100,

        marketPrice:
          100,
      },
    ];

    const result =
      evaluatePortfolioRisk({
        portfolio,

        limits: {
          maximumExposurePercent:
            80,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "BLOCKED",
    );

    assert.ok(
      result.blockers.includes(
        "MAXIMUM_EXPOSURE_EXCEEDED",
      ),
    );
  },
);

test(
  "Blocks maximum drawdown",
  () => {
    const portfolio =
      healthyPortfolio();

    portfolio.drawdownPercent =
      20;

    const result =
      evaluatePortfolioRisk({
        portfolio,

        limits: {
          maximumDrawdownPercent:
            15,
        },

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "MAXIMUM_DRAWDOWN_REACHED",
      ),
    );
  },
);

test(
  "Blocks daily loss limit",
  () => {
    const portfolio =
      healthyPortfolio();

    portfolio.dailyReturnPercent =
      -4;

    const result =
      evaluatePortfolioRisk({
        portfolio,

        limits: {
          maximumDailyLossPercent:
            3,
        },

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "DAILY_LOSS_LIMIT_REACHED",
      ),
    );
  },
);

test(
  "Allows affordable order",
  () => {
    const result =
      evaluateOrderRisk({
        order: {
          symbol:
            "6758.T",

          side:
            "BUY",

          quantity:
            10,

          price:
            1000,

          stopPrice:
            950,

          sector:
            "TECH",

          confidence:
            80,

          riskScore:
            30,
        },

        portfolio:
          healthyPortfolio(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.decision,
      "ALLOW",
    );

    assert.equal(
      result.approvedQuantity,
      10,
    );
  },
);

test(
  "Blocks order with insufficient cash",
  () => {
    const result =
      evaluateOrderRisk({
        order: {
          symbol:
            "6758.T",

          side:
            "BUY",

          quantity:
            1000,

          price:
            1000,

          stopPrice:
            990,

          sector:
            "TECH",
        },

        portfolio:
          healthyPortfolio(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.decision,
      "BLOCK",
    );

    assert.ok(
      result.blockers.includes(
        "INSUFFICIENT_CASH",
      ),
    );
  },
);

test(
  "Blocks oversize position",
  () => {
    const result =
      evaluateOrderRisk({
        order: {
          symbol:
            "6758.T",

          side:
            "BUY",

          quantity:
            40,

          price:
            1000,

          stopPrice:
            990,

          sector:
            "TECH",
        },

        portfolio:
          healthyPortfolio(),

        limits: {
          maximumPositionPercent:
            20,
        },

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "MAXIMUM_POSITION_EXCEEDED",
      ),
    );
  },
);

test(
  "Blocks excessive order risk",
  () => {
    const result =
      evaluateOrderRisk({
        order: {
          symbol:
            "6758.T",

          side:
            "BUY",

          quantity:
            100,

          price:
            1000,

          stopPrice:
            900,

          sector:
            "TECH",
        },

        portfolio: {
          ...healthyPortfolio(),

          cash:
            200000,

          equity:
            300000,
        },

        limits: {
          maximumOrderRiskPercent:
            2,
        },

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "ORDER_RISK_LIMIT_EXCEEDED",
      ),
    );
  },
);

test(
  "Warns when stop price is missing",
  () => {
    const result =
      evaluateOrderRisk({
        order: {
          symbol:
            "6758.T",

          side:
            "BUY",

          quantity:
            5,

          price:
            1000,

          sector:
            "TECH",
        },

        portfolio:
          healthyPortfolio(),

        timestamp:
          NOW,
      });

    assert.ok(
      result.warnings.includes(
        "STOP_PRICE_NOT_DEFINED",
      ),
    );
  },
);

test(
  "Blocks sell above owned quantity",
  () => {
    const result =
      evaluateOrderRisk({
        order: {
          symbol:
            "7203.T",

          side:
            "SELL",

          quantity:
            20,

          price:
            1100,

          sector:
            "AUTO",
        },

        portfolio:
          healthyPortfolio(),

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "INSUFFICIENT_POSITION",
      ),
    );
  },
);

test(
  "Kill switch blocks every order",
  () => {
    const engine =
      new RiskManagementEngineV3();

    engine.activateKillSwitch(
      "MANUAL_TEST",
    );

    const result =
      engine.evaluateOrder({
        order: {
          symbol:
            "6758.T",

          side:
            "BUY",

          quantity:
            1,

          price:
            1000,

          stopPrice:
            950,

          sector:
            "TECH",
        },

        portfolio:
          healthyPortfolio(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.decision,
      "BLOCK",
    );

    assert.equal(
      result.approvedQuantity,
      0,
    );

    assert.ok(
      result.blockers.includes(
        "KILL_SWITCH_ACTIVE",
      ),
    );
  },
);

test(
  "Kill switch can be deactivated",
  () => {
    const engine =
      new RiskManagementEngineV3();

    engine.activateKillSwitch();
    engine.deactivateKillSwitch();

    assert.equal(
      engine.getState()
        .killSwitch,
      false,
    );
  },
);

test(
  "Engine stores evaluation history",
  () => {
    const engine =
      new RiskManagementEngineV3();

    engine.evaluatePortfolio({
      portfolio:
        healthyPortfolio(),

      timestamp:
        NOW,
    });

    assert.equal(
      engine.getHistory().length,
      1,
    );

    assert.ok(
      engine.latest(),
    );
  },
);

test(
  "Engine reset clears state",
  () => {
    const engine =
      new RiskManagementEngineV3();

    engine.activateKillSwitch();

    engine.evaluatePortfolio({
      portfolio:
        healthyPortfolio(),

      timestamp:
        NOW,
    });

    engine.reset();

    assert.equal(
      engine.getHistory().length,
      0,
    );

    assert.equal(
      engine.getState()
        .killSwitch,
      false,
    );
  },
);

test(
  "Validates timestamp",
  () => {
    assert.throws(
      () =>
        evaluatePortfolioRisk({
          portfolio:
            healthyPortfolio(),

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);