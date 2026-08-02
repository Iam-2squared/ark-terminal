import {
  NEWS_ITEM_STATUS,
  NEWS_METRIC_DIRECTIONS,
  NEWS_SOURCE_TYPES,
  clampNewsValue,
  createNewsItem,
  newsFiniteOrNull,
  normalizeNewsTimestamp,
} from "./news-data-model.js";

const TYPE_ALIASES = Object.freeze({
  news: NEWS_SOURCE_TYPES.NEWS,
  article: NEWS_SOURCE_TYPES.NEWS,
  ir: NEWS_SOURCE_TYPES.IR,
  pressrelease: NEWS_SOURCE_TYPES.IR,
  disclosure: NEWS_SOURCE_TYPES.TDNET,
  timelydisclosure: NEWS_SOURCE_TYPES.TDNET,
  tdnet: NEWS_SOURCE_TYPES.TDNET,
  earnings: NEWS_SOURCE_TYPES.EARNINGS,
  financialresults: NEWS_SOURCE_TYPES.EARNINGS,
  results: NEWS_SOURCE_TYPES.EARNINGS,
});

const DIRECTION_ALIASES = Object.freeze({
  higherisbetter: NEWS_METRIC_DIRECTIONS.HIGHER_IS_BETTER,
  higher: NEWS_METRIC_DIRECTIONS.HIGHER_IS_BETTER,
  positive: NEWS_METRIC_DIRECTIONS.HIGHER_IS_BETTER,
  lowerisbetter: NEWS_METRIC_DIRECTIONS.LOWER_IS_BETTER,
  lower: NEWS_METRIC_DIRECTIONS.LOWER_IS_BETTER,
  negative: NEWS_METRIC_DIRECTIONS.LOWER_IS_BETTER,
  neutral: NEWS_METRIC_DIRECTIONS.NEUTRAL,
});

const DEFAULT_IMPORTANCE = Object.freeze({
  [NEWS_SOURCE_TYPES.NEWS]: 55,
  [NEWS_SOURCE_TYPES.IR]: 70,
  [NEWS_SOURCE_TYPES.TDNET]: 80,
  [NEWS_SOURCE_TYPES.EARNINGS]: 90,
});

function lookupKey(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function limitedText(value, maximum) {
  return String(value ?? "").trim().slice(0, maximum);
}

function resolveType(value, fallback = NEWS_SOURCE_TYPES.NEWS) {
  if (Object.values(NEWS_SOURCE_TYPES).includes(value)) {
    return value;
  }

  return TYPE_ALIASES[lookupKey(value)] || fallback;
}

function resolveMetricDirection(value) {
  if (Object.values(NEWS_METRIC_DIRECTIONS).includes(value)) {
    return value;
  }

  return (
    DIRECTION_ALIASES[lookupKey(value)] ||
    NEWS_METRIC_DIRECTIONS.HIGHER_IS_BETTER
  );
}

function normalizeMetric(metric = {}, index = 0) {
  return {
    name: limitedText(
      metric.name ?? metric.metric ?? metric.label ?? `metric-${index + 1}`,
      120,
    ),
    actual: newsFiniteOrNull(metric.actual ?? metric.value),
    consensus: newsFiniteOrNull(
      metric.consensus ?? metric.estimate ?? metric.expected,
    ),
    previous: newsFiniteOrNull(metric.previous ?? metric.prior),
    direction: resolveMetricDirection(
      metric.direction ?? metric.metricDirection ?? metric.polarity,
    ),
    unit: limitedText(metric.unit, 32) || null,
  };
}

function extractMetrics(raw) {
  if (Array.isArray(raw?.metrics)) {
    return raw.metrics.map(normalizeMetric);
  }

  const actual = raw?.actual ?? raw?.value;
  const consensus = raw?.consensus ?? raw?.estimate ?? raw?.expected;
  const previous = raw?.previous ?? raw?.prior;

  if (
    newsFiniteOrNull(actual) === null &&
    newsFiniteOrNull(consensus) === null &&
    newsFiniteOrNull(previous) === null
  ) {
    return [];
  }

  return [
    normalizeMetric({
      name: raw.metricName ?? raw.metric ?? "reported-result",
      actual,
      consensus,
      previous,
      direction: raw.metricDirection ?? raw.direction,
      unit: raw.unit,
    }),
  ];
}

function sourceName(raw) {
  const source = raw?.source ?? raw?.provider ?? raw?.publisher;

  if (source && typeof source === "object") {
    return limitedText(source.name ?? source.label ?? source.id, 200);
  }

  return limitedText(source, 200);
}

function inferLanguage(text) {
  if (!text) return null;
  return /[\u3040-\u30ff\u3400-\u9fff]/.test(text) ? "ja" : "en";
}

function hashText(value) {
  let hash = 0x811c9dc5;

  for (const character of String(value)) {
    hash ^= character.codePointAt(0);
    hash = Math.imul(hash, 0x01000193);
  }

  return (hash >>> 0).toString(36);
}

function deterministicId({ type, symbol, title, publishedAt, url }) {
  const identity = [type, symbol, title, publishedAt, url]
    .map((value) => String(value || "").trim().toLowerCase())
    .join("|");
  return `news-${hashText(identity)}`;
}

function resolveStatus(raw, { hasText, publishedAt, source }) {
  const rawStatus = String(raw?.status || "").toLowerCase();

  if (rawStatus === NEWS_ITEM_STATUS.ERROR) {
    return NEWS_ITEM_STATUS.ERROR;
  }

  if (!hasText || rawStatus === NEWS_ITEM_STATUS.UNAVAILABLE) {
    return NEWS_ITEM_STATUS.UNAVAILABLE;
  }

  if (
    rawStatus === NEWS_ITEM_STATUS.PARTIAL ||
    !publishedAt ||
    !source
  ) {
    return NEWS_ITEM_STATUS.PARTIAL;
  }

  return NEWS_ITEM_STATUS.AVAILABLE;
}

function resolveConfidence(raw, { hasText, publishedAt, source, status }) {
  if (
    !hasText ||
    status === NEWS_ITEM_STATUS.ERROR ||
    status === NEWS_ITEM_STATUS.UNAVAILABLE
  ) {
    return 0;
  }

  let confidence = newsFiniteOrNull(raw?.confidence) ?? 75;

  if (!publishedAt) confidence -= 20;
  if (!source) confidence -= 10;
  if (!raw?.summary && !raw?.description && !raw?.body && !raw?.content) {
    confidence -= 5;
  }

  return Math.round(clampNewsValue(confidence));
}

export function normalizeNewsItem(
  raw = {},
  { type: forcedType = null } = {},
) {
  const type = resolveType(
    forcedType ?? raw.type ?? raw.sourceType ?? raw.category,
  );
  const title = limitedText(raw.title ?? raw.headline ?? raw.name, 500);
  const summary = limitedText(
    raw.summary ?? raw.description ?? raw.abstract,
    2_000,
  );
  const body = limitedText(raw.body ?? raw.content ?? raw.text, 20_000);
  const publishedAt = normalizeNewsTimestamp(
    raw.publishedAt ??
      raw.published_at ??
      raw.pubDate ??
      raw.date ??
      raw.timestamp,
  );
  const source = sourceName(raw);
  const symbol = limitedText(raw.symbol ?? raw.ticker ?? raw.code, 64) || null;
  const url = limitedText(raw.url ?? raw.link, 2_000) || null;
  const hasText = Boolean(title || summary || body);
  const status = resolveStatus(raw, {
    hasText,
    publishedAt,
    source,
  });
  const confidence = resolveConfidence(raw, {
    hasText,
    publishedAt,
    source,
    status,
  });
  const id =
    limitedText(raw.id ?? raw.guid, 300) ||
    deterministicId({ type, symbol, title, publishedAt, url });
  const language =
    limitedText(raw.language ?? raw.lang, 16) ||
    inferLanguage(`${title} ${summary} ${body}`);

  return createNewsItem({
    id,
    type,
    symbol,
    title,
    summary,
    body,
    publishedAt,
    source: source || "unknown",
    url,
    language,
    importance:
      newsFiniteOrNull(raw.importance ?? raw.relevance) ??
      DEFAULT_IMPORTANCE[type],
    confidence,
    status,
    metrics: extractMetrics(raw),
    tags: raw.tags ?? raw.labels ?? [],
  });
}

function collectRawItems(input) {
  if (Array.isArray(input)) {
    return input.map((item) => ({ item, type: null }));
  }

  if (!input || typeof input !== "object") {
    return [];
  }

  if (input.title || input.headline || input.body || input.content) {
    return [{ item: input, type: null }];
  }

  const groups = [
    [input.items, null],
    [input.news, NEWS_SOURCE_TYPES.NEWS],
    [input.ir, NEWS_SOURCE_TYPES.IR],
    [input.disclosures, NEWS_SOURCE_TYPES.TDNET],
    [input.tdnet, NEWS_SOURCE_TYPES.TDNET],
    [input.earnings, NEWS_SOURCE_TYPES.EARNINGS],
    [input.results, NEWS_SOURCE_TYPES.EARNINGS],
  ];

  return groups.flatMap(([items, type]) =>
    (Array.isArray(items) ? items : []).map((item) => ({ item, type })),
  );
}

function preferredItem(first, second) {
  if (second.confidence !== first.confidence) {
    return second.confidence > first.confidence ? second : first;
  }

  const firstTime = Date.parse(first.publishedAt || 0) || 0;
  const secondTime = Date.parse(second.publishedAt || 0) || 0;
  return secondTime > firstTime ? second : first;
}

export function normalizeNewsCollection(input = []) {
  const indexed = new Map();

  for (const { item, type } of collectRawItems(input)) {
    const normalized = normalizeNewsItem(item, { type });
    const key = normalized.url || normalized.id;
    const existing = indexed.get(key);
    indexed.set(key, existing ? preferredItem(existing, normalized) : normalized);
  }

  return [...indexed.values()].sort((first, second) => {
    const timeDifference =
      (Date.parse(second.publishedAt || 0) || 0) -
      (Date.parse(first.publishedAt || 0) || 0);
    return timeDifference || first.id.localeCompare(second.id);
  });
}

export const NewsDataNormalizerInternals = Object.freeze({
  deterministicId,
  hashText,
  resolveType,
  resolveMetricDirection,
  collectRawItems,
});

export default normalizeNewsCollection;
