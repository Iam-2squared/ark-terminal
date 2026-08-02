import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperAccount,
} from "../paper/paper-account.js";

import {
  executePaperOrder,
  markPaperAccount,
  submitPaperOrder,
} from "../paper/paper-engine.js";

test(
  "買い注文を受付して約定",
  () => {
    const account =
      createPaperAccount({
        initialCash:
          1_000_000,
      });

    const submitted =
      submitPaperOrder({
        account,

        orderInput: {
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
          2_500,
      });

    assert.equal(
      submitted.order.status,
      "accepted",
    );

    assert.equal(
      submitted.account
        .openOrders.length,
      1,
    );

    const executed =
      executePaperOrder({
        account:
          submitted.account,

        orderId:
          submitted.order.orderId,

        fillPrice:
          2_500,
      });

    assert.equal(
      executed.order.status,
      "filled",
    );

    assert.equal(
      executed.account.cash,
      750_000,
    );

    assert.equal(
      executed.account
        .positions["7203.T"]
        .quantity,
      100,
    );

    assert.equal(
      executed.account
        .openOrders.length,
      0,
    );
  },
);

test(
  "保有株を評価替え",
  () => {
    const account =
      createPaperAccount({
        initialCash:
          1_000_000,
      });

    const submitted =
      submitPaperOrder({
        account,

        orderInput: {
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

    const executed =
      executePaperOrder({
        account:
          submitted.account,

        orderId:
          submitted.order.orderId,

        fillPrice:
          2_000,
      });

    const marked =
      markPaperAccount({
        account:
          executed.account,

        prices: {
          "7203.T":
            2_100,
        },
      });

    assert.equal(
      marked.marketValue,
      210_000,
    );

    assert.equal(
      marked.unrealizedPnl,
      10_000,
    );

    assert.equal(
      marked.equity,
      1_010_000,
    );
  },
);

test(
  "売却で実現損益を計上",
  () => {
    let account =
      createPaperAccount({
        initialCash:
          1_000_000,
      });

    const buy =
      submitPaperOrder({
        account,

        orderInput: {
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

    account =
      executePaperOrder({
        account:
          buy.account,

        orderId:
          buy.order.orderId,

        fillPrice:
          2_000,
      }).account;

    const sell =
      submitPaperOrder({
        account,

        orderInput: {
          symbol:
            "7203.T",
          side:
            "sell",
          quantity:
            100,
        },

        estimatedPrice:
          2_200,
      });

    const closed =
      executePaperOrder({
        account:
          sell.account,

        orderId:
          sell.order.orderId,

        fillPrice:
          2_200,
      });

    assert.equal(
      closed.account.cash,
      1_020_000,
    );

    assert.equal(
      closed.account
        .realizedPnl,
      20_000,
    );

    assert.equal(
      closed.account
        .tradeHistory.length,
      1,
    );

    assert.equal(
      closed.account
        .positions["7203.T"],
      undefined,
    );
  },
);

test(
  "100株未満の注文を拒否",
  () => {
    const account =
      createPaperAccount({
        initialCash:
          1_000_000,
      });

    const result =
      submitPaperOrder({
        account,

        orderInput: {
          symbol:
            "7203.T",
          side:
            "buy",
          quantity:
            50,
        },

        estimatedPrice:
          2_000,
      });

    assert.equal(
      result.order.status,
      "rejected",
    );

    assert.ok(
      result.risk.reasons
        .includes(
          "invalid_lot_size",
        ),
    );
  },
);

test(
  "最大注文金額超過を拒否",
  () => {
    const account =
      createPaperAccount({
        initialCash:
          1_000_000,
      });

    const result =
      submitPaperOrder({
        account,

        orderInput: {
          symbol:
            "7203.T",
          side:
            "buy",
          quantity:
            200,
        },

        estimatedPrice:
          2_000,
      });

    assert.equal(
      result.order.status,
      "rejected",
    );

    assert.ok(
      result.risk.reasons
        .includes(
          "maximum_order_value_exceeded",
        ),
    );
  },
);