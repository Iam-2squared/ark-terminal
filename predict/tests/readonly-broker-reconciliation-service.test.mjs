import test from "node:test";
import assert from "node:assert/strict";

import {
  createReadonlyBrokerReconciliationService,
} from "../broker/readonly-broker-reconciliation-service.js";

function createSnapshot({
  quantity = 100,
} = {}) {
  return {
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

        quantity,

        averagePrice:
          2_000,

        marketValue:
          210_000,
      },
    ],

    orders: [],
  };
}

test(
  "一致データをmatched状態へ変更",
  async () => {
    const service =
      createReadonlyBrokerReconciliationService({
        brokerSnapshotProvider:
          async () =>
            createSnapshot(),

        localSnapshotProvider:
          async () =>
            createSnapshot(),
      });

    const state =
      await service.reconcile();

    assert.equal(
      state.status,
      "matched",
    );

    assert.equal(
      state.result.matched,
      true,
    );

    assert.equal(
      service.isSafe(),
      true,
    );
  },
);

test(
  "警告差分を保持",
  async () => {
    const service =
      createReadonlyBrokerReconciliationService({
        brokerSnapshotProvider:
          async () => ({
            ...createSnapshot(),

            account: {
              cash:
                500_000,

              buyingPower:
                450_000,

              equity:
                800_000,
            },
          }),

        localSnapshotProvider:
          async () => ({
            ...createSnapshot(),

            account: {
              cash:
                490_000,

              buyingPower:
                450_000,

              equity:
                800_000,
            },
          }),
      });

    const state =
      await service.reconcile();

    assert.equal(
      state.status,
      "warning",
    );

    assert.equal(
      state.result.safe,
      true,
    );

    assert.equal(
      service
        .getDifferences()
        .length,
      1,
    );
  },
);

test(
  "保有数量差をerror状態へ変更",
  async () => {
    const service =
      createReadonlyBrokerReconciliationService({
        brokerSnapshotProvider:
          async () =>
            createSnapshot({
              quantity:
                100,
            }),

        localSnapshotProvider:
          async () =>
            createSnapshot({
              quantity:
                200,
            }),
      });

    const state =
      await service.reconcile();

    assert.equal(
      state.status,
      "error",
    );

    assert.equal(
      state.result.safe,
      false,
    );

    assert.equal(
      service.isSafe(),
      false,
    );
  },
);

test(
  "Provider失敗を状態へ記録",
  async () => {
    const service =
      createReadonlyBrokerReconciliationService({
        brokerSnapshotProvider:
          async () => {
            throw new Error(
              "Broker unavailable.",
            );
          },

        localSnapshotProvider:
          async () =>
            createSnapshot(),
      });

    await assert.rejects(
      () =>
        service.reconcile(),
      /Broker unavailable/,
    );

    const state =
      service.getState();

    assert.equal(
      state.status,
      "error",
    );

    assert.equal(
      state.lastError.action,
      "reconcile",
    );
  },
);