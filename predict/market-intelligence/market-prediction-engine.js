import { predictionFeatureComposer } from "./prediction-feature-composer.js";
import { multiHorizonPredictionEngine } from "./multi-horizon-prediction-engine.js";
import { buildPredictionFeedbackRecords } from "./prediction-feedback-adapter.js";

function requireMethod(value, method, label) {
  if (!value || typeof value[method] !== "function") {
    throw new TypeError(`Market Prediction ${label} is invalid.`);
  }
}

function resultStatus(features, predictions) {
  if (features.status === "unavailable") return "unavailable";
  if (predictions.every((prediction) => prediction.status !== "ready")) {
    return "validation_required";
  }
  return features.status === "ready" ? "ready" : "partial";
}

export class MarketPredictionEngine {
  constructor({
    featureComposer = predictionFeatureComposer,
    predictionEngine = multiHorizonPredictionEngine,
  } = {}) {
    requireMethod(featureComposer, "compose", "feature composer");
    requireMethod(predictionEngine, "predict", "horizon engine");

    this.featureComposer = featureComposer;
    this.predictionEngine = predictionEngine;
  }

  analyze(input = {}, options = {}) {
    const features = this.featureComposer.compose(input, {
      timestamp: options.timestamp,
    });
    const predictions = this.predictionEngine.predict(features, {
      atrPercent:
        options.atrPercent ??
        input.technical?.atrPercent ??
        input.technical?.atr?.percent ??
        null,
      calibration: options.calibration,
    });

    return {
      modelVersion: predictions[0]?.modelVersion ?? null,
      status: resultStatus(features, predictions),
      timestamp: features.timestamp,
      features,
      predictions,
      horizons: predictions.map((prediction) => prediction.horizon),
      executionAllowed: false,
    };
  }

  buildFeedback(result, metadata = {}) {
    return buildPredictionFeedbackRecords({
      ...metadata,
      featureSet: result?.features,
      predictions: result?.predictions,
    });
  }
}

export const marketPredictionEngine = new MarketPredictionEngine();

export default MarketPredictionEngine;
