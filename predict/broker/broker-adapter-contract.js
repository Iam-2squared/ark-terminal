export const BROKER_ADAPTER_CONTRACT_VERSION =
  "broker-adapter-contract-v1";

export const BROKER_MODES =
  Object.freeze({
    PAPER:
      "paper",

    DRY_RUN:
      "dry-run",

    LIVE:
      "live",
  });

export const BROKER_CAPABILITIES =
  Object.freeze({
    ACCOUNT_READ:
      "account-read",

    QUOTE_READ:
      "quote-read",

    ORDER_CREATE:
      "order-create",

    ORDER_CANCEL:
      "order-cancel",

    ORDER_READ:
      "order-read",

    POSITION_READ:
      "position-read",
  });

export const BROKER_ORDER_STATUS =
  Object.freeze({
    CREATED:
      "created",

    VALIDATED:
      "validated",

    SIMULATED:
      "simulated",

    SUBMITTED:
      "submitted",

    PARTIALLY_FILLED:
      "partially-filled",

    FILLED:
      "filled",

    CANCELLED:
      "cancelled",

    REJECTED:
      "rejected",

    FAILED:
      "failed",
  });

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

export function normalizeBrokerSymbol(
  value,
) {
  return String(value || "")
    .trim()
    .toUpperCase();
}

export function normalizeBrokerSide(
  value,
) {
  const side =
    String(value || "")
      .trim()
      .toLowerCase();

  if (
    side !== "buy" &&
    side !== "sell"
  ) {
    throw new Error(
      "Broker order side must be buy or sell.",
    );
  }

  return side;
}

export function normalizeBrokerOrderType(
  value = "market",
) {
  const type =
    String(value || "")
      .trim()
      .toLowerCase();

  if (
    ![
      "market",
      "limit",
      "stop",
      "stop_limit",
    ].includes(type)
  ) {
    throw new Error(
      "Broker order type is invalid.",
    );
  }

  return type;
}

export function validateBrokerOrder(
  order = {},
) {
  const errors = [];

  const symbol =
    normalizeBrokerSymbol(
      order.symbol,
    );

  if (!symbol) {
    errors.push(
      "symbol_required",
    );
  }

  let side = null;

  try {
    side =
      normalizeBrokerSide(
        order.side,
      );
  }
  catch {
    errors.push(
      "side_invalid",
    );
  }

  let type = null;

  try {
    type =
      normalizeBrokerOrderType(
        order.type ||
        "market",
      );
  }
  catch {
    errors.push(
      "type_invalid",
    );
  }

  const quantity =
    Number(
      order.quantity,
    );

  if (
    !Number.isInteger(
      quantity,
    ) ||
    quantity <= 0
  ) {
    errors.push(
      "quantity_invalid",
    );
  }

  if (
    type === "limit" ||
    type === "stop_limit"
  ) {
    if (
      !finite(
        order.limitPrice,
      ) ||
      Number(
        order.limitPrice,
      ) <= 0
    ) {
      errors.push(
        "limit_price_invalid",
      );
    }
  }

  if (
    type === "stop" ||
    type === "stop_limit"
  ) {
    if (
      !finite(
        order.stopPrice,
      ) ||
      Number(
        order.stopPrice,
      ) <= 0
    ) {
      errors.push(
        "stop_price_invalid",
      );
    }
  }

  return {
    valid:
      errors.length === 0,

    errors,

    normalizedOrder: {
      clientOrderId:
        order.clientOrderId ||
        null,

      symbol,

      side,

      type,

      quantity:
        Number.isInteger(
          quantity,
        )
          ? quantity
          : 0,

      limitPrice:
        finite(
          order.limitPrice,
        )
          ? Number(
              order.limitPrice,
            )
          : null,

      stopPrice:
        finite(
          order.stopPrice,
        )
          ? Number(
              order.stopPrice,
            )
          : null,

      timeInForce:
        String(
          order.timeInForce ||
          "day",
        )
          .trim()
          .toLowerCase(),

      metadata:
        order.metadata &&
        typeof order.metadata ===
          "object"
          ? structuredClone(
              order.metadata,
            )
          : {},
    },
  };
}

export function assertBrokerAdapter(
  adapter,
) {
  if (
    !adapter ||
    typeof adapter !==
      "object"
  ) {
    throw new Error(
      "Broker adapter is required.",
    );
  }

  const methods = [
    "getInfo",
    "getAccount",
    "getPositions",
    "getOrders",
    "submitOrder",
    "cancelOrder",
  ];

  for (
    const method of
    methods
  ) {
    if (
      typeof adapter[method] !==
      "function"
    ) {
      throw new Error(
        `Broker adapter method is missing: ${method}`,
      );
    }
  }

  return true;
}

export const BrokerAdapterContractInternals = {
  finite,
};