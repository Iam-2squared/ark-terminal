export const EXECUTION_SIMULATOR_V3_VERSION =
  "execution-simulator-v3";

const SIDES =
  new Set([
    "BUY",
    "SELL",
  ]);

const TYPES =
  new Set([
    "MARKET",
    "LIMIT",
    "STOP",
    "STOP_LIMIT",
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

function clamp(
  value,
  minimum,
  maximum,
) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      value,
    ),
  );
}

function round(
  value,
  digits = 6,
) {
  if (!Number.isFinite(value)) {
    return null;
  }

  const factor =
    10 ** digits;

  return Math.round(
    value *
    factor,
  ) /
  factor;
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
      "Execution timestamp is invalid.",
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
      "Execution symbol is required.",
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

  if (!SIDES.has(side)) {
    throw new TypeError(
      `Unsupported execution side: ${side}`,
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

  if (!TYPES.has(type)) {
    throw new TypeError(
      `Unsupported execution type: ${type}`,
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

function seededRandom(seed) {
  let value =
    Math.floor(
      Math.abs(
        finiteNumber(
          seed,
          1,
        ),
      ),
    ) %
    2147483647;

  if (value === 0) {
    value = 1;
  }

  return () => {
    value =
      value *
      16807 %
      2147483647;

    return (
      value -
      1
    ) /
    2147483646;
  };
}

function normalizeOrder(
  order = {},
) {
  const type =
    normalizeType(
      order.type,
    );

  const quantity =
    Math.floor(
      positiveNumber(
        order.quantity,
        0,
      ),
    );

  if (quantity <= 0) {
    throw new TypeError(
      "Execution quantity must be greater than zero.",
    );
  }

  const limitPrice =
    order.limitPrice ===
      null ||
    order.limitPrice ===
      undefined
      ? null
      : positiveNumber(
          order.limitPrice,
          0,
        );

  const stopPrice =
    order.stopPrice ===
      null ||
    order.stopPrice ===
      undefined
      ? null
      : positiveNumber(
          order.stopPrice,
          0,
        );

  if (
    [
      "LIMIT",
      "STOP_LIMIT",
    ].includes(type) &&
    (
      limitPrice === null ||
      limitPrice <= 0
    )
  ) {
    throw new TypeError(
      "Limit price must be greater than zero.",
    );
  }

  if (
    [
      "STOP",
      "STOP_LIMIT",
    ].includes(type) &&
    (
      stopPrice === null ||
      stopPrice <= 0
    )
  ) {
    throw new TypeError(
      "Stop price must be greater than zero.",
    );
  }

  return {
    id:
      order.id ??
      null,

    symbol:
      normalizeSymbol(
        order.symbol,
      ),

    side:
      normalizeSide(
        order.side,
      ),

    type,

    quantity,

    remainingQuantity:
      Math.floor(
        positiveNumber(
          order.remainingQuantity,
          quantity,
        ),
      ),

    limitPrice,

    stopPrice,

    timeInForce:
      String(
        order.timeInForce ??
        "DAY",
      )
        .trim()
        .toUpperCase(),

    status:
      String(
        order.status ??
        "OPEN",
      )
        .trim()
        .toUpperCase(),

    triggered:
      order.triggered ===
      true,

    metadata:
      clone(
        order.metadata ??
        {},
      ),
  };
}

function normalizeMarket(
  market = {},
) {
  const bid =
    positiveNumber(
      market.bid,
      0,
    );

  const ask =
    positiveNumber(
      market.ask,
      0,
    );

  const last =
    positiveNumber(
      market.last,
      bid > 0 && ask > 0
        ? (
            bid +
            ask
          ) /
          2
        : 0,
    );

  if (
    last <= 0 &&
    bid <= 0 &&
    ask <= 0
  ) {
    throw new TypeError(
      "Market price is unavailable.",
    );
  }

  return {
    bid:
      bid > 0
        ? bid
        : last,

    ask:
      ask > 0
        ? ask
        : last,

    last:
      last > 0
        ? last
        : (
            bid +
            ask
          ) /
          2,

    volume:
      positiveNumber(
        market.volume,
        0,
      ),

    availableLiquidity:
      Math.floor(
        positiveNumber(
          market.availableLiquidity,
          Number.MAX_SAFE_INTEGER,
        ),
      ),

    volatilityPercent:
      positiveNumber(
        market.volatilityPercent,
        0,
      ),

    timestamp:
      normalizeTimestamp(
        market.timestamp,
      ),
  };
}

function stopTriggered(
  order,
  market,
) {
  if (
    ![
      "STOP",
      "STOP_LIMIT",
    ].includes(
      order.type,
    )
  ) {
    return true;
  }

  if (order.triggered) {
    return true;
  }

  if (
    order.side === "BUY"
  ) {
    return market.last >=
      order.stopPrice;
  }

  return market.last <=
    order.stopPrice;
}

function limitExecutable(
  order,
  market,
) {
  if (
    ![
      "LIMIT",
      "STOP_LIMIT",
    ].includes(
      order.type,
    )
  ) {
    return true;
  }

  if (
    order.side === "BUY"
  ) {
    return market.ask <=
      order.limitPrice;
  }

  return market.bid >=
    order.limitPrice;
}

function baseExecutionPrice(
  order,
  market,
) {
  if (
    order.side === "BUY"
  ) {
    return market.ask;
  }

  return market.bid;
}

export class ExecutionSimulatorV3 {
  constructor({
    commissionRate = 0.001,
    minimumCommission = 0,
    baseSlippageRate = 0.0005,
    marketImpactFactor = 0.1,
    maximumParticipationRate = 0.2,
    fillProbability = 1,
    seed = 1,
  } = {}) {
    this.commissionRate =
      positiveNumber(
        commissionRate,
        0.001,
      );

    this.minimumCommission =
      positiveNumber(
        minimumCommission,
        0,
      );

    this.baseSlippageRate =
      positiveNumber(
        baseSlippageRate,
        0.0005,
      );

    this.marketImpactFactor =
      positiveNumber(
        marketImpactFactor,
        0.1,
      );

    this.maximumParticipationRate =
      clamp(
        finiteNumber(
          maximumParticipationRate,
          0.2,
        ),
        0,
        1,
      );

    this.fillProbability =
      clamp(
        finiteNumber(
          fillProbability,
          1,
        ),
        0,
        1,
      );

    this.random =
      seededRandom(
        seed,
      );

    this.orders = [];
    this.executions = [];
    this.orderSequence = 0;
    this.executionSequence = 0;
  }

  submitOrder({
    timestamp =
      new Date().toISOString(),
    ...input
  } = {}) {
    const order =
      normalizeOrder(
        input,
      );

    this.orderSequence += 1;

    order.id =
      createId(
        "SIM-ORDER",
        this.orderSequence,
      );

    order.createdAt =
      normalizeTimestamp(
        timestamp,
      );

    order.updatedAt =
      order.createdAt;

    order.filledQuantity = 0;
    order.averageFillPrice = 0;
    order.totalCommission = 0;
    order.totalSlippage = 0;

    this.orders.push(
      order,
    );

    return clone(
      order,
    );
  }

  calculateFillQuantity(
    order,
    market,
  ) {
    const volumeCapacity =
      market.volume > 0
        ? Math.floor(
            market.volume *
            this.maximumParticipationRate,
          )
        : order.remainingQuantity;

    const liquidityCapacity =
      market.availableLiquidity;

    return Math.max(
      0,
      Math.min(
        order.remainingQuantity,
        volumeCapacity,
        liquidityCapacity,
      ),
    );
  }

  calculateSlippageRate({
    quantity,
    market,
  }) {
    const volatilityComponent =
      market.volatilityPercent /
      100 *
      0.05;

    const participation =
      market.volume > 0
        ? quantity /
          market.volume
        : 0;

    const impactComponent =
      participation *
      this.marketImpactFactor;

    return Math.max(
      0,
      this.baseSlippageRate +
      volatilityComponent +
      impactComponent,
    );
  }

  simulateExecution({
    orderId,
    market,
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
        `Simulation order not found: ${orderId}`,
      );
    }

    if (
      ![
        "OPEN",
        "PARTIALLY_FILLED",
      ].includes(
        order.status,
      )
    ) {
      throw new Error(
        `Simulation order cannot execute: ${order.status}`,
      );
    }

    const normalizedMarket =
      normalizeMarket({
        ...market,
        timestamp:
          market?.timestamp ??
          timestamp,
      });

    if (
      !stopTriggered(
        order,
        normalizedMarket,
      )
    ) {
      return {
        order:
          clone(order),

        execution:
          null,

        reason:
          "STOP_NOT_TRIGGERED",
      };
    }

    if (
      [
        "STOP",
        "STOP_LIMIT",
      ].includes(
        order.type,
      )
    ) {
      order.triggered = true;
    }

    if (
      !limitExecutable(
        order,
        normalizedMarket,
      )
    ) {
      return {
        order:
          clone(order),

        execution:
          null,

        reason:
          "LIMIT_NOT_MARKETABLE",
      };
    }

    if (
      this.random() >
      this.fillProbability
    ) {
      return {
        order:
          clone(order),

        execution:
          null,

        reason:
          "FILL_PROBABILITY_REJECTED",
      };
    }

    const fillQuantity =
      this.calculateFillQuantity(
        order,
        normalizedMarket,
      );

    if (fillQuantity <= 0) {
      return {
        order:
          clone(order),

        execution:
          null,

        reason:
          "NO_LIQUIDITY",
      };
    }

    const referencePrice =
      baseExecutionPrice(
        order,
        normalizedMarket,
      );

    const slippageRate =
      this.calculateSlippageRate({
        quantity:
          fillQuantity,

        market:
          normalizedMarket,
      });

    const slippagePerShare =
      referencePrice *
      slippageRate;

    const executionPrice =
      order.side === "BUY"
        ? referencePrice +
          slippagePerShare
        : referencePrice -
          slippagePerShare;

    const grossValue =
      executionPrice *
      fillQuantity;

    const commission =
      Math.max(
        this.minimumCommission,
        grossValue *
        this.commissionRate,
      );

    const previousFilledValue =
      order.averageFillPrice *
      order.filledQuantity;

    order.filledQuantity +=
      fillQuantity;

    order.remainingQuantity -=
      fillQuantity;

    order.averageFillPrice =
      (
        previousFilledValue +
        executionPrice *
        fillQuantity
      ) /
      order.filledQuantity;

    order.totalCommission +=
      commission;

    order.totalSlippage +=
      slippagePerShare *
      fillQuantity;

    order.status =
      order.remainingQuantity ===
      0
        ? "FILLED"
        : "PARTIALLY_FILLED";

    order.updatedAt =
      normalizeTimestamp(
        timestamp,
      );

    this.executionSequence += 1;

    const execution = {
      id:
        createId(
          "SIM-FILL",
          this.executionSequence,
        ),

      orderId:
        order.id,

      symbol:
        order.symbol,

      side:
        order.side,

      quantity:
        fillQuantity,

      referencePrice:
        round(
          referencePrice,
        ),

      executionPrice:
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

      slippageRate:
        round(
          slippageRate,
          8,
        ),

      slippageAmount:
        round(
          slippagePerShare *
          fillQuantity,
        ),

      marketTimestamp:
        normalizedMarket.timestamp,

      timestamp:
        order.updatedAt,
    };

    this.executions.push(
      execution,
    );

    return {
      order:
        clone(order),

      execution:
        clone(execution),

      reason:
        "EXECUTED",
    };
  }

  processMarketSnapshot({
    markets = {},
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const results = [];

    for (
      const order of
      this.orders
    ) {
      if (
        ![
          "OPEN",
          "PARTIALLY_FILLED",
        ].includes(
          order.status,
        )
      ) {
        continue;
      }

      const market =
        markets[
          order.symbol
        ];

      if (!market) {
        continue;
      }

      results.push(
        this.simulateExecution({
          orderId:
            order.id,

          market,

          timestamp,
        }),
      );
    }

    return clone(
      results,
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
        `Simulation order not found: ${orderId}`,
      );
    }

    if (
      ![
        "OPEN",
        "PARTIALLY_FILLED",
      ].includes(
        order.status,
      )
    ) {
      throw new Error(
        `Simulation order cannot cancel: ${order.status}`,
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

  expireDayOrders({
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const expired = [];

    for (
      const order of
      this.orders
    ) {
      if (
        order.timeInForce !==
        "DAY"
      ) {
        continue;
      }

      if (
        ![
          "OPEN",
          "PARTIALLY_FILLED",
        ].includes(
          order.status,
        )
      ) {
        continue;
      }

      order.status =
        "EXPIRED";

      order.updatedAt =
        normalizeTimestamp(
          timestamp,
        );

      expired.push(
        clone(order),
      );
    }

    return expired;
  }

  getOrders() {
    return clone(
      this.orders,
    );
  }

  getExecutions() {
    return clone(
      this.executions,
    );
  }

  getStatistics() {
    const totalQuantity =
      this.executions.reduce(
        (
          total,
          execution,
        ) =>
          total +
          execution.quantity,
        0,
      );

    const totalCommission =
      this.executions.reduce(
        (
          total,
          execution,
        ) =>
          total +
          execution.commission,
        0,
      );

    const totalSlippage =
      this.executions.reduce(
        (
          total,
          execution,
        ) =>
          total +
          execution.slippageAmount,
        0,
      );

    return {
      orderCount:
        this.orders.length,

      executionCount:
        this.executions.length,

      filledOrderCount:
        this.orders.filter(
          (
            order,
          ) =>
            order.status ===
            "FILLED",
        ).length,

      partialOrderCount:
        this.orders.filter(
          (
            order,
          ) =>
            order.status ===
            "PARTIALLY_FILLED",
        ).length,

      totalQuantity,

      totalCommission:
        round(
          totalCommission,
        ),

      totalSlippage:
        round(
          totalSlippage,
        ),
    };
  }

  reset() {
    this.orders = [];
    this.executions = [];
    this.orderSequence = 0;
    this.executionSequence = 0;

    return {
      orders: [],
      executions: [],
    };
  }
}

export const executionSimulatorV3 =
  new ExecutionSimulatorV3();

export default ExecutionSimulatorV3;