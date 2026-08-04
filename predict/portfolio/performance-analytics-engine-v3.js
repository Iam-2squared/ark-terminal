export const PERFORMANCE_ANALYTICS_ENGINE_V3_VERSION =
  "performance-analytics-engine-v3";

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
  digits = 6,
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
      "Performance timestamp is invalid.",
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
      "UNKNOWN",
    )
      .trim()
      .toUpperCase();

  return symbol || "UNKNOWN";
}

function normalizeStrategy(value) {
  const strategy =
    String(
      value ??
      "UNSPECIFIED",
    )
      .trim()
      .toUpperCase();

  return strategy || "UNSPECIFIED";
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

function downsideDeviation(values) {
  if (
    !Array.isArray(values) ||
    values.length === 0
  ) {
    return 0;
  }

  const negativeValues =
    values.filter(
      (
        value,
      ) =>
        value < 0,
    );

  if (
    negativeValues.length === 0
  ) {
    return 0;
  }

  return Math.sqrt(
    negativeValues.reduce(
      (
        total,
        value,
      ) =>
        total +
        value ** 2,
      0,
    ) /
    negativeValues.length,
  );
}

function calculateReturns(
  equityCurve,
) {
  const returns = [];

  for (
    let index = 1;
    index < equityCurve.length;
    index += 1
  ) {
    const previous =
      equityCurve[
        index -
        1
      ].equity;

    const current =
      equityCurve[
        index
      ].equity;

    if (previous === 0) {
      returns.push(0);
      continue;
    }

    returns.push(
      (
        current -
        previous
      ) /
      previous,
    );
  }

  return returns;
}

function calculateDrawdown(
  equityCurve,
) {
  let peak = 0;
  let maximumDrawdown = 0;
  let maximumDrawdownAmount = 0;
  let currentDrawdown = 0;

  const series =
    equityCurve.map(
      (
        point,
      ) => {
        peak =
          Math.max(
            peak,
            point.equity,
          );

        const drawdownAmount =
          peak -
          point.equity;

        const drawdownPercent =
          peak <= 0
            ? 0
            : drawdownAmount /
              peak *
              100;

        currentDrawdown =
          drawdownPercent;

        if (
          drawdownPercent >
          maximumDrawdown
        ) {
          maximumDrawdown =
            drawdownPercent;

          maximumDrawdownAmount =
            drawdownAmount;
        }

        return {
          timestamp:
            point.timestamp,

          equity:
            point.equity,

          peak:
            round(
              peak,
            ),

          drawdownAmount:
            round(
              drawdownAmount,
            ),

          drawdownPercent:
            round(
              drawdownPercent,
            ),
        };
      },
    );

  return {
    currentDrawdownPercent:
      round(
        currentDrawdown,
      ),

    maximumDrawdownPercent:
      round(
        maximumDrawdown,
      ),

    maximumDrawdownAmount:
      round(
        maximumDrawdownAmount,
      ),

    series,
  };
}

function calculateCagr(
  firstEquity,
  lastEquity,
  firstTimestamp,
  lastTimestamp,
) {
  if (
    firstEquity <= 0 ||
    lastEquity <= 0
  ) {
    return 0;
  }

  const elapsedMilliseconds =
    Date.parse(
      lastTimestamp,
    ) -
    Date.parse(
      firstTimestamp,
    );

  const years =
    elapsedMilliseconds /
    (
      365.25 *
      24 *
      60 *
      60 *
      1000
    );

  if (years <= 0) {
    return 0;
  }

  return (
    (
      lastEquity /
      firstEquity
    ) **
      (
        1 /
        years
      ) -
    1
  ) *
  100;
}

function calculateSharpe(
  returns,
  riskFreeRate,
  periodsPerYear,
) {
  if (
    returns.length < 2
  ) {
    return 0;
  }

  const periodicRiskFreeRate =
    riskFreeRate /
    periodsPerYear;

  const excessReturns =
    returns.map(
      (
        value,
      ) =>
        value -
        periodicRiskFreeRate,
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
    Math.sqrt(
      periodsPerYear,
    )
  );
}

function calculateSortino(
  returns,
  riskFreeRate,
  periodsPerYear,
) {
  if (
    returns.length < 2
  ) {
    return 0;
  }

  const periodicRiskFreeRate =
    riskFreeRate /
    periodsPerYear;

  const excessReturns =
    returns.map(
      (
        value,
      ) =>
        value -
        periodicRiskFreeRate,
    );

  const deviation =
    downsideDeviation(
      excessReturns,
    );

  if (deviation === 0) {
    return average(
      excessReturns,
    ) > 0
      ? Infinity
      : 0;
  }

  return (
    average(
      excessReturns,
    ) /
    deviation *
    Math.sqrt(
      periodsPerYear,
    )
  );
}

function calculateProfitFactor(
  trades,
) {
  const grossProfit =
    trades
      .filter(
        (
          trade,
        ) =>
          trade.pnl >
          0,
      )
      .reduce(
        (
          total,
          trade,
        ) =>
          total +
          trade.pnl,
        0,
      );

  const grossLoss =
    Math.abs(
      trades
        .filter(
          (
            trade,
          ) =>
            trade.pnl <
            0,
        )
        .reduce(
          (
            total,
            trade,
          ) =>
            total +
            trade.pnl,
          0,
        ),
    );

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

function calculateStreaks(
  trades,
) {
  let currentWinStreak = 0;
  let currentLossStreak = 0;
  let maximumWinStreak = 0;
  let maximumLossStreak = 0;

  for (
    const trade of
    trades
  ) {
    if (trade.pnl > 0) {
      currentWinStreak += 1;
      currentLossStreak = 0;

      maximumWinStreak =
        Math.max(
          maximumWinStreak,
          currentWinStreak,
        );
    }
    else if (trade.pnl < 0) {
      currentLossStreak += 1;
      currentWinStreak = 0;

      maximumLossStreak =
        Math.max(
          maximumLossStreak,
          currentLossStreak,
        );
    }
    else {
      currentWinStreak = 0;
      currentLossStreak = 0;
    }
  }

  return {
    maximumWinStreak,
    maximumLossStreak,
  };
}

function groupTrades(
  trades,
  keyResolver,
) {
  const groups = {};

  for (
    const trade of
    trades
  ) {
    const key =
      keyResolver(
        trade,
      );

    if (!groups[key]) {
      groups[key] = [];
    }

    groups[key].push(
      trade,
    );
  }

  return Object.fromEntries(
    Object.entries(
      groups,
    ).map(
      (
        [
          key,
          values,
        ],
      ) => [
        key,
        calculateTradeStatistics(
          values,
        ),
      ],
    ),
  );
}

function calculateTradeStatistics(
  trades,
) {
  const wins =
    trades.filter(
      (
        trade,
      ) =>
        trade.pnl >
        0,
    );

  const losses =
    trades.filter(
      (
        trade,
      ) =>
        trade.pnl <
        0,
    );

  const grossProfit =
    wins.reduce(
      (
        total,
        trade,
      ) =>
        total +
        trade.pnl,
      0,
    );

  const grossLoss =
    losses.reduce(
      (
        total,
        trade,
      ) =>
        total +
        trade.pnl,
      0,
    );

  const totalPnl =
    trades.reduce(
      (
        total,
        trade,
      ) =>
        total +
        trade.pnl,
      0,
    );

  const averageWin =
    wins.length === 0
      ? 0
      : grossProfit /
        wins.length;

  const averageLoss =
    losses.length === 0
      ? 0
      : Math.abs(
          grossLoss /
          losses.length,
        );

  const winRate =
    trades.length === 0
      ? 0
      : wins.length /
        trades.length *
        100;

  const expectancy =
    trades.length === 0
      ? 0
      : totalPnl /
        trades.length;

  const streaks =
    calculateStreaks(
      trades,
    );

  const profitFactor =
    calculateProfitFactor(
      trades,
    );

  return {
    tradeCount:
      trades.length,

    winCount:
      wins.length,

    lossCount:
      losses.length,

    winRate:
      round(
        winRate,
      ),

    grossProfit:
      round(
        grossProfit,
      ),

    grossLoss:
      round(
        grossLoss,
      ),

    netPnl:
      round(
        totalPnl,
      ),

    averageWin:
      round(
        averageWin,
      ),

    averageLoss:
      round(
        averageLoss,
      ),

    expectancy:
      round(
        expectancy,
      ),

    profitFactor:
      profitFactor ===
      Infinity
        ? "Infinity"
        : round(
            profitFactor,
          ),

    maximumWinStreak:
      streaks
        .maximumWinStreak,

    maximumLossStreak:
      streaks
        .maximumLossStreak,
  };
}

function normalizeTrade(
  trade = {},
) {
  return {
    id:
      String(
        trade.id ??
        "",
      ),

    symbol:
      normalizeSymbol(
        trade.symbol,
      ),

    strategy:
      normalizeStrategy(
        trade.strategy,
      ),

    pnl:
      finiteNumber(
        trade.pnl,
        0,
      ),

    returnPercent:
      finiteNumber(
        trade.returnPercent,
        0,
      ),

    entryTimestamp:
      normalizeTimestamp(
        trade.entryTimestamp ??
        trade.timestamp,
      ),

    exitTimestamp:
      normalizeTimestamp(
        trade.exitTimestamp ??
        trade.timestamp,
      ),

    fees:
      positiveNumber(
        trade.fees,
        0,
      ),

    metadata:
      clone(
        trade.metadata ??
        {},
      ),
  };
}

function normalizeEquityPoint(
  point = {},
) {
  const equity =
    positiveNumber(
      point.equity,
      0,
    );

  if (equity <= 0) {
    throw new TypeError(
      "Equity must be greater than zero.",
    );
  }

  return {
    timestamp:
      normalizeTimestamp(
        point.timestamp,
      ),

    equity,
  };
}

function calculatePeriodReturns(
  equityCurve,
  period,
) {
  const groups = {};

  for (
    const point of
    equityCurve
  ) {
    const date =
      new Date(
        point.timestamp,
      );

    let key;

    if (period === "MONTH") {
      key =
        `${date.getUTCFullYear()}-${String(
          date.getUTCMonth() + 1,
        ).padStart(2, "0")}`;
    }
    else if (period === "WEEK") {
      const firstDay =
        new Date(
          Date.UTC(
            date.getUTCFullYear(),
            0,
            1,
          ),
        );

      const dayOffset =
        Math.floor(
          (
            date -
            firstDay
          ) /
          86400000,
        );

      const week =
        Math.ceil(
          (
            dayOffset +
            firstDay.getUTCDay() +
            1
          ) /
          7,
        );

      key =
        `${date.getUTCFullYear()}-W${String(
          week,
        ).padStart(2, "0")}`;
    }
    else {
      key =
        point.timestamp.slice(
          0,
          10,
        );
    }

    if (!groups[key]) {
      groups[key] = [];
    }

    groups[key].push(
      point,
    );
  }

  return Object.fromEntries(
    Object.entries(
      groups,
    ).map(
      (
        [
          key,
          points,
        ],
      ) => {
        const first =
          points[0].equity;

        const last =
          points.at(-1).equity;

        const returnPercent =
          first === 0
            ? 0
            : (
                last -
                first
              ) /
              first *
              100;

        return [
          key,
          round(
            returnPercent,
          ),
        ];
      },
    ),
  );
}

export function analyzePerformance({
  equityCurve = [],
  trades = [],
  benchmarkCurve = [],
  riskFreeRate = 0,
  periodsPerYear = 252,
  timestamp =
    new Date().toISOString(),
} = {}) {
  const evaluatedAt =
    normalizeTimestamp(
      timestamp,
    );

  const normalizedEquity =
    equityCurve
      .map(
        normalizeEquityPoint,
      )
      .sort(
        (
          a,
          b,
        ) =>
          Date.parse(
            a.timestamp,
          ) -
          Date.parse(
            b.timestamp,
          ),
      );

  if (
    normalizedEquity.length === 0
  ) {
    throw new TypeError(
      "Equity curve is required.",
    );
  }

  const normalizedTrades =
    trades
      .map(
        normalizeTrade,
      )
      .sort(
        (
          a,
          b,
        ) =>
          Date.parse(
            a.exitTimestamp,
          ) -
          Date.parse(
            b.exitTimestamp,
          ),
      );

  const returns =
    calculateReturns(
      normalizedEquity,
    );

  const drawdown =
    calculateDrawdown(
      normalizedEquity,
    );

  const initialEquity =
    normalizedEquity[0]
      .equity;

  const finalEquity =
    normalizedEquity.at(-1)
      .equity;

  const totalReturnPercent =
    (
      finalEquity -
      initialEquity
    ) /
    initialEquity *
    100;

  const cagr =
    calculateCagr(
      initialEquity,
      finalEquity,
      normalizedEquity[0]
        .timestamp,
      normalizedEquity.at(-1)
        .timestamp,
    );

  const sharpeRatio =
    calculateSharpe(
      returns,
      finiteNumber(
        riskFreeRate,
        0,
      ),
      positiveNumber(
        periodsPerYear,
        252,
      ),
    );

  const sortinoRatio =
    calculateSortino(
      returns,
      finiteNumber(
        riskFreeRate,
        0,
      ),
      positiveNumber(
        periodsPerYear,
        252,
      ),
    );

  const annualizedVolatility =
    standardDeviation(
      returns,
    ) *
    Math.sqrt(
      positiveNumber(
        periodsPerYear,
        252,
      ),
    ) *
    100;

  const calmarRatio =
    drawdown
      .maximumDrawdownPercent ===
    0
      ? cagr > 0
        ? Infinity
        : 0
      : cagr /
        drawdown
          .maximumDrawdownPercent;

  const tradeStatistics =
    calculateTradeStatistics(
      normalizedTrades,
    );

  const normalizedBenchmark =
    benchmarkCurve
      .map(
        normalizeEquityPoint,
      )
      .sort(
        (
          a,
          b,
        ) =>
          Date.parse(
            a.timestamp,
          ) -
          Date.parse(
            b.timestamp,
          ),
      );

  let benchmark = null;

  if (
    normalizedBenchmark.length >
    0
  ) {
    const benchmarkInitial =
      normalizedBenchmark[0]
        .equity;

    const benchmarkFinal =
      normalizedBenchmark.at(-1)
        .equity;

    const benchmarkReturnPercent =
      (
        benchmarkFinal -
        benchmarkInitial
      ) /
      benchmarkInitial *
      100;

    benchmark = {
      totalReturnPercent:
        round(
          benchmarkReturnPercent,
        ),

      excessReturnPercent:
        round(
          totalReturnPercent -
          benchmarkReturnPercent,
        ),

      outperformed:
        totalReturnPercent >
        benchmarkReturnPercent,
    };
  }

  return {
    version:
      PERFORMANCE_ANALYTICS_ENGINE_V3_VERSION,

    evaluatedAt,

    summary: {
      initialEquity:
        round(
          initialEquity,
        ),

      finalEquity:
        round(
          finalEquity,
        ),

      netProfit:
        round(
          finalEquity -
          initialEquity,
        ),

      totalReturnPercent:
        round(
          totalReturnPercent,
        ),

      cagrPercent:
        round(
          cagr,
        ),

      annualizedVolatilityPercent:
        round(
          annualizedVolatility,
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

      calmarRatio:
        calmarRatio ===
        Infinity
          ? "Infinity"
          : round(
              calmarRatio,
            ),

      maximumDrawdownPercent:
        drawdown
          .maximumDrawdownPercent,

      maximumDrawdownAmount:
        drawdown
          .maximumDrawdownAmount,
    },

    trades:
      tradeStatistics,

    periodReturns: {
      daily:
        calculatePeriodReturns(
          normalizedEquity,
          "DAY",
        ),

      weekly:
        calculatePeriodReturns(
          normalizedEquity,
          "WEEK",
        ),

      monthly:
        calculatePeriodReturns(
          normalizedEquity,
          "MONTH",
        ),
    },

    breakdown: {
      bySymbol:
        groupTrades(
          normalizedTrades,
          (
            trade,
          ) =>
            trade.symbol,
        ),

      byStrategy:
        groupTrades(
          normalizedTrades,
          (
            trade,
          ) =>
            trade.strategy,
        ),

      byMonth:
        groupTrades(
          normalizedTrades,
          (
            trade,
          ) =>
            trade.exitTimestamp.slice(
              0,
              7,
            ),
        ),
    },

    benchmark,

    equityCurve:
      clone(
        normalizedEquity,
      ),

    returns:
      returns.map(
        (
          value,
        ) =>
          round(
            value,
            8,
          ),
      ),

    drawdown:
      clone(
        drawdown,
      ),
  };
}

export class PerformanceAnalyticsEngineV3 {
  constructor({
    riskFreeRate = 0,
    periodsPerYear = 252,
  } = {}) {
    this.riskFreeRate =
      finiteNumber(
        riskFreeRate,
        0,
      );

    this.periodsPerYear =
      positiveNumber(
        periodsPerYear,
        252,
      );

    this.equityCurve = [];
    this.trades = [];
    this.benchmarkCurve = [];
    this.history = [];
  }

  addEquityPoint(point) {
    const normalized =
      normalizeEquityPoint(
        point,
      );

    this.equityCurve.push(
      normalized,
    );

    this.equityCurve.sort(
      (
        a,
        b,
      ) =>
        Date.parse(
          a.timestamp,
        ) -
        Date.parse(
          b.timestamp,
        ),
    );

    return clone(
      normalized,
    );
  }

  addTrade(trade) {
    const normalized =
      normalizeTrade(
        trade,
      );

    this.trades.push(
      normalized,
    );

    this.trades.sort(
      (
        a,
        b,
      ) =>
        Date.parse(
          a.exitTimestamp,
        ) -
        Date.parse(
          b.exitTimestamp,
        ),
    );

    return clone(
      normalized,
    );
  }

  addBenchmarkPoint(point) {
    const normalized =
      normalizeEquityPoint(
        point,
      );

    this.benchmarkCurve.push(
      normalized,
    );

    this.benchmarkCurve.sort(
      (
        a,
        b,
      ) =>
        Date.parse(
          a.timestamp,
        ) -
        Date.parse(
          b.timestamp,
        ),
    );

    return clone(
      normalized,
    );
  }

  analyze({
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const result =
      analyzePerformance({
        equityCurve:
          this.equityCurve,

        trades:
          this.trades,

        benchmarkCurve:
          this.benchmarkCurve,

        riskFreeRate:
          this.riskFreeRate,

        periodsPerYear:
          this.periodsPerYear,

        timestamp,
      });

    this.history.push(
      clone(
        result,
      ),
    );

    return clone(
      result,
    );
  }

  snapshot() {
    return {
      version:
        PERFORMANCE_ANALYTICS_ENGINE_V3_VERSION,

      riskFreeRate:
        this.riskFreeRate,

      periodsPerYear:
        this.periodsPerYear,

      equityCurve:
        clone(
          this.equityCurve,
        ),

      trades:
        clone(
          this.trades,
        ),

      benchmarkCurve:
        clone(
          this.benchmarkCurve,
        ),

      history:
        clone(
          this.history,
        ),
    };
  }

  restore(snapshot) {
    if (
      !snapshot ||
      typeof snapshot !==
        "object"
    ) {
      throw new TypeError(
        "Performance snapshot is required.",
      );
    }

    this.riskFreeRate =
      finiteNumber(
        snapshot.riskFreeRate,
        0,
      );

    this.periodsPerYear =
      positiveNumber(
        snapshot.periodsPerYear,
        252,
      );

    this.equityCurve =
      clone(
        snapshot.equityCurve ??
        [],
      );

    this.trades =
      clone(
        snapshot.trades ??
        [],
      );

    this.benchmarkCurve =
      clone(
        snapshot.benchmarkCurve ??
        [],
      );

    this.history =
      clone(
        snapshot.history ??
        [],
      );

    return this.snapshot();
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

  reset() {
    this.equityCurve = [];
    this.trades = [];
    this.benchmarkCurve = [];
    this.history = [];

    return this.snapshot();
  }
}

export const performanceAnalyticsEngineV3 =
  new PerformanceAnalyticsEngineV3();

export default PerformanceAnalyticsEngineV3;