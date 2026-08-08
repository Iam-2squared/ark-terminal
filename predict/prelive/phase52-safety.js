import crypto from 'node:crypto';

export const PHASE52_SAFETY = Object.freeze({
  mode: 'PRE_LIVE_VALIDATION_ONLY',
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

export function runEndToEndSafetyAudit({ stages = [], safety = PHASE52_SAFETY } = {}) {
  const blockers = [];
  const required = ['SHADOW', 'READINESS', 'CANDIDATE', 'RISK', 'APPROVAL', 'DRY_RUN', 'AUDIT'];
  const seen = new Set((Array.isArray(stages) ? stages : []).map((x) => String(x?.name ?? x).toUpperCase()));
  for (const stage of required) if (!seen.has(stage)) blockers.push(`MISSING_STAGE_${stage}`);
  if (safety?.executionAllowed !== false) blockers.push('EXECUTION_NOT_BLOCKED');
  if (safety?.brokerWriteAllowed !== false) blockers.push('BROKER_WRITE_NOT_BLOCKED');
  if (safety?.excelOrderWriteAllowed !== false) blockers.push('EXCEL_WRITE_NOT_BLOCKED');
  if (safety?.rssOrderFunctionAllowed !== false) blockers.push('RSS_ORDER_NOT_BLOCKED');
  if (safety?.liveTradingAllowed !== false) blockers.push('LIVE_TRADING_NOT_BLOCKED');
  return Object.freeze({ phase: 52.0, status: blockers.length ? 'BLOCKED' : 'VALID', blockers, safety: PHASE52_SAFETY });
}

export function injectFailure({ kind, context = {} } = {}) {
  const normalized = String(kind ?? '').toUpperCase();
  const supported = new Set(['MISSING_DATA', 'API_DOWN', 'STALE_PRICE', 'OUTLIER', 'DUPLICATE_RUN', 'TIMEOUT', 'CORRUPT_STATE']);
  const blockers = [];
  if (!supported.has(normalized)) blockers.push('UNSUPPORTED_FAILURE_KIND');
  else blockers.push(`FAILURE_${normalized}`);
  return Object.freeze({ phase: 52.1, status: 'BLOCKED', failure: normalized, blockers, context, executionAllowed: false, transmitted: false, safety: PHASE52_SAFETY });
}

export function enforceIdempotency({ operationKey, priorKeys = [] } = {}) {
  const key = String(operationKey ?? '').trim();
  const seen = new Set((Array.isArray(priorKeys) ? priorKeys : []).map(String));
  const blockers = [];
  if (!key) blockers.push('OPERATION_KEY_REQUIRED');
  if (key && seen.has(key)) blockers.push('DUPLICATE_OPERATION');
  return Object.freeze({ phase: 52.2, status: blockers.length ? 'BLOCKED' : 'UNIQUE', blockers, operationKey: key || null, executionAllowed: false, safety: PHASE52_SAFETY });
}

export function validateRecovery({ checkpoint, resumedState, lastCompletedStep = null } = {}) {
  const blockers = [];
  if (!checkpoint || typeof checkpoint !== 'object') blockers.push('CHECKPOINT_REQUIRED');
  if (!resumedState || typeof resumedState !== 'object') blockers.push('RESUMED_STATE_REQUIRED');
  if (checkpoint && resumedState && hash(checkpoint.expectedState ?? checkpoint) !== hash(resumedState)) blockers.push('RECOVERY_STATE_MISMATCH');
  return Object.freeze({ phase: 52.3, status: blockers.length ? 'BLOCKED' : 'RECOVERABLE', blockers, lastCompletedStep, executionAllowed: false, safety: PHASE52_SAFETY });
}

export function verifyBrokerBoundary({ counters = {}, imports = [], safety = PHASE52_SAFETY } = {}) {
  const blockers = [];
  const forbidden = ['ORDER', 'MODIFY', 'CANCEL', 'RSS.ORDER', 'EXCEL.WRITE.ORDER', 'BROKER.WRITE'];
  for (const token of forbidden) {
    if ((Array.isArray(imports) ? imports : []).some((x) => String(x).toUpperCase().includes(token))) blockers.push(`FORBIDDEN_BOUNDARY_${token.replaceAll('.', '_')}`);
  }
  const checks = {
    brokerWriteCount: finite(counters.brokerWriteCount),
    excelOrderWriteCount: finite(counters.excelOrderWriteCount),
    rssOrderFunctionCallCount: finite(counters.rssOrderFunctionCallCount),
    liveOrderCount: finite(counters.liveOrderCount),
    modifyOrderCount: finite(counters.modifyOrderCount),
    cancelOrderCount: finite(counters.cancelOrderCount),
  };
  for (const [name, value] of Object.entries(checks)) if (value !== 0) blockers.push(`${name.toUpperCase()}_NONZERO`);
  if (safety?.brokerWriteAllowed !== false || safety?.liveTradingAllowed !== false) blockers.push('SAFETY_BOUNDARY_OPEN');
  return Object.freeze({ phase: 52.4, status: blockers.length ? 'BLOCKED' : 'READ_ONLY_CONFIRMED', blockers: [...new Set(blockers)], counters: checks, executionAllowed: false, safety: PHASE52_SAFETY });
}

export function validateApprovalIntegrity({ candidate, risk, approval, currentCandidate, currentRisk, now = new Date().toISOString() } = {}) {
  const blockers = [];
  if (!candidate || !risk || !approval) blockers.push('APPROVAL_CHAIN_INCOMPLETE');
  if (candidate && currentCandidate && hash(candidate) !== hash(currentCandidate)) blockers.push('CANDIDATE_CHANGED');
  if (risk && currentRisk && hash(risk) !== hash(currentRisk)) blockers.push('RISK_CHANGED');
  if (approval?.candidateId && candidate?.candidateId && approval.candidateId !== candidate.candidateId) blockers.push('APPROVAL_CANDIDATE_MISMATCH');
  if (approval?.expiresAt && Date.parse(now) > Date.parse(approval.expiresAt)) blockers.push('APPROVAL_EXPIRED');
  if (approval?.status !== 'APPROVED_DRY_RUN') blockers.push('APPROVAL_NOT_VALID');
  return Object.freeze({ phase: 52.5, status: blockers.length ? 'BLOCKED' : 'VALID', blockers: [...new Set(blockers)], approvalFingerprint: hash({ candidate, risk, approval }), executionAllowed: false, transmitted: false, safety: PHASE52_SAFETY });
}

export function auditPhase52(items = []) {
  const blockers = [];
  for (const item of Array.isArray(items) ? items : []) {
    if (item?.executionAllowed !== false) blockers.push('EXECUTION_NOT_BLOCKED');
    if (item?.transmitted === true) blockers.push('TRANSMISSION_DETECTED');
    if (item?.safety?.liveTradingAllowed !== false) blockers.push('LIVE_TRADING_FLAG_OPEN');
    if (item?.safety?.brokerWriteAllowed !== false) blockers.push('BROKER_WRITE_FLAG_OPEN');
  }
  return Object.freeze({ phase: 52.5, status: blockers.length ? 'BLOCKED' : 'VALID', blockers: [...new Set(blockers)], safety: PHASE52_SAFETY });
}
