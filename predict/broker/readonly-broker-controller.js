import {
  assertBrokerAdapter,
} from "./broker-adapter-contract.js";

export const READONLY_BROKER_CONTROLLER_VERSION =
  "readonly-broker-controller-v1";

function clone(value) {
  return structuredClone(value);
}

export function createReadonlyBrokerController({
  adapter,

  nowProvider =
    () =>
      new Date()
        .toISOString(),
} = {}) {
  assertBrokerAdapter(
    adapter,
  );

  if (
    typeof adapter.connect !==
      "function" ||
    typeof adapter.sync !==
      "function" ||
    typeof adapter.disconnect !==
      "function" ||
    typeof adapter.getSnapshot !==
      "function"
  ) {
    throw new Error(
      "Read-only broker adapter methods are missing.",
    );
  }

  const createdAt =
    nowProvider();

  let state = {
    version:
      READONLY_BROKER_CONTROLLER_VERSION,

    status:
      "idle",

    connection:
      adapter.getConnection(),

    snapshot:
      adapter.getSnapshot(),

    lastError:
      null,

    createdAt,

    updatedAt:
      createdAt,
  };

  function update({
    status,
    connection =
      adapter.getConnection(),

    snapshot =
      adapter.getSnapshot(),

    lastError = null,
  }) {
    state = {
      ...state,

      status,
      connection:
        clone(connection),

      snapshot:
        clone(snapshot),

      lastError,

      updatedAt:
        nowProvider(),
    };

    return getState();
  }

  async function connect() {
    try {
      update({
        status:
          "connecting",
      });

      const connection =
        await adapter.connect();

      const status =
        connection.connected &&
        connection.authenticated
          ? "connected"
          : "disconnected";

      return update({
        status,
        connection,
      });
    }
    catch (error) {
      update({
        status:
          "error",

        lastError: {
          action:
            "connect",

          message:
            error instanceof Error
              ? error.message
              : String(error),
        },
      });

      throw error;
    }
  }

  async function sync() {
    try {
      update({
        status:
          "syncing",
      });

      const snapshot =
        await adapter.sync();

      return update({
        status:
          "ready",

        snapshot,
      });
    }
    catch (error) {
      update({
        status:
          "error",

        lastError: {
          action:
            "sync",

          message:
            error instanceof Error
              ? error.message
              : String(error),
        },
      });

      throw error;
    }
  }

  function disconnect() {
    const connection =
      adapter.disconnect();

    return update({
      status:
        "disconnected",

      connection,
    });
  }

  function getState() {
    return clone(state);
  }

  function getSnapshot() {
    return clone(
      state.snapshot,
    );
  }

  function getConnection() {
    return clone(
      state.connection,
    );
  }

  return {
    version:
      READONLY_BROKER_CONTROLLER_VERSION,

    connect,
    sync,
    disconnect,

    getState,
    getSnapshot,
    getConnection,
  };
}

export const ReadonlyBrokerControllerInternals = {
  clone,
};