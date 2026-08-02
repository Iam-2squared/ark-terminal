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

import {
  marketIntelligenceRuntimeAdapter,
} from "./market-intelligence-runtime-adapter.js";

import {
  historicalMarketSnapshotService,
} from "../market-intelligence/historical-market-snapshot-service.js";

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

function marketIntelligenceCacheKey(
  input = {},
) {
  const source =
    input.marketIntelligenceResult ??
    input.marketIntelligence ??
    null;

  if (!source) return null;
  if (source.cacheKey !== undefined) return source.cacheKey;

  return {
    version:
      source.version ?? null,

    status:
      source.status ?? null,

    timestamp:
      source.timestamp ??
      source.features?.timestamp ??
      null,

    marketData:
      source.marketData ?? null,

    observations:
      source.observations ??
      source.marketObservations ??
      null,

    marketSnapshot:
      source.marketSnapshot ??
      source.snapshot ??
      null,

    compositeMarket:
      source.compositeMarket ?? null,

    breadth:
      source.breadth ?? null,

    liquidity:
      source.liquidity ?? null,

    sectorStrength:
      source.sectorStrength ?? null,

    sectorRotation:
      source.sectorRotation ?? null,

    news:
      source.newsIntelligence ??
      source.newsItems ??
      source.news ??
      null,

    technical:
      source.technical ?? null,

    quote:
      source.quote ?? null,

    selectedHorizon:
      source.selectedHorizon ?? null,
  };
}

function marketIntelligenceContext(
  report = {},
) {
  const source =
    report.result ?? {};

  const snapshot =
    source.marketSnapshot ??
    source.snapshot ??
    null;

  return {
    macro:
      snapshot?.macro?.sentiment ??
      null,

    regime:
      snapshot?.regime?.regime ??
      null,
  };
}

function marketIntelligenceFactors(
  report = {},
) {
  if (!report.enabled) {
    return {
      buyFactors: [],
      riskFactors: [],
    };
  }

  if (report.status === "error") {
    return {
      buyFactors: [],
      riskFactors: [
        `Market Intelligence unavailable: ${
          report.error?.message ??
          "unknown error"
        }`,
      ],
    };
  }

  const prediction =
    report.selectedPrediction;

  if (!prediction) {
    return {
      buyFactors: [],
      riskFactors: [
        "Market Intelligence data unavailable",
      ],
    };
  }

  const factor =
    `Market Intelligence ${report.selectedHorizon}d: ` +
    `${prediction.direction} (${Math.round(
      finiteNumber(prediction.score, 50),
    )})`;

  const action =
    report.engine?.result?.action ??
    "HOLD";

  return {
    buyFactors:
      action === "BUY"
        ? [factor]
        : [],

    riskFactors:
      action === "SELL" ||
      !report.participating
        ? [factor]
        : [],
  };
}

function skippedHistoricalSnapshot(reason) {
  return {
    version:
      "historical-market-snapshot-capture-v1",
    status:
      "skipped",
    inserted:
      false,
    retained:
      false,
    reference:
      null,
    error:
      null,
    reason,
    executionAllowed:
      false,
  };
}

function captureHistoricalMarketSnapshot(
  input,
  marketIntelligence,
  service = historicalMarketSnapshotService,
) {
  if (
    input.captureMarketIntelligenceSnapshot !==
    true
  ) {
    return null;
  }

  if (
    !marketIntelligence.enabled ||
    !marketIntelligence.result
  ) {
    return skippedHistoricalSnapshot(
      "market_intelligence_unavailable",
    );
  }

  const captured =
    service.captureSafely({
      symbol:
        input.symbol,
      marketIntelligence,
      metadata: {
        predictionPrice:
          input.price > 0
            ? input.price
            : null,
        requestedHorizon:
          input.predictionHorizon,
        selectedHorizon:
          marketIntelligence.selectedHorizon,
        source:
          "runtime-v3",
      },
    });

  return {
    version:
      captured.version,
    status:
      captured.status,
    inserted:
      captured.inserted,
    retained:
      captured.retained,
    reference:
      captured.reference,
    error:
      captured.error,
    reason:
      null,
    executionAllowed:
      false,
  };
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

    predictionHorizon:
      input.predictionHorizon ??
      input.period ??
      5,

    marketIntelligenceWeight:
      finiteNumber(
        input.marketIntelligenceWeight,
        1,
      ),

    marketIntelligence:
      marketIntelligenceCacheKey(
        input,
      ),

    marketIntelligenceTimestamp:
      input.marketIntelligenceTimestamp ??
      null,

    forceMarketIntelligenceRefresh:
      input.forceMarketIntelligenceRefresh ===
      true,

    captureMarketIntelligenceSnapshot:
      input.captureMarketIntelligenceSnapshot ===
      true,
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

    predictionHorizon:
      Math.max(
        1,
        finiteNumber(
          input.predictionHorizon ??
          input.period,
          5,
        ),
      ),

    marketIntelligenceWeight:
      Math.max(
        0,
        finiteNumber(
          input.marketIntelligenceWeight,
          1,
        ),
      ),

    marketIntelligence:
      input.marketIntelligence ??
      null,

    marketIntelligenceResult:
      input.marketIntelligenceResult ??
      null,

    marketIntelligenceTimestamp:
      input.marketIntelligenceTimestamp ??
      null,

    marketIntelligenceCalibration:
      input.marketIntelligenceCalibration ??
      null,

    atrPercent:
      input.atrPercent ??
      input.marketIntelligence
        ?.technical
        ?.atrPercent ??
      null,

    forceMarketIntelligenceRefresh:
      input.forceMarketIntelligenceRefresh ===
      true,

    captureMarketIntelligenceSnapshot:
      input.captureMarketIntelligenceSnapshot ===
      true,

    marketIntelligenceSnapshot:
      input.marketIntelligenceSnapshot ??
      null,

    signal:
      input.signal,
  };
}

export function executeRuntimeV3Sync(
  input = {},
) {
  const normalized =
    normalizeRuntimeV3Input(
      input,
    );

  const marketIntelligence =
    marketIntelligenceRuntimeAdapter
      .analyzeSync(
        normalized,
      );

  const marketIntelligenceSnapshot =
    normalized.marketIntelligenceSnapshot ??
    captureHistoricalMarketSnapshot(
      normalized,
      marketIntelligence,
    );

  const consensusEngines =
    marketIntelligence.engine
      ? [
          ...normalized.engines,
          marketIntelligence.engine,
        ]
      : normalized.engines;

  const consensus =
    buildConsensus({
      engines:
        consensusEngines,

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

  const marketContext =
    marketIntelligenceContext(
      marketIntelligence,
    );

  const marketFactors =
    marketIntelligenceFactors(
      marketIntelligence,
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
        marketContext.macro ??
        normalized.macro,

      regime:
        marketContext.regime ??
        normalized.regime,
    },

    decision: {
      buyFactors:
        gatedDecision.approved
          ? [
              "Consensus approved",
              `Agreement ${consensus.agreementRate}%`,
              ...marketFactors.buyFactors,
            ]
          : marketFactors.buyFactors,

      riskFactors:
        gatedDecision.reasons.length
          ? [
              ...gatedDecision.reasons,
              ...marketFactors.riskFactors,
            ]
          : marketFactors.riskFactors.length
            ? marketFactors.riskFactors
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

      marketIntelligence,
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

    marketIntelligence,

    marketIntelligenceSnapshot,

    dashboard,

    status:
      "ready",
  };
}

async function executeRuntimeV3WithMarketIntelligence(
  normalized,
) {
  const marketIntelligence =
    await marketIntelligenceRuntimeAdapter
      .analyze(
        normalized,
      );

  return executeRuntimeV3Sync({
    ...normalized,
    marketIntelligenceResult:
      marketIntelligence,
  });
}

export async function executeRuntimeV3(
  input = {},
) {
  const normalized =
    normalizeRuntimeV3Input(
      input,
    );

  if (
    normalized
      .forceMarketIntelligenceRefresh
  ) {
    return executeRuntimeV3WithMarketIntelligence(
      normalized,
    );
  }

  const key =
    createRuntimeKey(
      normalized,
    );

  return runtimeV2.execute(
    key,
    () =>
      executeRuntimeV3WithMarketIntelligence(
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
  executeRuntimeV3WithMarketIntelligence,
  marketIntelligenceCacheKey,
  marketIntelligenceContext,
  marketIntelligenceFactors,
  skippedHistoricalSnapshot,
  captureHistoricalMarketSnapshot,
};
