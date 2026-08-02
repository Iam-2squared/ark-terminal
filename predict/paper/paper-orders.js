export const PAPER_ORDERS_VERSION =
  "paper-orders-v1";

export const PAPER_ORDER_SIDES =
  Object.freeze({
    BUY: "buy",
    SELL: "sell",
  });

export const PAPER_ORDER_TYPES =
  Object.freeze({
    MARKET: "market",
    LIMIT: "limit",
  });

export const PAPER_ORDER_STATUS =
  Object.freeze({
    PENDING: "pending",
    ACCEPTED: "accepted",
    PARTIALLY_FILLED:
      "partially_filled",
    FILLED: "filled",
    REJECTED: "rejected",
    CANCELLED: "cancelled",
  });

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function integer(value) {
  return (
    finite(value) &&
    Number.isInteger(Number(value))
  );
}

function createId(
  prefix = "paper-order",
) {
  return (
    prefix +
    "-" +
    Date.now().toString(36) +
    "-" +
    Math.random()
      .toString(36)
      .slice(2, 10)
  );
}

export function createPaperOrder({
  orderId =
    createId(),

  symbol,

  side,

  quantity,

  type =
    PAPER_ORDER_TYPES.MARKET,

  limitPrice = null,

  timeInForce =
    "day",

  submittedAt =
    new Date().toISOString(),

  metadata = {},
} = {}) {
  const normalizedSymbol =
    String(symbol || "")
      .trim()
      .toUpperCase();

  const normalizedSide =
    String(side || "")
      .toLowerCase();

  const normalizedType =
    String(type || "")
      .toLowerCase();

  if (!normalizedSymbol) {
    throw new Error(
      "Order symbol is required.",
    );
  }

  if (
    !Object.values(
      PAPER_ORDER_SIDES,
    ).includes(
      normalizedSide,
    )
  ) {
    throw new Error(
      "Order side is invalid.",
    );
  }

  if (
    !integer(quantity) ||
    Number(quantity) <= 0
  ) {
    throw new Error(
      "Order quantity must be a positive integer.",
    );
  }

  if (
    !Object.values(
      PAPER_ORDER_TYPES,
    ).includes(
      normalizedType,
    )
  ) {
    throw new Error(
      "Order type is invalid.",
    );
  }

  if (
    normalizedType ===
      PAPER_ORDER_TYPES.LIMIT &&
    (
      !finite(limitPrice) ||
      Number(limitPrice) <= 0
    )
  ) {
    throw new Error(
      "Limit price is required.",
    );
  }

  return {
    version:
      PAPER_ORDERS_VERSION,

    orderId:
      String(orderId),

    symbol:
      normalizedSymbol,

    side:
      normalizedSide,

    type:
      normalizedType,

    quantity:
      Number(quantity),

    filledQuantity:
      0,

    remainingQuantity:
      Number(quantity),

    limitPrice:
      normalizedType ===
        PAPER_ORDER_TYPES.LIMIT
        ? Number(limitPrice)
        : null,

    averageFillPrice:
      null,

    status:
      PAPER_ORDER_STATUS.PENDING,

    rejectionReason:
      null,

    timeInForce:
      String(timeInForce),

    submittedAt,

    acceptedAt:
      null,

    filledAt:
      null,

    cancelledAt:
      null,

    metadata: {
      ...metadata,
    },
  };
}

export function acceptPaperOrder({
  order,
  acceptedAt =
    new Date().toISOString(),
} = {}) {
  return {
    ...order,

    status:
      PAPER_ORDER_STATUS.ACCEPTED,

    acceptedAt,

    rejectionReason:
      null,
  };
}

export function rejectPaperOrder({
  order,
  reason,
  rejectedAt =
    new Date().toISOString(),
} = {}) {
  return {
    ...order,

    status:
      PAPER_ORDER_STATUS.REJECTED,

    rejectionReason:
      String(
        reason ||
        "order_rejected",
      ),

    rejectedAt,
  };
}

export function fillPaperOrder({
  order,
  fillPrice,
  fillQuantity,
  filledAt =
    new Date().toISOString(),
} = {}) {
  if (
    !finite(fillPrice) ||
    Number(fillPrice) <= 0
  ) {
    throw new Error(
      "Fill price is invalid.",
    );
  }

  if (
    !integer(fillQuantity) ||
    Number(fillQuantity) <= 0
  ) {
    throw new Error(
      "Fill quantity is invalid.",
    );
  }

  const quantity =
    Math.min(
      Number(fillQuantity),
      Number(
        order.remainingQuantity,
      ),
    );

  const previousFilled =
    Number(
      order.filledQuantity || 0,
    );

  const previousNotional =
    previousFilled *
    Number(
      order.averageFillPrice || 0,
    );

  const nextFilled =
    previousFilled +
    quantity;

  const nextAverage =
    (
      previousNotional +
      quantity *
      Number(fillPrice)
    ) /
    nextFilled;

  const remaining =
    Math.max(
      0,
      Number(order.quantity) -
      nextFilled,
    );

  return {
    ...order,

    filledQuantity:
      nextFilled,

    remainingQuantity:
      remaining,

    averageFillPrice:
      nextAverage,

    status:
      remaining === 0
        ? PAPER_ORDER_STATUS.FILLED
        : PAPER_ORDER_STATUS
            .PARTIALLY_FILLED,

    filledAt:
      remaining === 0
        ? filledAt
        : order.filledAt,
  };
}

export function cancelPaperOrder({
  order,
  cancelledAt =
    new Date().toISOString(),
} = {}) {
  if (
    order.status ===
      PAPER_ORDER_STATUS.FILLED
  ) {
    throw new Error(
      "Filled order cannot be cancelled.",
    );
  }

  return {
    ...order,

    status:
      PAPER_ORDER_STATUS.CANCELLED,

    cancelledAt,
  };
}

export const PaperOrdersInternals = {
  finite,
  integer,
  createId,
};