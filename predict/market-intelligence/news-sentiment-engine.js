import { analyzeTextSentiment } from "../analysis/context-scoring.js";
import { calculateWeightedScore } from "./market-score.js";
import {
  clampNewsValue,
  isUsableNewsItem,
} from "./news-data-model.js";

function round(value, digits = 2) {
  const factor = 10 ** digits;
  return Math.round(Number(value) * factor) / factor;
}

function itemText(item) {
  return [item?.title, item?.summary, item?.body]
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .join(" ");
}

function sentimentLabel(score) {
  if (score === null) return "UNKNOWN";
  if (score >= 60) return "POSITIVE";
  if (score <= 40) return "NEGATIVE";
  return "NEUTRAL";
}

export function analyzeNewsItemSentiment(item = {}) {
  const text = itemText(item);

  if (!isUsableNewsItem(item) || !text) {
    return {
      score: null,
      confidence: 0,
      coverage: 0,
      label: "UNKNOWN",
      positiveSignals: 0,
      negativeSignals: 0,
      method: "existing-context-lexicon-v1",
    };
  }

  const result = analyzeTextSentiment([{ headline: text }]);
  const signalCount = result.positive + result.negative;
  const evidenceFactor = signalCount
    ? Math.min(1, 0.5 + signalCount * 0.125)
    : 0.25;
  const confidence = clampNewsValue(item.confidence * evidenceFactor);

  return {
    score: round(result.score),
    confidence: round(confidence, 1),
    coverage: 100,
    label: sentimentLabel(result.score),
    positiveSignals: result.positive,
    negativeSignals: result.negative,
    method: "existing-context-lexicon-v1",
  };
}

export function analyzeNewsSentiment(items = []) {
  const reports = (Array.isArray(items) ? items : []).map((item) => ({
    id: item.id,
    importance: item.importance,
    report: analyzeNewsItemSentiment(item),
  }));
  const aggregate = calculateWeightedScore(
    reports.map(({ id, importance, report }) => ({
      key: id,
      report,
      weight: Math.max(1, Number(importance) || 1),
    })),
  );

  return {
    score: aggregate.score,
    confidence: aggregate.confidence,
    coverage: aggregate.coverage,
    label: sentimentLabel(aggregate.score),
    analyzedCount: reports.filter(({ report }) => report.score !== null).length,
    requestedCount: reports.length,
    items: reports.map(({ id, report }) => ({ id, ...report })),
  };
}

export class NewsSentimentEngine {
  analyzeItem(item = {}) {
    return analyzeNewsItemSentiment(item);
  }

  analyze(items = []) {
    return analyzeNewsSentiment(items);
  }
}

export const newsSentimentEngine = new NewsSentimentEngine();

export default analyzeNewsSentiment;
