import {
  marketIntelligenceOrchestrator,
} from "../market-intelligence/market-intelligence-orchestrator.js";
import {
  marketPredictionEngine,
} from "../market-intelligence/market-prediction-engine.js";
import {
  PREDICTION_HORIZONS,
} from "../market-intelligence/multi-horizon-prediction-engine.js";

export const MARKET_INTELLIGENCE_RUNTIME_VERSION =
  "market-intelligence-runtime-v1";

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number(value)));
}

function resolveSource(input = {}) {
  const source =
    input.marketIntelligenceResult ??
    input.marketIntelligence ??
    input.state?.marketIntelligence ??
    null;

  return {
    enabled: source !== null && source !== undefined,
    source,
  };
}

export function resolvePredictionHorizon(value) {
  const requested = finiteOrNull(value);

  if (requested === null || requested <= 0) {
    return 5;
  }

  return PREDICTION_HORIZONS.reduce((nearest, horizon) => {
    const distance = Math.abs(horizon - requested);
    const nearestDistance = Math.abs(nearest - requested);

    return distance < nearestDistance ? horizon : nearest;
  }, PREDICTION_HORIZONS[0]);
}

function predictionResult(source) {
  if (!source || typeof source !== "object") return null;

  if (Array.isArray(source.predictions) && source.features) {
    return source;
  }

  if (
    Array.isArray(source.prediction?.predictions) &&
    source.prediction?.features
  ) {
    return source.prediction;
  }

  if (
    Array.isArray(source.result?.predictions) &&
    source.result?.features
  ) {
    return source.result;
  }

  return null;
}

function directionAction(direction, score) {
  const normalized = String(direction ?? "").trim().toUpperCase();

  if (["上昇", "BUY", "BULLISH", "UP"].includes(normalized)) {
    return "BUY";
  }

  if (["下落", "SELL", "BEARISH", "DOWN"].includes(normalized)) {
    return "SELL";
  }

  if (["中立", "HOLD", "NEUTRAL", "判定不能"].includes(normalized)) {
    return "HOLD";
  }

  const numericScore = finiteOrNull(score);

  if (numericScore === null) return "HOLD";
  if (numericScore >= 55) return "BUY";
  if (numericScore <= 45) return "SELL";
  return "HOLD";
}

function selectedPrediction(result, horizon) {
  return (
    result?.predictions?.find(
      (prediction) => Number(prediction?.horizon) === horizon,
    ) ?? null
  );
}

function predictionConfidence(prediction) {
  return clamp(
    finiteOrNull(prediction?.confidence?.score ?? prediction?.confidence) ?? 0,
  );
}

function isParticipating(prediction) {
  return Boolean(
    prediction?.status === "ready" &&
      finiteOrNull(prediction?.score) !== null &&
      predictionConfidence(prediction) > 0,
  );
}

function predictionSummaries(result) {
  return (Array.isArray(result?.predictions) ? result.predictions : []).map(
    (prediction) => ({
      horizon: finiteOrNull(prediction?.horizon),
      direction: prediction?.direction ?? "判定不能",
      score: finiteOrNull(prediction?.score),
      confidence: predictionConfidence(prediction),
      coverage: clamp(
        finiteOrNull(prediction?.confidence?.coverage) ?? 0,
      ),
      status: prediction?.status ?? "unavailable",
      expectedReturn: finiteOrNull(prediction?.expectedReturn),
      executionAllowed: false,
    }),
  );
}

function notRequestedReport(horizon) {
  return {
    version: MARKET_INTELLIGENCE_RUNTIME_VERSION,
    enabled: false,
    status: "not_requested",
    participating: false,
    requestedHorizon: horizon,
    selectedHorizon: horizon,
    selectedPrediction: null,
    predictions: [],
    engine: null,
    result: null,
    error: null,
    executionAllowed: false,
  };
}

function errorReport(horizon, error) {
  return {
    ...notRequestedReport(horizon),
    enabled: true,
    status: "error",
    error: {
      name: error?.name ?? "Error",
      message: error?.message ?? String(error),
    },
  };
}

export function buildMarketIntelligenceRuntimeReport({
  source,
  requestedHorizon = 5,
  weight = 1,
} = {}) {
  const reusableResult =
    source?.version === MARKET_INTELLIGENCE_RUNTIME_VERSION
      ? source.result
      : null;

  if (
    source?.version === MARKET_INTELLIGENCE_RUNTIME_VERSION &&
    !predictionResult(reusableResult)
  ) {
    return source;
  }

  const resolvedSource =
    reusableResult ?? source;
  const horizon = resolvePredictionHorizon(requestedHorizon);
  const result = predictionResult(resolvedSource);

  if (!result) {
    return errorReport(
      horizon,
      new TypeError("Market Intelligence prediction result is invalid."),
    );
  }

  const selected = selectedPrediction(result, horizon);
  const participating = isParticipating(selected);
  const confidence = predictionConfidence(selected);
  const score = finiteOrNull(selected?.score);
  const normalizedWeight = Math.max(0, finiteOrNull(weight) ?? 1);

  return {
    version: MARKET_INTELLIGENCE_RUNTIME_VERSION,
    enabled: true,
    status: resolvedSource?.status ?? result.status ?? "unavailable",
    participating,
    requestedHorizon: finiteOrNull(requestedHorizon) ?? horizon,
    selectedHorizon: horizon,
    selectedPrediction: selected,
    predictions: predictionSummaries(result),
    featureStatus: result.features?.status ?? "unavailable",
    featureConfidence: clamp(
      finiteOrNull(result.features?.confidence) ?? 0,
    ),
    featureCoverage: clamp(
      finiteOrNull(result.features?.coverage) ?? 0,
    ),
    engine: participating
      ? {
          name: "market-intelligence",
          weight: normalizedWeight,
          result: {
            action: directionAction(selected.direction, score),
            score,
            confidence,
          },
        }
      : null,
    result: resolvedSource,
    error: null,
    executionAllowed: false,
  };
}

export class MarketIntelligenceRuntimeAdapter {
  constructor({
    orchestrator = marketIntelligenceOrchestrator,
    predictionEngine = marketPredictionEngine,
  } = {}) {
    if (!orchestrator || typeof orchestrator.analyze !== "function") {
      throw new TypeError("Market Intelligence orchestrator is invalid.");
    }

    if (!predictionEngine || typeof predictionEngine.analyze !== "function") {
      throw new TypeError("Market Intelligence prediction engine is invalid.");
    }

    this.orchestrator = orchestrator;
    this.predictionEngine = predictionEngine;
  }

  async analyze(input = {}) {
    const horizon = resolvePredictionHorizon(
      input.predictionHorizon ?? input.period,
    );
    const resolved = resolveSource(input);

    if (!resolved.enabled) return notRequestedReport(horizon);

    try {
      const source =
        resolved.source?.version === MARKET_INTELLIGENCE_RUNTIME_VERSION ||
        predictionResult(resolved.source)
          ? resolved.source
          : await this.orchestrator.analyze(resolved.source, {
              timestamp: input.marketIntelligenceTimestamp,
              atrPercent: input.atrPercent,
              calibration: input.marketIntelligenceCalibration,
              forceRefresh: input.forceMarketIntelligenceRefresh,
              signal: input.signal,
            });

      return buildMarketIntelligenceRuntimeReport({
        source,
        requestedHorizon: input.predictionHorizon ?? input.period,
        weight: input.marketIntelligenceWeight,
      });
    } catch (error) {
      if (error?.name === "AbortError") throw error;
      return errorReport(horizon, error);
    }
  }

  analyzeSync(input = {}) {
    const horizon = resolvePredictionHorizon(
      input.predictionHorizon ?? input.period,
    );
    const resolved = resolveSource(input);

    if (!resolved.enabled) return notRequestedReport(horizon);

    try {
      const source =
        resolved.source?.version === MARKET_INTELLIGENCE_RUNTIME_VERSION ||
        predictionResult(resolved.source)
          ? resolved.source
          : this.predictionEngine.analyze(resolved.source, {
              timestamp: input.marketIntelligenceTimestamp,
              atrPercent: input.atrPercent,
              calibration: input.marketIntelligenceCalibration,
            });

      return buildMarketIntelligenceRuntimeReport({
        source,
        requestedHorizon: input.predictionHorizon ?? input.period,
        weight: input.marketIntelligenceWeight,
      });
    } catch (error) {
      return errorReport(horizon, error);
    }
  }
}

export const marketIntelligenceRuntimeAdapter =
  new MarketIntelligenceRuntimeAdapter();

export const MarketIntelligenceRuntimeAdapterInternals = Object.freeze({
  finiteOrNull,
  clamp,
  resolveSource,
  predictionResult,
  directionAction,
  selectedPrediction,
  predictionConfidence,
  isParticipating,
  predictionSummaries,
  notRequestedReport,
  errorReport,
});

export default MarketIntelligenceRuntimeAdapter;
