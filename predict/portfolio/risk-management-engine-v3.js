export const RISK_MANAGEMENT_ENGINE_V3_VERSION =
  "risk-management-engine-v3";

const DECISIONS =
  Object.freeze({
    ALLOW:
      "ALLOW",

    REDUCE:
      "REDUCE",

    BLOCK:
      "BLOCK",
  });

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
      "Risk management timestamp is invalid.",
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
      "Risk symbol is required.",
    );
  }

  return symbol;
}

function normalizeSector(value) {
  return (
    String(
      value ??
      "UNKNOWN",
    )
      .trim()
      .toUpperCase() ||
    "UNKNOWN"
  );
}

function normalizeSide(value) {
  const side =
    String(
      value ??
      "BUY",
    )
      .trim()
      .toUpperCase();

  if (
    side !== "BUY" &&
    side !== "SELL"
  ) {
    throw new TypeError(
      `Unsupported risk side: ${side}`,
    );
  }

  return side;
}

function classifyRisk(score) {
  if (score >= 85) {
    return "CRITICAL";
  }

  if (score >= 70) {
    return "HIGH";
  }

  if (score >= 45) {
    return "MODERATE";
  }

  if (score >= 25) {
    return "LOW";
  }

  return "VERY_LOW";
}

function decisionForRisk({
  riskScore,
  blockers,
}) {
  if (
    blockers.length > 0 ||
    riskScore >= 85
  ) {
    return DECISIONS.BLOCK;
  }

  if (riskScore >= 60) {
    return DECISIONS.REDUCE;
  }

  return DECISIONS.ALLOW;
}

function normalizePortfolio(
  portfolio = {},
) {
  const positions =
    Array.isArray(
      portfolio.positions,
    )
      ? portfolio.positions
      : [];

  return {
    cash:
      positiveNumber(
        portfolio.cash,
        0,
      ),

    equity:
      positiveNumber(
        portfolio.equity,
        portfolio.cash,
      ),

    marketValue:
      positiveNumber(
        portfolio.marketValue,
        0,
      ),

    dailyPnl:
      finiteNumber(
        portfolio.dailyPnl,
        0,
      ),

    dailyReturnPercent:
      finiteNumber(
        portfolio.dailyReturnPercent,
        0,
      ),

    drawdownPercent:
      positiveNumber(
        portfolio.drawdownPercent,
        0,
      ),

    realizedPnl:
      finiteNumber(
        portfolio.realizedPnl,
        0,
      ),

    unrealizedPnl:
      finiteNumber(
        portfolio.unrealizedPnl,
        0,
      ),

    portfolioBeta:
      finiteNumber(
        portfolio.portfolioBeta,
        1,
      ),

    portfolioVolatility:
      positiveNumber(
        portfolio.portfolioVolatility,
        0,
      ),

    positions:
      positions.map(
        (
          position,
        ) => ({
          symbol:
            normalizeSymbol(
              position.symbol,
            ),

          sector:
            normalizeSector(
              position.sector,
            ),

          quantity:
            positiveNumber(
              position.quantity,
              0,
            ),

          averagePrice:
            positiveNumber(
              position.averagePrice,
              0,
            ),

          marketPrice:
            positiveNumber(
              position.marketPrice,
              position.averagePrice,
            ),

          beta:
            finiteNumber(
              position.beta,
              1,
            ),

          volatility:
            positiveNumber(
              position.volatility,
              0,
            ),
        }),
      ),
  };
}

function positionValue(position) {
  return (
    positiveNumber(
      position.quantity,
      0,
    ) *
    positiveNumber(
      position.marketPrice,
      position.averagePrice,
    )
  );
}

function calculateSectorExposure(
  portfolio,
) {
  const exposures = {};

  for (
    const position of
    portfolio.positions
  ) {
    const sector =
      normalizeSector(
        position.sector,
      );

    exposures[sector] =
      (
        exposures[
          sector
        ] ??
        0
      ) +
      positionValue(
        position,
      );
  }

  const equity =
    portfolio.equity;

  return Object.fromEntries(
    Object.entries(
      exposures,
    ).map(
      (
        [
          sector,
          value,
        ],
      ) => [
        sector,
        equity <= 0
          ? 0
          : round(
              value /
              equity *
              100,
            ),
      ],
    ),
  );
}

function calculateConcentration(
  portfolio,
) {
  if (
    portfolio.equity <= 0 ||
    portfolio.positions.length === 0
  ) {
    return {
      largestPositionPercent:
        0,

      herfindahlIndex:
        0,

      diversificationScore:
        100,
    };
  }

  const weights =
    portfolio.positions.map(
      (
        position,
      ) =>
        positionValue(
          position,
        ) /
        portfolio.equity,
    );

  const largestPositionPercent =
    Math.max(
      0,
      ...weights,
    ) *
    100;

  const herfindahlIndex =
    weights.reduce(
      (
        total,
        weight,
      ) =>
        total +
        weight ** 2,
      0,
    );

  const diversificationScore =
    clamp(
      (
        1 -
        herfindahlIndex
      ) *
      100,
      0,
      100,
    );

  return {
    largestPositionPercent:
      round(
        largestPositionPercent,
      ),

    herfindahlIndex:
      round(
        herfindahlIndex,
        6,
      ),

    diversificationScore:
      round(
        diversificationScore,
      ),
  };
}

function calculatePortfolioExposure(
  portfolio,
) {
  if (
    portfolio.equity <= 0
  ) {
    return 0;
  }

  const value =
    portfolio.positions.reduce(
      (
        total,
        position,
      ) =>
        total +
        positionValue(
          position,
        ),
      0,
    );

  return clamp(
    value /
    portfolio.equity *
    100,
    0,
    1000,
  );
}

function calculateProjectedOrder({
  order,
  portfolio,
}) {
  const current =
    portfolio.positions.find(
      (
        position,
      ) =>
        position.symbol ===
        order.symbol,
    );

  const currentQuantity =
    current?.quantity ??
    0;

  const quantityChange =
    order.side === "BUY"
      ? order.quantity
      : -order.quantity;

  const projectedQuantity =
    currentQuantity +
    quantityChange;

  const projectedValue =
    Math.max(
      0,
      projectedQuantity,
    ) *
    order.price;

  const orderValue =
    order.quantity *
    order.price;

  const currentMarketValue =
    portfolio.positions.reduce(
      (
        total,
        position,
      ) =>
        total +
        positionValue(
          position,
        ),
      0,
    );

  const projectedMarketValue =
    order.side === "BUY"
      ? currentMarketValue +
        orderValue
      : Math.max(
          0,
          currentMarketValue -
          orderValue,
        );

  const projectedCash =
    order.side === "BUY"
      ? portfolio.cash -
        orderValue -
        order.fee
      : portfolio.cash +
        orderValue -
        order.fee;

  return {
    currentQuantity,

    projectedQuantity,

    projectedValue,

    orderValue,

    projectedMarketValue,

    projectedCash,

    projectedExposurePercent:
      portfolio.equity <= 0
        ? 0
        : projectedMarketValue /
          portfolio.equity *
          100,
  };
}

function calculateSuggestedQuantity({
  equity,
  riskPerTradePercent,
  entryPrice,
  stopPrice,
  maximumPositionPercent,
}) {
  const riskBudget =
    equity *
    riskPerTradePercent /
    100;

  const riskPerShare =
    Math.abs(
      entryPrice -
      stopPrice,
    );

  if (
    riskPerShare <= 0 ||
    entryPrice <= 0
  ) {
    return 0;
  }

  const riskQuantity =
    Math.floor(
      riskBudget /
      riskPerShare,
    );

  const maximumPositionValue =
    equity *
    maximumPositionPercent /
    100;

  const maximumPositionQuantity =
    Math.floor(
      maximumPositionValue /
      entryPrice,
    );

  return Math.max(
    0,
    Math.min(
      riskQuantity,
      maximumPositionQuantity,
    ),
  );
}

export function calculatePositionSize({
  equity,
  entryPrice,
  stopPrice,
  riskPerTradePercent = 1,
  maximumPositionPercent = 20,
  lotSize = 1,
} = {}) {
  const normalizedEquity =
    positiveNumber(
      equity,
      0,
    );

  const normalizedEntry =
    positiveNumber(
      entryPrice,
      0,
    );

  const normalizedStop =
    positiveNumber(
      stopPrice,
      0,
    );

  const normalizedRisk =
    positiveNumber(
      riskPerTradePercent,
      1,
    );

  const normalizedMaximum =
    positiveNumber(
      maximumPositionPercent,
      20,
    );

  const normalizedLotSize =
    Math.max(
      1,
      Math.floor(
        positiveNumber(
          lotSize,
          1,
        ),
      ),
    );

  if (
    normalizedEquity <= 0
  ) {
    throw new TypeError(
      "Equity must be greater than zero.",
    );
  }

  if (
    normalizedEntry <= 0
  ) {
    throw new TypeError(
      "Entry price must be greater than zero.",
    );
  }

  if (
    normalizedStop <= 0
  ) {
    throw new TypeError(
      "Stop price must be greater than zero.",
    );
  }

  const rawQuantity =
    calculateSuggestedQuantity({
      equity:
        normalizedEquity,

      riskPerTradePercent:
        normalizedRisk,

      entryPrice:
        normalizedEntry,

      stopPrice:
        normalizedStop,

      maximumPositionPercent:
        normalizedMaximum,
    });

  const quantity =
    Math.floor(
      rawQuantity /
      normalizedLotSize,
    ) *
    normalizedLotSize;

  const riskPerShare =
    Math.abs(
      normalizedEntry -
      normalizedStop,
    );

  return {
    quantity,

    riskBudget:
      round(
        normalizedEquity *
        normalizedRisk /
        100,
      ),

    riskPerShare:
      round(
        riskPerShare,
      ),

    positionValue:
      round(
        quantity *
        normalizedEntry,
      ),

    maximumPositionValue:
      round(
        normalizedEquity *
        normalizedMaximum /
        100,
      ),

    lotSize:
      normalizedLotSize,
  };
}

export function calculateValueAtRisk({
  equity,
  volatilityPercent,
  confidenceMultiplier = 1.65,
  holdingPeriodDays = 1,
} = {}) {
  const normalizedEquity =
    positiveNumber(
      equity,
      0,
    );

  const normalizedVolatility =
    positiveNumber(
      volatilityPercent,
      0,
    ) /
    100;

  const normalizedConfidence =
    positiveNumber(
      confidenceMultiplier,
      1.65,
    );

  const normalizedHoldingPeriod =
    Math.max(
      1,
      positiveNumber(
        holdingPeriodDays,
        1,
      ),
    );

  const valueAtRisk =
    normalizedEquity *
    normalizedVolatility *
    normalizedConfidence *
    Math.sqrt(
      normalizedHoldingPeriod,
    );

  return {
    value:
      round(
        valueAtRisk,
      ),

    percent:
      normalizedEquity <= 0
        ? 0
        : round(
            valueAtRisk /
            normalizedEquity *
            100,
          ),

    confidenceMultiplier:
      normalizedConfidence,

    holdingPeriodDays:
      normalizedHoldingPeriod,
  };
}

export function evaluatePortfolioRisk({
  portfolio = {},
  limits = {},
  timestamp =
    new Date().toISOString(),
} = {}) {
  const evaluatedAt =
    normalizeTimestamp(
      timestamp,
    );

  const normalized =
    normalizePortfolio(
      portfolio,
    );

  const maximumExposurePercent =
    positiveNumber(
      limits.maximumExposurePercent,
      90,
    );

  const maximumDrawdownPercent =
    positiveNumber(
      limits.maximumDrawdownPercent,
      15,
    );

  const maximumDailyLossPercent =
    positiveNumber(
      limits.maximumDailyLossPercent,
      3,
    );

  const maximumPositionPercent =
    positiveNumber(
      limits.maximumPositionPercent,
      25,
    );

  const maximumSectorPercent =
    positiveNumber(
      limits.maximumSectorPercent,
      40,
    );

  const maximumPortfolioBeta =
    positiveNumber(
      limits.maximumPortfolioBeta,
      1.5,
    );

  const maximumPortfolioVolatility =
    positiveNumber(
      limits.maximumPortfolioVolatility,
      35,
    );

  const exposurePercent =
    calculatePortfolioExposure(
      normalized,
    );

  const concentration =
    calculateConcentration(
      normalized,
    );

  const sectorExposure =
    calculateSectorExposure(
      normalized,
    );

  const largestSectorPercent =
    Math.max(
      0,
      ...Object.values(
        sectorExposure,
      ),
    );

  const dailyLossPercent =
    normalized.dailyReturnPercent <
    0
      ? Math.abs(
          normalized.dailyReturnPercent,
        )
      : 0;

  const components = {
    exposureRisk:
      clamp(
        exposurePercent /
        Math.max(
          1,
          maximumExposurePercent,
        ) *
        70,
        0,
        100,
      ),

    drawdownRisk:
      clamp(
        normalized.drawdownPercent /
        Math.max(
          1,
          maximumDrawdownPercent,
        ) *
        85,
        0,
        100,
      ),

    dailyLossRisk:
      clamp(
        dailyLossPercent /
        Math.max(
          0.01,
          maximumDailyLossPercent,
        ) *
        90,
        0,
        100,
      ),

    concentrationRisk:
      clamp(
        concentration
          .largestPositionPercent /
        Math.max(
          1,
          maximumPositionPercent,
        ) *
        70,
        0,
        100,
      ),

    sectorRisk:
      clamp(
        largestSectorPercent /
        Math.max(
          1,
          maximumSectorPercent,
        ) *
        70,
        0,
        100,
      ),

    betaRisk:
      clamp(
        Math.abs(
          normalized.portfolioBeta,
        ) /
        Math.max(
          0.1,
          maximumPortfolioBeta,
        ) *
        65,
        0,
        100,
      ),

    volatilityRisk:
      clamp(
        normalized.portfolioVolatility /
        Math.max(
          1,
          maximumPortfolioVolatility,
        ) *
        75,
        0,
        100,
      ),
  };

  const riskScore =
    clamp(
      components.exposureRisk *
        0.15 +
      components.drawdownRisk *
        0.2 +
      components.dailyLossRisk *
        0.2 +
      components.concentrationRisk *
        0.15 +
      components.sectorRisk *
        0.1 +
      components.betaRisk *
        0.1 +
      components.volatilityRisk *
        0.1,
      0,
      100,
    );

  const blockers = [];
  const warnings = [];

  if (
    exposurePercent >
    maximumExposurePercent
  ) {
    blockers.push(
      "MAXIMUM_EXPOSURE_EXCEEDED",
    );
  }

  if (
    normalized.drawdownPercent >=
    maximumDrawdownPercent
  ) {
    blockers.push(
      "MAXIMUM_DRAWDOWN_REACHED",
    );
  }

  if (
    dailyLossPercent >=
    maximumDailyLossPercent
  ) {
    blockers.push(
      "DAILY_LOSS_LIMIT_REACHED",
    );
  }

  if (
    concentration
      .largestPositionPercent >
    maximumPositionPercent
  ) {
    blockers.push(
      "POSITION_CONCENTRATION_EXCEEDED",
    );
  }

  if (
    largestSectorPercent >
    maximumSectorPercent
  ) {
    blockers.push(
      "SECTOR_CONCENTRATION_EXCEEDED",
    );
  }

  if (
    Math.abs(
      normalized.portfolioBeta,
    ) >
    maximumPortfolioBeta
  ) {
    warnings.push(
      "HIGH_PORTFOLIO_BETA",
    );
  }

  if (
    normalized.portfolioVolatility >
    maximumPortfolioVolatility
  ) {
    warnings.push(
      "HIGH_PORTFOLIO_VOLATILITY",
    );
  }

  if (
    normalized.cash <= 0
  ) {
    warnings.push(
      "NO_AVAILABLE_CASH",
    );
  }

  const level =
    classifyRisk(
      riskScore,
    );

  const decision =
    decisionForRisk({
      riskScore,
      blockers,
    });

  const positionMultiplier =
    decision === DECISIONS.BLOCK
      ? 0
      : decision === DECISIONS.REDUCE
        ? 0.5
        : level === "MODERATE"
          ? 0.75
          : 1;

  return {
    version:
      RISK_MANAGEMENT_ENGINE_V3_VERSION,

    evaluatedAt,

    status:
      blockers.length > 0
        ? "BLOCKED"
        : warnings.length > 0
          ? "WARNING"
          : "READY",

    decision,

    riskScore:
      round(
        riskScore,
      ),

    level,

    positionMultiplier,

    blockers:
      [...new Set(
        blockers,
      )],

    warnings:
      [...new Set(
        warnings,
      )],

    metrics: {
      exposurePercent:
        round(
          exposurePercent,
        ),

      drawdownPercent:
        round(
          normalized.drawdownPercent,
        ),

      dailyLossPercent:
        round(
          dailyLossPercent,
        ),

      largestPositionPercent:
        concentration
          .largestPositionPercent,

      largestSectorPercent:
        round(
          largestSectorPercent,
        ),

      diversificationScore:
        concentration
          .diversificationScore,

      portfolioBeta:
        round(
          normalized.portfolioBeta,
        ),

      portfolioVolatility:
        round(
          normalized.portfolioVolatility,
        ),

      sectorExposure,
    },

    components: Object.fromEntries(
      Object.entries(
        components,
      ).map(
        (
          [
            key,
            value,
          ],
        ) => [
          key,
          round(
            value,
          ),
        ],
      ),
    ),

    limits: {
      maximumExposurePercent,

      maximumDrawdownPercent,

      maximumDailyLossPercent,

      maximumPositionPercent,

      maximumSectorPercent,

      maximumPortfolioBeta,

      maximumPortfolioVolatility,
    },
  };
}

export function evaluateOrderRisk({
  order = {},
  portfolio = {},
  limits = {},
  timestamp =
    new Date().toISOString(),
} = {}) {
  const evaluatedAt =
    normalizeTimestamp(
      timestamp,
    );

  const normalizedPortfolio =
    normalizePortfolio(
      portfolio,
    );

  const normalizedOrder = {
    symbol:
      normalizeSymbol(
        order.symbol,
      ),

    side:
      normalizeSide(
        order.side,
      ),

    quantity:
      Math.floor(
        positiveNumber(
          order.quantity,
          0,
        ),
      ),

    price:
      positiveNumber(
        order.price,
        0,
      ),

    stopPrice:
      positiveNumber(
        order.stopPrice,
        0,
      ),

    sector:
      normalizeSector(
        order.sector,
      ),

    fee:
      positiveNumber(
        order.fee,
        0,
      ),

    confidence:
      clamp(
        finiteNumber(
          order.confidence,
          50,
        ),
        0,
        100,
      ),

    riskScore:
      clamp(
        finiteNumber(
          order.riskScore,
          50,
        ),
        0,
        100,
      ),
  };

  if (
    normalizedOrder.quantity <=
    0
  ) {
    throw new TypeError(
      "Order quantity must be greater than zero.",
    );
  }

  if (
    normalizedOrder.price <=
    0
  ) {
    throw new TypeError(
      "Order price must be greater than zero.",
    );
  }

  const maximumPositionPercent =
    positiveNumber(
      limits.maximumPositionPercent,
      25,
    );

  const maximumSectorPercent =
    positiveNumber(
      limits.maximumSectorPercent,
      40,
    );

  const maximumExposurePercent =
    positiveNumber(
      limits.maximumExposurePercent,
      90,
    );

  const maximumOrderRiskPercent =
    positiveNumber(
      limits.maximumOrderRiskPercent,
      2,
    );

  const minimumConfidence =
    positiveNumber(
      limits.minimumConfidence,
      50,
    );

  const maximumSignalRisk =
    positiveNumber(
      limits.maximumSignalRisk,
      80,
    );

  const projected =
    calculateProjectedOrder({
      order:
        normalizedOrder,

      portfolio:
        normalizedPortfolio,
    });

  const blockers = [];
  const warnings = [];

  if (
    normalizedOrder.side ===
      "BUY" &&
    projected.projectedCash <
      0
  ) {
    blockers.push(
      "INSUFFICIENT_CASH",
    );
  }

  if (
    normalizedOrder.side ===
      "SELL" &&
    projected.projectedQuantity <
      0
  ) {
    blockers.push(
      "INSUFFICIENT_POSITION",
    );
  }

  const projectedPositionPercent =
    normalizedPortfolio.equity <= 0
      ? 100
      : projected.projectedValue /
        normalizedPortfolio.equity *
        100;

  if (
    normalizedOrder.side ===
      "BUY" &&
    projectedPositionPercent >
      maximumPositionPercent
  ) {
    blockers.push(
      "MAXIMUM_POSITION_EXCEEDED",
    );
  }

  if (
    normalizedOrder.side ===
      "BUY" &&
    projected
      .projectedExposurePercent >
      maximumExposurePercent
  ) {
    blockers.push(
      "MAXIMUM_EXPOSURE_EXCEEDED",
    );
  }

  const currentSectorExposure =
    calculateSectorExposure(
      normalizedPortfolio,
    );

  const addedSectorPercent =
    normalizedPortfolio.equity <= 0
      ? 100
      : projected.orderValue /
        normalizedPortfolio.equity *
        100;

  const projectedSectorPercent =
    (
      currentSectorExposure[
        normalizedOrder.sector
      ] ??
      0
    ) +
    (
      normalizedOrder.side ===
      "BUY"
        ? addedSectorPercent
        : -addedSectorPercent
    );

  if (
    normalizedOrder.side ===
      "BUY" &&
    projectedSectorPercent >
      maximumSectorPercent
  ) {
    blockers.push(
      "MAXIMUM_SECTOR_EXPOSURE_EXCEEDED",
    );
  }

  let orderRiskAmount = 0;
  let orderRiskPercent = 0;

  if (
    normalizedOrder.stopPrice >
    0
  ) {
    orderRiskAmount =
      Math.abs(
        normalizedOrder.price -
        normalizedOrder.stopPrice,
      ) *
      normalizedOrder.quantity;

    orderRiskPercent =
      normalizedPortfolio.equity <= 0
        ? 100
        : orderRiskAmount /
          normalizedPortfolio.equity *
          100;

    if (
      orderRiskPercent >
      maximumOrderRiskPercent
    ) {
      blockers.push(
        "ORDER_RISK_LIMIT_EXCEEDED",
      );
    }
  }
  else if (
    normalizedOrder.side ===
    "BUY"
  ) {
    warnings.push(
      "STOP_PRICE_NOT_DEFINED",
    );
  }

  if (
    normalizedOrder.confidence <
    minimumConfidence
  ) {
    warnings.push(
      "LOW_SIGNAL_CONFIDENCE",
    );
  }

  if (
    normalizedOrder.riskScore >
    maximumSignalRisk
  ) {
    blockers.push(
      "SIGNAL_RISK_TOO_HIGH",
    );
  }

  const portfolioRisk =
    evaluatePortfolioRisk({
      portfolio:
        normalizedPortfolio,

      limits,

      timestamp:
        evaluatedAt,
    });

  if (
    portfolioRisk.status ===
    "BLOCKED"
  ) {
    blockers.push(
      "PORTFOLIO_RISK_BLOCKED",
    );
  }

  const combinedRiskScore =
    clamp(
      normalizedOrder.riskScore *
        0.35 +
      portfolioRisk.riskScore *
        0.45 +
      clamp(
        orderRiskPercent /
        Math.max(
          0.01,
          maximumOrderRiskPercent,
        ) *
        100,
        0,
        100,
      ) *
        0.2,
      0,
      100,
    );

  let decision =
    blockers.length > 0
      ? DECISIONS.BLOCK
      : combinedRiskScore >= 65 ||
          warnings.length >= 2
        ? DECISIONS.REDUCE
        : DECISIONS.ALLOW;

  let approvedQuantity =
    normalizedOrder.quantity;

  if (
    decision ===
    DECISIONS.REDUCE
  ) {
    approvedQuantity =
      Math.max(
        1,
        Math.floor(
          normalizedOrder.quantity *
          0.5,
        ),
      );
  }

  if (
    decision ===
    DECISIONS.BLOCK
  ) {
    approvedQuantity = 0;
  }

  return {
    version:
      RISK_MANAGEMENT_ENGINE_V3_VERSION,

    evaluatedAt,

    status:
      decision === DECISIONS.BLOCK
        ? "BLOCKED"
        : warnings.length > 0
          ? "WARNING"
          : "READY",

    decision,

    approvedQuantity,

    requestedQuantity:
      normalizedOrder.quantity,

    combinedRiskScore:
      round(
        combinedRiskScore,
      ),

    level:
      classifyRisk(
        combinedRiskScore,
      ),

    blockers:
      [...new Set(
        blockers,
      )],

    warnings:
      [...new Set(
        warnings,
      )],

    projected: {
      orderValue:
        round(
          projected.orderValue,
        ),

      projectedCash:
        round(
          projected.projectedCash,
        ),

      projectedPositionPercent:
        round(
          projectedPositionPercent,
        ),

      projectedSectorPercent:
        round(
          projectedSectorPercent,
        ),

      projectedExposurePercent:
        round(
          projected
            .projectedExposurePercent,
        ),

      orderRiskAmount:
        round(
          orderRiskAmount,
        ),

      orderRiskPercent:
        round(
          orderRiskPercent,
        ),
    },

    portfolioRisk,
  };
}

export class RiskManagementEngineV3 {
  constructor({
    limits = {},
  } = {}) {
    this.limits = {
      maximumExposurePercent:
        90,

      maximumDrawdownPercent:
        15,

      maximumDailyLossPercent:
        3,

      maximumPositionPercent:
        25,

      maximumSectorPercent:
        40,

      maximumPortfolioBeta:
        1.5,

      maximumPortfolioVolatility:
        35,

      maximumOrderRiskPercent:
        2,

      minimumConfidence:
        50,

      maximumSignalRisk:
        80,

      ...limits,
    };

    this.history = [];
    this.killSwitch = false;
    this.killSwitchReason = null;
  }

  activateKillSwitch(
    reason =
      "MANUAL_KILL_SWITCH",
  ) {
    this.killSwitch = true;

    this.killSwitchReason =
      String(
        reason,
      );

    return this.getState();
  }

  deactivateKillSwitch() {
    this.killSwitch = false;
    this.killSwitchReason = null;

    return this.getState();
  }

  evaluatePortfolio(input = {}) {
    const result =
      evaluatePortfolioRisk({
        ...input,

        limits: {
          ...this.limits,
          ...input.limits,
        },
      });

    const finalResult =
      this.killSwitch
        ? {
            ...result,

            status:
              "BLOCKED",

            decision:
              DECISIONS.BLOCK,

            positionMultiplier:
              0,

            blockers: [
              ...new Set([
                ...result.blockers,
                "KILL_SWITCH_ACTIVE",
              ]),
            ],
          }
        : result;

    this.history.push(
      clone(
        finalResult,
      ),
    );

    return clone(
      finalResult,
    );
  }

  evaluateOrder(input = {}) {
    const result =
      evaluateOrderRisk({
        ...input,

        limits: {
          ...this.limits,
          ...input.limits,
        },
      });

    const finalResult =
      this.killSwitch
        ? {
            ...result,

            status:
              "BLOCKED",

            decision:
              DECISIONS.BLOCK,

            approvedQuantity:
              0,

            blockers: [
              ...new Set([
                ...result.blockers,
                "KILL_SWITCH_ACTIVE",
              ]),
            ],
          }
        : result;

    this.history.push(
      clone(
        finalResult,
      ),
    );

    return clone(
      finalResult,
    );
  }

  calculatePositionSize(
    input = {},
  ) {
    return calculatePositionSize({
      maximumPositionPercent:
        this.limits
          .maximumPositionPercent,

      ...input,
    });
  }

  getHistory() {
    return clone(
      this.history,
    );
  }

  latest() {
    return clone(
      this.history.at(-1) ??
      null,
    );
  }

  getState() {
    return {
      version:
        RISK_MANAGEMENT_ENGINE_V3_VERSION,

      killSwitch:
        this.killSwitch,

      killSwitchReason:
        this.killSwitchReason,

      limits:
        clone(
          this.limits,
        ),

      historyCount:
        this.history.length,
    };
  }

  reset() {
    this.history = [];
    this.killSwitch = false;
    this.killSwitchReason = null;

    return this.getState();
  }
}

export const riskManagementEngineV3 =
  new RiskManagementEngineV3();

export default RiskManagementEngineV3;