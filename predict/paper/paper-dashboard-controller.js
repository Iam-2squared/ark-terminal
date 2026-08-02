import {
  cancelBrokerOrder,
  createPaperBrokerSnapshot,
  fillBrokerOrder,
  markPaperBroker,
  submitBrokerOrder,
} from "./paper-broker.js";

import {
  createPaperSessionController,
} from "./paper-session.js";

import {
  createPaperKillSwitch,
  evaluatePaperTradingGuard,
} from "./paper-risk-guard.js";

import {
  mountPaperDashboard,
} from "./paper-dashboard-ui.js";

export const PAPER_DASHBOARD_CONTROLLER_VERSION =
  "paper-dashboard-controller-v1";

function clone(value) {
  return structuredClone(value);
}

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function normalizeSymbol(value) {
  return String(value || "")
    .trim()
    .toUpperCase();
}

function createControllerState({
  broker,
  killSwitch,
  createdAt,
} = {}) {
  return {
    version:
      PAPER_DASHBOARD_CONTROLLER_VERSION,

    broker:
      clone(broker),

    killSwitch:
      clone(killSwitch),

    lastAction:
      null,

    lastError:
      null,

    createdAt,

    updatedAt:
      createdAt,
  };
}

export function createPaperDashboardController({
  root = null,

  storage =
    globalThis.localStorage,

  storageKey,

  initialCash =
    1_000_000,

  riskPolicy = {},

  sectorBySymbol = {},

  nowProvider =
    () =>
      new Date().toISOString(),
} = {}) {
  const session =
    createPaperSessionController({
      storage,
      storageKey,
      initialCash,
    });

  const createdAt =
    nowProvider();

  let state =
    createControllerState({
      broker:
        session.getBroker(),

      killSwitch:
        createPaperKillSwitch({
          enabled: false,
        }),

      createdAt,
    });

  function persistBroker(
    broker,
  ) {
    session.setBroker(
      broker,
      {
        persist: true,
      },
    );
  }

  function setBroker(
    broker,
    action,
  ) {
    const updatedAt =
      nowProvider();

    state = {
      ...state,

      broker:
        clone(broker),

      lastAction: {
        ...action,
        at:
          updatedAt,
      },

      lastError:
        null,

      updatedAt,
    };

    persistBroker(
      state.broker,
    );

    return clone(
      state.broker,
    );
  }

  function setError(
    error,
    actionType,
  ) {
    const updatedAt =
      nowProvider();

    state = {
      ...state,

      lastError: {
        actionType,

        message:
          error instanceof Error
            ? error.message
            : String(error),

        at:
          updatedAt,
      },

      updatedAt,
    };
  }

  function render() {
    return mountPaperDashboard({
      root,

      broker:
        state.broker,

      sectorBySymbol,

      killSwitch:
        state.killSwitch,
    });
  }

  function evaluateGuard({
    orderInput,
    estimatedPrice,
    dailyRealizedPnl = 0,
    peakEquity = null,
  } = {}) {
    return evaluatePaperTradingGuard({
      account:
        state.broker.account,

      order: {
        ...orderInput,

        symbol:
          normalizeSymbol(
            orderInput?.symbol,
          ),
      },

      estimatedPrice,
      dailyRealizedPnl,
      peakEquity,

      policy: {
        ...riskPolicy,

        emergencyStop:
          Boolean(
            state.killSwitch
              ?.enabled,
          ),
      },
    });
  }

  function submitOrder({
    orderInput,
    estimatedPrice,
    dailyRealizedPnl = 0,
    peakEquity = null,
  } = {}) {
    try {
      if (
        !finite(estimatedPrice) ||
        Number(estimatedPrice) <= 0
      ) {
        throw new Error(
          "Estimated price is invalid.",
        );
      }

      const normalizedOrder = {
        ...orderInput,

        symbol:
          normalizeSymbol(
            orderInput?.symbol,
          ),
      };

      const guard =
        evaluateGuard({
          orderInput:
            normalizedOrder,

          estimatedPrice,
          dailyRealizedPnl,
          peakEquity,
        });

      if (!guard.passed) {
        const error =
          new Error(
            guard.reasons.join(","),
          );

        error.code =
          "PAPER_GUARD_REJECTED";

        error.guard =
          guard;

        throw error;
      }

      const submittedAt =
        nowProvider();

      const result =
        submitBrokerOrder({
          broker:
            state.broker,

          orderInput:
            normalizedOrder,

          estimatedPrice:
            Number(
              estimatedPrice,
            ),

          riskPolicy,

          submittedAt,
        });

      setBroker(
        result.broker,
        {
          type:
            "submit_order",

          orderId:
            result.order
              .orderId,

          symbol:
            result.order.symbol,

          status:
            result.order.status,
        },
      );

      render();

      return {
        ...result,
        guard,
      };
    }
    catch (error) {
      setError(
        error,
        "submit_order",
      );

      throw error;
    }
  }

  function fillOrder({
    orderId,
    fillPrice,
    fillQuantity = null,
    commission = 0,
  } = {}) {
    try {
      const result =
        fillBrokerOrder({
          broker:
            state.broker,

          orderId,

          fillPrice,
          fillQuantity,
          commission,

          filledAt:
            nowProvider(),
        });

      setBroker(
        result.broker,
        {
          type:
            "fill_order",

          orderId,

          status:
            result.order.status,
        },
      );

      render();

      return result;
    }
    catch (error) {
      setError(
        error,
        "fill_order",
      );

      throw error;
    }
  }

  function cancelOrder({
    orderId,
  } = {}) {
    try {
      const result =
        cancelBrokerOrder({
          broker:
            state.broker,

          orderId,

          cancelledAt:
            nowProvider(),
        });

      setBroker(
        result.broker,
        {
          type:
            "cancel_order",

          orderId,

          status:
            result.order.status,
        },
      );

      render();

      return result;
    }
    catch (error) {
      setError(
        error,
        "cancel_order",
      );

      throw error;
    }
  }

  function updatePrices(
    prices = {},
  ) {
    try {
      const normalizedPrices =
        Object.fromEntries(
          Object.entries(
            prices || {},
          )
            .filter(
              ([, value]) =>
                finite(value) &&
                Number(value) > 0,
            )
            .map(
              ([
                symbol,
                value,
              ]) => [
                normalizeSymbol(
                  symbol,
                ),

                Number(value),
              ],
            ),
        );

      const broker =
        markPaperBroker({
          broker:
            state.broker,

          prices:
            normalizedPrices,

          updatedAt:
            nowProvider(),
        });

      setBroker(
        broker,
        {
          type:
            "mark_prices",

          symbolCount:
            Object.keys(
              normalizedPrices,
            ).length,
        },
      );

      render();

      return clone(
        state.broker,
      );
    }
    catch (error) {
      setError(
        error,
        "mark_prices",
      );

      throw error;
    }
  }

  function activateKillSwitch({
    reason =
      "manual_stop",
  } = {}) {
    const updatedAt =
      nowProvider();

    state = {
      ...state,

      killSwitch:
        createPaperKillSwitch({
          enabled: true,
          reason,
          activatedAt:
            updatedAt,
        }),

      lastAction: {
        type:
          "activate_kill_switch",

        reason,

        at:
          updatedAt,
      },

      lastError:
        null,

      updatedAt,
    };

    render();

    return clone(
      state.killSwitch,
    );
  }

  function deactivateKillSwitch() {
    const updatedAt =
      nowProvider();

    state = {
      ...state,

      killSwitch:
        createPaperKillSwitch({
          enabled: false,
        }),

      lastAction: {
        type:
          "deactivate_kill_switch",

        at:
          updatedAt,
      },

      lastError:
        null,

      updatedAt,
    };

    render();

    return clone(
      state.killSwitch,
    );
  }

  function reset() {
    const broker =
      session.reset();

    const updatedAt =
      nowProvider();

    state =
      createControllerState({
        broker,

        killSwitch:
          createPaperKillSwitch({
            enabled: false,
          }),

        createdAt:
          updatedAt,
      });

    state.lastAction = {
      type:
        "reset_session",

      at:
        updatedAt,
    };

    render();

    return clone(
      state.broker,
    );
  }

  function getState() {
    return clone(state);
  }

  function getBroker() {
    return clone(
      state.broker,
    );
  }

  function getSnapshot() {
    return createPaperBrokerSnapshot(
      state.broker,
    );
  }

  return {
    version:
      PAPER_DASHBOARD_CONTROLLER_VERSION,

    render,
    submitOrder,
    fillOrder,
    cancelOrder,
    updatePrices,

    activateKillSwitch,
    deactivateKillSwitch,

    reset,

    getState,
    getBroker,
    getSnapshot,

    evaluateGuard,
  };
}

export const PaperDashboardControllerInternals = {
  clone,
  finite,
  normalizeSymbol,
  createControllerState,
};