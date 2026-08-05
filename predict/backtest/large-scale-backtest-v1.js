export const LARGE_SCALE_BACKTEST_V1 = "large-scale-backtest-v1";

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function summarize(trades = []) {
  const closed = trades.filter((trade) => Number.isFinite(Number(trade?.return)));
  const wins = closed.filter((trade) => finite(trade.return) > 0);
  const losses = closed.filter((trade) => finite(trade.return) < 0);
  const grossProfit = wins.reduce((sum, trade) => sum + finite(trade.netReturn, trade.return), 0);
  const grossLoss = Math.abs(losses.reduce((sum, trade) => sum + finite(trade.netReturn, trade.return), 0));
  const expectedValue = closed.length ? closed.reduce((sum, trade) => sum + finite(trade.netReturn, trade.return), 0) / closed.length : 0;
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  for (const trade of closed) {
    equity *= 1 + finite(trade.netReturn, trade.return);
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak ? (peak - equity) / peak : 0);
  }
  return {
    sampleSize: closed.length,
    winRate: closed.length ? wins.length / closed.length : 0,
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0,
    expectedValue,
    maxDrawdown,
  };
}

export function runLargeScaleBacktestV1({ signals = [], feeRate = 0.001, slippageRate = 0.001 } = {}) {
  const trades = signals.map((signal) => {
    const gross = finite(signal?.return);
    const cost = Math.abs(finite(signal?.positionSize, 1)) * (feeRate + slippageRate);
    return {
      ...signal,
      grossReturn: gross,
      netReturn: gross - cost,
    };
  });
  const breakdown = (key) => Object.entries(trades.reduce((acc, trade) => {
    const value = trade?.[key] ?? "UNKNOWN";
    (acc[value] ??= []).push(trade);
    return acc;
  }, {})).map(([name, rows]) => ({ name, ...summarize(rows) }));

  return {
    version: LARGE_SCALE_BACKTEST_V1,
    generatedAt: new Date().toISOString(),
    status: trades.length ? "READY" : "BLOCKED",
    assumptions: { feeRate, slippageRate },
    overall: summarize(trades),
    bySymbol: breakdown("symbol"),
    bySector: breakdown("sector"),
    byRegime: breakdown("regime"),
    byAction: breakdown("action"),
    trades,
    futureLeakDetected: signals.some((row) => row?.signalAt && row?.outcomeAt && Date.parse(row.outcomeAt) <= Date.parse(row.signalAt)),
    advisoryOnly: true,
    brokerExecutionAllowed: false,
  };
}

export default runLargeScaleBacktestV1;
