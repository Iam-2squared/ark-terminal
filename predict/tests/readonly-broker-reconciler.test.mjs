import test from "node:test";
import assert from "node:assert/strict";

import {
  reconcileReadonlyAccount,
  reconcileReadonlyBrokerSnapshot,
  reconcileReadonlyOrders,
  reconcileReadonlyPositions,
} from "../broker/readonly-broker-reconciler.js";

test(
  "一致する口座情報は差分なし",
  () => {
    const result =
      reconcileReadonlyAccount({
        brokerAccount: {
          cash:
            500_000,

          buyingPower:
            450_000,

          equity:
            800_000,
        },

        localAccount: {
          cash:
            500_000,

          buyingPower:
            450_000,

          equity:
            800_000,
        },
      });

    assert.equal(
      result.length,
      0,
    );
  },
);

test(
  "現金残高の差を検出",
  () => {
    const result =
      reconcileReadonlyAccount({
        brokerAccount: {
          cash:
            500_000,
        },

        localAccount: {
          cash:
            490_000,
        },
      });

    assert.equal(
      result.length,
      1,
    );

    assert.equal(
      result[0].field,
      "cash",
    );

    assert.equal(
      result[0].difference,
      10_000,
    );
  },
);

test(
  "保有数量の差を重大エラーとして検出",
  () => {
    const result =
      reconcileReadonlyPositions({
        brokerPositions: [
          {
            symbol:
              "7203.T",

            quantity:
              100,

            averagePrice:
              2_000,

            marketValue:
              210_000,
          },
        ],

        localPositions: [
          {
            symbol:
              "7203.T",

            quantity:
              200,

            averagePrice:
              2_000,

            marketValue:
              420_000,
          },
        ],
      });

    const quantity =
      result.find(
        (row) =>
          row.field ===
          "quantity",
      );

    assert.equal(
      quantity.severity,
      "error",
    );

    assert.equal(
      quantity.difference,
      -100,
    );
  },
);

test(
  "Brokerだけにある保有株を検出",
  () => {
    const result =
      reconcileReadonlyPositions({
        brokerPositions: [
          {
            symbol:
              "6758.T",

            quantity:
              100,
          },
        ],

        localPositions: [],
      });

    assert.equal(
      result[0].type,
      "position_missing_locally",
    );
  },
);

test(
  "注文状態の差を検出",
  () => {
    const result =
      reconcileReadonlyOrders({
        brokerOrders: [
          {
            orderId:
              "order-1",

            status:
              "filled",

            filledQuantity:
              100,
          },
        ],

        localOrders: [
          {
            orderId:
              "order-1",

            status:
              "open",

            filledQuantity:
              0,
          },
        ],
      });

    assert.equal(
      result.length,
      2,
    );

    assert.ok(
      result.some(
        (row) =>
          row.type ===
          "order_status_mismatch",
      ),
    );

    assert.ok(
      result.some(
        (row) =>
          row.type ===
          "order_fill_mismatch",
      ),
    );
  },
);

test(
  "完全一致Snapshotをmatched判定",
  () => {
    const snapshot = {
      account: {
        cash:
          500_000,

        buyingPower:
          450_000,

        equity:
          800_000,
      },

      positions: [
        {
          symbol:
            "7203.T",

          quantity:
            100,

          averagePrice:
            2_000,

          marketValue:
            210_000,
        },
      ],

      orders: [],
    };

    const result =
      reconcileReadonlyBrokerSnapshot({
        brokerSnapshot:
          snapshot,

        localSnapshot:
          structuredClone(
            snapshot,
          ),
      });

    assert.equal(
      result.matched,
      true,
    );

    assert.equal(
      result.safe,
      true,
    );

    assert.equal(
      result.summary
        .totalDifferences,
      0,
    );
  },
);