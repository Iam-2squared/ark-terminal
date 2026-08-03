import {
  runRollingValidation,
} from "../backtest/rolling-validation-v2.js";

import {
  runMonteCarloValidation,
} from "../backtest/monte-carlo-validation-v2.js";

import {
  optimizePortfolio,
} from "../portfolio/portfolio-optimizer-v2.js";

import {
  evaluatePortfolioRisk,
} from "../portfolio/risk-engine-v2.js";

import {
  simulateExecutionBatch,
} from "../trading/execution-simulator-v2.js";

import {
  planTradingCapacity,
} from "../trading/capacity-planner-v2.js";

export const PHASE2_RUNTIME_INTEGRATION_V2_VERSION =
  "phase2-runtime-integration-v2";

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

function safeArray(value) {
  return Array.isArray(value)
    ? value
    : [];
}

function normalizeSymbol(value) {
  return String(
    value ??
    "UNKNOWN",
  ).trim();
}

function createRiskPositions({
  portfolio,
  capacity,
  marketBySymbol,
}) {
  const capacityBySymbol =
    new Map(
      safeArray(
        capacity?.plans,
      ).map(
        (
          plan,
        ) => [
          normalizeSymbol(
            plan.symbol,
          ),
          plan,
        ],
      ),
    );

  return safeArray(
    portfolio?.allocations,
  )
    .map(
      (
        allocation,
      ) => {
        const symbol =
          normalizeSymbol(
            allocation.symbol,
          );

        const capacityPlan =
          capacityBySymbol.get(
            symbol,
          );

        const market =
          marketBySymbol?.[
            symbol
          ] ?? {};

        const price =
          finiteOrNull(
            market.last ??
            market.price ??
            market.close ??
            capacityPlan?.price,
          );

        const quantity =
          finiteOrNull(
            capacityPlan?.allocatedQuantity ??
            capacityPlan?.recommendedQuantity,
          );

        let marketValue =
          finiteOrNull(
            capacityPlan?.allocatedValue ??
            capacityPlan?.recommendedValue,
          );

        if (
          marketValue === null &&
          price !== null &&
          quantity !== null
        ) {
          marketValue =
            price *
            quantity;
        }

        if (
          marketValue === null
        ) {
          return null;
        }

        return {
          symbol,

          sector:
            allocation.sector ??
            capacityPlan?.sector ??
            "UNKNOWN",

          marketValue,

          beta:
            finiteOrNull(
              market.beta,
            ) ?? 1,

          volatility:
            finiteOrNull(
              allocation.volatility ??
              market.volatility,
            ) ?? 0,

          liquidityScore:
            finiteOrNull(
              capacityPlan?.quality?.liquidityScore ??
              market.liquidityScore,
            ) ?? 100,
        };
      },
    )
    .filter(Boolean);
}

function createExecutionOrders(
  capacity,
) {
  return safeArray(
    capacity?.plans,
  )
    .filter(
      (
        plan,
      ) =>
        plan.approved &&
        (
          finiteOrNull(
            plan.allocatedQuantity,
          ) ??
          0
        ) > 0,
    )
    .map(
      (
        plan,
        index,
      ) => ({
        id:
          `phase2-${index + 1}-${plan.symbol}`,

        symbol:
          normalizeSymbol(
            plan.symbol,
          ),

        side:
          plan.side ??
          "BUY",

        type:
          "MARKET",

        quantity:
          plan.allocatedQuantity,
      }),
    );
}

function summarizeExecutions(
  execution,
) {
  const executions =
    safeArray(
      execution?.executions,
    );

  const successful =
    executions.filter(
      (
        item,
      ) =>
        item.status ===
          "FILLED" ||
        item.status ===
          "PARTIALLY_FILLED",
    );

  const averageSlippage =
    successful.length
      ? successful.reduce(
          (
            sum,
            item,
          ) =>
            sum +
            (
              finiteOrNull(
                item.slippagePercent,
              ) ??
              0
            ),
          0,
        ) /
        successful.length
      : null;

  return {
    orderCount:
      execution?.orderCount ??
      0,

    filledCount:
      execution?.filledCount ??
      0,

    rejectedCount:
      execution?.rejectedCount ??
      0,

    unfilledCount:
      execution?.unfilledCount ??
      0,

    totalFees:
      execution?.totalFees ??
      0,

    averageSlippagePercent:
      averageSlippage === null
        ? null
        : round(
            averageSlippage,
          ),
  };
}

function calculateGate({
  rolling,
  monteCarlo,
  portfolio,
  risk,
  capacity,
  execution,
}) {
  const checks = {
    rollingValidation:
      rolling?.ready === true &&
      rolling?.passed === true,

    monteCarlo:
      monteCarlo?.ready === true &&
      monteCarlo?.passed === true,

    portfolio:
      portfolio?.ready === true,

    risk:
      risk?.ready === true &&
      risk?.approved === true,

    capacity:
      capacity?.ready === true &&
      capacity?.approved === true,

    execution:
      (
        execution?.filledCount ??
        0
      ) > 0 &&
      (
        execution?.rejectedCount ??
        0
      ) === 0,
  };

  const entries =
    Object.entries(
      checks,
    );

  const passedCount =
    entries.filter(
      (
        [
          ,
          passed,
        ],
      ) =>
        passed,
    ).length;

  const score =
    entries.length
      ? (
          passedCount /
          entries.length
        ) *
        100
      : 0;

  const blockers =
    entries
      .filter(
        (
          [
            ,
            passed,
          ],
        ) =>
          !passed,
      )
      .map(
        (
          [
            name,
          ],
        ) =>
          name,
      );

  return {
    approved:
      blockers.length === 0,

    score:
      round(
        score,
        2,
      ),

    passedCount,

    totalChecks:
      entries.length,

    checks,

    blockers,
  };
}

export async function runPhase2RuntimeIntegration({
  records = [],
  predictor,
  splitter = {},
  predictionHorizon = 1,
  neutralThreshold = 0,
  minimumAccuracy = 50,

  returns = [],
  monteCarlo = {},

  assets = [],
  portfolio = {},

  candidates = [],
  capacity = {},

  marketBySymbol = {},
  execution = {},

  equity = 100000,
  risk = {},
} = {}) {
  if (
    typeof predictor !==
    "function"
  ) {
    throw new TypeError(
      "Phase2 runtime predictor must be a function.",
    );
  }

  const normalizedEquity =
    finiteOrNull(
      equity,
    );

  if (
    normalizedEquity === null ||
    normalizedEquity <= 0
  ) {
    throw new TypeError(
      "Phase2 runtime equity must be greater than zero.",
    );
  }

  const rollingResult =
    await runRollingValidation({
      records:
        safeArray(
          records,
        ),

      predictor,

      splitter,

      predictionHorizon,

      neutralThreshold,

      minimumAccuracy,
    });

  const monteCarloResult =
    runMonteCarloValidation({
      ...monteCarlo,

      returns:
        safeArray(
          returns,
        ),
    });

  const portfolioResult =
    optimizePortfolio({
      ...portfolio,

      assets:
        safeArray(
          assets,
        ),
    });

  const capacityResult =
    planTradingCapacity({
      capital:
        normalizedEquity,

      ...capacity,

      candidates:
        safeArray(
          candidates,
        ),
    });

  const riskPositions =
    createRiskPositions({
      portfolio:
        portfolioResult,

      capacity:
        capacityResult,

      marketBySymbol,
    });

  const riskResult =
    evaluatePortfolioRisk({
      equity:
        normalizedEquity,

      ...risk,

      returns:
        safeArray(
          returns,
        ),

      positions:
        riskPositions,
    });

  const orders =
    createExecutionOrders(
      capacityResult,
    );

  const executionResult =
    simulateExecutionBatch({
      orders,

      marketBySymbol,

      config:
        execution,
    });

  const gate =
    calculateGate({
      rolling:
        rollingResult,

      monteCarlo:
        monteCarloResult,

      portfolio:
        portfolioResult,

      risk:
        riskResult,

      capacity:
        capacityResult,

      execution:
        executionResult,
    });

  return {
    version:
      PHASE2_RUNTIME_INTEGRATION_V2_VERSION,

    ready:
      rollingResult.ready &&
      monteCarloResult.ready &&
      portfolioResult.ready &&
      capacityResult.ready,

    approved:
      gate.approved,

    gate,

    rollingValidation:
      rollingResult,

    monteCarloValidation:
      monteCarloResult,

    portfolioOptimization:
      portfolioResult,

    riskEvaluation:
      riskResult,

    capacityPlan:
      capacityResult,

    executionSimulation:
      executionResult,

    summary: {
      rollingAccuracy:
        rollingResult.aggregate
          ?.meanAccuracy ??
        null,

      monteCarloSuccessRate:
        monteCarloResult.summary
          ?.successRate ??
        null,

      portfolioExpectedReturn:
        portfolioResult.metrics
          ?.expectedReturn ??
        null,

      portfolioVolatility:
        portfolioResult.metrics
          ?.volatility ??
        null,

      riskScore:
        riskResult.riskScore ??
        null,

      riskLevel:
        riskResult.riskLevel ??
        null,

      approvedCapacityPlans:
        capacityResult.approvedCount ??
        0,

      execution:
        summarizeExecutions(
          executionResult,
        ),
    },

    diagnostics: {
      recordCount:
        safeArray(
          records,
        ).length,

      returnCount:
        safeArray(
          returns,
        ).length,

      assetCount:
        safeArray(
          assets,
        ).length,

      candidateCount:
        safeArray(
          candidates,
        ).length,

      orderCount:
        orders.length,

      riskPositionCount:
        riskPositions.length,
    },
  };
}

export class Phase2RuntimeIntegrationV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  run(
    input = {},
  ) {
    return runPhase2RuntimeIntegration({
      ...this.config,

      ...input,
    });
  }
}

export const phase2RuntimeIntegrationV2 =
  new Phase2RuntimeIntegrationV2();

export default runPhase2RuntimeIntegration;