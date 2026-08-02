export const PAPER_STORAGE_VERSION =
  "paper-storage-v1";

export const DEFAULT_PAPER_STORAGE_KEY =
  "ark-terminal.paper-broker.v1";

function validStorage(storage) {
  return Boolean(
    storage &&
    typeof storage.getItem === "function" &&
    typeof storage.setItem === "function" &&
    typeof storage.removeItem === "function"
  );
}

function clone(value) {
  return structuredClone(value);
}

export function resolvePaperStorage(
  storage =
    globalThis.localStorage,
) {
  if (!validStorage(storage)) {
    return null;
  }

  return storage;
}

export function serializePaperBroker(
  broker,
) {
  if (!broker || typeof broker !== "object") {
    throw new Error(
      "Paper broker is required.",
    );
  }

  return JSON.stringify({
    storageVersion:
      PAPER_STORAGE_VERSION,

    savedAt:
      new Date().toISOString(),

    broker:
      clone(broker),
  });
}

export function deserializePaperBroker(
  serialized,
) {
  if (
    typeof serialized !== "string" ||
    serialized.trim() === ""
  ) {
    return null;
  }

  const parsed =
    JSON.parse(serialized);

  if (
    parsed.storageVersion !==
    PAPER_STORAGE_VERSION
  ) {
    throw new Error(
      "Unsupported paper storage version.",
    );
  }

  if (
    !parsed.broker ||
    parsed.broker.mode !== "paper"
  ) {
    throw new Error(
      "Stored paper broker is invalid.",
    );
  }

  return clone(
    parsed.broker,
  );
}

export function savePaperBroker({
  broker,
  storage =
    globalThis.localStorage,
  key =
    DEFAULT_PAPER_STORAGE_KEY,
} = {}) {
  const resolvedStorage =
    resolvePaperStorage(
      storage,
    );

  if (!resolvedStorage) {
    return {
      saved: false,
      reason:
        "storage_unavailable",
      key,
    };
  }

  const serialized =
    serializePaperBroker(
      broker,
    );

  resolvedStorage.setItem(
    key,
    serialized,
  );

  return {
    saved: true,
    reason: null,
    key,
    bytes:
      serialized.length,
  };
}

export function loadPaperBroker({
  storage =
    globalThis.localStorage,
  key =
    DEFAULT_PAPER_STORAGE_KEY,
} = {}) {
  const resolvedStorage =
    resolvePaperStorage(
      storage,
    );

  if (!resolvedStorage) {
    return {
      loaded: false,
      reason:
        "storage_unavailable",
      key,
      broker: null,
    };
  }

  const serialized =
    resolvedStorage.getItem(
      key,
    );

  if (!serialized) {
    return {
      loaded: false,
      reason:
        "not_found",
      key,
      broker: null,
    };
  }

  try {
    return {
      loaded: true,
      reason: null,
      key,
      broker:
        deserializePaperBroker(
          serialized,
        ),
    };
  }
  catch (error) {
    return {
      loaded: false,
      reason:
        "invalid_data",
      key,
      broker: null,
      error:
        error instanceof Error
          ? error.message
          : String(error),
    };
  }
}

export function removeStoredPaperBroker({
  storage =
    globalThis.localStorage,
  key =
    DEFAULT_PAPER_STORAGE_KEY,
} = {}) {
  const resolvedStorage =
    resolvePaperStorage(
      storage,
    );

  if (!resolvedStorage) {
    return false;
  }

  resolvedStorage.removeItem(
    key,
  );

  return true;
}

export function createMemoryStorage(
  initialEntries = {},
) {
  const store =
    new Map(
      Object.entries(
        initialEntries,
      ),
    );

  return {
    get length() {
      return store.size;
    },

    getItem(key) {
      return store.has(
        String(key),
      )
        ? store.get(
            String(key),
          )
        : null;
    },

    setItem(key, value) {
      store.set(
        String(key),
        String(value),
      );
    },

    removeItem(key) {
      store.delete(
        String(key),
      );
    },

    clear() {
      store.clear();
    },

    key(index) {
      return (
        Array.from(
          store.keys(),
        )[index] ??
        null
      );
    },
  };
}

export const PaperStorageInternals = {
  validStorage,
  clone,
};