import { deriveExpectedMove } from "../analysis/prediction-output.js";
import {
  DEFAULT_MODEL_CALIBRATION,
  directionFromScore,
  normalizeModelCalibration,
} from "../learning/model-calibration.js";
import { deriveTradeDecision } from "../learning/evaluation-policy.js";
import { calculateWeightedScore } from "./market-score.js";
import { PREDICTION_FEATURE_KEYS } from "./prediction-feature-model.js";

export const MARKET_PREDICTION_MODEL_VERSION =
  "market-intelligence-multi-horizon-v1";

export const PREDICTION_HORIZONS = Object.freeze([1, 3, 5, 10, 20]);

export const HORIZON_FEATURE_WEIGHTS = Object.freeze({
  1: Object.freeze({
    marketScore: 10,
    breadth: 12,
    liquidity: 12,
    volatility: 15,
    macro: 5,
    newsScore: 18,
    sectorStrength: 5,
    momentum: 15,
    fearGreed: 5,
    compositeAI: 3,
  }),
  3: Object.freeze({
    marketScore: 10,
    breadth: 12,
    liquidity: 10,
    volatility: 12,
    macro: 8,
    newsScore: 16,
    sectorStrength: 8,
    momentum: 14,
    fearGreed: 5,
    compositeAI: 5,
  }),
  5: Object.freeze({
    marketScore: 12,
    breadth: 12,
    liquidity: 8,
    volatility: 10,
    macro: 12,
    newsScore: 14,
    sectorStrength: 10,
    momentum: 12,
    fearGreed: 5,
    compositeAI: 5,
  }),
  10: Object.freeze({
    marketScore: 14,
    breadth: 10,
    liquidity: 6,
    volatility: 10,
    macro: 17,
    newsScore: 10,
    sectorStrength: 13,
    momentum: 10,
    fearGreed: 5,
    compositeAI: 5,
  }),
  20: Object.freeze({
    marketScore: 15,
    breadth: 8,
    liquidity: 5,
    volatility: 10,
    macro: 20,
    newsScore: 8,
    sectorStrength: 17,
    momentum: 8,
    fearGreed: 4,
    compositeAI: 5,
  }),
});

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function confidenceLabel(score) {
  if (score >= 75) return "高";
  if (score >= 55) return "中";
  return "低";
}

function featureReport(featureSet, key) {
  const detail = featureSet?.details?.[key] || {};
  const rawScore = finiteOrNull(detail.score ?? featureSet?.values?.[key]);
  const score =
    rawScore === null
      ? null
      : key === "volatility"
        ? 100 - rawScore
        : rawScore;

  return {
    score,
    confidence: finiteOrNull(detail.confidence) ?? 0,
    coverage: finiteOrNull(detail.coverage) ?? 0,
  };
}

function explainComponents(components, featureSet) {
  return components.map((component) => ({
    ...component,
    rawScore: finiteOrNull(featureSet?.values?.[component.key]),
    polarity:
      component.key === "volatility" ? "risk-inverted" : "supportive",
  }));
}

function createHorizonPrediction({
  featureSet,
  horizon,
  weights,
  atrPercent,
  calibration,
}) {
  const aggregate = calculateWeightedScore(
    PREDICTION_FEATURE_KEYS.map((key) => ({
      key,
      report: featureReport(featureSet, key),
      weight: Math.max(0, finiteOrNull(weights?.[key]) ?? 0),
    })),
  );
  const score = aggregate.score;
  const direction =
    score === null ? "判定不能" : directionFromScore(score, calibration);
  const expectedMove =
    score === null
      ? { expectedReturn: null, lower: null, upper: null, amplitude: null }
      : deriveExpectedMove({ score, atrPercent, period: horizon });
  const confidenceScore = aggregate.confidence;
  const dataQualityScore = Math.min(
    aggregate.confidence,
    aggregate.coverage,
  );
  const decision =
    direction === "判定不能"
      ? {
          action: "見送り",
          isActionable: false,
          reasons: ["利用可能な市場特徴量がありません。"],
          policy: { ...calibration },
        }
      : deriveTradeDecision({
          direction,
          confidenceScore,
          dataQualityScore,
          policy: {
            minimumConfidenceScore: calibration.minimumConfidenceScore,
          },
        });

  return {
    modelVersion: MARKET_PREDICTION_MODEL_VERSION,
    horizon,
    horizonUnit: "trading_days",
    score,
    direction,
    status:
      score === null
        ? "unavailable"
        : decision.isActionable
          ? "ready"
          : "low_confidence",
    confidence: {
      score: confidenceScore,
      label: confidenceLabel(confidenceScore),
      coverage: aggregate.coverage,
      method: "市場特徴量の取得品質とカバレッジ",
      isProbability: false,
    },
    expectedReturn: expectedMove.expectedReturn,
    expectedMoveRange:
      finiteOrNull(expectedMove.amplitude) === null
        ? null
        : {
            lower: expectedMove.lower,
            upper: expectedMove.upper,
            amplitude: expectedMove.amplitude,
            center: expectedMove.expectedReturn,
            method: `ATR×√${horizon}の概算`,
          },
    downsideRisk:
      finiteOrNull(expectedMove.lower) === null
        ? null
        : Math.abs(Math.min(0, expectedMove.lower)),
    decision: {
      ...decision,
      purpose: "forecast_evaluation",
      executionAllowed: false,
    },
    components: explainComponents(aggregate.components, featureSet),
    timestamp: featureSet?.timestamp ?? null,
  };
}

function normalizeHorizonWeights(weights = HORIZON_FEATURE_WEIGHTS) {
  return Object.freeze(
    Object.fromEntries(
      PREDICTION_HORIZONS.map((horizon) => [
        horizon,
        Object.freeze({
          ...HORIZON_FEATURE_WEIGHTS[horizon],
          ...(weights?.[horizon] || {}),
        }),
      ]),
    ),
  );
}

export function predictMultipleHorizons(
  featureSet,
  {
    atrPercent = null,
    calibration = DEFAULT_MODEL_CALIBRATION,
    weights = HORIZON_FEATURE_WEIGHTS,
  } = {},
) {
  if (!featureSet || typeof featureSet !== "object") {
    throw new TypeError("Prediction feature set is required.");
  }

  const normalizedCalibration = normalizeModelCalibration(calibration);
  const normalizedWeights = normalizeHorizonWeights(weights);

  return PREDICTION_HORIZONS.map((horizon) =>
    createHorizonPrediction({
      featureSet,
      horizon,
      weights: normalizedWeights[horizon],
      atrPercent,
      calibration: normalizedCalibration,
    }),
  );
}

export class MultiHorizonPredictionEngine {
  constructor({
    calibration = DEFAULT_MODEL_CALIBRATION,
    weights = HORIZON_FEATURE_WEIGHTS,
  } = {}) {
    this.calibration = normalizeModelCalibration(calibration);
    this.weights = normalizeHorizonWeights(weights);
  }

  predict(featureSet, options = {}) {
    return predictMultipleHorizons(featureSet, {
      ...options,
      calibration: options.calibration ?? this.calibration,
      weights: this.weights,
    });
  }
}

export const multiHorizonPredictionEngine =
  new MultiHorizonPredictionEngine();

export const MultiHorizonPredictionInternals = Object.freeze({
  featureReport,
  createHorizonPrediction,
  normalizeHorizonWeights,
});

export default predictMultipleHorizons;
