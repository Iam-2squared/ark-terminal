import {
  BROKER_ADAPTER_CONTRACT_VERSION,
  BROKER_CAPABILITIES,
  BROKER_MODES,
  BROKER_ORDER_STATUS,
  validateBrokerOrder,
} from "./broker-adapter-contract.js";

export const DISABLED_LIVE_BROKER_ADAPTER_VERSION =
  "disabled-live-broker-adapter-v1";

function clone(value) {
  return structuredClone(value);
}

function nowIso() {
  return new Date().toISOString();
}

export function createDisabledLiveBrokerAdapter({
  provider =
    "unconfigured",

  accountId =
    null,

  reason =
    "live_adapter_not_configured",

  nowProvider =
    nowIso,
} = {}) {
  const rejectedOrders = [];

  function getInfo() {
    return {
      adapterVersion:
        DISABLED_LIVE_BROKER_ADAPTER_VERSION,

      contractVersion:
        BROKER_ADAPTER_CONTRACT_VERSION,

      mode:
        BROKER_MODES.LIVE,

      provider:
        String(provider),

      connected:
        false,

      authenticated:
        false,

      liveTradingEnabled:
        false,

      readOnly:
        true,

      disabledReason:
        String(reason),

      capabilities: [
        BROKER_CAPABILITIES.ACCOUNT_READ,
        BROKER_CAPABILITIES.ORDER_READ,
        BROKER_CAPABILITIES.POSITION_READ,
      ],
    };
  }

  function getAccount() {
    return {
      accountId,

      provider:
        String(provider),

      mode:
        BROKER_MODES.LIVE,

      connected:
        false,

      authenticated:
        false,

      available:
        false,

      reason:
        String(reason),
    };
  }

  function getPositions() {
    return [];
  }

  function getOrders() {
    return clone(
      rejectedOrders,
    );
  }

  function submitOrder(
    orderInput,
  ) {
    const validation =
      validateBrokerOrder(
        orderInput,
      );

    const rejected = {
      adapterOrderId:
        null,

      clientOrderId:
        orderInput
          ?.clientOrderId ||
        null,

      symbol:
        validation
          .normalizedOrder
          .symbol,

      side:
        validation
          .normalizedOrder
          .side,

      quantity:
        validation
          .normalizedOrder
          .quantity,

      status:
        BROKER_ORDER_STATUS.REJECTED,

      mode:
        BROKER_MODES.LIVE,

      transmitted:
        false,

      simulated:
        false,

      reason:
        validation.valid
          ? String(reason)
          : "validation_failed",

      validationErrors:
        validation.errors,

      createdAt:
        nowProvider(),
    };

    rejectedOrders.push(
      rejected,
    );

    return clone(
      rejected,
    );
  }

  function cancelOrder({
    adapterOrderId,
  } = {}) {
    return {
      adapterOrderId:
        adapterOrderId ||
        null,

      status:
        BROKER_ORDER_STATUS.REJECTED,

      mode:
        BROKER_MODES.LIVE,

      transmitted:
        false,

      cancelled:
        false,

      reason:
        String(reason),

      updatedAt:
        nowProvider(),
    };
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

export const DisabledLiveBrokerAdapterInternals = {
  clone,
  nowIso,
};