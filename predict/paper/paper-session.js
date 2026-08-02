import {
  createPaperBroker,
} from "./paper-broker.js";

import {
  loadPaperBroker,
  removeStoredPaperBroker,
  savePaperBroker,
} from "./paper-storage.js";

export const PAPER_SESSION_VERSION =
  "paper-session-v1";

export function startPaperSession({
  storage =
    globalThis.localStorage,
  storageKey,
  initialCash =
    1_000_000,
  now =
    new Date().toISOString(),
} = {}) {
  const loaded =
    loadPaperBroker({
      storage,
      key:
        storageKey,
    });

  if (
    loaded.loaded &&
    loaded.broker
  ) {
    return {
      version:
        PAPER_SESSION_VERSION,

      restored:
        true,

      broker:
        loaded.broker,

      storageResult:
        loaded,

      startedAt:
        now,
    };
  }

  return {
    version:
      PAPER_SESSION_VERSION,

    restored:
      false,

    broker:
      createPaperBroker({
        initialCash,
        createdAt:
          now,
      }),

    storageResult:
      loaded,

    startedAt:
      now,
  };
}

export function persistPaperSession({
  broker,
  storage =
    globalThis.localStorage,
  storageKey,
} = {}) {
  return savePaperBroker({
    broker,
    storage,
    key:
      storageKey,
  });
}

export function resetPaperSession({
  storage =
    globalThis.localStorage,
  storageKey,
  initialCash =
    1_000_000,
  now =
    new Date().toISOString(),
} = {}) {
  removeStoredPaperBroker({
    storage,
    key:
      storageKey,
  });

  const broker =
    createPaperBroker({
      initialCash,
      createdAt:
        now,
    });

  const saveResult =
    persistPaperSession({
      broker,
      storage,
      storageKey,
    });

  return {
    version:
      PAPER_SESSION_VERSION,

    broker,
    resetAt:
      now,

    saveResult,
  };
}

export function createPaperSessionController({
  storage =
    globalThis.localStorage,
  storageKey,
  initialCash =
    1_000_000,
} = {}) {
  let state =
    startPaperSession({
      storage,
      storageKey,
      initialCash,
    });

  return {
    getState() {
      return structuredClone(
        state,
      );
    },

    getBroker() {
      return structuredClone(
        state.broker,
      );
    },

    setBroker(
      broker,
      {
        persist = true,
      } = {},
    ) {
      state = {
        ...state,
        broker:
          structuredClone(
            broker,
          ),
      };

      if (persist) {
        persistPaperSession({
          broker:
            state.broker,
          storage,
          storageKey,
        });
      }

      return this.getBroker();
    },

    save() {
      return persistPaperSession({
        broker:
          state.broker,
        storage,
        storageKey,
      });
    },

    reset() {
      const reset =
        resetPaperSession({
          storage,
          storageKey,
          initialCash,
        });

      state = {
        version:
          PAPER_SESSION_VERSION,

        restored:
          false,

        broker:
          reset.broker,

        storageResult:
          reset.saveResult,

        startedAt:
          reset.resetAt,
      };

      return this.getBroker();
    },
  };
}