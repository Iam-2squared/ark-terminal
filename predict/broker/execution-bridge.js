import {
  assertBrokerAdapter,
  BROKER_MODES,
  validateBrokerOrder,
} from "./broker-adapter-contract.js";

export const EXECUTION_BRIDGE_VERSION =
  "execution-bridge-v1";

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
          Boolean(
            allowLiveTrading,
          ),

        requireHumanApproval:
          Boolean(
            requireHumanApproval,
          ),
      },
    };
  }

  function verifyLiveSafety({
    order,
    approvalToken = null,
  } = {}) {
    const info =
      adapter.getInfo();

    if (
      info.mode !==
      BROKER_MODES.LIVE
    ) {
      return {
        passed: true,
        reason: null,
      };
    }

    if (!allowLiveTrading) {
      return {
        passed: false,
        reason:
          "live_trading_disabled",
      };
    }

    if (
      !info.liveTradingEnabled
    ) {
      return {
        passed: false,
        reason:
          "adapter_live_trading_disabled",
      };
    }

    if (
      requireHumanApproval
    ) {
      if (
        typeof approvalProvider !==
        "function"
      ) {
        return {
          passed: false,
          reason:
            "approval_provider_missing",
        };
      }

      const approved =
        approvalProvider({
          order:
            clone(order),

          approvalToken,
        });

      if (
        approved !== true
      ) {
        return {
          passed: false,
          reason:
            "human_approval_required",
        };
      }
    }

    return {
      passed: true,
      reason: null,
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
      };
    }

    const safety =
      verifyLiveSafety({
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
    };
  }

  function cancelOrder({
    adapterOrderId,
  } = {}) {
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