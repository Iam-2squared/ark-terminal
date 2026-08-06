export const STRATEGY_ENSEMBLE_VERSION = "phase24-strategy-ensemble-v1";

const finite = (value) => Number.isFinite(Number(value));
const number = (value, fallback = null) => finite(value) ? Number(value) : fallback;
const normalizeAction = (value) => {
  const action = String(value ?? "").trim().toUpperCase();
  return ["BUY", "SELL", "HOLD"].includes(action) ? action : "HOLD";
};

export function buildStrategyEnsemble(votes = [], context = {}, options = {}) {
  if (!Array.isArray(votes)) throw new TypeError("votes must be an array");
  const eligible = votes.filter((vote) => number(vote.confidence) !== null);
  const minimumModels = Math.max(1, Math.trunc(number(options.minimumModels, 2)));
  const minimumAgreement = Math.min(1, Math.max(0, number(options.minimumAgreement, 0.67)));
  const minimumConfidence = Math.min(1, Math.max(0, number(options.minimumConfidence, 0.7)));
  const counts = { BUY: 0, SELL: 0, HOLD: 0 };
  let weightedConfidence = 0;
  let totalWeight = 0;

  for (const vote of eligible) {
    const action = normalizeAction(vote.action ?? vote.signal);
    const confidenceRaw = number(vote.confidence, 0);
    const confidence = Math.min(1, Math.max(0, confidenceRaw > 1 ? confidenceRaw / 100 : confidenceRaw));
    const weight = Math.max(0, number(vote.weight, 1));
    counts[action] += 1;
    weightedConfidence += confidence * weight;
    totalWeight += weight;
  }

  const ranked = Object.entries(counts).sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
  const action = ranked[0]?.[1] > 0 ? ranked[0][0] : "HOLD";
  const agreement = eligible.length ? counts[action] / eligible.length : 0;
  const confidence = totalWeight > 0 ? weightedConfidence / totalWeight : 0;
  const blockers = [];

  if (eligible.length < minimumModels) blockers.push("INSUFFICIENT_MODEL_COUNT");
  if (agreement < minimumAgreement) blockers.push("AGREEMENT_BELOW_THRESHOLD");
  if (confidence < minimumConfidence) blockers.push("CONFIDENCE_BELOW_THRESHOLD");
  if (context.riskBlocked === true || context.riskStatus === "BLOCKED") blockers.push("RISK_BLOCKED");
  if (context.liquidityStatus !== "PASS") blockers.push("LIQUIDITY_NOT_PASSED");
  if (context.costStatus === "BLOCKED" || context.costPassed === false) blockers.push("COST_GATE_BLOCKED");
  if (context.marketRegimeSupported === false) blockers.push("REGIME_UNSUPPORTED");

  return {
    version: STRATEGY_ENSEMBLE_VERSION,
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    action: blockers.length ? "HOLD" : action,
    agreement,
    confidence,
    counts,
    modelCount: eligible.length,
    blockers,
    context: {
      marketRegime: String(context.marketRegime ?? "UNKNOWN").toUpperCase(),
      liquidityStatus: context.liquidityStatus ?? "UNKNOWN",
      riskStatus: context.riskStatus ?? (context.riskBlocked ? "BLOCKED" : "UNKNOWN"),
      costStatus: context.costStatus ?? (context.costPassed === true ? "PASS" : "UNKNOWN"),
    },
    thresholds: { minimumModels, minimumAgreement, minimumConfidence },
    safety: {
      advisoryOnly: true,
      humanApprovalRequired: true,
      executionAllowed: false,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
    },
  };
}

export default buildStrategyEnsemble;
