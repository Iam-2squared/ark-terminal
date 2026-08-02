import {
  BROKER_ADAPTER_CONTRACT_VERSION,
  BROKER_CAPABILITIES,
  BROKER_MODES,
  BROKER_ORDER_STATUS,
  validateBrokerOrder,
} from "./broker-adapter-contract.js";

export const DRY_RUN_BROKER_ADAPTER_VERSION =
  "dry-run-broker-adapter-v1";

function clone(value) {
  return structuredClone(value);
}

function createId() {
  return (
    "dry-run-" +
    Date.now()
      .toString(36) +
    "-" +
    Math.random()
      .toString(36)
      .slice(2, 10)
  );
}

export function createDryRunBrokerAdapter({
  accountId =
    "dry-run-account",

  initialCash =
    1_000_000,

  nowProvider =
    () =>
      new Date()
        .toISOString(),
} = {}) {
  let orders = [];

  const account = {
    accountId,

    currency:
      "JPY",

    cash:
      Number(
        initialCash,
      ),

    buyingPower:
      Number(
        initialCash,
      ),

    equity:
      Number(
        initialCash,
      ),

    mode:
      BROKER_MODES
        .DRY_RUN,
  };

  function getInfo() {
    return {
      adapterVersion:
        DRY_RUN_BROKER_ADAPTER_VERSION,

      contractVersion:
        BROKER_ADAPTER_CONTRACT_VERSION,

      mode:
        BROKER_MODES
          .DRY_RUN,

      provider:
        "ark-terminal",

      connected:
        true,

      liveTradingEnabled:
        false,

      capabilities: [
        BROKER_CAPABILITIES
          .ACCOUNT_READ,

        BROKER_CAPABILITIES
          .ORDER_CREATE,

        BROKER_CAPABILITIES
          .ORDER_CANCEL,

        BROKER_CAPABILITIES
          .ORDER_READ,

        BROKER_CAPABILITIES
          .POSITION_READ,
      ],
    };
  }

  function getAccount() {
    return clone(
      account,
    );
  }

  function getPositions() {
    return [];
  }

  function getOrders() {
    return clone(
      orders,
    );
  }

  function submitOrder(
    orderInput,
  ) {
    const validation =
      validateBrokerOrder(
        orderInput,
      );

    if (
      !validation.valid
    ) {
      const rejected = {
        adapterOrderId:
          createId(),

        clientOrderId:
          orderInput
            ?.clientOrderId ||
          null,

        status:
          BROKER_ORDER_STATUS
            .REJECTED,

        mode:
          BROKER_MODES
            .DRY_RUN,

        simulated:
          true,

        transmitted:
          false,

        validationErrors:
          validation.errors,

        createdAt:
          nowProvider(),
      };

      orders.push(
        rejected,
      );

      return clone(
        rejected,
      );
    }

    const createdAt =
      nowProvider();

    const order = {
      adapterOrderId:
        createId(),

      ...validation
        .normalizedOrder,

      status:
        BROKER_ORDER_STATUS
          .SIMULATED,

      mode:
        BROKER_MODES
          .DRY_RUN,

      simulated:
        true,

      transmitted:
        false,

      createdAt,

      updatedAt:
        createdAt,
    };

    orders.push(
      order,
    );

    return clone(
      order,
    );
  }

  function cancelOrder({
    adapterOrderId,
  } = {}) {
    const index =
      orders.findIndex(
        (order) =>
          order.adapterOrderId ===
          adapterOrderId,
      );

    if (index < 0) {
      throw new Error(
        "Dry-run order was not found.",
      );
    }

    const order =
      orders[index];

    if (
      order.status ===
      BROKER_ORDER_STATUS
        .CANCELLED
    ) {
      return clone(
        order,
      );
    }

    const updatedAt =
      nowProvider();

    orders[index] = {
      ...order,

      status:
        BROKER_ORDER_STATUS
          .CANCELLED,

      cancelledAt:
        updatedAt,

      updatedAt,
    };

    return clone(
      orders[index],
    );
  }

  return {
    getInfo,
    getAccount,
    getPositions,
    getOrders,
    submitOrder,
    cancelOrder,
  };
}

export const DryRunBrokerAdapterInternals = {
  clone,
  createId,
};