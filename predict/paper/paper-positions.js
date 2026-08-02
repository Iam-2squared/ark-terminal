export const PAPER_POSITIONS_VERSION =
  "paper-positions-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function emptyPosition(
  symbol,
) {
  return {
    version:
      PAPER_POSITIONS_VERSION,

    symbol,

    quantity:
      0,

    averagePrice:
      0,

    costBasis:
      0,

    marketPrice:
      null,

    marketValue:
      0,

    unrealizedPnl:
      0,

    unrealizedReturnPercent:
      0,

    realizedPnl:
      0,

    openedAt:
      null,

    updatedAt:
      null,
  };
}

export function applyBuyFill({
  position,
  symbol,
  quantity,
  price,
  filledAt =
    new Date().toISOString(),
} = {}) {
  if (
    !finite(quantity) ||
    Number(quantity) <= 0 ||
    !finite(price) ||
    Number(price) <= 0
  ) {
    throw new Error(
      "Buy fill is invalid.",
    );
  }

  const current =
    position ||
    emptyPosition(symbol);

  const currentQuantity =
    Number(
      current.quantity || 0,
    );

  const currentCost =
    currentQuantity *
    Number(
      current.averagePrice || 0,
    );

  const addedCost =
    Number(quantity) *
    Number(price);

  const nextQuantity =
    currentQuantity +
    Number(quantity);

  const averagePrice =
    (
      currentCost +
      addedCost
    ) /
    nextQuantity;

  return {
    ...current,

    symbol:
      String(symbol),

    quantity:
      nextQuantity,

    averagePrice,

    costBasis:
      nextQuantity *
      averagePrice,

    marketPrice:
      Number(price),

    marketValue:
      nextQuantity *
      Number(price),

    unrealizedPnl:
      nextQuantity *
      (
        Number(price) -
        averagePrice
      ),

    unrealizedReturnPercent:
      averagePrice > 0
        ? (
            (
              Number(price) -
              averagePrice
            ) /
            averagePrice
          ) * 100
        : 0,

    openedAt:
      current.openedAt ||
      filledAt,

    updatedAt:
      filledAt,
  };
}

export function applySellFill({
  position,
  quantity,
  price,
  filledAt =
    new Date().toISOString(),
} = {}) {
  if (!position) {
    throw new Error(
      "Position is required.",
    );
  }

  if (
    !finite(quantity) ||
    Number(quantity) <= 0 ||
    Number(quantity) >
      Number(position.quantity)
  ) {
    throw new Error(
      "Sell quantity exceeds position.",
    );
  }

  if (
    !finite(price) ||
    Number(price) <= 0
  ) {
    throw new Error(
      "Sell price is invalid.",
    );
  }

  const soldQuantity =
    Number(quantity);

  const averagePrice =
    Number(
      position.averagePrice,
    );

  const realizedPnl =
    soldQuantity *
    (
      Number(price) -
      averagePrice
    );

  const remainingQuantity =
    Number(position.quantity) -
    soldQuantity;

  if (
    remainingQuantity === 0
  ) {
    return {
      position: null,
      realizedPnl,
    };
  }

  const nextPosition = {
    ...position,

    quantity:
      remainingQuantity,

    costBasis:
      remainingQuantity *
      averagePrice,

    marketPrice:
      Number(price),

    marketValue:
      remainingQuantity *
      Number(price),

    unrealizedPnl:
      remainingQuantity *
      (
        Number(price) -
        averagePrice
      ),

    unrealizedReturnPercent:
      averagePrice > 0
        ? (
            (
              Number(price) -
              averagePrice
            ) /
            averagePrice
          ) * 100
        : 0,

    realizedPnl:
      Number(
        position.realizedPnl || 0,
      ) +
      realizedPnl,

    updatedAt:
      filledAt,
  };

  return {
    position:
      nextPosition,

    realizedPnl,
  };
}

export function markPosition({
  position,
  marketPrice,
  updatedAt =
    new Date().toISOString(),
} = {}) {
  if (
    !position ||
    !finite(marketPrice) ||
    Number(marketPrice) <= 0
  ) {
    return position;
  }

  const price =
    Number(marketPrice);

  const quantity =
    Number(
      position.quantity || 0,
    );

  const averagePrice =
    Number(
      position.averagePrice || 0,
    );

  return {
    ...position,

    marketPrice:
      price,

    marketValue:
      quantity *
      price,

    unrealizedPnl:
      quantity *
      (
        price -
        averagePrice
      ),

    unrealizedReturnPercent:
      averagePrice > 0
        ? (
            (
              price -
              averagePrice
            ) /
            averagePrice
          ) * 100
        : 0,

    updatedAt,
  };
}

export function summarizePositions(
  positions = {},
) {
  const rows =
    Object.values(
      positions || {},
    );

  return {
    count:
      rows.length,

    marketValue:
      rows.reduce(
        (sum, row) =>
          sum +
          Number(
            row.marketValue || 0,
          ),
        0,
      ),

    unrealizedPnl:
      rows.reduce(
        (sum, row) =>
          sum +
          Number(
            row.unrealizedPnl || 0,
          ),
        0,
      ),
  };
}

export const PaperPositionsInternals = {
  finite,
  emptyPosition,
};