import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperBroker,
} from "../paper/paper-broker.js";

import {
  createMemoryStorage,
  deserializePaperBroker,
  loadPaperBroker,
  removeStoredPaperBroker,
  savePaperBroker,
  serializePaperBroker,
} from "../paper/paper-storage.js";

test(
  "Paper BrokerをJSON化して復元",
  () => {
    const broker =
      createPaperBroker({
        initialCash:
          750_000,
      });

    const serialized =
      serializePaperBroker(
        broker,
      );

    const restored =
      deserializePaperBroker(
        serialized,
      );

    assert.equal(
      restored.mode,
      "paper",
    );

    assert.equal(
      restored.account.cash,
      750_000,
    );
  },
);

test(
  "Memory Storageへ保存して読込",
  () => {
    const storage =
      createMemoryStorage();

    const broker =
      createPaperBroker({
        initialCash:
          500_000,
      });

    const saved =
      savePaperBroker({
        broker,
        storage,
      });

    assert.equal(
      saved.saved,
      true,
    );

    const loaded =
      loadPaperBroker({
        storage,
      });

    assert.equal(
      loaded.loaded,
      true,
    );

    assert.equal(
      loaded.broker.account.cash,
      500_000,
    );
  },
);

test(
  "保存データを削除",
  () => {
    const storage =
      createMemoryStorage();

    savePaperBroker({
      broker:
        createPaperBroker(),
      storage,
    });

    assert.equal(
      storage.length,
      1,
    );

    assert.equal(
      removeStoredPaperBroker({
        storage,
      }),
      true,
    );

    assert.equal(
      storage.length,
      0,
    );
  },
);

test(
  "保存が無い場合はnot_found",
  () => {
    const loaded =
      loadPaperBroker({
        storage:
          createMemoryStorage(),
      });

    assert.equal(
      loaded.loaded,
      false,
    );

    assert.equal(
      loaded.reason,
      "not_found",
    );
  },
);

test(
  "壊れた保存データを安全に拒否",
  () => {
    const storage =
      createMemoryStorage({
        "ark-terminal.paper-broker.v1":
          "{broken-json",
      });

    const loaded =
      loadPaperBroker({
        storage,
      });

    assert.equal(
      loaded.loaded,
      false,
    );

    assert.equal(
      loaded.reason,
      "invalid_data",
    );
  },
);