import {
  calculateFeatureImportance,
} from "./feature-importance-engine.js";

import {
  buildMarketBreadthV2,
} from "../market-intelligence/market-breadth-v2.js";

import {
  rankSectorRotation,
} from "../market-intelligence/sector-rotation-engine.js";

import {
  calculateCompositeMarketScoreV2,
} from "../market-intelligence/composite-market-score-v2.js";

import {
  buildConfidenceCalibrationModel,
  calibrateConfidence,
  evaluateConfidenceCalibration,
} from "./confidence-calibration-v2.js";

import {
  buildExplainabilityReport,
} from "./explainability-v2.js";

export const RUNTIME_INTEGRATION_V2_VERSION =
  "runtime-integration-v2";

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

function normalizeDirection(value) {
  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "BUY",
      "BULLISH",
      "UP",
      "LONG",
      "POSITIVE",
    ].includes(text)
  ) {
    return "BULLISH";
  }

  if (
    [
      "SELL",
      "BEARISH",
      "DOWN",
      "SHORT",
      "NEGATIVE",
    ].includes(text)
  ) {
    return "BEARISH";
  }

  return "NEUTRAL";
}

function normalizePrediction(
  prediction = {},
) {
  const score =
    clamp(
      prediction.score ??
      prediction.confidence ??
      50,
    ) ?? 50;

  return {
    ...prediction,

    direction:
      normalizeDirection(
        prediction.direction ??
        prediction.signal ??
        prediction.recommendation,
      ),

    score,

    confidence:
      clamp(
        prediction.confidence ??
        score,
      ) ?? score,
  };
}

function mapFeatureImportance(
  importance = [],
) {
  return importance.map(
    (
      feature,
    ) => ({
      name:
        feature.name,

      value:
        feature.value,

      weight:
        feature.weight,

      contribution:
        feature.contribution,

      reason:
        feature.reason ??
        "",
    }),
  );
}

function marketComponent(
  score,
  confidence = 100,
  coverage = 100,
) {
  const normalizedScore =
    clamp(score);

  if (normalizedScore === null) {
    return null;
  }

  return {
    score:
      normalizedScore,

    confidence:
      clamp(confidence) ??
      100,

    coverage:
      clamp(coverage) ??
      100,
  };
}

function sectorRotationScore(
  report,
) {
  const strongest =
    finiteOrNull(
      report?.summary?.strongest?.score,
    );

  const weakest =
    finiteOrNull(
      report?.summary?.weakest?.score,
    );

  if (
    strongest === null &&
    weakest === null
  ) {
    return null;
  }

  if (strongest !== null && weakest !== null) {
    return (
      strongest +
      (
        100 -
        weakest
      )
    ) / 2;
  }

  return strongest ??
    (
      100 -
      weakest
    );
}

function buildRuntimeWarnings({
  calibratedConfidence,
  marketScore,
  explainability,
  calibration,
}) {
  const warnings = [];

  if (
    calibratedConfidence !== null &&
    calibratedConfidence < 40
  ) {
    warnings.push(
      "Calibrated prediction confidence is low.",
    );
  }

  if (
    marketScore?.regime ===
    "FRAGMENTED"
  ) {
    warnings.push(
      "Market components disagree strongly.",
    );
  }

  if (
    explainability?.agreement ===
    "CONFLICTS"
  ) {
    warnings.push(
      "Prediction direction conflicts with dominant feature contributions.",
    );
  }

  if (
    calibration?.status ===
    "POOR"
  ) {
    warnings.push(
      "Historical confidence calibration is poor.",
    );
  }

  return warnings;
}

export function buildRuntimeIntegrationV2({
  prediction = {},
  features = {},
  marketBreadth = {},
  marketBreadthHistory = [],
  sectors = [],
  benchmark = {},
  liquidity = null,
  volatility = null,
  news = null,
  confidenceHistory = [],
  timestamp = null,
  now = Date.now,
} = {}) {
  if (typeof now !== "function") {
    throw new TypeError(
      "Runtime Integration v2 clock must be a function.",
    );
  }

  const generatedAt =
    new Date(
      timestamp ??
      now(),
    );

  if (
    Number.isNaN(
      generatedAt.getTime(),
    )
  ) {
    throw new TypeError(
      "Runtime Integration v2 timestamp is invalid.",
    );
  }

  const normalizedPrediction =
    normalizePrediction(
      prediction,
    );

  const featureImportance =
    calculateFeatureImportance(
      features,
      normalizedPrediction,
    );

  const breadthReport =
    buildMarketBreadthV2({
      snapshot:
        marketBreadth,

      history:
        marketBreadthHistory,
    });

  const sectorReport =
    rankSectorRotation({
      sectors,
      benchmark,
    });

  const calibration =
    evaluateConfidenceCalibration(
      confidenceHistory,
    );

  const calibrationModel =
    buildConfidenceCalibrationModel(
      confidenceHistory,
    );

  const calibratedConfidence =
    calibrateConfidence(
      normalizedPrediction.confidence,
      calibrationModel,
    );

  const strongestSectorScore =
    finiteOrNull(
      sectorReport?.summary?.strongest?.score,
    );

  const rotationScore =
    sectorRotationScore(
      sectorReport,
    );

  const compositeMarket =
    calculateCompositeMarketScoreV2({
      breadth:
        marketComponent(
          breadthReport.score,
          breadthReport.score === null
            ? 0
            : 100,
          breadthReport.score === null
            ? 0
            : 100,
        ),

      liquidity:
        liquidity,

      sectorStrength:
        marketComponent(
          strongestSectorScore,
          strongestSectorScore === null
            ? 0
            : 100,
          strongestSectorScore === null
            ? 0
            : 100,
        ),

      sectorRotation:
        marketComponent(
          rotationScore,
          rotationScore === null
            ? 0
            : 100,
          rotationScore === null
            ? 0
            : 100,
        ),

      volatility,
      news,

      timestamp:
        generatedAt.toISOString(),

      now,
    });

  const explainability =
    buildExplainabilityReport({
      prediction: {
        ...normalizedPrediction,

        confidence:
          calibratedConfidence ??
          normalizedPrediction.confidence,
      },

      features:
        mapFeatureImportance(
          featureImportance,
        ),

      marketContext: {
        regime:
          compositeMarket.regime,

        score:
          compositeMarket.score,

        confidence:
          compositeMarket.confidence,
      },

      timestamp:
        generatedAt.toISOString(),

      now,
    });

  const warnings =
    buildRuntimeWarnings({
      calibratedConfidence,
      marketScore:
        compositeMarket,
      explainability,
      calibration,
    });

  return {
    version:
      RUNTIME_INTEGRATION_V2_VERSION,

    timestamp:
      generatedAt.toISOString(),

    prediction: {
      raw:
        normalizedPrediction,

      calibratedConfidence,

      calibrationStatus:
        calibration.status,
    },

    featureImportance,

    market: {
      breadth:
        breadthReport,

      sectors:
        sectorReport,

      composite:
        compositeMarket,
    },

    calibration,

    explainability,

    decisionSupport: {
      direction:
        normalizedPrediction.direction,

      confidence:
        calibratedConfidence ??
        normalizedPrediction.confidence,

      marketRegime:
        compositeMarket.regime,

      marketScore:
        compositeMarket.score,

      explanationQuality:
        explainability.explanationQuality,

      agreement:
        explainability.agreement,

      warningCount:
        warnings.length,

      warnings,
    },

    diagnostics: {
      featureCount:
        featureImportance.length,

      confidenceHistorySize:
        confidenceHistory.length,

      sectorCount:
        sectorReport.summary.sectorCount,

      marketBreadthAvailable:
        breadthReport.score !== null,

      compositeMarketAvailable:
        compositeMarket.score !== null,
    },
  };
}

export class RuntimeIntegrationV2Engine {
  constructor({
    now = Date.now,
  } = {}) {
    if (typeof now !== "function") {
      throw new TypeError(
        "Runtime Integration v2 clock must be a function.",
      );
    }

    this.now =
      now;
  }

  run(
    input = {},
  ) {
    return buildRuntimeIntegrationV2({
      ...input,

      now:
        this.now,
    });
  }
}

export const runtimeIntegrationV2Engine =
  new RuntimeIntegrationV2Engine();

export default buildRuntimeIntegrationV2;