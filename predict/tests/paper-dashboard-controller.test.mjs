import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperDashboardController,
} from "../paper/paper-dashboard-controller.js";

import {
  createMemoryStorage,
} from "../paper/paper-storage.js";

function createRoot() {
  return {
    innerHTML: "",
    dataset: {},
  };
}

function createClock() {
  let counter = 0;

  return () => {
    counter += 1;

    return (
      "2026-08-02T" +
      String(counter)
        .padStart(2, "0") +
      ":00:00.000Z"
    );
  };
}

test(
  "Controllerを作成してDashboardを描画",
  () => {
    const root =
      createRoot();

    const controller =
      createPaperDashboardController({
        root,

        storage:
          createMemoryStorage(),

        nowProvider:
          createClock(),
      });

    const result =
      controller.render();

    assert.equal(
      result.mounted,
      true,
    );

    assert.match(
      root.innerHTML,
      /仮想口座ダッシュボード/,
    );

    assert.equal(
      controller
        .getSnapshot()
        .cash,
      1_000_000,
    );
  },
);

test(
  "注文受付・約定・時価評価を一括管理",
  () => {
    const controller =
      createPaperDashboardController({
        root:
          createRoot(),

        storage:
          createMemoryStorage(),

        nowProvider:
          createClock(),
      });

    const submitted =
      controller.submitOrder({
        orderInput: {
          orderId:
            "controller-buy-1",

          symbol:
            "7203.t",

          side:
            "buy",

          quantity:
            100,

          type:
            "market",
        },

        estimatedPrice:
          2_000,
      });

    assert.equal(
      submitted.order.symbol,
      "7203.T",
    );

    assert.equal(
      submitted.order.status,
      "accepted",
    );

    const filled =
      controller.fillOrder({
        orderId:
          "controller-buy-1",

        fillPrice:
          2_000,
      });

    assert.equal(
      filled.order.status,
      "filled",
    );

    controller.updatePrices({
      "7203.t":
        2_100,
    });

    const snapshot =
      controller.getSnapshot();

    assert.equal(
      snapshot.cash,
      800_000,
    );

    assert.equal(
      snapshot.marketValue,
      210_000,
    );

    assert.equal(
      snapshot.unrealizedPnl,
      10_000,
    );

    assert.equal(
      snapshot.equity,
      1_010_000,
    );
  },
);

test(
  "未約定注文を取消",
  () => {
    const controller =
      createPaperDashboardController({
        root:
          createRoot(),

        storage:
          createMemoryStorage(),

        nowProvider:
          createClock(),
      });

    controller.submitOrder({
      orderInput: {
        orderId:
          "controller-cancel-1",

        symbol:
          "6758.T",

        side:
          "buy",

        quantity:
          100,
      },

      estimatedPrice:
        2_000,
    });

    const cancelled =
      controller.cancelOrder({
        orderId:
          "controller-cancel-1",
      });

    assert.equal(
      cancelled.order.status,
      "cancelled",
    );

    assert.equal(
      controller
        .getSnapshot()
        .openOrders.length,
      0,
    );

    assert.equal(
      controller
        .getSnapshot()
        .reservedCash,
      0,
    );
  },
);

test(
  "Kill Switch中は新規注文を拒否",
  () => {
    const controller =
      createPaperDashboardController({
        root:
          createRoot(),

        storage:
          createMemoryStorage(),

        nowProvider:
          createClock(),
      });

    controller.activateKillSwitch({
      reason:
        "manual_test",
    });

    assert.throws(
      () =>
        controller.submitOrder({
          orderInput: {
            symbol:
              "7203.T",

            side:
              "buy",

            quantity:
              100,
          },

          estimatedPrice:
            2_000,
        }),
      /emergency_stop_enabled/,
    );

    const state =
      controller.getState();

    assert.equal(
      state.killSwitch.enabled,
      true,
    );

    assert.equal(
      state.lastError
        .actionType,
      "submit_order",
    );
  },
);

test(
  "Kill Switch解除後は注文可能",
  () => {
    const controller =
      createPaperDashboardController({
        root:
          createRoot(),

        storage:
          createMemoryStorage(),

        nowProvider:
          createClock(),
      });

    controller.activateKillSwitch();

    controller.deactivateKillSwitch();

    const result =
      controller.submitOrder({
        orderInput: {
          symbol:
            "7203.T",

          side:
            "buy",

          quantity:
            100,
        },

        estimatedPrice:
          2_000,
      });

    assert.equal(
      result.order.status,
      "accepted",
    );
  },
);

test(
  "Broker状態をStorageへ自動保存",
  () => {
    const storage =
      createMemoryStorage();

    const first =
      createPaperDashboardController({
        root:
          createRoot(),

        storage,

        nowProvider:
          createClock(),
      });

    first.submitOrder({
      orderInput: {
        orderId:
          "persist-controller-1",

        symbol:
          "7203.T",

        side:
          "buy",

        quantity:
          100,
      },

      estimatedPrice:
        2_000,
    });

    const second =
      createPaperDashboardController({
        root:
          createRoot(),

        storage,

        nowProvider:
          createClock(),
      });

    assert.equal(
      second
        .getSnapshot()
        .openOrders.length,
      1,
    );
  },
);

test(
  "Sessionを初期状態へリセット",
  () => {
    const controller =
      createPaperDashboardController({
        root:
          createRoot(),

        storage:
          createMemoryStorage(),

        initialCash:
          500_000,

        nowProvider:
          createClock(),
      });

    controller.submitOrder({
      orderInput: {
        symbol:
          "7203.T",

        side:
          "buy",

        quantity:
          100,
      },

      estimatedPrice:
        1_000,
    });

    controller.reset();

    const snapshot =
      controller.getSnapshot();

    assert.equal(
      snapshot.cash,
      500_000,
    );

    assert.equal(
      snapshot.openOrders.length,
      0,
    );

    assert.equal(
      snapshot.positionCount,
      0,
    );
  },
);