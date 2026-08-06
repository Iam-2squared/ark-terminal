export const CANDIDATE_REVIEW_VERSION = "candidate-review-v1";

const SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function finite(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function numberOrNull(value) {
  return finite(value) ? Number(value) : null;
}

function metric(source, keys) {
  for (const key of keys) {
    const value = key.split(".").reduce((current, part) => current?.[part], source);
    if (finite(value)) return Number(value);
  }
  return null;
}

function delta(candidate, champion) {
  if (!finite(candidate) || !finite(champion)) return null;
  return Number(candidate) - Number(champion);
}

function normalizeModel(model = {}, fallbackRole = "UNKNOWN") {
  return {
    role: String(model.role ?? fallbackRole).toUpperCase(),
    version: String(model.version ?? model.id ?? "UNKNOWN"),
    sampleCount: metric(model, ["sampleCount", "metrics.sampleCount", "metrics.total"]),
    accuracy: metric(model, ["accuracy", "metrics.accuracy", "metrics.accuracyPercent"]),
    profitFactor: metric(model, ["profitFactor", "metrics.profitFactor"]),
    maxDrawdown: metric(model, ["maxDrawdown", "metrics.maxDrawdown", "metrics.maximumDrawdown"]),
    calibrationError: metric(model, ["calibrationError", "metrics.calibrationError", "metrics.ece"]),
    sharpe: metric(model, ["sharpe", "metrics.sharpe", "metrics.sharpeRatio"]),
    forwardSessions: metric(model, ["forwardSessions", "forwardTest.sessions", "metrics.forwardSessions"]),
    futureLeakChecked: model.futureLeakChecked === true || model.validation?.futureLeakChecked === true,
    dataQualityPassed: model.dataQualityPassed === true || model.validation?.dataQualityPassed === true,
    driftStatus: String(model.driftStatus ?? model.validation?.driftStatus ?? "UNKNOWN").toUpperCase(),
  };
}

export function buildCandidateReview({ champion = {}, candidate = {}, options = {} } = {}) {
  const current = normalizeModel(champion, "CHAMPION");
  const challenger = normalizeModel(candidate, "CANDIDATE");
  const minimumSample = finite(options.minimumSample) ? Number(options.minimumSample) : 300;
  const minimumForwardSessions = finite(options.minimumForwardSessions) ? Number(options.minimumForwardSessions) : 60;
  const minimumProfitFactor = finite(options.minimumProfitFactor) ? Number(options.minimumProfitFactor) : 1.2;
  const maximumDrawdown = finite(options.maximumDrawdown) ? Number(options.maximumDrawdown) : 10;
  const maximumCalibrationError = finite(options.maximumCalibrationError) ? Number(options.maximumCalibrationError) : 0.08;

  const blockers = [];
  if (!challenger.futureLeakChecked) blockers.push("FUTURE_LEAK_NOT_VERIFIED");
  if (!challenger.dataQualityPassed) blockers.push("DATA_QUALITY_NOT_VERIFIED");
  if ((challenger.sampleCount ?? 0) < minimumSample) blockers.push("INSUFFICIENT_SAMPLE");
  if ((challenger.forwardSessions ?? 0) < minimumForwardSessions) blockers.push("INSUFFICIENT_FORWARD_TEST");
  if ((challenger.profitFactor ?? -Infinity) < minimumProfitFactor) blockers.push("PROFIT_FACTOR_BELOW_THRESHOLD");
  if (challenger.maxDrawdown === null || challenger.maxDrawdown > maximumDrawdown) blockers.push("MAX_DRAWDOWN_ABOVE_THRESHOLD");
  if (challenger.calibrationError === null || challenger.calibrationError > maximumCalibrationError) blockers.push("CALIBRATION_ERROR_ABOVE_THRESHOLD");
  if (["DEGRADED", "BLOCKED"].includes(challenger.driftStatus)) blockers.push("DRIFT_STATUS_UNSAFE");

  const comparison = {
    accuracyDelta: delta(challenger.accuracy, current.accuracy),
    profitFactorDelta: delta(challenger.profitFactor, current.profitFactor),
    maxDrawdownDelta: delta(challenger.maxDrawdown, current.maxDrawdown),
    calibrationErrorDelta: delta(challenger.calibrationError, current.calibrationError),
    sharpeDelta: delta(challenger.sharpe, current.sharpe),
  };

  const beatsChampion =
    (comparison.profitFactorDelta ?? -Infinity) > 0 &&
    (comparison.maxDrawdownDelta ?? Infinity) <= 0 &&
    (comparison.calibrationErrorDelta ?? Infinity) <= 0;

  let recommendation = "KEEP";
  if (blockers.length) recommendation = "REJECT";
  else if (beatsChampion) recommendation = "PROMOTE_REVIEW";

  return {
    version: CANDIDATE_REVIEW_VERSION,
    generatedAt: options.generatedAt ?? new Date().toISOString(),
    champion: current,
    candidate: challenger,
    comparison,
    thresholds: {
      minimumSample,
      minimumForwardSessions,
      minimumProfitFactor,
      maximumDrawdown,
      maximumCalibrationError,
    },
    blockers,
    recommendation,
    promotionReadyForHumanReview: recommendation === "PROMOTE_REVIEW",
    promotionExecuted: false,
    safety: SAFETY,
  };
}

export const CandidateReviewInternals = Object.freeze({
  finite,
  numberOrNull,
  metric,
  delta,
  normalizeModel,
});

export default buildCandidateReview;
