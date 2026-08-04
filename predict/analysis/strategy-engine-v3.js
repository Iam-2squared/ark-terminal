export const STRATEGY_ENGINE_V3_VERSION =
  "strategy-engine-v3";

const ACTIONS =
  Object.freeze({
    BUY:
      "BUY",

    SELL:
      "SELL",

    HOLD:
      "HOLD",

    BLOCK:
      "BLOCK",
  });

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function finiteNumber(
  value,
  fallback = 0,
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return fallback;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function positiveNumber(
  value,
  fallback = 0,
) {
  return Math.max(
    0,
    finiteNumber(
      value,
      fallback,
    ),
  );
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
  digits = 6,
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
      "Strategy timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function normalizeSymbol(value) {
  const symbol =
    String(
      value ??
      "",
    )
      .trim()
      .toUpperCase();

  if (!symbol) {
    throw new TypeError(
      "Strategy symbol is required.",
    );
  }

  return symbol;
}

function normalizeRegime(value) {
  const regime =
    String(
      value ??
      "NEUTRAL",
    )
      .trim()
      .toUpperCase();

  const supported =
    new Set([
      "BULL",
      "BEAR",
      "SIDEWAYS",
      "HIGH_VOLATILITY",
      "LOW_VOLATILITY",
      "RISK_ON",
      "RISK_OFF",
      "NEUTRAL",
    ]);

  return supported.has(regime)
    ? regime
    : "NEUTRAL";
}

function normalizeSignal(
  signal = {},
) {
  return {
    name:
      String(
        signal.name ??
        "UNKNOWN",
      )
        .trim()
        .toUpperCase(),

    score:
      clamp(
        finiteNumber(
          signal.score,
          50,
        ),
        0,
        100,
      ),

    confidence:
      clamp(
        finiteNumber(
          signal.confidence,
          50,
        ),
        0,
        100,
      ),

    weight:
      positiveNumber(
        signal.weight,
        1,
      ),

    direction:
      String(
        signal.direction ??
        "NEUTRAL",
      )
        .trim()
        .toUpperCase(),

    metadata:
      clone(
        signal.metadata ??
        {},
      ),
  };
}

function normalizeContext(
  context = {},
) {
  return {
    symbol:
      normalizeSymbol(
        context.symbol,
      ),

    price:
      positiveNumber(
        context.price,
        0,
      ),

    regime:
      normalizeRegime(
        context.regime,
      ),

    riskScore:
      clamp(
        finiteNumber(
          context.riskScore,
          50,
        ),
        0,
        100,
      ),

    marketScore:
      clamp(
        finiteNumber(
          context.marketScore,
          50,
        ),
        0,
        100,
      ),

    liquidityScore:
      clamp(
        finiteNumber(
          context.liquidityScore,
          50,
        ),
        0,
        100,
      ),

    portfolioExposurePercent:
      positiveNumber(
        context.portfolioExposurePercent,
        0,
      ),

    drawdownPercent:
      positiveNumber(
        context.drawdownPercent,
        0,
      ),

    volatilityPercent:
      positiveNumber(
        context.volatilityPercent,
        0,
      ),

    currentPosition:
      finiteNumber(
        context.currentPosition,
        0,
      ),

    signals:
      Array.isArray(
        context.signals,
      )
        ? context.signals.map(
            normalizeSignal,
          )
        : [],
  };
}

function scoreSignal(
  signal,
) {
  const directionMultiplier =
    signal.direction === "BULLISH"
      ? 1
      : signal.direction === "BEARISH"
        ? -1
        : 0;

  const normalizedScore =
    (
      signal.score -
      50
    ) /
    50;

  return (
    normalizedScore *
    signal.confidence /
    100 *
    signal.weight *
    directionMultiplier
  );
}

function aggregateSignals(
  signals,
) {
  if (signals.length === 0) {
    return {
      score:
        0,

      confidence:
        0,

      agreement:
        0,

      bullishCount:
        0,

      bearishCount:
        0,

      neutralCount:
        0,
    };
  }

  let weightedScore = 0;
  let totalWeight = 0;
  let bullishCount = 0;
  let bearishCount = 0;
  let neutralCount = 0;

  for (
    const signal of
    signals
  ) {
    const effectiveWeight =
      Math.max(
        0.0001,
        signal.weight,
      );

    weightedScore +=
      scoreSignal(
        signal,
      );

    totalWeight +=
      effectiveWeight;

    if (
      signal.direction ===
      "BULLISH"
    ) {
      bullishCount += 1;
    }
    else if (
      signal.direction ===
      "BEARISH"
    ) {
      bearishCount += 1;
    }
    else {
      neutralCount += 1;
    }
  }

  const score =
    totalWeight <= 0
      ? 0
      : weightedScore /
        totalWeight;

  const directionalCount =
    bullishCount +
    bearishCount;

  const agreement =
    directionalCount === 0
      ? 0
      : Math.max(
          bullishCount,
          bearishCount,
        ) /
        directionalCount *
        100;

  const confidence =
    signals.reduce(
      (
        total,
        signal,
      ) =>
        total +
        signal.confidence,
      0,
    ) /
    signals.length;

  return {
    score:
      round(
        score,
      ),

    confidence:
      round(
        confidence,
      ),

    agreement:
      round(
        agreement,
      ),

    bullishCount,

    bearishCount,

    neutralCount,
  };
}

function regimeAdjustment(
  regime,
) {
  switch (regime) {
    case "BULL":
    case "RISK_ON":
      return 12;

    case "BEAR":
    case "RISK_OFF":
      return -15;

    case "HIGH_VOLATILITY":
      return -10;

    case "LOW_VOLATILITY":
      return 5;

    case "SIDEWAYS":
      return -3;

    default:
      return 0;
  }
}

function determineAction({
  finalScore,
  blockers,
  currentPosition,
}) {
  if (blockers.length > 0) {
    return ACTIONS.BLOCK;
  }

  if (finalScore >= 65) {
    return ACTIONS.BUY;
  }

  if (finalScore <= 35) {
    return currentPosition > 0
      ? ACTIONS.SELL
      : ACTIONS.HOLD;
  }

  return ACTIONS.HOLD;
}

function buildReasons({
  action,
  context,
  aggregate,
  finalScore,
}) {
  const reasons = [];

  if (
    aggregate.bullishCount >
    aggregate.bearishCount
  ) {
    reasons.push(
      "BULLISH_SIGNAL_MAJORITY",
    );
  }

  if (
    aggregate.bearishCount >
    aggregate.bullishCount
  ) {
    reasons.push(
      "BEARISH_SIGNAL_MAJORITY",
    );
  }

  if (
    aggregate.agreement >= 70
  ) {
    reasons.push(
      "HIGH_SIGNAL_AGREEMENT",
    );
  }

  if (
    context.marketScore >= 65
  ) {
    reasons.push(
      "SUPPORTIVE_MARKET_CONTEXT",
    );
  }

  if (
    context.marketScore <= 35
  ) {
    reasons.push(
      "WEAK_MARKET_CONTEXT",
    );
  }

  if (
    context.liquidityScore >= 65
  ) {
    reasons.push(
      "STRONG_LIQUIDITY",
    );
  }

  if (
    context.regime === "BULL" ||
    context.regime === "RISK_ON"
  ) {
    reasons.push(
      "FAVORABLE_MARKET_REGIME",
    );
  }

  if (
    context.regime === "BEAR" ||
    context.regime === "RISK_OFF"
  ) {
    reasons.push(
      "DEFENSIVE_MARKET_REGIME",
    );
  }

  if (
    finalScore >= 65
  ) {
    reasons.push(
      "COMPOSITE_SCORE_BUY_ZONE",
    );
  }

  if (
    finalScore <= 35
  ) {
    reasons.push(
      "COMPOSITE_SCORE_SELL_ZONE",
    );
  }

  if (
    action === ACTIONS.HOLD
  ) {
    reasons.push(
      "INSUFFICIENT_EDGE",
    );
  }

  return [
    ...new Set(
      reasons,
    ),
  ];
}

export function evaluateStrategy({
  context = {},
  config = {},
  timestamp =
    new Date().toISOString(),
} = {}) {
  const evaluatedAt =
    normalizeTimestamp(
      timestamp,
    );

  const normalized =
    normalizeContext(
      context,
    );

  if (normalized.price <= 0) {
    throw new TypeError(
      "Strategy price must be greater than zero.",
    );
  }

  const minimumConfidence =
    positiveNumber(
      config.minimumConfidence,
      55,
    );

  const maximumRiskScore =
    positiveNumber(
      config.maximumRiskScore,
      75,
    );

  const maximumDrawdownPercent =
    positiveNumber(
      config.maximumDrawdownPercent,
      15,
    );

  const maximumExposurePercent =
    positiveNumber(
      config.maximumExposurePercent,
      90,
    );

  const minimumLiquidityScore =
    positiveNumber(
      config.minimumLiquidityScore,
      30,
    );

  const aggregate =
    aggregateSignals(
      normalized.signals,
    );

  const signalComponent =
    clamp(
      50 +
      aggregate.score *
      50,
      0,
      100,
    );

  const regimeComponent =
    regimeAdjustment(
      normalized.regime,
    );

  const riskPenalty =
    normalized.riskScore *
    0.25;

  const volatilityPenalty =
    Math.min(
      20,
      normalized.volatilityPercent *
      0.5,
    );

  const finalScore =
    clamp(
      signalComponent *
        0.5 +
      normalized.marketScore *
        0.2 +
      normalized.liquidityScore *
        0.15 +
      aggregate.confidence *
        0.15 +
      regimeComponent -
      riskPenalty -
      volatilityPenalty,
      0,
      100,
    );

  const blockers = [];
  const warnings = [];

  if (
    normalized.riskScore >
    maximumRiskScore
  ) {
    blockers.push(
      "RISK_SCORE_TOO_HIGH",
    );
  }

  if (
    normalized.drawdownPercent >=
    maximumDrawdownPercent
  ) {
    blockers.push(
      "DRAWDOWN_LIMIT_REACHED",
    );
  }

  if (
    normalized.portfolioExposurePercent >=
    maximumExposurePercent
  ) {
    blockers.push(
      "PORTFOLIO_EXPOSURE_LIMIT_REACHED",
    );
  }

  if (
    normalized.liquidityScore <
    minimumLiquidityScore
  ) {
    blockers.push(
      "INSUFFICIENT_LIQUIDITY",
    );
  }

  if (
    aggregate.confidence <
    minimumConfidence
  ) {
    warnings.push(
      "LOW_SIGNAL_CONFIDENCE",
    );
  }

  if (
    aggregate.agreement <
    50
  ) {
    warnings.push(
      "LOW_SIGNAL_AGREEMENT",
    );
  }

  if (
    normalized.regime ===
    "HIGH_VOLATILITY"
  ) {
    warnings.push(
      "HIGH_VOLATILITY_REGIME",
    );
  }

  const action =
    determineAction({
      finalScore,

      blockers,

      currentPosition:
        normalized.currentPosition,
    });

  const positionMultiplier =
    action === ACTIONS.BLOCK
      ? 0
      : warnings.length >= 2
        ? 0.5
        : normalized.regime === "HIGH_VOLATILITY"
          ? 0.5
          : finalScore >= 80
            ? 1
            : finalScore >= 65
              ? 0.75
              : 0;

  const reasons =
    buildReasons({
      action,

      context:
        normalized,

      aggregate,

      finalScore,
    });

  return {
    version:
      STRATEGY_ENGINE_V3_VERSION,

    evaluatedAt,

    symbol:
      normalized.symbol,

    action,

    finalScore:
      round(
        finalScore,
      ),

    confidence:
      aggregate.confidence,

    agreement:
      aggregate.agreement,

    positionMultiplier,

    blockers: [
      ...new Set(
        blockers,
      ),
    ],

    warnings: [
      ...new Set(
        warnings,
      ),
    ],

    reasons,

    components: {
      signalComponent:
        round(
          signalComponent,
        ),

      marketComponent:
        round(
          normalized.marketScore,
        ),

      liquidityComponent:
        round(
          normalized.liquidityScore,
        ),

      regimeAdjustment:
        round(
          regimeComponent,
        ),

      riskPenalty:
        round(
          riskPenalty,
        ),

      volatilityPenalty:
        round(
          volatilityPenalty,
        ),
    },

    signalSummary:
      aggregate,

    context: {
      regime:
        normalized.regime,

      riskScore:
        normalized.riskScore,

      marketScore:
        normalized.marketScore,

      liquidityScore:
        normalized.liquidityScore,

      portfolioExposurePercent:
        normalized.portfolioExposurePercent,

      drawdownPercent:
        normalized.drawdownPercent,

      volatilityPercent:
        normalized.volatilityPercent,

      currentPosition:
        normalized.currentPosition,
    },
  };
}

export function rankStrategies({
  candidates = [],
  config = {},
  timestamp =
    new Date().toISOString(),
} = {}) {
  const evaluated =
    candidates.map(
      (
        context,
      ) =>
        evaluateStrategy({
          context,
          config,
          timestamp,
        }),
    );

  return evaluated.sort(
    (
      a,
      b,
    ) => {
      if (
        a.action === ACTIONS.BLOCK &&
        b.action !== ACTIONS.BLOCK
      ) {
        return 1;
      }

      if (
        b.action === ACTIONS.BLOCK &&
        a.action !== ACTIONS.BLOCK
      ) {
        return -1;
      }

      return (
        b.finalScore -
        a.finalScore
      );
    },
  );
}

export class StrategyEngineV3 {
  constructor(config = {}) {
    this.config = {
      minimumConfidence:
        55,

      maximumRiskScore:
        75,

      maximumDrawdownPercent:
        15,

      maximumExposurePercent:
        90,

      minimumLiquidityScore:
        30,

      ...config,
    };

    this.history = [];
    this.enabled = true;
  }

  enable() {
    this.enabled = true;

    return this.getState();
  }

  disable() {
    this.enabled = false;

    return this.getState();
  }

  evaluate(input = {}) {
    if (!this.enabled) {
      const result = {
        version:
          STRATEGY_ENGINE_V3_VERSION,

        evaluatedAt:
          normalizeTimestamp(
            input.timestamp,
          ),

        symbol:
          normalizeSymbol(
            input.context?.symbol,
          ),

        action:
          ACTIONS.BLOCK,

        finalScore:
          0,

        confidence:
          0,

        agreement:
          0,

        positionMultiplier:
          0,

        blockers: [
          "STRATEGY_ENGINE_DISABLED",
        ],

        warnings: [],

        reasons: [
          "ENGINE_DISABLED",
        ],
      };

      this.history.push(
        clone(
          result,
        ),
      );

      return clone(
        result,
      );
    }

    const result =
      evaluateStrategy({
        ...input,

        config: {
          ...this.config,
          ...input.config,
        },
      });

    this.history.push(
      clone(
        result,
      ),
    );

    return clone(
      result,
    );
  }

  rank({
    candidates = [],
    timestamp =
      new Date().toISOString(),
    config = {},
  } = {}) {
    return rankStrategies({
      candidates,

      timestamp,

      config: {
        ...this.config,
        ...config,
      },
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

  getState() {
    return {
      version:
        STRATEGY_ENGINE_V3_VERSION,

      enabled:
        this.enabled,

      historyCount:
        this.history.length,

      config:
        clone(
          this.config,
        ),
    };
  }

  snapshot() {
    return {
      ...this.getState(),

      history:
        clone(
          this.history,
        ),
    };
  }

  restore(snapshot) {
    if (
      !snapshot ||
      typeof snapshot !==
        "object"
    ) {
      throw new TypeError(
        "Strategy snapshot is required.",
      );
    }

    this.enabled =
      snapshot.enabled !==
      false;

    this.config = {
      ...this.config,
      ...clone(
        snapshot.config ??
        {},
      ),
    };

    this.history =
      clone(
        snapshot.history ??
        [],
      );

    return this.snapshot();
  }

  reset() {
    this.history = [];
    this.enabled = true;

    return this.getState();
  }
}

export const strategyEngineV3 =
  new StrategyEngineV3();

export default StrategyEngineV3;