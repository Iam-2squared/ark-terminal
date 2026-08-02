export const HISTORICAL_MARKET_REPORT_KEYS = Object.freeze([
  "marketSnapshot",
  "breadth",
  "liquidity",
  "sectorStrength",
  "sectorRotation",
  "compositeMarket",
  "newsIntelligence",
]);

export const HISTORICAL_MARKET_RETENTION_POLICY =
  "derived-records-with-source-reference-v1";

const POINT_IN_TIME_FIELDS = new Set([
  "timestamp",
  "sourceTimestamp",
  "publishedAt",
  "published_at",
]);

const OMITTED_NEWS_FIELDS = new Set([
  "article",
  "articleText",
  "body",
  "content",
  "fullText",
  "html",
  "raw",
  "rawContent",
]);

function isObject(value) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number(value)));
}

function timestampMilliseconds(value, label = "Historical snapshot timestamp") {
  const numeric =
    typeof value === "number" || /^\d+(?:\.\d+)?$/.test(String(value))
      ? Number(value)
      : null;
  const normalized =
    numeric !== null && numeric < 1_000_000_000_000
      ? numeric * 1000
      : value;
  const milliseconds = new Date(normalized).getTime();

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(`${label} is invalid.`);
  }

  return milliseconds;
}

function isoTimestamp(value, label = "Historical snapshot timestamp") {
  return new Date(timestampMilliseconds(value, label)).toISOString();
}

function normalizeSymbol(value) {
  const symbol = String(value ?? "").trim().toUpperCase();

  if (!symbol) {
    throw new TypeError("Historical snapshot symbol is required.");
  }

  return symbol;
}

function clonePlainData(value, seen = new WeakSet()) {
  if (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean"
  ) {
    return value;
  }

  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (value instanceof Date) {
    return isoTimestamp(value, "Historical snapshot Date");
  }

  if (typeof value !== "object") return undefined;

  if (seen.has(value)) {
    throw new TypeError("Historical snapshot data cannot contain cycles.");
  }

  seen.add(value);

  if (Array.isArray(value)) {
    const result = value
      .map((item) => clonePlainData(item, seen))
      .filter((item) => item !== undefined);
    seen.delete(value);
    return result;
  }

  if (value instanceof Map) {
    const result = Object.fromEntries(
      [...value.entries()]
        .map(([key, item]) => [String(key), clonePlainData(item, seen)])
        .filter(([, item]) => item !== undefined),
    );
    seen.delete(value);
    return result;
  }

  const result = {};

  for (const key of Object.keys(value)) {
    const item = clonePlainData(value[key], seen);
    if (item !== undefined) result[key] = item;
  }

  seen.delete(value);
  return result;
}

function runtimeReport(value) {
  return value?.version === "market-intelligence-runtime-v1"
    ? value
    : null;
}

function resolveSources(input) {
  const supplied =
    input.marketIntelligence ??
    input.result ??
    input;
  const runtime = runtimeReport(supplied);
  const source = runtime?.result ?? supplied;
  const prediction =
    source?.prediction ??
    (source?.features && Array.isArray(source?.predictions)
      ? source
      : null);

  return { runtime, source, prediction };
}

function resolveAsOf(input, source, prediction, features) {
  const value =
    input.asOf ??
    input.timestamp ??
    source?.timestamp ??
    prediction?.timestamp ??
    features?.timestamp;

  if (value === null || value === undefined || value === "") {
    throw new TypeError("Historical snapshot analysis timestamp is required.");
  }

  return isoTimestamp(value, "Historical snapshot analysis timestamp");
}

function sanitizeNewsItem(item) {
  if (!isObject(item)) return clonePlainData(item);
  const sanitized = {};

  for (const key of Object.keys(item)) {
    if (OMITTED_NEWS_FIELDS.has(key)) continue;
    const value = clonePlainData(item[key]);
    if (value !== undefined) sanitized[key] = value;
  }

  return sanitized;
}

function sanitizeNewsReport(report) {
  const normalized = clonePlainData(report);

  if (!isObject(normalized)) return normalized;

  return {
    ...normalized,
    ...(Array.isArray(report?.items)
      ? { items: report.items.map(sanitizeNewsItem) }
      : {}),
    retentionPolicy: HISTORICAL_MARKET_RETENTION_POLICY,
  };
}

function normalizeReports(input, source) {
  const supplied = isObject(input.reports) ? input.reports : {};

  return Object.fromEntries(
    HISTORICAL_MARKET_REPORT_KEYS.map((key) => {
      const fallback =
        key === "marketSnapshot"
          ? source?.marketSnapshot ?? source?.snapshot
          : source?.[key];
      const value = supplied[key] ?? fallback ?? null;

      return [
        key,
        key === "newsIntelligence"
          ? sanitizeNewsReport(value)
          : clonePlainData(value),
      ];
    }),
  );
}

function normalizePredictions(value) {
  if (!Array.isArray(value)) return [];

  return value.map((prediction) => ({
    ...(clonePlainData(prediction) || {}),
    executionAllowed: false,
  }));
}

function normalizeStatus(value) {
  const status = String(value ?? "unavailable").trim().toLowerCase();
  return status || "unavailable";
}

function normalizeScore(value) {
  const number = finiteOrNull(value);
  return number === null ? 0 : Math.round(clamp(number) * 10) / 10;
}

function buildLineage(features) {
  const details = isObject(features?.details) ? features.details : {};

  return Object.freeze(
    Object.keys(details)
      .sort()
      .map((key) => {
        const detail = details[key] || {};
        return {
          key,
          source: String(detail.source ?? "unknown"),
          sourceTimestamp: detail.sourceTimestamp
            ? isoTimestamp(
                detail.sourceTimestamp,
                `${key} historical source timestamp`,
              )
            : null,
          available: detail.available === true,
          confidence: normalizeScore(detail.confidence),
          coverage: normalizeScore(detail.coverage),
        };
      }),
  );
}

function validatePointInTime(value, asOf, path = "snapshot") {
  const asOfMilliseconds = timestampMilliseconds(asOf);

  function visit(current, currentPath) {
    if (Array.isArray(current)) {
      current.forEach((item, index) => visit(item, `${currentPath}[${index}]`));
      return;
    }

    if (!isObject(current)) return;

    for (const [key, item] of Object.entries(current)) {
      const itemPath = `${currentPath}.${key}`;

      if (
        POINT_IN_TIME_FIELDS.has(key) &&
        item !== null &&
        item !== undefined &&
        item !== ""
      ) {
        const sourceTime = timestampMilliseconds(item, `${itemPath} timestamp`);

        if (sourceTime > asOfMilliseconds) {
          throw new RangeError(
            `${itemPath} is later than the historical snapshot timestamp.`,
          );
        }
      }

      visit(item, itemPath);
    }
  }

  visit(value, path);
}

function normalizeVersions(input, runtime, source, prediction, features) {
  return {
    runtime: input.versions?.runtime ?? runtime?.version ?? null,
    orchestrator:
      input.versions?.orchestrator ??
      (source?.prediction ? source.version ?? null : null),
    feature: input.versions?.feature ?? features?.version ?? null,
    model: input.versions?.model ?? prediction?.modelVersion ?? null,
  };
}

export function normalizeHistoricalMarketSnapshotInput(
  input = {},
  { now = Date.now } = {},
) {
  if (!isObject(input)) {
    throw new TypeError("Historical snapshot input must be an object.");
  }

  if (typeof now !== "function") {
    throw new TypeError("Historical snapshot clock must be a function.");
  }

  const symbol = normalizeSymbol(input.symbol ?? input.metadata?.symbol);
  const { runtime, source, prediction } = resolveSources(input);
  const features = clonePlainData(input.features ?? prediction?.features);

  if (!isObject(features) || !isObject(features.values)) {
    throw new TypeError("Historical snapshot feature set is required.");
  }

  if (!features.timestamp) {
    throw new TypeError("Historical snapshot feature timestamp is required.");
  }

  const asOf = resolveAsOf(input, source, prediction, features);
  const featureTimestamp = isoTimestamp(
    features.timestamp,
    "Historical snapshot feature timestamp",
  );
  const capturedAt = isoTimestamp(
    input.capturedAt ?? now(),
    "Historical snapshot capture timestamp",
  );

  if (featureTimestamp !== asOf) {
    throw new RangeError(
      "Historical snapshot feature timestamp must match the analysis timestamp.",
    );
  }

  if (Date.parse(capturedAt) < Date.parse(asOf)) {
    throw new RangeError(
      "Historical snapshot capture timestamp cannot precede analysis.",
    );
  }

  const reports = normalizeReports(input, source);
  const predictions = normalizePredictions(
    input.predictions ?? prediction?.predictions,
  );

  validatePointInTime(reports, asOf, "reports");
  validatePointInTime(features, asOf, "features");
  validatePointInTime(predictions, asOf, "predictions");

  return {
    symbol,
    asOf,
    capturedAt,
    status: normalizeStatus(input.status ?? source?.status ?? prediction?.status),
    confidence: normalizeScore(input.confidence ?? features.confidence),
    coverage: normalizeScore(input.coverage ?? features.coverage),
    reports,
    features,
    predictions,
    lineage: buildLineage(features),
    versions: normalizeVersions(input, runtime, source, prediction, features),
    metadata: clonePlainData(input.metadata ?? {}),
    retentionPolicy: HISTORICAL_MARKET_RETENTION_POLICY,
    executionAllowed: false,
  };
}

export const HistoricalMarketSnapshotNormalizerInternals = Object.freeze({
  isObject,
  finiteOrNull,
  clamp,
  timestampMilliseconds,
  isoTimestamp,
  normalizeSymbol,
  clonePlainData,
  runtimeReport,
  resolveSources,
  resolveAsOf,
  sanitizeNewsItem,
  sanitizeNewsReport,
  normalizeReports,
  normalizePredictions,
  normalizeStatus,
  normalizeScore,
  buildLineage,
  validatePointInTime,
  normalizeVersions,
});

export default normalizeHistoricalMarketSnapshotInput;
