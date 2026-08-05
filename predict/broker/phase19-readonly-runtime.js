import {
  createReadonlyBrokerController,
} from "./readonly-broker-controller.js";
import {
  createReadonlyBrokerReconciliationService,
} from "./readonly-broker-reconciliation-service.js";
import {
  assertPhase19ReadonlyOperation,
  createPhase19ReadonlySafetyState,
} from "./phase19-readonly-policy.js";

export const PHASE19_READONLY_RUNTIME_VERSION =
  "phase19-readonly-runtime-v1";

function clone(value) {
  return structuredClone(value);
}

export function createPhase19ReadonlyBrokerRuntime({
  adapter,
  localSnapshotProvider,
  tolerances = {},
  nowProvider = () => new Date().toISOString(),
} = {}) {
  if (typeof localSnapshotProvider !== "function") {
    throw new Error("Local snapshot provider is required.");
  }

  const controller = createReadonlyBrokerController({
    adapter,
    nowProvider,
  });

  const reconciliation =
    createReadonlyBrokerReconciliationService({
      brokerSnapshotProvider: async () => controller.getSnapshot(),
      localSnapshotProvider,
      tolerances,
      nowProvider,
    });

  let state = {
    version: PHASE19_READONLY_RUNTIME_VERSION,
    status: "idle",
    safety: createPhase19ReadonlySafetyState(),
    connection: controller.getConnection(),
    brokerSnapshot: controller.getSnapshot(),
    reconciliation: reconciliation.getState(),
    lastError: null,
    updatedAt: nowProvider(),
  };

  function update(patch = {}) {
    state = {
      ...state,
      ...patch,
      safety: {
        ...state.safety,
        ...(patch.safety || {}),
        liveTradingEnabled: false,
        brokerExecutionAllowed: false,
        orderCreationAllowed: false,
        orderTransmissionAllowed: false,
        transmitted: false,
      },
      updatedAt: nowProvider(),
    };
    return getState();
  }

  async function connect() {
    assertPhase19ReadonlyOperation("CONNECT");
    try {
      const controllerState = await controller.connect();
      return update({
        status: controllerState.status,
        connection: controllerState.connection,
        safety: {
          connected: controllerState.connection?.connected === true,
          authenticated: controllerState.connection?.authenticated === true,
        },
        lastError: null,
      });
    }
    catch (error) {
      update({
        status: "error",
        lastError: {
          action: "connect",
          message: error instanceof Error ? error.message : String(error),
        },
      });
      throw error;
    }
  }

  async function sync() {
    assertPhase19ReadonlyOperation("READ_ACCOUNT");
    const controllerState = await controller.sync();
    const reconciliationState = await reconciliation.reconcile();
    return update({
      status: reconciliationState.status === "matched"
        ? "ready"
        : "review_required",
      brokerSnapshot: controllerState.snapshot,
      reconciliation: reconciliationState,
      lastError: null,
    });
  }

  function disconnect() {
    assertPhase19ReadonlyOperation("DISCONNECT");
    const controllerState = controller.disconnect();
    return update({
      status: "disconnected",
      connection: controllerState.connection,
      safety: {
        connected: false,
        authenticated: false,
      },
    });
  }

  function rejectWrite(operation = "ORDER") {
    return assertPhase19ReadonlyOperation(operation);
  }

  function getState() {
    return clone(state);
  }

  return {
    version: PHASE19_READONLY_RUNTIME_VERSION,
    connect,
    sync,
    disconnect,
    rejectWrite,
    getState,
    getSnapshot: () => clone(state.brokerSnapshot),
    getDifferences: () => reconciliation.getDifferences(),
  };
}
