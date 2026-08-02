const EPSILON = 1e-12;

function toFiniteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function round(value, digits = 6) {
  if (!Number.isFinite(value)) {
    return 0;
  }

  const factor = 10 ** digits;
  return Math.round((value + Number.EPSILON) * factor) / factor;
}

function normalizeSignal(value) {
  const signal = String(value ?? "").trim().toUpperCase();

  if (signal === "BUY" || signal === "LONG") {
    return "BUY";
  }

  if (signal === "SELL" || signal === "SHORT") {
    return "SELL";
  }

  if (signal === "HOLD" || signal === "NEUTRAL") {
    return "HOLD";
  }

  return "UNKNOWN";
}

function readProfit(row) {
  const candidates = [
    row?.profit,
    row?.pnl,
    row?.return,
    row?.returnRate,
    row?.result?.profit,
    row?.result?.pnl,
    row?.outcome?.profit,
    row?.outcome?.pnl,
  ];

  for (const candidate of candidates) {
    const number = Number(candidate);

    if (Number.isFinite(number)) {
      return number;
    }
  }

  return 0;
}

function readCorrect(row, profit) {
  const candidates = [
    row?.correct,
    row?.isCorrect,
    row?.hit,
    row?.result?.correct,
    row?.outcome?.correct,
  ];

  for (const candidate of candidates) {
    if (typeof candidate === "boolean") {
      return candidate;
    }
  }

  const predicted = normalizeSignal(
    row?.signal ??
      row?.prediction ??
      row?.action ??
      row?.decision ??
      row?.result?.signal,
  );

  const actual = normalizeSignal(
    row?.actual ??
      row?.actualSignal ??
      row?.outcome?.signal ??
      row?.result?.actual,
  );

  if (predicted !== "UNKNOWN" && actual !== "UNKNOWN") {
    return predicted === actual;
  }

  return profit > 0;
}

function safeRate(numerator, denominator) {
  return denominator > 0 ? numerator / denominator : 0;
}

function calculateMaxDrawdown(profits) {
  let equity = 0;
  let peak = 0;
  let maxDrawdown = 0;

  for (const profit of profits) {
    equity += profit;

    if (equity > peak) {
      peak = equity;
    }

    const drawdown = peak - equity;

    if (drawdown > maxDrawdown) {
      maxDrawdown = drawdown;
    }
  }

  return maxDrawdown;
}

export function normalizeAccuracyRows(rows = []) {
  if (!Array.isArray(rows)) {
    throw new TypeError("rows must be an array");
  }

  return rows.map((row, index) => {
    const profit = readProfit(row);
    const signal = normalizeSignal(
      row?.signal ??
        row?.prediction ??
        row?.action ??
        row?.decision ??
        row?.result?.signal,
    );

    return {
      ...row,
      index,
      signal,
      profit,
      correct: readCorrect(row, profit),
    };
  });
}

export function calculateAccuracyMetrics(rows = []) {
  const normalizedRows = normalizeAccuracyRows(rows);

  const total = normalizedRows.length;
  const correct = normalizedRows.filter((row) => row.correct).length;
  const incorrect = total - correct;

  const buyRows = normalizedRows.filter((row) => row.signal === "BUY");
  const sellRows = normalizedRows.filter((row) => row.signal === "SELL");
  const holdRows = normalizedRows.filter((row) => row.signal === "HOLD");

  const winners = normalizedRows.filter((row) => row.profit > 0);
  const losers = normalizedRows.filter((row) => row.profit < 0);
  const flat = normalizedRows.filter(
    (row) => Math.abs(row.profit) <= EPSILON,
  );

  const grossProfit = winners.reduce((sum, row) => sum + row.profit, 0);
  const grossLoss = Math.abs(
    losers.reduce((sum, row) => sum + row.profit, 0),
  );

  const netProfit = normalizedRows.reduce(
    (sum, row) => sum + row.profit,
    0,
  );

  const averageProfit = safeRate(grossProfit, winners.length);
  const averageLoss = safeRate(grossLoss, losers.length);
  const expectancy = safeRate(netProfit, total);

  const profitFactor =
    grossLoss > EPSILON
      ? grossProfit / grossLoss
      : grossProfit > EPSILON
        ? Number.POSITIVE_INFINITY
        : 0;

  const buyCorrect = buyRows.filter((row) => row.correct).length;
  const sellCorrect = sellRows.filter((row) => row.correct).length;

  return {
    total,
    correct,
    incorrect,

    accuracy: round(safeRate(correct, total)),
    accuracyPercent: round(safeRate(correct, total) * 100),

    buy: {
      total: buyRows.length,
      correct: buyCorrect,
      winRate: round(safeRate(buyCorrect, buyRows.length)),
      winRatePercent: round(
        safeRate(buyCorrect, buyRows.length) * 100,
      ),
    },

    sell: {
      total: sellRows.length,
      correct: sellCorrect,
      winRate: round(safeRate(sellCorrect, sellRows.length)),
      winRatePercent: round(
        safeRate(sellCorrect, sellRows.length) * 100,
      ),
    },

    hold: {
      total: holdRows.length,
    },

    trades: {
      winners: winners.length,
      losers: losers.length,
      flat: flat.length,
      winRate: round(safeRate(winners.length, total)),
      winRatePercent: round(
        safeRate(winners.length, total) * 100,
      ),
    },

    grossProfit: round(grossProfit),
    grossLoss: round(grossLoss),
    netProfit: round(netProfit),
    averageProfit: round(averageProfit),
    averageLoss: round(averageLoss),
    expectancy: round(expectancy),
    profitFactor:
      profitFactor === Number.POSITIVE_INFINITY
        ? Number.POSITIVE_INFINITY
        : round(profitFactor),

    maxDrawdown: round(
      calculateMaxDrawdown(
        normalizedRows.map((row) => toFiniteNumber(row.profit)),
      ),
    ),
  };
}

export default calculateAccuracyMetrics;
