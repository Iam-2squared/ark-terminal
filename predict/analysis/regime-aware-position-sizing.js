import {
  detectMarketRegime,
} from "./market-regime-engine.js";

import {
  calculatePositionSize,
} from "./position-sizing-engine.js";

function finiteNumber(value, fallback = 0) {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function clamp(value, minimum, maximum) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      finiteNumber(value),
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

export function calculateRegimeAdjustedAllocation({
  baseAllocation = 0,
  regime = {},
  confidence = 50,
  maximumAllocation = 1,
} = {}) {
  const base =
    clamp(
      baseAllocation,
      0,
      maximumAllocation,
    );

  const multiplier =
    clamp(
      regime.riskMultiplier ?? 1,
      0,
      2,
    );

  const confidenceMultiplier =
    clamp(
      finiteNumber(
        confidence,
        50,
      ) / 100,
      0,
      1,
    );

  const adjustedAllocation =
    clamp(
      base *
      multiplier *
      confidenceMultiplier,
      0,
      maximumAllocation,
    );

  return {
    baseAllocation:
      round(
        base,
        4,
      ),

    regimeMultiplier:
      round(
        multiplier,
        3,
      ),

    confidenceMultiplier:
      round(
        confidenceMultiplier,
        3,
      ),

    adjustedAllocation:
      round(
        adjustedAllocation,
        4,
      ),
  };
}

export function buildRegimeAwarePositionPlan({
  capital = 0,
  price = 0,
  baseAllocation = 0,
  confidence = 50,
  riskLevel = 50,
  market = {},
  lotSize = 100,
  maximumAllocation = 1,
} = {}) {
  const regime =
    detectMarketRegime(
      market,
    );

  const allocation =
    calculateRegimeAdjustedAllocation({
      baseAllocation,
      regime,
      confidence,
      maximumAllocation,
    });

  const sizing =
    calculatePositionSize({
      capital,
      allocation:
        allocation.adjustedAllocation,
      confidence,
      riskLevel,
      price,
    });

  const safeLotSize =
    Math.max(
      1,
      Math.floor(
        finiteNumber(
          lotSize,
          100,
        ),
      ),
    );

  const executableShares =
    Math.floor(
      sizing.shares /
      safeLotSize,
    ) *
    safeLotSize;

  const estimatedCost =
    round(
      executableShares *
      Math.max(
        0,
        finiteNumber(price),
      ),
      2,
    );

  return {
    version:
      "regime-aware-position-sizing-v1",

    generatedAt:
      new Date().toISOString(),

    regime,

    allocation,

    sizing: {
      ...sizing,

      lotSize:
        safeLotSize,

      executableShares,

      estimatedCost,
    },

    executable:
      executableShares > 0,

    remainingCapital:
      round(
        Math.max(
          0,
          finiteNumber(capital),
        ) -
        estimatedCost,
        2,
      ),
  };
}

export function compareRegimePositionPlans({
  capital = 0,
  price = 0,
  baseAllocation = 0,
  confidence = 50,
  riskLevel = 50,
  lotSize = 100,
} = {}) {
  const scenarios = {
    bull: {
      trendScore: 90,
      momentum: 85,
      breadth: 80,
      volatility: 20,
      vix: 15,
    },

    sideways: {
      trendScore: 50,
      momentum: 50,
      breadth: 50,
      volatility: 30,
      vix: 20,
    },

    highVolatility: {
      trendScore: 55,
      momentum: 50,
      breadth: 50,
      volatility: 85,
      vix: 40,
    },

    bear: {
      trendScore: 20,
      momentum: 25,
      breadth: 30,
      volatility: 55,
      vix: 30,
    },
  };

  return Object.fromEntries(
    Object.entries(
      scenarios,
    ).map(
      ([
        name,
        market,
      ]) => [
        name,

        buildRegimeAwarePositionPlan({
          capital,
          price,
          baseAllocation,
          confidence,
          riskLevel,
          market,
          lotSize,
        }),
      ],
    ),
  );
}