const EPSILON = 1e-12;

function round(value, digits = 6) {
  if (!Number.isFinite(value)) {
    return 0;
  }

  const factor = 10 ** digits;
  return Math.round((value + Number.EPSILON) * factor) / factor;
}

function mean(values) {
  if (values.length === 0) {
    return 0;
  }

  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function sampleStandardDeviation(values) {
  if (values.length < 2) {
    return 0;
  }

  const average = mean(values);
  const variance =
    values.reduce(
      (sum, value) => sum + (value - average) ** 2,
      0,
    ) /
    (values.length - 1);

  return Math.sqrt(Math.max(variance, 0));
}

function downsideDeviation(values, target = 0) {
  if (values.length === 0) {
    return 0;
  }

  const downsideSquares = values.map((value) =>
    Math.min(value - target, 0) ** 2,
  );

  return Math.sqrt(mean(downsideSquares));
}

function calculateMaxDrawdownFromReturns(returns) {
  let equity = 1;
  let peak = 1;
  let maximumDrawdown = 0;

  for (const value of returns) {
    equity *= 1 + value;

    if (equity > peak) {
      peak = equity;
    }

    if (peak > EPSILON) {
      const drawdown = (peak - equity) / peak;

      if (drawdown > maximumDrawdown) {
        maximumDrawdown = drawdown;
      }
    }
  }

  return maximumDrawdown;
}

export function normalizeReturns(values = []) {
  if (!Array.isArray(values)) {
    throw new TypeError("returns must be an array");
  }

  return values
    .map((value) => {
      if (typeof value === "number") {
        return value;
      }

      const candidates = [
        value?.return,
        value?.returnRate,
        value?.profitRate,
        value?.profit,
        value?.pnl,
        value?.result?.return,
        value?.result?.profit,
      ];

      for (const candidate of candidates) {
        const number = Number(candidate);

        if (Number.isFinite(number)) {
          return number;
        }
      }

      return null;
    })
    .filter((value) => Number.isFinite(value));
}

export function calculateRiskAdjustedMetrics(
  values = [],
  options = {},
) {
  const returns = normalizeReturns(values);

  const periodsPerYear = Number.isFinite(
    Number(options.periodsPerYear),
  )
    ? Math.max(1, Number(options.periodsPerYear))
    : 252;

  const riskFreeRate = Number.isFinite(
    Number(options.riskFreeRate),
  )
    ? Number(options.riskFreeRate)
    : 0;

  const targetReturn = Number.isFinite(
    Number(options.targetReturn),
  )
    ? Number(options.targetReturn)
    : 0;

  if (returns.length === 0) {
    return {
      count: 0,
      averageReturn: 0,
      volatility: 0,
      downsideDeviation: 0,
      annualizedReturn: 0,
      annualizedVolatility: 0,
      sharpeRatio: 0,
      sortinoRatio: 0,
      calmarRatio: 0,
      maxDrawdown: 0,
    };
  }

  const averageReturn = mean(returns);
  const volatility = sampleStandardDeviation(returns);
  const downside = downsideDeviation(returns, targetReturn);

  const annualizedVolatility =
    volatility * Math.sqrt(periodsPerYear);

  const compoundedReturn = returns.reduce(
    (value, currentReturn) => value * (1 + currentReturn),
    1,
  );

  const annualizedReturn =
    compoundedReturn > 0
      ? compoundedReturn **
          (periodsPerYear / returns.length) -
        1
      : -1;

  const periodRiskFreeRate = riskFreeRate / periodsPerYear;

  const sharpeRatio =
    volatility > EPSILON
      ? ((averageReturn - periodRiskFreeRate) / volatility) *
        Math.sqrt(periodsPerYear)
      : 0;

  const sortinoRatio =
    downside > EPSILON
      ? ((averageReturn - targetReturn) / downside) *
        Math.sqrt(periodsPerYear)
      : 0;

  const maxDrawdown =
    calculateMaxDrawdownFromReturns(returns);

  const calmarRatio =
    maxDrawdown > EPSILON
      ? annualizedReturn / maxDrawdown
      : 0;

  return {
    count: returns.length,
    averageReturn: round(averageReturn),
    volatility: round(volatility),
    downsideDeviation: round(downside),
    annualizedReturn: round(annualizedReturn),
    annualizedVolatility: round(annualizedVolatility),
    sharpeRatio: round(sharpeRatio),
    sortinoRatio: round(sortinoRatio),
    calmarRatio: round(calmarRatio),
    maxDrawdown: round(maxDrawdown),
  };
}

export default calculateRiskAdjustedMetrics;
