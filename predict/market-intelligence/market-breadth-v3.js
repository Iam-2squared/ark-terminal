export const MARKET_BREADTH_V3_VERSION =
  "market-breadth-v3";

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function finiteNumber(
  value,
  fallback = 0,
) {
  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
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
      "Market breadth timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function normalizeStock(
  stock = {},
) {
  return {
    symbol:
      String(
        stock.symbol ??
        "UNKNOWN",
      ).trim() ||
      "UNKNOWN",

    changePercent:
      finiteNumber(
        stock.changePercent,
        0,
      ),

    volumeRatio:
      Math.max(
        0,
        finiteNumber(
          stock.volumeRatio,
          1,
        ),
      ),

    aboveSma25:
      stock.aboveSma25 ===
      true,

    aboveSma75:
      stock.aboveSma75 ===
      true,

    newHigh:
      stock.newHigh ===
      true,

    newLow:
      stock.newLow ===
      true,

    limitUp:
      stock.limitUp ===
      true,

    limitDown:
      stock.limitDown ===
      true,

    marketCapWeight:
      Math.max(
        0,
        finiteNumber(
          stock.marketCapWeight,
          1,
        ),
      ),
  };
}

function classifyBreadth({
  score,
  advanceDeclineRatio,
  participationRate,
}) {
  if (
    score >= 70 &&
    advanceDeclineRatio >= 2 &&
    participationRate >= 65
  ) {
    return "VERY_STRONG";
  }

  if (score >= 35) {
    return "STRONG";
  }

  if (score >= 10) {
    return "POSITIVE";
  }

  if (score <= -70) {
    return "CAPITULATION";
  }

  if (score <= -35) {
    return "WEAK";
  }

  if (score <= -10) {
    return "NEGATIVE";
  }

  return "NEUTRAL";
}

function detectDivergence({
  indexChangePercent,
  breadthScore,
}) {
  if (
    indexChangePercent >= 1 &&
    breadthScore <= -10
  ) {
    return {
      detected:
        true,

      type:
        "BEARISH_DIVERGENCE",

      message:
        "Index is rising while market breadth is weakening.",
    };
  }

  if (
    indexChangePercent <= -1 &&
    breadthScore >= 10
  ) {
    return {
      detected:
        true,

      type:
        "BULLISH_DIVERGENCE",

      message:
        "Index is falling while market breadth is improving.",
    };
  }

  return {
    detected:
      false,

    type:
      "NONE",

    message:
      "No material index-breadth divergence.",
  };
}

export function calculateAdvanceDecline({
  stocks = [],
} = {}) {
  const normalized =
    stocks.map(
      normalizeStock,
    );

  let advancing = 0;
  let declining = 0;
  let unchanged = 0;
  let weightedAdvance = 0;
  let weightedDecline = 0;

  for (const stock of normalized) {
    if (stock.changePercent > 0) {
      advancing += 1;

      weightedAdvance +=
        stock.marketCapWeight *
        stock.changePercent;
    }
    else if (
      stock.changePercent < 0
    ) {
      declining += 1;

      weightedDecline +=
        stock.marketCapWeight *
        Math.abs(
          stock.changePercent,
        );
    }
    else {
      unchanged += 1;
    }
  }

  const ratio =
    declining === 0
      ? advancing > 0
        ? advancing
        : 1
      : advancing /
        declining;

  return {
    total:
      normalized.length,

    advancing,

    declining,

    unchanged,

    ratio:
      round(
        ratio,
        4,
      ),

    netAdvances:
      advancing -
      declining,

    weightedNet:
      round(
        weightedAdvance -
        weightedDecline,
      ),
  };
}

export function calculateBreadthIndicators({
  stocks = [],
} = {}) {
  const normalized =
    stocks.map(
      normalizeStock,
    );

  if (
    normalized.length ===
    0
  ) {
    return {
      sampleSize:
        0,

      aboveSma25Percent:
        0,

      aboveSma75Percent:
        0,

      newHighLowNet:
        0,

      upVolumePercent:
        0,

      participationRate:
        0,

      extremeMoveBalance:
        0,
    };
  }

  let aboveSma25 = 0;
  let aboveSma75 = 0;
  let newHighs = 0;
  let newLows = 0;
  let upVolume = 0;
  let downVolume = 0;
  let active = 0;
  let limitUps = 0;
  let limitDowns = 0;

  for (const stock of normalized) {
    if (stock.aboveSma25) {
      aboveSma25 += 1;
    }

    if (stock.aboveSma75) {
      aboveSma75 += 1;
    }

    if (stock.newHigh) {
      newHighs += 1;
    }

    if (stock.newLow) {
      newLows += 1;
    }

    if (
      Math.abs(
        stock.changePercent,
      ) >= 0.3
    ) {
      active += 1;
    }

    if (stock.changePercent > 0) {
      upVolume +=
        stock.volumeRatio;
    }
    else if (
      stock.changePercent < 0
    ) {
      downVolume +=
        stock.volumeRatio;
    }

    if (stock.limitUp) {
      limitUps += 1;
    }

    if (stock.limitDown) {
      limitDowns += 1;
    }
  }

  const totalVolume =
    upVolume +
    downVolume;

  return {
    sampleSize:
      normalized.length,

    aboveSma25Percent:
      round(
        (
          aboveSma25 /
          normalized.length
        ) *
        100,
      ),

    aboveSma75Percent:
      round(
        (
          aboveSma75 /
          normalized.length
        ) *
        100,
      ),

    newHighLowNet:
      newHighs -
      newLows,

    newHighs,

    newLows,

    upVolumePercent:
      totalVolume === 0
        ? 50
        : round(
            (
              upVolume /
              totalVolume
            ) *
            100,
          ),

    participationRate:
      round(
        (
          active /
          normalized.length
        ) *
        100,
      ),

    extremeMoveBalance:
      limitUps -
      limitDowns,

    limitUps,

    limitDowns,
  };
}

export function analyzeMarketBreadth({
  stocks = [],
  indexChangePercent = 0,
  timestamp =
    new Date().toISOString(),
  minimumSampleSize = 5,
} = {}) {
  const evaluatedAt =
    normalizeTimestamp(
      timestamp,
    );

  const normalized =
    stocks.map(
      normalizeStock,
    );

  const advanceDecline =
    calculateAdvanceDecline({
      stocks:
        normalized,
    });

  const indicators =
    calculateBreadthIndicators({
      stocks:
        normalized,
    });

  if (
    normalized.length <
    minimumSampleSize
  ) {
    return {
      version:
        MARKET_BREADTH_V3_VERSION,

      evaluatedAt,

      status:
        "INSUFFICIENT_DATA",

      score:
        0,

      classification:
        "UNKNOWN",

      confidence:
        0,

      advanceDecline,

      indicators,

      divergence: {
        detected:
          false,

        type:
          "NONE",

        message:
          "Insufficient data for divergence analysis.",
      },

      recommendation:
        "WAIT_FOR_MORE_DATA",
    };
  }

  const advanceDeclineScore =
    clamp(
      advanceDecline.netAdvances /
      normalized.length *
      100,
      -100,
      100,
    );

  const trendParticipationScore =
    (
      indicators
        .aboveSma25Percent -
      50
    ) *
    1.2;

  const longTrendScore =
    (
      indicators
        .aboveSma75Percent -
      50
    ) *
    0.8;

  const volumeScore =
    (
      indicators
        .upVolumePercent -
      50
    ) *
    1.1;

  const highLowScore =
    clamp(
      indicators.newHighLowNet /
      normalized.length *
      150,
      -40,
      40,
    );

  const extremeScore =
    clamp(
      indicators.extremeMoveBalance /
      normalized.length *
      100,
      -25,
      25,
    );

  const breadthScore =
    clamp(
      advanceDeclineScore *
        0.3 +
      trendParticipationScore *
        0.25 +
      longTrendScore *
        0.15 +
      volumeScore *
        0.15 +
      highLowScore *
        0.1 +
      extremeScore *
        0.05,
      -100,
      100,
    );

  const classification =
    classifyBreadth({
      score:
        breadthScore,

      advanceDeclineRatio:
        advanceDecline.ratio,

      participationRate:
        indicators
          .participationRate,
    });

  const divergence =
    detectDivergence({
      indexChangePercent:
        finiteNumber(
          indexChangePercent,
          0,
        ),

      breadthScore,
    });

  const confidence =
    clamp(
      40 +
      Math.min(
        35,
        normalized.length /
        5,
      ) +
      Math.min(
        25,
        indicators
          .participationRate /
        4,
      ),
      0,
      100,
    );

  let recommendation =
    "NEUTRAL";

  if (
    classification ===
      "VERY_STRONG" ||
    classification ===
      "STRONG"
  ) {
    recommendation =
      "RISK_ON";
  }
  else if (
    classification ===
      "WEAK" ||
    classification ===
      "CAPITULATION"
  ) {
    recommendation =
      "RISK_OFF";
  }
  else if (
    classification ===
      "POSITIVE"
  ) {
    recommendation =
      "CAUTIOUS_RISK_ON";
  }
  else if (
    classification ===
      "NEGATIVE"
  ) {
    recommendation =
      "REDUCE_EXPOSURE";
  }

  if (
    divergence.type ===
    "BEARISH_DIVERGENCE"
  ) {
    recommendation =
      "REDUCE_EXPOSURE";
  }

  if (
    divergence.type ===
    "BULLISH_DIVERGENCE"
  ) {
    recommendation =
      "WATCH_FOR_REVERSAL";
  }

  return {
    version:
      MARKET_BREADTH_V3_VERSION,

    evaluatedAt,

    status:
      "READY",

    score:
      round(
        breadthScore,
      ),

    classification,

    confidence:
      round(
        confidence,
      ),

    advanceDecline,

    indicators,

    components: {
      advanceDeclineScore:
        round(
          advanceDeclineScore,
        ),

      trendParticipationScore:
        round(
          trendParticipationScore,
        ),

      longTrendScore:
        round(
          longTrendScore,
        ),

      volumeScore:
        round(
          volumeScore,
        ),

      highLowScore:
        round(
          highLowScore,
        ),

      extremeScore:
        round(
          extremeScore,
        ),
    },

    divergence,

    recommendation,
  };
}

export function analyzeBreadthHistory({
  history = [],
} = {}) {
  const valid =
    history.filter(
      (
        entry,
      ) =>
        Number.isFinite(
          Number(
            entry?.score,
          ),
        ),
    );

  if (
    valid.length ===
    0
  ) {
    return {
      trend:
        "UNKNOWN",

      momentum:
        0,

      latestScore:
        null,

      averageScore:
        null,

      improving:
        false,
    };
  }

  const scores =
    valid.map(
      (
        entry,
      ) =>
        Number(
          entry.score,
        ),
    );

  const latestScore =
    scores.at(-1);

  const averageScore =
    scores.reduce(
      (
        total,
        score,
      ) =>
        total +
        score,
      0,
    ) /
    scores.length;

  const momentum =
    scores.length >= 2
      ? latestScore -
        scores[
          scores.length -
          2
        ]
      : 0;

  return {
    trend:
      momentum > 5
        ? "IMPROVING"
        : momentum < -5
          ? "DETERIORATING"
          : "STABLE",

    momentum:
      round(
        momentum,
      ),

    latestScore:
      round(
        latestScore,
      ),

    averageScore:
      round(
        averageScore,
      ),

    improving:
      momentum >
      0,
  };
}

export class MarketBreadthV3 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  analyze(input = {}) {
    const result =
      analyzeMarketBreadth({
        ...this.config,
        ...input,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
  }

  analyzeHistory() {
    return analyzeBreadthHistory({
      history:
        this.history,
    });
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

export const marketBreadthV3 =
  new MarketBreadthV3();

export default analyzeMarketBreadth;