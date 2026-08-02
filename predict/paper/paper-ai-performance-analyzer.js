export const PAPER_AI_PERFORMANCE_ANALYZER_VERSION =
  "paper-ai-performance-analyzer-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function numberOr(
  value,
  fallback = 0,
) {
  return finite(value)
    ? Number(value)
    : fallback;
}

function average(
  values = [],
) {
  const rows =
    values
      .filter(finite)
      .map(Number);

  if (!rows.length) {
    return null;
  }

  return (
    rows.reduce(
      (sum, value) =>
        sum + value,
      0,
    ) /
    rows.length
  );
}

function standardDeviation(
  values = [],
) {
  const rows =
    values
      .filter(finite)
      .map(Number);

  if (rows.length < 2) {
    return null;
  }

  const mean =
    average(rows);

  const variance =
    rows.reduce(
      (sum, value) =>
        sum +
        (
          value -
          mean
        ) ** 2,
      0,
    ) /
    rows.length;

  return Math.sqrt(
    variance,
  );
}

function calculateProfitFactor(
  trades = [],
) {
  const grossProfit =
    trades
      .filter(
        (trade) =>
          numberOr(
            trade.realizedPnl,
          ) > 0,
      )
      .reduce(
        (sum, trade) =>
          sum +
          numberOr(
            trade.realizedPnl,
          ),
        0,
      );

  const grossLoss =
    Math.abs(
      trades
        .filter(
          (trade) =>
            numberOr(
              trade.realizedPnl,
            ) < 0,
        )
        .reduce(
          (sum, trade) =>
            sum +
            numberOr(
              trade.realizedPnl,
            ),
          0,
        ),
    );

  if (grossLoss > 0) {
    return (
      grossProfit /
      grossLoss
    );
  }

  if (grossProfit > 0) {
    return Infinity;
  }

  return null;
}

function calculateMaximumDrawdown(
  equityHistory = [],
) {
  const points =
    equityHistory
      .map(
        (row) =>
          typeof row === "object"
            ? numberOr(
                row.equity,
                NaN,
              )
            : numberOr(
                row,
                NaN,
              ),
      )
      .filter(
        Number.isFinite,
      );

  if (!points.length) {
    return {
      amount: 0,
      percent: 0,
      peakEquity: null,
      troughEquity: null,
    };
  }

  let peak =
    points[0];

  let maximumAmount = 0;
  let maximumPercent = 0;
  let drawdownPeak =
    peak;
  let drawdownTrough =
    peak;

  for (
    const equity of
    points
  ) {
    if (equity > peak) {
      peak =
        equity;
    }

    const amount =
      peak -
      equity;

    const percent =
      peak > 0
        ? (
            amount /
            peak
          ) * 100
        : 0;

    if (
      percent >
      maximumPercent
    ) {
      maximumAmount =
        amount;

      maximumPercent =
        percent;

      drawdownPeak =
        peak;

      drawdownTrough =
        equity;
    }
  }

  return {
    amount:
      maximumAmount,

    percent:
      maximumPercent,

    peakEquity:
      drawdownPeak,

    troughEquity:
      drawdownTrough,
  };
}

function groupTradesBySymbol(
  trades = [],
) {
  const groups = {};

  for (
    const trade of
    trades
  ) {
    const symbol =
      String(
        trade.symbol ||
        "UNKNOWN",
      ).toUpperCase();

    if (!groups[symbol]) {
      groups[symbol] = [];
    }

    groups[symbol].push(
      trade,
    );
  }

  return groups;
}

function createSymbolStatistics(
  trades = [],
) {
  const groups =
    groupTradesBySymbol(
      trades,
    );

  return Object.entries(
    groups,
  )
    .map(
      ([
        symbol,
        rows,
      ]) => {
        const wins =
          rows.filter(
            (trade) =>
              numberOr(
                trade.realizedPnl,
              ) > 0,
          );

        const losses =
          rows.filter(
            (trade) =>
              numberOr(
                trade.realizedPnl,
              ) < 0,
          );

        const totalPnl =
          rows.reduce(
            (sum, trade) =>
              sum +
              numberOr(
                trade.realizedPnl,
              ),
            0,
          );

        return {
          symbol,

          tradeCount:
            rows.length,

          winCount:
            wins.length,

          lossCount:
            losses.length,

          winRate:
            rows.length > 0
              ? (
                  wins.length /
                  rows.length
                ) * 100
              : null,

          totalPnl,

          averagePnl:
            average(
              rows.map(
                (trade) =>
                  trade.realizedPnl,
              ),
            ),

          profitFactor:
            calculateProfitFactor(
              rows,
            ),
        };
      },
    )
    .sort(
      (a, b) =>
        b.totalPnl -
        a.totalPnl,
    );
}

function calculateSharpeLikeRatio({
  trades = [],
  initialCash = 0,
} = {}) {
  const capital =
    numberOr(
      initialCash,
      0,
    );

  if (
    capital <= 0 ||
    trades.length < 2
  ) {
    return null;
  }

  const returns =
    trades.map(
      (trade) =>
        numberOr(
          trade.realizedPnl,
        ) /
        capital,
    );

  const mean =
    average(
      returns,
    );

  const deviation =
    standardDeviation(
      returns,
    );

  if (
    !finite(deviation) ||
    deviation === 0
  ) {
    return null;
  }

  return (
    mean /
    deviation
  ) * Math.sqrt(
    returns.length,
  );
}

function calculatePerformanceScore({
  winRate,
  profitFactor,
  totalReturnPercent,
  maximumDrawdownPercent,
  sampleSize,
} = {}) {
  let score = 50;

  if (finite(winRate)) {
    score +=
      (
        Number(winRate) -
        50
      ) * 0.3;
  }

  if (finite(profitFactor)) {
    score +=
      Math.max(
        -15,
        Math.min(
          20,
          (
            Number(profitFactor) -
            1
          ) * 12,
        ),
      );
  }

  if (
    finite(
      totalReturnPercent,
    )
  ) {
    score +=
      Math.max(
        -15,
        Math.min(
          15,
          Number(
            totalReturnPercent,
          ) * 1.5,
        ),
      );
  }

  if (
    finite(
      maximumDrawdownPercent,
    )
  ) {
    score -=
      Math.min(
        20,
        Number(
          maximumDrawdownPercent,
        ) * 1.5,
      );
  }

  if (
    Number(sampleSize) < 10
  ) {
    score -= 10;
  }

  return Math.max(
    0,
    Math.min(
      100,
      Math.round(
        score * 100,
      ) / 100,
    ),
  );
}

export function analyzePaperAiPerformance({
  account = {},
  equityHistory = [],
} = {}) {
  const trades =
    Array.isArray(
      account.tradeHistory,
    )
      ? account.tradeHistory
          .filter(
            (trade) =>
              finite(
                trade.realizedPnl,
              ),
          )
      : [];

  const wins =
    trades.filter(
      (trade) =>
        numberOr(
          trade.realizedPnl,
        ) > 0,
    );

  const losses =
    trades.filter(
      (trade) =>
        numberOr(
          trade.realizedPnl,
        ) < 0,
    );

  const totalPnl =
    trades.reduce(
      (sum, trade) =>
        sum +
        numberOr(
          trade.realizedPnl,
        ),
      0,
    );

  const averageWin =
    average(
      wins.map(
        (trade) =>
          trade.realizedPnl,
      ),
    );

  const averageLoss =
    average(
      losses.map(
        (trade) =>
          trade.realizedPnl,
      ),
    );

  const profitFactor =
    calculateProfitFactor(
      trades,
    );

  const maximumDrawdown =
    calculateMaximumDrawdown(
      equityHistory,
    );

  const initialCash =
    numberOr(
      account.initialCash,
      0,
    );

  const totalReturnPercent =
    finite(
      account.totalReturnPercent,
    )
      ? Number(
          account.totalReturnPercent,
        )
      : (
          initialCash > 0
            ? (
                totalPnl /
                initialCash
              ) * 100
            : 0
        );

  const winRate =
    trades.length > 0
      ? (
          wins.length /
          trades.length
        ) * 100
      : null;

  const performanceScore =
    calculatePerformanceScore({
      winRate,
      profitFactor:
        Number.isFinite(
          profitFactor,
        )
          ? profitFactor
          : null,

      totalReturnPercent,

      maximumDrawdownPercent:
        maximumDrawdown.percent,

      sampleSize:
        trades.length,
    });

  return {
    version:
      PAPER_AI_PERFORMANCE_ANALYZER_VERSION,

    sampleSize:
      trades.length,

    dataStatus:
      trades.length >= 30
        ? "sufficient"
        : trades.length >= 10
          ? "limited"
          : "insufficient",

    metrics: {
      tradeCount:
        trades.length,

      winCount:
        wins.length,

      lossCount:
        losses.length,

      winRate,

      totalPnl,

      totalReturnPercent,

      averagePnl:
        average(
          trades.map(
            (trade) =>
              trade.realizedPnl,
          ),
        ),

      averageWin,

      averageLoss,

      payoffRatio:
        finite(averageWin) &&
        finite(averageLoss) &&
        Number(averageLoss) !== 0
          ? (
              Number(
                averageWin,
              ) /
              Math.abs(
                Number(
                  averageLoss,
                ),
              )
            )
          : null,

      profitFactor,

      sharpeLikeRatio:
        calculateSharpeLikeRatio({
          trades,
          initialCash,
        }),

      maximumDrawdownAmount:
        maximumDrawdown.amount,

      maximumDrawdownPercent:
        maximumDrawdown.percent,

      performanceScore,
    },

    symbols:
      createSymbolStatistics(
        trades,
      ),

    warnings: [
      ...(
        trades.length < 10
          ? [
              "sample_size_too_small",
            ]
          : []
      ),

      ...(
        maximumDrawdown.percent >= 10
          ? [
              "drawdown_high",
            ]
          : []
      ),

      ...(
        finite(profitFactor) &&
        Number(profitFactor) < 1
          ? [
              "profit_factor_below_one",
            ]
          : []
      ),
    ],
  };
}

export const PaperAiPerformanceAnalyzerInternals = {
  finite,
  numberOr,
  average,
  standardDeviation,
  calculateProfitFactor,
  calculateMaximumDrawdown,
  groupTradesBySymbol,
  createSymbolStatistics,
  calculateSharpeLikeRatio,
  calculatePerformanceScore,
};