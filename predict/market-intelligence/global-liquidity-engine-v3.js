export const GLOBAL_LIQUIDITY_ENGINE_V3_VERSION =
  "global-liquidity-engine-v3";

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
      "Global liquidity timestamp is invalid.",
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
    centralBankBalanceSheetGrowth:
      finiteNumber(
        input.centralBankBalanceSheetGrowth,
        0,
      ),

    moneySupplyGrowth:
      finiteNumber(
        input.moneySupplyGrowth,
        0,
      ),

    realRate:
      finiteNumber(
        input.realRate,
        0,
      ),

    policyRateChange:
      finiteNumber(
        input.policyRateChange,
        0,
      ),

    creditGrowth:
      finiteNumber(
        input.creditGrowth,
        0,
      ),

    dollarIndexChange:
      finiteNumber(
        input.dollarIndexChange,
        0,
      ),

    yenLiquidityChange:
      finiteNumber(
        input.yenLiquidityChange,
        0,
      ),

    treasuryLiquidityChange:
      finiteNumber(
        input.treasuryLiquidityChange,
        0,
      ),

    reverseRepoChange:
      finiteNumber(
        input.reverseRepoChange,
        0,
      ),

    fundingStress:
      clamp(
        finiteNumber(
          input.fundingStress,
          20,
        ),
        0,
        100,
      ),

    creditSpread:
      Math.max(
        0,
        finiteNumber(
          input.creditSpread,
          1,
        ),
      ),

    volatilityIndex:
      Math.max(
        0,
        finiteNumber(
          input.volatilityIndex,
          20,
        ),
      ),

    foreignFlow:
      finiteNumber(
        input.foreignFlow,
        0,
      ),

    equityFlow:
      finiteNumber(
        input.equityFlow,
        0,
      ),

    bondFlow:
      finiteNumber(
        input.bondFlow,
        0,
      ),

    cryptoLiquidity:
      finiteNumber(
        input.cryptoLiquidity,
        0,
      ),

    emergingMarketFlow:
      finiteNumber(
        input.emergingMarketFlow,
        0,
      ),
  };
}

function calculateMonetaryScore(
  input,
) {
  return clamp(
    input.centralBankBalanceSheetGrowth *
      3 +
    input.moneySupplyGrowth *
      3 +
    input.creditGrowth *
      2 -
    input.realRate *
      5 -
    input.policyRateChange *
      6,
    -100,
    100,
  );
}

function calculateSystemLiquidityScore(
  input,
) {
  return clamp(
    input.treasuryLiquidityChange *
      2 -
    input.reverseRepoChange *
      2 +
    input.yenLiquidityChange *
      2 -
    input.dollarIndexChange *
      4,
    -100,
    100,
  );
}

function calculateFlowScore(
  input,
) {
  return clamp(
    input.foreignFlow *
      1.5 +
    input.equityFlow *
      2 +
    input.bondFlow *
      0.8 +
    input.cryptoLiquidity *
      0.8 +
    input.emergingMarketFlow *
      1.2,
    -100,
    100,
  );
}

function calculateStressPenalty(
  input,
) {
  const creditPenalty =
    clamp(
      (
        input.creditSpread -
        1
      ) *
        18,
      0,
      45,
    );

  const volatilityPenalty =
    clamp(
      (
        input.volatilityIndex -
        15
      ) *
        2,
      0,
      45,
    );

  return clamp(
    input.fundingStress *
      0.45 +
    creditPenalty *
      0.3 +
    volatilityPenalty *
      0.25,
    0,
    100,
  );
}

function classifyLiquidity(
  score,
) {
  if (score >= 65) {
    return "STRONGLY_EXPANSIONARY";
  }

  if (score >= 25) {
    return "EXPANSIONARY";
  }

  if (score > -25) {
    return "NEUTRAL";
  }

  if (score > -65) {
    return "CONTRACTIONARY";
  }

  return "SEVERELY_CONTRACTIONARY";
}

function actionForLiquidity(
  regime,
) {
  const actions = {
    STRONGLY_EXPANSIONARY: {
      stance:
        "RISK_ON",

      positionMultiplier:
        1,

      growthAssets:
        "OVERWEIGHT",

      defensiveAssets:
        "UNDERWEIGHT",
    },

    EXPANSIONARY: {
      stance:
        "CAUTIOUS_RISK_ON",

      positionMultiplier:
        0.85,

      growthAssets:
        "OVERWEIGHT",

      defensiveAssets:
        "NEUTRAL",
    },

    NEUTRAL: {
      stance:
        "BALANCED",

      positionMultiplier:
        0.65,

      growthAssets:
        "NEUTRAL",

      defensiveAssets:
        "NEUTRAL",
    },

    CONTRACTIONARY: {
      stance:
        "RISK_OFF",

      positionMultiplier:
        0.35,

      growthAssets:
        "UNDERWEIGHT",

      defensiveAssets:
        "OVERWEIGHT",
    },

    SEVERELY_CONTRACTIONARY: {
      stance:
        "CAPITAL_PRESERVATION",

      positionMultiplier:
        0,

      growthAssets:
        "AVOID",

      defensiveAssets:
        "OVERWEIGHT",
    },
  };

  return clone(
    actions[
      regime
    ],
  );
}

function buildReasons(
  input,
  components,
) {
  const reasons = [];

  if (
    components.monetaryScore >=
    35
  ) {
    reasons.push(
      "MONETARY_EXPANSION",
    );
  }

  if (
    components.monetaryScore <=
    -35
  ) {
    reasons.push(
      "MONETARY_TIGHTENING",
    );
  }

  if (
    components.systemLiquidityScore >=
    35
  ) {
    reasons.push(
      "SYSTEM_LIQUIDITY_INFLOW",
    );
  }

  if (
    components.systemLiquidityScore <=
    -35
  ) {
    reasons.push(
      "SYSTEM_LIQUIDITY_DRAIN",
    );
  }

  if (
    components.flowScore >=
    35
  ) {
    reasons.push(
      "POSITIVE_CAPITAL_FLOWS",
    );
  }

  if (
    components.flowScore <=
    -35
  ) {
    reasons.push(
      "CAPITAL_OUTFLOWS",
    );
  }

  if (
    components.stressPenalty >=
    65
  ) {
    reasons.push(
      "FUNDING_MARKET_STRESS",
    );
  }

  if (
    input.dollarIndexChange >=
    3
  ) {
    reasons.push(
      "DOLLAR_LIQUIDITY_PRESSURE",
    );
  }

  if (
    reasons.length ===
    0
  ) {
    reasons.push(
      "BALANCED_GLOBAL_LIQUIDITY",
    );
  }

  return reasons;
}

export function evaluateGlobalLiquidity({
  input = {},
  timestamp =
    new Date().toISOString(),
  blockThreshold = -70,
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
    monetaryScore:
      calculateMonetaryScore(
        normalized,
      ),

    systemLiquidityScore:
      calculateSystemLiquidityScore(
        normalized,
      ),

    flowScore:
      calculateFlowScore(
        normalized,
      ),

    stressPenalty:
      calculateStressPenalty(
        normalized,
      ),
  };

  const score =
    clamp(
      components.monetaryScore *
        0.35 +
      components.systemLiquidityScore *
        0.3 +
      components.flowScore *
        0.2 -
      components.stressPenalty *
        0.35,
      -100,
      100,
    );

  const regime =
    classifyLiquidity(
      score,
    );

  const action =
    actionForLiquidity(
      regime,
    );

  const blockers = [];

  if (
    score <=
    blockThreshold
  ) {
    blockers.push(
      "SEVERE_LIQUIDITY_CONTRACTION",
    );
  }

  if (
    normalized.fundingStress >=
    90
  ) {
    blockers.push(
      "SYSTEMIC_FUNDING_STRESS",
    );
  }

  if (
    normalized.creditSpread >=
    5
  ) {
    blockers.push(
      "CREDIT_MARKET_DISLOCATION",
    );
  }

  const confidence =
    clamp(
      55 +
      Math.abs(
        score,
      ) *
        0.25 +
      Math.min(
        15,
        Math.abs(
          components.monetaryScore -
          components.systemLiquidityScore,
        ) *
          -0.1 +
        15,
      ),
      35,
      95,
    );

  return {
    version:
      GLOBAL_LIQUIDITY_ENGINE_V3_VERSION,

    evaluatedAt,

    status:
      blockers.length === 0
        ? "READY"
        : "BLOCKED",

    score:
      round(
        score,
      ),

    regime,

    confidence:
      round(
        confidence,
      ),

    action,

    blockers,

    reasons:
      buildReasons(
        normalized,
        components,
      ),

    components: {
      monetaryScore:
        round(
          components.monetaryScore,
        ),

      systemLiquidityScore:
        round(
          components.systemLiquidityScore,
        ),

      flowScore:
        round(
          components.flowScore,
        ),

      stressPenalty:
        round(
          components.stressPenalty,
        ),
    },

    input:
      normalized,
  };
}

export function compareGlobalLiquidity({
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

      regimeChanged:
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

  if (scoreChange >= 8) {
    trend =
      "IMPROVING";
  }

  if (scoreChange <= -8) {
    trend =
      "DETERIORATING";
  }

  return {
    changed:
      Math.abs(
        scoreChange,
      ) >= 8 ||
      previous.regime !==
        current.regime,

    trend,

    scoreChange:
      round(
        scoreChange,
      ),

    regimeChanged:
      previous.regime !==
      current.regime,

    previousRegime:
      previous.regime,

    currentRegime:
      current.regime,
  };
}

export class GlobalLiquidityEngineV3 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  evaluate(input = {}) {
    const result =
      evaluateGlobalLiquidity({
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
      return compareGlobalLiquidity({
        previous:
          null,

        current:
          this.history.at(-1) ??
          null,
      });
    }

    return compareGlobalLiquidity({
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

export const globalLiquidityEngineV3 =
  new GlobalLiquidityEngineV3();

export default evaluateGlobalLiquidity;