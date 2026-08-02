import test from "node:test";
import assert from "node:assert/strict";

import {
  createDisabledLiveBrokerAdapter,
} from "../broker/disabled-live-broker-adapter.js";

test(
  "未設定Live Adapterは接続無効",
  () => {
    const adapter =
      createDisabledLiveBrokerAdapter();

    const info =
      adapter.getInfo();

    assert.equal(
      info.mode,
      "live",
    );

    assert.equal(
      info.connected,
      false,
    );

    assert.equal(
      info.authenticated,
      false,
    );

    assert.equal(
      info.liveTradingEnabled,
      false,
    );
  },
);

test(
  "未設定Live Adapterは注文を送信しない",
  () => {
    const adapter =
      createDisabledLiveBrokerAdapter();

    const order =
      adapter.submitOrder({
        symbol:
          "7203.T",

        side:
          "buy",

        quantity:
          100,
      });

    assert.equal(
      order.status,
      "rejected",
    );

    assert.equal(
      order.transmitted,
      false,
    );

    assert.equal(
      order.reason,
      "live_adapter_not_configured",
    );
  },
);

test(
  "未設定Live Adapterは取消も送信しない",
  () => {
    const adapter =
      createDisabledLiveBrokerAdapter();

    const result =
      adapter.cancelOrder({
        adapterOrderId:
          "live-order-1",
      });

    assert.equal(
      result.cancelled,
      false,
    );

    assert.equal(
      result.transmitted,
      false,
    );
  },
);