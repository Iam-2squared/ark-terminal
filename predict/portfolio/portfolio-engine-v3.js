export const PORTFOLIO_ENGINE_V3_VERSION =
  "portfolio-engine-v3";

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
      "Portfolio timestamp is invalid.",
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
      "Portfolio symbol is required.",
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

function average(values) {
  if (
    !Array.isArray(values) ||
    values.length === 0
  ) {
    return 0;
  }

  return (
    values.reduce(
      (
        total,
        value,
      ) =>
        total +
        value,
      0,
    ) /
    values.length
  );
}

function standardDeviation(values) {
  if (
    !Array.isArray(values) ||
    values.length < 2
  ) {
    return 0;
  }

  const mean =
    average(
      values,
    );

  const variance =
    values.reduce(
      (
        total,
        value,
      ) =>
        total +
        (
          value -
          mean
        ) ** 2,
      0,
    ) /
    (
      values.length -
      1
    );

  return Math.sqrt(
    variance,
  );
}

function calculateMaximumDrawdown(
  equityHistory,
) {
  if (
    !Array.isArray(
      equityHistory,
    ) ||
    equityHistory.length === 0
  ) {
    return 0;
  }

  let peak =
    equityHistory[0].equity;

  let maximumDrawdown = 0;

  for (
    const entry of
    equityHistory
  ) {
    peak =
      Math.max(
        peak,
        entry.equity,
      );

    if (peak <= 0) {
      continue;
    }

    const drawdown =
      (
        peak -
        entry.equity
      ) /
      peak *
      100;

    maximumDrawdown =
      Math.max(
        maximumDrawdown,
        drawdown,
      );
  }

  return maximumDrawdown;
}

function calculateProfitFactor(
  closedTrades,
) {
  let grossProfit = 0;
  let grossLoss = 0;

  for (
    const trade of
    closedTrades
  ) {
    if (
      trade.realizedPnl >
      0
    ) {
      grossProfit +=
        trade.realizedPnl;
    }

    if (
      trade.realizedPnl <
      0
    ) {
      grossLoss +=
        Math.abs(
          trade.realizedPnl,
        );
    }
  }

  if (grossLoss === 0) {
    return grossProfit > 0
      ? Infinity
      : 0;
  }

  return (
    grossProfit /
    grossLoss
  );
}

function calculateSharpeRatio(
  returns,
  riskFreeRate = 0,
) {
  if (
    !Array.isArray(returns) ||
    returns.length < 2
  ) {
    return 0;
  }

  const excessReturns =
    returns.map(
      (
        value,
      ) =>
        value -
        riskFreeRate,
    );

  const deviation =
    standardDeviation(
      excessReturns,
    );

  if (deviation === 0) {
    return 0;
  }

  return (
    average(
      excessReturns,
    ) /
    deviation *
    Math.sqrt(252)
  );
}

function calculateSortinoRatio(
  returns,
  riskFreeRate = 0,
) {
  if (
    !Array.isArray(returns) ||
    returns.length < 2
  ) {
    return 0;
  }

  const excessReturns =
    returns.map(
      (
        value,
      ) =>
        value -
        riskFreeRate,
    );

  const downside =
    excessReturns.filter(
      (
        value,
      ) =>
        value < 0,
    );

  if (
    downside.length === 0
  ) {
    return average(
      excessReturns,
    ) > 0
      ? Infinity
      : 0;
  }

  const downsideDeviation =
    Math.sqrt(
      downside.reduce(
        (
          total,
          value,
        ) =>
          total +
          value ** 2,
        0,
      ) /
      downside.length,
    );

  if (
    downsideDeviation === 0
  ) {
    return 0;
  }

  return (
    average(
      excessReturns,
    ) /
    downsideDeviation *
    Math.sqrt(252)
  );
}

function normalizePosition(
  position = {},
) {
  return {
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

    realizedPnl:
      finiteNumber(
        position.realizedPnl,
        0,
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
  };
}

export class PortfolioEngineV3 {
  constructor({
    initialCash = 1000000,
    maximumPositionPercent = 25,
    maximumSectorPercent = 40,
    riskFreeRate = 0,
    timestamp =
      new Date().toISOString(),
  } = {}) {
    this.initialCash =
      positiveNumber(
        initialCash,
        1000000,
      );

    if (
      this.initialCash <= 0
    ) {
      throw new TypeError(
        "Initial cash must be greater than zero.",
      );
    }

    this.cash =
      this.initialCash;

    this.maximumPositionPercent =
      positiveNumber(
        maximumPositionPercent,
        25,
      );

    this.maximumSectorPercent =
      positiveNumber(
        maximumSectorPercent,
        40,
      );

    this.riskFreeRate =
      finiteNumber(
        riskFreeRate,
        0,
      );

    this.positions =
      new Map();

    this.closedTrades = [];
    this.equityHistory = [];
    this.returnHistory = [];

    this.createdAt =
      normalizeTimestamp(
        timestamp,
      );

    this.updatedAt =
      this.createdAt;

    this.recordEquity({
      timestamp:
        this.createdAt,
    });
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

        sector:
          "UNKNOWN",

        quantity:
          0,

        averagePrice:
          0,

        marketPrice:
          0,

        realizedPnl:
          0,

        beta:
          1,

        volatility:
          0,
      },
    );
  }

  getPositions() {
    return clone(
      [...this.positions.values()],
    );
  }

  calculateMarketValue() {
    return [...this.positions.values()]
      .reduce(
        (
          total,
          position,
        ) =>
          total +
          position.quantity *
          position.marketPrice,
        0,
      );
  }

  calculateUnrealizedPnl() {
    return [...this.positions.values()]
      .reduce(
        (
          total,
          position,
        ) =>
          total +
          position.quantity *
          (
            position.marketPrice -
            position.averagePrice
          ),
        0,
      );
  }

  calculateRealizedPnl() {
    return [...this.positions.values()]
      .reduce(
        (
          total,
          position,
        ) =>
          total +
          position.realizedPnl,
        0,
      );
  }

  calculateEquity() {
    return (
      this.cash +
      this.calculateMarketValue()
    );
  }

  calculateBuyingPower() {
    return Math.max(
      0,
      this.cash,
    );
  }

  calculateExposure() {
    const equity =
      this.calculateEquity();

    const marketValue =
      this.calculateMarketValue();

    return equity <= 0
      ? 0
      : marketValue /
        equity *
        100;
  }

  calculateSectorAllocation() {
    const equity =
      this.calculateEquity();

    const allocation = {};

    for (
      const position of
      this.positions.values()
    ) {
      const value =
        position.quantity *
        position.marketPrice;

      allocation[
        position.sector
      ] =
        (
          allocation[
            position.sector
          ] ??
          0
        ) +
        value;
    }

    for (
      const sector of
      Object.keys(
        allocation,
      )
    ) {
      allocation[
        sector
      ] =
        equity <= 0
          ? 0
          : round(
              allocation[
                sector
              ] /
              equity *
              100,
            );
    }

    return allocation;
  }

  validatePositionLimit({
    symbol,
    quantity,
    price,
  }) {
    const equity =
      this.calculateEquity();

    const existing =
      this.getPosition(
        symbol,
      );

    const projectedValue =
      (
        existing.quantity +
        quantity
      ) *
      price;

    const maximumValue =
      equity *
      this.maximumPositionPercent /
      100;

    if (
      projectedValue >
      maximumValue
    ) {
      throw new Error(
        "Maximum portfolio position exceeded.",
      );
    }
  }

  validateSectorLimit({
    sector,
    addedValue,
  }) {
    const equity =
      this.calculateEquity();

    const allocation =
      this.calculateSectorAllocation();

    const currentPercent =
      finiteNumber(
        allocation[
          normalizeSector(
            sector,
          )
        ],
        0,
      );

    const addedPercent =
      equity <= 0
        ? 100
        : addedValue /
          equity *
          100;

    if (
      currentPercent +
      addedPercent >
      this.maximumSectorPercent
    ) {
      throw new Error(
        "Maximum sector exposure exceeded.",
      );
    }
  }

  buy({
    symbol,
    quantity,
    price,
    sector = "UNKNOWN",
    beta = 1,
    volatility = 0,
    fee = 0,
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const normalizedSymbol =
      normalizeSymbol(
        symbol,
      );

    const normalizedSector =
      normalizeSector(
        sector,
      );

    const normalizedQuantity =
      Math.floor(
        positiveNumber(
          quantity,
          0,
        ),
      );

    const normalizedPrice =
      positiveNumber(
        price,
        0,
      );

    const normalizedFee =
      positiveNumber(
        fee,
        0,
      );

    if (
      normalizedQuantity <= 0
    ) {
      throw new TypeError(
        "Buy quantity must be greater than zero.",
      );
    }

    if (
      normalizedPrice <= 0
    ) {
      throw new TypeError(
        "Buy price must be greater than zero.",
      );
    }

    const grossValue =
      normalizedQuantity *
      normalizedPrice;

    const totalCost =
      grossValue +
      normalizedFee;

    if (
      totalCost >
      this.cash
    ) {
      throw new Error(
        "Insufficient portfolio cash.",
      );
    }

    this.validatePositionLimit({
      symbol:
        normalizedSymbol,

      quantity:
        normalizedQuantity,

      price:
        normalizedPrice,
    });

    this.validateSectorLimit({
      sector:
        normalizedSector,

      addedValue:
        grossValue,
    });

    const current =
      this.getPosition(
        normalizedSymbol,
      );

    const previousCost =
      current.quantity *
      current.averagePrice;

    const newQuantity =
      current.quantity +
      normalizedQuantity;

    const next = {
      ...current,

      symbol:
        normalizedSymbol,

      sector:
        normalizedSector,

      quantity:
        newQuantity,

      averagePrice:
        (
          previousCost +
          grossValue
        ) /
        newQuantity,

      marketPrice:
        normalizedPrice,

      beta:
        finiteNumber(
          beta,
          1,
        ),

      volatility:
        positiveNumber(
          volatility,
          0,
        ),
    };

    this.cash -=
      totalCost;

    this.positions.set(
      normalizedSymbol,
      next,
    );

    this.updatedAt =
      normalizeTimestamp(
        timestamp,
      );

    this.recordEquity({
      timestamp:
        this.updatedAt,
    });

    return {
      position:
        clone(next),

      cash:
        round(
          this.cash,
        ),

      equity:
        round(
          this.calculateEquity(),
        ),
    };
  }

  sell({
    symbol,
    quantity,
    price,
    fee = 0,
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const normalizedSymbol =
      normalizeSymbol(
        symbol,
      );

    const normalizedQuantity =
      Math.floor(
        positiveNumber(
          quantity,
          0,
        ),
      );

    const normalizedPrice =
      positiveNumber(
        price,
        0,
      );

    const normalizedFee =
      positiveNumber(
        fee,
        0,
      );

    if (
      normalizedQuantity <= 0
    ) {
      throw new TypeError(
        "Sell quantity must be greater than zero.",
      );
    }

    if (
      normalizedPrice <= 0
    ) {
      throw new TypeError(
        "Sell price must be greater than zero.",
      );
    }

    const current =
      this.getPosition(
        normalizedSymbol,
      );

    if (
      normalizedQuantity >
      current.quantity
    ) {
      throw new Error(
        "Insufficient portfolio position.",
      );
    }

    const grossValue =
      normalizedQuantity *
      normalizedPrice;

    const realizedPnl =
      normalizedQuantity *
      (
        normalizedPrice -
        current.averagePrice
      ) -
      normalizedFee;

    current.quantity -=
      normalizedQuantity;

    current.marketPrice =
      normalizedPrice;

    current.realizedPnl +=
      realizedPnl;

    if (
      current.quantity === 0
    ) {
      current.averagePrice =
        0;
    }

    this.cash +=
      grossValue -
      normalizedFee;

    this.positions.set(
      normalizedSymbol,
      current,
    );

    this.closedTrades.push({
      symbol:
        normalizedSymbol,

      quantity:
        normalizedQuantity,

      price:
        normalizedPrice,

      realizedPnl:
        round(
          realizedPnl,
        ),

      timestamp:
        normalizeTimestamp(
          timestamp,
        ),
    });

    this.updatedAt =
      normalizeTimestamp(
        timestamp,
      );

    this.recordEquity({
      timestamp:
        this.updatedAt,
    });

    return {
      position:
        clone(current),

      realizedPnl:
        round(
          realizedPnl,
        ),

      cash:
        round(
          this.cash,
        ),

      equity:
        round(
          this.calculateEquity(),
        ),
    };
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

    if (
      normalizedPrice <= 0
    ) {
      throw new TypeError(
        "Market price must be greater than zero.",
      );
    }

    const current =
      this.getPosition(
        normalizedSymbol,
      );

    if (
      !this.positions.has(
        normalizedSymbol,
      )
    ) {
      throw new Error(
        `Portfolio position not found: ${normalizedSymbol}`,
      );
    }

    current.marketPrice =
      normalizedPrice;

    this.positions.set(
      normalizedSymbol,
      current,
    );

    this.updatedAt =
      normalizeTimestamp(
        timestamp,
      );

    this.recordEquity({
      timestamp:
        this.updatedAt,
    });

    return clone(
      current,
    );
  }

  recordEquity({
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const normalizedTimestamp =
      normalizeTimestamp(
        timestamp,
      );

    const equity =
      this.calculateEquity();

    const previous =
      this.equityHistory.at(-1);

    const dailyReturn =
      previous &&
      previous.equity !== 0
        ? (
            equity -
            previous.equity
          ) /
          previous.equity
        : 0;

    this.equityHistory.push({
      timestamp:
        normalizedTimestamp,

      equity:
        round(
          equity,
        ),

      dailyReturn:
        round(
          dailyReturn,
          8,
        ),
    });

    if (previous) {
      this.returnHistory.push(
        dailyReturn,
      );
    }

    return clone(
      this.equityHistory.at(-1),
    );
  }

  calculateRisk() {
    const equity =
      this.calculateEquity();

    let weightedBeta = 0;
    let weightedVolatility = 0;
    let concentration = 0;

    for (
      const position of
      this.positions.values()
    ) {
      const value =
        position.quantity *
        position.marketPrice;

      const weight =
        equity <= 0
          ? 0
          : value /
            equity;

      weightedBeta +=
        weight *
        position.beta;

      weightedVolatility +=
        weight *
        position.volatility;

      concentration +=
        weight ** 2;
    }

    const diversificationScore =
      Math.max(
        0,
        Math.min(
          100,
          (
            1 -
            concentration
          ) *
          100,
        ),
      );

    return {
      exposurePercent:
        round(
          this.calculateExposure(),
        ),

      portfolioBeta:
        round(
          weightedBeta,
        ),

      portfolioVolatility:
        round(
          weightedVolatility,
        ),

      diversificationScore:
        round(
          diversificationScore,
        ),

      maximumDrawdownPercent:
        round(
          calculateMaximumDrawdown(
            this.equityHistory,
          ),
        ),

      sectorAllocation:
        this.calculateSectorAllocation(),
    };
  }

  calculatePerformance() {
    const equity =
      this.calculateEquity();

    const totalReturnPercent =
      (
        equity -
        this.initialCash
      ) /
      this.initialCash *
      100;

    const dailyReturnPercent =
      (
        this.equityHistory.at(-1)
          ?.dailyReturn ??
        0
      ) *
      100;

    const wins =
      this.closedTrades.filter(
        (
          trade,
        ) =>
          trade.realizedPnl >
          0,
      ).length;

    const winRate =
      this.closedTrades.length ===
      0
        ? 0
        : wins /
          this.closedTrades.length *
          100;

    const profitFactor =
      calculateProfitFactor(
        this.closedTrades,
      );

    const sharpeRatio =
      calculateSharpeRatio(
        this.returnHistory,
        this.riskFreeRate,
      );

    const sortinoRatio =
      calculateSortinoRatio(
        this.returnHistory,
        this.riskFreeRate,
      );

    return {
      totalReturnPercent:
        round(
          totalReturnPercent,
        ),

      dailyReturnPercent:
        round(
          dailyReturnPercent,
        ),

      winRate:
        round(
          winRate,
        ),

      profitFactor:
        profitFactor ===
        Infinity
          ? "Infinity"
          : round(
              profitFactor,
            ),

      sharpeRatio:
        round(
          sharpeRatio,
        ),

      sortinoRatio:
        sortinoRatio ===
        Infinity
          ? "Infinity"
          : round(
              sortinoRatio,
            ),

      closedTradeCount:
        this.closedTrades.length,
    };
  }

  calculateStatistics() {
    return {
      account: {
        initialCash:
          round(
            this.initialCash,
          ),

        cash:
          round(
            this.cash,
          ),

        buyingPower:
          round(
            this.calculateBuyingPower(),
          ),

        marketValue:
          round(
            this.calculateMarketValue(),
          ),

        equity:
          round(
            this.calculateEquity(),
          ),

        unrealizedPnl:
          round(
            this.calculateUnrealizedPnl(),
          ),

        realizedPnl:
          round(
            this.calculateRealizedPnl(),
          ),
      },

      performance:
        this.calculatePerformance(),

      risk:
        this.calculateRisk(),
    };
  }

  snapshot() {
    return {
      version:
        PORTFOLIO_ENGINE_V3_VERSION,

      initialCash:
        this.initialCash,

      cash:
        this.cash,

      maximumPositionPercent:
        this.maximumPositionPercent,

      maximumSectorPercent:
        this.maximumSectorPercent,

      riskFreeRate:
        this.riskFreeRate,

      positions:
        this.getPositions(),

      closedTrades:
        clone(
          this.closedTrades,
        ),

      equityHistory:
        clone(
          this.equityHistory,
        ),

      returnHistory:
        clone(
          this.returnHistory,
        ),

      createdAt:
        this.createdAt,

      updatedAt:
        this.updatedAt,
    };
  }

  restore(snapshot) {
    if (
      !snapshot ||
      typeof snapshot !==
        "object"
    ) {
      throw new TypeError(
        "Portfolio snapshot is required.",
      );
    }

    const initialCash =
      positiveNumber(
        snapshot.initialCash,
        0,
      );

    const cash =
      finiteNumber(
        snapshot.cash,
        -1,
      );

    if (
      initialCash <= 0 ||
      cash < 0
    ) {
      throw new TypeError(
        "Portfolio snapshot is invalid.",
      );
    }

    this.initialCash =
      initialCash;

    this.cash =
      cash;

    this.maximumPositionPercent =
      positiveNumber(
        snapshot.maximumPositionPercent,
        25,
      );

    this.maximumSectorPercent =
      positiveNumber(
        snapshot.maximumSectorPercent,
        40,
      );

    this.riskFreeRate =
      finiteNumber(
        snapshot.riskFreeRate,
        0,
      );

    this.positions.clear();

    for (
      const position of
      snapshot.positions ??
      []
    ) {
      const normalized =
        normalizePosition(
          position,
        );

      this.positions.set(
        normalized.symbol,
        normalized,
      );
    }

    this.closedTrades =
      clone(
        snapshot.closedTrades ??
        [],
      );

    this.equityHistory =
      clone(
        snapshot.equityHistory ??
        [],
      );

    this.returnHistory =
      clone(
        snapshot.returnHistory ??
        [],
      );

    this.createdAt =
      normalizeTimestamp(
        snapshot.createdAt,
      );

    this.updatedAt =
      normalizeTimestamp(
        snapshot.updatedAt,
      );

    return this.snapshot();
  }

  reset({
    timestamp =
      new Date().toISOString(),
  } = {}) {
    this.cash =
      this.initialCash;

    this.positions.clear();

    this.closedTrades = [];
    this.equityHistory = [];
    this.returnHistory = [];

    this.updatedAt =
      normalizeTimestamp(
        timestamp,
      );

    this.recordEquity({
      timestamp:
        this.updatedAt,
    });

    return this.snapshot();
  }
}

export function createPortfolio(
  options = {},
) {
  return new PortfolioEngineV3(
    options,
  );
}

export const portfolioEngineV3 =
  new PortfolioEngineV3();

export default PortfolioEngineV3;