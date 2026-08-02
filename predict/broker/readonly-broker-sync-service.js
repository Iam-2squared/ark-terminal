import {
  normalizeReadonlyBrokerSnapshot,
} from "./readonly-broker-normalizer.js";

export const READONLY_BROKER_SYNC_SERVICE_VERSION =
  "readonly-broker-sync-service-v1";

function clone(value) {
  return structuredClone(value);
}

function toTime(value) {
  const time =
    Date.parse(
      String(value || ""),
    );

  return Number.isFinite(time)
    ? time
    : null;
}

export function createReadonlyBrokerSyncService({
  controller,

  maximumAgeMs =
    5 * 60 * 1000,

  nowProvider =
    () =>
      new Date()
        .toISOString(),
} = {}) {
  if (
    !controller ||
    typeof controller.connect !==
      "function" ||
    typeof controller.sync !==
      "function" ||
    typeof controller.getState !==
      "function"
  ) {
    throw new Error(
      "Read-only broker controller is required.",
    );
  }

  let state = {
    version:
      READONLY_BROKER_SYNC_SERVICE_VERSION,

    status:
      "idle",

    normalizedSnapshot:
      null,

    health: {
      connected: false,
      synchronized: false,
      fresh: false,
      stale: false,
      ageMs: null,
      lastSyncAt: null,
    },

    lastError:
      null,

    updatedAt:
      nowProvider(),
  };

  function evaluateHealth(
    snapshot,
  ) {
    const now =
      toTime(
        nowProvider(),
      );

    const lastSync =
      toTime(
        snapshot
          ?.synchronizedAt,
      );

    const ageMs =
      now !== null &&
      lastSync !== null
        ? Math.max(
            0,
            now - lastSync,
          )
        : null;

    const synchronized =
      Boolean(
        snapshot
          ?.synchronizedAt,
      );

    const fresh =
      synchronized &&
      ageMs !== null &&
      ageMs <=
        maximumAgeMs;

    return {
      connected:
        snapshot
          ?.connection
          ?.connected === true &&
        snapshot
          ?.connection
          ?.authenticated === true,

      synchronized,
      fresh,

      stale:
        synchronized &&
        !fresh,

      ageMs,

      lastSyncAt:
        snapshot
          ?.synchronizedAt ||
        null,
    };
  }

  function update({
    status,
    normalizedSnapshot =
      state.normalizedSnapshot,

    lastError = null,
  }) {
    state = {
      ...state,

      status,

      normalizedSnapshot:
        normalizedSnapshot
          ? clone(
              normalizedSnapshot,
            )
          : null,

      health:
        evaluateHealth(
          normalizedSnapshot,
        ),

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

      const controllerState =
        await controller.connect();

      return update({
        status:
          controllerState
            .connection
            ?.connected &&
          controllerState
            .connection
            ?.authenticated
            ? "connected"
            : "disconnected",
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

  async function synchronize() {
    try {
      update({
        status:
          "syncing",
      });

      const controllerState =
        await controller.sync();

      const normalizedSnapshot =
        normalizeReadonlyBrokerSnapshot({
          snapshot:
            controllerState.snapshot,

          provider:
            controllerState
              .snapshot
              ?.adapter
              ?.provider ||
            null,

          synchronizedAt:
            controllerState
              .snapshot
              ?.connection
              ?.lastSyncAt ||
            nowProvider(),
        });

      return update({
        status:
          "ready",

        normalizedSnapshot,
      });
    }
    catch (error) {
      update({
        status:
          "error",

        lastError: {
          action:
            "synchronize",

          message:
            error instanceof Error
              ? error.message
              : String(error),
        },
      });

      throw error;
    }
  }

  async function connectAndSynchronize() {
    await connect();

    return synchronize();
  }

  function refreshHealth() {
    return update({
      status:
        state.status,
    });
  }

  function getState() {
    return clone(state);
  }

  function getSnapshot() {
    return state
      .normalizedSnapshot
        ? clone(
            state
              .normalizedSnapshot,
          )
        : null;
  }

  function getHealth() {
    return clone(
      state.health,
    );
  }

  return {
    version:
      READONLY_BROKER_SYNC_SERVICE_VERSION,

    connect,
    synchronize,
    connectAndSynchronize,
    refreshHealth,

    getState,
    getSnapshot,
    getHealth,
  };
}

export const ReadonlyBrokerSyncServiceInternals = {
  clone,
  toTime,
};