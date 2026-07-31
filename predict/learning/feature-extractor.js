function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function average(values) {
  const numbers = values.filter(finite).map(Number);

  return numbers.length
    ? numbers.reduce((sum, value) => sum + value, 0) / numbers.length
    : null;
}

function previousSma(candles, period) {
  const closes = (candles || [])
    .slice(-(period + 1), -1)
    .map((candle) => Number(candle.close));

  return closes.length === period ? average(closes) : null;
}

export const FEATURE_DEFINITIONS = Object.freeze({
  rsiBelow30: {
    label: "RSI30以下",
    factorKey: "rsi",
    category: "overheat",
    direction: "bullish",
  },
  rsiAbove70: {
    label: "RSI70以上",
    factorKey: "rsi",
    category: "overheat",
    direction: "bearish",
  },
  macdGoldenCross: {
    label: "MACDゴールデンクロス",
    factorKey: "macd",
    category: "trend",
    direction: "bullish",
  },
  macdDeadCross: {
    label: "MACDデッドクロス",
    factorKey: "macd",
    category: "trend",
    direction: "bearish",
  },
  ma25Bounce: {
    label: "25日線反発",
    factorKey: "movingAverages",
    category: "trend",
    direction: "bullish",
  },
  ma75Breakout: {
    label: "75日線突破",
    factorKey: "movingAverages",
    category: "trend",
    direction: "bullish",
  },
  volumeSurge: {
    label: "出来高急増",
    factorKey: "volume",
    category: "volume",
    direction: "contextual",
  },
  highBreakout: {
    label: "高値更新",
    factorKey: "high52Week",
    category: "relativePosition",
    direction: "bullish",
  },
  lowBreakdown: {
    label: "安値更新",
    factorKey: "low52Week",
    category: "relativePosition",
    direction: "bearish",
  },
});

function createCondition(key, active, value = null, source = "indicator") {
  const definition = FEATURE_DEFINITIONS[key];

  return {
    key,
    ...definition,
    active: Boolean(active),
    value: finite(value) ? Number(value) : value,
    source,
  };
}

function previousRange(candles, accessor, sessions = 252) {
  const values = (candles || [])
    .slice(-(sessions + 1), -1)
    .map(accessor)
    .filter(finite)
    .map(Number);

  if (!values.length) {
    return null;
  }

  return {
    high: Math.max(...values),
    low: Math.min(...values),
  };
}

export function extractPredictionFeatures(indicators = {}) {
  const candles = Array.isArray(indicators.candles)
    ? indicators.candles
    : [];
  const currentCandle = candles.at(-1) || {};
  const previousCandle = candles.at(-2) || {};
  const movingAverages = indicators.movingAverages || {};
  const macd = indicators.macd || {};
  const previousMa25 = movingAverages.previousMa25;
  const previousMa75 = previousSma(candles, 75);
  const priorRange = previousRange(candles, (candle) => candle.high);
  const priorLowRange = previousRange(candles, (candle) => candle.low);
  const ma25 = Number(movingAverages.ma25);
  const currentPrice = Number(indicators.currentPrice);
  const previousPrice = Number(previousCandle.close);
  const touchedMa25 =
    finite(ma25) &&
    finite(currentCandle.low) &&
    (Math.abs(Number(currentCandle.low) - ma25) / ma25 <= 0.015 ||
      (Number(currentCandle.low) <= ma25 && currentPrice >= ma25));

  const conditions = [
    createCondition("rsiBelow30", finite(indicators.rsi) && indicators.rsi <= 30, indicators.rsi),
    createCondition("rsiAbove70", finite(indicators.rsi) && indicators.rsi >= 70, indicators.rsi),
    createCondition(
      "macdGoldenCross",
      finite(macd.previousValue) &&
        finite(macd.previousSignal) &&
        finite(macd.value) &&
        finite(macd.signal) &&
        macd.previousValue <= macd.previousSignal &&
        macd.value > macd.signal,
      macd.histogram,
    ),
    createCondition(
      "macdDeadCross",
      finite(macd.previousValue) &&
        finite(macd.previousSignal) &&
        finite(macd.value) &&
        finite(macd.signal) &&
        macd.previousValue >= macd.previousSignal &&
        macd.value < macd.signal,
      macd.histogram,
    ),
    createCondition(
      "ma25Bounce",
      touchedMa25 &&
        finite(previousPrice) &&
        finite(currentPrice) &&
        currentPrice >= ma25 &&
        currentPrice > previousPrice &&
        (!finite(previousMa25) || previousPrice <= Number(previousMa25) * 1.015),
      indicators.ma25Deviation,
    ),
    createCondition(
      "ma75Breakout",
      finite(previousPrice) &&
        finite(previousMa75) &&
        finite(currentPrice) &&
        finite(movingAverages.ma75) &&
        previousPrice <= Number(previousMa75) &&
        currentPrice > Number(movingAverages.ma75),
      finite(movingAverages.ma75)
        ? ((currentPrice - Number(movingAverages.ma75)) /
            Number(movingAverages.ma75)) *
          100
        : null,
    ),
    createCondition(
      "volumeSurge",
      finite(indicators.volume?.ratio) && indicators.volume.ratio >= 1.5,
      indicators.volume?.ratio,
    ),
    createCondition(
      "highBreakout",
      finite(currentPrice) &&
        finite(priorRange?.high) &&
        currentPrice > priorRange.high,
      finite(priorRange?.high)
        ? ((currentPrice - priorRange.high) / priorRange.high) * 100
        : null,
    ),
    createCondition(
      "lowBreakdown",
      finite(currentPrice) &&
        finite(priorLowRange?.low) &&
        currentPrice < priorLowRange.low,
      finite(priorLowRange?.low)
        ? ((currentPrice - priorLowRange.low) / priorLowRange.low) * 100
        : null,
    ),
  ];

  return {
    schemaVersion: 1,
    capturedAt: Number(currentCandle.time) || null,
    values: {
      rsi: finite(indicators.rsi) ? Number(indicators.rsi) : null,
      macdHistogram: finite(macd.histogram) ? Number(macd.histogram) : null,
      ma25Deviation: finite(indicators.ma25Deviation)
        ? Number(indicators.ma25Deviation)
        : null,
      volumeRatio: finite(indicators.volume?.ratio)
        ? Number(indicators.volume.ratio)
        : null,
      atrPercent: finite(indicators.atr?.percent)
        ? Number(indicators.atr.percent)
        : null,
      adx: finite(indicators.adx?.value)
        ? Number(indicators.adx.value)
        : null,
      stochasticK: finite(indicators.stochastic?.k)
        ? Number(indicators.stochastic.k)
        : null,
      bollingerPercentB: finite(indicators.bollingerBands?.percentB)
        ? Number(indicators.bollingerBands.percentB)
        : null,
      distanceFrom52WeekHigh: finite(indicators.distanceFrom52WeekHigh)
        ? Number(indicators.distanceFrom52WeekHigh)
        : null,
      distanceFrom52WeekLow: finite(indicators.distanceFrom52WeekLow)
        ? Number(indicators.distanceFrom52WeekLow)
        : null,
    },
    conditions,
  };
}

function legacyConditions(record) {
  const reasonText = (record.reasons || []).join(" ");
  const conditions = [];
  const patterns = {
    macdGoldenCross: /ゴールデンクロス/i,
    macdDeadCross: /デッドクロス/i,
    ma25Bounce: /25日線.{0,12}(反発|下げ止)/,
    ma75Breakout: /75日線.{0,12}(突破|上抜)/,
    volumeSurge: /出来高.{0,20}(急増|1\.[5-9]倍|[2-9](?:\.\d+)?倍)/,
    highBreakout: /(高値更新|52週高値.{0,8}(更新|上抜))/,
    lowBreakdown: /(安値更新|52週安値.{0,8}(更新|下抜))/,
  };

  Object.entries(patterns).forEach(([key, pattern]) => {
    if (pattern.test(reasonText)) {
      conditions.push(createCondition(key, true, null, "legacy-reason"));
    }
  });

  const rsiMatch = reasonText.match(/RSI(?:は|が)?\s*([0-9]+(?:\.[0-9]+)?)/i);

  if (rsiMatch) {
    const rsi = Number(rsiMatch[1]);

    if (rsi <= 30) {
      conditions.push(createCondition("rsiBelow30", true, rsi, "legacy-reason"));
    }

    if (rsi >= 70) {
      conditions.push(createCondition("rsiAbove70", true, rsi, "legacy-reason"));
    }
  }

  return conditions;
}

export function activeConditionsForRecord(record) {
  const stored = record?.features?.conditions;

  if (Array.isArray(stored)) {
    return stored.filter((condition) => condition.active);
  }

  return legacyConditions(record || {});
}

export const FeatureExtractorInternals = {
  previousSma,
  previousRange,
  legacyConditions,
};
