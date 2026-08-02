export const PAPER_PERFORMANCE_VERSION =
  "paper-performance-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function average(values) {
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

export function calculatePaperPerformance(
  account = {},
) {
  const trades =
    Array.isArray(
      account.tradeHistory,
    )
      ? account.tradeHistory
      : [];

  const closedTrades =
    trades.filter(
      (trade) =>
        finite(
          trade.realizedPnl,
        ),
    );

  const winners =
    closedTrades.filter(
      (trade) =>
        Number(
          trade.realizedPnl,
        ) > 0,
    );

  const losers =
    closedTrades.filter(
      (trade) =>
        Number(
          trade.realizedPnl,
        ) < 0,
    );

  const grossProfit =
    winners.reduce(
      (sum, trade) =>
        sum +
        Number(
          trade.realizedPnl,
        ),
      0,
    );

  const grossLoss =
    losers.reduce(
      (sum, trade) =>
        sum +
        Number(
          trade.realizedPnl,
        ),
      0,
    );

  return {
    version:
      PAPER_PERFORMANCE_VERSION,

    initialCash:
      Number(
        account.initialCash || 0,
      ),

    cash:
      Number(
        account.cash || 0,
      ),

    equity:
      Number(
        account.equity || 0,
      ),

    realizedPnl:
      Number(
        account.realizedPnl || 0,
      ),

    unrealizedPnl:
      Number(
        account.unrealizedPnl || 0,
      ),

    totalPnl:
      Number(
        account.totalPnl || 0,
      ),

    totalReturnPercent:
      Number(
        account.totalReturnPercent || 0,
      ),

    tradeCount:
      closedTrades.length,

    winCount:
      winners.length,

    lossCount:
      losers.length,

    winRate:
      closedTrades.length > 0
        ? (
            winners.length /
            closedTrades.length
          ) * 100
        : null,

    averageWin:
      average(
        winners.map(
          (trade) =>
            trade.realizedPnl,
        ),
      ),

    averageLoss:
      average(
        losers.map(
          (trade) =>
            trade.realizedPnl,
        ),
      ),

    profitFactor:
      grossLoss < 0
        ? (
            grossProfit /
            Math.abs(grossLoss)
          )
        : grossProfit > 0
          ? Infinity
          : null,
  };
}