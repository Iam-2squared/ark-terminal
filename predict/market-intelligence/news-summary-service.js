import {
  clampNewsValue,
  isUsableNewsItem,
} from "./news-data-model.js";

export const NEWS_SUMMARY_METHODS = Object.freeze({
  AI: "ai",
  SOURCE: "source",
  EXTRACTIVE: "extractive",
  TITLE: "title",
  UNAVAILABLE: "unavailable",
});

function normalizeMaximumLength(value) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.max(80, Math.round(number)) : 240;
}

function compactWhitespace(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function truncate(value, maximumLength) {
  const text = compactWhitespace(value);

  if (text.length <= maximumLength) {
    return text;
  }

  return `${text.slice(0, Math.max(1, maximumLength - 1)).trimEnd()}…`;
}

function extractSentences(value, maximumLength) {
  const text = compactWhitespace(value);

  if (!text) return "";

  const sentences = text.match(/[^。！？.!?]+[。！？.!?]?/g) || [text];
  const selected = sentences.slice(0, 2).join(" ");
  return truncate(selected, maximumLength);
}

function fallbackSummary(item, maximumLength, fallbackReason = null) {
  if (item.summary) {
    return {
      text: truncate(item.summary, maximumLength),
      method: NEWS_SUMMARY_METHODS.SOURCE,
      confidence: Math.round(clampNewsValue(item.confidence)),
      fallbackReason,
    };
  }

  if (item.body) {
    return {
      text: extractSentences(item.body, maximumLength),
      method: NEWS_SUMMARY_METHODS.EXTRACTIVE,
      confidence: Math.round(clampNewsValue(item.confidence * 0.75)),
      fallbackReason,
    };
  }

  if (item.title) {
    return {
      text: truncate(item.title, maximumLength),
      method: NEWS_SUMMARY_METHODS.TITLE,
      confidence: Math.round(clampNewsValue(item.confidence * 0.6)),
      fallbackReason,
    };
  }

  return {
    text: null,
    method: NEWS_SUMMARY_METHODS.UNAVAILABLE,
    confidence: 0,
    fallbackReason,
  };
}

function normalizeAiResult(result, maximumLength, itemConfidence) {
  const text = compactWhitespace(
    typeof result === "string" ? result : result?.text ?? result?.summary,
  );

  if (!text) return null;

  return {
    text: truncate(text, maximumLength),
    method: NEWS_SUMMARY_METHODS.AI,
    confidence: Math.round(
      clampNewsValue(result?.confidence ?? itemConfidence),
    ),
    fallbackReason: null,
  };
}

export class NewsSummaryService {
  constructor({ summarizer = null, maximumLength = 240 } = {}) {
    if (summarizer !== null && typeof summarizer !== "function") {
      throw new TypeError("News summarizer must be a function or null.");
    }

    this.summarizer = summarizer;
    this.maximumLength = normalizeMaximumLength(maximumLength);
  }

  async summarize(item = {}) {
    if (!isUsableNewsItem(item)) {
      return fallbackSummary(item, this.maximumLength);
    }

    if (!this.summarizer) {
      return fallbackSummary(item, this.maximumLength);
    }

    try {
      const result = await this.summarizer({
        id: item.id,
        type: item.type,
        symbol: item.symbol,
        title: item.title,
        summary: item.summary,
        body: item.body,
        language: item.language,
      });
      const normalized = normalizeAiResult(
        result,
        this.maximumLength,
        item.confidence,
      );

      return (
        normalized ||
        fallbackSummary(item, this.maximumLength, "empty_ai_summary")
      );
    } catch {
      return fallbackSummary(item, this.maximumLength, "ai_summary_error");
    }
  }

  summarizeAll(items = []) {
    return Promise.all(
      (Array.isArray(items) ? items : []).map((item) => this.summarize(item)),
    );
  }
}

export const newsSummaryService = new NewsSummaryService();

export const NewsSummaryServiceInternals = Object.freeze({
  compactWhitespace,
  extractSentences,
  truncate,
});

export default NewsSummaryService;
