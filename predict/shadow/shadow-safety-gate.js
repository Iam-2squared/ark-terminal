export const SHADOW_SAFETY_GATE_VERSION = "phase26-shadow-safety-gate-v1";

const finite = (value) => Number.isFinite(Number(value));
const number = (value, fallback = null) => finite(value) ? Number(value) : fallback;
const normalize = (value, fallback = "UNKNOWN") => String(value ?? fallback).trim().toUpperCase() || fallback;

export function assessShadowSafety(input = {}, options = {}) {
  const maxPriceAgeMs = number(options.maxPriceAgeMs, 15000);
  const maxClockSkewMs = number(options.maxClockSkewMs, 2000);
  const blockers = [];

  const apiStatus = normalize(input.apiStatus, "UNKNOWN");
  const rssStatus = normalize(input.rssStatus, "UNKNOWN");
  const bridgeStatus = normalize(input.bridgeStatus, "UNKNOWN");
  const priceAgeMs = number(input.priceAgeMs);
  const clockSkewMs = Math.abs(number(input.clockSkewMs, 0));
  const duplicateDetected = Boolean(input.duplicateDetected);
  const timestampOrderValid = input.timestampOrderValid !== false;
  const symbolMatched = input.symbolMatched !== false;
  const dataQualityPassed = input.dataQualityPassed === true;

  if (apiStatus !== "HEALTHY") blockers.push("API_UNHEALTHY");
  if (rssStatus !== "HEALTHY") blockers.push("RSS_UNHEALTHY");
  if (bridgeStatus !== "HEALTHY") blockers.push("BRIDGE_UNHEALTHY");
  if (!(priceAgeMs >= 0)) blockers.push("PRICE_AGE_MISSING");
  else if (priceAgeMs > maxPriceAgeMs) blockers.push("STALE_PRICE");
  if (clockSkewMs > maxClockSkewMs) blockers.push("CLOCK_SKEW_TOO_LARGE");
  if (duplicateDetected) blockers.push("DUPLICATE_DATA");
  if (!timestampOrderValid) blockers.push("TIMESTAMP_ORDER_INVALID");
  if (!symbolMatched) blockers.push("SYMBOL_MISMATCH");
  if (!dataQualityPassed) blockers.push("DATA_QUALITY_FAILED");

  return {
    version: SHADOW_SAFETY_GATE_VERSION,
    status: blockers.length ? "BLOCKED" : "SAFE_FOR_SHADOW_ANALYSIS",
    blockers,
    metrics: {
      apiStatus,
      rssStatus,
      bridgeStatus,
      priceAgeMs,
      clockSkewMs,
      duplicateDetected,
      timestampOrderValid,
      symbolMatched,
      dataQualityPassed,
    },
    thresholds: { maxPriceAgeMs, maxClockSkewMs },
    safety: {
      mode: "SHADOW_ONLY",
      executionAllowed: false,
      brokerWriteAllowed: false,
      orderCreationAllowed: false,
      orderCancellationAllowed: false,
      orderModificationAllowed: false,
      liveTradingAllowed: false,
      haltOnBlocker: true,
    },
  };
}

export default assessShadowSafety;
