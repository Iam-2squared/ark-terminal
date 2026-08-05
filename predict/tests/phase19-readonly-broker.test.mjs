import test from "node:test";
import assert from "node:assert/strict";

import {
  createReadonlyBrokerAdapter,
} from "../broker/readonly-broker-adapter.js";
import {
  assertPhase19ReadonlyOperation,
  PHASE19_READONLY_POLICY,
} from "../broker/phase19-readonly-policy.js";
import {
  createPhase19ReadonlyBrokerRuntime,
} from "../broker/phase19-readonly-runtime.js";

test("Phase19 policy permanently blocks write operations", () => {
  assert.equal(PHASE19_READONLY_POLICY.allowLiveTrading, false);
  assert.equal(PHASE19_READONLY_POLICY.allowOrderTransmission, false);

  assert.throws(
    () => assertPhase19ReadonlyOperation("SUBMIT_ORDER"),
    (error) => {
      assert.equal(error.code, "PHASE19_READONLY_OPERATION_BLOCKED");
      assert.equal(error.transmitted, false);
      return true;
    },
  );
});

test("Phase19 runtime connects and syncs read-only broker data", async () => {
  const now = "2026-08-05T07:00:00.000Z";
  const account = {
    accountId: "masked-account",
    currency: "JPY",
    cash: 1000000,
    buyingPower: 1000000,
  };
  const positions = [];
  const orders = [];

  const adapter = createReadonlyBrokerAdapter({
    provider: "provider-pending-verification",
    nowProvider: () => now,
    connectionProvider: async () => ({
      connected: true,
      authenticated: true,
      provider: "provider-pending-verification",
      accountId: "masked-account",
    }),
    accountProvider: async () => account,
    positionsProvider: async () => positions,
    ordersProvider: async () => orders,
  });

  const runtime = createPhase19ReadonlyBrokerRuntime({
    adapter,
    nowProvider: () => now,
    localSnapshotProvider: async () => ({
      account,
      positions,
      orders,
    }),
  });

  const connected = await runtime.connect();
  assert.equal(connected.safety.connected, true);
  assert.equal(connected.safety.authenticated, true);
  assert.equal(connected.safety.brokerExecutionAllowed, false);
  assert.equal(connected.safety.orderTransmissionAllowed, false);
  assert.equal(connected.safety.transmitted, false);

  const synced = await runtime.sync();
  assert.equal(synced.brokerSnapshot.readOnly, true);
  assert.equal(synced.brokerSnapshot.account.cash, 1000000);
  assert.equal(synced.safety.transmitted, false);

  assert.throws(
    () => runtime.rejectWrite("ORDER_CREATE"),
    /blocked operation/i,
  );
});

test("underlying read-only adapter rejects submit and cancel", () => {
  const adapter = createReadonlyBrokerAdapter();
  const submit = adapter.submitOrder({ clientOrderId: "x" });
  const cancel = adapter.cancelOrder({ adapterOrderId: "y" });

  assert.equal(submit.transmitted, false);
  assert.equal(submit.status, "rejected");
  assert.equal(cancel.transmitted, false);
  assert.equal(cancel.cancelled, false);
});
