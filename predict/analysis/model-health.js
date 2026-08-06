export const MODEL_HEALTH_VERSION = "model-health-v1";

const SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
});

function finite(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function read(source, paths, fallback = null) {
  for (const path of paths) {
    const value = path.split(".").reduce((current, key) => current?.[key], source);
    if (finite(value)) return Number(value);
  }
  return fallback;
}

function normalizeBoolean(value) {
  return value === true;
}

export function assessModelHealth({ metrics = {}, diagnostics = {}, options = {} } = {}) {
  const sampleCount = read(metrics, ["sampleCount", "total"], 0);
  const accuracy = read(metrics, ["accuracy", "accuracyPercent"]);
  const profitFactor = read(metrics, ["profitFactor"]);
  const maxDrawdown = read(metrics, ["maxDrawdown", "maximumDrawdown"]);
  const calibrationError = read(metrics, ["calibrationError", "ece"]);
  const pendingRatio = read(diagnostics, ["pendingRatio"], 0);
  const apiHealthy = diagnostics.apiHealthy !== false;
  const rssHealthy = diagnostics.rssHealthy !== false;
  const dataQualityPassed = normalizeBoolean(diagnostics.dataQualityPassed);
  const futureLeakChecked = normalizeBoolean(diagnostics.futureLeakChecked);
  const driftStatus = String(diagnostics.driftStatus ?? "UNKNOWN").toUpperCase();

  const thresholds = {
    minimumSample: finite(options.minimumSample) ? Number(options.minimumSample) : 300,
    warningSample: finite(options.warningSample) ? Number(options.warningSample) : 150,
    minimumProfitFactor: finite(options.minimumProfitFactor) ? Number(options.minimumProfitFactor) : 1.2,
    warningProfitFactor: finite(options.warningProfitFactor) ? Number(options.warningProfitFactor) : 1.05,
    maximumDrawdown: finite(options.maximumDrawdown) ? Number(options.maximumDrawdown) : 10,
    warningDrawdown: finite(options.warningDrawdown) ? Number(options.warningDrawdown) : 8,
    maximumCalibrationError: finite(options.maximumCalibrationError) ? Number(options.maximumCalibrationError) : 0.08,
    warningCalibrationError: finite(options.warningCalibrationError) ? Number(options.warningCalibrationError) : 0.06,
    maximumPendingRatio: finite(options.maximumPendingRatio) ? Number(options.maximumPendingRatio) : 0.4,
  };

  const blockers = [];
  const warnings = [];

  if (!futureLeakChecked) blockers.push("FUTURE_LEAK_NOT_VERIFIED");
  if (!dataQualityPassed) blockers.push("DATA_QUALITY_FAILED_OR_UNKNOWN");
  if (!apiHealthy) blockers.push("API_UNHEALTHY");
  if (!rssHealthy) blockers.push("RSS_UNHEALTHY");
  if (["BLOCKED", "DEGRADED"].includes(driftStatus)) blockers.push("DRIFT_UNSAFE");
  if (sampleCount < thresholds.warningSample) blockers.push("SAMPLE_TOO_SMALL");
  else if (sampleCount < thresholds.minimumSample) warnings.push("SAMPLE_BELOW_TARGET");
  if (profitFactor === null || profitFactor < thresholds.warningProfitFactor) blockers.push("PROFIT_FACTOR_UNSAFE");
  else if (profitFactor < thresholds.minimumProfitFactor) warnings.push("PROFIT_FACTOR_BELOW_TARGET");
  if (maxDrawdown === null || maxDrawdown > thresholds.maximumDrawdown) blockers.push("DRAWDOWN_UNSAFE");
  else if (maxDrawdown > thresholds.warningDrawdown) warnings.push("DRAWDOWN_NEAR_LIMIT");
  if (calibrationError === null || calibrationError > thresholds.maximumCalibrationError) blockers.push("CALIBRATION_UNSAFE");
  else if (calibrationError > thresholds.warningCalibrationError) warnings.push("CALIBRATION_NEAR_LIMIT");
  if (pendingRatio > thresholds.maximumPendingRatio) warnings.push("PENDING_OUTCOME_RATIO_HIGH");
  if (driftStatus === "WARNING") warnings.push("DRIFT_WARNING");

  let status = "HEALTHY";
  if (blockers.length) status = blockers.some((item) => ["FUTURE_LEAK_NOT_VERIFIED", "DATA_QUALITY_FAILED_OR_UNKNOWN", "API_UNHEALTHY", "RSS_UNHEALTHY"].includes(item)) ? "BLOCKED" : "DEGRADED";
  else if (warnings.length) status = "WARNING";

  return {
    version: MODEL_HEALTH_VERSION,
    generatedAt: options.generatedAt ?? new Date().toISOString(),
    status,
    metrics: { sampleCount, accuracy, profitFactor, maxDrawdown, calibrationError, pendingRatio },
    diagnostics: { apiHealthy, rssHealthy, dataQualityPassed, futureLeakChecked, driftStatus },
    thresholds,
    warnings,
    blockers,
    paperForwardTestAllowed: status === "HEALTHY" || status === "WARNING",
    semiAutomaticTradingAllowed: false,
    automaticTradingAllowed: false,
    safety: SAFETY,
  };
}

export default assessModelHealth;
