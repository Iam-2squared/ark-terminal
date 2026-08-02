import {
  reconcileReadonlyBrokerSnapshot,
} from "./readonly-broker-reconciler.js";

export const READONLY_BROKER_RECONCILIATION_SERVICE_VERSION =
  "readonly-broker-reconciliation-service-v1";

function clone(value) {
  return structuredClone(value);
}

export function createReadonlyBrokerReconciliationService({
  brokerSnapshotProvider,
  localSnapshotProvider,

  tolerances = {},

  nowProvider =
    () =>
      new Date()
        .toISOString(),
} = {}) {
  if (
    typeof brokerSnapshotProvider !==
    "function"
  ) {
    throw new Error(
      "Broker snapshot provider is required.",
    );
  }

  if (
    typeof localSnapshotProvider !==
    "function"
  ) {
    throw new Error(
      "Local snapshot provider is required.",
    );
  }

  let state = {
    version:
      READONLY_BROKER_RECONCILIATION_SERVICE_VERSION,

    status:
      "idle",

    result:
      null,

    lastError:
      null,

    lastRunAt:
      null,

    updatedAt:
      nowProvider(),
  };

  function update({
    status,
    result =
      state.result,

    lastError = null,

    lastRunAt =
      state.lastRunAt,
  }) {
    state = {
      ...state,

      status,

      result:
        result === null
          ? null
          : clone(result),

      lastError,

      lastRunAt,

      updatedAt:
        nowProvider(),
    };

    return getState();
  }

  async function reconcile() {
    try {
      update({
        status:
          "running",
      });

      const [
        brokerSnapshot,
        localSnapshot,
      ] =
        await Promise.all([
          brokerSnapshotProvider(),
          localSnapshotProvider(),
        ]);

      const result =
        reconcileReadonlyBrokerSnapshot({
          brokerSnapshot,
          localSnapshot,
          tolerances,
        });

      const lastRunAt =
        nowProvider();

      return update({
        status:
          result.matched
            ? "matched"
            : result.safe
              ? "warning"
              : "error",

        result,
        lastError:
          null,

        lastRunAt,
      });
    }
    catch (error) {
      update({
        status:
          "error",

        lastError: {
          action:
            "reconcile",

          message:
            error instanceof Error
              ? error.message
              : String(error),
        },

        lastRunAt:
          nowProvider(),
      });

      throw error;
    }
  }

  function getState() {
    return clone(state);
  }

  function getResult() {
    return state.result ===
      null
        ? null
        : clone(
            state.result,
          );
  }

  function getDifferences() {
    return clone(
      state.result
        ?.differences ||
      [],
    );
  }

  function isSafe() {
    return (
      state.result
        ?.safe === true
    );
  }

  return {
    version:
      READONLY_BROKER_RECONCILIATION_SERVICE_VERSION,

    reconcile,

    getState,
    getResult,
    getDifferences,
    isSafe,
  };
}

export const ReadonlyBrokerReconciliationServiceInternals = {
  clone,
};