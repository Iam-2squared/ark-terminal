function finiteNumber(value, fallback = 0) {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function clamp(value, minimum, maximum) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      value,
    ),
  );
}

function round(value, digits = 2) {
  const factor = 10 ** digits;

  return (
    Math.round(
      finiteNumber(value) * factor,
    ) / factor
  );
}

function normalizeCandidate(candidate = {}) {
  return {
    code:
      String(
        candidate.code ?? "",
      ).trim(),

    score:
      clamp(
        finiteNumber(
          candidate.score,
        ),
        0,
        100,
      ),

    price:
      Math.max(
        0,
        finiteNumber(
          candidate.price,
        ),
      ),

    volatility:
      Math.max(
        0,
        finiteNumber(
          candidate.volatility,
        ),
      ),

    sector:
      String(
        candidate.sector ??
        "UNKNOWN",
      ).trim() ||
      "UNKNOWN",

    lotSize:
      Math.max(
        1,
        Math.floor(
          finiteNumber(
            candidate.lotSize,
            100,
          ),
        ),
      ),
  };
}

export function calculatePortfolioAllocation({
  candidates = [],
  maximumPositionPercent = 25,
  maximumSectorPercent = 40,
  minimumScore = 60,
  cashReservePercent = 10,
} = {}) {
  const normalized =
    candidates
      .map(
        normalizeCandidate,
      )
      .filter(
        (candidate) =>
          candidate.code &&
          candidate.price > 0 &&
          candidate.score >=
            minimumScore,
      );

  const reserve =
    clamp(
      finiteNumber(
        cashReservePercent,
        10,
      ),
      0,
      100,
    );

  const investablePercent =
    100 - reserve;

  if (
    normalized.length === 0 ||
    investablePercent <= 0
  ) {
    return {
      allocations: [],
      cashPercent: 100,
      investedPercent: 0,
    };
  }

  const scored =
    normalized.map(
      (candidate) => {
        const riskPenalty =
          clamp(
            candidate.volatility,
            0,
            100,
          ) * 0.35;

        const adjustedScore =
          Math.max(
            1,
            candidate.score -
            riskPenalty,
          );

        return {
          ...candidate,
          adjustedScore,
        };
      },
    );

  const totalAdjustedScore =
    scored.reduce(
      (sum, candidate) =>
        sum +
        candidate.adjustedScore,
      0,
    );

  const sectorTotals =
    new Map();

  const allocations =
    scored
      .sort(
        (first, second) =>
          second.adjustedScore -
          first.adjustedScore,
      )
      .map(
        (candidate) => {
          const rawPercent =
            (
              candidate.adjustedScore /
              totalAdjustedScore
            ) *
            investablePercent;

          const positionLimited =
            Math.min(
              rawPercent,
              maximumPositionPercent,
            );

          const sectorUsed =
            sectorTotals.get(
              candidate.sector,
            ) ?? 0;

          const sectorRemaining =
            Math.max(
              0,
              maximumSectorPercent -
              sectorUsed,
            );

          const allocationPercent =
            Math.min(
              positionLimited,
              sectorRemaining,
            );

          sectorTotals.set(
            candidate.sector,
            sectorUsed +
              allocationPercent,
          );

          return {
            ...candidate,

            adjustedScore:
              round(
                candidate.adjustedScore,
                3,
              ),

            allocationPercent:
              round(
                allocationPercent,
                2,
              ),
          };
        },
      )
      .filter(
        (candidate) =>
          candidate.allocationPercent >
          0,
      );

  const investedPercent =
    round(
      allocations.reduce(
        (sum, candidate) =>
          sum +
          candidate.allocationPercent,
        0,
      ),
      2,
    );

  return {
    allocations,

    investedPercent,

    cashPercent:
      round(
        100 - investedPercent,
        2,
      ),
  };
}

export function buildExecutablePortfolio({
  capital = 0,
  allocations = [],
} = {}) {
  const safeCapital =
    Math.max(
      0,
      finiteNumber(capital),
    );

  const positions =
    allocations.map(
      (allocation) => {
        const allocatedCapital =
          safeCapital *
          (
            finiteNumber(
              allocation
                .allocationPercent,
            ) / 100
          );

        const lotCost =
          allocation.price *
          allocation.lotSize;

        const lots =
          lotCost > 0
            ? Math.floor(
                allocatedCapital /
                lotCost,
              )
            : 0;

        const shares =
          lots *
          allocation.lotSize;

        const investedAmount =
          shares *
          allocation.price;

        return {
          ...allocation,

          allocatedCapital:
            round(
              allocatedCapital,
              2,
            ),

          lots,

          shares,

          investedAmount:
            round(
              investedAmount,
              2,
            ),

          unusedCapital:
            round(
              allocatedCapital -
              investedAmount,
              2,
            ),

          executable:
            shares > 0,
        };
      },
    );

  const totalInvested =
    round(
      positions.reduce(
        (sum, position) =>
          sum +
          position.investedAmount,
        0,
      ),
      2,
    );

  return {
    capital:
      safeCapital,

    positions,

    totalInvested,

    remainingCapital:
      round(
        safeCapital -
        totalInvested,
        2,
      ),
  };
}

export function evaluatePortfolioRisk({
  positions = [],
  capital = 0,
  maximumPortfolioRiskPercent = 6,
} = {}) {
  const safeCapital =
    Math.max(
      1,
      finiteNumber(
        capital,
        1,
      ),
    );

  const estimatedRiskAmount =
    positions.reduce(
      (sum, position) => {
        const volatilityRate =
          clamp(
            finiteNumber(
              position.volatility,
            ),
            0,
            100,
          ) / 100;

        return (
          sum +
          finiteNumber(
            position.investedAmount,
          ) *
            volatilityRate
        );
      },
      0,
    );

  const riskPercent =
    (
      estimatedRiskAmount /
      safeCapital
    ) * 100;

  const limit =
    Math.max(
      0,
      finiteNumber(
        maximumPortfolioRiskPercent,
        6,
      ),
    );

  return {
    estimatedRiskAmount:
      round(
        estimatedRiskAmount,
        2,
      ),

    riskPercent:
      round(
        riskPercent,
        2,
      ),

    limitPercent:
      limit,

    approved:
      riskPercent <= limit,

    status:
      riskPercent <= limit
        ? "WITHIN_LIMIT"
        : "RISK_LIMIT_EXCEEDED",
  };
}

export function buildAiPortfolioPlan({
  capital = 0,
  candidates = [],
  settings = {},
} = {}) {
  const allocation =
    calculatePortfolioAllocation({
      candidates,
      ...settings,
    });

  const executable =
    buildExecutablePortfolio({
      capital,
      allocations:
        allocation.allocations,
    });

  const risk =
    evaluatePortfolioRisk({
      positions:
        executable.positions,

      capital,

      maximumPortfolioRiskPercent:
        settings
          .maximumPortfolioRiskPercent ??
        6,
    });

  return {
    version:
      "ai-portfolio-manager-v1",

    generatedAt:
      new Date().toISOString(),

    allocation,

    executable,

    risk,

    approved:
      risk.approved,

    summary: {
      candidateCount:
        candidates.length,

      selectedCount:
        executable.positions.length,

      executableCount:
        executable.positions.filter(
          (position) =>
            position.executable,
        ).length,

      totalInvested:
        executable.totalInvested,

      remainingCapital:
        executable.remainingCapital,

      cashPercent:
        allocation.cashPercent,
    },
  };
}