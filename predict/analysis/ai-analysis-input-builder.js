function finiteNumber(
  value,
  fallback = 0,
) {
  const parsed =
    Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function finiteOrNull(
  value,
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const parsed =
    Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : null;
}

function clamp(
  value,
  minimum = 0,
  maximum = 100,
) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      finiteNumber(value),
    ),
  );
}

function firstValue(
  source,
  paths,
  fallback = null,
) {
  for (const path of paths) {
    const value =
      path
        .split(".")
        .reduce(
          (current, key) =>
            current?.[key],
          source,
        );

    if (
      value !== undefined &&
      value !== null &&
      value !== ""
    ) {
      return value;
    }
  }

  return fallback;
}

function normalizeEngine({
  name,
  score,
  confidence,
  action,
  weight = 1,
} = {}) {
  return {
    name:
      String(
        name ?? "unknown",
      ),

    weight:
      Math.max(
        0,
        finiteNumber(
          weight,
          1,
        ),
      ),

    result: {
      score:
        clamp(
          score,
        ),

      confidence:
        clamp(
          confidence,
        ),

      action:
        String(
          action ?? "HOLD",
        ).toUpperCase(),
    },
  };
}

function marketEnvironmentReport(
  state = {},
) {
  const environment =
    state.marketEnvironment;

  const score =
    finiteOrNull(
      environment?.score,
    );

  if (score === null) {
    return null;
  }

  const availableCount =
    Math.max(
      0,
      finiteNumber(
        environment?.availableCount,
      ),
    );

  const requestedCount =
    Math.max(
      0,
      finiteNumber(
        environment?.requestedCount,
      ),
    );

  const coverage =
    requestedCount > 0
      ? Math.min(
          100,
          (availableCount /
            requestedCount) *
            100,
        )
      : 0;

  return {
    score:
      clamp(score),

    confidence:
      coverage,

    coverage,

    source:
      "market-context",
  };
}

function marketNewsItems(
  state = {},
) {
  return [
    ...(Array.isArray(
      state.context?.news,
    )
      ? state.context.news.map(
          (item) => ({
            ...item,
            type:
              item?.type ??
              "news",
          }),
        )
      : []),

    ...(Array.isArray(
      state.context?.disclosures,
    )
      ? state.context.disclosures.map(
          (item) => ({
            ...item,
            type:
              item?.type ??
              "tdnet",
          }),
        )
      : []),
  ];
}

export function buildMarketIntelligenceInput(
  state = {},
) {
  const explicit =
    state.marketIntelligenceInput ??
    state.marketIntelligence ??
    null;

  if (
    explicit &&
    typeof explicit === "object" &&
    !Array.isArray(explicit)
  ) {
    return explicit;
  }

  const result = {};
  const copiedReports = [
    "marketSnapshot",
    "breadth",
    "liquidity",
    "sectorStrength",
    "sectorRotation",
    "compositeMarket",
    "newsIntelligence",
    "volatility",
    "macro",
    "momentum",
    "previousSectorStrength",
  ];

  for (const key of copiedReports) {
    if (
      state[key] !== null &&
      state[key] !== undefined
    ) {
      result[key] = state[key];
    }
  }

  const observations =
    state.marketObservations ??
    state.observations ??
    null;

  if (Array.isArray(observations)) {
    result.observations =
      observations;
  }

  const marketData =
    state.marketData ??
    null;

  if (Array.isArray(marketData)) {
    result.marketData =
      marketData;
  }

  if (!result.compositeMarket) {
    const fallbackReport =
      marketEnvironmentReport(
        state,
      );

    if (fallbackReport) {
      result.compositeMarket =
        fallbackReport;
    }
  }

  if (!result.newsIntelligence) {
    const newsItems =
      marketNewsItems(
        state,
      );

    if (newsItems.length) {
      result.newsItems =
        newsItems;
    }
  }

  const quoteChange =
    finiteOrNull(
      state.quote?.changePercent,
    );

  if (quoteChange !== null) {
    result.quote = {
      ...state.quote,
      changePercent:
        quoteChange,
    };
  }

  const atrPercent =
    finiteOrNull(
      state.indicators?.atr?.percent ??
      state.indicators?.atrPercent,
    );

  if (atrPercent !== null) {
    result.technical = {
      ...(state.marketIntelligenceTechnical ?? {}),
      atrPercent,
    };
  }

  const hasSignal = [
    result.marketSnapshot,
    result.compositeMarket,
    result.breadth,
    result.liquidity,
    result.sectorStrength,
    result.newsIntelligence,
    result.newsItems,
    result.momentum,
    result.quote,
    result.marketData,
    result.observations,
  ].some(Boolean);

  return hasSignal
    ? result
    : null;
}

export function buildAIAnalysisInput({
  state = {},
  settings = {},
} = {}) {
  const symbol =
    firstValue(
      state,
      [
        "symbol",
        "ticker",
        "code",
        "quote.symbol",
      ],
      null,
    );

  const price =
    Math.max(
      0,
      finiteNumber(
        firstValue(
          state,
          [
            "price",
            "currentPrice",
            "quote.price",
            "market.price",
          ],
          0,
        ),
      ),
    );

  const technicalScore =
    clamp(
      firstValue(
        state,
        [
          "analysis.technicalScore",
          "analysis.totalScore",
          "technicalScore",
          "score",
        ],
        50,
      ),
    );

  const aiScore =
    clamp(
      firstValue(
        state,
        [
          "aiAnalysis.overallAiScore",
          "aiScore",
          "analysis.aiScore",
          "prediction.score",
        ],
        technicalScore,
      ),
    );

  const macroScore =
    clamp(
      firstValue(
        state,
        [
          "macro.score",
          "macroScore",
          "market.macroScore",
        ],
        50,
      ),
    );

  const confidence =
    clamp(
      firstValue(
        state,
        [
          "aiAnalysis.confidence.score",
          "prediction.confidence",
          "analysis.confidence",
          "confidence",
        ],
        50,
      ),
    );

  const riskScore =
    clamp(
      firstValue(
        state,
        [
          "risk.score",
          "riskScore",
          "analysis.riskScore",
        ],
        50,
      ),
    );

  const volatility =
    clamp(
      firstValue(
        state,
        [
          "indicators.atr.percent",
          "indicators.atrPercent",
          "volatility",
        ],
        20,
      ),
    );

  const marketIntelligence =
    buildMarketIntelligenceInput(
      state,
    );

  const engines = [
    normalizeEngine({
      name:
        "technical",

      score:
        technicalScore,

      confidence,

      action:
        technicalScore >= 70
          ? "BUY"
          : technicalScore <= 35
            ? "SELL"
            : "HOLD",

      weight:
        settings.weights
          ?.technical ??
        1,
    }),

    normalizeEngine({
      name:
        "ai",

      score:
        aiScore,

      confidence,

      action:
        aiScore >= 70
          ? "BUY"
          : aiScore <= 35
            ? "SELL"
            : "HOLD",

      weight:
        settings.weights?.ai ??
        1,
    }),

    normalizeEngine({
      name:
        "macro",

      score:
        macroScore,

      confidence:
        clamp(
          confidence * 0.9,
        ),

      action:
        macroScore >= 70
          ? "BUY"
          : macroScore <= 35
            ? "SELL"
            : "HOLD",

      weight:
        settings.weights
          ?.macro ??
        1,
    }),
  ];

  return {
    symbol,

    engines,

    historicalAccuracy:
      clamp(
        firstValue(
          state,
          [
            "performance.accuracy",
            "learning.accuracy",
            "historicalAccuracy",
          ],
          50,
        ),
      ),

    volatility,

    portfolioRisk: {
      riskPercent:
        Math.max(
          0,
          finiteNumber(
            firstValue(
              state,
              [
                "portfolioRisk.riskPercent",
                "risk.riskPercent",
                "portfolio.riskPercent",
              ],
              riskScore / 10,
            ),
          ),
        ),
    },

    limits: {
      maximumRiskPercent:
        Math.max(
          0,
          finiteNumber(
            settings.maximumRiskPercent,
            6,
          ),
        ),

      minimumConfidence:
        clamp(
          settings.minimumConfidence ??
          55,
        ),

      minimumScore:
        clamp(
          settings.minimumScore ??
          60,
        ),
    },

    capital:
      Math.max(
        0,
        finiteNumber(
          settings.capital ??
          state.capital,
          0,
        ),
      ),

    allocation:
      Math.min(
        1,
        Math.max(
          0,
          finiteNumber(
            settings.allocation ??
            state.allocation,
            0.25,
          ),
        ),
      ),

    price,

    lotSize:
      Math.max(
        1,
        Math.floor(
          finiteNumber(
            settings.lotSize ??
            state.lotSize,
            100,
          ),
        ),
      ),

    stopPercent:
      Math.max(
        0,
        finiteNumber(
          settings.stopPercent,
          5,
        ),
      ),

    targetPercent:
      Math.max(
        0,
        finiteNumber(
          settings.targetPercent,
          10,
        ),
      ),

    macro:
      firstValue(
        state,
        [
          "macro.sentiment",
          "market.macro",
        ],
        "NEUTRAL",
      ),

    regime:
      firstValue(
        state,
        [
          "regime.regime",
          "market.regime",
        ],
        "RANGE",
      ),

    learning:
      state.learning ?? {},

    predictionHorizon:
      Math.max(
        1,
        finiteNumber(
          firstValue(
            state,
            [
              "period",
              "prediction.period",
            ],
            5,
          ),
          5,
        ),
      ),

    marketIntelligenceWeight:
      Math.max(
        0,
        finiteNumber(
          settings.weights
            ?.marketIntelligence,
          1,
        ),
      ),

    marketIntelligence,

    captureMarketIntelligenceSnapshot:
      marketIntelligence !== null &&
      settings.marketIntelligence
        ?.captureHistoricalSnapshots !==
        false,

    atrPercent:
      finiteOrNull(
        state.indicators
          ?.atr
          ?.percent ??
        state.indicators
          ?.atrPercent,
      ),
  };
}

export function installAIAnalysisInputProvider({
  windowRef = globalThis.window,
  stateProvider,
  settingsProvider,
} = {}) {
  if (!windowRef) {
    return false;
  }

  windowRef.ArkBuildAIAnalysisInput =
    () =>
      buildAIAnalysisInput({
        state:
          typeof stateProvider ===
          "function"
            ? stateProvider()
            : windowRef
                .__ARK_LATEST_ANALYSIS__ ??
              windowRef
                .__ARK_ANALYSIS_STATE__ ??
              {},

        settings:
          typeof settingsProvider ===
          "function"
            ? settingsProvider()
            : windowRef
                .__ARK_ANALYSIS_SETTINGS__ ??
              {},
      });

  Object.defineProperty(
    windowRef,
    "__ARK_ANALYSIS_INPUT__",
    {
      configurable: true,

      get() {
        return windowRef
          .ArkBuildAIAnalysisInput();
      },
    },
  );

  return true;
}

if (
  typeof window !== "undefined"
) {
  installAIAnalysisInputProvider({
    windowRef:
      window,
  });
}
