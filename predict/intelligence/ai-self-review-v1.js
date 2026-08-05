import { buildAccuracyDashboardV4 } from "../analysis/accuracy-dashboard-v4.js";

export const AI_SELF_REVIEW_V1 = "ai-self-review-v1";

function keyOf(record, field, fallback) {
  const value = String(record?.[field] ?? record?.metadata?.[field] ?? fallback).trim();
  return value || fallback;
}

function summarize(records, performance = {}) {
  return buildAccuracyDashboardV4({ tradeMemoryRecords: records, performance });
}

function group(records, selector, performance = {}) {
  const buckets = new Map();
  for (const record of Array.isArray(records) ? records : []) {
    const key = selector(record);
    const bucket = buckets.get(key) ?? [];
    bucket.push(record);
    buckets.set(key, bucket);
  }
  return [...buckets.entries()]
    .map(([key, values]) => ({ key, count: values.length, review: summarize(values, performance) }))
    .sort((a, b) => b.count - a.count || a.key.localeCompare(b.key));
}

export function buildAiSelfReviewV1({
  tradeMemoryRecords = [],
  performance = {},
  generatedAt = new Date().toISOString(),
} = {}) {
  const records = Array.isArray(tradeMemoryRecords) ? tradeMemoryRecords : [];
  const overall = summarize(records, performance);
  return {
    version: AI_SELF_REVIEW_V1,
    generatedAt,
    overall,
    bySymbol: group(records, (record) => keyOf(record, "symbol", "UNKNOWN"), performance),
    bySector: group(records, (record) => keyOf(record, "sector", "UNKNOWN"), performance),
    byRegime: group(records, (record) => keyOf(record, "marketRegime", "UNKNOWN"), performance),
    safety: {
      productionUpdateAllowed: false,
      brokerExecutionAllowed: false,
      humanApprovalRequired: true,
    },
  };
}

export default buildAiSelfReviewV1;
