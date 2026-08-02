import { normalizeNewsCollection } from "./news-data-normalizer.js";
import { isUsableNewsItem } from "./news-data-model.js";
import { newsEventClassifier } from "./news-event-classifier.js";
import { newsRiskEngine } from "./news-risk-engine.js";
import { NewsScoreEngine } from "./news-score.js";
import { newsSentimentEngine } from "./news-sentiment-engine.js";
import { newsSummaryService } from "./news-summary-service.js";
import { newsSurpriseEngine } from "./news-surprise-engine.js";

function isoTimestamp(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    throw new TypeError("News Intelligence timestamp is invalid.");
  }

  return date.toISOString();
}

function riskSeverity(score) {
  if (score === null) return "UNKNOWN";
  if (score >= 75) return "HIGH";
  if (score >= 45) return "MEDIUM";
  if (score > 0) return "LOW";
  return "NONE";
}

function aggregateRisk(items) {
  const available = items.filter((item) => Number.isFinite(item.risk?.score));

  if (!available.length) {
    return {
      score: null,
      confidence: 0,
      severity: "UNKNOWN",
      eventCount: 0,
    };
  }

  const highest = available.reduce((first, second) =>
    second.risk.score > first.risk.score ? second : first,
  );
  const weightTotal = available.reduce(
    (total, item) => total + Math.max(1, Number(item.importance) || 1),
    0,
  );
  const weightedAverage = available.reduce(
    (total, item) =>
      total +
      item.risk.score * Math.max(1, Number(item.importance) || 1),
    0,
  ) / weightTotal;
  const score = Math.round((highest.risk.score * 0.65 + weightedAverage * 0.35) * 100) / 100;

  return {
    score,
    confidence: highest.risk.confidence,
    severity: riskSeverity(score),
    eventCount: available.filter((item) => item.risk.score > 0).length,
  };
}

function countEvents(items) {
  return Object.fromEntries(
    [...new Set(items.map((item) => item.event.category))]
      .sort()
      .map((category) => [
        category,
        items.filter((item) => item.event.category === category).length,
      ]),
  );
}

function reportStatus(items, score) {
  const usableCount = items.filter(isUsableNewsItem).length;

  if (!usableCount || score.score === null) return "unavailable";
  if (usableCount < items.length || score.coverage < 70) return "partial";
  return "ready";
}

function requireMethod(value, method, label) {
  if (!value || typeof value[method] !== "function") {
    throw new TypeError(`News Intelligence ${label} is invalid.`);
  }
}

export class NewsIntelligenceEngine {
  constructor({
    normalizer = normalizeNewsCollection,
    sentimentEngine = newsSentimentEngine,
    eventClassifier = newsEventClassifier,
    surpriseEngine = newsSurpriseEngine,
    riskEngine = newsRiskEngine,
    summaryService = newsSummaryService,
    scoreEngine = null,
    now = Date.now,
  } = {}) {
    if (typeof normalizer !== "function") {
      throw new TypeError("News Intelligence normalizer must be a function.");
    }

    if (typeof now !== "function") {
      throw new TypeError("News Intelligence clock must be a function.");
    }

    const resolvedScoreEngine = scoreEngine || new NewsScoreEngine({ now });

    requireMethod(sentimentEngine, "analyzeItem", "sentiment engine");
    requireMethod(eventClassifier, "classify", "event classifier");
    requireMethod(surpriseEngine, "detect", "surprise engine");
    requireMethod(riskEngine, "detect", "risk engine");
    requireMethod(summaryService, "summarizeAll", "summary service");
    requireMethod(resolvedScoreEngine, "calculateItem", "score engine");
    requireMethod(resolvedScoreEngine, "calculate", "score engine");

    this.normalizer = normalizer;
    this.sentimentEngine = sentimentEngine;
    this.eventClassifier = eventClassifier;
    this.surpriseEngine = surpriseEngine;
    this.riskEngine = riskEngine;
    this.summaryService = summaryService;
    this.scoreEngine = resolvedScoreEngine;
    this.now = now;
  }

  async analyze(input = [], { timestamp = null } = {}) {
    const normalized = this.normalizer(input);
    const summaries = await this.summaryService.summarizeAll(normalized);
    const items = normalized.map((item, index) => {
      const sentiment = this.sentimentEngine.analyzeItem(item);
      const event = this.eventClassifier.classify(item);
      const surprise = this.surpriseEngine.detect(item);
      const risk = this.riskEngine.detect(item);
      const scoreReport = this.scoreEngine.calculateItem({
        sentiment,
        surprise,
        risk,
      });

      return {
        ...item,
        generatedSummary: summaries[index],
        sentiment,
        event,
        surprise,
        risk,
        score: scoreReport.score,
        scoreReport,
      };
    });
    const score = this.scoreEngine.calculate(items);
    const resolvedTimestamp = isoTimestamp(timestamp ?? this.now());
    const topEvents = items
      .filter((item) => item.event.available)
      .sort(
        (first, second) =>
          second.importance * second.event.confidence -
          first.importance * first.event.confidence,
      )
      .slice(0, 10)
      .map((item) => ({
        id: item.id,
        symbol: item.symbol,
        type: item.type,
        category: item.event.category,
        importance: item.importance,
        score: item.score,
        publishedAt: item.publishedAt,
      }));

    return {
      score: score.score,
      confidence: score.confidence,
      coverage: score.coverage,
      sentiment: score.sentiment,
      risk: aggregateRisk(items),
      eventCounts: countEvents(items),
      topEvents,
      timestamp: resolvedTimestamp,
      status: reportStatus(items, score),
      sourceCount: new Set(items.map((item) => item.source)).size,
      items,
    };
  }
}

export const newsIntelligenceEngine = new NewsIntelligenceEngine();

export default NewsIntelligenceEngine;
