export const MACRO_RISK_ENGINE_V3_VERSION =
  "macro-risk-engine-v3";

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
      "Macro risk timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function normalizeInput(
  input = {},
) {
  return {
    growthScore:
      clamp(
        finiteNumber(
          input.growthScore,
          50,
        ),
        0,
        100,
      ),

    inflationScore:
      clamp(
        finiteNumber(
          input.inflationScore,
          50,
        ),
        0,
        100,
      ),

    policyTightness:
      clamp(
        finiteNumber(
          input.policyTightness,
          50,
        ),
        0,
        100,
      ),

    liquidityScore:
      clamp(
        finiteNumber(
          input.liquidityScore,
          50,
        ),
        0,
        100,
      ),

    creditStress:
      clamp(
        finiteNumber(
          input.creditStress,
          20,
        ),
        0,
        100,
      ),

    volatilityIndex:
      Math.max(
        0,
        finiteNumber(
          input.volatilityIndex,
          20,
        ),
      ),

    yieldCurveSpread:
      finiteNumber(
        input.yieldCurveSpread,
        0,
      ),

    currencyStress:
      clamp(
        finiteNumber(
          input.currencyStress,
          20,
        ),
        0,
        100,
      ),

    commodityShock:
      clamp(
        finiteNumber(
          input.commodityShock,
          20,
        ),
        0,
        100,
      ),

    geopoliticalRisk:
      clamp(
        finiteNumber(
          input.geopoliticalRisk,
          20,
        ),
        0,
        100,
      ),

    earningsRevision:
      clamp(
        finiteNumber(
          input.earningsRevision,
          50,
        ),
        0,
        100,
      ),

    marketBreadth:
      clamp(
        finiteNumber(
          input.marketBreadth,
          50,
        ),
        0,
        100,
      ),

    regime:
      String(
        input.regime ??
        "UNKNOWN",
      )
        .trim()
        .toUpperCase(),
  };
}

function calculateGrowthRisk(
  input,
) {
  let score =
    100 -
    input.growthScore;

  if (
    input.earningsRevision <
    40
  ) {
    score +=
      (
        40 -
        input.earningsRevision
      ) *
      0.8;
  }

  if (
    input.yieldCurveSpread <
    0
  ) {
    score +=
      Math.min(
        25,
        Math.abs(
          input.yieldCurveSpread,
        ) *
          12,
      );
  }

  return clamp(
    score,
    0,
    100,
  );
}

function calculateInflationRisk(
  input,
) {
  const inflationPressure =
    input.inflationScore;

  const commodityPressure =
    input.commodityShock *
    0.35;

  const policyPressure =
    input.policyTightness *
    0.25;

  return clamp(
    inflationPressure *
      0.55 +
    commodityPressure +
    policyPressure,
    0,
    100,
  );
}

function calculateLiquidityRisk(
  input,
) {
  return clamp(
    (
      100 -
      input.liquidityScore
    ) *
      0.55 +
    input.policyTightness *
      0.25 +
    input.creditStress *
      0.2,
    0,
    100,
  );
}

function calculateMarketStress(
  input,
) {
  const volatilityRisk =
    clamp(
      (
        input.volatilityIndex -
        12
      ) *
        3,
      0,
      100,
    );

  const breadthRisk =
    100 -
    input.marketBreadth;

  let regimePenalty = 0;

  if (
    [
      "BEAR",
      "STRONG_BEAR",
    ].includes(
      input.regime,
    )
  ) {
    regimePenalty = 20;
  }

  if (
    [
      "CRASH",
      "HIGH_VOLATILITY",
    ].includes(
      input.regime,
    )
  ) {
    regimePenalty = 35;
  }

  return clamp(
    volatilityRisk *
      0.45 +
    breadthRisk *
      0.35 +
    regimePenalty,
    0,
    100,
  );
}

function calculateExternalRisk(
  input,
) {
  return clamp(
    input.geopoliticalRisk *
      0.45 +
    input.currencyStress *
      0.3 +
    input.commodityShock *
      0.25,
    0,
    100,
  );
}

function classifyRisk(
  score,
) {
  if (score >= 80) {
    return "CRITICAL";
  }

  if (score >= 65) {
    return "HIGH";
  }

  if (score >= 45) {
    return "MODERATE";
  }

  if (score >= 25) {
    return "LOW";
  }

  return "VERY_LOW";
}

function riskAction(
  level,
) {
  const actions = {
    VERY_LOW: {
      stance:
        "RISK_ON",

      positionMultiplier:
        1,

      newTrades:
        "ALLOW",

      hedge:
        "OPTIONAL",
    },

    LOW: {
      stance:
        "CAUTIOUS_RISK_ON",

      positionMultiplier:
        0.85,

      newTrades:
        "ALLOW",

      hedge:
        "LIGHT",
    },

    MODERATE: {
      stance:
        "NEUTRAL",

      positionMultiplier:
        0.6,

      newTrades:
        "SELECTIVE",

      hedge:
        "MODERATE",
    },

    HIGH: {
      stance:
        "RISK_OFF",

      positionMultiplier:
        0.3,

      newTrades:
        "RESTRICT",

      hedge:
        "HIGH",
    },

    CRITICAL: {
      stance:
        "CAPITAL_PRESERVATION",

      positionMultiplier:
        0,

      newTrades:
        "BLOCK",

      hedge:
        "MAXIMUM",
    },
  };

  return clone(
    actions[
      level
    ],
  );
}

function buildReasons(
  input,
  components,
) {
  const reasons = [];

  if (
    components.growthRisk >=
    65
  ) {
    reasons.push(
      "GROWTH_SLOWDOWN_RISK",
    );
  }

  if (
    components.inflationRisk >=
    65
  ) {
    reasons.push(
      "INFLATION_PRESSURE",
    );
  }

  if (
    components.liquidityRisk >=
    65
  ) {
    reasons.push(
      "LIQUIDITY_TIGHTENING",
    );
  }

  if (
    components.marketStress >=
    65
  ) {
    reasons.push(
      "MARKET_STRESS",
    );
  }

  if (
    components.externalRisk >=
    65
  ) {
    reasons.push(
      "EXTERNAL_SHOCK_RISK",
    );
  }

  if (
    input.creditStress >=
    70
  ) {
    reasons.push(
      "CREDIT_STRESS",
    );
  }

  if (
    input.volatilityIndex >=
    35
  ) {
    reasons.push(
      "EXTREME_VOLATILITY",
    );
  }

  if (
    input.yieldCurveSpread <
    0
  ) {
    reasons.push(
      "INVERTED_YIELD_CURVE",
    );
  }

  if (
    reasons.length ===
    0
  ) {
    reasons.push(
      "NO_MAJOR_MACRO_STRESS",
    );
  }

  return reasons;
}

export function evaluateMacroRisk({
  input = {},
  timestamp =
    new Date().toISOString(),
  criticalBlockThreshold = 80,
} = {}) {
  const evaluatedAt =
    normalizeTimestamp(
      timestamp,
    );

  const normalized =
    normalizeInput(
      input,
    );

  const components = {
    growthRisk:
      calculateGrowthRisk(
        normalized,
      ),

    inflationRisk:
      calculateInflationRisk(
        normalized,
      ),

    liquidityRisk:
      calculateLiquidityRisk(
        normalized,
      ),

    marketStress:
      calculateMarketStress(
        normalized,
      ),

    externalRisk:
      calculateExternalRisk(
        normalized,
      ),
  };

  const score =
    clamp(
      components.growthRisk *
        0.2 +
      components.inflationRisk *
        0.18 +
      components.liquidityRisk *
        0.24 +
      components.marketStress *
        0.23 +
      components.externalRisk *
        0.15,
      0,
      100,
    );

  const level =
    classifyRisk(
      score,
    );

  const action =
    riskAction(
      level,
    );

  const reasons =
    buildReasons(
      normalized,
      components,
    );

  const blockers = [];

  if (
    score >=
    criticalBlockThreshold
  ) {
    blockers.push(
      "CRITICAL_MACRO_RISK",
    );
  }

  if (
    normalized.creditStress >=
    90
  ) {
    blockers.push(
      "SYSTEMIC_CREDIT_STRESS",
    );
  }

  if (
    normalized.volatilityIndex >=
    50
  ) {
    blockers.push(
      "EXTREME_MARKET_VOLATILITY",
    );
  }

  const confidenceInputs = [
    normalized.growthScore,
    normalized.inflationScore,
    normalized.policyTightness,
    normalized.liquidityScore,
    normalized.creditStress,
    normalized.currencyStress,
    normalized.geopoliticalRisk,
    normalized.marketBreadth,
  ];

  const dispersion =
    Math.max(
      ...confidenceInputs,
    ) -
    Math.min(
      ...confidenceInputs,
    );

  const confidence =
    clamp(
      85 -
      dispersion *
        0.25 +
      Math.abs(
        score -
        50,
      ) *
        0.2,
      35,
      95,
    );

  return {
    version:
      MACRO_RISK_ENGINE_V3_VERSION,

    evaluatedAt,

    status:
      blockers.length === 0
        ? "READY"
        : "BLOCKED",

    score:
      round(
        score,
      ),

    level,

    confidence:
      round(
        confidence,
      ),

    action,

    blockers,

    reasons,

    components: {
      growthRisk:
        round(
          components.growthRisk,
        ),

      inflationRisk:
        round(
          components.inflationRisk,
        ),

      liquidityRisk:
        round(
          components.liquidityRisk,
        ),

      marketStress:
        round(
          components.marketStress,
        ),

      externalRisk:
        round(
          components.externalRisk,
        ),
    },

    input:
      normalized,
  };
}

export function compareMacroRisk({
  previous,
  current,
} = {}) {
  if (
    !previous ||
    !current
  ) {
    return {
      changed:
        false,

      trend:
        "UNKNOWN",

      scoreChange:
        0,

      levelChanged:
        false,
    };
  }

  const scoreChange =
    finiteNumber(
      current.score,
      0,
    ) -
    finiteNumber(
      previous.score,
      0,
    );

  let trend =
    "STABLE";

  if (scoreChange >= 5) {
    trend =
      "DETERIORATING";
  }

  if (scoreChange <= -5) {
    trend =
      "IMPROVING";
  }

  return {
    changed:
      Math.abs(
        scoreChange,
      ) >= 5 ||
      previous.level !==
        current.level,

    trend,

    scoreChange:
      round(
        scoreChange,
      ),

    levelChanged:
      previous.level !==
      current.level,

    previousLevel:
      previous.level,

    currentLevel:
      current.level,
  };
}

export class MacroRiskEngineV3 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  evaluate(input = {}) {
    const result =
      evaluateMacroRisk({
        ...this.config,
        ...input,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
  }

  compareLatest() {
    if (
      this.history.length <
      2
    ) {
      return compareMacroRisk({
        previous:
          null,

        current:
          this.history.at(-1) ??
          null,
      });
    }

    return compareMacroRisk({
      previous:
        this.history.at(-2),

      current:
        this.history.at(-1),
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

export const macroRiskEngineV3 =
  new MacroRiskEngineV3();

export default evaluateMacroRisk;