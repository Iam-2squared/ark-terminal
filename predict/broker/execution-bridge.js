import {
  assertBrokerAdapter,
  validateBrokerOrder,
} from "./broker-adapter-contract.js";
import {
  BROKER_WRITE_LOCK,
  evaluateBrokerWriteLock,
} from "./broker-write-lock.js";

export const EXECUTION_BRIDGE_VERSION =
  "execution-bridge-v2";

function clone(value) {
  return structuredClone(value);
}

export function createExecutionBridge({
  adapter,

  allowLiveTrading =
    false,

  requireHumanApproval =
    true,

  approvalProvider =
    null,
} = {}) {
  assertBrokerAdapter(
    adapter,
  );

  function getInfo() {
    const adapterInfo =
      adapter.getInfo();

    return {
      version:
        EXECUTION_BRIDGE_VERSION,

      adapter:
        clone(
          adapterInfo,
        ),

      policy: {
        allowLiveTrading:
          false,

        requestedAllowLiveTrading:
          Boolean(
            allowLiveTrading,
          ),

        requireHumanApproval:
          Boolean(
            requireHumanApproval,
          ),

        approvalProviderConfigured:
          typeof approvalProvider ===
          "function",

        brokerWriteLock:
          clone(
            BROKER_WRITE_LOCK,
          ),
      },
    };
  }

  function verifyWriteSafety({
    operation,
  } = {}) {
    const lock =
      evaluateBrokerWriteLock({
        adapterInfo:
          adapter.getInfo(),

        operation,
      });

    if (lock.blocked) {
      return {
        passed: false,
        reason: lock.reason,
        lock,
      };
    }

    return {
      passed: true,
      reason: null,
      lock,
    };
  }

  function submitOrder({
    order,
    approvalToken = null,
  } = {}) {
    const validation =
      validateBrokerOrder(
        order,
      );

    if (
      !validation.valid
    ) {
      return {
        submitted: false,

        reason:
          "validation_failed",

        validation,

        brokerOrder: null,

        transmitted: false,
      };
    }

    const safety =
      verifyWriteSafety({
        operation:
          "SUBMIT_ORDER",

        order:
          validation
            .normalizedOrder,

        approvalToken,
      });

    if (!safety.passed) {
      return {
        submitted: false,

        reason:
          safety.reason,

        validation,

        brokerOrder: null,

        transmitted: false,

        safety,
      };
    }

    const brokerOrder =
      adapter.submitOrder(
        validation
          .normalizedOrder,
      );

    return {
      submitted:
        true,

      reason:
        null,

      validation,

      brokerOrder:
        clone(
          brokerOrder,
        ),

      transmitted:
        brokerOrder?.transmitted ===
        true,

      safety,
    };
  }

  function cancelOrder({
    adapterOrderId,
  } = {}) {
    const safety =
      verifyWriteSafety({
        operation:
          "CANCEL_ORDER",
      });

    if (!safety.passed) {
      return {
        adapterOrderId:
          adapterOrderId ||
          null,

        cancelled: false,
        transmitted: false,
        reason: safety.reason,
        safety,
      };
    }

    return adapter.cancelOrder({
      adapterOrderId,
    });
  }

  function getAccount() {
    return adapter.getAccount();
  }

  function getPositions() {
    return adapter.getPositions();
  }

  function getOrders() {
    return adapter.getOrders();
  }

  return {
    version:
      EXECUTION_BRIDGE_VERSION,

    getInfo,
    submitOrder,
    cancelOrder,
    getAccount,
    getPositions,
    getOrders,
  };
}

export const ExecutionBridgeInternals = {
  clone,
};