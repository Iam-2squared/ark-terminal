import {
  cancelPaperOrder,
  fillPaperOrder,
  PAPER_ORDER_STATUS,
  PAPER_ORDER_TYPES,
} from "./paper-orders.js";

export const PAPER_EXECUTION_VERSION =
  "paper-execution-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function positive(value) {
  return (
    finite(value) &&
    Number(value) > 0
  );
}

export function shouldExecuteOrder({
  order,
  marketPrice,
  highPrice = null,
  lowPrice = null,
} = {}) {
  if (
    !order ||
    !positive(marketPrice)
  ) {
    return false;
  }

  const price =
    Number(marketPrice);

  const high =
    positive(highPrice)
      ? Number(highPrice)
      : price;

  const low =
    positive(lowPrice)
      ? Number(lowPrice)
      : price;

  if (
    order.type ===
    PAPER_ORDER_TYPES.MARKET
  ) {
    return true;
  }

  if (
    order.type ===
    PAPER_ORDER_TYPES.LIMIT
  ) {
    if (order.side === "buy") {
      return (
        low <=
        Number(order.limitPrice)
      );
    }

    return (
      high >=
      Number(order.limitPrice)
    );
  }

  if (order.type === "stop") {
    if (order.side === "buy") {
      return (
        high >=
        Number(order.stopPrice)
      );
    }

    return (
      low <=
      Number(order.stopPrice)
    );
  }

  if (
    order.type ===
    "stop_limit"
  ) {
    const triggered =
      order.side === "buy"
        ? (
            high >=
            Number(order.stopPrice)
          )
        : (
            low <=
            Number(order.stopPrice)
          );

    if (!triggered) {
      return false;
    }

    if (order.side === "buy") {
      return (
        low <=
        Number(order.limitPrice)
      );
    }

    return (
      high >=
      Number(order.limitPrice)
    );
  }

  return false;
}

export function resolveExecutionPrice({
  order,
  marketPrice,
} = {}) {
  if (!positive(marketPrice)) {
    throw new Error(
      "Market price is invalid.",
    );
  }

  if (
    order.type ===
      PAPER_ORDER_TYPES.LIMIT ||
    order.type ===
      "stop_limit"
  ) {
    return Number(
      order.limitPrice,
    );
  }

  if (
    order.type ===
    "stop"
  ) {
    return Number(
      order.stopPrice,
    );
  }

  return Number(
    marketPrice,
  );
}

export function executeOrderFill({
  order,
  marketPrice,
  fillQuantity = null,
  filledAt =
    new Date().toISOString(),
} = {}) {
  if (
    !shouldExecuteOrder({
      order,
      marketPrice,
    })
  ) {
    return {
      executed: false,
      order,
      fill: null,
    };
  }

  const quantity =
    fillQuantity === null
      ? Number(
          order.remainingQuantity,
        )
      : Math.min(
          Number(fillQuantity),
          Number(
            order.remainingQuantity,
          ),
        );

  if (
    !Number.isInteger(quantity) ||
    quantity <= 0
  ) {
    throw new Error(
      "Execution quantity is invalid.",
    );
  }

  const fillPrice =
    resolveExecutionPrice({
      order,
      marketPrice,
    });

  const nextOrder =
    fillPaperOrder({
      order,
      fillPrice,
      fillQuantity:
        quantity,
      filledAt,
    });

  return {
    executed: true,

    order:
      nextOrder,

    fill: {
      orderId:
        order.orderId,

      symbol:
        order.symbol,

      side:
        order.side,

      quantity,

      price:
        fillPrice,

      notional:
        quantity *
        fillPrice,

      filledAt,
    },
  };
}

export function cancelOpenOrder({
  order,
  cancelledAt =
    new Date().toISOString(),
} = {}) {
  if (
    !order ||
    ![
      PAPER_ORDER_STATUS.PENDING,
      PAPER_ORDER_STATUS.ACCEPTED,
      PAPER_ORDER_STATUS.PARTIALLY_FILLED,
    ].includes(
      order.status,
    )
  ) {
    throw new Error(
      "Only open orders can be cancelled.",
    );
  }

  return cancelPaperOrder({
    order,
    cancelledAt,
  });
}

export function executeAvailableOrders({
  orders = [],
  prices = {},
  filledAt =
    new Date().toISOString(),
} = {}) {
  const executions = [];
  const updatedOrders = [];

  for (const order of orders) {
    const marketPrice =
      prices[
        order.symbol
      ];

    if (!positive(marketPrice)) {
      updatedOrders.push(
        order,
      );

      continue;
    }

    const result =
      executeOrderFill({
        order,
        marketPrice,
        filledAt,
      });

    updatedOrders.push(
      result.order,
    );

    if (result.executed) {
      executions.push(
        result.fill,
      );
    }
  }

  return {
    orders:
      updatedOrders,

    executions,
  };
}

export const PaperExecutionInternals = {
  finite,
  positive,
};