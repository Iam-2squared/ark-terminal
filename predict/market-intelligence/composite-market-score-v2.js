import {
  calculateCompositeMarketScore,
} from "./composite-market-score.js";

export const COMPOSITE_MARKET_V2_VERSION =
  "composite-market-score-v2";

export const COMPOSITE_MARKET_V2_WEIGHTS =
  Object.freeze({
    breadth:
      30,

    liquidity:
      20,

    sectorStrength:
      20,

    sectorRotation:
      15,

    volatility:
      10,

    news:
      5,
  });

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
  digits = 2,
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

function normalizeReport(
  report,
) {
  if (
    !report ||
    typeof report !== "object" ||
    Array.isArray(report)
  ) {
    return {
      score:
        null,

      confidence:
        0,

      coverage:
        0,

      available:
        false,
    };
  }

  const score =
    clamp(report.score);

  const confidence =
    clamp(
      report.confidence ??
      100,
    ) ?? 0;

  const coverage =
    clamp(
      report.coverage ??
      confidence,
    ) ?? 0;

  return {
    score,

    confidence,

    coverage,

    available:
      score !== null &&
      confidence > 0 &&
      coverage > 0,
  };
}

function normalizeWeights(
  weights = {},
) {
  return Object.freeze(
    Object.fromEntries(
      Object.entries(
        COMPOSITE_MARKET_V2_WEIGHTS,
      ).map(
        (
          [
            key,
            fallback,
          ],
        ) => [
          key,

          Math.max(
            0,
            finiteOrNull(
              weights?.[key],
            ) ??
            fallback,
          ),
        ],
      ),
    ),
  );
}

function componentContribution({
  key,
  report,
  weight,
}) {
  const normalized =
    normalizeReport(report);

  const effectiveWeight =
    normalized.available
      ? weight *
        (
          normalized.confidence /
          100
        ) *
        (
          normalized.coverage /
          100
        )
      : 0;

  return {
    key,

    score:
      normalized.score,

    confidence:
      normalized.confidence,

    coverage:
      normalized.coverage,

    weight,

    effectiveWeight:
      round(
        effectiveWeight,
        4,
      ),

    available:
      normalized.available,

    weightedValue:
      normalized.available
        ? normalized.score *
          effectiveWeight
        : 0,
  };
}

function calculateDispersion(
  scores,
) {
  const available =
    scores.filter(
      Number.isFinite,
    );

  if (!available.length) {
    return null;
  }

  const mean =
    available.reduce(
      (
        sum,
        value,
      ) =>
        sum + value,
      0,
    ) /
    available.length;

  const variance =
    available.reduce(
      (
        sum,
        value,
      ) =>
        sum +
        (
          value - mean
        ) ** 2,
      0,
    ) /
    available.length;

  return Math.sqrt(
    variance,
  );
}

function sentimentFromScore(
  score,
) {
  if (score === null) {
    return "UNKNOWN";
  }

  if (score >= 70) {
    return "STRONGLY_BULLISH";
  }

  if (score >= 58) {
    return "BULLISH";
  }

  if (score <= 30) {
    return "STRONGLY_BEARISH";
  }

  if (score <= 42) {
    return "BEARISH";
  }

  return "NEUTRAL";
}

function regimeFromScore({
  score,
  dispersion,
  confidence,
}) {
  if (
    score === null ||
    confidence <= 0
  ) {
    return "UNKNOWN";
  }

  if (
    dispersion !== null &&
    dispersion >= 25
  ) {
    return "FRAGMENTED";
  }

  if (score >= 65) {
    return "RISK_ON";
  }

  if (score <= 35) {
    return "RISK_OFF";
  }

  return "MIXED";
}

function confidencePenalty({
  dispersion,
  availableCount,
  totalCount,
}) {
  const availabilityRatio =
    totalCount > 0
      ? availableCount /
        totalCount
      : 0;

  const availabilityPenalty =
    (
      1 -
      availabilityRatio
    ) * 35;

  const disagreementPenalty =
    dispersion === null
      ? 0
      : Math.min(
          30,
          dispersion * 0.75,
        );

  return (
    availabilityPenalty +
    disagreementPenalty
  );
}

export function calculateCompositeMarketScoreV2({
  breadth,
  liquidity,
  sectorStrength,
  sectorRotation,
  volatility,
  news,
  weights =
    COMPOSITE_MARKET_V2_WEIGHTS,
  timestamp =
    null,
  now =
    Date.now,
} = {}) {
  if (typeof now !== "function") {
    throw new TypeError(
      "Composite Market Score v2 clock must be a function.",
    );
  }

  const generatedAt =
    new Date(
      timestamp ??
      now(),
    );

  if (
    Number.isNaN(
      generatedAt.getTime(),
    )
  ) {
    throw new TypeError(
      "Composite Market Score v2 timestamp is invalid.",
    );
  }

  const normalizedWeights =
    normalizeWeights(
      weights,
    );

  const components = [
    componentContribution({
      key:
        "breadth",

      report:
        breadth,

      weight:
        normalizedWeights.breadth,
    }),

    componentContribution({
      key:
        "liquidity",

      report:
        liquidity,

      weight:
        normalizedWeights.liquidity,
    }),

    componentContribution({
      key:
        "sectorStrength",

      report:
        sectorStrength,

      weight:
        normalizedWeights.sectorStrength,
    }),

    componentContribution({
      key:
        "sectorRotation",

      report:
        sectorRotation,

      weight:
        normalizedWeights.sectorRotation,
    }),

    componentContribution({
      key:
        "volatility",

      report:
        volatility,

      weight:
        normalizedWeights.volatility,
    }),

    componentContribution({
      key:
        "news",

      report:
        news,

      weight:
        normalizedWeights.news,
    }),
  ];

  const available =
    components.filter(
      (
        component,
      ) =>
        component.available,
    );

  const effectiveWeightTotal =
    available.reduce(
      (
        sum,
        component,
      ) =>
        sum +
        component.effectiveWeight,
      0,
    );

  const rawScore =
    effectiveWeightTotal > 0
      ? available.reduce(
          (
            sum,
            component,
          ) =>
            sum +
            component.weightedValue,
          0,
        ) /
        effectiveWeightTotal
      : null;

  const dispersion =
    calculateDispersion(
      available.map(
        (
          component,
        ) =>
          component.score,
      ),
    );

  const baseConfidence =
    effectiveWeightTotal > 0
      ? clamp(
          effectiveWeightTotal /
          Object.values(
            normalizedWeights,
          ).reduce(
            (
              sum,
              value,
            ) =>
              sum + value,
            0,
          ) *
          100,
        )
      : 0;

  const penalty =
    confidencePenalty({
      dispersion,

      availableCount:
        available.length,

      totalCount:
        components.length,
    });

  const confidence =
    clamp(
      (
        baseConfidence ??
        0
      ) -
      penalty,
    ) ?? 0;

  const legacy =
    calculateCompositeMarketScore({
      breadth,
      liquidity,
      sectorStrength,
      sectorRotation,
      timestamp:
        generatedAt.toISOString(),
      now,
    });

  const score =
    rawScore === null
      ? null
      : round(
          rawScore,
        );

  return {
    version:
      COMPOSITE_MARKET_V2_VERSION,

    timestamp:
      generatedAt.toISOString(),

    score,

    rawScore:
      rawScore === null
        ? null
        : round(
            rawScore,
            4,
          ),

    confidence:
      round(
        confidence,
      ),

    coverage:
      round(
        (
          available.length /
          components.length
        ) *
        100,
      ),

    sentiment:
      sentimentFromScore(
        score,
      ),

    regime:
      regimeFromScore({
        score,

        dispersion,

        confidence,
      }),

    dispersion:
      dispersion === null
        ? null
        : round(
            dispersion,
          ),

    disagreement:
      dispersion === null
        ? "UNKNOWN"
        : dispersion >= 25
          ? "HIGH"
          : dispersion >= 12
            ? "MODERATE"
            : "LOW",

    components,

    diagnostics: {
      availableCount:
        available.length,

      totalCount:
        components.length,

      effectiveWeightTotal:
        round(
          effectiveWeightTotal,
          4,
        ),

      baseConfidence:
        round(
          baseConfidence ??
          0,
        ),

      confidencePenalty:
        round(
          penalty,
        ),

      legacyScore:
        legacy.score,

      legacySentiment:
        legacy.sentiment,
    },
  };
}

export class CompositeMarketScoreV2Engine {
  constructor({
    weights =
      COMPOSITE_MARKET_V2_WEIGHTS,

    now =
      Date.now,
  } = {}) {
    if (typeof now !== "function") {
      throw new TypeError(
        "Composite Market Score v2 clock must be a function.",
      );
    }

    this.weights =
      normalizeWeights(
        weights,
      );

    this.now =
      now;
  }

  calculate(
    input = {},
  ) {
    return calculateCompositeMarketScoreV2({
      ...input,

      weights:
        this.weights,

      now:
        this.now,
    });
  }
}

export const compositeMarketScoreV2Engine =
  new CompositeMarketScoreV2Engine();

export default calculateCompositeMarketScoreV2;