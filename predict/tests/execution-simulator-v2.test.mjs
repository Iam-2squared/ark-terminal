import test from "node:test";
import assert from "node:assert/strict";

import {
  ExecutionSimulatorV2,
  simulateExecution,
  simulateExecutionBatch,
} from "../trading/execution-simulator-v2.js";

test(
  "Execution Simulator v2 fills market buy order",
  () => {
    const result =
      simulateExecution({
        order: {
          id:
            "buy-1",

          symbol:
            "7203",

          side:
            "BUY",

          type:
            "MARKET",

          quantity:
            100,
        },

        market: {
          bid:
            2999,

          ask:
            3000,

          last:
            2999.5,

          volume:
            100000,

          liquidityScore:
            95,
        },

        baseSlippageBps:
          1,

        impactFactor:
          0,
      });

    assert.equal(
      result.version,
      "execution-simulator-v2",
    );

    assert.equal(
      result.status,
      "FILLED",
    );

    assert.equal(
      result.filledQuantity,
      100,
    );

    assert.ok(
      result.executionPrice >
      3000,
    );

    assert.ok(
      result.netCashFlow < 0,
    );
  },
);

test(
  "Execution Simulator v2 fills market sell order",
  () => {
    const result =
      simulateExecution({
        order: {
          symbol:
            "7203",

          side:
            "SELL",

          quantity:
            100,
        },

        market: {
          bid:
            2999,

          ask:
            3000,

          volume:
            100000,
        },

        baseSlippageBps:
          1,

        impactFactor:
          0,
      });

    assert.equal(
      result.status,
      "FILLED",
    );

    assert.ok(
      result.executionPrice <
      2999,
    );

    assert.ok(
      result.netCashFlow > 0,
    );
  },
);

test(
  "Execution Simulator v2 leaves unreachable limit order unfilled",
  () => {
    const result =
      simulateExecution({
        order: {
          symbol:
            "AAA",

          side:
            "BUY",

          type:
            "LIMIT",

          quantity:
            100,

          limitPrice:
            95,
        },

        market: {
          bid:
            99,

          ask:
            100,

          volume:
            10000,
        },
      });

    assert.equal(
      result.status,
      "UNFILLED",
    );

    assert.equal(
      result.filledQuantity,
      0,
    );

    assert.equal(
      result.executionPrice,
      null,
    );
  },
);

test(
  "Execution Simulator v2 respects buy limit price",
  () => {
    const result =
      simulateExecution({
        order: {
          symbol:
            "AAA",

          side:
            "BUY",

          type:
            "LIMIT",

          quantity:
            100,

          limitPrice:
            101,
        },

        market: {
          bid:
            99,

          ask:
            100,

          volume:
            10000,
        },

        baseSlippageBps:
          50,

        impactFactor:
          0,
      });

    assert.equal(
      result.status,
      "FILLED",
    );

    assert.ok(
      result.executionPrice <=
      101,
    );
  },
);

test(
  "Execution Simulator v2 produces partial fill under low volume",
  () => {
    const result =
      simulateExecution({
        order: {
          symbol:
            "LOWVOL",

          side:
            "BUY",

          quantity:
            1000,
        },

        market: {
          bid:
            99,

          ask:
            100,

          volume:
            1000,

          liquidityScore:
            50,
        },

        participationRate:
          0.1,

        minimumFillRatio:
          0,
      });

    assert.equal(
      result.status,
      "PARTIALLY_FILLED",
    );

    assert.ok(
      result.filledQuantity <
      1000,
    );

    assert.ok(
      result.remainingQuantity >
      0,
    );
  },
);

test(
  "Execution Simulator v2 calculates fees",
  () => {
    const result =
      simulateExecution({
        order: {
          symbol:
            "AAA",

          side:
            "BUY",

          quantity:
            100,
        },

        market: {
          bid:
            99,

          ask:
            100,

          volume:
            100000,
        },

        commissionRate:
          0.001,

        minimumCommission:
          5,

        exchangeFeeRate:
          0.0001,

        impactFactor:
          0,
      });

    assert.ok(
      result.fees.commission >=
      5,
    );

    assert.ok(
      result.fees.exchangeFee >
      0,
    );

    assert.equal(
      result.fees.total,
      Number(
        (
          result.fees.commission +
          result.fees.exchangeFee
        ).toFixed(6),
      ),
    );
  },
);

test(
  "Execution Simulator v2 rejects invalid quantity",
  () => {
    assert.throws(
      () =>
        simulateExecution({
          order: {
            symbol:
              "AAA",

            side:
              "BUY",

            quantity:
              0,
          },

          market: {
            last:
              100,
          },
        }),

      /quantity must be greater than zero/,
    );
  },
);

test(
  "Execution Simulator v2 batch handles missing market data",
  () => {
    const result =
      simulateExecutionBatch({
        orders: [
          {
            symbol:
              "AAA",

            side:
              "BUY",

            quantity:
              10,
          },

          {
            symbol:
              "BBB",

            side:
              "SELL",

            quantity:
              5,
          },
        ],

        marketBySymbol: {
          AAA: {
            bid:
              99,

            ask:
              100,

            volume:
              10000,
          },
        },
      });

    assert.equal(
      result.orderCount,
      2,
    );

    assert.equal(
      result.rejectedCount,
      1,
    );

    assert.equal(
      result.executions[1].status,
      "REJECTED",
    );
  },
);

test(
  "Execution Simulator v2 class is deterministic",
  () => {
    const engine =
      new ExecutionSimulatorV2({
        impactFactor:
          0,

        baseSlippageBps:
          2,
      });

    const input = {
      order: {
        id:
          "deterministic",

        symbol:
          "AAA",

        side:
          "BUY",

        quantity:
          100,
      },

      market: {
        bid:
          99,

        ask:
          100,

        volume:
          100000,
      },
    };

    assert.deepEqual(
      engine.execute(input),
      engine.execute(input),
    );
  },
);