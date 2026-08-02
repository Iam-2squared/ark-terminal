import test from "node:test";
import assert from "node:assert/strict";

import {
  createReadonlyBrokerAdapter,
} from "../broker/readonly-broker-adapter.js";

import {
  createReadonlyBrokerController,
} from "../broker/readonly-broker-controller.js";

test(
  "Controllerが接続状態を管理",
  async () => {
    const adapter =
      createReadonlyBrokerAdapter({
        connectionProvider:
          async () => ({
            connected:
              true,

            authenticated:
              true,

            provider:
              "test-broker",
          }),
      });

    const controller =
      createReadonlyBrokerController({
        adapter,
      });

    const state =
      await controller.connect();

    assert.equal(
      state.status,
      "connected",
    );

    assert.equal(
      state.connection.connected,
      true,
    );
  },
);

test(
  "Controller経由でBrokerデータを同期",
  async () => {
    const adapter =
      createReadonlyBrokerAdapter({
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
              "readonly-account",

            cash:
              1_000_000,
          }),

        positionsProvider:
          async () => [
            {
              symbol:
                "6758.T",

              quantity:
                100,
            },
          ],
      });

    const controller =
      createReadonlyBrokerController({
        adapter,
      });

    await controller.connect();

    const state =
      await controller.sync();

    assert.equal(
      state.status,
      "ready",
    );

    assert.equal(
      state.snapshot
        .account
        .accountId,
      "readonly-account",
    );

    assert.equal(
      state.snapshot
        .positions
        .length,
      1,
    );
  },
);

test(
  "切断すると状態を初期化",
  async () => {
    const adapter =
      createReadonlyBrokerAdapter({
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
      });

    await controller.connect();

    const state =
      controller.disconnect();

    assert.equal(
      state.status,
      "disconnected",
    );

    assert.equal(
      state.connection.connected,
      false,
    );
  },
);