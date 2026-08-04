export const REGIME_ADAPTIVE_ENSEMBLE_V2_VERSION =
  "regime-adaptive-ensemble-v2";

const REGIMES =
  Object.freeze([
    "TRENDING_BULL",
    "TRENDING_BEAR",
    "RANGE",
    "HIGH_VOLATILITY",
    "LOW_VOLATILITY",
    "UNKNOWN",
  ]);

const DIRECTIONS =
  Object.freeze({
    BUY: 1,
    NEUTRAL: 0,
    SELL: -1,
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

function standardDeviation(values) {
  const mean =
    average(values);

  if (mean === null) {
    return null;
  }

  const variance =
    values.reduce(
      (
        sum,
        value,
      ) =>
        sum +
        (
          value -
          mean
        ) ** 2,
      0,
    ) /
    values.length;

  return Math.sqrt(
    variance,
  );
}

function normalizeDirection(value) {
  if (typeof value === "number") {
    if (value > 0) {
      return DIRECTIONS.BUY;
    }

    if (value < 0) {
      return DIRECTIONS.SELL;
    }

    return DIRECTIONS.NEUTRAL;
  }

  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "BUY",
      "BULLISH",
      "LONG",
      "UP",
      "POSITIVE",
      "1",
    ].includes(text)
  ) {
    return DIRECTIONS.BUY;
  }

  if (
    [
      "SELL",
      "BEARISH",
      "SHORT",
      "DOWN",
      "NEGATIVE",
      "-1",
    ].includes(text)
  ) {
    return DIRECTIONS.SELL;
  }

  return DIRECTIONS.NEUTRAL;
}

function directionLabel(value) {
  if (value > 0) {
    return "BUY";
  }

  if (value < 0) {
    return "SELL";
  }

  return "NEUTRAL";
}

function normalizeRegime(value) {
  const text =
    String(value ?? "")
      .trim()
      .toUpperCase()
      .replaceAll("-", "_")
      .replaceAll(" ", "_");

  const aliases = {
    BULL:
      "TRENDING_BULL",

    BULLISH:
      "TRENDING_BULL",

    UPTREND:
      "TRENDING_BULL",

    BEAR:
      "TRENDING_BEAR",

    BEARISH:
      "TRENDING_BEAR",

    DOWNTREND:
      "TRENDING_BEAR",

    SIDEWAYS:
      "RANGE",

    RANGING:
      "RANGE",

    VOLATILE:
      "HIGH_VOLATILITY",

    HIGH_VOL:
      "HIGH_VOLATILITY",

    CALM:
      "LOW_VOLATILITY",

    LOW_VOL:
      "LOW_VOLATILITY",
  };

  const normalized =
    aliases[text] ??
    text;

  return REGIMES.includes(
    normalized,
  )
    ? normalized
    : "UNKNOWN";
}

function normalizeReturns(values = []) {
  if (!Array.isArray(values)) {
    return [];
  }

  return values
    .map(
      (
        value,
      ) =>
        typeof value === "object"
          ? finiteOrNull(
              value.return ??
              value.changePercent ??
              value.value,
            )
          : finiteOrNull(value),
    )
    .filter(
      Number.isFinite,
    );
}

function inferRegime({
  returns = [],
  trendScore = null,
  volatility = null,
  adx = null,
  movingAverageSlope = null,
} = {}) {
  const normalizedReturns =
    normalizeReturns(
      returns,
    );

  const meanReturn =
    average(
      normalizedReturns,
    ) ?? 0;

  const measuredVolatility =
    finiteOrNull(
      volatility,
    ) ??
    standardDeviation(
      normalizedReturns,
    ) ??
    0;

  const normalizedTrendScore =
    finiteOrNull(
      trendScore,
    ) ??
    (
      meanReturn *
      10
    );

  const normalizedAdx =
    finiteOrNull(
      adx,
    ) ?? 0;

  const slope =
    finiteOrNull(
      movingAverageSlope,
    ) ??
    meanReturn;

  if (
    measuredVolatility >= 4.5
  ) {
    return {
      regime:
        "HIGH_VOLATILITY",

      confidence:
        clamp(
          55 +
          measuredVolatility *
          5,
        ) ?? 55,

      metrics: {
        meanReturn:
          round(
            meanReturn,
          ),

        volatility:
          round(
            measuredVolatility,
          ),

        trendScore:
          round(
            normalizedTrendScore,
          ),

        adx:
          round(
            normalizedAdx,
          ),

        movingAverageSlope:
          round(
            slope,
          ),
      },
    };
  }

  if (
    measuredVolatility <= 0.5 &&
    Math.abs(
      normalizedTrendScore,
    ) < 15
  ) {
    return {
      regime:
        "LOW_VOLATILITY",

      confidence:
        clamp(
          75 -
          measuredVolatility *
          20,
        ) ?? 60,

      metrics: {
        meanReturn:
          round(
            meanReturn,
          ),

        volatility:
          round(
            measuredVolatility,
          ),

        trendScore:
          round(
            normalizedTrendScore,
          ),

        adx:
          round(
            normalizedAdx,
          ),

        movingAverageSlope:
          round(
            slope,
          ),
      },
    };
  }

  const strongTrend =
    normalizedAdx >= 22 ||
    Math.abs(
      normalizedTrendScore,
    ) >= 20 ||
    Math.abs(
      slope,
    ) >= 0.4;

  if (strongTrend) {
    const bullish =
      normalizedTrendScore > 0 ||
      slope > 0 ||
      meanReturn > 0;

    return {
      regime:
        bullish
          ? "TRENDING_BULL"
          : "TRENDING_BEAR",

      confidence:
        clamp(
          50 +
          Math.abs(
            normalizedTrendScore,
          ) *
          0.8 +
          normalizedAdx *
          0.5,
        ) ?? 50,

      metrics: {
        meanReturn:
          round(
            meanReturn,
          ),

        volatility:
          round(
            measuredVolatility,
          ),

        trendScore:
          round(
            normalizedTrendScore,
          ),

        adx:
          round(
            normalizedAdx,
          ),

        movingAverageSlope:
          round(
            slope,
          ),
      },
    };
  }

  return {
    regime:
      "RANGE",

    confidence:
      clamp(
        75 -
        Math.abs(
          normalizedTrendScore,
        ),
      ) ?? 50,

    metrics: {
      meanReturn:
        round(
          meanReturn,
        ),

      volatility:
        round(
          measuredVolatility,
        ),

      trendScore:
        round(
          normalizedTrendScore,
        ),

      adx:
        round(
          normalizedAdx,
        ),

      movingAverageSlope:
        round(
          slope,
        ),
    },
  };
}

function normalizeModel(
  model,
  index,
) {
  if (
    !model ||
    typeof model !== "object"
  ) {
    return null;
  }

  const id =
    String(
      model.id ??
      model.name ??
      `model-${index + 1}`,
    ).trim();

  const prediction =
    model.prediction ??
    model.output ??
    model.signal ??
    model;

  const direction =
    normalizeDirection(
      prediction.direction ??
      prediction.signal ??
      prediction.recommendation ??
      prediction.value,
    );

  const confidence =
    clamp(
      prediction.confidence ??
      prediction.probability ??
      model.confidence ??
      50,
    ) ?? 50;

  const score =
    finiteOrNull(
      prediction.score ??
      model.score,
    );

  const baseWeight =
    Math.max(
      0,
      finiteOrNull(
        model.weight ??
        model.baseWeight,
      ) ?? 1,
    );

  const historicalAccuracy =
    clamp(
      model.historicalAccuracy ??
      model.accuracy ??
      50,
    ) ?? 50;

  const regimePerformance =
    model.regimePerformance &&
    typeof model.regimePerformance ===
      "object"
      ? Object.fromEntries(
          Object.entries(
            model.regimePerformance,
          ).map(
            (
              [
                key,
                value,
              ],
            ) => [
              normalizeRegime(
                key,
              ),

              clamp(
                value,
              ) ?? 50,
            ],
          ),
        )
      : {};

  return {
    id,

    family:
      String(
        model.family ??
        model.type ??
        "GENERAL",
      ).toUpperCase(),

    direction,

    confidence,

    score,

    baseWeight,

    historicalAccuracy,

    regimePerformance,

    enabled:
      model.enabled !== false,

    metadata:
      model.metadata ??
      {},
  };
}

function modelRegimeMultiplier(
  model,
  regime,
) {
  const performance =
    model.regimePerformance?.[
      regime
    ];

  if (
    Number.isFinite(
      performance,
    )
  ) {
    return Math.max(
      0.2,
      performance /
      50,
    );
  }

  const family =
    model.family;

  const familyMultipliers = {
    TREND:
      {
        TRENDING_BULL:
          1.35,

        TRENDING_BEAR:
          1.35,

        RANGE:
          0.7,

        HIGH_VOLATILITY:
          0.85,

        LOW_VOLATILITY:
          0.9,

        UNKNOWN:
          1,
      },

    MOMENTUM:
      {
        TRENDING_BULL:
          1.25,

        TRENDING_BEAR:
          1.2,

        RANGE:
          0.75,

        HIGH_VOLATILITY:
          0.9,

        LOW_VOLATILITY:
          0.85,

        UNKNOWN:
          1,
      },

    MEAN_REVERSION:
      {
        TRENDING_BULL:
          0.75,

        TRENDING_BEAR:
          0.75,

        RANGE:
          1.4,

        HIGH_VOLATILITY:
          1.05,

        LOW_VOLATILITY:
          1.1,

        UNKNOWN:
          1,
      },

    VOLATILITY:
      {
        TRENDING_BULL:
          0.9,

        TRENDING_BEAR:
          0.95,

        RANGE:
          0.9,

        HIGH_VOLATILITY:
          1.45,

        LOW_VOLATILITY:
          0.8,

        UNKNOWN:
          1,
      },

    FUNDAMENTAL:
      {
        TRENDING_BULL:
          1.05,

        TRENDING_BEAR:
          1.05,

        RANGE:
          1,

        HIGH_VOLATILITY:
          0.85,

        LOW_VOLATILITY:
          1.15,

        UNKNOWN:
          1,
      },

    NEWS:
      {
        TRENDING_BULL:
          1.05,

        TRENDING_BEAR:
          1.05,

        RANGE:
          0.9,

        HIGH_VOLATILITY:
          1.25,

        LOW_VOLATILITY:
          0.85,

        UNKNOWN:
          1,
      },

    GENERAL:
      {
        TRENDING_BULL:
          1,

        TRENDING_BEAR:
          1,

        RANGE:
          1,

        HIGH_VOLATILITY:
          1,

        LOW_VOLATILITY:
          1,

        UNKNOWN:
          1,
      },
  };

  return (
    familyMultipliers[
      family
    ] ??
    familyMultipliers.GENERAL
  )[
    regime
  ] ?? 1;
}

function calculateModelWeight(
  model,
  regime,
) {
  const accuracyMultiplier =
    Math.max(
      0.2,
      model.historicalAccuracy /
      50,
    );

  const confidenceMultiplier =
    Math.max(
      0.1,
      model.confidence /
      100,
    );

  const regimeMultiplier =
    modelRegimeMultiplier(
      model,
      regime,
    );

  return (
    model.baseWeight *
    accuracyMultiplier *
    confidenceMultiplier *
    regimeMultiplier
  );
}

function normalizeWeights(
  weightedModels,
) {
  const total =
    weightedModels.reduce(
      (
        sum,
        model,
      ) =>
        sum +
        model.rawWeight,
      0,
    );

  if (total <= 0) {
    const equalWeight =
      weightedModels.length
        ? 1 /
          weightedModels.length
        : 0;

    return weightedModels.map(
      (
        model,
      ) => ({
        ...model,

        normalizedWeight:
          equalWeight,
      }),
    );
  }

  return weightedModels.map(
    (
      model,
    ) => ({
      ...model,

      normalizedWeight:
        model.rawWeight /
        total,
    }),
  );
}

function calculateAgreement(
  models,
  finalDirection,
) {
  if (!models.length) {
    return 0;
  }

  const agreeingWeight =
    models
      .filter(
        (
          model,
        ) =>
          model.direction ===
          finalDirection,
      )
      .reduce(
        (
          sum,
          model,
        ) =>
          sum +
          model.normalizedWeight,
        0,
      );

  return agreeingWeight *
    100;
}

function calculateDispersion(
  models,
  ensembleScore,
) {
  if (!models.length) {
    return 0;
  }

  const variance =
    models.reduce(
      (
        sum,
        model,
      ) =>
        sum +
        model.normalizedWeight *
        (
          model.direction *
          model.confidence -
          ensembleScore
        ) ** 2,
      0,
    );

  return Math.sqrt(
    variance,
  );
}

function buildExplanation({
  regime,
  finalDirection,
  confidence,
  agreement,
  contributors,
}) {
  const strongest =
    contributors[0];

  const parts = [
    `Regime: ${regime}.`,
    `Signal: ${directionLabel(finalDirection)}.`,
    `Confidence: ${round(confidence, 1)}%.`,
    `Agreement: ${round(agreement, 1)}%.`,
  ];

  if (strongest) {
    parts.push(
      `Largest contributor: ${strongest.id} (${round(strongest.weightPercent, 1)}%).`,
    );
  }

  return parts.join(" ");
}

export function combineRegimeAdaptivePredictions({
  models = [],
  regime = null,
  marketContext = {},
  buyThreshold = 12,
  sellThreshold = -12,
  minimumAgreement = 45,
  minimumConfidence = 50,
} = {}) {
  if (!Array.isArray(models)) {
    throw new TypeError(
      "Regime adaptive ensemble models must be an array.",
    );
  }

  const inferred =
    inferRegime(
      marketContext,
    );

  const activeRegime =
    regime === null ||
    regime === undefined
      ? inferred.regime
      : normalizeRegime(
          regime,
        );

  const normalizedModels =
    models
      .map(
        normalizeModel,
      )
      .filter(
        (
          model,
        ) =>
          model &&
          model.enabled,
      );

  if (!normalizedModels.length) {
    return {
      version:
        REGIME_ADAPTIVE_ENSEMBLE_V2_VERSION,

      ready:
        false,

      regime:
        activeRegime,

      regimeConfidence:
        inferred.confidence,

      direction:
        "NEUTRAL",

      directionValue:
        DIRECTIONS.NEUTRAL,

      confidence:
        0,

      agreement:
        0,

      score:
        0,

      approved:
        false,

      blockers: [
        "NO_ACTIVE_MODELS",
      ],

      contributors:
        [],

      diagnostics: {
        modelCount:
          0,

        dispersion:
          0,
      },
    };
  }

  const weightedModels =
    normalizeWeights(
      normalizedModels.map(
        (
          model,
        ) => ({
          ...model,

          rawWeight:
            calculateModelWeight(
              model,
              activeRegime,
            ),
        }),
      ),
    );

  const ensembleScore =
    weightedModels.reduce(
      (
        sum,
        model,
      ) =>
        sum +
        model.direction *
        model.confidence *
        model.normalizedWeight,
      0,
    );

  const normalizedBuyThreshold =
    finiteOrNull(
      buyThreshold,
    ) ?? 12;

  const normalizedSellThreshold =
    finiteOrNull(
      sellThreshold,
    ) ?? -12;

  let finalDirection =
    DIRECTIONS.NEUTRAL;

  if (
    ensembleScore >=
    normalizedBuyThreshold
  ) {
    finalDirection =
      DIRECTIONS.BUY;
  } else if (
    ensembleScore <=
    normalizedSellThreshold
  ) {
    finalDirection =
      DIRECTIONS.SELL;
  }

  const agreement =
    calculateAgreement(
      weightedModels,
      finalDirection,
    );

  const dispersion =
    calculateDispersion(
      weightedModels,
      ensembleScore,
    );

  const regimeConfidence =
    clamp(
      inferred.confidence,
    ) ?? 50;

  const baseConfidence =
    Math.abs(
      ensembleScore,
    );

  const confidence =
    clamp(
      baseConfidence *
        0.55 +
      agreement *
        0.3 +
      regimeConfidence *
        0.15 -
      dispersion *
        0.15,
    ) ?? 0;

  const blockers = [];

  if (
    finalDirection ===
    DIRECTIONS.NEUTRAL
  ) {
    blockers.push(
      "SIGNAL_BELOW_THRESHOLD",
    );
  }

  if (
    agreement <
    minimumAgreement
  ) {
    blockers.push(
      "LOW_MODEL_AGREEMENT",
    );
  }

  if (
    confidence <
    minimumConfidence
  ) {
    blockers.push(
      "LOW_CONFIDENCE",
    );
  }

  const contributors =
    weightedModels
      .map(
        (
          model,
        ) => ({
          id:
            model.id,

          family:
            model.family,

          direction:
            directionLabel(
              model.direction,
            ),

          confidence:
            round(
              model.confidence,
              2,
            ),

          historicalAccuracy:
            round(
              model.historicalAccuracy,
              2,
            ),

          regimeMultiplier:
            round(
              modelRegimeMultiplier(
                model,
                activeRegime,
              ),
            ),

          rawWeight:
            round(
              model.rawWeight,
            ),

          weight:
            round(
              model.normalizedWeight,
            ),

          weightPercent:
            round(
              model.normalizedWeight *
              100,
              2,
            ),

          contribution:
            round(
              model.direction *
              model.confidence *
              model.normalizedWeight,
            ),
        }),
      )
      .sort(
        (
          left,
          right,
        ) =>
          right.weight -
          left.weight,
      );

  const approved =
    blockers.length === 0;

  return {
    version:
      REGIME_ADAPTIVE_ENSEMBLE_V2_VERSION,

    ready:
      true,

    regime:
      activeRegime,

    regimeConfidence:
      round(
        regimeConfidence,
        2,
      ),

    inferredRegime:
      inferred,

    direction:
      directionLabel(
        finalDirection,
      ),

    directionValue:
      finalDirection,

    confidence:
      round(
        confidence,
        2,
      ),

    agreement:
      round(
        agreement,
        2,
      ),

    score:
      round(
        ensembleScore,
      ),

    approved,

    blockers,

    thresholds: {
      buy:
        normalizedBuyThreshold,

      sell:
        normalizedSellThreshold,

      minimumAgreement,

      minimumConfidence,
    },

    contributors,

    explanation:
      buildExplanation({
        regime:
          activeRegime,

        finalDirection,

        confidence,

        agreement,

        contributors,
      }),

    diagnostics: {
      modelCount:
        weightedModels.length,

      bullishModels:
        weightedModels.filter(
          (
            model,
          ) =>
            model.direction ===
            DIRECTIONS.BUY,
        ).length,

      bearishModels:
        weightedModels.filter(
          (
            model,
          ) =>
            model.direction ===
            DIRECTIONS.SELL,
        ).length,

      neutralModels:
        weightedModels.filter(
          (
            model,
          ) =>
            model.direction ===
            DIRECTIONS.NEUTRAL,
        ).length,

      dispersion:
        round(
          dispersion,
        ),

      weightTotal:
        round(
          weightedModels.reduce(
            (
              sum,
              model,
            ) =>
              sum +
              model.normalizedWeight,
            0,
          ),
        ),
    },
  };
}

export class RegimeAdaptiveEnsembleV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  combine(
    models = [],
    overrides = {},
  ) {
    return combineRegimeAdaptivePredictions({
      ...this.config,

      ...overrides,

      models,
    });
  }
}

export const regimeAdaptiveEnsembleV2 =
  new RegimeAdaptiveEnsembleV2();

export {
  inferRegime,
  normalizeRegime,
};

export default combineRegimeAdaptivePredictions;