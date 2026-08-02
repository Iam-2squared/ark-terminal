import {
  calculateWeightedScore,
  scoreToSentiment,
} from "./market-score.js";

export const NEWS_ITEM_SCORE_WEIGHTS = Object.freeze({
  sentiment: 45,
  surprise: 35,
  risk: 20,
});

export const DEFAULT_NEWS_HALF_LIFE_HOURS = 72;

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

function normalizeWeights(weights = {}) {
  return Object.freeze(
    Object.fromEntries(
      Object.entries(NEWS_ITEM_SCORE_WEIGHTS).map(([key, fallback]) => [
        key,
        Math.max(0, finiteOrNull(weights?.[key]) ?? fallback),
      ]),
    ),
  );
}

function riskSupportReport(risk = {}) {
  const riskScore = finiteOrNull(risk?.score);

  return {
    score: riskScore === null ? null : 100 - clamp(riskScore),
    confidence: finiteOrNull(risk?.confidence) ?? 0,
    coverage: finiteOrNull(risk?.coverage) ?? 0,
  };
}

export function calculateNewsItemScore({
  sentiment,
  surprise,
  risk,
  weights = NEWS_ITEM_SCORE_WEIGHTS,
} = {}) {
  const normalizedWeights = normalizeWeights(weights);
  const aggregate = calculateWeightedScore([
    {
      key: "sentiment",
      report: sentiment,
      weight: normalizedWeights.sentiment,
    },
    {
      key: "surprise",
      report: surprise,
      weight: normalizedWeights.surprise,
    },
    {
      key: "risk",
      report: riskSupportReport(risk),
      weight: normalizedWeights.risk,
    },
  ]);

  return {
    ...aggregate,
    sentiment: scoreToSentiment(aggregate.score),
  };
}

export function calculateNewsRecencyWeight(
  publishedAt,
  { now = Date.now, halfLifeHours = DEFAULT_NEWS_HALF_LIFE_HOURS } = {},
) {
  if (typeof now !== "function") {
    throw new TypeError("News score clock must be a function.");
  }

  const timestamp = Date.parse(publishedAt);

  if (!Number.isFinite(timestamp)) {
    return 0.5;
  }

  const ageHours = Math.max(0, (Number(now()) - timestamp) / 3_600_000);
  const halfLife = Math.max(1, Number(halfLifeHours) || 1);
  return Math.max(0.05, 2 ** (-ageHours / halfLife));
}

export function calculateNewsScore(
  items = [],
  {
    now = Date.now,
    halfLifeHours = DEFAULT_NEWS_HALF_LIFE_HOURS,
  } = {},
) {
  if (typeof now !== "function") {
    throw new TypeError("News score clock must be a function.");
  }

  const prepared = (Array.isArray(items) ? items : []).map((item) => {
    const recencyWeight = calculateNewsRecencyWeight(item.publishedAt, {
      now,
      halfLifeHours,
    });
    const importanceWeight = Math.max(
      1,
      finiteOrNull(item.importance) ?? 50,
    );
    const scoreReport =
      item.scoreReport ||
      calculateNewsItemScore({
        sentiment: item.sentiment,
        surprise: item.surprise,
        risk: item.risk,
      });

    return {
      id: item.id,
      scoreReport,
      recencyWeight,
      weight: importanceWeight * recencyWeight,
    };
  });
  const aggregate = calculateWeightedScore(
    prepared.map((item) => ({
      key: item.id,
      report: item.scoreReport,
      weight: item.weight,
    })),
  );

  return {
    score: aggregate.score,
    confidence: aggregate.confidence,
    coverage: aggregate.coverage,
    sentiment: scoreToSentiment(aggregate.score),
    analyzedCount: prepared.filter(
      (item) => finiteOrNull(item.scoreReport?.score) !== null,
    ).length,
    requestedCount: prepared.length,
    items: prepared.map((item) => ({
      id: item.id,
      score: item.scoreReport.score,
      confidence: item.scoreReport.confidence,
      recencyWeight:
        Math.round(item.recencyWeight * 10_000) / 10_000,
    })),
    components: aggregate.components,
  };
}

export class NewsScoreEngine {
  constructor({
    now = Date.now,
    halfLifeHours = DEFAULT_NEWS_HALF_LIFE_HOURS,
  } = {}) {
    if (typeof now !== "function") {
      throw new TypeError("News score clock must be a function.");
    }

    this.now = now;
    this.halfLifeHours = Math.max(1, Number(halfLifeHours) || 1);
  }

  calculateItem(input = {}) {
    return calculateNewsItemScore(input);
  }

  calculate(items = []) {
    return calculateNewsScore(items, {
      now: this.now,
      halfLifeHours: this.halfLifeHours,
    });
  }
}

export const newsScoreEngine = new NewsScoreEngine();

export default calculateNewsScore;
