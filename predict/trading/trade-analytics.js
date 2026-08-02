export const TRADE_ANALYTICS_VERSION =
  "trade-analytics-v1";

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

function average(values) {
  const valid =
    values.filter(finite)
      .map(Number);

  if (!valid.length) {
    return null;
  }

  return (
    valid.reduce(
      (sum, value) => sum + value,
      0,
    ) / valid.length
  );
}

function median(values) {
  const valid =
    values.filter(finite)
      .map(Number)
      .sort((a, b) => a - b);

  if (!valid.length) {
    return null;
  }

  const middle =
    Math.floor(valid.length / 2);

  if (valid.length % 2 === 0) {
    return (
      valid[middle - 1] +
      valid[middle]
    ) / 2;
  }

  return valid[middle];
}

function sideMultiplier(side) {
  return side === "short"
    ? -1
    : 1;
}

function returnPercent({
  side,
  entryPrice,
  exitPrice,
}) {
  if (
    !finite(entryPrice) ||
    !finite(exitPrice) ||
    Number(entryPrice) <= 0
  ) {
    return null;
  }

  return (
    (
      Number(exitPrice) -
      Number(entryPrice)
    ) /
    Number(entryPrice) *
    100 *
    sideMultiplier(side)
  );
}

export function calculateTradeExcursion({
  side = "long",
  entryPrice,
  highestPrice,
  lowestPrice,
}) {
  if (
    !finite(entryPrice) ||
    Number(entryPrice) <= 0 ||
    !finite(highestPrice) ||
    !finite(lowestPrice)
  ) {
    return {
      mfePercent: null,
      maePercent: null,
    };
  }

  const entry =
    Number(entryPrice);

  const high =
    Number(highestPrice);

  const low =
    Number(lowestPrice);

  if (side === "short") {
    return {
      mfePercent:
        ((entry - low) / entry) *
        100,

      maePercent:
        ((entry - high) / entry) *
        100,
    };
  }

  return {
    mfePercent:
      ((high - entry) / entry) *
      100,

    maePercent:
      ((low - entry) / entry) *
      100,
  };
}

export function normalizeTradeAnalyticsRow(
  trade = {},
) {
  const excursion =
    calculateTradeExcursion({
      side: trade.side,
      entryPrice:
        trade.entryPrice,
      highestPrice:
        trade.highestPrice ??
        trade.maximumPrice ??
        trade.maxPrice,
      lowestPrice:
        trade.lowestPrice ??
        trade.minimumPrice ??
        trade.minPrice,
    });

  const grossPnl =
    numberOrNull(
      trade.grossPnl,
    );

  const netPnl =
    numberOrNull(
      trade.netPnl,
    );

  const totalTradingCost =
    numberOrNull(
      trade.totalTradingCost ??
      trade.tradingCost ??
      trade.cost,
    );

  const resolvedReturn =
    numberOrNull(
      trade.returnPercent,
    ) ??
    returnPercent({
      side: trade.side,
      entryPrice:
        trade.entryPrice,
      exitPrice:
        trade.exitPrice,
    });

  return {
    ...trade,

    grossPnl,
    netPnl,
    totalTradingCost,

    returnPercent:
      resolvedReturn,

    holdingBars:
      numberOrNull(
        trade.holdingBars ??
        trade.barsHeld,
      ),

    mfePercent:
      numberOrNull(
        trade.mfePercent,
      ) ??
      excursion.mfePercent,

    maePercent:
      numberOrNull(
        trade.maePercent,
      ) ??
      excursion.maePercent,

    exitReason:
      String(
        trade.exitReason ||
        trade.reason ||
        "unknown",
      ),
  };
}

export function groupTradesByExitReason(
  trades = [],
) {
  const groups = {};

  trades
    .map(normalizeTradeAnalyticsRow)
    .forEach((trade) => {
      const key =
        trade.exitReason ||
        "unknown";

      if (!groups[key]) {
        groups[key] = [];
      }

      groups[key].push(trade);
    });

  return Object.fromEntries(
    Object.entries(groups)
      .map(([reason, rows]) => {
        const pnlValues =
          rows.map(
            (row) =>
              row.netPnl,
          );

        const winners =
          rows.filter(
            (row) =>
              finite(row.netPnl) &&
              row.netPnl > 0,
          );

        return [
          reason,
          {
            count: rows.length,

            winCount:
              winners.length,

            winRate:
              rows.length > 0
                ? (
                    winners.length /
                    rows.length
                  ) * 100
                : null,

            totalNetPnl:
              pnlValues
                .filter(finite)
                .reduce(
                  (sum, value) =>
                    sum +
                    Number(value),
                  0,
                ),

            averageNetPnl:
              average(pnlValues),

            averageReturnPercent:
              average(
                rows.map(
                  (row) =>
                    row.returnPercent,
                ),
              ),

            averageHoldingBars:
              average(
                rows.map(
                  (row) =>
                    row.holdingBars,
                ),
              ),
          },
        ];
      }),
  );
}

export function summarizeTradeAnalytics(
  trades = [],
) {
  const rows =
    trades.map(
      normalizeTradeAnalyticsRow,
    );

  const winners =
    rows.filter(
      (row) =>
        finite(row.netPnl) &&
        row.netPnl > 0,
    );

  const losers =
    rows.filter(
      (row) =>
        finite(row.netPnl) &&
        row.netPnl < 0,
    );

  const flats =
    rows.filter(
      (row) =>
        finite(row.netPnl) &&
        row.netPnl === 0,
    );

  const grossProfit =
    winners.reduce(
      (sum, row) =>
        sum +
        Number(row.netPnl),
      0,
    );

  const grossLoss =
    losers.reduce(
      (sum, row) =>
        sum +
        Number(row.netPnl),
      0,
    );

  const averageWin =
    average(
      winners.map(
        (row) =>
          row.netPnl,
      ),
    );

  const averageLoss =
    average(
      losers.map(
        (row) =>
          row.netPnl,
      ),
    );

  const winRate =
    rows.length > 0
      ? (
          winners.length /
          rows.length
        ) * 100
      : null;

  const lossRate =
    rows.length > 0
      ? (
          losers.length /
          rows.length
        ) * 100
      : null;

  const expectancy =
    finite(winRate) &&
    finite(lossRate)
      ? (
          (
            Number(winRate) /
            100
          ) *
          Number(
            averageWin || 0,
          )
        ) +
        (
          (
            Number(lossRate) /
            100
          ) *
          Number(
            averageLoss || 0,
          )
        )
      : null;

  const payoffRatio =
    finite(averageWin) &&
    finite(averageLoss) &&
    Number(averageLoss) !== 0
      ? (
          Number(averageWin) /
          Math.abs(
            Number(averageLoss),
          )
        )
      : null;

  const totalTradingCost =
    rows.reduce(
      (sum, row) =>
        sum +
        Number(
          row.totalTradingCost ||
          0,
        ),
      0,
    );

  const grossPnlBeforeCosts =
    rows.reduce(
      (sum, row) => {
        if (finite(row.grossPnl)) {
          return (
            sum +
            Number(row.grossPnl)
          );
        }

        if (
          finite(row.netPnl) &&
          finite(
            row.totalTradingCost,
          )
        ) {
          return (
            sum +
            Number(row.netPnl) +
            Number(
              row.totalTradingCost,
            )
          );
        }

        return sum;
      },
      0,
    );

  const totalNetPnl =
    rows.reduce(
      (sum, row) =>
        sum +
        Number(
          row.netPnl || 0,
        ),
      0,
    );

  return {
    version:
      TRADE_ANALYTICS_VERSION,

    tradeCount:
      rows.length,

    winCount:
      winners.length,

    lossCount:
      losers.length,

    flatCount:
      flats.length,

    winRate,
    lossRate,

    grossProfit,
    grossLoss,

    profitFactor:
      grossLoss < 0
        ? (
            grossProfit /
            Math.abs(grossLoss)
          )
        : grossProfit > 0
          ? Infinity
          : null,

    averageWin,
    averageLoss,

    medianWin:
      median(
        winners.map(
          (row) =>
            row.netPnl,
        ),
      ),

    medianLoss:
      median(
        losers.map(
          (row) =>
            row.netPnl,
        ),
      ),

    payoffRatio,
    expectancy,

    maximumWin:
      winners.length
        ? Math.max(
            ...winners.map(
              (row) =>
                Number(row.netPnl),
            ),
          )
        : null,

    maximumLoss:
      losers.length
        ? Math.min(
            ...losers.map(
              (row) =>
                Number(row.netPnl),
            ),
          )
        : null,

    averageHoldingBars:
      average(
        rows.map(
          (row) =>
            row.holdingBars,
        ),
      ),

    averageWinningHoldingBars:
      average(
        winners.map(
          (row) =>
            row.holdingBars,
        ),
      ),

    averageLosingHoldingBars:
      average(
        losers.map(
          (row) =>
            row.holdingBars,
        ),
      ),

    averageMfePercent:
      average(
        rows.map(
          (row) =>
            row.mfePercent,
        ),
      ),

    averageMaePercent:
      average(
        rows.map(
          (row) =>
            row.maePercent,
        ),
      ),

    averageWinnerMfePercent:
      average(
        winners.map(
          (row) =>
            row.mfePercent,
        ),
      ),

    averageLoserMaePercent:
      average(
        losers.map(
          (row) =>
            row.maePercent,
        ),
      ),

    grossPnlBeforeCosts,
    totalTradingCost,
    totalNetPnl,

    costDragPercent:
      grossPnlBeforeCosts !== 0
        ? (
            totalTradingCost /
            Math.abs(
              grossPnlBeforeCosts,
            )
          ) * 100
        : null,

    byExitReason:
      groupTradesByExitReason(
        rows,
      ),
  };
}
