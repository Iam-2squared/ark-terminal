import crypto from 'node:crypto';
import { PHASE51_SAFETY, auditPhase51 } from './phase51-foundation.js';

function hash(value) {
  return crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function buildDailyDryRunRecord({ date, candidateCount = 0, pendingApprovalCount = 0, rejectedCount = 0, expiredCount = 0, riskBlockedCount = 0, killSwitchCount = 0, simulatedCount = 0, shadowDivergence = 0, auditStatus = 'VALID' } = {}) {
  const record = {
    phase: 51.6,
    mode: 'DRY_RUN_ONLY',
    date: String(date ?? ''),
    candidateCount: Math.max(0, Math.floor(finite(candidateCount))),
    pendingApprovalCount: Math.max(0, Math.floor(finite(pendingApprovalCount))),
    rejectedCount: Math.max(0, Math.floor(finite(rejectedCount))),
    expiredCount: Math.max(0, Math.floor(finite(expiredCount))),
    riskBlockedCount: Math.max(0, Math.floor(finite(riskBlockedCount))),
    killSwitchCount: Math.max(0, Math.floor(finite(killSwitchCount))),
    simulatedCount: Math.max(0, Math.floor(finite(simulatedCount))),
    shadowDivergence: Math.max(0, finite(shadowDivergence)),
    auditStatus: String(auditStatus),
    executionAllowed: false,
    transmitted: false,
    brokerWriteCount: 0,
    excelOrderWriteCount: 0,
    rssOrderFunctionCallCount: 0,
    liveOrderCount: 0,
    safety: PHASE51_SAFETY,
  };
  return Object.freeze({ ...record, recordId: hash(record) });
}

export function mergeDailyDryRunHistory(history = [], record) {
  const byDate = new Map();
  for (const item of [...(Array.isArray(history) ? history : []), record].filter(Boolean)) {
    if (!item?.date) continue;
    byDate.set(item.date, item);
  }
  return Object.freeze([...byDate.values()].sort((a, b) => a.date.localeCompare(b.date)));
}

export function evaluateOperationalStability(history = [], thresholds = {}) {
  const limits = {
    minDays: Math.max(5, Math.floor(finite(thresholds.minDays, 20))),
    maxAuditFailureRate: Math.max(0, Math.min(1, finite(thresholds.maxAuditFailureRate, 0))),
    maxKillSwitchRate: Math.max(0, Math.min(1, finite(thresholds.maxKillSwitchRate, 0.1))),
    maxShadowDivergence: Math.max(0, finite(thresholds.maxShadowDivergence, 0.05)),
  };
  const rows = Array.isArray(history) ? history : [];
  const dayCount = rows.length;
  const auditFailures = rows.filter((x) => x.auditStatus !== 'VALID').length;
  const killSwitchDays = rows.filter((x) => finite(x.killSwitchCount) > 0).length;
  const worstShadowDivergence = rows.reduce((m, x) => Math.max(m, finite(x.shadowDivergence)), 0);
  const blockers = [];
  if (dayCount < limits.minDays) blockers.push('INSUFFICIENT_OPERATIONAL_DAYS');
  if ((dayCount ? auditFailures / dayCount : 1) > limits.maxAuditFailureRate) blockers.push('AUDIT_FAILURE_RATE_ABOVE_GATE');
  if ((dayCount ? killSwitchDays / dayCount : 1) > limits.maxKillSwitchRate) blockers.push('KILL_SWITCH_RATE_ABOVE_GATE');
  if (worstShadowDivergence > limits.maxShadowDivergence) blockers.push('SHADOW_DIVERGENCE_ABOVE_GATE');

  const result = {
    phase: 51.7,
    mode: 'DRY_RUN_ONLY',
    status: blockers.length ? 'NOT_STABLE' : 'STABLE',
    blockers,
    metrics: {
      dayCount,
      auditFailureRate: dayCount ? auditFailures / dayCount : 1,
      killSwitchRate: dayCount ? killSwitchDays / dayCount : 1,
      worstShadowDivergence,
      totalSimulated: rows.reduce((s, x) => s + finite(x.simulatedCount), 0),
      totalRiskBlocked: rows.reduce((s, x) => s + finite(x.riskBlockedCount), 0),
    },
    executionAllowed: false,
    transmitted: false,
    safety: PHASE51_SAFETY,
  };
  return Object.freeze({ ...result, stabilityId: hash(result) });
}

export function buildOperationsDashboard({ history = [], stability = null } = {}) {
  const latest = Array.isArray(history) && history.length ? history[history.length - 1] : null;
  const alerts = [];
  if (latest?.auditStatus && latest.auditStatus !== 'VALID') alerts.push('AUDIT_BLOCKED');
  if (finite(latest?.killSwitchCount) > 0) alerts.push('KILL_SWITCH_TRIGGERED');
  if (stability?.status === 'NOT_STABLE') alerts.push('OPERATIONAL_STABILITY_NOT_READY');
  return Object.freeze({
    phase: 51.8,
    mode: 'DRY_RUN_ONLY',
    latest,
    stability,
    alerts: Object.freeze(alerts),
    humanReviewRequired: alerts.length > 0,
    executionAllowed: false,
    transmitted: false,
    safety: PHASE51_SAFETY,
  });
}

export function evaluatePhase51Release({ foundationAudit, stability, dashboard } = {}) {
  const blockers = [];
  if (!foundationAudit || foundationAudit.status !== 'VALID') blockers.push('FOUNDATION_AUDIT_NOT_VALID');
  if (!stability || stability.status !== 'STABLE') blockers.push('OPERATIONAL_STABILITY_NOT_READY');
  if (!dashboard || dashboard.mode !== 'DRY_RUN_ONLY') blockers.push('INVALID_DASHBOARD');
  if ((dashboard?.alerts ?? []).length > 0) blockers.push('ACTIVE_OPERATIONAL_ALERTS');

  const result = {
    phase: 51.9,
    mode: 'DRY_RUN_ONLY',
    status: blockers.length ? 'BLOCKED' : 'RELEASE_READY_FOR_DRY_RUN_ONLY',
    blockers,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    transmittedOrderCount: 0,
    brokerWriteCount: 0,
    excelOrderWriteCount: 0,
    rssOrderFunctionCallCount: 0,
    liveOrderCount: 0,
    safety: PHASE51_SAFETY,
  };
  return Object.freeze({ ...result, releaseId: hash(result) });
}

export function verifyPhase51Release(result) {
  return auditPhase51([result]);
}
