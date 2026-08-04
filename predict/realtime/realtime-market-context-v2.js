export const REALTIME_MARKET_CONTEXT_V2_VERSION =
  "realtime-market-context-v2";

function finiteOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function clamp(
  value,
  minimum = 0,
  maximum = 100,
) {
  const number =
    finiteOrNull(value);

  if (number === null) {
    return null;
  }

  return Math.min(
    maximum,
    Math.max(
      minimum,
      number,
    ),
  );
}

function round(
  value,
  digits = 4,
) {
  if (!Number.isFinite(value)) {
    return value;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value * factor,
    ) / factor
  );
}

function average(values) {
  const available =
    values.filter(
      Number.isFinite,
    );

  if (!available.length) {
    return null;
  }

  return (
    available.reduce(
      (
        sum,
        value,
      ) =>
        sum + value,
      0,
    ) /
    available.length
  );
}

function normalizeTimestamp(
  value,
  now,
) {
  const raw =
    value ??
    now();

  const parsed =
    typeof raw === "number"
      ? raw
      : Date.parse(raw);

  if (!Number.isFinite(parsed)) {
    throw new TypeError(
      "Realtime market context timestamp is invalid.",
    );
  }

  return parsed;
}

function normalizeIndex(
  index,
  position,
  now,
) {
  if (
    !index ||
    typeof index !== "object"
  ) {
    return null;
  }

  const symbol =
    String(
      index.symbol ??
      index.code ??
      index.name ??
      `INDEX-${position + 1}`,
    ).trim();

  const changePercent =
    finiteOrNull(
      index.changePercent ??
      index.change ??
      index.return,
    );

  const score =
    clamp(
      index.score ??
      (
        changePercent === null
          ? 50
          : 50 +
            changePercent *
            8
      ),
    ) ?? 50;

  return {
    symbol,

    changePercent:
      changePercent === null
        ? null
        : round(
            changePercent,
          ),

    score:
      round(
        score,
        2,
      ),

    timestamp:
      normalizeTimestamp(
        index.timestamp ??
        index.updatedAt,
        now,
      ),
  };
}

function normalizeBreadth(
  breadth = {},
) {
  const advancing =
    finiteOrNull(
      breadth.advancing,
    );

  const declining =
    finiteOrNull(
      breadth.declining,
    );

  const unchanged =
    finiteOrNull(
      breadth.unchanged,
    ) ?? 0;

  const total =
    (
      advancing ??
      0
    ) +
    (
      declining ??
      0
    ) +
    unchanged;

  const advanceRatio =
    total > 0
      ? (
          (
            advancing ??
            0
          ) /
          total
        ) *
        100
      : null;

  const score =
    clamp(
      breadth.score ??
      advanceRatio ??
      50,
    ) ?? 50;

  return {
    advancing,
    declining,
    unchanged,
    total,

    advanceRatio:
      advanceRatio === null
        ? null
        : round(
            advanceRatio,
            2,
          ),

    score:
      round(
        score,
        2,
      ),
  };
}

function normalizeVolatility(
  volatility = {},
) {
  const value =
    finiteOrNull(
      volatility.value ??
      volatility.vix ??
      volatility.index,
    );

  const changePercent =
    finiteOrNull(
      volatility.changePercent ??
      volatility.change,
    );

  let score =
    finiteOrNull(
      volatility.score,
    );

  if (score === null) {
    if (value === null) {
      score = 50;
    } else if (value <= 15) {
      score = 80;
    } else if (value <= 22) {
      score = 65;
    } else if (value <= 30) {
      score = 45;
    } else {
      score = 20;
    }
  }

  return {
    value,

    changePercent:
      changePercent === null
        ? null
        : round(
            changePercent,
          ),

    score:
      round(
        clamp(score) ?? 50,
        2,
      ),
  };
}

function normalizeLiquidity(
  liquidity = {},
) {
  const turnover =
    finiteOrNull(
      liquidity.turnover ??
      liquidity.value,
    );

  const relativeVolume =
    finiteOrNull(
      liquidity.relativeVolume ??
      liquidity.rvol,
    );

  const score =
    clamp(
      liquidity.score ??
      (
        relativeVolume === null
          ? 50
          : 50 +
            (
              relativeVolume -
              1
            ) *
            25
      ),
    ) ?? 50;

  return {
    turnover,

    relativeVolume,

    score:
      round(
        score,
        2,
      ),
  };
}

function normalizeNews(
  news = {},
) {
  const sentiment =
    finiteOrNull(
      news.sentiment ??
      news.score,
    );

  const articleCount =
    Math.max(
      0,
      Math.floor(
        finiteOrNull(
          news.articleCount ??
          news.count,
        ) ?? 0,
      ),
    );

  const confidence =
    clamp(
      news.confidence ??
      (
        articleCount > 0
          ? Math.min(
              100,
              40 +
              articleCount *
              5
            )
          : 0
      ),
    ) ?? 0;

  return {
    sentiment:
      sentiment === null
        ? null
        : round(
            clamp(
              sentiment,
              -100,
              100,
            ),
            2,
          ),

    articleCount,

    confidence:
      round(
        confidence,
        2,
      ),
  };
}

function freshnessStatus({
  timestamp,
  nowTimestamp,
  staleAfterSeconds,
}) {
  const ageSeconds =
    Math.max(
      0,
      (
        nowTimestamp -
        timestamp
      ) /
      1000,
    );

  return {
    ageSeconds:
      round(
        ageSeconds,
        2,
      ),

    stale:
      ageSeconds >
      staleAfterSeconds,
  };
}

function calculateCompositeScore({
  indices,
  breadth,
  volatility,
  liquidity,
  news,
}) {
  const indexScore =
    average(
      indices.map(
        (
          index,
        ) =>
          index.score,
      ),
    );

  const components = [
    {
      name:
        "indices",

      score:
        indexScore,

      weight:
        0.3,
    },

    {
      name:
        "breadth",

      score:
        breadth.score,

      weight:
        0.25,
    },

    {
      name:
        "volatility",

      score:
        volatility.score,

      weight:
        0.2,
    },

    {
      name:
        "liquidity",

      score:
        liquidity.score,

      weight:
        0.15,
    },

    {
      name:
        "news",

      score:
        news.sentiment === null
          ? null
          : clamp(
              50 +
              news.sentiment /
              2,
            ),

      weight:
        0.1,
    },
  ];

  const available =
    components.filter(
      (
        component,
      ) =>
        Number.isFinite(
          component.score,
        ),
    );

  const totalWeight =
    available.reduce(
      (
        sum,
        component,
      ) =>
        sum +
        component.weight,
      0,
    );

  const score =
    totalWeight > 0
      ? available.reduce(
          (
            sum,
            component,
          ) =>
            sum +
            component.score *
            component.weight,
          0,
        ) /
        totalWeight
      : null;

  return {
    score:
      score === null
        ? null
        : round(
            clamp(score),
            2,
          ),

    components:
      components.map(
        (
          component,
        ) => ({
          ...component,

          score:
            component.score === null
              ? null
              : round(
                  component.score,
                  2,
                ),
        }),
      ),
  };
}

function marketRegime({
  score,
  volatility,
  breadth,
}) {
  if (score === null) {
    return "UNKNOWN";
  }

  if (
    volatility.value !== null &&
    volatility.value >= 30
  ) {
    return "HIGH_VOLATILITY";
  }

  if (
    score >= 68 &&
    (
      breadth.advanceRatio ??
      50
    ) >= 55
  ) {
    return "RISK_ON";
  }

  if (
    score <= 35 ||
    (
      breadth.advanceRatio ??
      50
    ) <= 35
  ) {
    return "RISK_OFF";
  }

  return "NEUTRAL";
}

function buildRecommendation({
  regime,
  score,
  staleSourceCount,
}) {
  if (
    staleSourceCount > 0
  ) {
    return {
      action:
        "REFRESH",

      riskMultiplier:
        0,

      reason:
        "ONE_OR_MORE_CONTEXT_SOURCES_ARE_STALE",
    };
  }

  if (
    regime === "RISK_ON"
  ) {
    return {
      action:
        "ALLOW_LONG_BIAS",

      riskMultiplier:
        1,

      reason:
        "MARKET_CONTEXT_SUPPORTS_RISK_TAKING",
    };
  }

  if (
    regime === "RISK_OFF"
  ) {
    return {
      action:
        "REDUCE_RISK",

      riskMultiplier:
        0.5,

      reason:
        "MARKET_CONTEXT_IS_DEFENSIVE",
    };
  }

  if (
    regime ===
    "HIGH_VOLATILITY"
  ) {
    return {
      action:
        "TIGHTEN_RISK_LIMITS",

      riskMultiplier:
        0.4,

      reason:
        "VOLATILITY_REGIME_IS_ELEVATED",
    };
  }

  return {
    action:
      "NORMAL",

    riskMultiplier:
      score === null
        ? 0.5
        : 0.75,

    reason:
      "MARKET_CONTEXT_IS_MIXED",
  };
}

export function buildRealtimeMarketContext({
  indices = [],
  breadth = {},
  volatility = {},
  liquidity = {},
  news = {},
  timestamp = null,
  sourceTimestamps = {},
  staleAfterSeconds = 300,
  now = Date.now,
} = {}) {
  if (
    typeof now !== "function"
  ) {
    throw new TypeError(
      "Realtime market context clock must be a function.",
    );
  }

  if (!Array.isArray(indices)) {
    throw new TypeError(
      "Realtime market context indices must be an array.",
    );
  }

  const nowTimestamp =
    finiteOrNull(
      now(),
    );

  if (nowTimestamp === null) {
    throw new TypeError(
      "Realtime market context clock returned an invalid value.",
    );
  }

  const generatedAt =
    normalizeTimestamp(
      timestamp,
      now,
    );

  const normalizedIndices =
    indices
      .map(
        (
          index,
          position,
        ) =>
          normalizeIndex(
            index,
            position,
            now,
          ),
      )
      .filter(Boolean);

  const normalizedBreadth =
    normalizeBreadth(
      breadth,
    );

  const normalizedVolatility =
    normalizeVolatility(
      volatility,
    );

  const normalizedLiquidity =
    normalizeLiquidity(
      liquidity,
    );

  const normalizedNews =
    normalizeNews(
      news,
    );

  const normalizedStaleAfter =
    Math.max(
      1,
      finiteOrNull(
        staleAfterSeconds,
      ) ?? 300,
    );

  const sourceStatus =
    Object.fromEntries(
      [
        "indices",
        "breadth",
        "volatility",
        "liquidity",
        "news",
      ].map(
        (
          source,
        ) => {
          const sourceTimestamp =
            normalizeTimestamp(
              sourceTimestamps[
                source
              ] ??
              generatedAt,
              now,
            );

          return [
            source,
            {
              timestamp:
                new Date(
                  sourceTimestamp,
                ).toISOString(),

              ...freshnessStatus({
                timestamp:
                  sourceTimestamp,

                nowTimestamp,

                staleAfterSeconds:
                  normalizedStaleAfter,
              }),
            },
          ];
        },
      ),
    );

  const staleSources =
    Object.entries(
      sourceStatus,
    )
      .filter(
        (
          [
            ,
            status,
          ],
        ) =>
          status.stale,
      )
      .map(
        (
          [
            source,
          ],
        ) =>
          source,
      );

  const composite =
    calculateCompositeScore({
      indices:
        normalizedIndices,

      breadth:
        normalizedBreadth,

      volatility:
        normalizedVolatility,

      liquidity:
        normalizedLiquidity,

      news:
        normalizedNews,
    });

  const regime =
    marketRegime({
      score:
        composite.score,

      volatility:
        normalizedVolatility,

      breadth:
        normalizedBreadth,
    });

  const recommendation =
    buildRecommendation({
      regime,

      score:
        composite.score,

      staleSourceCount:
        staleSources.length,
    });

  return {
    version:
      REALTIME_MARKET_CONTEXT_V2_VERSION,

    ready:
      composite.score !== null,

    generatedAt:
      new Date(
        generatedAt,
      ).toISOString(),

    score:
      composite.score,

    regime,

    recommendation,

    indices:
      normalizedIndices.map(
        (
          index,
        ) => ({
          ...index,

          timestamp:
            new Date(
              index.timestamp,
            ).toISOString(),
        }),
      ),

    breadth:
      normalizedBreadth,

    volatility:
      normalizedVolatility,

    liquidity:
      normalizedLiquidity,

    news:
      normalizedNews,

    components:
      composite.components,

    freshness: {
      staleAfterSeconds:
        normalizedStaleAfter,

      staleSourceCount:
        staleSources.length,

      staleSources,

      sources:
        sourceStatus,
    },

    diagnostics: {
      indexCount:
        normalizedIndices.length,

      availableComponentCount:
        composite.components.filter(
          (
            component,
          ) =>
            component.score !==
            null,
        ).length,

      stale:
        staleSources.length >
        0,
    },
  };
}

export class RealtimeMarketContextV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  build(input = {}) {
    return buildRealtimeMarketContext({
      ...this.config,

      ...input,
    });
  }
}

export const realtimeMarketContextV2 =
  new RealtimeMarketContextV2();

export default buildRealtimeMarketContext;