import {
  calculateCompositeMarketScore,
  calculateWeightedScore,
  scoreDirectionalChange,
} from "./market-score.js";
import { scoreVixVolatility } from "./market-regime.js";
import { calculateFearGreed } from "./fear-greed-engine.js";
import { createPredictionFeatureSet } from "./prediction-feature-model.js";

export const COMPOSITE_AI_WEIGHTS = Object.freeze({
  marketScore: 15,
  breadth: 12,
  liquidity: 8,
  volatility: 12,
  macro: 12,
  newsScore: 13,
  sectorStrength: 10,
  momentum: 10,
  fearGreed: 8,
});

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

function asReport(value, { source, sourceTimestamp = null } = {}) {
  const input = value && typeof value === "object" ? value : { score: value };
  const score = finiteOrNull(input?.score);

  return {
    score: score === null ? null : clamp(score),
    confidence:
      score === null ? 0 : clamp(finiteOrNull(input?.confidence) ?? 0),
    coverage:
      score === null ? 0 : clamp(finiteOrNull(input?.coverage) ?? 100),
    source: String(input?.source || source || "unknown"),
    sourceTimestamp: input?.timestamp ?? sourceTimestamp ?? null,
  };
}

function marketScoreReport(snapshot, compositeMarket) {
  if (snapshot?.indexes || snapshot?.macro) {
    return {
      ...calculateCompositeMarketScore({
        indexes: snapshot.indexes,
        macro: snapshot.macro,
      }),
      source: "market-snapshot",
      sourceTimestamp: snapshot.timestamp ?? null,
    };
  }

  return asReport(compositeMarket ?? snapshot, {
    source: compositeMarket ? "composite-market-score" : "market-snapshot",
    sourceTimestamp: compositeMarket?.timestamp ?? snapshot?.timestamp ?? null,
  });
}

function vixItem(snapshot) {
  return snapshot?.macro?.items?.find((item) => item?.symbol === "VIX") || null;
}

function volatilityReport(input, snapshot) {
  if (input !== null && input !== undefined) {
    return asReport(input, { source: "volatility-input" });
  }

  const vix = vixItem(snapshot);
  const level =
    vix?.available === false
      ? null
      : finiteOrNull(vix?.price ?? snapshot?.macro?.vixLevel);
  const score = scoreVixVolatility(level);

  return {
    score,
    confidence:
      score === null
        ? 0
        : clamp(
            finiteOrNull(vix?.confidence) ??
              finiteOrNull(snapshot?.macro?.confidence) ??
              0,
          ),
    coverage: score === null ? 0 : 100,
    source: "vix-level",
    sourceTimestamp: snapshot?.timestamp ?? null,
  };
}

function momentumReport(input = {}) {
  const supplied = input.momentum ?? input.technical?.momentum;

  if (supplied !== null && supplied !== undefined) {
    return asReport(supplied, { source: "momentum-input" });
  }

  const score = finiteOrNull(input.technical?.momentumScore);

  if (score !== null) {
    return asReport(
      {
        score,
        confidence: input.technical?.confidence,
        coverage: input.technical?.coverage,
        timestamp: input.technical?.timestamp,
      },
      { source: "technical-momentum" },
    );
  }

  const changePercent = finiteOrNull(
    input.technical?.changePercent ?? input.quote?.changePercent,
  );

  return {
    score: scoreDirectionalChange(changePercent, { scale: 5 }),
    confidence:
      changePercent === null
        ? 0
        : clamp(
            finiteOrNull(
              input.technical?.confidence ?? input.quote?.confidence,
            ) ?? 70,
          ),
    coverage: changePercent === null ? 0 : 100,
    source: "directional-change",
    sourceTimestamp:
      input.technical?.timestamp ?? input.quote?.timestamp ?? null,
  };
}

function invertedReport(report) {
  return {
    ...report,
    score: report.score === null ? null : 100 - report.score,
  };
}

function validatePointInTime(details, timestamp) {
  const asOf = Date.parse(timestamp);

  for (const [key, detail] of Object.entries(details)) {
    if (!detail.sourceTimestamp) continue;

    const sourceTime = Date.parse(detail.sourceTimestamp);

    if (Number.isFinite(sourceTime) && sourceTime > asOf) {
      throw new RangeError(
        `${key} source timestamp is later than the feature snapshot.`,
      );
    }
  }
}

function compositeAiReport(details, weights = COMPOSITE_AI_WEIGHTS) {
  return calculateWeightedScore(
    Object.entries(COMPOSITE_AI_WEIGHTS).map(([key, fallbackWeight]) => ({
      key,
      report: key === "volatility" ? invertedReport(details[key]) : details[key],
      weight: Math.max(0, finiteOrNull(weights?.[key]) ?? fallbackWeight),
    })),
  );
}

export function composePredictionFeatures(
  input = {},
  { now = Date.now, weights = COMPOSITE_AI_WEIGHTS, timestamp = null } = {},
) {
  if (typeof now !== "function") {
    throw new TypeError("Prediction feature clock must be a function.");
  }

  const timestampDate = new Date(timestamp ?? now());

  if (Number.isNaN(timestampDate.getTime())) {
    throw new TypeError("Prediction feature timestamp is invalid.");
  }
  const resolvedTimestamp = timestampDate.toISOString();

  const snapshot = input.marketSnapshot ?? input.snapshot ?? null;
  const details = {
    marketScore: marketScoreReport(snapshot, input.compositeMarket),
    breadth: asReport(input.breadth, {
      source: "market-breadth",
      sourceTimestamp: input.breadth?.timestamp ?? null,
    }),
    liquidity: asReport(input.liquidity, {
      source: "liquidity-engine",
      sourceTimestamp: input.liquidity?.timestamp ?? null,
    }),
    volatility: volatilityReport(input.volatility, snapshot),
    macro: asReport(snapshot?.macro ?? input.macro, {
      source: "macro-engine",
      sourceTimestamp: snapshot?.timestamp ?? input.macro?.timestamp ?? null,
    }),
    newsScore: asReport(input.newsIntelligence ?? input.news, {
      source: "news-intelligence",
      sourceTimestamp:
        input.newsIntelligence?.timestamp ?? input.news?.timestamp ?? null,
    }),
    sectorStrength: asReport(input.sectorStrength, {
      source: "sector-strength-engine",
      sourceTimestamp: input.sectorStrength?.timestamp ?? null,
    }),
    momentum: momentumReport(input),
  };
  const fearGreed = calculateFearGreed({
    volatility: details.volatility,
    breadth: details.breadth,
    momentum: details.momentum,
    news: details.newsScore,
    market: details.marketScore,
  });
  details.fearGreed = {
    ...fearGreed,
    source: "fear-greed-engine",
    sourceTimestamp: resolvedTimestamp,
  };

  validatePointInTime(details, resolvedTimestamp);

  const compositeAI = compositeAiReport(details, weights);
  details.compositeAI = {
    ...compositeAI,
    source: "composite-ai-v1",
    sourceTimestamp: resolvedTimestamp,
  };

  return createPredictionFeatureSet({
    details,
    confidence: compositeAI.confidence,
    coverage: compositeAI.coverage,
    timestamp: resolvedTimestamp,
  });
}

export class PredictionFeatureComposer {
  constructor({ now = Date.now, weights = COMPOSITE_AI_WEIGHTS } = {}) {
    if (typeof now !== "function") {
      throw new TypeError("Prediction feature clock must be a function.");
    }

    this.now = now;
    this.weights = Object.freeze({
      ...COMPOSITE_AI_WEIGHTS,
      ...(weights || {}),
    });
  }

  compose(input = {}, options = {}) {
    return composePredictionFeatures(input, {
      ...options,
      now: this.now,
      weights: this.weights,
    });
  }
}

export const predictionFeatureComposer = new PredictionFeatureComposer();

export const PredictionFeatureComposerInternals = Object.freeze({
  asReport,
  marketScoreReport,
  volatilityReport,
  momentumReport,
  validatePointInTime,
  compositeAiReport,
});

export default composePredictionFeatures;
