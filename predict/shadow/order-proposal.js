export const SHADOW_ORDER_PROPOSAL_VERSION = "phase26-shadow-order-proposal-v1";

const finite = (value) => Number.isFinite(Number(value));
const number = (value, fallback = null) => finite(value) ? Number(value) : fallback;
const normalize = (value, fallback = "UNKNOWN") => String(value ?? fallback).trim().toUpperCase() || fallback;

export function buildShadowOrderProposal(input = {}, options = {}) {
  const symbol = normalize(input.symbol, "");
  const side = normalize(input.side ?? input.signal, "HOLD");
  const referencePrice = number(input.referencePrice ?? input.price);
  const quantity = Math.max(0, Math.floor(number(input.quantity, 0)));
  const stopLossPercent = number(input.stopLossPercent, number(options.stopLossPercent, 3));
  const takeProfitPercent = number(input.takeProfitPercent, number(options.takeProfitPercent, 6));
  const limitOffsetPercent = number(input.limitOffsetPercent, 0);
  const blockers = [];

  if (!symbol) blockers.push("SYMBOL_MISSING");
  if (!["BUY", "SELL"].includes(side)) blockers.push("SIDE_NOT_DIRECTIONAL");
  if (!(referencePrice > 0)) blockers.push("REFERENCE_PRICE_INVALID");
  if (!(quantity > 0)) blockers.push("QUANTITY_INVALID");

  const direction = side === "SELL" ? -1 : 1;
  const limitPrice = referencePrice > 0 ? referencePrice * (1 + direction * limitOffsetPercent / 100) : null;
  const stopLossPrice = referencePrice > 0 ? referencePrice * (1 - direction * stopLossPercent / 100) : null;
  const takeProfitPrice = referencePrice > 0 ? referencePrice * (1 + direction * takeProfitPercent / 100) : null;
  const maxLoss = referencePrice > 0 ? Math.abs(referencePrice - stopLossPrice) * quantity : null;

  return {
    version: SHADOW_ORDER_PROPOSAL_VERSION,
    status: blockers.length ? "BLOCKED" : "READY_FOR_SHADOW_REVIEW",
    blockers,
    proposal: {
      symbol,
      side,
      quantity,
      orderType: normalize(input.orderType, "LIMIT"),
      referencePrice,
      limitPrice,
      stopLossPrice,
      takeProfitPrice,
      maxLoss,
      validUntil: input.validUntil ?? null,
      rationale: input.rationale ?? [],
    },
    safety: {
      mode: "SHADOW_ONLY",
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

export default buildShadowOrderProposal;
