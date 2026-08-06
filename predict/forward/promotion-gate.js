export const PROMOTION_GATE_VERSION = "phase25-promotion-gate-v1";

const finite = (value) => Number.isFinite(Number(value));

export function evaluatePromotionGate(metrics = {}, options = {}) {
  const thresholds = {
    minResolvedPredictions: finite(options.minResolvedPredictions) ? Number(options.minResolvedPredictions) : 300,
    minSessions: finite(options.minSessions) ? Number(options.minSessions) : 60,
    minProfitFactor: finite(options.minProfitFactor) ? Number(options.minProfitFactor) : 1.2,
    maxDrawdown: finite(options.maxDrawdown) ? Number(options.maxDrawdown) : 10,
    maxCalibrationError: finite(options.maxCalibrationError) ? Number(options.maxCalibrationError) : 0.08,
    maxConcentration: finite(options.maxConcentration) ? Number(options.maxConcentration) : 0.3,
  };

  const blockers = [];
  if (!finite(metrics.resolvedPredictions) || Number(metrics.resolvedPredictions) < thresholds.minResolvedPredictions) blockers.push("INSUFFICIENT_RESOLVED_PREDICTIONS");
  if (!finite(metrics.sessions) || Number(metrics.sessions) < thresholds.minSessions) blockers.push("INSUFFICIENT_FORWARD_SESSIONS");
  if (!finite(metrics.profitFactor) || Number(metrics.profitFactor) < thresholds.minProfitFactor) blockers.push("PROFIT_FACTOR_BELOW_GATE");
  if (!finite(metrics.maxDrawdown) || Number(metrics.maxDrawdown) > thresholds.maxDrawdown) blockers.push("DRAWDOWN_ABOVE_GATE");
  if (!finite(metrics.calibrationError) || Number(metrics.calibrationError) > thresholds.maxCalibrationError) blockers.push("CALIBRATION_ERROR_ABOVE_GATE");
  if (!finite(metrics.symbolConcentration) || Number(metrics.symbolConcentration) > thresholds.maxConcentration) blockers.push("SYMBOL_CONCENTRATION_ABOVE_GATE");
  if (!finite(metrics.industryConcentration) || Number(metrics.industryConcentration) > thresholds.maxConcentration) blockers.push("INDUSTRY_CONCENTRATION_ABOVE_GATE");
  if (metrics.futureLeakChecked !== true) blockers.push("FUTURE_LEAK_NOT_VERIFIED");
  if (metrics.dataQualityPassed !== true) blockers.push("DATA_QUALITY_NOT_VERIFIED");
  if (metrics.killSwitchTestPassed !== true) blockers.push("KILL_SWITCH_NOT_VERIFIED");
  if (metrics.majorIncidentCount !== 0) blockers.push("MAJOR_INCIDENTS_PRESENT");

  return {
    version: PROMOTION_GATE_VERSION,
    status: blockers.length ? "NOT_READY" : "READY_FOR_HUMAN_REVIEW",
    blockers,
    thresholds,
    metrics,
    promotionExecuted: false,
    safety: {
      humanApprovalRequired: true,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
    },
  };
}

export default evaluatePromotionGate;
