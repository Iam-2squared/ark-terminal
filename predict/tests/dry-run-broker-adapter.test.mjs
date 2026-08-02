import test from "node:test";
import assert from "node:assert/strict";

import {
  createDryRunBrokerAdapter,
} from "../broker/dry-run-broker-adapter.js";

test(
  "Dry Runは実送信を無効化",
  () => {
    const adapter =
      createDryRunBrokerAdapter();

    const info =
      adapter.getInfo();

    assert.equal(
      info.mode,
      "dry-run",
    );

    assert.equal(
      info.liveTradingEnabled,
      false,
    );
  },
);

test(
  "注文をシミュレーション",
  () => {
    const adapter =
      createDryRunBrokerAdapter();

    const order =
      adapter.submitOrder({
        clientOrderId:
          "dry-1",

        symbol:
          "7203.T",

        side:
          "buy",

        quantity:
          100,

        type:
          "market",
      });

    assert.equal(
      order.status,
      "simulated",
    );

    assert.equal(
      order.simulated,
      true,
    );

    assert.equal(
      order.transmitted,
      false,
    );

    assert.equal(
      adapter
        .getOrders()
        .length,
      1,
    );
  },
);

test(
  "Dry Run注文を取消",
  () => {
    const adapter =
      createDryRunBrokerAdapter();

    const order =
      adapter.submitOrder({
        symbol:
          "6758.T",

        side:
          "buy",

        quantity:
          100,
      });

    const cancelled =
      adapter.cancelOrder({
        adapterOrderId:
          order.adapterOrderId,
      });

    assert.equal(
      cancelled.status,
      "cancelled",
    );

    assert.equal(
      cancelled.transmitted,
      false,
    );
  },
);