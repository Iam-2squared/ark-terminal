export const PAPER_TRADING_ENGINE_V3_VERSION =
  "paper-trading-engine-v3";

const ORDER_SIDES =
  new Set([
    "BUY",
    "SELL",
  ]);

const ORDER_TYPES =
  new Set([
    "MARKET",
    "LIMIT",
  ]);

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function finiteNumber(
  value,
  fallback = 0,
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return fallback;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function positiveNumber(
  value,
  fallback = 0,
) {
  return Math.max(
    0,
    finiteNumber(
      value,
      fallback,
    ),
  );
}

function round(
  value,
  digits = 4,
) {
  if (!Number.isFinite(value)) {
    return null;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value *
      factor,
    ) /
    factor
  );
}

function normalizeTimestamp(value) {
  const milliseconds =
    typeof value === "number"
      ? value
      : Date.parse(
          value ??
          new Date().toISOString(),
        );

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(
      "Paper trading timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function normalizeSymbol(value) {
  const symbol =
    String(
      value ??
      "",
    )
      .trim()
      .toUpperCase();

  if (!symbol) {
    throw new TypeError(
      "Order symbol is required.",
    );
  }

  return symbol;
}

function normalizeSide(value) {
  const side =
    String(
      value ??
      "",
    )
      .trim()
      .toUpperCase();

  if (!ORDER_SIDES.has(side)) {
    throw new TypeError(
      `Unsupported order side: ${side}`,
    );
  }

  return side;
}

function normalizeType(value) {
  const type =
    String(
      value ??
      "MARKET",
    )
      .trim()
      .toUpperCase();

  if (!ORDER_TYPES.has(type)) {
    throw new TypeError(
      `Unsupported order type: ${type}`,
    );
  }

  return type;
}

function createId(
  prefix,
  sequence,
) {
  return `${prefix}-${String(sequence).padStart(6, "0")}`;
}

export class PaperTradingEngineV3 {
  constructor({
    initialCash = 1000000,
    commissionRate = 0.001,
    slippageRate = 0.0005,
    allowShort = false,
    maximumPositionPercent = 25,
  } = {}) {
    this.initialCash =
      positiveNumber(
        initialCash,
        1000000,
      );

    this.cash =
      this.initialCash;

    this.commissionRate =
      positiveNumber(
        commissionRate,
        0.001,
      );

    this.slippageRate =
      positiveNumber(
        slippageRate,
        0.0005,
      );

    this.allowShort =
      allowShort === true;

    this.maximumPositionPercent =
      positiveNumber(
        maximumPositionPercent,
        25,
      );

    this.orders = [];
    this.trades = [];
    this.positions =
      new Map();

    this.marketPrices =
      new Map();

    this.orderSequence = 0;
    this.tradeSequence = 0;
  }

  updateMarketPrice({
    symbol,
    price,
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const normalizedSymbol =
      normalizeSymbol(
        symbol,
      );

    const normalizedPrice =
      positiveNumber(
        price,
        0,
      );

    if (normalizedPrice <= 0) {
      throw new TypeError(
        "Market price must be greater than zero.",
      );
    }

    this.marketPrices.set(
      normalizedSymbol,
      {
        price:
          normalizedPrice,

        timestamp:
          normalizeTimestamp(
            timestamp,
          ),
      },
    );

    return clone(
      this.marketPrices.get(
        normalizedSymbol,
      ),
    );
  }

  getMarketPrice(symbol) {
    return clone(
      this.marketPrices.get(
        normalizeSymbol(
          symbol,
        ),
      ) ??
      null,
    );
  }

  getPosition(symbol) {
    const normalizedSymbol =
      normalizeSymbol(
        symbol,
      );

    return clone(
      this.positions.get(
        normalizedSymbol,
      ) ?? {
        symbol:
          normalizedSymbol,

        quantity:
          0,

        averagePrice:
          0,

        realizedPnl:
          0,
      },
    );
  }

  calculateEquity() {
    let marketValue = 0;
    let unrealizedPnl = 0;

    for (
      const position of
      this.positions.values()
    ) {
      const market =
        this.marketPrices.get(
          position.symbol,
        );

      const price =
        market?.price ??
        position.averagePrice;

      marketValue +=
        position.quantity *
        price;

      unrealizedPnl +=
        position.quantity *
        (
          price -
          position.averagePrice
        );
    }

    return {
      cash:
        round(
          this.cash,
        ),

      marketValue:
        round(
          marketValue,
        ),

      equity:
        round(
          this.cash +
          marketValue,
        ),

      unrealizedPnl:
        round(
          unrealizedPnl,
        ),

      realizedPnl:
        round(
          [...this.positions.values()]
            .reduce(
              (
                total,
                position,
              ) =>
                total +
                position.realizedPnl,
              0,
            ),
        ),
    };
  }

  validatePositionLimit({
    symbol,
    side,
    quantity,
    executionPrice,
  }) {
    if (
      side !== "BUY"
    ) {
      return;
    }

    const equity =
      this.calculateEquity()
        .equity;

    const current =
      this.getPosition(
        symbol,
      );

    const newValue =
      (
        current.quantity +
        quantity
      ) *
      executionPrice;

    const maximumValue =
      equity *
      (
        this.maximumPositionPercent /
        100
      );

    if (
      newValue >
      maximumValue
    ) {
      throw new Error(
        "Maximum position size exceeded.",
      );
    }
  }

  submitOrder({
    symbol,
    side,
    quantity,
    type = "MARKET",
    limitPrice = null,
    timestamp =
      new Date().toISOString(),
    metadata = {},
  } = {}) {
    const normalizedSymbol =
      normalizeSymbol(
        symbol,
      );

    const normalizedSide =
      normalizeSide(
        side,
      );

    const normalizedType =
      normalizeType(
        type,
      );

    const normalizedQuantity =
      Math.floor(
        positiveNumber(
          quantity,
          0,
        ),
      );

    if (
      normalizedQuantity <= 0
    ) {
      throw new TypeError(
        "Order quantity must be greater than zero.",
      );
    }

    let normalizedLimitPrice =
      null;

    if (
      normalizedType ===
      "LIMIT"
    ) {
      normalizedLimitPrice =
        positiveNumber(
          limitPrice,
          0,
        );

      if (
        normalizedLimitPrice <=
        0
      ) {
        throw new TypeError(
          "Limit price must be greater than zero.",
        );
      }
    }

    this.orderSequence += 1;

    const order = {
      id:
        createId(
          "ORDER",
          this.orderSequence,
        ),

      symbol:
        normalizedSymbol,

      side:
        normalizedSide,

      quantity:
        normalizedQuantity,

      remainingQuantity:
        normalizedQuantity,

      filledQuantity:
        0,

      type:
        normalizedType,

      limitPrice:
        normalizedLimitPrice,

      status:
        "OPEN",

      averageFillPrice:
        0,

      commission:
        0,

      createdAt:
        normalizeTimestamp(
          timestamp,
        ),

      updatedAt:
        normalizeTimestamp(
          timestamp,
        ),

      metadata:
        clone(
          metadata,
        ),
    };

    this.orders.push(
      order,
    );

    return clone(
      order,
    );
  }

  shouldFill(
    order,
    marketPrice,
  ) {
    if (
      order.type ===
      "MARKET"
    ) {
      return true;
    }

    if (
      order.side ===
        "BUY" &&
      marketPrice <=
        order.limitPrice
    ) {
      return true;
    }

    if (
      order.side ===
        "SELL" &&
      marketPrice >=
        order.limitPrice
    ) {
      return true;
    }

    return false;
  }

  calculateExecutionPrice(
    order,
    marketPrice,
  ) {
    const slippage =
      marketPrice *
      this.slippageRate;

    if (
      order.side ===
      "BUY"
    ) {
      return marketPrice +
        slippage;
    }

    return marketPrice -
      slippage;
  }

  executeOrder({
    orderId,
    marketPrice = null,
    fillQuantity = null,
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const order =
      this.orders.find(
        (
          candidate,
        ) =>
          candidate.id ===
          orderId,
      );

    if (!order) {
      throw new Error(
        `Order not found: ${orderId}`,
      );
    }

    if (
      order.status !==
      "OPEN" &&
      order.status !==
      "PARTIALLY_FILLED"
    ) {
      throw new Error(
        `Order cannot be filled: ${order.status}`,
      );
    }

    const storedMarket =
      this.marketPrices.get(
        order.symbol,
      );

    const normalizedMarketPrice =
      positiveNumber(
        marketPrice ??
        storedMarket?.price,
        0,
      );

    if (
      normalizedMarketPrice <=
      0
    ) {
      throw new Error(
        "Market price is unavailable.",
      );
    }

    if (
      !this.shouldFill(
        order,
        normalizedMarketPrice,
      )
    ) {
      return clone(
        order,
      );
    }

    const quantity =
      Math.min(
        order.remainingQuantity,
        Math.floor(
          positiveNumber(
            fillQuantity,
            order.remainingQuantity,
          ),
        ),
      );

    if (
      quantity <= 0
    ) {
      throw new TypeError(
        "Fill quantity must be greater than zero.",
      );
    }

    const executionPrice =
      this.calculateExecutionPrice(
        order,
        normalizedMarketPrice,
      );

    const grossValue =
      executionPrice *
      quantity;

    const commission =
      grossValue *
      this.commissionRate;

    const position =
      this.getPosition(
        order.symbol,
      );

    if (
      order.side ===
      "BUY"
    ) {
      const totalCost =
        grossValue +
        commission;

      if (
        totalCost >
        this.cash
      ) {
        throw new Error(
          "Insufficient paper cash.",
        );
      }

      this.validatePositionLimit({
        symbol:
          order.symbol,

        side:
          order.side,

        quantity,

        executionPrice,
      });

      const oldCost =
        position.quantity *
        position.averagePrice;

      const newQuantity =
        position.quantity +
        quantity;

      position.quantity =
        newQuantity;

      position.averagePrice =
        newQuantity === 0
          ? 0
          : (
              oldCost +
              grossValue
            ) /
            newQuantity;

      this.cash -=
        totalCost;
    }
    else {
      if (
        !this.allowShort &&
        quantity >
        position.quantity
      ) {
        throw new Error(
          "Insufficient paper position.",
        );
      }

      const closingQuantity =
        Math.min(
          quantity,
          Math.max(
            0,
            position.quantity,
          ),
        );

      const realizedPnl =
        closingQuantity *
        (
          executionPrice -
          position.averagePrice
        ) -
        commission;

      position.realizedPnl +=
        realizedPnl;

      position.quantity -=
        quantity;

      if (
        position.quantity === 0
      ) {
        position.averagePrice =
          0;
      }

      this.cash +=
        grossValue -
        commission;
    }

    this.positions.set(
      order.symbol,
      position,
    );

    const previousFilledValue =
      order.averageFillPrice *
      order.filledQuantity;

    order.filledQuantity +=
      quantity;

    order.remainingQuantity -=
      quantity;

    order.averageFillPrice =
      (
        previousFilledValue +
        executionPrice *
        quantity
      ) /
      order.filledQuantity;

    order.commission +=
      commission;

    order.status =
      order.remainingQuantity ===
      0
        ? "FILLED"
        : "PARTIALLY_FILLED";

    order.updatedAt =
      normalizeTimestamp(
        timestamp,
      );

    this.tradeSequence += 1;

    const trade = {
      id:
        createId(
          "TRADE",
          this.tradeSequence,
        ),

      orderId:
        order.id,

      symbol:
        order.symbol,

      side:
        order.side,

      quantity,

      price:
        round(
          executionPrice,
        ),

      grossValue:
        round(
          grossValue,
        ),

      commission:
        round(
          commission,
        ),

      timestamp:
        order.updatedAt,
    };

    this.trades.push(
      trade,
    );

    return {
      order:
        clone(
          order,
        ),

      trade:
        clone(
          trade,
        ),

      position:
        clone(
          position,
        ),

      account:
        this.calculateEquity(),
    };
  }

  processOpenOrders({
    prices = {},
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const executions = [];

    for (
      const [
        symbol,
        price,
      ] of Object.entries(
        prices,
      )
    ) {
      this.updateMarketPrice({
        symbol,
        price,
        timestamp,
      });
    }

    for (
      const order of
      this.orders
    ) {
      if (
        order.status !==
          "OPEN" &&
        order.status !==
          "PARTIALLY_FILLED"
      ) {
        continue;
      }

      const market =
        this.marketPrices.get(
          order.symbol,
        );

      if (!market) {
        continue;
      }

      if (
        !this.shouldFill(
          order,
          market.price,
        )
      ) {
        continue;
      }

      executions.push(
        this.executeOrder({
          orderId:
            order.id,

          marketPrice:
            market.price,

          timestamp,
        }),
      );
    }

    return clone(
      executions,
    );
  }

  cancelOrder({
    orderId,
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const order =
      this.orders.find(
        (
          candidate,
        ) =>
          candidate.id ===
          orderId,
      );

    if (!order) {
      throw new Error(
        `Order not found: ${orderId}`,
      );
    }

    if (
      order.status !==
        "OPEN" &&
      order.status !==
        "PARTIALLY_FILLED"
    ) {
      throw new Error(
        `Order cannot be cancelled: ${order.status}`,
      );
    }

    order.status =
      "CANCELLED";

    order.updatedAt =
      normalizeTimestamp(
        timestamp,
      );

    return clone(
      order,
    );
  }

  getOrders() {
    return clone(
      this.orders,
    );
  }

  getTrades() {
    return clone(
      this.trades,
    );
  }

  getPositions() {
    return clone(
      [...this.positions.values()],
    );
  }

  getAccountSnapshot() {
    return {
      version:
        PAPER_TRADING_ENGINE_V3_VERSION,

      ...this.calculateEquity(),

      initialCash:
        round(
          this.initialCash,
        ),

      orders:
        this.getOrders(),

      trades:
        this.getTrades(),

      positions:
        this.getPositions(),
    };
  }

  reset() {
    this.cash =
      this.initialCash;

    this.orders = [];
    this.trades = [];

    this.positions.clear();
    this.marketPrices.clear();

    this.orderSequence = 0;
    this.tradeSequence = 0;

    return this.getAccountSnapshot();
  }
}

export const paperTradingEngineV3 =
  new PaperTradingEngineV3();

export default PaperTradingEngineV3;