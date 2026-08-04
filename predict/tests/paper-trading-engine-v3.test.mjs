import test from "node:test";
import assert from "node:assert/strict";

import {
  PaperTradingEngineV3,
} from "../paper/paper-trading-engine-v3.js";

const NOW =
  "2026-08-04T11:00:00.000Z";

test(
  "Executes market buy order",
  () => {
    const engine =
      new PaperTradingEngineV3({
        initialCash:
          100000,

        maximumPositionPercent:
          100,
      });

    engine.updateMarketPrice({
      symbol:
        "7203.T",

      price:
        1000,

      timestamp:
        NOW,
    });

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
      engine.executeOrder({
        orderId:
          order.id,

        timestamp:
          NOW,
      });

    assert.equal(
      result.order.status,
      "FILLED",
    );

    assert.equal(
      result.position.quantity,
      10,
    );

    assert.ok(
      result.account.cash <
      90000,
    );
  },
);

test(
  "Executes sell and calculates realized pnl",
  () => {
    const engine =
      new PaperTradingEngineV3({
        initialCash:
          100000,

        commissionRate:
          0,

        slippageRate:
          0,

        maximumPositionPercent:
          100,
      });

    engine.updateMarketPrice({
      symbol:
        "TEST",

      price:
        100,

      timestamp:
        NOW,
    });

    const buy =
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

    engine.executeOrder({
      orderId:
        buy.id,

      timestamp:
        NOW,
    });

    engine.updateMarketPrice({
      symbol:
        "TEST",

      price:
        120,

      timestamp:
        NOW,
    });

    const sell =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "SELL",

        quantity:
          10,

        timestamp:
          NOW,
      });

    engine.executeOrder({
      orderId:
        sell.id,

      timestamp:
        NOW,
    });

    const position =
      engine.getPosition(
        "TEST",
      );

    assert.equal(
      position.quantity,
      0,
    );

    assert.equal(
      position.realizedPnl,
      200,
    );
  },
);

test(
  "Limit buy waits above limit price",
  () => {
    const engine =
      new PaperTradingEngineV3({
        maximumPositionPercent:
          100,
      });

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        type:
          "LIMIT",

        limitPrice:
          100,

        quantity:
          10,

        timestamp:
          NOW,
      });

    const result =
      engine.executeOrder({
        orderId:
          order.id,

        marketPrice:
          110,

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "OPEN",
    );
  },
);

test(
  "Limit buy fills at or below limit price",
  () => {
    const engine =
      new PaperTradingEngineV3({
        maximumPositionPercent:
          100,
      });

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        type:
          "LIMIT",

        limitPrice:
          100,

        quantity:
          10,

        timestamp:
          NOW,
      });

    const result =
      engine.executeOrder({
        orderId:
          order.id,

        marketPrice:
          99,

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
  "Supports partial fills",
  () => {
    const engine =
      new PaperTradingEngineV3({
        maximumPositionPercent:
          100,
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

    const first =
      engine.executeOrder({
        orderId:
          order.id,

        marketPrice:
          100,

        fillQuantity:
          4,

        timestamp:
          NOW,
      });

    assert.equal(
      first.order.status,
      "PARTIALLY_FILLED",
    );

    assert.equal(
      first.order.remainingQuantity,
      6,
    );

    const second =
      engine.executeOrder({
        orderId:
          order.id,

        marketPrice:
          100,

        timestamp:
          NOW,
      });

    assert.equal(
      second.order.status,
      "FILLED",
    );

    assert.equal(
      second.position.quantity,
      10,
    );
  },
);

test(
  "Rejects purchase with insufficient cash",
  () => {
    const engine =
      new PaperTradingEngineV3({
        initialCash:
          1000,

        maximumPositionPercent:
          100,
      });

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

    assert.throws(
      () =>
        engine.executeOrder({
          orderId:
            order.id,

          marketPrice:
            100,

          timestamp:
            NOW,
        }),

      /Insufficient paper cash/,
    );
  },
);

test(
  "Rejects oversize position",
  () => {
    const engine =
      new PaperTradingEngineV3({
        initialCash:
          100000,

        maximumPositionPercent:
          10,
      });

    const order =
      engine.submitOrder({
        symbol:
          "TEST",

        side:
          "BUY",

        quantity:
          200,

        timestamp:
          NOW,
      });

    assert.throws(
      () =>
        engine.executeOrder({
          orderId:
            order.id,

          marketPrice:
            100,

          timestamp:
            NOW,
        }),

      /Maximum position size exceeded/,
    );
  },
);

test(
  "Cancels open order",
  () => {
    const engine =
      new PaperTradingEngineV3();

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

    const cancelled =
      engine.cancelOrder({
        orderId:
          order.id,

        timestamp:
          NOW,
      });

    assert.equal(
      cancelled.status,
      "CANCELLED",
    );
  },
);

test(
  "Processes multiple open orders",
  () => {
    const engine =
      new PaperTradingEngineV3({
        maximumPositionPercent:
          100,
      });

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
        "BUY",

      quantity:
        20,

      timestamp:
        NOW,
    });

    const results =
      engine.processOpenOrders({
        prices: {
          AAA:
            100,

          BBB:
            50,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      results.length,
      2,
    );

    assert.equal(
      engine.getTrades().length,
      2,
    );
  },
);

test(
  "Returns account snapshot",
  () => {
    const engine =
      new PaperTradingEngineV3();

    const snapshot =
      engine.getAccountSnapshot();

    assert.equal(
      snapshot.initialCash,
      1000000,
    );

    assert.equal(
      snapshot.orders.length,
      0,
    );

    assert.equal(
      snapshot.positions.length,
      0,
    );
  },
);

test(
  "Validates timestamp",
  () => {
    const engine =
      new PaperTradingEngineV3();

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