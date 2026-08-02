import test from "node:test";
import assert from "node:assert/strict";

import {
  createReadonlyBrokerAdapter,
} from "../broker/readonly-broker-adapter.js";

test(
  "Read-only Adapterは発注機能を無効化",
  () => {
    const adapter =
      createReadonlyBrokerAdapter();

    const info =
      adapter.getInfo();

    assert.equal(
      info.readOnly,
      true,
    );

    assert.equal(
      info.liveTradingEnabled,
      false,
    );

    assert.equal(
      info.capabilities.includes(
        "order-create",
      ),
      false,
    );
  },
);

test(
  "接続後に口座・保有株・注文履歴を同期",
  async () => {
    const adapter =
      createReadonlyBrokerAdapter({
        provider:
          "test-broker",

        connectionProvider:
          async () => ({
            connected:
              true,

            authenticated:
              true,

            provider:
              "test-broker",
          }),

        accountProvider:
          async () => ({
            accountId:
              "account-1",

            cash:
              500_000,

            equity:
              800_000,
          }),

        positionsProvider:
          async () => [
            {
              symbol:
                "7203.T",

              quantity:
                100,
            },
          ],

        ordersProvider:
          async () => [
            {
              orderId:
                "order-1",

              status:
                "filled",
            },
          ],
      });

    const connection =
      await adapter.connect();

    assert.equal(
      connection.connected,
      true,
    );

    assert.equal(
      connection.authenticated,
      true,
    );

    const snapshot =
      await adapter.sync();

    assert.equal(
      snapshot.account.accountId,
      "account-1",
    );

    assert.equal(
      snapshot.positions.length,
      1,
    );

    assert.equal(
      snapshot.orders.length,
      1,
    );

    assert.equal(
      snapshot.synchronized,
      true,
    );
  },
);

test(
  "未接続状態では同期を拒否",
  async () => {
    const adapter =
      createReadonlyBrokerAdapter();

    await assert.rejects(
      () =>
        adapter.sync(),
      /not connected and authenticated/,
    );
  },
);

test(
  "注文送信を必ず拒否",
  () => {
    const adapter =
      createReadonlyBrokerAdapter();

    const result =
      adapter.submitOrder({
        clientOrderId:
          "readonly-order-1",

        symbol:
          "7203.T",

        side:
          "buy",

        quantity:
          100,
      });

    assert.equal(
      result.status,
      "rejected",
    );

    assert.equal(
      result.transmitted,
      false,
    );

    assert.equal(
      result.reason,
      "readonly_adapter",
    );
  },
);