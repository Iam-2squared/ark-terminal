export const READONLY_BROKER_NORMALIZER_VERSION =
  "readonly-broker-normalizer-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function numberOrNull(value) {
  return finite(value)
    ? Number(value)
    : null;
}

function numberOrZero(value) {
  return finite(value)
    ? Number(value)
    : 0;
}

function textOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  return String(value);
}

function normalizeSymbol(value) {
  return String(value || "")
    .trim()
    .toUpperCase();
}

function normalizeSide(value) {
  const side =
    String(value || "")
      .trim()
      .toLowerCase();

  if (
    [
      "buy",
      "long",
      "買",
      "買付",
    ].includes(side)
  ) {
    return "buy";
  }

  if (
    [
      "sell",
      "short",
      "売",
      "売却",
    ].includes(side)
  ) {
    return "sell";
  }

  return "unknown";
}

function normalizeOrderStatus(value) {
  const status =
    String(value || "")
      .trim()
      .toLowerCase();

  const aliases = {
    new:
      "open",

    accepted:
      "open",

    pending:
      "open",

    open:
      "open",

    partially_filled:
      "partially-filled",

    "partially-filled":
      "partially-filled",

    filled:
      "filled",

    executed:
      "filled",

    cancelled:
      "cancelled",

    canceled:
      "cancelled",

    rejected:
      "rejected",

    expired:
      "expired",
  };

  return (
    aliases[status] ||
    "unknown"
  );
}

export function normalizeReadonlyAccount(
  account = {},
) {
  const cash =
    numberOrZero(
      account.cash ??
      account.cashBalance ??
      account.availableCash,
    );

  const buyingPower =
    numberOrZero(
      account.buyingPower ??
      account.availableBuyingPower ??
      account.availableAmount ??
      cash,
    );

  const marketValue =
    numberOrZero(
      account.marketValue ??
      account.positionsValue ??
      account.securityValue,
    );

  const equity =
    numberOrZero(
      account.equity ??
      account.totalAssets ??
      account.netAssetValue ??
      (
        cash +
        marketValue
      ),
    );

  return {
    accountId:
      textOrNull(
        account.accountId ??
        account.id ??
        account.accountNumber,
      ),

    provider:
      textOrNull(
        account.provider,
      ),

    accountType:
      textOrNull(
        account.accountType ??
        account.type,
      ),

    currency:
      String(
        account.currency ||
        "JPY",
      ).toUpperCase(),

    cash,
    buyingPower,
    marketValue,
    equity,

    realizedPnl:
      numberOrZero(
        account.realizedPnl ??
        account.realizedProfitLoss,
      ),

    unrealizedPnl:
      numberOrZero(
        account.unrealizedPnl ??
        account.unrealizedProfitLoss,
      ),

    updatedAt:
      textOrNull(
        account.updatedAt ??
        account.asOf,
      ),

    raw:
      structuredClone(
        account,
      ),
  };
}

export function normalizeReadonlyPosition(
  position = {},
) {
  const quantity =
    numberOrZero(
      position.quantity ??
      position.qty ??
      position.holdingQuantity,
    );

  const averagePrice =
    numberOrNull(
      position.averagePrice ??
      position.avgPrice ??
      position.costPrice,
    );

  const marketPrice =
    numberOrNull(
      position.marketPrice ??
      position.currentPrice ??
      position.lastPrice,
    );

  const marketValue =
    numberOrNull(
      position.marketValue ??
      position.currentValue,
    ) ??
    (
      marketPrice === null
        ? null
        : marketPrice *
          quantity
    );

  const unrealizedPnl =
    numberOrNull(
      position.unrealizedPnl ??
      position.profitLoss,
    ) ??
    (
      marketPrice !== null &&
      averagePrice !== null
        ? (
            marketPrice -
            averagePrice
          ) *
          quantity
        : null
    );

  return {
    symbol:
      normalizeSymbol(
        position.symbol ??
        position.code ??
        position.securityCode,
      ),

    name:
      textOrNull(
        position.name ??
        position.securityName,
      ),

    quantity,

    availableQuantity:
      numberOrZero(
        position.availableQuantity ??
        position.sellableQuantity ??
        quantity,
      ),

    averagePrice,
    marketPrice,
    marketValue,
    unrealizedPnl,

    unrealizedPnlPercent:
      numberOrNull(
        position.unrealizedPnlPercent ??
        position.profitLossPercent,
      ),

    currency:
      String(
        position.currency ||
        "JPY",
      ).toUpperCase(),

    accountType:
      textOrNull(
        position.accountType,
      ),

    updatedAt:
      textOrNull(
        position.updatedAt ??
        position.asOf,
      ),

    raw:
      structuredClone(
        position,
      ),
  };
}

export function normalizeReadonlyOrder(
  order = {},
) {
  return {
    orderId:
      textOrNull(
        order.orderId ??
        order.id ??
        order.executionId,
      ),

    clientOrderId:
      textOrNull(
        order.clientOrderId,
      ),

    symbol:
      normalizeSymbol(
        order.symbol ??
        order.code ??
        order.securityCode,
      ),

    name:
      textOrNull(
        order.name ??
        order.securityName,
      ),

    side:
      normalizeSide(
        order.side ??
        order.transactionType,
      ),

    type:
      String(
        order.type ??
        order.orderType ??
        "unknown",
      )
        .trim()
        .toLowerCase(),

    status:
      normalizeOrderStatus(
        order.status ??
        order.orderStatus,
      ),

    quantity:
      numberOrZero(
        order.quantity ??
        order.orderQuantity,
      ),

    filledQuantity:
      numberOrZero(
        order.filledQuantity ??
        order.executedQuantity,
      ),

    remainingQuantity:
      numberOrNull(
        order.remainingQuantity,
      ) ??
      Math.max(
        0,
        numberOrZero(
          order.quantity ??
          order.orderQuantity,
        ) -
        numberOrZero(
          order.filledQuantity ??
          order.executedQuantity,
        ),
      ),

    limitPrice:
      numberOrNull(
        order.limitPrice ??
        order.price,
      ),

    stopPrice:
      numberOrNull(
        order.stopPrice,
      ),

    averageFillPrice:
      numberOrNull(
        order.averageFillPrice ??
        order.executionPrice,
      ),

    submittedAt:
      textOrNull(
        order.submittedAt ??
        order.createdAt ??
        order.orderDate,
      ),

    updatedAt:
      textOrNull(
        order.updatedAt ??
        order.asOf,
      ),

    raw:
      structuredClone(
        order,
      ),
  };
}

export function normalizeReadonlyBrokerSnapshot({
  snapshot = {},
  provider = null,
  synchronizedAt = null,
} = {}) {
  const account =
    snapshot.account
      ? normalizeReadonlyAccount(
          {
            ...snapshot.account,
            provider:
              snapshot.account.provider ||
              provider,
          },
        )
      : null;

  const positions =
    Array.isArray(
      snapshot.positions,
    )
      ? snapshot.positions
          .map(
            normalizeReadonlyPosition,
          )
          .filter(
            (position) =>
              position.symbol &&
              position.quantity !== 0,
          )
      : [];

  const orders =
    Array.isArray(
      snapshot.orders,
    )
      ? snapshot.orders.map(
          normalizeReadonlyOrder,
        )
      : [];

  return {
    version:
      READONLY_BROKER_NORMALIZER_VERSION,

    provider:
      provider ||
      snapshot.adapter
        ?.provider ||
      account?.provider ||
      null,

    connection:
      snapshot.connection
        ? structuredClone(
            snapshot.connection,
          )
        : null,

    account,
    positions,
    orders,

    summary: {
      positionCount:
        positions.length,

      orderCount:
        orders.length,

      openOrderCount:
        orders.filter(
          (order) =>
            [
              "open",
              "partially-filled",
            ].includes(
              order.status,
            ),
        ).length,

      totalMarketValue:
        positions.reduce(
          (sum, position) =>
            sum +
            numberOrZero(
              position.marketValue,
            ),
          0,
        ),

      totalUnrealizedPnl:
        positions.reduce(
          (sum, position) =>
            sum +
            numberOrZero(
              position.unrealizedPnl,
            ),
          0,
        ),
    },

    synchronizedAt:
      synchronizedAt ||
      snapshot.connection
        ?.lastSyncAt ||
      null,

    readOnly: true,
  };
}

export const ReadonlyBrokerNormalizerInternals = {
  finite,
  numberOrNull,
  numberOrZero,
  textOrNull,
  normalizeSymbol,
  normalizeSide,
  normalizeOrderStatus,
};