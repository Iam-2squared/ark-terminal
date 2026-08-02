function finiteNumber(value, fallback = 0) {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function round(value, digits = 4) {
  const factor = 10 ** digits;

  return (
    Math.round(
      finiteNumber(value) * factor,
    ) / factor
  );
}

function clamp(value, minimum, maximum) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      finiteNumber(value),
    ),
  );
}

function normalizeAction(action = "HOLD") {
  const normalized =
    String(action)
      .trim()
      .toUpperCase();

  if (normalized === "STRONG BUY") {
    return "BUY";
  }

  if (
    normalized === "STRONG SELL" ||
    normalized === "REDUCE"
  ) {
    return "SELL";
  }

  if (
    [
      "BUY",
      "SELL",
      "HOLD",
      "WATCH",
      "NO TRADE",
    ].includes(normalized)
  ) {
    return normalized;
  }

  return "HOLD";
}

function actionToDirection(action = "HOLD") {
  const normalized =
    normalizeAction(action);

  if (normalized === "BUY") {
    return "UP";
  }

  if (normalized === "SELL") {
    return "DOWN";
  }

  return "FLAT";
}

function classifyReturn({
  returnPercent = 0,
  neutralThreshold = 0.5,
} = {}) {
  const value =
    finiteNumber(
      returnPercent,
      0,
    );

  const threshold =
    Math.max(
      0,
      finiteNumber(
        neutralThreshold,
        0.5,
      ),
    );

  if (value > threshold) {
    return "UP";
  }

  if (value < -threshold) {
    return "DOWN";
  }

  return "FLAT";
}

function calculateProfitFactor(
  returns = [],
) {
  const grossProfit =
    returns
      .filter(
        (value) =>
          finiteNumber(value) > 0,
      )
      .reduce(
        (sum, value) =>
          sum +
          finiteNumber(value),
        0,
      );

  const grossLoss =
    Math.abs(
      returns
        .filter(
          (value) =>
            finiteNumber(value) < 0,
        )
        .reduce(
          (sum, value) =>
            sum +
            finiteNumber(value),
          0,
        ),
    );

  if (grossLoss === 0) {
    return grossProfit > 0
      ? Infinity
      : 0;
  }

  return round(
    grossProfit / grossLoss,
    4,
  );
}

function calculateMaximumDrawdown(
  returns = [],
) {
  let equity = 1;
  let peak = 1;
  let maximumDrawdown = 0;

  for (const value of returns) {
    equity *=
      1 +
      finiteNumber(
        value,
        0,
      ) /
      100;

    peak =
      Math.max(
        peak,
        equity,
      );

    const drawdown =
      peak > 0
        ? (
            peak -
            equity
          ) /
          peak *
          100
        : 0;

    maximumDrawdown =
      Math.max(
        maximumDrawdown,
        drawdown,
      );
  }

  return round(
    maximumDrawdown,
    4,
  );
}

function calculateCalibrationError(
  predictions = [],
) {
  const valid =
    predictions.filter(
      (item) =>
        Number.isFinite(
          Number(
            item.confidence,
          ),
        ),
    );

  if (valid.length === 0) {
    return null;
  }

  const totalError =
    valid.reduce(
      (sum, item) => {
        const predictedProbability =
          clamp(
            item.confidence,
            0,
            100,
          ) /
          100;

        const actualOutcome =
          item.correct
            ? 1
            : 0;

        return (
          sum +
          Math.abs(
            predictedProbability -
            actualOutcome,
          )
        );
      },
      0,
    );

  return round(
    totalError /
    valid.length,
    4,
  );
}

export function normalizeWalkForwardRows(
  rows = [],
) {
  const safeRows =
    Array.isArray(rows)
      ? rows
      : [];

  return safeRows
    .map(
      (
        row,
        originalIndex,
      ) => ({
        originalIndex,

        date:
          row.date ??
          row.timestamp ??
          null,

        symbol:
          row.symbol ??
          null,

        close:
          finiteNumber(
            row.close ??
            row.price,
            NaN,
          ),

        features:
          row.features ??
          row.input ??
          {},

        raw:
          row,
      }),
    )
    .filter(
      (row) =>
        Number.isFinite(
          row.close,
        ) &&
        row.close > 0 &&
        row.date,
    )
    .sort(
      (
        first,
        second,
      ) =>
        new Date(
          first.date,
        ) -
        new Date(
          second.date,
        ),
    );
}

export function evaluateWalkForwardPrediction({
  prediction = {},
  entryRow = {},
  exitRow = {},
  horizon = 5,
  neutralThreshold = 0.5,
} = {}) {
  const entryPrice =
    finiteNumber(
      entryRow.close,
      0,
    );

  const exitPrice =
    finiteNumber(
      exitRow.close,
      0,
    );

  const returnPercent =
    entryPrice > 0
      ? (
          exitPrice -
          entryPrice
        ) /
        entryPrice *
        100
      : 0;

  const action =
    normalizeAction(
      prediction.action,
    );

  const predictedDirection =
    actionToDirection(
      action,
    );

  const actualDirection =
    classifyReturn({
      returnPercent,
      neutralThreshold,
    });

  const correct =
    predictedDirection ===
    actualDirection;

  let strategyReturn = 0;

  if (action === "BUY") {
    strategyReturn =
      returnPercent;
  }
  else if (action === "SELL") {
    strategyReturn =
      -returnPercent;
  }

  return {
    symbol:
      entryRow.symbol ??
      prediction.symbol ??
      null,

    entryDate:
      entryRow.date ??
      null,

    exitDate:
      exitRow.date ??
      null,

    horizon,

    entryPrice:
      round(
        entryPrice,
        4,
      ),

    exitPrice:
      round(
        exitPrice,
        4,
      ),

    action,

    predictedDirection,

    actualDirection,

    correct,

    score:
      finiteNumber(
        prediction.score,
        50,
      ),

    confidence:
      finiteNumber(
        prediction.confidence,
        0,
      ),

    returnPercent:
      round(
        returnPercent,
        4,
      ),

    strategyReturn:
      round(
        strategyReturn,
        4,
      ),
  };
}

export function summarizeWalkForwardAudit(
  predictions = [],
) {
  const safePredictions =
    Array.isArray(
      predictions,
    )
      ? predictions
      : [];

  const total =
    safePredictions.length;

  if (total === 0) {
    return {
      total: 0,
      correct: 0,
      accuracy: 0,
      buySignals: 0,
      buyWins: 0,
      buyPrecision: 0,
      sellSignals: 0,
      sellWins: 0,
      sellPrecision: 0,
      averageReturn: 0,
      averageStrategyReturn: 0,
      profitFactor: 0,
      maximumDrawdown: 0,
      calibrationError: null,
    };
  }

  const correct =
    safePredictions.filter(
      (item) =>
        item.correct === true,
    ).length;

  const buyPredictions =
    safePredictions.filter(
      (item) =>
        item.action === "BUY",
    );

  const sellPredictions =
    safePredictions.filter(
      (item) =>
        item.action === "SELL",
    );

  const buyWins =
    buyPredictions.filter(
      (item) =>
        item.actualDirection ===
        "UP",
    ).length;

  const sellWins =
    sellPredictions.filter(
      (item) =>
        item.actualDirection ===
        "DOWN",
    ).length;

  const marketReturns =
    safePredictions.map(
      (item) =>
        finiteNumber(
          item.returnPercent,
        ),
    );

  const strategyReturns =
    safePredictions.map(
      (item) =>
        finiteNumber(
          item.strategyReturn,
        ),
    );

  return {
    total,

    correct,

    accuracy:
      round(
        correct /
        total *
        100,
        2,
      ),

    buySignals:
      buyPredictions.length,

    buyWins,

    buyPrecision:
      buyPredictions.length
        ? round(
            buyWins /
            buyPredictions.length *
            100,
            2,
          )
        : 0,

    sellSignals:
      sellPredictions.length,

    sellWins,

    sellPrecision:
      sellPredictions.length
        ? round(
            sellWins /
            sellPredictions.length *
            100,
            2,
          )
        : 0,

    averageReturn:
      round(
        marketReturns.reduce(
          (sum, value) =>
            sum + value,
          0,
        ) /
        total,
        4,
      ),

    averageStrategyReturn:
      round(
        strategyReturns.reduce(
          (sum, value) =>
            sum + value,
          0,
        ) /
        total,
        4,
      ),

    profitFactor:
      calculateProfitFactor(
        strategyReturns,
      ),

    maximumDrawdown:
      calculateMaximumDrawdown(
        strategyReturns,
      ),

    calibrationError:
      calculateCalibrationError(
        safePredictions,
      ),
  };
}

export async function runWalkForwardAudit({
  rows = [],
  predictor,
  horizon = 5,
  minimumHistory = 20,
  neutralThreshold = 0.5,
  onProgress,
} = {}) {
  if (
    typeof predictor !==
    "function"
  ) {
    throw new TypeError(
      "predictor must be a function",
    );
  }

  const normalizedRows =
    normalizeWalkForwardRows(
      rows,
    );

  const safeHorizon =
    Math.max(
      1,
      Math.floor(
        finiteNumber(
          horizon,
          5,
        ),
      ),
    );

  const safeMinimumHistory =
    Math.max(
      1,
      Math.floor(
        finiteNumber(
          minimumHistory,
          20,
        ),
      ),
    );

  const predictions = [];

  const lastEntryIndex =
    normalizedRows.length -
    safeHorizon;

  for (
    let index =
      safeMinimumHistory - 1;
    index <
      lastEntryIndex;
    index++
  ) {
    const entryRow =
      normalizedRows[index];

    const exitRow =
      normalizedRows[
        index +
        safeHorizon
      ];

    const visibleHistory =
      normalizedRows.slice(
        0,
        index + 1,
      );

    const predictorInput = {
      symbol:
        entryRow.symbol,

      date:
        entryRow.date,

      price:
        entryRow.close,

      features:
        entryRow.features,

      horizon:
        safeHorizon,

      history:
        visibleHistory.map(
          (row) => ({
            date:
              row.date,

            symbol:
              row.symbol,

            close:
              row.close,

            features:
              row.features,
          }),
        ),
    };

    const prediction =
      await predictor(
        predictorInput,
      );

    const evaluated =
      evaluateWalkForwardPrediction({
        prediction,
        entryRow,
        exitRow,
        horizon:
          safeHorizon,
        neutralThreshold,
      });

    predictions.push(
      evaluated,
    );

    if (
      typeof onProgress ===
      "function"
    ) {
      onProgress({
        completed:
          predictions.length,

        total:
          Math.max(
            0,
            lastEntryIndex -
            (
              safeMinimumHistory -
              1
            ),
          ),

        latest:
          evaluated,
      });
    }
  }

  return {
    version:
      "walk-forward-accuracy-audit-v1",

    generatedAt:
      new Date()
        .toISOString(),

    horizon:
      safeHorizon,

    minimumHistory:
      safeMinimumHistory,

    neutralThreshold:
      finiteNumber(
        neutralThreshold,
        0.5,
      ),

    sourceRows:
      normalizedRows.length,

    predictions,

    summary:
      summarizeWalkForwardAudit(
        predictions,
      ),
  };
}

export const WalkForwardAccuracyAuditInternals = {
  actionToDirection,
  calculateCalibrationError,
  calculateMaximumDrawdown,
  calculateProfitFactor,
  classifyReturn,
  finiteNumber,
  normalizeAction,
  round,
};