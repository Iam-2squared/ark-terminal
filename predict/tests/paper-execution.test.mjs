import test from "node:test";
import assert from "node:assert/strict";

import {
  acceptPaperOrder,
  createPaperOrder,
} from "../paper/paper-orders.js";

import {
  cancelOpenOrder,
  executeAvailableOrders,
  executeOrderFill,
  shouldExecuteOrder,
} from "../paper/paper-execution.js";

test(
  "成行注文を約定",
  () => {
    const order =
      acceptPaperOrder({
        order:
          createPaperOrder({
            orderId:
              "market-1",
            symbol:
              "7203.T",
            side:
              "buy",
            quantity:
              100,
          }),
      });

    const result =
      executeOrderFill({
        order,
        marketPrice:
          2_500,
      });

    assert.equal(
      result.executed,
      true,
    );

    assert.equal(
      result.order.status,
      "filled",
    );

    assert.equal(
      result.fill.notional,
      250_000,
    );
  },
);

test(
  "部分約定を処理",
  () => {
    const order =
      acceptPaperOrder({
        order:
          createPaperOrder({
            orderId:
              "partial-1",
            symbol:
              "7203.T",
            side:
              "buy",
            quantity:
              200,
          }),
      });

    const result =
      executeOrderFill({
        order,
        marketPrice:
          2_000,
        fillQuantity:
          100,
      });

    assert.equal(
      result.order.status,
      "partially_filled",
    );

    assert.equal(
      result.order.filledQuantity,
      100,
    );

    assert.equal(
      result.order.remainingQuantity,
      100,
    );
  },
);

test(
  "指値買いの約定条件",
  () => {
    const order =
      acceptPaperOrder({
        order:
          createPaperOrder({
            symbol:
              "7203.T",
            side:
              "buy",
            quantity:
              100,
            type:
              "limit",
            limitPrice:
              2_000,
          }),
      });

    assert.equal(
      shouldExecuteOrder({
        order,
        marketPrice:
          1_980,
      }),
      true,
    );

    assert.equal(
      shouldExecuteOrder({
        order,
        marketPrice:
          2_100,
      }),
      false,
    );
  },
);

test(
  "注文をキャンセル",
  () => {
    const order =
      acceptPaperOrder({
        order:
          createPaperOrder({
            symbol:
              "6758.T",
            side:
              "buy",
            quantity:
              100,
          }),
      });

    const cancelled =
      cancelOpenOrder({
        order,
      });

    assert.equal(
      cancelled.status,
      "cancelled",
    );
  },
);

test(
  "複数注文を一括約定",
  () => {
    const orders = [
      acceptPaperOrder({
        order:
          createPaperOrder({
            orderId:
              "bulk-1",
            symbol:
              "7203.T",
            side:
              "buy",
            quantity:
              100,
          }),
      }),

      acceptPaperOrder({
        order:
          createPaperOrder({
            orderId:
              "bulk-2",
            symbol:
              "6758.T",
            side:
              "buy",
            quantity:
              100,
          }),
      }),
    ];

    const result =
      executeAvailableOrders({
        orders,
        prices: {
          "7203.T":
            2_000,
          "6758.T":
            3_000,
        },
      });

    assert.equal(
      result.executions.length,
      2,
    );

    assert.equal(
      result.orders[0].status,
      "filled",
    );

    assert.equal(
      result.orders[1].status,
      "filled",
    );
  },
);