export const EXECUTION_SIMULATOR_V2_VERSION =
  "execution-simulator-v2";

function finiteOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function positiveNumber(
  value,
  fallback = 0,
) {
  const number =
    finiteOrNull(value);

  if (
    number === null ||
    number < 0
  ) {
    return fallback;
  }

  return number;
}

function clamp(
  value,
  minimum = 0,
  maximum = 1,
) {
  const number =
    finiteOrNull(value);

  if (number === null) {
    return null;
  }

  return Math.min(
    maximum,
    Math.max(
      minimum,
      number,
    ),
  );
}

function round(
  value,
  digits = 6,
) {
  if (!Number.isFinite(value)) {
    return value;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value * factor,
    ) / factor
  );
}

function normalizeSide(value) {
  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "BUY",
      "LONG",
      "B",
    ].includes(text)
  ) {
    return "BUY";
  }

  if (
    [
      "SELL",
      "SHORT",
      "S",
    ].includes(text)
  ) {
    return "SELL";
  }

  throw new TypeError(
    "Execution order side must be BUY or SELL.",
  );
}

function normalizeOrderType(value) {
  const text =
    String(
      value ??
      "MARKET",
    )
      .trim()
      .toUpperCase();

  if (
    [
      "MARKET",
      "LIMIT",
    ].includes(text)
  ) {
    return text;
  }

  throw new TypeError(
    "Execution order type must be MARKET or LIMIT.",
  );
}

function normalizeOrder(
  order = {},
) {
  if (
    !order ||
    typeof order !== "object" ||
    Array.isArray(order)
  ) {
    throw new TypeError(
      "Execution order must be an object.",
    );
  }

  const quantity =
    finiteOrNull(
      order.quantity ??
      order.shares ??
      order.units,
    );

  if (
    quantity === null ||
    quantity <= 0
  ) {
    throw new TypeError(
      "Execution order quantity must be greater than zero.",
    );
  }

  const type =
    normalizeOrderType(
      order.type ??
      order.orderType,
    );

  const limitPrice =
    finiteOrNull(
      order.limitPrice ??
      order.price,
    );

  if (
    type === "LIMIT" &&
    (
      limitPrice === null ||
      limitPrice <= 0
    )
  ) {
    throw new TypeError(
      "Limit order requires a valid limit price.",
    );
  }

  return {
    id:
      String(
        order.id ??
        `order-${Date.now()}`,
      ),

    symbol:
      String(
        order.symbol ??
        order.code ??
        "UNKNOWN",
      ),

    side:
      normalizeSide(
        order.side,
      ),

    type,

    quantity,

    limitPrice,

    timestamp:
      order.timestamp ??
      null,
  };
}

function normalizeMarket(
  market = {},
) {
  const bid =
    finiteOrNull(
      market.bid,
    );

  const ask =
    finiteOrNull(
      market.ask,
    );

  const last =
    finiteOrNull(
      market.last ??
      market.price ??
      market.close,
    );

  const referencePrice =
    last ??
    (
      bid !== null &&
      ask !== null
        ? (
            bid +
            ask
          ) /
          2
        : bid ??
          ask
    );

  if (
    referencePrice === null ||
    referencePrice <= 0
  ) {
    throw new TypeError(
      "Execution market requires a valid price.",
    );
  }

  return {
    bid:
      bid ??
      referencePrice,

    ask:
      ask ??
      referencePrice,

    last:
      last ??
      referencePrice,

    volume:
      positiveNumber(
        market.volume ??
        market.availableVolume,
        Infinity,
      ),

    volatility:
      positiveNumber(
        market.volatility,
        0,
      ),

    liquidityScore:
      clamp(
        (
          finiteOrNull(
            market.liquidityScore,
          ) ??
          100
        ) /
        100,
        0,
        1,
      ) ?? 1,
  };
}

function calculateReferencePrice(
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

function limitOrderExecutable(
  order,
  market,
) {
  if (
    order.type === "MARKET"
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

function calculateFillRatio({
  order,
  market,
  participationRate,
  minimumFillRatio,
}) {
  if (
    !Number.isFinite(
      market.volume,
    )
  ) {
    return 1;
  }

  const maximumAvailable =
    market.volume *
    participationRate *
    (
      0.25 +
      market.liquidityScore *
      0.75
    );

  const rawRatio =
    maximumAvailable /
    order.quantity;

  return Math.min(
    1,
    Math.max(
      minimumFillRatio,
      rawRatio,
    ),
  );
}

function calculateSlippagePercent({
  order,
  market,
  filledQuantity,
  baseSlippageBps,
  impactFactor,
}) {
  const base =
    positiveNumber(
      baseSlippageBps,
      0,
    ) /
    100;

  const participation =
    Number.isFinite(
      market.volume,
    ) &&
    market.volume > 0
      ? filledQuantity /
        market.volume
      : 0;

  const liquidityPenalty =
    (
      1 -
      market.liquidityScore
    ) *
    0.5;

  const volatilityPenalty =
    market.volatility *
    0.05;

  const impact =
    participation *
    positiveNumber(
      impactFactor,
      1,
    ) *
    100;

  return (
    base +
    liquidityPenalty +
    volatilityPenalty +
    impact
  );
}

function calculateExecutionPrice({
  order,
  referencePrice,
  slippagePercent,
}) {
  const direction =
    order.side === "BUY"
      ? 1
      : -1;

  let executionPrice =
    referencePrice *
    (
      1 +
      direction *
      slippagePercent /
      100
    );

  if (
    order.type === "LIMIT"
  ) {
    if (
      order.side === "BUY"
    ) {
      executionPrice =
        Math.min(
          executionPrice,
          order.limitPrice,
        );
    } else {
      executionPrice =
        Math.max(
          executionPrice,
          order.limitPrice,
        );
    }
  }

  return executionPrice;
}

function calculateFees({
  grossValue,
  commissionRate,
  minimumCommission,
  exchangeFeeRate,
}) {
  const commission =
    Math.max(
      positiveNumber(
        minimumCommission,
        0,
      ),
      grossValue *
      positiveNumber(
        commissionRate,
        0,
      ),
    );

  const exchangeFee =
    grossValue *
    positiveNumber(
      exchangeFeeRate,
      0,
    );

  return {
    commission:
      round(commission),

    exchangeFee:
      round(exchangeFee),

    total:
      round(
        commission +
        exchangeFee,
      ),
  };
}

export function simulateExecution({
  order,
  market,
  commissionRate = 0.0005,
  minimumCommission = 0,
  exchangeFeeRate = 0,
  baseSlippageBps = 2,
  impactFactor = 1,
  participationRate = 0.1,
  minimumFillRatio = 0,
} = {}) {
  const normalizedOrder =
    normalizeOrder(
      order,
    );

  const normalizedMarket =
    normalizeMarket(
      market,
    );

  const executable =
    limitOrderExecutable(
      normalizedOrder,
      normalizedMarket,
    );

  if (!executable) {
    return {
      version:
        EXECUTION_SIMULATOR_V2_VERSION,

      order:
        normalizedOrder,

      status:
        "UNFILLED",

      filledQuantity:
        0,

      remainingQuantity:
        normalizedOrder.quantity,

      fillRatio:
        0,

      executionPrice:
        null,

      grossValue:
        0,

      fees: {
        commission:
          0,

        exchangeFee:
          0,

        total:
          0,
      },

      netCashFlow:
        0,

      slippagePercent:
        null,

      reason:
        "Limit price was not reached.",
    };
  }

  const normalizedParticipationRate =
    clamp(
      participationRate,
      0.000001,
      1,
    ) ?? 0.1;

  const normalizedMinimumFillRatio =
    clamp(
      minimumFillRatio,
      0,
      1,
    ) ?? 0;

  const fillRatio =
    calculateFillRatio({
      order:
        normalizedOrder,

      market:
        normalizedMarket,

      participationRate:
        normalizedParticipationRate,

      minimumFillRatio:
        normalizedMinimumFillRatio,
    });

  const filledQuantity =
    Math.min(
      normalizedOrder.quantity,
      normalizedOrder.quantity *
      fillRatio,
    );

  const referencePrice =
    calculateReferencePrice(
      normalizedOrder,
      normalizedMarket,
    );

  const slippagePercent =
    calculateSlippagePercent({
      order:
        normalizedOrder,

      market:
        normalizedMarket,

      filledQuantity,

      baseSlippageBps,

      impactFactor,
    });

  const executionPrice =
    calculateExecutionPrice({
      order:
        normalizedOrder,

      referencePrice,

      slippagePercent,
    });

  const grossValue =
    executionPrice *
    filledQuantity;

  const fees =
    calculateFees({
      grossValue,

      commissionRate,

      minimumCommission,

      exchangeFeeRate,
    });

  const signedGross =
    normalizedOrder.side === "BUY"
      ? -grossValue
      : grossValue;

  const netCashFlow =
    signedGross -
    fees.total;

  const remainingQuantity =
    normalizedOrder.quantity -
    filledQuantity;

  const status =
    remainingQuantity <=
    0.0000001
      ? "FILLED"
      : "PARTIALLY_FILLED";

  return {
    version:
      EXECUTION_SIMULATOR_V2_VERSION,

    order:
      normalizedOrder,

    market:
      normalizedMarket,

    status,

    filledQuantity:
      round(
        filledQuantity,
      ),

    remainingQuantity:
      round(
        Math.max(
          0,
          remainingQuantity,
        ),
      ),

    fillRatio:
      round(
        fillRatio,
      ),

    fillRatioPercent:
      round(
        fillRatio *
        100,
        2,
      ),

    referencePrice:
      round(
        referencePrice,
      ),

    executionPrice:
      round(
        executionPrice,
      ),

    slippagePercent:
      round(
        slippagePercent,
      ),

    slippageCost:
      round(
        Math.abs(
          executionPrice -
          referencePrice
        ) *
        filledQuantity,
      ),

    grossValue:
      round(
        grossValue,
      ),

    fees,

    netCashFlow:
      round(
        netCashFlow,
      ),

    diagnostics: {
      participationRate:
        normalizedParticipationRate,

      liquidityScore:
        normalizedMarket.liquidityScore,

      volume:
        normalizedMarket.volume,

      marketImpactEnabled:
        positiveNumber(
          impactFactor,
          0,
        ) > 0,
    },
  };
}

export function simulateExecutionBatch({
  orders = [],
  marketBySymbol = {},
  config = {},
} = {}) {
  if (!Array.isArray(orders)) {
    throw new TypeError(
      "Execution batch orders must be an array.",
    );
  }

  const executions =
    orders.map(
      (
        order,
      ) => {
        const symbol =
          String(
            order?.symbol ??
            order?.code ??
            "UNKNOWN",
          );

        const market =
          marketBySymbol[
            symbol
          ];

        if (!market) {
          return {
            version:
              EXECUTION_SIMULATOR_V2_VERSION,

            order,

            status:
              "REJECTED",

            reason:
              `Market data is unavailable for ${symbol}.`,
          };
        }

        return simulateExecution({
          order,
          market,
          ...config,
        });
      },
    );

  const filled =
    executions.filter(
      (
        execution,
      ) =>
        execution.status ===
          "FILLED" ||
        execution.status ===
          "PARTIALLY_FILLED",
    );

  return {
    version:
      EXECUTION_SIMULATOR_V2_VERSION,

    orderCount:
      orders.length,

    executionCount:
      executions.length,

    filledCount:
      filled.length,

    rejectedCount:
      executions.filter(
        (
          execution,
        ) =>
          execution.status ===
          "REJECTED",
      ).length,

    unfilledCount:
      executions.filter(
        (
          execution,
        ) =>
          execution.status ===
          "UNFILLED",
      ).length,

    totalFees:
      round(
        filled.reduce(
          (
            sum,
            execution,
          ) =>
            sum +
            (
              execution.fees?.total ??
              0
            ),
          0,
        ),
      ),

    totalGrossValue:
      round(
        filled.reduce(
          (
            sum,
            execution,
          ) =>
            sum +
            (
              execution.grossValue ??
              0
            ),
          0,
        ),
      ),

    executions,
  };
}

export class ExecutionSimulatorV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  execute({
    order,
    market,
    ...overrides
  } = {}) {
    return simulateExecution({
      ...this.config,
      ...overrides,
      order,
      market,
    });
  }

  executeBatch({
    orders,
    marketBySymbol,
    config = {},
  } = {}) {
    return simulateExecutionBatch({
      orders,
      marketBySymbol,
      config: {
        ...this.config,
        ...config,
      },
    });
  }
}

export const executionSimulatorV2 =
  new ExecutionSimulatorV2();

export default simulateExecution;