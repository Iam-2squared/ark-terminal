export const CANDIDATE_REJECTION_VERSION = "phase24-candidate-rejection-v1";

const finite = (value) => Number.isFinite(Number(value));
const number = (value, fallback = null) => finite(value) ? Number(value) : fallback;

export function evaluateCandidateRejection(candidate = {}, options = {}) {
  const minimumSample = number(options.minimumSample, 100);
  const minimumProfitFactor = number(options.minimumProfitFactor, 1.2);
  const maximumDrawdown = number(options.maximumDrawdown, 10);
  const maximumCalibrationError = number(options.maximumCalibrationError, 0.08);
  const maximumConcentration = number(options.maximumConcentration, 0.3);

  const sampleCount = number(candidate.sampleCount, 0);
  const profitFactor = number(candidate.profitFactor);
  const maxDrawdown = number(candidate.maxDrawdown);
  const calibrationError = number(candidate.calibrationError);
  const symbolConcentration = number(candidate.symbolConcentration, 0);
  const industryConcentration = number(candidate.industryConcentration, 0);
  const blockers = [];

  if (sampleCount < minimumSample) blockers.push("INSUFFICIENT_SAMPLE");
  if (profitFactor === null || profitFactor < minimumProfitFactor) blockers.push("PROFIT_FACTOR_BELOW_THRESHOLD");
  if (maxDrawdown === null || maxDrawdown > maximumDrawdown) blockers.push("MAX_DRAWDOWN_EXCEEDED");
  if (calibrationError === null || calibrationError > maximumCalibrationError) blockers.push("CALIBRATION_ERROR_EXCEEDED");
  if (symbolConcentration > maximumConcentration) blockers.push("SYMBOL_CONCENTRATION_TOO_HIGH");
  if (industryConcentration > maximumConcentration) blockers.push("INDUSTRY_CONCENTRATION_TOO_HIGH");
  if (candidate.futureLeakChecked !== true) blockers.push("FUTURE_LEAK_CHECK_REQUIRED");
  if (candidate.dataQualityStatus === "BLOCKED" || candidate.dataQualityPassed === false) blockers.push("DATA_QUALITY_BLOCKED");
  if (candidate.outOfSamplePassed === false) blockers.push("OUT_OF_SAMPLE_FAILED");
  if (candidate.walkForwardPassed === false) blockers.push("WALK_FORWARD_FAILED");

  return {
    version: CANDIDATE_REJECTION_VERSION,
    decision: blockers.length ? "REJECT" : "KEEP_FOR_HUMAN_REVIEW",
    blockers,
    metrics: {
      sampleCount,
      profitFactor,
      maxDrawdown,
      calibrationError,
      symbolConcentration,
      industryConcentration,
    },
    thresholds: {
      minimumSample,
      minimumProfitFactor,
      maximumDrawdown,
      maximumCalibrationError,
      maximumConcentration,
    },
    safety: {
      automaticRejectionAllowed: true,
      automaticPromotionAllowed: false,
      humanApprovalRequired: true,
      productionUpdateAllowed: false,
      executionAllowed: false,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
    },
  };
}

export default evaluateCandidateRejection;
