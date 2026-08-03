export const EXPLAINABILITY_V2_VERSION =
  "explainability-v2";

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

function normalizeDirection(value) {
  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "BUY",
      "BULLISH",
      "UP",
      "LONG",
      "POSITIVE",
    ].includes(text)
  ) {
    return "BULLISH";
  }

  if (
    [
      "SELL",
      "BEARISH",
      "DOWN",
      "SHORT",
      "NEGATIVE",
    ].includes(text)
  ) {
    return "BEARISH";
  }

  return "NEUTRAL";
}

function normalizeFeature(
  feature,
  index,
) {
  if (
    !feature ||
    typeof feature !== "object" ||
    Array.isArray(feature)
  ) {
    return null;
  }

  const name =
    String(
      feature.name ??
      feature.key ??
      feature.feature ??
      `feature-${index + 1}`,
    ).trim();

  const rawValue =
    finiteOrNull(
      feature.value ??
      feature.rawValue,
    );

  const weight =
    Math.max(
      0,
      finiteOrNull(
        feature.weight ??
        feature.importance,
      ) ??
      0,
    );

  const contribution =
    finiteOrNull(
      feature.contribution ??
      feature.impact,
    ) ??
    0;

  const direction =
    contribution > 0
      ? "BULLISH"
      : contribution < 0
        ? "BEARISH"
        : "NEUTRAL";

  return {
    name,
    value:
      rawValue,
    weight:
      round(weight, 4),
    contribution:
      round(contribution, 4),
    absoluteContribution:
      round(
        Math.abs(contribution),
        4,
      ),
    direction,
    reason:
      String(
        feature.reason ??
        feature.explanation ??
        "",
      ).trim(),
  };
}

function normalizeFeatures(
  features = [],
) {
  if (Array.isArray(features)) {
    return features
      .map(
        normalizeFeature,
      )
      .filter(Boolean);
  }

  if (
    features &&
    typeof features === "object"
  ) {
    return Object.entries(features)
      .map(
        (
          [
            name,
            value,
          ],
          index,
        ) =>
          normalizeFeature(
            {
              name,
              value:
                typeof value === "object"
                  ? value.value
                  : value,
              weight:
                typeof value === "object"
                  ? value.weight
                  : Math.abs(
                      finiteOrNull(value) ??
                      0,
                    ),
              contribution:
                typeof value === "object"
                  ? value.contribution
                  : finiteOrNull(value) ??
                    0,
              reason:
                typeof value === "object"
                  ? value.reason
                  : "",
            },
            index,
          ),
      )
      .filter(Boolean);
  }

  return [];
}

function rankFeatures(
  features,
) {
  return [
    ...features,
  ]
    .sort(
      (
        left,
        right,
      ) =>
        right.absoluteContribution -
        left.absoluteContribution,
    )
    .map(
      (
        feature,
        index,
      ) => ({
        ...feature,
        rank:
          index + 1,
      }),
    );
}

function calculateContributionTotals(
  features,
) {
  const bullish =
    features
      .filter(
        (
          feature,
        ) =>
          feature.contribution > 0,
      )
      .reduce(
        (
          sum,
          feature,
        ) =>
          sum +
          feature.contribution,
        0,
      );

  const bearish =
    Math.abs(
      features
        .filter(
          (
            feature,
          ) =>
            feature.contribution < 0,
        )
        .reduce(
          (
            sum,
            feature,
          ) =>
            sum +
            feature.contribution,
          0,
        ),
    );

  const total =
    bullish +
    bearish;

  return {
    bullish:
      round(bullish, 4),
    bearish:
      round(bearish, 4),
    total:
      round(total, 4),
    bullishShare:
      total > 0
        ? round(
            bullish /
            total *
            100,
          )
        : 0,
    bearishShare:
      total > 0
        ? round(
            bearish /
            total *
            100,
          )
        : 0,
  };
}

function determineAgreement({
  predictionDirection,
  totals,
}) {
  if (
    predictionDirection === "NEUTRAL"
  ) {
    return "NEUTRAL";
  }

  if (
    predictionDirection === "BULLISH"
  ) {
    return totals.bullish >
      totals.bearish
      ? "AGREES"
      : totals.bullish <
          totals.bearish
        ? "CONFLICTS"
        : "MIXED";
  }

  return totals.bearish >
    totals.bullish
    ? "AGREES"
    : totals.bearish <
        totals.bullish
      ? "CONFLICTS"
      : "MIXED";
}

function determineExplainabilityQuality({
  featureCount,
  topFeatureShare,
  confidence,
}) {
  if (!featureCount) {
    return "UNAVAILABLE";
  }

  if (
    confidence >= 70 &&
    topFeatureShare <= 55 &&
    featureCount >= 3
  ) {
    return "HIGH";
  }

  if (
    confidence >= 40 &&
    featureCount >= 2
  ) {
    return "MEDIUM";
  }

  return "LOW";
}

function buildSummary({
  direction,
  confidence,
  strongestBullish,
  strongestBearish,
  agreement,
}) {
  const directionText =
    direction === "BULLISH"
      ? "上昇寄り"
      : direction === "BEARISH"
        ? "下落寄り"
        : "中立";

  const bullishText =
    strongestBullish
      ? `${strongestBullish.name}が最大の上昇要因`
      : "明確な上昇要因なし";

  const bearishText =
    strongestBearish
      ? `${strongestBearish.name}が最大の下落要因`
      : "明確な下落要因なし";

  const agreementText =
    agreement === "AGREES"
      ? "主要因は判定方向と一致"
      : agreement === "CONFLICTS"
        ? "主要因と判定方向に矛盾あり"
        : "主要因は拮抗";

  return `${directionText}、信頼度${round(confidence)}%。${bullishText}。${bearishText}。${agreementText}。`;
}

export function buildExplainabilityReport({
  prediction = {},
  features = [],
  marketContext = {},
  timestamp = null,
  now = Date.now,
} = {}) {
  if (typeof now !== "function") {
    throw new TypeError(
      "Explainability v2 clock must be a function.",
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
      "Explainability v2 timestamp is invalid.",
    );
  }

  const direction =
    normalizeDirection(
      prediction.direction ??
      prediction.signal ??
      prediction.recommendation,
    );

  const confidence =
    clamp(
      prediction.confidence ??
      prediction.score ??
      0,
    ) ?? 0;

  const normalized =
    rankFeatures(
      normalizeFeatures(
        features,
      ),
    );

  const totals =
    calculateContributionTotals(
      normalized,
    );

  const strongestBullish =
    normalized.find(
      (
        feature,
      ) =>
        feature.contribution > 0,
    ) ??
    null;

  const strongestBearish =
    normalized.find(
      (
        feature,
      ) =>
        feature.contribution < 0,
    ) ??
    null;

  const topFeature =
    normalized[0] ??
    null;

  const topFeatureShare =
    topFeature &&
    totals.total > 0
      ? topFeature.absoluteContribution /
        totals.total *
        100
      : 0;

  const agreement =
    determineAgreement({
      predictionDirection:
        direction,
      totals,
    });

  const conflicts =
    normalized
      .filter(
        (
          feature,
        ) =>
          direction === "BULLISH"
            ? feature.contribution < 0
            : direction === "BEARISH"
              ? feature.contribution > 0
              : false,
      )
      .slice(
        0,
        5,
      );

  const drivers =
    normalized
      .filter(
        (
          feature,
        ) =>
          direction === "BULLISH"
            ? feature.contribution > 0
            : direction === "BEARISH"
              ? feature.contribution < 0
              : feature.contribution !== 0,
      )
      .slice(
        0,
        5,
      );

  const quality =
    determineExplainabilityQuality({
      featureCount:
        normalized.length,
      topFeatureShare,
      confidence,
    });

  return {
    version:
      EXPLAINABILITY_V2_VERSION,

    timestamp:
      generatedAt.toISOString(),

    prediction: {
      direction,
      confidence:
        round(confidence),
      score:
        finiteOrNull(
          prediction.score,
        ),
    },

    explanationQuality:
      quality,

    agreement,

    featureCount:
      normalized.length,

    topFeatureShare:
      round(
        topFeatureShare,
      ),

    drivers,
    conflicts,
    rankedFeatures:
      normalized,

    contributionTotals:
      totals,

    strongestBullish,
    strongestBearish,

    marketContext: {
      regime:
        String(
          marketContext.regime ??
          "UNKNOWN",
        ),
      score:
        finiteOrNull(
          marketContext.score,
        ),
      confidence:
        finiteOrNull(
          marketContext.confidence,
        ),
    },

    summary:
      buildSummary({
        direction,
        confidence,
        strongestBullish,
        strongestBearish,
        agreement,
      }),

    warnings: [
      ...(
        agreement === "CONFLICTS"
          ? [
              "Prediction direction conflicts with dominant feature contributions.",
            ]
          : []
      ),
      ...(
        confidence < 40
          ? [
              "Prediction confidence is low.",
            ]
          : []
      ),
      ...(
        normalized.length < 2
          ? [
              "Too few explanatory features are available.",
            ]
          : []
      ),
    ],
  };
}

export class ExplainabilityV2Engine {
  constructor({
    now = Date.now,
  } = {}) {
    if (typeof now !== "function") {
      throw new TypeError(
        "Explainability v2 clock must be a function.",
      );
    }

    this.now =
      now;
  }

  explain(
    input = {},
  ) {
    return buildExplainabilityReport({
      ...input,
      now:
        this.now,
    });
  }
}

export const explainabilityV2Engine =
  new ExplainabilityV2Engine();

export default buildExplainabilityReport;