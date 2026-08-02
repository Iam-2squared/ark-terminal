export const NEWS_SOURCE_TYPES = Object.freeze({
  NEWS: "news",
  IR: "ir",
  TDNET: "tdnet",
  EARNINGS: "earnings",
});

export const NEWS_ITEM_STATUS = Object.freeze({
  AVAILABLE: "available",
  PARTIAL: "partial",
  UNAVAILABLE: "unavailable",
  ERROR: "error",
});

export const NEWS_METRIC_DIRECTIONS = Object.freeze({
  HIGHER_IS_BETTER: "higher_is_better",
  LOWER_IS_BETTER: "lower_is_better",
  NEUTRAL: "neutral",
});

const VALID_SOURCE_TYPES = new Set(Object.values(NEWS_SOURCE_TYPES));
const VALID_STATUSES = new Set(Object.values(NEWS_ITEM_STATUS));
const VALID_METRIC_DIRECTIONS = new Set(
  Object.values(NEWS_METRIC_DIRECTIONS),
);

export function newsFiniteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function clampNewsValue(value, minimum = 0, maximum = 100) {
  const number = newsFiniteOrNull(value) ?? minimum;
  return Math.min(maximum, Math.max(minimum, number));
}

export function normalizeNewsTimestamp(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const numeric =
    typeof value === "number" || /^\d+(?:\.\d+)?$/.test(String(value))
      ? Number(value)
      : null;
  const date = new Date(
    numeric !== null && numeric < 1_000_000_000_000
      ? numeric * 1000
      : value,
  );

  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function freezeMetric(metric = {}) {
  const direction = VALID_METRIC_DIRECTIONS.has(metric.direction)
    ? metric.direction
    : NEWS_METRIC_DIRECTIONS.NEUTRAL;

  return Object.freeze({
    name: String(metric.name || "metric"),
    actual: newsFiniteOrNull(metric.actual),
    consensus: newsFiniteOrNull(metric.consensus),
    previous: newsFiniteOrNull(metric.previous),
    direction,
    unit: metric.unit ? String(metric.unit) : null,
  });
}

export function createNewsItem({
  id,
  type = NEWS_SOURCE_TYPES.NEWS,
  symbol = null,
  title = "",
  summary = "",
  body = "",
  publishedAt = null,
  source = "unknown",
  url = null,
  language = null,
  importance = 50,
  confidence = 0,
  status = NEWS_ITEM_STATUS.PARTIAL,
  metrics = [],
  tags = [],
} = {}) {
  if (!String(id || "").trim()) {
    throw new TypeError("News item id is required.");
  }

  if (!VALID_SOURCE_TYPES.has(type)) {
    throw new RangeError(`Unknown news source type: ${String(type)}`);
  }

  if (!VALID_STATUSES.has(status)) {
    throw new RangeError(`Unknown news item status: ${String(status)}`);
  }

  const normalizedMetrics = Object.freeze(
    (Array.isArray(metrics) ? metrics : []).map(freezeMetric),
  );
  const normalizedTags = Object.freeze(
    [...new Set((Array.isArray(tags) ? tags : []).map(String).filter(Boolean))],
  );

  return Object.freeze({
    id: String(id),
    type,
    symbol: symbol ? String(symbol) : null,
    title: String(title || ""),
    summary: String(summary || ""),
    body: String(body || ""),
    publishedAt: normalizeNewsTimestamp(publishedAt),
    source: String(source || "unknown"),
    url: url ? String(url) : null,
    language: language ? String(language) : null,
    importance: Math.round(clampNewsValue(importance)),
    confidence: Math.round(clampNewsValue(confidence)),
    status,
    metrics: normalizedMetrics,
    tags: normalizedTags,
  });
}

export function isUsableNewsItem(item) {
  return Boolean(
    item &&
      (item.status === NEWS_ITEM_STATUS.AVAILABLE ||
        item.status === NEWS_ITEM_STATUS.PARTIAL) &&
      (item.title || item.summary || item.body) &&
      item.confidence > 0,
  );
}

export default createNewsItem;
