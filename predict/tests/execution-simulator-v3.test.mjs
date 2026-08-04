import test from "node:test";
import assert from "node:assert/strict";

import {
  ExecutionSimulatorV3,
} from "../paper/execution-simulator-v3.js";

const NOW =
  "2026-08-04T14:00:00.000Z";

function market(
  overrides = {},
) {
  return {
    bid:
      99,

    ask:
      101,

    last:
      100,

    volume:
      10000,

    availableLiquidity:
      1000,

    volatilityPercent:
      0,

    timestamp:
      NOW,

    ...overrides,
  };
}

function simulator(
  overrides = {},
) {
  return new ExecutionSimulatorV3({
    commissionRate:
      0,

    baseSlippageRate:
      0,

    marketImpactFactor:
      0,

    maximumParticipationRate:
      1,

    fillProbability:
      1,

    ...overrides,
  });
}

test(
  "Executes market buy at ask",
  () => {
    const engine =
      simulator();

    const order =
      engine.submitOrder({
        symbol:
          "7203.T",

        side:
          "BUY",

        quantity:
          10,

        timestamp:
          NOW,
      });

    const result =
      engine.simulateExecution({
        orderId:
          order.id,

        market:
          market(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.order.status,
      "FILLED",
    );

    assert.equal(
      result.execution
        .executionPrice,
      101,
    );
  },
);

test(
  "Executes market sell at bid",
  () => {
    const engine =
      simulator();

    const order =
      engine.submitOrder({
        symbol:
          "7203.T",

        side:
          "SELL",

        quantity:
          10,

        timestamp:
          NOW,
      });

    const result =
      engine.simulateExecution({
        orderId:
          order.id,

        market:
          market(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.execution
        .executionPrice,
      99,
    );
  },
);

test(
  "Limit buy waits above limit",
  () => {
    const engine =
      simulator();

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        type:
          "LIMIT",

        quantity:
          10,

        limitPrice:
          100,

        timestamp:
          NOW,
      });

    const result =
      engine.simulateExecution({
        orderId:
          order.id,

        market:
          market({
            ask:
              101,
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      result.execution,
      null,
    );

    assert.equal(
      result.reason,
      "LIMIT_NOT_MARKETABLE",
    );
  },
);

test(
  "Limit buy fills below limit",
  () => {
    const engine =
      simulator();

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        type:
          "LIMIT",

        quantity:
          10,

        limitPrice:
          100,

        timestamp:
          NOW,
      });

    const result =
      engine.simulateExecution({
        orderId:
          order.id,

        market:
          market({
            ask:
              99,
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      result.order.status,
      "FILLED",
    );
  },
);

test(
  "Stop buy waits before trigger",
  () => {
    const engine =
      simulator();

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        type:
          "STOP",

        quantity:
          10,

        stopPrice:
          105,

        timestamp:
          NOW,
      });

    const result =
      engine.simulateExecution({
        orderId:
          order.id,

        market:
          market({
            last:
              100,
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      result.reason,
      "STOP_NOT_TRIGGERED",
    );
  },
);

test(
  "Stop buy executes after trigger",
  () => {
    const engine =
      simulator();

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        type:
          "STOP",

        quantity:
          10,

        stopPrice:
          105,

        timestamp:
          NOW,
      });

    const result =
      engine.simulateExecution({
        orderId:
          order.id,

        market:
          market({
            last:
              106,

            ask:
              106,
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      result.order.triggered,
      true,
    );

    assert.equal(
      result.order.status,
      "FILLED",
    );
  },
);

test(
  "Supports partial fills",
  () => {
    const engine =
      simulator();

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        quantity:
          100,

        timestamp:
          NOW,
      });

    const first =
      engine.simulateExecution({
        orderId:
          order.id,

        market:
          market({
            availableLiquidity:
              40,
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      first.order.status,
      "PARTIALLY_FILLED",
    );

    assert.equal(
      first.order.remainingQuantity,
      60,
    );

    const second =
      engine.simulateExecution({
        orderId:
          order.id,

        market:
          market({
            availableLiquidity:
              100,
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      second.order.status,
      "FILLED",
    );
  },
);

test(
  "Applies participation limit",
  () => {
    const engine =
      simulator({
        maximumParticipationRate:
          0.1,
      });

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        quantity:
          500,

        timestamp:
          NOW,
      });

    const result =
      engine.simulateExecution({
        orderId:
          order.id,

        market:
          market({
            volume:
              1000,

            availableLiquidity:
              1000,
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      result.execution.quantity,
      100,
    );
  },
);

test(
  "Applies commission",
  () => {
    const engine =
      simulator({
        commissionRate:
          0.01,
      });

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        quantity:
          10,

        timestamp:
          NOW,
      });

    const result =
      engine.simulateExecution({
        orderId:
          order.id,

        market:
          market({
            volatilityPercent:
              0,
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      result.execution.commission,
      10.1,
    );
  },
);

test(
  "Applies slippage",
  () => {
    const engine =
      simulator({
        baseSlippageRate:
          0.01,
      });

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        quantity:
          10,

        timestamp:
          NOW,
      });

    const result =
      engine.simulateExecution({
        orderId:
          order.id,

        market:
          market(),

        timestamp:
          NOW,
      });

    assert.ok(
      result.execution
        .executionPrice >
      101,
    );
  },
);

test(
  "Cancels open order",
  () => {
    const engine =
      simulator();

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        quantity:
          10,

        timestamp:
          NOW,
      });

    const result =
      engine.cancelOrder({
        orderId:
          order.id,

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "CANCELLED",
    );
  },
);

test(
  "Expires day orders",
  () => {
    const engine =
      simulator();

    engine.submitOrder({
      symbol:
        "TEST",

      side:
        "BUY",

      quantity:
        10,

      timeInForce:
        "DAY",

      timestamp:
        NOW,
    });

    const expired =
      engine.expireDayOrders({
        timestamp:
          NOW,
      });

    assert.equal(
      expired.length,
      1,
    );

    assert.equal(
      expired[0].status,
      "EXPIRED",
    );
  },
);

test(
  "Processes market snapshot",
  () => {
    const engine =
      simulator();

    engine.submitOrder({
      symbol:
        "AAA",

      side:
        "BUY",

      quantity:
        10,

      timestamp:
        NOW,
    });

    engine.submitOrder({
      symbol:
        "BBB",

      side:
        "SELL",

      quantity:
        10,

      timestamp:
        NOW,
    });

    const results =
      engine.processMarketSnapshot({
        markets: {
          AAA:
            market(),

          BBB:
            market(),
        },

        timestamp:
          NOW,
      });

    assert.equal(
      results.length,
      2,
    );

    assert.equal(
      engine
        .getExecutions()
        .length,
      2,
    );
  },
);

test(
  "Returns execution statistics",
  () => {
    const engine =
      simulator();

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        quantity:
          10,

        timestamp:
          NOW,
      });

    engine.simulateExecution({
      orderId:
        order.id,

      market:
        market(),

      timestamp:
        NOW,
    });

    const statistics =
      engine.getStatistics();

    assert.equal(
      statistics.orderCount,
      1,
    );

    assert.equal(
      statistics.executionCount,
      1,
    );

    assert.equal(
      statistics.filledOrderCount,
      1,
    );
  },
);

test(
  "Reset clears simulator",
  () => {
    const engine =
      simulator();

    engine.submitOrder({
      symbol:
        "TEST",

      side:
        "BUY",

      quantity:
        10,

      timestamp:
        NOW,
    });

    engine.reset();

    assert.equal(
      engine.getOrders().length,
      0,
    );

    assert.equal(
      engine
        .getExecutions()
        .length,
      0,
    );
  },
);

test(
  "Validates timestamp",
  () => {
    const engine =
      simulator();

    assert.throws(
      () =>
        engine.submitOrder({
          symbol:
            "TEST",

          side:
            "BUY",

          quantity:
            10,

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);