import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperBroker,
  submitBrokerOrder,
} from "../paper/paper-broker.js";

import {
  createMemoryStorage,
} from "../paper/paper-storage.js";

import {
  createPaperSessionController,
  persistPaperSession,
  resetPaperSession,
  startPaperSession,
} from "../paper/paper-session.js";

test(
  "保存データが無ければ新規Session",
  () => {
    const session =
      startPaperSession({
        storage:
          createMemoryStorage(),

        initialCash:
          800_000,
      });

    assert.equal(
      session.restored,
      false,
    );

    assert.equal(
      session.broker.account.cash,
      800_000,
    );
  },
);

test(
  "保存済みBrokerを復元",
  () => {
    const storage =
      createMemoryStorage();

    let broker =
      createPaperBroker({
        initialCash:
          1_000_000,
      });

    broker =
      submitBrokerOrder({
        broker,

        orderInput: {
          orderId:
            "persist-1",

          symbol:
            "7203.T",

          side:
            "buy",

          quantity:
            100,
        },

        estimatedPrice:
          2_000,
      }).broker;

    persistPaperSession({
      broker,
      storage,
    });

    const restored =
      startPaperSession({
        storage,
      });

    assert.equal(
      restored.restored,
      true,
    );

    assert.equal(
      restored.broker.account
        .openOrders.length,
      1,
    );

    assert.equal(
      restored.broker.orderBook
        .orders.length,
      1,
    );
  },
);

test(
  "Session Controllerで更新を自動保存",
  () => {
    const storage =
      createMemoryStorage();

    const controller =
      createPaperSessionController({
        storage,
        initialCash:
          600_000,
      });

    const broker =
      controller.getBroker();

    broker.account.cash =
      550_000;

    controller.setBroker(
      broker,
    );

    const restored =
      startPaperSession({
        storage,
      });

    assert.equal(
      restored.broker.account.cash,
      550_000,
    );
  },
);

test(
  "Sessionを初期化",
  () => {
    const storage =
      createMemoryStorage();

    const reset =
      resetPaperSession({
        storage,
        initialCash:
          300_000,
      });

    assert.equal(
      reset.broker.account.cash,
      300_000,
    );

    const restored =
      startPaperSession({
        storage,
      });

    assert.equal(
      restored.restored,
      true,
    );

    assert.equal(
      restored.broker.account.cash,
      300_000,
    );
  },
);