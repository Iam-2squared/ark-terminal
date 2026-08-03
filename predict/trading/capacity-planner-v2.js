export const CAPACITY_PLANNER_V2_VERSION =
  "capacity-planner-v2";

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

function positiveNumber(
  value,
  fallback = 0,
) {
  const number =
    finiteOrNull(value);

  if (
    number === null ||
    number < 0
  ) {
    return fallback;
  }

  return number;
}

function clamp(
  value,
  minimum = 0,
  maximum = 1,
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
  digits = 6,
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

function normalizeSide(value) {
  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "BUY",
      "LONG",
      "B",
    ].includes(text)
  ) {
    return "BUY";
  }

  if (
    [
      "SELL",
      "SHORT",
      "S",
    ].includes(text)
  ) {
    return "SELL";
  }

  return "BUY";
}

function normalizeCandidate(
  candidate,
  index,
) {
  if (
    !candidate ||
    typeof candidate !== "object"
  ) {
    return null;
  }

  const price =
    finiteOrNull(
      candidate.price ??
      candidate.last ??
      candidate.close,
    );

  const averageDailyVolume =
    finiteOrNull(
      candidate.averageDailyVolume ??
      candidate.adv ??
      candidate.volume,
    );

  if (
    price === null ||
    price <= 0 ||
    averageDailyVolume === null ||
    averageDailyVolume <= 0
  ) {
    return null;
  }

  const confidence =
    clamp(
      (
        finiteOrNull(
          candidate.confidence,
        ) ??
        50
      ) / 100,
      0,
      1,
    ) ?? 0.5;

  const score =
    clamp(
      (
        finiteOrNull(
          candidate.score,
        ) ??
        50
      ) / 100,
      0,
      1,
    ) ?? 0.5;

  const liquidityScore =
    clamp(
      (
        finiteOrNull(
          candidate.liquidityScore,
        ) ??
        100
      ) / 100,
      0,
      1,
    ) ?? 1;

  const volatility =
    positiveNumber(
      candidate.volatility,
      0,
    );

  return {
    symbol:
      String(
        candidate.symbol ??
        candidate.code ??
        candidate.name ??
        `ASSET-${index + 1}`,
      ),

    side:
      normalizeSide(
        candidate.side,
      ),

    price,

    averageDailyVolume,

    confidence,

    score,

    liquidityScore,

    volatility,

    requestedQuantity:
      positiveNumber(
        candidate.requestedQuantity ??
        candidate.quantity,
        0,
      ),

    requestedValue:
      positiveNumber(
        candidate.requestedValue ??
        candidate.value,
        0,
      ),

    sector:
      String(
        candidate.sector ??
        "UNKNOWN",
      ),
  };
}

function normalizeCandidates(
  candidates = [],
) {
  if (!Array.isArray(candidates)) {
    throw new TypeError(
      "Capacity Planner candidates must be an array.",
    );
  }

  return candidates
    .map(
      normalizeCandidate,
    )
    .filter(Boolean);
}

function estimateMaximumParticipation({
  baseParticipationRate,
  liquidityScore,
  volatility,
}) {
  const liquidityMultiplier =
    0.25 +
    liquidityScore *
    0.75;

  const volatilityPenalty =
    1 /
    (
      1 +
      volatility *
      0.08
    );

  return clamp(
    baseParticipationRate *
    liquidityMultiplier *
    volatilityPenalty,
    0.000001,
    1,
  ) ?? 0.01;
}

function estimateMarketImpact({
  participationRate,
  volatility,
  liquidityScore,
  impactCoefficient,
}) {
  const liquidityPenalty =
    1 +
    (
      1 -
      liquidityScore
    ) *
    2;

  const volatilityMultiplier =
    1 +
    volatility *
    0.05;

  return (
    Math.sqrt(
      Math.max(
        0,
        participationRate,
      ),
    ) *
    impactCoefficient *
    liquidityPenalty *
    volatilityMultiplier
  );
}

function calculateRequestedQuantity(
  candidate,
) {
  if (
    candidate.requestedQuantity >
    0
  ) {
    return candidate.requestedQuantity;
  }

  if (
    candidate.requestedValue >
    0
  ) {
    return (
      candidate.requestedValue /
      candidate.price
    );
  }

  return 0;
}

function scoreOpportunity(
  candidate,
) {
  return (
    candidate.score *
      0.5 +
    candidate.confidence *
      0.3 +
    candidate.liquidityScore *
      0.2
  );
}

function calculateCapacityForCandidate({
  candidate,
  capital,
  maximumPositionWeight,
  baseParticipationRate,
  maximumImpactPercent,
  impactCoefficient,
  holdingDays,
  lotSize,
}) {
  const maximumParticipation =
    estimateMaximumParticipation({
      baseParticipationRate,

      liquidityScore:
        candidate.liquidityScore,

      volatility:
        candidate.volatility,
    });

  const dailyCapacityQuantity =
    candidate.averageDailyVolume *
    maximumParticipation;

  const holdingPeriodCapacity =
    dailyCapacityQuantity *
    holdingDays;

  const capitalLimitValue =
    capital *
    maximumPositionWeight;

  const capitalLimitQuantity =
    capitalLimitValue /
    candidate.price;

  const impactLimitedParticipation =
    maximumImpactPercent > 0
      ? Math.min(
          maximumParticipation,

          (
            maximumImpactPercent /
            Math.max(
              0.000001,
              impactCoefficient *
              (
                1 +
                (
                  1 -
                  candidate.liquidityScore
                ) *
                2
              ) *
              (
                1 +
                candidate.volatility *
                0.05
              ),
            )
          ) ** 2,
        )
      : maximumParticipation;

  const impactLimitQuantity =
    candidate.averageDailyVolume *
    impactLimitedParticipation *
    holdingDays;

  const rawMaximumQuantity =
    Math.max(
      0,
      Math.min(
        holdingPeriodCapacity,
        capitalLimitQuantity,
        impactLimitQuantity,
      ),
    );

  const normalizedLotSize =
    Math.max(
      1,
      Math.floor(
        positiveNumber(
          lotSize,
          1,
        ),
      ),
    );

  const maximumQuantity =
    Math.floor(
      rawMaximumQuantity /
      normalizedLotSize,
    ) *
    normalizedLotSize;

  const requestedQuantity =
    calculateRequestedQuantity(
      candidate,
    );

  const recommendedQuantity =
    requestedQuantity > 0
      ? Math.min(
          requestedQuantity,
          maximumQuantity,
        )
      : maximumQuantity;

  const roundedRecommendedQuantity =
    Math.floor(
      recommendedQuantity /
      normalizedLotSize,
    ) *
    normalizedLotSize;

  const recommendedValue =
    roundedRecommendedQuantity *
    candidate.price;

  const participationRate =
    candidate.averageDailyVolume > 0 &&
    holdingDays > 0
      ? roundedRecommendedQuantity /
        (
          candidate.averageDailyVolume *
          holdingDays
        )
      : 0;

  const estimatedImpactPercent =
    estimateMarketImpact({
      participationRate,

      volatility:
        candidate.volatility,

      liquidityScore:
        candidate.liquidityScore,

      impactCoefficient,
    });

  const capacityUtilization =
    maximumQuantity > 0
      ? roundedRecommendedQuantity /
        maximumQuantity
      : 0;

  const constraints = [];

  if (
    rawMaximumQuantity ===
    capitalLimitQuantity
  ) {
    constraints.push(
      "CAPITAL_LIMIT",
    );
  }

  if (
    rawMaximumQuantity ===
    holdingPeriodCapacity
  ) {
    constraints.push(
      "LIQUIDITY_LIMIT",
    );
  }

  if (
    rawMaximumQuantity ===
    impactLimitQuantity
  ) {
    constraints.push(
      "MARKET_IMPACT_LIMIT",
    );
  }

  const approved =
    roundedRecommendedQuantity > 0 &&
    estimatedImpactPercent <=
      maximumImpactPercent +
      0.000001;

  return {
    symbol:
      candidate.symbol,

    sector:
      candidate.sector,

    side:
      candidate.side,

    approved,

    price:
      round(
        candidate.price,
      ),

    requestedQuantity:
      round(
        requestedQuantity,
      ),

    maximumQuantity:
      round(
        maximumQuantity,
      ),

    recommendedQuantity:
      round(
        roundedRecommendedQuantity,
      ),

    maximumValue:
      round(
        maximumQuantity *
        candidate.price,
      ),

    recommendedValue:
      round(
        recommendedValue,
      ),

    opportunityScore:
      round(
        scoreOpportunity(
          candidate,
        ) *
        100,
        2,
      ),

    capacity: {
      dailyQuantity:
        round(
          dailyCapacityQuantity,
        ),

      holdingPeriodQuantity:
        round(
          holdingPeriodCapacity,
        ),

      maximumParticipationRate:
        round(
          maximumParticipation,
        ),

      maximumParticipationPercent:
        round(
          maximumParticipation *
          100,
          4,
        ),

      actualParticipationRate:
        round(
          participationRate,
        ),

      actualParticipationPercent:
        round(
          participationRate *
          100,
          4,
        ),

      utilization:
        round(
          capacityUtilization,
        ),

      utilizationPercent:
        round(
          capacityUtilization *
          100,
          2,
        ),
    },

    impact: {
      estimatedPercent:
        round(
          estimatedImpactPercent,
          4,
        ),

      maximumAllowedPercent:
        round(
          maximumImpactPercent,
          4,
        ),
    },

    quality: {
      score:
        round(
          candidate.score *
          100,
          2,
        ),

      confidence:
        round(
          candidate.confidence *
          100,
          2,
        ),

      liquidityScore:
        round(
          candidate.liquidityScore *
          100,
          2,
        ),

      volatility:
        round(
          candidate.volatility,
          4,
        ),
    },

    constraints:
      [
        ...new Set(
          constraints,
        ),
      ],
  };
}

function allocateCapital({
  plans,
  capital,
  maximumGrossExposure,
}) {
  const availableCapital =
    capital *
    maximumGrossExposure;

  const sorted =
    [
      ...plans,
    ].sort(
      (
        left,
        right,
      ) =>
        right.opportunityScore -
        left.opportunityScore,
    );

  let remainingCapital =
    availableCapital;

  const allocated = [];

  for (
    const plan
    of sorted
  ) {
    if (
      !plan.approved ||
      remainingCapital <= 0
    ) {
      allocated.push({
        ...plan,

        allocatedQuantity:
          0,

        allocatedValue:
          0,

        allocationStatus:
          plan.approved
            ? "CAPITAL_EXHAUSTED"
            : "REJECTED",
      });

      continue;
    }

    const maximumAffordableQuantity =
      Math.floor(
        remainingCapital /
        plan.price,
      );

    const allocatedQuantity =
      Math.min(
        plan.recommendedQuantity,
        maximumAffordableQuantity,
      );

    const allocatedValue =
      allocatedQuantity *
      plan.price;

    remainingCapital -=
      allocatedValue;

    allocated.push({
      ...plan,

      allocatedQuantity:
        round(
          allocatedQuantity,
        ),

      allocatedValue:
        round(
          allocatedValue,
        ),

      allocationStatus:
        allocatedQuantity > 0
          ? allocatedQuantity >=
              plan.recommendedQuantity
            ? "FULL"
            : "PARTIAL"
          : "CAPITAL_EXHAUSTED",
    });
  }

  return {
    plans:
      allocated.sort(
        (
          left,
          right,
        ) =>
          right.allocatedValue -
          left.allocatedValue,
      ),

    availableCapital:
      round(
        availableCapital,
      ),

    allocatedCapital:
      round(
        availableCapital -
        remainingCapital,
      ),

    remainingCapital:
      round(
        remainingCapital,
      ),
  };
}

export function planTradingCapacity({
  candidates = [],
  capital = 100000,
  maximumPositionWeight = 0.2,
  maximumGrossExposure = 1,
  baseParticipationRate = 0.1,
  maximumImpactPercent = 0.5,
  impactCoefficient = 1,
  holdingDays = 1,
  lotSize = 1,
} = {}) {
  const normalizedCapital =
    finiteOrNull(
      capital,
    );

  if (
    normalizedCapital === null ||
    normalizedCapital <= 0
  ) {
    throw new TypeError(
      "Capacity Planner capital must be greater than zero.",
    );
  }

  const normalizedCandidates =
    normalizeCandidates(
      candidates,
    );

  const normalizedMaximumPositionWeight =
    clamp(
      maximumPositionWeight,
      0.000001,
      1,
    ) ?? 0.2;

  const normalizedMaximumGrossExposure =
    clamp(
      maximumGrossExposure,
      0.000001,
      2,
    ) ?? 1;

  const normalizedBaseParticipationRate =
    clamp(
      baseParticipationRate,
      0.000001,
      1,
    ) ?? 0.1;

  const normalizedMaximumImpactPercent =
    positiveNumber(
      maximumImpactPercent,
      0.5,
    );

  const normalizedImpactCoefficient =
    positiveNumber(
      impactCoefficient,
      1,
    );

  const normalizedHoldingDays =
    Math.max(
      1,
      Math.floor(
        positiveNumber(
          holdingDays,
          1,
        ),
      ),
    );

  if (!normalizedCandidates.length) {
    return {
      version:
        CAPACITY_PLANNER_V2_VERSION,

      ready:
        false,

      approved:
        false,

      capital:
        round(
          normalizedCapital,
        ),

      candidateCount:
        0,

      approvedCount:
        0,

      rejectedCount:
        0,

      plans:
        [],

      summary: {
        availableCapital:
          round(
            normalizedCapital *
            normalizedMaximumGrossExposure,
          ),

        allocatedCapital:
          0,

        remainingCapital:
          round(
            normalizedCapital *
            normalizedMaximumGrossExposure,
          ),

        grossExposure:
          0,

        grossExposurePercent:
          0,
      },
    };
  }

  const plans =
    normalizedCandidates.map(
      (
        candidate,
      ) =>
        calculateCapacityForCandidate({
          candidate,

          capital:
            normalizedCapital,

          maximumPositionWeight:
            normalizedMaximumPositionWeight,

          baseParticipationRate:
            normalizedBaseParticipationRate,

          maximumImpactPercent:
            normalizedMaximumImpactPercent,

          impactCoefficient:
            normalizedImpactCoefficient,

          holdingDays:
            normalizedHoldingDays,

          lotSize,
        }),
    );

  const allocation =
    allocateCapital({
      plans,

      capital:
        normalizedCapital,

      maximumGrossExposure:
        normalizedMaximumGrossExposure,
    });

  const approvedPlans =
    allocation.plans.filter(
      (
        plan,
      ) =>
        plan.approved &&
        plan.allocatedQuantity > 0,
    );

  const rejectedPlans =
    allocation.plans.filter(
      (
        plan,
      ) =>
        !plan.approved ||
        plan.allocatedQuantity <= 0,
    );

  const grossExposure =
    allocation.allocatedCapital /
    normalizedCapital;

  return {
    version:
      CAPACITY_PLANNER_V2_VERSION,

    ready:
      true,

    approved:
      approvedPlans.length > 0,

    capital:
      round(
        normalizedCapital,
      ),

    configuration: {
      maximumPositionWeight:
        normalizedMaximumPositionWeight,

      maximumGrossExposure:
        normalizedMaximumGrossExposure,

      baseParticipationRate:
        normalizedBaseParticipationRate,

      maximumImpactPercent:
        normalizedMaximumImpactPercent,

      impactCoefficient:
        normalizedImpactCoefficient,

      holdingDays:
        normalizedHoldingDays,

      lotSize:
        Math.max(
          1,
          Math.floor(
            positiveNumber(
              lotSize,
              1,
            ),
          ),
        ),
    },

    candidateCount:
      normalizedCandidates.length,

    approvedCount:
      approvedPlans.length,

    rejectedCount:
      rejectedPlans.length,

    plans:
      allocation.plans,

    summary: {
      availableCapital:
        allocation.availableCapital,

      allocatedCapital:
        allocation.allocatedCapital,

      remainingCapital:
        allocation.remainingCapital,

      grossExposure:
        round(
          grossExposure,
        ),

      grossExposurePercent:
        round(
          grossExposure *
          100,
          2,
        ),

      averageImpactPercent:
        approvedPlans.length
          ? round(
              approvedPlans.reduce(
                (
                  sum,
                  plan,
                ) =>
                  sum +
                  plan.impact.estimatedPercent,
                0,
              ) /
              approvedPlans.length,
              4,
            )
          : null,

      averageCapacityUtilizationPercent:
        approvedPlans.length
          ? round(
              approvedPlans.reduce(
                (
                  sum,
                  plan,
                ) =>
                  sum +
                  plan.capacity.utilizationPercent,
                0,
              ) /
              approvedPlans.length,
              2,
            )
          : null,
    },
  };
}

export class CapacityPlannerV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  plan(
    candidates = [],
    overrides = {},
  ) {
    return planTradingCapacity({
      ...this.config,

      ...overrides,

      candidates,
    });
  }
}

export const capacityPlannerV2 =
  new CapacityPlannerV2();

export default planTradingCapacity;