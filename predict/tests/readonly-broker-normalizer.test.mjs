import test from "node:test";
import assert from "node:assert/strict";

import {
  normalizeReadonlyAccount,
  normalizeReadonlyBrokerSnapshot,
  normalizeReadonlyOrder,
  normalizeReadonlyPosition,
} from "../broker/readonly-broker-normalizer.js";

test(
  "口座データをArk共通形式へ変換",
  () => {
    const account =
      normalizeReadonlyAccount({
        accountNumber:
          "account-1",

        cashBalance:
          "500000",

        availableAmount:
          "450000",

        positionsValue:
          "300000",

        totalAssets:
          "800000",
      });

    assert.equal(
      account.accountId,
      "account-1",
    );

    assert.equal(
      account.cash,
      500_000,
    );

    assert.equal(
      account.buyingPower,
      450_000,
    );

    assert.equal(
      account.equity,
      800_000,
    );
  },
);

test(
  "保有株データを正規化",
  () => {
    const position =
      normalizeReadonlyPosition({
        securityCode:
          "7203.t",

        holdingQuantity:
          "100",

        costPrice:
          "2000",

        currentPrice:
          "2100",
      });

    assert.equal(
      position.symbol,
      "7203.T",
    );

    assert.equal(
      position.quantity,
      100,
    );

    assert.equal(
      position.marketValue,
      210_000,
    );

    assert.equal(
      position.unrealizedPnl,
      10_000,
    );
  },
);

test(
  "注文履歴を正規化",
  () => {
    const order =
      normalizeReadonlyOrder({
        id:
          "order-1",

        code:
          "6758.t",

        transactionType:
          "買",

        orderStatus:
          "partially_filled",

        orderQuantity:
          100,

        executedQuantity:
          40,
      });

    assert.equal(
      order.symbol,
      "6758.T",
    );

    assert.equal(
      order.side,
      "buy",
    );

    assert.equal(
      order.status,
      "partially-filled",
    );

    assert.equal(
      order.remainingQuantity,
      60,
    );
  },
);

test(
  "Snapshot集計を作成",
  () => {
    const snapshot =
      normalizeReadonlyBrokerSnapshot({
        provider:
          "test-broker",

        synchronizedAt:
          "2026-08-03T00:00:00.000Z",

        snapshot: {
          connection: {
            connected:
              true,

            authenticated:
              true,
          },

          account: {
            accountId:
              "account-1",

            cash:
              500_000,
          },

          positions: [
            {
              symbol:
                "7203.T",

              quantity:
                100,

              marketPrice:
                2_100,

              averagePrice:
                2_000,
            },
          ],

          orders: [
            {
              orderId:
                "order-1",

              symbol:
                "7203.T",

              side:
                "buy",

              status:
                "open",

              quantity:
                100,
            },
          ],
        },
      });

    assert.equal(
      snapshot.summary
        .positionCount,
      1,
    );

    assert.equal(
      snapshot.summary
        .openOrderCount,
      1,
    );

    assert.equal(
      snapshot.summary
        .totalMarketValue,
      210_000,
    );

    assert.equal(
      snapshot.summary
        .totalUnrealizedPnl,
      10_000,
    );
  },
);