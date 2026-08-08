import crypto from 'node:crypto';

export const PHASE51_SAFETY = Object.freeze({
  mode: 'DRY_RUN_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
  killSwitchRequired: true,
});

function hash(value) {
  return crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function buildOrderCandidate({ readiness, symbol, side, referencePrice, quantity, confidence = 0, expectedReturn = 0, rationale = [] } = {}) {
  const blockers = [];
  if (!readiness || readiness.status !== 'READY') blockers.push('READINESS_NOT_READY');
  const normalizedSide = String(side ?? '').toUpperCase();
  if (!['BUY', 'SELL'].includes(normalizedSide)) blockers.push('INVALID_SIDE');
  const px = finite(referencePrice);
  const qty = Math.max(0, Math.floor(finite(quantity)));
  if (!String(symbol ?? '').trim()) blockers.push('SYMBOL_REQUIRED');
  if (!(px > 0)) blockers.push('INVALID_REFERENCE_PRICE');
  if (!(qty > 0)) blockers.push('INVALID_QUANTITY');

  const candidate = {
    phase: 51.1,
    mode: 'DRY_RUN_ONLY',
    status: blockers.length ? 'BLOCKED' : 'CANDIDATE',
    blockers,
    symbol: String(symbol ?? '').trim().toUpperCase(),
    side: normalizedSide,
    referencePrice: px,
    quantity: qty,
    notional: px * qty,
    confidence: Math.max(0, Math.min(1, finite(confidence))),
    expectedReturn: finite(expectedReturn),
    rationale: Array.isArray(rationale) ? rationale.map(String) : [],
    approved: false,
    executable: false,
    transmitted: false,
    safety: PHASE51_SAFETY,
  };
  return Object.freeze({ ...candidate, candidateId: hash(candidate) });
}

export function evaluatePreTradeRisk({ candidate, limits = {}, killSwitch = false } = {}) {
  const blockers = [];
  if (!candidate || candidate.mode !== 'DRY_RUN_ONLY' || candidate.status !== 'CANDIDATE') blockers.push('INVALID_CANDIDATE');
  if (killSwitch) blockers.push('KILL_SWITCH_ACTIVE');
  const maxNotional = Math.max(0, finite(limits.maxNotional, 30000));
  const maxQuantity = Math.max(1, Math.floor(finite(limits.maxQuantity, 100)));
  const minConfidence = Math.max(0, Math.min(1, finite(limits.minConfidence, 0.55)));
  if (finite(candidate?.notional) > maxNotional) blockers.push('NOTIONAL_LIMIT_EXCEEDED');
  if (finite(candidate?.quantity) > maxQuantity) blockers.push('QUANTITY_LIMIT_EXCEEDED');
  if (finite(candidate?.confidence) < minConfidence) blockers.push('CONFIDENCE_BELOW_GATE');

  return Object.freeze({
    phase: 51.2,
    mode: 'DRY_RUN_ONLY',
    status: blockers.length ? 'BLOCKED' : 'PASS',
    blockers,
    limits: { maxNotional, maxQuantity, minConfidence },
    candidateId: candidate?.candidateId ?? null,
    executionAllowed: false,
    safety: PHASE51_SAFETY,
  });
}

export function createApprovalState({ candidate, risk, now = new Date().toISOString(), expiresAt = null } = {}) {
  const blockers = [];
  if (!candidate || candidate.status !== 'CANDIDATE') blockers.push('INVALID_CANDIDATE');
  if (!risk || risk.status !== 'PASS') blockers.push('RISK_NOT_PASSED');
  const expiry = expiresAt ? new Date(expiresAt) : new Date(Date.parse(now) + 15 * 60 * 1000);
  const state = {
    phase: 51.3,
    mode: 'DRY_RUN_ONLY',
    status: blockers.length ? 'BLOCKED' : 'PENDING_HUMAN_APPROVAL',
    candidateId: candidate?.candidateId ?? null,
    approved: false,
    rejected: false,
    createdAt: new Date(now).toISOString(),
    expiresAt: expiry.toISOString(),
    executionAllowed: false,
    transmitted: false,
    safety: PHASE51_SAFETY,
  };
  return Object.freeze({ ...state, approvalId: hash(state) });
}

export function resolveApproval({ approval, decision, actor = 'human', now = new Date().toISOString() } = {}) {
  const normalized = String(decision ?? '').toUpperCase();
  const expired = !approval || Date.parse(now) > Date.parse(approval.expiresAt);
  let status = 'BLOCKED';
  if (approval?.status === 'PENDING_HUMAN_APPROVAL' && !expired && normalized === 'APPROVE') status = 'APPROVED_DRY_RUN';
  else if (approval?.status === 'PENDING_HUMAN_APPROVAL' && !expired && normalized === 'REJECT') status = 'REJECTED';
  else if (expired) status = 'EXPIRED';
  return Object.freeze({
    phase: 51.3,
    mode: 'DRY_RUN_ONLY',
    status,
    approvalId: approval?.approvalId ?? null,
    actor: String(actor),
    resolvedAt: new Date(now).toISOString(),
    approved: status === 'APPROVED_DRY_RUN',
    executionAllowed: false,
    transmitted: false,
    safety: PHASE51_SAFETY,
  });
}

export function simulateExecution({ candidate, approval, killSwitch = false } = {}) {
  const blockers = [];
  if (!candidate || candidate.status !== 'CANDIDATE') blockers.push('INVALID_CANDIDATE');
  if (!approval || approval.status !== 'APPROVED_DRY_RUN') blockers.push('HUMAN_APPROVAL_REQUIRED');
  if (killSwitch) blockers.push('KILL_SWITCH_ACTIVE');
  const result = {
    phase: 51.4,
    mode: 'DRY_RUN_ONLY',
    status: blockers.length ? 'BLOCKED' : 'SIMULATED_ONLY',
    blockers,
    candidateId: candidate?.candidateId ?? null,
    simulatedOrder: blockers.length ? null : {
      symbol: candidate.symbol,
      side: candidate.side,
      quantity: candidate.quantity,
      referencePrice: candidate.referencePrice,
    },
    transmittedOrderCount: 0,
    brokerWriteCount: 0,
    excelOrderWriteCount: 0,
    rssOrderFunctionCallCount: 0,
    liveOrderCount: 0,
    executionAllowed: false,
    transmitted: false,
    safety: PHASE51_SAFETY,
  };
  return Object.freeze({ ...result, simulationId: hash(result) });
}

export function auditPhase51(items = []) {
  const blockers = [];
  for (const item of Array.isArray(items) ? items : []) {
    if (item?.executionAllowed !== false) blockers.push('EXECUTION_NOT_BLOCKED');
    if (item?.transmitted === true) blockers.push('TRANSMISSION_DETECTED');
    if (finite(item?.brokerWriteCount) !== 0) blockers.push('BROKER_WRITE_DETECTED');
    if (finite(item?.excelOrderWriteCount) !== 0) blockers.push('EXCEL_WRITE_DETECTED');
    if (finite(item?.rssOrderFunctionCallCount) !== 0) blockers.push('RSS_ORDER_CALL_DETECTED');
    if (finite(item?.liveOrderCount) !== 0) blockers.push('LIVE_ORDER_DETECTED');
  }
  return Object.freeze({
    phase: 51.5,
    status: blockers.length ? 'BLOCKED' : 'VALID',
    blockers: [...new Set(blockers)],
    killSwitchAvailable: true,
    safety: PHASE51_SAFETY,
  });
}
