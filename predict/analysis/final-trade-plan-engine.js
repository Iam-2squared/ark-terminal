import {
  evaluateRiskAwareDecision,
} from "./risk-aware-decision-gate.js";

import {
  calculatePositionSize,
} from "./position-sizing-engine.js";

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

function clamp(
  value,
  minimum,
  maximum,
) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      finiteNumber(value),
    ),
  );
}

function round(
  value,
  digits = 2,
) {
  const factor =
    10 ** digits;

  return (
    Math.round(
      finiteNumber(value) *
      factor,
    ) /
    factor
  );
}

function executableLot({
  shares = 0,
  lotSize = 100,
} = {}) {
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

  return (
    Math.floor(
      Math.max(
        0,
        finiteNumber(shares),
      ) /
      safeLotSize,
    ) *
    safeLotSize
  );
}

function calculatePriceLevels({
  price = 0,
  stopPercent = 5,
  targetPercent = 10,
} = {}) {
  const safePrice =
    Math.max(
      0,
      finiteNumber(price),
    );

  const safeStopPercent =
    clamp(
      stopPercent,
      0,
      100,
    );

  const safeTargetPercent =
    Math.max(
      0,
      finiteNumber(
        targetPercent,
      ),
    );

  return {
    entryPrice:
      round(
        safePrice,
        2,
      ),

    stopPrice:
      round(
        safePrice *
        (
          1 -
          safeStopPercent /
          100
        ),
        2,
      ),

    targetPrice:
      round(
        safePrice *
        (
          1 +
          safeTargetPercent /
          100
        ),
        2,
      ),

    stopPercent:
      safeStopPercent,

    targetPercent:
      safeTargetPercent,

    riskRewardRatio:
      safeStopPercent > 0
        ? round(
            safeTargetPercent /
            safeStopPercent,
            2,
          )
        : null,
  };
}

export function buildFinalTradePlan({
  symbol = null,
  decision = {},
  portfolioRisk = {},
  limits = {},
  capital = 0,
  allocation = 0,
  price = 0,
  lotSize = 100,
  stopPercent = 5,
  targetPercent = 10,
} = {}) {
  const gate =
    evaluateRiskAwareDecision({
      decision,
      portfolioRisk,
      limits,
    });

  const riskLevel =
    clamp(
      finiteNumber(
        portfolioRisk.riskPercent,
      ) * 10,
      0,
      100,
    );

  const sizing =
    calculatePositionSize({
      capital:
        Math.max(
          0,
          finiteNumber(capital),
        ),

      allocation:
        clamp(
          allocation,
          0,
          1,
        ),

      confidence:
        gate.confidence,

      riskLevel,

      price:
        Math.max(
          0,
          finiteNumber(price),
        ),
    });

  const shares =
    gate.approved
      ? executableLot({
          shares:
            sizing.shares,

          lotSize,
        })
      : 0;

  const levels =
    calculatePriceLevels({
      price,
      stopPercent,
      targetPercent,
    });

  const estimatedCost =
    round(
      shares *
      levels.entryPrice,
      2,
    );

  const estimatedLoss =
    round(
      shares *
      Math.max(
        0,
        levels.entryPrice -
        levels.stopPrice,
      ),
      2,
    );

  const estimatedProfit =
    round(
      shares *
      Math.max(
        0,
        levels.targetPrice -
        levels.entryPrice,
      ),
      2,
    );

  const executable =
    gate.approved &&
    shares > 0 &&
    estimatedCost <=
      Math.max(
        0,
        finiteNumber(capital),
      );

  return {
    version:
      "final-trade-plan-v1",

    generatedAt:
      new Date()
        .toISOString(),

    symbol,

    action:
      executable
        ? gate.action
        : "NO TRADE",

    executable,

    gate,

    sizing: {
      ...sizing,

      lotSize:
        Math.max(
          1,
          Math.floor(
            finiteNumber(
              lotSize,
              100,
            ),
          ),
        ),

      shares,

      estimatedCost,
    },

    levels,

    estimatedLoss,

    estimatedProfit,

    remainingCapital:
      round(
        Math.max(
          0,
          finiteNumber(capital),
        ) -
        estimatedCost,
        2,
      ),

    reasons:
      executable
        ? []
        : [
            ...gate.reasons,

            ...(
              shares <= 0
                ? [
                    "insufficient_capital_for_lot",
                  ]
                : []
            ),
          ],
  };
}

export function buildTradePlanSummary(
  plan = {},
) {
  return {
    symbol:
      plan.symbol,

    action:
      plan.action ??
      "NO TRADE",

    executable:
      plan.executable === true,

    shares:
      plan.sizing?.shares ??
      0,

    entryPrice:
      plan.levels?.entryPrice ??
      0,

    stopPrice:
      plan.levels?.stopPrice ??
      0,

    targetPrice:
      plan.levels?.targetPrice ??
      0,

    riskRewardRatio:
      plan.levels
        ?.riskRewardRatio ??
      null,

    estimatedCost:
      plan.sizing
        ?.estimatedCost ??
      0,

    estimatedLoss:
      plan.estimatedLoss ??
      0,

    estimatedProfit:
      plan.estimatedProfit ??
      0,
  };
}

export const FinalTradePlanInternals = {
  calculatePriceLevels,
  executableLot,
};