import test from "node:test";
import assert from "node:assert/strict";

import {
  createReadonlyBrokerAdapter,
} from "../broker/readonly-broker-adapter.js";

import {
  createReadonlyBrokerController,
} from "../broker/readonly-broker-controller.js";

import {
  createReadonlyBrokerSyncService,
} from "../broker/readonly-broker-sync-service.js";

function createClock() {
  let current =
    Date.parse(
      "2026-08-03T00:00:00.000Z",
    );

  return {
    now() {
      return new Date(
        current,
      ).toISOString();
    },

    advance(ms) {
      current += ms;
    },
  };
}

test(
  "接続と同期を一括実行",
  async () => {
    const clock =
      createClock();

    const adapter =
      createReadonlyBrokerAdapter({
        provider:
          "test-broker",

        nowProvider:
          clock.now,

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

              marketPrice:
                2_100,
            },
          ],

        ordersProvider:
          async () => [],
      });

    const controller =
      createReadonlyBrokerController({
        adapter,

        nowProvider:
          clock.now,
      });

    const service =
      createReadonlyBrokerSyncService({
        controller,

        nowProvider:
          clock.now,
      });

    const state =
      await service
        .connectAndSynchronize();

    assert.equal(
      state.status,
      "ready",
    );

    assert.equal(
      state.health.connected,
      true,
    );

    assert.equal(
      state.health.fresh,
      true,
    );

    assert.equal(
      state.normalizedSnapshot
        .account
        .accountId,
      "account-1",
    );
  },
);

test(
  "古い同期データをstale判定",
  async () => {
    const clock =
      createClock();

    const adapter =
      createReadonlyBrokerAdapter({
        nowProvider:
          clock.now,

        connectionProvider:
          async () => ({
            connected:
              true,

            authenticated:
              true,
          }),
      });

    const controller =
      createReadonlyBrokerController({
        adapter,

        nowProvider:
          clock.now,
      });

    const service =
      createReadonlyBrokerSyncService({
        controller,

        maximumAgeMs:
          60_000,

        nowProvider:
          clock.now,
      });

    await service
      .connectAndSynchronize();

    clock.advance(
      120_000,
    );

    const state =
      service.refreshHealth();

    assert.equal(
      state.health.fresh,
      false,
    );

    assert.equal(
      state.health.stale,
      true,
    );

    assert.equal(
      state.health.ageMs,
      120_000,
    );
  },
);

test(
  "未接続同期エラーを保持",
  async () => {
    const adapter =
      createReadonlyBrokerAdapter();

    const controller =
      createReadonlyBrokerController({
        adapter,
      });

    const service =
      createReadonlyBrokerSyncService({
        controller,
      });

    await assert.rejects(
      () =>
        service.synchronize(),
      /not connected and authenticated/,
    );

    const state =
      service.getState();

    assert.equal(
      state.status,
      "error",
    );

    assert.equal(
      state.lastError.action,
      "synchronize",
    );
  },
);