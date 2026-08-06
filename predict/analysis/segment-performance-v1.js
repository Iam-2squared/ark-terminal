import { buildAccuracyDashboardV6 } from "./accuracy-dashboard-v6.js";

export const SEGMENT_PERFORMANCE_VERSION = "segment-performance-v1";

function finite(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function numberOrNull(value) {
  return finite(value) ? Number(value) : null;
}

function readPrice(row) {
  return numberOrNull(row?.entryPrice ?? row?.price ?? row?.currentPrice);
}

function readVolume(row) {
  return numberOrNull(row?.volume ?? row?.averageVolume ?? row?.avgVolume);
}

function readMarketCap(row) {
  return numberOrNull(row?.marketCap ?? row?.marketCapitalization);
}

function classifyRange(value, bands, unknown = "UNKNOWN") {
  if (!finite(value)) return unknown;
  const numeric = Number(value);
  for (const band of bands) {
    if (numeric < band.max) return band.label;
  }
  return bands.at(-1)?.label ?? unknown;
}

function marketSection(row) {
  return String(row?.marketSection ?? row?.market ?? row?.exchangeSection ?? "UNKNOWN").trim().toUpperCase() || "UNKNOWN";
}

function marketCapBucket(row) {
  return classifyRange(readMarketCap(row), [
    { max: 10_000_000_000, label: "UNDER_10B" },
    { max: 50_000_000_000, label: "10B_50B" },
    { max: 300_000_000_000, label: "50B_300B" },
    { max: 1_000_000_000_000, label: "300B_1T" },
    { max: Number.POSITIVE_INFINITY, label: "OVER_1T" },
  ]);
}

function priceBucket(row) {
  return classifyRange(readPrice(row), [
    { max: 100, label: "UNDER_100" },
    { max: 500, label: "100_500" },
    { max: 1_000, label: "500_1000" },
    { max: 3_000, label: "1000_3000" },
    { max: Number.POSITIVE_INFINITY, label: "OVER_3000" },
  ]);
}

function volumeBucket(row) {
  return classifyRange(readVolume(row), [
    { max: 100_000, label: "LOW" },
    { max: 1_000_000, label: "MEDIUM" },
    { max: 10_000_000, label: "HIGH" },
    { max: Number.POSITIVE_INFINITY, label: "VERY_HIGH" },
  ]);
}

function groupRows(rows, selector) {
  const groups = new Map();
  for (const row of rows) {
    const key = selector(row);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return groups;
}

function summarizeGroups(rows, selector, options) {
  return Object.fromEntries(
    [...groupRows(rows, selector).entries()]
      .sort(([left], [right]) => String(left).localeCompare(String(right), undefined, { numeric: true }))
      .map(([key, values]) => {
        const dashboard = buildAccuracyDashboardV6({ rows: values, options });
        return [key, {
          ...dashboard.overall,
          confidenceCalibration: dashboard.confidenceCalibration,
          calibrationError: dashboard.calibrationError,
          brierScore: dashboard.brierScore,
        }];
      }),
  );
}

function rankEntries(record, minimumSample = 5) {
  return Object.entries(record)
    .map(([key, metrics]) => ({ key, ...metrics }))
    .filter((item) => item.sampleCount >= minimumSample)
    .sort((left, right) => {
      const leftPf = Number.isFinite(Number(left.profitFactor)) ? Number(left.profitFactor) : -Infinity;
      const rightPf = Number.isFinite(Number(right.profitFactor)) ? Number(right.profitFactor) : -Infinity;
      if (rightPf !== leftPf) return rightPf - leftPf;
      return (right.accuracy ?? -Infinity) - (left.accuracy ?? -Infinity);
    });
}

export function buildSegmentPerformanceV1({ rows = [], options = {} } = {}) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");
  const minimumSample = Math.max(1, Number(options.minimumSample) || 5);

  const bySymbol = summarizeGroups(rows, (row) => String(row?.symbol ?? row?.ticker ?? row?.code ?? "UNKNOWN").trim().toUpperCase() || "UNKNOWN", options);
  const byIndustry = summarizeGroups(rows, (row) => String(row?.industry ?? row?.sector ?? "UNKNOWN").trim() || "UNKNOWN", options);
  const byMarketSection = summarizeGroups(rows, marketSection, options);
  const byMarketCap = summarizeGroups(rows, marketCapBucket, options);
  const byPrice = summarizeGroups(rows, priceBucket, options);
  const byVolume = summarizeGroups(rows, volumeBucket, options);

  return {
    version: SEGMENT_PERFORMANCE_VERSION,
    generatedAt: options.generatedAt ?? new Date().toISOString(),
    minimumSample,
    bySymbol,
    byIndustry,
    byMarketSection,
    byMarketCap,
    byPrice,
    byVolume,
    rankings: {
      symbols: rankEntries(bySymbol, minimumSample),
      industries: rankEntries(byIndustry, minimumSample),
    },
    warnings: Object.fromEntries(
      [
        ["symbol", bySymbol],
        ["industry", byIndustry],
        ["marketSection", byMarketSection],
        ["marketCap", byMarketCap],
        ["price", byPrice],
        ["volume", byVolume],
      ].map(([name, groups]) => [name, Object.entries(groups)
        .filter(([, metrics]) => metrics.sampleCount < minimumSample)
        .map(([key, metrics]) => ({ key, sampleCount: metrics.sampleCount, required: minimumSample }))]),
    ),
    safety: {
      executionAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
    },
  };
}

export const SegmentPerformanceInternals = Object.freeze({
  marketSection,
  marketCapBucket,
  priceBucket,
  volumeBucket,
  rankEntries,
});

export default buildSegmentPerformanceV1;
