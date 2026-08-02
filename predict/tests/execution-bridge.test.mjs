import test from "node:test";
import assert from "node:assert/strict";

import {
  createDryRunBrokerAdapter,
} from "../broker/dry-run-broker-adapter.js";

import {
  createExecutionBridge,
} from "../broker/execution-bridge.js";

test(
  "Dry Run注文をBridge経由で処理",
  () => {
    const bridge =
      createExecutionBridge({
        adapter:
          createDryRunBrokerAdapter(),
      });

    const result =
      bridge.submitOrder({
        order: {
          symbol:
            "7203.T",

          side:
            "buy",

          quantity:
            100,
        },
      });

    assert.equal(
      result.submitted,
      true,
    );

    assert.equal(
      result.brokerOrder
        .transmitted,
      false,
    );

    assert.equal(
      result.brokerOrder
        .status,
      "simulated",
    );
  },
);

test(
  "不正注文はAdapterへ渡さない",
  () => {
    const adapter =
      createDryRunBrokerAdapter();

    const bridge =
      createExecutionBridge({
        adapter,
      });

    const result =
      bridge.submitOrder({
        order: {
          symbol:
            "7203.T",

          side:
            "buy",

          quantity:
            0,
        },
      });

    assert.equal(
      result.submitted,
      false,
    );

    assert.equal(
      result.reason,
      "validation_failed",
    );

    assert.equal(
      adapter
        .getOrders()
        .length,
      0,
    );
  },
);

test(
  "Bridgeから口座情報を取得",
  () => {
    const bridge =
      createExecutionBridge({
        adapter:
          createDryRunBrokerAdapter({
            initialCash:
              500_000,
          }),
      });

    assert.equal(
      bridge
        .getAccount()
        .cash,
      500_000,
    );
  },
);