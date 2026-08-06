export const ORDER_CANDIDATE_VIEW_VERSION = "phase27-order-candidate-view-v1";

const finite = (value) => Number.isFinite(Number(value));
const number = (value, fallback = null) => finite(value) ? Number(value) : fallback;
const normalize = (value, fallback = "UNKNOWN") => String(value ?? fallback).trim().toUpperCase() || fallback;

export function buildOrderCandidateView({ proposal = {}, analysis = {}, costs = {}, risk = {} } = {}) {
  const candidate = proposal.proposal ?? proposal;
  const blockers = [...(proposal.blockers ?? [])];
  const symbol = normalize(candidate.symbol, "");
  const side = normalize(candidate.side, "HOLD");
  const quantity = Math.max(0, Math.floor(number(candidate.quantity, 0)));

  if (!symbol) blockers.push("SYMBOL_MISSING");
  if (!["BUY", "SELL"].includes(side)) blockers.push("SIDE_NOT_DIRECTIONAL");
  if (!(quantity > 0)) blockers.push("QUANTITY_INVALID");

  return {
    version: ORDER_CANDIDATE_VIEW_VERSION,
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    blockers: [...new Set(blockers)],
    candidate: {
      symbol,
      side,
      quantity,
      orderType: normalize(candidate.orderType, "LIMIT"),
      referencePrice: number(candidate.referencePrice),
      limitPrice: number(candidate.limitPrice),
      stopLossPrice: number(candidate.stopLossPrice),
      takeProfitPrice: number(candidate.takeProfitPrice),
      maxLoss: number(candidate.maxLoss),
      validUntil: candidate.validUntil ?? null,
      rationale: Array.isArray(candidate.rationale) ? candidate.rationale : [],
      confidence: number(analysis.confidence),
      marketRegime: normalize(analysis.marketRegime),
      liquidityStatus: normalize(analysis.liquidityStatus, "UNKNOWN"),
      riskLevel: normalize(risk.level ?? analysis.riskLevel, "UNKNOWN"),
      estimatedFeePercent: number(costs.feePercent, 0),
      estimatedSlippagePercent: number(costs.slippagePercent, 0),
      estimatedDelayCostPercent: number(costs.delayCostPercent, 0),
    },
    safety: {
      mode: "DRY_RUN_ONLY",
      executionAllowed: false,
      brokerWriteAllowed: false,
      orderCreationAllowed: false,
      orderCancellationAllowed: false,
      orderModificationAllowed: false,
      liveTradingAllowed: false,
      humanApprovalRequired: true,
    },
  };
}

export default buildOrderCandidateView;
