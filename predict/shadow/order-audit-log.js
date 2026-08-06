export const SHADOW_ORDER_AUDIT_VERSION = "phase26-shadow-order-audit-v1";

const finite = (value) => Number.isFinite(Number(value));
const number = (value, fallback = null) => finite(value) ? Number(value) : fallback;
const normalize = (value, fallback = "UNKNOWN") => String(value ?? fallback).trim().toUpperCase() || fallback;

export function buildShadowOrderAuditEntry(input = {}) {
  const proposal = input.proposal ?? {};
  const safety = input.safety ?? {};
  const blockers = Array.isArray(input.blockers) ? [...input.blockers] : [];
  const entry = {
    version: SHADOW_ORDER_AUDIT_VERSION,
    auditId: String(input.auditId ?? `${input.timestamp ?? "UNKNOWN"}:${proposal.symbol ?? "UNKNOWN"}:${proposal.side ?? "UNKNOWN"}`),
    timestamp: input.timestamp ?? null,
    marketDate: input.marketDate ?? null,
    symbol: normalize(proposal.symbol, ""),
    side: normalize(proposal.side, "HOLD"),
    quantity: Math.max(0, Math.floor(number(proposal.quantity, 0))),
    orderType: normalize(proposal.orderType, "LIMIT"),
    referencePrice: number(proposal.referencePrice),
    limitPrice: number(proposal.limitPrice),
    stopLossPrice: number(proposal.stopLossPrice),
    takeProfitPrice: number(proposal.takeProfitPrice),
    maxLoss: number(proposal.maxLoss),
    rationale: Array.isArray(proposal.rationale) ? [...proposal.rationale] : [],
    blockers,
    decision: blockers.length ? "BLOCKED" : normalize(input.decision, "SHADOW_REVIEW_ONLY"),
    modelVersion: input.modelVersion ?? null,
    datasetVersion: input.datasetVersion ?? null,
    marketSnapshotId: input.marketSnapshotId ?? null,
    safety: {
      mode: "SHADOW_ONLY",
      executionAllowed: false,
      brokerWriteAllowed: false,
      orderCreationAllowed: false,
      orderCancellationAllowed: false,
      orderModificationAllowed: false,
      liveTradingAllowed: false,
      humanApprovalRequired: safety.humanApprovalRequired !== false,
    },
    sideEffects: {
      brokerWrites: 0,
      liveOrders: 0,
      cancellations: 0,
      modifications: 0,
    },
  };

  return Object.freeze({
    ...entry,
    rationale: Object.freeze(entry.rationale),
    blockers: Object.freeze(entry.blockers),
    safety: Object.freeze(entry.safety),
    sideEffects: Object.freeze(entry.sideEffects),
  });
}

export default buildShadowOrderAuditEntry;
