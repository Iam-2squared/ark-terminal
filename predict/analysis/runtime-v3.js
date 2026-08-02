import {
  runtimeV2,
} from "./runtime-v2.js";

import {
  buildConsensus,
} from "./consensus-engine.js";

import {
  calibrateConfidence,
} from "./confidence-calibrator.js";

import {
  evaluateRiskAwareDecision,
} from "./risk-aware-decision-gate.js";

import {
  buildFinalTradePlan,
} from "./final-trade-plan-engine.js";

import {
  summarizeRealtimeAlerts,
} from "./realtime-alert-engine.js";

import {
  buildPredictionLabV3ViewModel,
} from "./prediction-lab-v3-dashboard.js";

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

function createRuntimeKey(
  input = {},
) {
  return {
    version:
      "runtime-v3",

    symbol:
      input.symbol ?? null,

    engines:
      input.engines ?? [],

    capital:
      finiteNumber(
        input.capital,
      ),

    price:
      finiteNumber(
        input.price,
      ),

    allocation:
      finiteNumber(
        input.allocation,
      ),

    portfolioRisk:
      input.portfolioRisk ?? {},

    limits:
      input.limits ?? {},
  };
}

export function normalizeRuntimeV3Input(
  input = {},
) {
  return {
    symbol:
      input.symbol ?? null,

    engines:
      Array.isArray(
        input.engines,
      )
        ? input.engines
        : [],

    historicalAccuracy:
      clamp(
        input.historicalAccuracy ?? 50,
      ),

    volatility:
      clamp(
        input.volatility ?? 50,
      ),

    portfolioRisk: {
      riskPercent:
        Math.max(
          0,
          finiteNumber(
            input.portfolioRisk
              ?.riskPercent,
            0,
          ),
        ),
    },

    limits: {
      maximumRiskPercent:
        Math.max(
          0,
          finiteNumber(
            input.limits
              ?.maximumRiskPercent,
            6,
          ),
        ),

      minimumConfidence:
        clamp(
          input.limits
            ?.minimumConfidence ??
          55,
        ),

      minimumScore:
        clamp(
          input.limits
            ?.minimumScore ??
          60,
        ),
    },

    capital:
      Math.max(
        0,
        finiteNumber(
          input.capital,
        ),
      ),

    allocation:
      Math.min(
        1,
        Math.max(
          0,
          finiteNumber(
            input.allocation,
          ),
        ),
      ),

    price:
      Math.max(
        0,
        finiteNumber(
          input.price,
        ),
      ),    lotSize:
      finiteNumber(
        input.lotSize,
        100,
      ) > 0
        ? Math.floor(
            finiteNumber(
              input.lotSize,
              100,
            ),
          )
        : 100,

    stopPercent:
      Math.max(
        0,
        finiteNumber(
          input.stopPercent,
          5,
        ),
      ),

    targetPercent:
      Math.max(
        0,
        finiteNumber(
          input.targetPercent,
          10,
        ),
      ),

    alerts:
      Array.isArray(
        input.alerts,
      )
        ? input.alerts
        : [],

    learning:
      input.learning ?? {},

    macro:
      input.macro ?? "NEUTRAL",

    regime:
      input.regime ?? "RANGE",
  };
}

export function executeRuntimeV3Sync(
  input = {},
) {
  const normalized =
    normalizeRuntimeV3Input(
      input,
    );

  const consensus =
    buildConsensus({
      engines:
        normalized.engines,

      minimumEngines:
        1,
    });

  const calibrated =
    calibrateConfidence({
      score:
        consensus.score,

      agreementRate:
        consensus.agreementRate,

      engineCount:
        consensus.engineCount,

      historicalAccuracy:
        normalized
          .historicalAccuracy,

      volatility:
        normalized.volatility,
    });

  const gatedDecision =
    evaluateRiskAwareDecision({
      decision: {
        action:
          consensus.action,

        score:
          consensus.score,

        confidence:
          calibrated.confidence,
      },

      portfolioRisk:
        normalized.portfolioRisk,

      limits:
        normalized.limits,
    });

  const tradePlan =
    buildFinalTradePlan({
      symbol:
        normalized.symbol,

      decision: {
        action:
          gatedDecision.action,

        score:
          gatedDecision.score,

        confidence:
          gatedDecision.confidence,
      },

      portfolioRisk:
        normalized.portfolioRisk,

      limits:
        normalized.limits,

      capital:
        normalized.capital,

      allocation:
        normalized.allocation,

      price:
        normalized.price,

      lotSize:
        normalized.lotSize,

      stopPercent:
        normalized.stopPercent,

      targetPercent:
        normalized.targetPercent,
    });

  const alertSummary =
    summarizeRealtimeAlerts(
      normalized.alerts,
    );

  const analysis = {
    dashboard: {
      action:
        gatedDecision.action,

      score:
        gatedDecision.score,

      confidence:
        gatedDecision.confidence,

      macro:
        normalized.macro,

      regime:
        normalized.regime,
    },

    decision: {
      buyFactors:
        gatedDecision.approved
          ? [
              "Consensus approved",
              `Agreement ${consensus.agreementRate}%`,
            ]
          : [],

      riskFactors:
        gatedDecision.reasons.length
          ? gatedDecision.reasons
          : [
              "No critical risk detected",
            ],
    },
  };

  const dashboard =
    buildPredictionLabV3ViewModel({
      analysis,

      tradePlan,

      alerts:
        alertSummary,

      runtime:
        runtimeV2.stats(),

      learning:
        normalized.learning,
    });

  return {
    version:
      "prediction-lab-runtime-v3",

    generatedAt:
      new Date()
        .toISOString(),

    normalized,

    consensus,

    calibratedConfidence:
      calibrated,

    gatedDecision,

    tradePlan,

    alertSummary,

    dashboard,

    status:
      "ready",
  };
}

export async function executeRuntimeV3(
  input = {},
) {
  const normalized =
    normalizeRuntimeV3Input(
      input,
    );

  const key =
    createRuntimeKey(
      normalized,
    );

  return runtimeV2.execute(
    key,
    async () =>
      executeRuntimeV3Sync(
        normalized,
      ),
  );
}

export class PredictionLabRuntimeV3 {
  async execute(
    input = {},
  ) {
    return executeRuntimeV3(
      input,
    );
  }

  executeSync(
    input = {},
  ) {
    return executeRuntimeV3Sync(
      input,
    );
  }

  stats() {
    return runtimeV2.stats();
  }
}

export const
predictionLabRuntimeV3 =
new PredictionLabRuntimeV3();

export const RuntimeV3Internals = {
  clamp,
  createRuntimeKey,
  finiteNumber,
};