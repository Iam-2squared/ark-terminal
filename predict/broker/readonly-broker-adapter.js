import {
  BROKER_ADAPTER_CONTRACT_VERSION,
  BROKER_CAPABILITIES,
  BROKER_MODES,
  BROKER_ORDER_STATUS,
} from "./broker-adapter-contract.js";

export const READONLY_BROKER_ADAPTER_VERSION =
  "readonly-broker-adapter-v1";

function clone(value) {
  return structuredClone(value);
}

function normalizeArray(
  value,
) {
  return Array.isArray(value)
    ? clone(value)
    : [];
}

function normalizeConnection(
  value = {},
) {
  return {
    connected:
      value.connected === true,

    authenticated:
      value.authenticated === true,

    provider:
      value.provider
        ? String(
            value.provider,
          )
        : "unconfigured",

    accountId:
      value.accountId
        ? String(
            value.accountId,
          )
        : null,

    connectedAt:
      value.connectedAt ||
      null,

    lastSyncAt:
      value.lastSyncAt ||
      null,

    message:
      value.message
        ? String(
            value.message,
          )
        : null,
  };
}

export function createReadonlyBrokerAdapter({
  provider =
    "unconfigured",

  accountProvider =
    async () => null,

  positionsProvider =
    async () => [],

  ordersProvider =
    async () => [],

  connectionProvider =
    async () => ({
      connected: false,
      authenticated: false,
      provider,
    }),

  nowProvider =
    () =>
      new Date()
        .toISOString(),
} = {}) {
  let connection =
    normalizeConnection({
      connected: false,
      authenticated: false,
      provider,
    });

  let account = null;
  let positions = [];
  let orders = [];

  function getInfo() {
    return {
      adapterVersion:
        READONLY_BROKER_ADAPTER_VERSION,

      contractVersion:
        BROKER_ADAPTER_CONTRACT_VERSION,

      mode:
        BROKER_MODES.LIVE,

      provider:
        connection.provider,

      connected:
        connection.connected,

      authenticated:
        connection.authenticated,

      readOnly:
        true,

      liveTradingEnabled:
        false,

      capabilities: [
        BROKER_CAPABILITIES
          .ACCOUNT_READ,

        BROKER_CAPABILITIES
          .POSITION_READ,

        BROKER_CAPABILITIES
          .ORDER_READ,
      ],
    };
  }

  async function connect() {
    const result =
      await connectionProvider();

    connection =
      normalizeConnection({
        ...result,

        provider:
          result?.provider ||
          provider,

        connectedAt:
          result?.connected ===
          true
            ? (
                result.connectedAt ||
                nowProvider()
              )
            : null,
      });

    return clone(
      connection,
    );
  }

  async function sync() {
    if (
      !connection.connected ||
      !connection.authenticated
    ) {
      throw new Error(
        "Read-only broker is not connected and authenticated.",
      );
    }

    const [
      nextAccount,
      nextPositions,
      nextOrders,
    ] =
      await Promise.all([
        accountProvider(),
        positionsProvider(),
        ordersProvider(),
      ]);

    account =
      nextAccount &&
      typeof nextAccount ===
        "object"
        ? clone(
            nextAccount,
          )
        : null;

    positions =
      normalizeArray(
        nextPositions,
      );

    orders =
      normalizeArray(
        nextOrders,
      );

    connection = {
      ...connection,

      accountId:
        account?.accountId ||
        connection.accountId ||
        null,

      lastSyncAt:
        nowProvider(),
    };

    return getSnapshot();
  }

  function disconnect() {
    connection =
      normalizeConnection({
        connected: false,
        authenticated: false,
        provider:
          connection.provider,
        message:
          "disconnected",
      });

    account = null;
    positions = [];
    orders = [];

    return clone(
      connection,
    );
  }

  function getConnection() {
    return clone(
      connection,
    );
  }

  function getAccount() {
    return account === null
      ? null
      : clone(account);
  }

  function getPositions() {
    return clone(
      positions,
    );
  }

  function getOrders() {
    return clone(
      orders,
    );
  }

  function getSnapshot() {
    return {
      adapter:
        getInfo(),

      connection:
        getConnection(),

      account:
        getAccount(),

      positions:
        getPositions(),

      orders:
        getOrders(),

      readOnly:
        true,

      synchronized:
        Boolean(
          connection.lastSyncAt,
        ),
    };
  }

  function submitOrder(
    orderInput = {},
  ) {
    return {
      status:
        BROKER_ORDER_STATUS
          .REJECTED,

      mode:
        BROKER_MODES.LIVE,

      transmitted:
        false,

      simulated:
        false,

      reason:
        "readonly_adapter",

      clientOrderId:
        orderInput.clientOrderId ||
        null,

      createdAt:
        nowProvider(),
    };
  }

  function cancelOrder({
    adapterOrderId = null,
  } = {}) {
    return {
      adapterOrderId,

      status:
        BROKER_ORDER_STATUS
          .REJECTED,

      mode:
        BROKER_MODES.LIVE,

      transmitted:
        false,

      cancelled:
        false,

      reason:
        "readonly_adapter",

      updatedAt:
        nowProvider(),
    };
  }

  return {
    getInfo,
    connect,
    sync,
    disconnect,

    getConnection,
    getSnapshot,

    getAccount,
    getPositions,
    getOrders,

    submitOrder,
    cancelOrder,
  };
}

export const ReadonlyBrokerAdapterInternals = {
  clone,
  normalizeArray,
  normalizeConnection,
};