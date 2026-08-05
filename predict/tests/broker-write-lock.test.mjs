import test from "node:test";
import assert from "node:assert/strict";

import {
  createExecutionBridge,
} from "../broker/execution-bridge.js";

function createProbeAdapter({
  mode = "live",
  liveTradingEnabled = true,
} = {}) {
  const calls = {
    submitOrder: 0,
    cancelOrder: 0,
  };

  return {
    calls,

    getInfo() {
      return {
        mode,
        liveTradingEnabled,
        provider: "test-probe",
      };
    },

    getAccount() {
      return {};
    },

    getPositions() {
      return [];
    },

    getOrders() {
      return [];
    },

    submitOrder() {
      calls.submitOrder += 1;
      return {
        transmitted: true,
      };
    },

    cancelOrder() {
      calls.cancelOrder += 1;
      return {
        cancelled: true,
        transmitted: true,
      };
    },
  };
}

test(
  "Live注文は明示許可と承認があっても送信しない",
  () => {
    const adapter =
      createProbeAdapter();

    const bridge =
      createExecutionBridge({
        adapter,
        allowLiveTrading: true,
        requireHumanApproval: true,
        approvalProvider: () => true,
      });

    const result =
      bridge.submitOrder({
        order: {
          symbol: "7203.T",
          side: "buy",
          quantity: 100,
        },
        approvalToken: "approved-for-test",
      });

    assert.equal(result.submitted, false);
    assert.equal(result.transmitted, false);
    assert.equal(
      result.reason,
      "live_broker_execution_locked",
    );
    assert.equal(adapter.calls.submitOrder, 0);

    const info = bridge.getInfo();
    assert.equal(info.policy.allowLiveTrading, false);
    assert.equal(
      info.policy.requestedAllowLiveTrading,
      true,
    );
    assert.equal(
      info.policy.brokerWriteLock.status,
      "LOCKED",
    );
  },
);

test(
  "Live注文の取消もBroker Adapterへ渡さない",
  () => {
    const adapter =
      createProbeAdapter();

    const bridge =
      createExecutionBridge({
        adapter,
        allowLiveTrading: true,
        approvalProvider: () => true,
      });

    const result =
      bridge.cancelOrder({
        adapterOrderId: "LIVE-ORDER-1",
      });

    assert.equal(result.cancelled, false);
    assert.equal(result.transmitted, false);
    assert.equal(
      result.reason,
      "live_broker_execution_locked",
    );
    assert.equal(adapter.calls.cancelOrder, 0);
  },
);

test(
  "不明なBroker modeはフェイルクローズで拒否する",
  () => {
    const adapter =
      createProbeAdapter({
        mode: "unknown",
        liveTradingEnabled: false,
      });

    const bridge =
      createExecutionBridge({
        adapter,
      });

    const result =
      bridge.submitOrder({
        order: {
          symbol: "9984.T",
          side: "sell",
          quantity: 100,
        },
      });

    assert.equal(result.submitted, false);
    assert.equal(
      result.reason,
      "broker_write_mode_not_allowed",
    );
    assert.equal(adapter.calls.submitOrder, 0);
  },
);

test(
  "Paperを名乗ってもLive有効報告があれば拒否する",
  () => {
    const adapter =
      createProbeAdapter({
        mode: "paper",
        liveTradingEnabled: true,
      });

    const bridge =
      createExecutionBridge({
        adapter,
      });

    const result =
      bridge.submitOrder({
        order: {
          symbol: "6758.T",
          side: "buy",
          quantity: 100,
        },
      });

    assert.equal(result.submitted, false);
    assert.equal(
      result.reason,
      "live_broker_execution_locked",
    );
    assert.equal(adapter.calls.submitOrder, 0);
  },
);
