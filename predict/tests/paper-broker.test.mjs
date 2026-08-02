import test from "node:test";
import assert from "node:assert/strict";

import {
  cancelBrokerOrder,
  createPaperBroker,
  createPaperBrokerSnapshot,
  fillBrokerOrder,
  markPaperBroker,
  submitBrokerOrder,
} from "../paper/paper-broker.js";

test(
  "Paper Brokerを作成",
  () => {
    const broker =
      createPaperBroker({
        initialCash:
          1_000_000,
      });

    assert.equal(
      broker.mode,
      "paper",
    );

    assert.equal(
      broker.account.cash,
      1_000_000,
    );

    assert.equal(
      broker.orderBook
        .orders.length,
      0,
    );
  },
);

test(
  "注文受付時に口座と注文簿を同期",
  () => {
    const broker =
      createPaperBroker();

    const result =
      submitBrokerOrder({
        broker,

        orderInput: {
          orderId:
            "broker-buy-1",

          symbol:
            "7203.T",

          side:
            "buy",

          quantity:
            100,

          type:
            "market",
        },

        estimatedPrice:
          2_000,
      });

    assert.equal(
      result.order.status,
      "accepted",
    );

    assert.equal(
      result.broker.account
        .openOrders.length,
      1,
    );

    assert.equal(
      result.broker.orderBook
        .orders.length,
      1,
    );

    assert.equal(
      result.broker.account
        .reservedCash,
      200_000,
    );

    assert.equal(
      result.order.metadata
        .reservedValue,
      200_000,
    );
  },
);

test(
  "買い注文を約定して保有株へ反映",
  () => {
    let broker =
      createPaperBroker();

    const submitted =
      submitBrokerOrder({
        broker,

        orderInput: {
          orderId:
            "broker-buy-2",

          symbol:
            "7203.T",

          side:
            "buy",

          quantity:
            100,
        },

        estimatedPrice:
          2_000,
      });

    broker =
      submitted.broker;

    const filled =
      fillBrokerOrder({
        broker,

        orderId:
          "broker-buy-2",

        fillPrice:
          2_000,
      });

    assert.equal(
      filled.order.status,
      "filled",
    );

    assert.equal(
      filled.broker.account.cash,
      800_000,
    );

    assert.equal(
      filled.broker.account
        .positions["7203.T"]
        .quantity,
      100,
    );

    assert.equal(
      filled.broker.orderBook
        .orders[0].status,
      "filled",
    );
  },
);

test(
  "未約定注文を取消して予約資金を解放",
  () => {
    let broker =
      createPaperBroker();

    broker =
      submitBrokerOrder({
        broker,

        orderInput: {
          orderId:
            "broker-cancel-1",

          symbol:
            "6758.T",

          side:
            "buy",

          quantity:
            100,
        },

        estimatedPrice:
          2_500,
      }).broker;

    assert.equal(
      broker.account
        .reservedCash,
      250_000,
    );

    const cancelled =
      cancelBrokerOrder({
        broker,

        orderId:
          "broker-cancel-1",
      });

    assert.equal(
      cancelled.order.status,
      "cancelled",
    );

    assert.equal(
      cancelled.broker.account
        .reservedCash,
      0,
    );

    assert.equal(
      cancelled.broker.account
        .openOrders.length,
      0,
    );

    assert.equal(
      cancelled.broker.orderBook
        .orders[0].status,
      "cancelled",
    );
  },
);

test(
  "保有株を時価評価",
  () => {
    let broker =
      createPaperBroker();

    broker =
      submitBrokerOrder({
        broker,

        orderInput: {
          orderId:
            "broker-mark-1",

          symbol:
            "7203.T",

          side:
            "buy",

          quantity:
            100,
        },

        estimatedPrice:
          2_000,
      }).broker;

    broker =
      fillBrokerOrder({
        broker,

        orderId:
          "broker-mark-1",

        fillPrice:
          2_000,
      }).broker;

    broker =
      markPaperBroker({
        broker,

        prices: {
          "7203.T":
            2_100,
        },
      });

    assert.equal(
      broker.account
        .unrealizedPnl,
      10_000,
    );

    assert.equal(
      broker.account.equity,
      1_010_000,
    );
  },
);

test(
  "Brokerスナップショットを生成",
  () => {
    const broker =
      createPaperBroker({
        initialCash:
          500_000,
      });

    const snapshot =
      createPaperBrokerSnapshot(
        broker,
      );

    assert.equal(
      snapshot.cash,
      500_000,
    );

    assert.equal(
      snapshot.positionCount,
      0,
    );

    assert.equal(
      snapshot.orderSummary.total,
      0,
    );
  },
);