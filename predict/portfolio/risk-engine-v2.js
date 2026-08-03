export const RISK_ENGINE_V2_VERSION =
  "risk-engine-v2";

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
          value - mean
        ) ** 2,
      0,
    ) /
    values.length;

  return Math.sqrt(
    variance,
  );
}

function percentile(
  values,
  probability,
) {
  const sorted =
    values
      .filter(
        Number.isFinite,
      )
      .sort(
        (
          left,
          right,
        ) =>
          left - right,
      );

  if (!sorted.length) {
    return null;
  }

  const bounded =
    Math.min(
      1,
      Math.max(
        0,
        probability,
      ),
    );

  const index =
    (
      sorted.length - 1
    ) *
    bounded;

  const lower =
    Math.floor(index);

  const upper =
    Math.ceil(index);

  if (lower === upper) {
    return sorted[lower];
  }

  const weight =
    index - lower;

  return (
    sorted[lower] *
      (
        1 - weight
      ) +
    sorted[upper] *
      weight
  );
}

function normalizeReturns(
  returns = [],
) {
  if (!Array.isArray(returns)) {
    throw new TypeError(
      "Risk Engine returns must be an array.",
    );
  }

  return returns
    .map(
      (
        value,
      ) =>
        typeof value === "object"
          ? finiteOrNull(
              value.return ??
              value.pnl ??
              value.value,
            )
          : finiteOrNull(value),
    )
    .filter(
      Number.isFinite,
    );
}

function normalizePositions(
  positions = [],
) {
  if (!Array.isArray(positions)) {
    throw new TypeError(
      "Risk Engine positions must be an array.",
    );
  }

  return positions
    .map(
      (
        position,
        index,
      ) => {
        if (
          !position ||
          typeof position !== "object"
        ) {
          return null;
        }

        const marketValue =
          finiteOrNull(
            position.marketValue ??
            position.value ??
            (
              finiteOrNull(
                position.price,
              ) !== null &&
              finiteOrNull(
                position.quantity,
              ) !== null
                ? finiteOrNull(
                    position.price,
                  ) *
                  finiteOrNull(
                    position.quantity,
                  )
                : null
            ),
          );

        if (
          marketValue === null
        ) {
          return null;
        }

        return {
          symbol:
            String(
              position.symbol ??
              position.code ??
              position.name ??
              `POSITION-${index + 1}`,
            ),

          sector:
            String(
              position.sector ??
              "UNKNOWN",
            ),

          marketValue,

          beta:
            finiteOrNull(
              position.beta,
            ) ?? 1,

          volatility:
            Math.max(
              0,
              finiteOrNull(
                position.volatility,
              ) ?? 0,
            ),

          stopLossPercent:
            Math.max(
              0,
              finiteOrNull(
                position.stopLossPercent,
              ) ?? 0,
            ),

          liquidityScore:
            clamp(
              position.liquidityScore ??
              100,
            ) ?? 100,
        };
      },
    )
    .filter(Boolean);
}

function calculateDrawdown(
  returns,
  initialCapital,
) {
  let equity =
    initialCapital;

  let peak =
    initialCapital;

  let maximumDrawdown =
    0;

  let currentDrawdown =
    0;

  for (
    const value
    of returns
  ) {
    equity *=
      1 +
      value / 100;

    peak =
      Math.max(
        peak,
        equity,
      );

    currentDrawdown =
      peak > 0
        ? (
            (
              peak -
              equity
            ) /
            peak
          ) *
          100
        : 0;

    maximumDrawdown =
      Math.max(
        maximumDrawdown,
        currentDrawdown,
      );
  }

  return {
    endingCapital:
      round(
        equity,
      ),

    currentDrawdown:
      round(
        currentDrawdown,
      ),

    maximumDrawdown:
      round(
        maximumDrawdown,
      ),
  };
}

function calculateValueAtRisk(
  returns,
  confidenceLevel,
) {
  if (!returns.length) {
    return null;
  }

  const tailProbability =
    1 -
    confidenceLevel;

  const threshold =
    percentile(
      returns,
      tailProbability,
    );

  return threshold === null
    ? null
    : Math.max(
        0,
        -threshold,
      );
}

function calculateConditionalValueAtRisk(
  returns,
  valueAtRisk,
) {
  if (
    valueAtRisk === null ||
    !returns.length
  ) {
    return null;
  }

  const tail =
    returns.filter(
      (
        value,
      ) =>
        value <=
        -valueAtRisk,
    );

  if (!tail.length) {
    return valueAtRisk;
  }

  return Math.max(
    0,
    -average(tail),
  );
}

function calculateSectorExposure(
  positions,
  grossExposure,
) {
  const exposure = {};

  for (
    const position
    of positions
  ) {
    exposure[
      position.sector
    ] =
      (
        exposure[
          position.sector
        ] ??
        0
      ) +
      Math.abs(
        position.marketValue,
      );
  }

  return Object.fromEntries(
    Object.entries(
      exposure,
    )
      .map(
        (
          [
            sector,
            value,
          ],
        ) => [
          sector,

          {
            marketValue:
              round(value),

            weight:
              grossExposure > 0
                ? round(
                    value /
                    grossExposure,
                  )
                : 0,

            weightPercent:
              grossExposure > 0
                ? round(
                    value /
                    grossExposure *
                    100,
                    2,
                  )
                : 0,
          },
        ],
      )
      .sort(
        (
          left,
          right,
        ) =>
          right[1].marketValue -
          left[1].marketValue,
      ),
  );
}

function calculatePositionExposure(
  positions,
  grossExposure,
) {
  return positions
    .map(
      (
        position,
      ) => ({
        ...position,

        weight:
          grossExposure > 0
            ? round(
                Math.abs(
                  position.marketValue,
                ) /
                grossExposure,
              )
            : 0,

        weightPercent:
          grossExposure > 0
            ? round(
                Math.abs(
                  position.marketValue,
                ) /
                grossExposure *
                100,
                2,
              )
            : 0,
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
}

function buildBreaches({
  leverage,
  maximumLeverage,
  valueAtRisk,
  maximumValueAtRisk,
  maximumDrawdown,
  maximumAllowedDrawdown,
  largestPositionWeight,
  maximumPositionWeight,
  largestSectorWeight,
  maximumSectorWeight,
  minimumLiquidityScore,
  positions,
}) {
  const breaches = [];

  if (
    leverage >
    maximumLeverage
  ) {
    breaches.push({
      code:
        "LEVERAGE_LIMIT",

      severity:
        "HIGH",

      actual:
        round(leverage),

      limit:
        maximumLeverage,

      message:
        "Portfolio leverage exceeds the configured limit.",
    });
  }

  if (
    valueAtRisk !== null &&
    valueAtRisk >
    maximumValueAtRisk
  ) {
    breaches.push({
      code:
        "VAR_LIMIT",

      severity:
        "HIGH",

      actual:
        round(valueAtRisk),

      limit:
        maximumValueAtRisk,

      message:
        "Value at Risk exceeds the configured limit.",
    });
  }

  if (
    maximumDrawdown >
    maximumAllowedDrawdown
  ) {
    breaches.push({
      code:
        "DRAWDOWN_LIMIT",

      severity:
        "CRITICAL",

      actual:
        round(maximumDrawdown),

      limit:
        maximumAllowedDrawdown,

      message:
        "Maximum drawdown exceeds the configured limit.",
    });
  }

  if (
    largestPositionWeight >
    maximumPositionWeight
  ) {
    breaches.push({
      code:
        "POSITION_CONCENTRATION",

      severity:
        "HIGH",

      actual:
        round(
          largestPositionWeight *
          100,
          2,
        ),

      limit:
        round(
          maximumPositionWeight *
          100,
          2,
        ),

      message:
        "Largest position exceeds the configured weight limit.",
    });
  }

  if (
    largestSectorWeight >
    maximumSectorWeight
  ) {
    breaches.push({
      code:
        "SECTOR_CONCENTRATION",

      severity:
        "HIGH",

      actual:
        round(
          largestSectorWeight *
          100,
          2,
        ),

      limit:
        round(
          maximumSectorWeight *
          100,
          2,
        ),

      message:
        "Largest sector exposure exceeds the configured limit.",
    });
  }

  const illiquid =
    positions.filter(
      (
        position,
      ) =>
        position.liquidityScore <
        minimumLiquidityScore,
    );

  if (illiquid.length) {
    breaches.push({
      code:
        "LIQUIDITY_LIMIT",

      severity:
        "MEDIUM",

      symbols:
        illiquid.map(
          (
            position,
          ) =>
            position.symbol,
        ),

      limit:
        minimumLiquidityScore,

      message:
        "One or more positions have insufficient liquidity.",
    });
  }

  return breaches;
}

function calculateRiskScore({
  leverage,
  maximumLeverage,
  valueAtRisk,
  maximumValueAtRisk,
  maximumDrawdown,
  maximumAllowedDrawdown,
  largestPositionWeight,
  maximumPositionWeight,
  largestSectorWeight,
  maximumSectorWeight,
  averageLiquidity,
}) {
  const leverageRisk =
    clamp(
      leverage /
      maximumLeverage *
      100,
    ) ?? 0;

  const varRisk =
    valueAtRisk === null
      ? 0
      : clamp(
          valueAtRisk /
          maximumValueAtRisk *
          100,
        ) ?? 0;

  const drawdownRisk =
    clamp(
      maximumDrawdown /
      maximumAllowedDrawdown *
      100,
    ) ?? 0;

  const positionRisk =
    clamp(
      largestPositionWeight /
      maximumPositionWeight *
      100,
    ) ?? 0;

  const sectorRisk =
    clamp(
      largestSectorWeight /
      maximumSectorWeight *
      100,
    ) ?? 0;

  const liquidityRisk =
    clamp(
      100 -
      averageLiquidity,
    ) ?? 0;

  const score =
    leverageRisk *
      0.15 +
    varRisk *
      0.25 +
    drawdownRisk *
      0.25 +
    positionRisk *
      0.15 +
    sectorRisk *
      0.1 +
    liquidityRisk *
      0.1;

  return {
    score:
      round(
        clamp(score) ?? 0,
        2,
      ),

    components: {
      leverage:
        round(
          leverageRisk,
          2,
        ),

      valueAtRisk:
        round(
          varRisk,
          2,
        ),

      drawdown:
        round(
          drawdownRisk,
          2,
        ),

      positionConcentration:
        round(
          positionRisk,
          2,
        ),

      sectorConcentration:
        round(
          sectorRisk,
          2,
        ),

      liquidity:
        round(
          liquidityRisk,
          2,
        ),
    },
  };
}

function riskLevel(
  score,
  breachCount,
) {
  if (
    breachCount >= 3 ||
    score >= 85
  ) {
    return "CRITICAL";
  }

  if (
    breachCount >= 1 ||
    score >= 65
  ) {
    return "HIGH";
  }

  if (score >= 40) {
    return "MEDIUM";
  }

  return "LOW";
}

export function evaluatePortfolioRisk({
  returns = [],
  positions = [],
  equity = 100000,
  confidenceLevel = 0.95,
  maximumLeverage = 1.5,
  maximumValueAtRisk = 5,
  maximumAllowedDrawdown = 20,
  maximumPositionWeight = 0.35,
  maximumSectorWeight = 0.5,
  minimumLiquidityScore = 40,
} = {}) {
  const normalizedReturns =
    normalizeReturns(
      returns,
    );

  const normalizedPositions =
    normalizePositions(
      positions,
    );

  const normalizedEquity =
    finiteOrNull(
      equity,
    );

  if (
    normalizedEquity === null ||
    normalizedEquity <= 0
  ) {
    throw new TypeError(
      "Risk Engine equity must be greater than zero.",
    );
  }

  const normalizedConfidenceLevel =
    Math.min(
      0.999,
      Math.max(
        0.5,
        finiteOrNull(
          confidenceLevel,
        ) ?? 0.95,
      ),
    );

  const grossExposure =
    normalizedPositions.reduce(
      (
        sum,
        position,
      ) =>
        sum +
        Math.abs(
          position.marketValue,
        ),
      0,
    );

  const netExposure =
    normalizedPositions.reduce(
      (
        sum,
        position,
      ) =>
        sum +
        position.marketValue,
      0,
    );

  const leverage =
    grossExposure /
    normalizedEquity;

  const positionExposure =
    calculatePositionExposure(
      normalizedPositions,
      grossExposure,
    );

  const sectors =
    calculateSectorExposure(
      normalizedPositions,
      grossExposure,
    );

  const largestPositionWeight =
    positionExposure[0]?.weight ??
    0;

  const largestSectorWeight =
    Math.max(
      0,
      ...Object.values(
        sectors,
      ).map(
        (
          sector,
        ) =>
          sector.weight,
      ),
    );

  const valueAtRisk =
    calculateValueAtRisk(
      normalizedReturns,
      normalizedConfidenceLevel,
    );

  const conditionalValueAtRisk =
    calculateConditionalValueAtRisk(
      normalizedReturns,
      valueAtRisk,
    );

  const drawdown =
    calculateDrawdown(
      normalizedReturns,
      normalizedEquity,
    );

  const volatility =
    standardDeviation(
      normalizedReturns,
    );

  const downsideReturns =
    normalizedReturns.filter(
      (
        value,
      ) =>
        value < 0,
    );

  const downsideDeviation =
    standardDeviation(
      downsideReturns,
    );

  const averageLiquidity =
    normalizedPositions.length
      ? average(
          normalizedPositions.map(
            (
              position,
            ) =>
              position.liquidityScore,
          ),
        )
      : 100;

  const portfolioBeta =
    grossExposure > 0
      ? normalizedPositions.reduce(
          (
            sum,
            position,
          ) =>
            sum +
            position.beta *
            (
              Math.abs(
                position.marketValue,
              ) /
              grossExposure
            ),
          0,
        )
      : 0;

  const breaches =
    buildBreaches({
      leverage,

      maximumLeverage:
        Math.max(
          0.01,
          finiteOrNull(
            maximumLeverage,
          ) ?? 1.5,
        ),

      valueAtRisk,

      maximumValueAtRisk:
        Math.max(
          0.01,
          finiteOrNull(
            maximumValueAtRisk,
          ) ?? 5,
        ),

      maximumDrawdown:
        drawdown.maximumDrawdown,

      maximumAllowedDrawdown:
        Math.max(
          0.01,
          finiteOrNull(
            maximumAllowedDrawdown,
          ) ?? 20,
        ),

      largestPositionWeight,

      maximumPositionWeight:
        Math.max(
          0.01,
          finiteOrNull(
            maximumPositionWeight,
          ) ?? 0.35,
        ),

      largestSectorWeight,

      maximumSectorWeight:
        Math.max(
          0.01,
          finiteOrNull(
            maximumSectorWeight,
          ) ?? 0.5,
        ),

      minimumLiquidityScore:
        clamp(
          minimumLiquidityScore,
        ) ?? 40,

      positions:
        normalizedPositions,
    });

  const risk =
    calculateRiskScore({
      leverage,

      maximumLeverage:
        Math.max(
          0.01,
          finiteOrNull(
            maximumLeverage,
          ) ?? 1.5,
        ),

      valueAtRisk,

      maximumValueAtRisk:
        Math.max(
          0.01,
          finiteOrNull(
            maximumValueAtRisk,
          ) ?? 5,
        ),

      maximumDrawdown:
        drawdown.maximumDrawdown,

      maximumAllowedDrawdown:
        Math.max(
          0.01,
          finiteOrNull(
            maximumAllowedDrawdown,
          ) ?? 20,
        ),

      largestPositionWeight,

      maximumPositionWeight:
        Math.max(
          0.01,
          finiteOrNull(
            maximumPositionWeight,
          ) ?? 0.35,
        ),

      largestSectorWeight,

      maximumSectorWeight:
        Math.max(
          0.01,
          finiteOrNull(
            maximumSectorWeight,
          ) ?? 0.5,
        ),

      averageLiquidity:
        averageLiquidity ??
        100,
    });

  const level =
    riskLevel(
      risk.score,
      breaches.length,
    );

  return {
    version:
      RISK_ENGINE_V2_VERSION,

    ready:
      normalizedReturns.length > 0 ||
      normalizedPositions.length > 0,

    approved:
      breaches.length === 0 &&
      level !== "CRITICAL" &&
      level !== "HIGH",

    riskLevel:
      level,

    riskScore:
      risk.score,

    riskComponents:
      risk.components,

    equity:
      round(
        normalizedEquity,
      ),

    exposure: {
      gross:
        round(
          grossExposure,
        ),

      net:
        round(
          netExposure,
        ),

      leverage:
        round(
          leverage,
        ),

      portfolioBeta:
        round(
          portfolioBeta,
        ),
    },

    returnRisk: {
      sampleSize:
        normalizedReturns.length,

      averageReturn:
        average(
          normalizedReturns,
        ) === null
          ? null
          : round(
              average(
                normalizedReturns,
              ),
            ),

      volatility:
        volatility === null
          ? null
          : round(
              volatility,
            ),

      downsideDeviation:
        downsideDeviation === null
          ? null
          : round(
              downsideDeviation,
            ),

      valueAtRisk:
        valueAtRisk === null
          ? null
          : round(
              valueAtRisk,
            ),

      conditionalValueAtRisk:
        conditionalValueAtRisk === null
          ? null
          : round(
              conditionalValueAtRisk,
            ),

      confidenceLevel:
        normalizedConfidenceLevel,

      currentDrawdown:
        drawdown.currentDrawdown,

      maximumDrawdown:
        drawdown.maximumDrawdown,
    },

    concentration: {
      largestPositionWeight:
        round(
          largestPositionWeight,
        ),

      largestPositionWeightPercent:
        round(
          largestPositionWeight *
          100,
          2,
        ),

      largestSectorWeight:
        round(
          largestSectorWeight,
        ),

      largestSectorWeightPercent:
        round(
          largestSectorWeight *
          100,
          2,
        ),
    },

    liquidity: {
      averageScore:
        round(
          averageLiquidity ??
          100,
          2,
        ),

      minimumRequired:
        clamp(
          minimumLiquidityScore,
        ) ?? 40,
    },

    positions:
      positionExposure,

    sectors,

    breaches,

    diagnostics: {
      positionCount:
        normalizedPositions.length,

      returnCount:
        normalizedReturns.length,

      breachCount:
        breaches.length,

      endingCapital:
        drawdown.endingCapital,
    },
  };
}

export class RiskEngineV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  evaluate(input = {}) {
    return evaluatePortfolioRisk({
      ...this.config,
      ...input,
    });
  }
}

export const riskEngineV2 =
  new RiskEngineV2();

export default evaluatePortfolioRisk;