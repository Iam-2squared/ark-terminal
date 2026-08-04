export const MARKET_REGIME_INTELLIGENCE_V3_VERSION =
  "market-regime-intelligence-v3";

const VALID_REGIMES =
  new Set([
    "STRONG_BULL",
    "BULL",
    "RANGE",
    "BEAR",
    "STRONG_BEAR",
    "HIGH_VOLATILITY",
    "CRASH",
    "INSUFFICIENT_DATA",
  ]);

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function finiteOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function clamp(
  value,
  minimum,
  maximum,
) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      value,
    ),
  );
}

function round(
  value,
  digits = 2,
) {
  if (!Number.isFinite(value)) {
    return null;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value *
      factor,
    ) /
    factor
  );
}

function normalizeTimestamp(value) {
  const milliseconds =
    typeof value === "number"
      ? value
      : Date.parse(
          value ??
          new Date().toISOString(),
        );

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(
      "Market regime timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function normalizeText(
  value,
  fallback = "",
) {
  const text =
    String(
      value ??
      fallback,
    ).trim();

  return text || fallback;
}

function normalizeInput(
  input = {},
) {
  const price =
    finiteOrNull(
      input.price ??
      input.close,
    );

  const changePercent =
    finiteOrNull(
      input.changePercent ??
      input.returnPercent,
    );

  const sma5 =
    finiteOrNull(
      input.sma5,
    );

  const sma25 =
    finiteOrNull(
      input.sma25,
    );

  const sma75 =
    finiteOrNull(
      input.sma75,
    );

  const rsi =
    finiteOrNull(
      input.rsi,
    );

  const macd =
    finiteOrNull(
      input.macd,
    );

  const macdSignal =
    finiteOrNull(
      input.macdSignal,
    );

  const adx =
    finiteOrNull(
      input.adx,
    );

  const atrPercent =
    finiteOrNull(
      input.atrPercent ??
      input.atrRatio,
    );

  const volatility =
    finiteOrNull(
      input.volatility,
    );

  const volumeRatio =
    finiteOrNull(
      input.volumeRatio,
    );

  const breadth =
    finiteOrNull(
      input.marketBreadth,
    );

  const drawdownPercent =
    finiteOrNull(
      input.drawdownPercent,
    );

  const indexTrendScore =
    finiteOrNull(
      input.indexTrendScore,
    );

  return {
    symbol:
      normalizeText(
        input.symbol,
        "MARKET",
      ),

    timestamp:
      normalizeTimestamp(
        input.timestamp,
      ),

    price,

    changePercent,

    sma5,

    sma25,

    sma75,

    rsi,

    macd,

    macdSignal,

    adx,

    atrPercent,

    volatility,

    volumeRatio,

    marketBreadth:
      breadth,

    drawdownPercent,

    indexTrendScore,
  };
}

function scoreTrend(input) {
  let score = 0;
  const reasons = [];

  if (
    input.price !== null &&
    input.sma25 !== null
  ) {
    if (
      input.price >
      input.sma25
    ) {
      score += 15;
      reasons.push(
        "PRICE_ABOVE_SMA25",
      );
    }
    else {
      score -= 15;
      reasons.push(
        "PRICE_BELOW_SMA25",
      );
    }
  }

  if (
    input.sma5 !== null &&
    input.sma25 !== null
  ) {
    if (
      input.sma5 >
      input.sma25
    ) {
      score += 15;
      reasons.push(
        "SMA5_ABOVE_SMA25",
      );
    }
    else {
      score -= 15;
      reasons.push(
        "SMA5_BELOW_SMA25",
      );
    }
  }

  if (
    input.sma25 !== null &&
    input.sma75 !== null
  ) {
    if (
      input.sma25 >
      input.sma75
    ) {
      score += 20;
      reasons.push(
        "SMA25_ABOVE_SMA75",
      );
    }
    else {
      score -= 20;
      reasons.push(
        "SMA25_BELOW_SMA75",
      );
    }
  }

  if (
    input.macd !== null &&
    input.macdSignal !== null
  ) {
    if (
      input.macd >
      input.macdSignal
    ) {
      score += 10;
      reasons.push(
        "MACD_BULLISH",
      );
    }
    else {
      score -= 10;
      reasons.push(
        "MACD_BEARISH",
      );
    }
  }

  if (
    input.indexTrendScore !==
    null
  ) {
    score +=
      clamp(
        input.indexTrendScore,
        -20,
        20,
      );

    reasons.push(
      input.indexTrendScore >=
      0
        ? "INDEX_TREND_POSITIVE"
        : "INDEX_TREND_NEGATIVE",
    );
  }

  return {
    score:
      clamp(
        score,
        -100,
        100,
      ),

    reasons,
  };
}

function scoreMomentum(input) {
  let score = 0;
  const reasons = [];

  if (
    input.rsi !== null
  ) {
    if (
      input.rsi >= 55 &&
      input.rsi <= 75
    ) {
      score += 15;
      reasons.push(
        "RSI_BULLISH",
      );
    }
    else if (
      input.rsi >
      75
    ) {
      score += 5;
      reasons.push(
        "RSI_OVERBOUGHT",
      );
    }
    else if (
      input.rsi <= 45 &&
      input.rsi >= 25
    ) {
      score -= 15;
      reasons.push(
        "RSI_BEARISH",
      );
    }
    else if (
      input.rsi <
      25
    ) {
      score -= 5;
      reasons.push(
        "RSI_OVERSOLD",
      );
    }
  }

  if (
    input.changePercent !==
    null
  ) {
    score +=
      clamp(
        input.changePercent *
        4,
        -20,
        20,
      );

    reasons.push(
      input.changePercent >=
      0
        ? "RETURN_POSITIVE"
        : "RETURN_NEGATIVE",
    );
  }

  if (
    input.marketBreadth !==
    null
  ) {
    score +=
      clamp(
        input.marketBreadth /
        5,
        -20,
        20,
      );

    reasons.push(
      input.marketBreadth >=
      0
        ? "BREADTH_POSITIVE"
        : "BREADTH_NEGATIVE",
    );
  }

  return {
    score:
      clamp(
        score,
        -100,
        100,
      ),

    reasons,
  };
}

function scoreRisk(input) {
  let score = 0;
  const reasons = [];

  const volatility =
    input.atrPercent ??
    input.volatility;

  if (
    volatility !== null
  ) {
    if (
      volatility >= 8
    ) {
      score += 50;
      reasons.push(
        "EXTREME_VOLATILITY",
      );
    }
    else if (
      volatility >= 5
    ) {
      score += 30;
      reasons.push(
        "HIGH_VOLATILITY",
      );
    }
    else if (
      volatility >= 3
    ) {
      score += 15;
      reasons.push(
        "ELEVATED_VOLATILITY",
      );
    }
    else {
      reasons.push(
        "NORMAL_VOLATILITY",
      );
    }
  }

  if (
    input.drawdownPercent !==
    null
  ) {
    const drawdown =
      Math.abs(
        input.drawdownPercent,
      );

    score +=
      clamp(
        drawdown *
        2,
        0,
        40,
      );

    if (
      drawdown >= 10
    ) {
      reasons.push(
        "LARGE_DRAWDOWN",
      );
    }
  }

  if (
    input.volumeRatio !==
      null &&
    input.volumeRatio >=
      2
  ) {
    score += 10;
    reasons.push(
      "VOLUME_SHOCK",
    );
  }

  return {
    score:
      clamp(
        score,
        0,
        100,
      ),

    reasons,
  };
}

function classifyRegime({
  trendScore,
  momentumScore,
  riskScore,
  input,
}) {
  const combined =
    trendScore *
      0.65 +
    momentumScore *
      0.35;

  const volatility =
    input.atrPercent ??
    input.volatility;

  const drawdown =
    Math.abs(
      input.drawdownPercent ??
      0,
    );

  if (
    riskScore >= 80 ||
    drawdown >= 15 ||
    (
      input.changePercent !==
        null &&
      input.changePercent <=
        -8
    )
  ) {
    return {
      regime:
        "CRASH",

      combinedScore:
        combined,
    };
  }

  if (
    volatility !== null &&
    volatility >= 7
  ) {
    return {
      regime:
        "HIGH_VOLATILITY",

      combinedScore:
        combined,
    };
  }

  if (
    combined >= 55
  ) {
    return {
      regime:
        "STRONG_BULL",

      combinedScore:
        combined,
    };
  }

  if (
    combined >= 20
  ) {
    return {
      regime:
        "BULL",

      combinedScore:
        combined,
    };
  }

  if (
    combined <= -55
  ) {
    return {
      regime:
        "STRONG_BEAR",

      combinedScore:
        combined,
    };
  }

  if (
    combined <= -20
  ) {
    return {
      regime:
        "BEAR",

      combinedScore:
        combined,
    };
  }

  return {
    regime:
      "RANGE",

    combinedScore:
      combined,
  };
}

function calculateConfidence({
  input,
  trendScore,
  momentumScore,
  riskScore,
}) {
  const available = [
    input.price,
    input.sma5,
    input.sma25,
    input.sma75,
    input.rsi,
    input.macd,
    input.macdSignal,
    input.adx,
    input.atrPercent,
    input.volatility,
    input.marketBreadth,
    input.indexTrendScore,
  ].filter(
    (
      value,
    ) =>
      value !== null,
  ).length;

  const completeness =
    available /
    12;

  const agreement =
    Math.sign(
      trendScore,
    ) ===
    Math.sign(
      momentumScore,
    )
      ? 1
      : 0.65;

  const strength =
    Math.min(
      1,
      (
        Math.abs(
          trendScore,
        ) +
        Math.abs(
          momentumScore,
        )
      ) /
      120,
    );

  const riskPenalty =
    Math.min(
      0.35,
      riskScore /
      250,
    );

  return round(
    clamp(
      (
        completeness *
          0.45 +
        agreement *
          0.25 +
        strength *
          0.30 -
        riskPenalty
      ) *
      100,
      0,
      100,
    ),
  );
}

function strategyForRegime(
  regime,
) {
  const strategies = {
    STRONG_BULL: {
      bias:
        "LONG",

      positionMultiplier:
        1,

      preferredStrategy:
        "TREND_FOLLOWING",

      entryMode:
        "BUY_PULLBACK_OR_BREAKOUT",

      riskLevel:
        "NORMAL",
    },

    BULL: {
      bias:
        "LONG",

      positionMultiplier:
        0.8,

      preferredStrategy:
        "TREND_FOLLOWING",

      entryMode:
        "BUY_PULLBACK",

      riskLevel:
        "NORMAL",
    },

    RANGE: {
      bias:
        "NEUTRAL",

      positionMultiplier:
        0.5,

      preferredStrategy:
        "MEAN_REVERSION",

      entryMode:
        "WAIT_FOR_RANGE_EDGE",

      riskLevel:
        "CAUTIOUS",
    },

    BEAR: {
      bias:
        "DEFENSIVE",

      positionMultiplier:
        0.35,

      preferredStrategy:
        "CAPITAL_PRESERVATION",

      entryMode:
        "WAIT_OR_REDUCE",

      riskLevel:
        "HIGH",
    },

    STRONG_BEAR: {
      bias:
        "DEFENSIVE",

      positionMultiplier:
        0.15,

      preferredStrategy:
        "CAPITAL_PRESERVATION",

      entryMode:
        "AVOID_NEW_LONGS",

      riskLevel:
        "VERY_HIGH",
    },

    HIGH_VOLATILITY: {
      bias:
        "NEUTRAL",

      positionMultiplier:
        0.2,

      preferredStrategy:
        "VOLATILITY_CONTROL",

      entryMode:
        "WAIT_FOR_STABILIZATION",

      riskLevel:
        "VERY_HIGH",
    },

    CRASH: {
      bias:
        "RISK_OFF",

      positionMultiplier:
        0,

      preferredStrategy:
        "CAPITAL_PRESERVATION",

      entryMode:
        "BLOCK_NEW_TRADES",

      riskLevel:
        "CRITICAL",
    },

    INSUFFICIENT_DATA: {
      bias:
        "UNKNOWN",

      positionMultiplier:
        0,

      preferredStrategy:
        "NONE",

      entryMode:
        "WAIT_FOR_DATA",

      riskLevel:
        "UNKNOWN",
    },
  };

  return clone(
    strategies[
      regime
    ],
  );
}

export function detectMarketRegime({
  input = {},
} = {}) {
  const normalized =
    normalizeInput(
      input,
    );

  const minimumData = [
    normalized.price,
    normalized.sma25,
    normalized.rsi,
  ].filter(
    (
      value,
    ) =>
      value !== null,
  ).length;

  if (
    minimumData <
    2
  ) {
    return {
      version:
        MARKET_REGIME_INTELLIGENCE_V3_VERSION,

      symbol:
        normalized.symbol,

      timestamp:
        normalized.timestamp,

      regime:
        "INSUFFICIENT_DATA",

      confidence:
        0,

      scores: {
        trend:
          0,

        momentum:
          0,

        risk:
          0,

        combined:
          0,
      },

      strategy:
        strategyForRegime(
          "INSUFFICIENT_DATA",
        ),

      reasons: [
        "INSUFFICIENT_MARKET_DATA",
      ],

      input:
        normalized,
    };
  }

  const trend =
    scoreTrend(
      normalized,
    );

  const momentum =
    scoreMomentum(
      normalized,
    );

  const risk =
    scoreRisk(
      normalized,
    );

  const classification =
    classifyRegime({
      trendScore:
        trend.score,

      momentumScore:
        momentum.score,

      riskScore:
        risk.score,

      input:
        normalized,
    });

  if (
    !VALID_REGIMES.has(
      classification.regime,
    )
  ) {
    throw new Error(
      `Unsupported market regime: ${classification.regime}`,
    );
  }

  const confidence =
    calculateConfidence({
      input:
        normalized,

      trendScore:
        trend.score,

      momentumScore:
        momentum.score,

      riskScore:
        risk.score,
    });

  return {
    version:
      MARKET_REGIME_INTELLIGENCE_V3_VERSION,

    symbol:
      normalized.symbol,

    timestamp:
      normalized.timestamp,

    regime:
      classification.regime,

    confidence,

    scores: {
      trend:
        round(
          trend.score,
        ),

      momentum:
        round(
          momentum.score,
        ),

      risk:
        round(
          risk.score,
        ),

      combined:
        round(
          classification
            .combinedScore,
        ),
    },

    strategy:
      strategyForRegime(
        classification.regime,
      ),

    reasons: [
      ...new Set([
        ...trend.reasons,
        ...momentum.reasons,
        ...risk.reasons,
      ]),
    ],

    input:
      normalized,
  };
}

export function detectMultiMarketRegime({
  markets = [],
  minimumConfidence = 30,
} = {}) {
  const results =
    markets.map(
      (
        market,
      ) =>
        detectMarketRegime({
          input:
            market,
        }),
    );

  const eligible =
    results.filter(
      (
        result,
      ) =>
        result.regime !==
          "INSUFFICIENT_DATA" &&
        result.confidence >=
          minimumConfidence,
    );

  if (
    eligible.length ===
    0
  ) {
    return {
      version:
        MARKET_REGIME_INTELLIGENCE_V3_VERSION,

      regime:
        "INSUFFICIENT_DATA",

      confidence:
        0,

      consensusScore:
        0,

      markets:
        results,
    };
  }

  const regimeValues = {
    STRONG_BULL:
      2,

    BULL:
      1,

    RANGE:
      0,

    BEAR:
      -1,

    STRONG_BEAR:
      -2,

    HIGH_VOLATILITY:
      -0.5,

    CRASH:
      -3,
  };

  let weightedTotal = 0;
  let totalWeight = 0;

  for (
    const result of eligible
  ) {
    const weight =
      Math.max(
        0.01,
        result.confidence /
        100,
      );

    weightedTotal +=
      (
        regimeValues[
          result.regime
        ] ??
        0
      ) *
      weight;

    totalWeight +=
      weight;
  }

  const consensus =
    weightedTotal /
    totalWeight;

  let regime =
    "RANGE";

  if (
    consensus >= 1.4
  ) {
    regime =
      "STRONG_BULL";
  }
  else if (
    consensus >= 0.45
  ) {
    regime =
      "BULL";
  }
  else if (
    consensus <= -2.2
  ) {
    regime =
      "CRASH";
  }
  else if (
    consensus <= -1.4
  ) {
    regime =
      "STRONG_BEAR";
  }
  else if (
    consensus <= -0.45
  ) {
    regime =
      "BEAR";
  }

  const confidence =
    round(
      eligible.reduce(
        (
          total,
          result,
        ) =>
          total +
          result.confidence,
        0,
      ) /
      eligible.length,
    );

  return {
    version:
      MARKET_REGIME_INTELLIGENCE_V3_VERSION,

    regime,

    confidence,

    consensusScore:
      round(
        consensus,
        4,
      ),

    strategy:
      strategyForRegime(
        regime,
      ),

    markets:
      results,
  };
}

export class MarketRegimeIntelligenceV3 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  detect(input = {}) {
    const result =
      detectMarketRegime({
        ...this.config,
        input,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
  }

  detectMulti(
    markets = [],
    options = {},
  ) {
    const result =
      detectMultiMarketRegime({
        markets,
        ...options,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
  }

  getHistory() {
    return clone(
      this.history,
    );
  }

  latest() {
    return clone(
      this.history.at(-1) ??
      null,
    );
  }

  reset() {
    this.history = [];

    return [];
  }
}

export const marketRegimeIntelligenceV3 =
  new MarketRegimeIntelligenceV3();

export default detectMarketRegime;