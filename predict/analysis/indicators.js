import { DataQualityError, validateHistoryData } from "./data-quality.js";

function finite(value) {
  return Number.isFinite(Number(value));
}

function last(values) {
  return values[values.length - 1];
}

function mean(values) {
  if (!values.length) {
    return null;
  }

  return values.reduce((sum, value) => sum + Number(value), 0) / values.length;
}

function latestWindow(values, period, offset = 0) {
  const end = values.length - offset;

  if (end < period) {
    return [];
  }

  return values.slice(end - period, end);
}

export function calculateSma(values, period, offset = 0) {
  const window = latestWindow(values, period, offset);

  return window.length === period ? mean(window) : null;
}

function calculateEmaSeries(values, period) {
  const result = new Array(values.length).fill(null);

  if (values.length < period) {
    return result;
  }

  const multiplier = 2 / (period + 1);

  let ema = mean(values.slice(0, period));

  result[period - 1] = ema;

  for (let index = period; index < values.length; index += 1) {
    ema = (Number(values[index]) - ema) * multiplier + ema;

    result[index] = ema;
  }

  return result;
}

function calculateRsi(closes, period = 14) {
  if (closes.length <= period) {
    return null;
  }

  let gains = 0;
  let losses = 0;

  for (let index = 1; index <= period; index += 1) {
    const change = closes[index] - closes[index - 1];

    gains += Math.max(change, 0);

    losses += Math.max(-change, 0);
  }

  let averageGain = gains / period;

  let averageLoss = losses / period;

  for (let index = period + 1; index < closes.length; index += 1) {
    const change = closes[index] - closes[index - 1];

    averageGain = (averageGain * (period - 1) + Math.max(change, 0)) / period;

    averageLoss = (averageLoss * (period - 1) + Math.max(-change, 0)) / period;
  }

  if (averageLoss === 0) {
    return 100;
  }

  const relativeStrength = averageGain / averageLoss;

  return 100 - 100 / (1 + relativeStrength);
}

function calculateMacd(closes) {
  const ema12 = calculateEmaSeries(closes, 12);

  const ema26 = calculateEmaSeries(closes, 26);

  const macdValues = [];
  const macdIndexes = [];

  closes.forEach((_value, index) => {
    if (finite(ema12[index]) && finite(ema26[index])) {
      macdValues.push(ema12[index] - ema26[index]);

      macdIndexes.push(index);
    }
  });

  const signalValues = calculateEmaSeries(macdValues, 9);

  if (!macdValues.length || !finite(last(signalValues))) {
    return null;
  }

  const value = last(macdValues);

  const signal = last(signalValues);

  const previousValue = macdValues[macdValues.length - 2];

  const previousSignal = signalValues[signalValues.length - 2];

  return {
    value,
    signal,
    histogram: value - signal,
    previousValue: finite(previousValue) ? previousValue : null,
    previousSignal: finite(previousSignal) ? previousSignal : null,
    sourceIndex: last(macdIndexes),
  };
}

function calculateBollingerBands(closes, period = 20, multiplier = 2) {
  const window = latestWindow(closes, period);

  if (window.length !== period) {
    return null;
  }

  const middle = mean(window);

  const variance = mean(window.map((value) => (value - middle) ** 2));

  const deviation = Math.sqrt(variance);

  const upper = middle + multiplier * deviation;

  const lower = middle - multiplier * deviation;

  const width = middle !== 0 ? ((upper - lower) / middle) * 100 : null;

  const percentB =
    upper !== lower ? (last(closes) - lower) / (upper - lower) : null;

  return {
    upper,
    middle,
    lower,
    width,
    percentB,
  };
}

function calculateTrueRanges(candles) {
  return candles.map((candle, index) => {
    if (index === 0) {
      return candle.high - candle.low;
    }

    const previousClose = candles[index - 1].close;

    return Math.max(
      candle.high - candle.low,
      Math.abs(candle.high - previousClose),
      Math.abs(candle.low - previousClose),
    );
  });
}

function calculateAtr(candles, period = 14) {
  const ranges = calculateTrueRanges(candles);

  if (ranges.length < period) {
    return null;
  }

  let atr = mean(ranges.slice(0, period));

  for (let index = period; index < ranges.length; index += 1) {
    atr = (atr * (period - 1) + ranges[index]) / period;
  }

  const close = last(candles).close;

  return {
    value: atr,
    percent: close !== 0 ? (atr / close) * 100 : null,
  };
}

function calculateAdx(candles, period = 14) {
  if (candles.length < period * 2 + 1) {
    return null;
  }

  const trueRanges = [];
  const plusDm = [];
  const minusDm = [];

  for (let index = 1; index < candles.length; index += 1) {
    const current = candles[index];

    const previous = candles[index - 1];

    const upMove = current.high - previous.high;

    const downMove = previous.low - current.low;

    trueRanges.push(
      Math.max(
        current.high - current.low,
        Math.abs(current.high - previous.close),
        Math.abs(current.low - previous.close),
      ),
    );

    plusDm.push(upMove > downMove && upMove > 0 ? upMove : 0);

    minusDm.push(downMove > upMove && downMove > 0 ? downMove : 0);
  }

  let smoothedTr = trueRanges
    .slice(0, period)
    .reduce((sum, value) => sum + value, 0);

  let smoothedPlus = plusDm
    .slice(0, period)
    .reduce((sum, value) => sum + value, 0);

  let smoothedMinus = minusDm
    .slice(0, period)
    .reduce((sum, value) => sum + value, 0);

  const dxValues = [];
  let latestPlusDi = null;
  let latestMinusDi = null;

  for (let index = period; index < trueRanges.length; index += 1) {
    smoothedTr = smoothedTr - smoothedTr / period + trueRanges[index];

    smoothedPlus = smoothedPlus - smoothedPlus / period + plusDm[index];

    smoothedMinus = smoothedMinus - smoothedMinus / period + minusDm[index];

    latestPlusDi = smoothedTr !== 0 ? (smoothedPlus / smoothedTr) * 100 : 0;

    latestMinusDi = smoothedTr !== 0 ? (smoothedMinus / smoothedTr) * 100 : 0;

    const denominator = latestPlusDi + latestMinusDi;

    dxValues.push(
      denominator !== 0
        ? (Math.abs(latestPlusDi - latestMinusDi) / denominator) * 100
        : 0,
    );
  }

  if (dxValues.length < period) {
    return null;
  }

  let adx = mean(dxValues.slice(0, period));

  for (let index = period; index < dxValues.length; index += 1) {
    adx = (adx * (period - 1) + dxValues[index]) / period;
  }

  return {
    value: adx,
    plusDi: latestPlusDi,
    minusDi: latestMinusDi,
  };
}

function calculateStochastic(candles, period = 14, smooth = 3) {
  if (candles.length < period + smooth - 1) {
    return null;
  }

  const kValues = [];

  for (let offset = smooth - 1; offset >= 0; offset -= 1) {
    const end = candles.length - offset;

    const window = candles.slice(end - period, end);

    const high = Math.max(...window.map((candle) => candle.high));

    const low = Math.min(...window.map((candle) => candle.low));

    const close = last(window).close;

    kValues.push(high !== low ? ((close - low) / (high - low)) * 100 : 50);
  }

  return {
    k: last(kValues),
    d: mean(kValues),
  };
}

function calculateVwap(candles, period = 20) {
  const window = latestWindow(candles, period);

  if (!window.length) {
    return null;
  }

  let weightedTotal = 0;
  let volumeTotal = 0;

  window.forEach((candle) => {
    const typicalPrice = (candle.high + candle.low + candle.close) / 3;

    weightedTotal += typicalPrice * candle.volume;

    volumeTotal += candle.volume;
  });

  if (volumeTotal === 0) {
    return null;
  }

  return weightedTotal / volumeTotal;
}

function calculateVolume(candles) {
  if (!candles.length) {
    return null;
  }

  const current = last(candles).volume;

  const previousWindow = candles
    .slice(-21, -1)
    .map((candle) => candle.volume)
    .filter(finite);

  const average = mean(previousWindow);

  return {
    current,
    average,
    ratio: average ? current / average : null,
  };
}

function normalizeCandles(candles) {
  return (Array.isArray(candles) ? candles : [])
    .map((candle) => ({
      time: Number(candle.time),
      open: Number(candle.open),
      high: Number(candle.high),
      low: Number(candle.low),
      close: Number(candle.close),
      volume: Number(candle.volume),
      rawClose: finite(candle.rawClose) ? Number(candle.rawClose) : null,
      adjustedClose: finite(candle.adjustedClose)
        ? Number(candle.adjustedClose)
        : null,
      adjustedCloseProvided: candle.adjustedCloseProvided === true,
      adjustmentFactor: finite(candle.adjustmentFactor)
        ? Number(candle.adjustmentFactor)
        : null,
      volumeAdjustmentFactor: finite(candle.volumeAdjustmentFactor)
        ? Number(candle.volumeAdjustmentFactor)
        : null,
    }))
    .sort((first, second) => first.time - second.time);
}

export function calculateIndicators(
  rawCandles,
  { qualityReport = null, validated = false } = {},
) {
  let report = qualityReport;

  if (!report && !validated) {
    report = validateHistoryData(
      {
        candles: rawCandles,
        adjustmentMethod: "caller-provided",
        meta: {
          volumeUnit: "shares",
        },
      },
      {
        minimumHistory: 2,
      },
    );
  }

  if (report && !report.canScore) {
    throw new DataQualityError(report);
  }

  const candles = normalizeCandles(report?.candles || rawCandles);

  if (candles.length < 2) {
    throw new Error("テクニカル分析に必要な株価履歴が不足しています。");
  }

  const closes = candles.map((candle) => candle.close);

  const current = last(candles);

  const previous = candles[candles.length - 2];

  const yearWindow = candles.slice(-252);

  const high52Week = Math.max(...yearWindow.map((candle) => candle.high));

  const low52Week = Math.min(...yearWindow.map((candle) => candle.low));

  const movingAverages = {
    ma5: calculateSma(closes, 5),
    ma25: calculateSma(closes, 25),
    ma75: calculateSma(closes, 75),
    ma200: calculateSma(closes, 200),
    previousMa5: calculateSma(closes, 5, 1),
    previousMa25: calculateSma(closes, 25, 1),
  };

  const priceChangePercent =
    previous.close !== 0
      ? ((current.close - previous.close) / previous.close) * 100
      : null;

  return {
    candleCount: candles.length,
    currentPrice: current.close,
    previousClose: previous.close,
    priceChangePercent,
    movingAverages,
    ma25Deviation: movingAverages.ma25
      ? ((current.close - movingAverages.ma25) / movingAverages.ma25) * 100
      : null,
    rsi: calculateRsi(closes),
    macd: calculateMacd(closes),
    bollingerBands: calculateBollingerBands(closes),
    volume: calculateVolume(candles),
    adx: calculateAdx(candles),
    atr: calculateAtr(candles),
    stochastic: calculateStochastic(candles),
    vwap: calculateVwap(candles),
    high52Week,
    low52Week,
    distanceFrom52WeekHigh:
      high52Week !== 0
        ? ((current.close - high52Week) / high52Week) * 100
        : null,
    distanceFrom52WeekLow:
      low52Week !== 0 ? ((current.close - low52Week) / low52Week) * 100 : null,
    recentRange: {
      high: Math.max(...candles.slice(-20).map((candle) => candle.high)),
      low: Math.min(...candles.slice(-20).map((candle) => candle.low)),
    },
    calculationAudit: {
      priceBasis: "adjusted-close-scaled-ohlc",
      volumeBasis: "split-adjusted-shares",
      movingAverageBasis: "simple-average-adjusted-close",
      week52Sessions: yearWindow.length,
      vwapBasis: "20-session-daily-typical-price-volume-approximation",
      vwapSessions: Math.min(20, candles.length),
    },
    candles,
  };
}

export const IndicatorMath = {
  calculateSma,
  calculateIndicators,
};
