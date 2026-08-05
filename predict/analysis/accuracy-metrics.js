const EPSILON = 1e-12;

function toFiniteNumber(value, fallback = null) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return fallback;
  }

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
  const signal = String(value ?? "")
    .trim()
    .toUpperCase()
    .replaceAll(" ", "_");

  if (signal === "BUY" || signal === "LONG") {
    return "BUY";
  }

  if (signal === "SELL" || signal === "SHORT") {
    return "SELL";
  }

  if (signal === "HOLD" || signal === "NEUTRAL") {
    return "HOLD";
  }

  if (
    signal === "NO_TRADE" ||
    signal === "NO-TRADE" ||
    signal === "BLOCK" ||
    signal === "WAIT" ||
    signal === "REJECT"
  ) {
    return "NO_TRADE";
  }

  return "UNKNOWN";
}

function normalizeStatus(value) {
  const status = String(value ?? "")
    .trim()
    .toUpperCase()
    .replaceAll(" ", "_");

  if (["WIN", "LOSS", "FLAT"].includes(status)) {
    return status;
  }

  if (["PENDING", "OPEN", "UNRESOLVED"].includes(status)) {
    return "PENDING";
  }

  if (["CANCELLED", "CANCELED", "VOID"].includes(status)) {
    return "CANCELLED";
  }

  return "UNKNOWN";
}

function readProfit(row) {
  const candidates = [
    row?.profit,
    row?.pnl,
    row?.return,
    row?.returnRate,
    row?.returnPercent,
    row?.actualReturnPercent,
    row?.result?.profit,
    row?.result?.pnl,
    row?.outcome?.profit,
    row?.outcome?.pnl,
  ];

  for (const candidate of candidates) {
    const number = toFiniteNumber(candidate);

    if (number !== null) {
      return number;
    }
  }

  return null;
}

function readExplicitCorrect(row) {
  const candidates = [
    row?.correct,
    row?.isCorrect,
    row?.hit,
    row?.evaluation?.hit,
    row?.result?.correct,
    row?.outcome?.correct,
  ];

  for (const candidate of candidates) {
    if (typeof candidate === "boolean") {
      return candidate;
    }
  }

  return null;
}

function readActualSignal(row) {
  return normalizeSignal(
    row?.actual ??
      row?.actualSignal ??
      row?.outcome?.signal ??
      row?.result?.actual,
  );
}

function readCorrect(row, { signal, profit, status }) {
  const explicit = readExplicitCorrect(row);

  if (explicit !== null) {
    return explicit;
  }

  if (status === "WIN") {
    return true;
  }

  if (status === "LOSS") {
    return false;
  }

  if (status === "FLAT") {
    return false;
  }

  const actual = readActualSignal(row);

  if (
    ["BUY", "SELL"].includes(signal) &&
    ["BUY", "SELL"].includes(actual)
  ) {
    return signal === actual;
  }

  if (
    ["BUY", "SELL"].includes(signal) &&
    profit !== null
  ) {
    return profit > 0;
  }

  return null;
}

function isResolvedRow(row, { status, correct, profit, signal }) {
  if (status === "PENDING" || status === "CANCELLED") {
    return false;
  }

  if (row?.resolved === false) {
    return false;
  }

  if (["WIN", "LOSS", "FLAT"].includes(status)) {
    return true;
  }

  if (correct !== null) {
    return true;
  }

  return (
    row?.resolved === true &&
    ["BUY", "SELL"].includes(signal) &&
    profit !== null
  );
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
    const status = normalizeStatus(
      row?.status ??
        row?.outcome?.status ??
        row?.result?.status ??
        row?.outcome,
    );
    const correct = readCorrect(row, {
      signal,
      profit,
      status,
    });
    const resolved = isResolvedRow(row, {
      status,
      correct,
      profit,
      signal,
    });

    return {
      ...row,
      index,
      signal,
      status,
      profit,
      correct,
      resolved,
      accuracyEligible:
        resolved &&
        ["BUY", "SELL"].includes(signal) &&
        correct !== null,
      tradePerformanceEligible:
        resolved &&
        ["BUY", "SELL"].includes(signal) &&
        profit !== null,
    };
  });
}

export function calculateAccuracyMetrics(rows = []) {
  const normalizedRows = normalizeAccuracyRows(rows);

  const accuracyRows = normalizedRows.filter(
    (row) => row.accuracyEligible,
  );
  const tradeRows = normalizedRows.filter(
    (row) => row.tradePerformanceEligible,
  );

  const total = accuracyRows.length;
  const correct = accuracyRows.filter(
    (row) => row.correct === true,
  ).length;
  const incorrect = total - correct;

  const buyRows = accuracyRows.filter(
    (row) => row.signal === "BUY",
  );
  const sellRows = accuracyRows.filter(
    (row) => row.signal === "SELL",
  );
  const holdRows = normalizedRows.filter(
    (row) => row.signal === "HOLD",
  );
  const noTradeRows = normalizedRows.filter(
    (row) => row.signal === "NO_TRADE",
  );
  const pendingRows = normalizedRows.filter(
    (row) => !row.resolved,
  );
  const unknownRows = normalizedRows.filter(
    (row) => row.signal === "UNKNOWN",
  );

  const winners = tradeRows.filter(
    (row) => row.profit > EPSILON,
  );
  const losers = tradeRows.filter(
    (row) => row.profit < -EPSILON,
  );
  const flat = tradeRows.filter(
    (row) => Math.abs(row.profit) <= EPSILON,
  );

  const grossProfit = winners.reduce(
    (sum, row) => sum + row.profit,
    0,
  );
  const grossLoss = Math.abs(
    losers.reduce((sum, row) => sum + row.profit, 0),
  );

  const netProfit = tradeRows.reduce(
    (sum, row) => sum + row.profit,
    0,
  );

  const averageProfit = safeRate(grossProfit, winners.length);
  const averageLoss = safeRate(grossLoss, losers.length);
  const expectancy = safeRate(netProfit, tradeRows.length);

  const profitFactor =
    grossLoss > EPSILON
      ? grossProfit / grossLoss
      : grossProfit > EPSILON
        ? Number.POSITIVE_INFINITY
        : 0;

  const buyCorrect = buyRows.filter(
    (row) => row.correct === true,
  ).length;
  const sellCorrect = sellRows.filter(
    (row) => row.correct === true,
  ).length;

  return {
    sourceTotal: normalizedRows.length,
    total,
    correct,
    incorrect,

    denominatorPolicy: {
      accuracy:
        "Resolved BUY/SELL predictions with a known correctness result only.",
      tradePerformance:
        "Resolved BUY/SELL rows with a finite realized or evaluated P&L only.",
      excludes: [
        "PENDING",
        "CANCELLED",
        "NO_TRADE",
        "HOLD",
        "UNKNOWN",
        "MISSING_OUTCOME",
      ],
    },

    excluded: {
      pending: pendingRows.length,
      noTrade: noTradeRows.length,
      hold: holdRows.length,
      unknown: unknownRows.length,
      missingCorrectness: normalizedRows.filter(
        (row) =>
          row.resolved &&
          ["BUY", "SELL"].includes(row.signal) &&
          row.correct === null,
      ).length,
      missingProfit: normalizedRows.filter(
        (row) =>
          row.resolved &&
          ["BUY", "SELL"].includes(row.signal) &&
          row.profit === null,
      ).length,
    },

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

    noTrade: {
      total: noTradeRows.length,
    },

    trades: {
      total: tradeRows.length,
      winners: winners.length,
      losers: losers.length,
      flat: flat.length,
      winRate: round(
        safeRate(winners.length, tradeRows.length),
      ),
      winRatePercent: round(
        safeRate(winners.length, tradeRows.length) * 100,
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
        tradeRows.map((row) =>
          toFiniteNumber(row.profit, 0),
        ),
      ),
    ),
  };
}

export const AccuracyMetricsInternals = {
  normalizeSignal,
  normalizeStatus,
  readProfit,
  readCorrect,
  isResolvedRow,
};

export default calculateAccuracyMetrics;
