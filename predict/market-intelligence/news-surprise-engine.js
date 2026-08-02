import {
  NEWS_METRIC_DIRECTIONS,
  clampNewsValue,
  isUsableNewsItem,
  newsFiniteOrNull,
} from "./news-data-model.js";
import { calculateWeightedScore } from "./market-score.js";

const POSITIVE_SURPRISE_TERMS = Object.freeze([
  "beat expectations",
  "above expectations",
  "better than expected",
  "予想を上回",
  "市場予想超",
  "上振れ",
]);

const NEGATIVE_SURPRISE_TERMS = Object.freeze([
  "miss expectations",
  "below expectations",
  "worse than expected",
  "予想を下回",
  "市場予想未達",
  "下振れ",
]);

function round(value, digits = 2) {
  const factor = 10 ** digits;
  return Math.round(Number(value) * factor) / factor;
}

function labelFromScore(score) {
  if (score === null) return "UNKNOWN";
  if (score >= 57.5) return "POSITIVE";
  if (score <= 42.5) return "NEGATIVE";
  return "IN_LINE";
}

function metricSurprise(metric, confidence) {
  const actual = newsFiniteOrNull(metric?.actual);
  const consensus = newsFiniteOrNull(metric?.consensus);
  const previous = newsFiniteOrNull(metric?.previous);

  if (actual === null || consensus === null) {
    return null;
  }

  const denominator = Math.max(
    Math.abs(consensus),
    Math.abs(previous ?? 0),
    Math.abs(actual) * 0.1,
    1e-6,
  );
  const rawPercent = ((actual - consensus) / denominator) * 100;
  const directionalPercent =
    metric.direction === NEWS_METRIC_DIRECTIONS.LOWER_IS_BETTER
      ? -rawPercent
      : metric.direction === NEWS_METRIC_DIRECTIONS.HIGHER_IS_BETTER
        ? rawPercent
        : null;
  const score =
    directionalPercent === null
      ? null
      : clampNewsValue(50 + Math.max(-20, Math.min(20, directionalPercent)) * 2.5);

  return {
    name: metric.name,
    actual,
    consensus,
    previous,
    direction: metric.direction,
    surprisePercent: round(rawPercent),
    directionalSurprisePercent:
      directionalPercent === null ? null : round(directionalPercent),
    score: score === null ? null : round(score),
    confidence: score === null ? 0 : Math.round(confidence),
    coverage: 100,
    label: labelFromScore(score),
  };
}

function textualSurprise(item) {
  const text = [item?.title, item?.summary, item?.body]
    .map((value) => String(value || "").toLowerCase())
    .filter(Boolean)
    .join(" ");
  const positive = POSITIVE_SURPRISE_TERMS.filter((term) =>
    text.includes(term),
  );
  const negative = NEGATIVE_SURPRISE_TERMS.filter((term) =>
    text.includes(term),
  );

  if (!positive.length && !negative.length) {
    return null;
  }

  const direction = Math.sign(positive.length - negative.length);
  const score = direction > 0 ? 70 : direction < 0 ? 30 : 50;

  return {
    score,
    confidence: Math.round(clampNewsValue(item.confidence * 0.45)),
    coverage: 100,
    label: labelFromScore(score),
    method: "text-signal-v1",
    metrics: [],
    matchedSignals: [...positive, ...negative],
  };
}

export function detectNewsSurprise(item = {}) {
  if (!isUsableNewsItem(item)) {
    return {
      score: null,
      confidence: 0,
      coverage: 0,
      label: "UNKNOWN",
      method: "unavailable",
      metrics: [],
      matchedSignals: [],
    };
  }

  const metrics = (Array.isArray(item.metrics) ? item.metrics : [])
    .map((metric) => metricSurprise(metric, item.confidence))
    .filter(Boolean);
  const scoreable = metrics.filter((metric) => metric.score !== null);

  if (!scoreable.length) {
    return (
      textualSurprise(item) || {
        score: null,
        confidence: 0,
        coverage: metrics.length ? 100 : 0,
        label: "UNKNOWN",
        method: metrics.length ? "numeric-unclassified" : "no-signal",
        metrics,
        matchedSignals: [],
      }
    );
  }

  const aggregate = calculateWeightedScore(
    scoreable.map((metric) => ({
      key: metric.name,
      report: metric,
      weight: 1,
    })),
  );

  return {
    score: aggregate.score,
    confidence: aggregate.confidence,
    coverage:
      metrics.length > 0 ? round((scoreable.length / metrics.length) * 100) : 0,
    label: labelFromScore(aggregate.score),
    method: "actual-vs-consensus-v1",
    metrics,
    matchedSignals: [],
  };
}

export class NewsSurpriseEngine {
  detect(item = {}) {
    return detectNewsSurprise(item);
  }
}

export const newsSurpriseEngine = new NewsSurpriseEngine();

export default detectNewsSurprise;
