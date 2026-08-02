import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperOrder,
  acceptPaperOrder,
  fillPaperOrder,
} from "../paper/paper-orders.js";

import {
  addOrderToBook,
  createPaperOrderBook,
  expireOrders,
  findOrderById,
  listOpenOrders,
  summarizeOrderBook,
  updateOrderInBook,
} from "../paper/paper-order-book.js";

test(
  "注文を追加して検索",
  () => {
    const order =
      acceptPaperOrder({
        order:
          createPaperOrder({
            orderId:
              "order-1",
            symbol:
              "7203.T",
            side:
              "buy",
            quantity:
              100,
          }),
      });

    const book =
      addOrderToBook({
        book:
          createPaperOrderBook(),
        order,
      });

    assert.equal(
      book.orders.length,
      1,
    );

    assert.equal(
      findOrderById({
        book,
        orderId:
          "order-1",
      }).symbol,
      "7203.T",
    );

    assert.equal(
      listOpenOrders({
        book,
      }).length,
      1,
    );
  },
);

test(
  "注文を更新",
  () => {
    const order =
      acceptPaperOrder({
        order:
          createPaperOrder({
            orderId:
              "order-2",
            symbol:
              "6758.T",
            side:
              "buy",
            quantity:
              100,
          }),
      });

    let book =
      addOrderToBook({
        book:
          createPaperOrderBook(),
        order,
      });

    const filled =
      fillPaperOrder({
        order,
        fillPrice:
          3_000,
        fillQuantity:
          100,
      });

    book =
      updateOrderInBook({
        book,
        order:
          filled,
      });

    assert.equal(
      findOrderById({
        book,
        orderId:
          "order-2",
      }).status,
      "filled",
    );
  },
);

test(
  "期限切れ注文を失効",
  () => {
    const order =
      acceptPaperOrder({
        order: {
          ...createPaperOrder({
            orderId:
              "order-3",
            symbol:
              "9984.T",
            side:
              "buy",
            quantity:
              100,
          }),

          expiresAt:
            "2026-08-01T00:00:00.000Z",
        },
      });

    const book =
      expireOrders({
        book:
          addOrderToBook({
            book:
              createPaperOrderBook(),
            order,
          }),

        now:
          "2026-08-02T00:00:00.000Z",
      });

    assert.equal(
      book.orders[0].status,
      "expired",
    );

    assert.equal(
      summarizeOrderBook(
        book,
      ).expired,
      1,
    );
  },
);