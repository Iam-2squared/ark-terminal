export const PHASE52_RELEASE_SAFETY = Object.freeze({
  mode: 'PRE_LIVE_REVIEW_ONLY',
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

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function aggregateDryRunEvidence(records = []) {
  const items = Array.isArray(records) ? records : [];
  const valid = items.filter((r) => r && r.mode === 'DRY_RUN_ONLY');
  const blocked = valid.filter((r) => r.status === 'BLOCKED').length;
  const simulated = valid.reduce((sum, r) => {
    const hasExplicitCount = r.simulatedCount !== undefined && r.simulatedCount !== null;
    const count = hasExplicitCount
      ? Math.max(0, Math.floor(finite(r.simulatedCount)))
      : r.status === 'SIMULATED_ONLY'
        ? 1
        : 0;
    return sum + count;
  }, 0);
  const anomalies = valid.reduce((sum, r) => sum + Math.max(0, finite(r.anomalyCount)), 0);
  const safetyViolations = valid.filter((r) => r.executionAllowed !== false || r.transmitted === true || finite(r.brokerWriteCount) !== 0 || finite(r.excelOrderWriteCount) !== 0 || finite(r.rssOrderFunctionCallCount) !== 0 || finite(r.liveOrderCount) !== 0).length;
  return Object.freeze({
    phase: 52.6,
    status: safetyViolations ? 'BLOCKED' : 'VALID',
    sampleCount: valid.length,
    blockedCount: blocked,
    simulatedCount: simulated,
    anomalyCount: anomalies,
    safetyViolationCount: safetyViolations,
    executionAllowed: false,
    transmitted: false,
    safety: PHASE52_RELEASE_SAFETY,
  });
}

export function evaluateAnomalyRate({ evidence, thresholds = {} } = {}) {
  const minSamples = Math.max(1, Math.floor(finite(thresholds.minSamples, 20)));
  const maxAnomalyRate = Math.max(0, Math.min(1, finite(thresholds.maxAnomalyRate, 0.05)));
  const maxBlockedRate = Math.max(0, Math.min(1, finite(thresholds.maxBlockedRate, 0.25)));
  const blockers = [];
  if (!evidence || evidence.status !== 'VALID') blockers.push('EVIDENCE_INVALID');
  if (finite(evidence?.sampleCount) < minSamples) blockers.push('INSUFFICIENT_SAMPLES');
  const sampleCount = Math.max(1, finite(evidence?.sampleCount));
  const anomalyRate = finite(evidence?.anomalyCount) / sampleCount;
  const blockedRate = finite(evidence?.blockedCount) / sampleCount;
  if (anomalyRate > maxAnomalyRate) blockers.push('ANOMALY_RATE_ABOVE_GATE');
  if (blockedRate > maxBlockedRate) blockers.push('BLOCKED_RATE_ABOVE_GATE');
  return Object.freeze({
    phase: 52.7,
    status: blockers.length ? 'NOT_READY' : 'PASS',
    blockers,
    anomalyRate,
    blockedRate,
    thresholds: { minSamples, maxAnomalyRate, maxBlockedRate },
    executionAllowed: false,
    transmitted: false,
    safety: PHASE52_RELEASE_SAFETY,
  });
}

export function evaluateSustainedSafety({ evidence, anomalyEvaluation, consecutiveSafeDays = 0, requiredSafeDays = 10 } = {}) {
  const blockers = [];
  const days = Math.max(0, Math.floor(finite(consecutiveSafeDays)));
  const required = Math.max(1, Math.floor(finite(requiredSafeDays, 10)));
  if (!evidence || evidence.status !== 'VALID') blockers.push('EVIDENCE_INVALID');
  if (!anomalyEvaluation || anomalyEvaluation.status !== 'PASS') blockers.push('ANOMALY_GATE_NOT_PASSED');
  if (days < required) blockers.push('INSUFFICIENT_SAFE_DAYS');
  return Object.freeze({
    phase: 52.8,
    status: blockers.length ? 'NOT_READY' : 'STABLE',
    blockers,
    consecutiveSafeDays: days,
    requiredSafeDays: required,
    executionAllowed: false,
    transmitted: false,
    safety: PHASE52_RELEASE_SAFETY,
  });
}

export function evaluatePreLiveReleaseGate({ evidence, anomalyEvaluation, sustainedSafety, boundaryAudit, approvalIntegrity } = {}) {
  const blockers = [];
  if (!evidence || evidence.status !== 'VALID') blockers.push('EVIDENCE_INVALID');
  if (!anomalyEvaluation || anomalyEvaluation.status !== 'PASS') blockers.push('ANOMALY_GATE_NOT_PASSED');
  if (!sustainedSafety || sustainedSafety.status !== 'STABLE') blockers.push('SUSTAINED_SAFETY_NOT_STABLE');
  if (!boundaryAudit || boundaryAudit.status !== 'VALID') blockers.push('BROKER_BOUNDARY_INVALID');
  if (!approvalIntegrity || approvalIntegrity.status !== 'VALID') blockers.push('APPROVAL_INTEGRITY_INVALID');

  const hardBlocked = [evidence, boundaryAudit, approvalIntegrity].some((x) => x?.status === 'BLOCKED');
  const status = hardBlocked ? 'BLOCKED' : blockers.length ? 'PRE_LIVE_NOT_READY' : 'PRE_LIVE_REVIEW_READY';

  return Object.freeze({
    phase: 52.9,
    status,
    blockers,
    reviewOnly: true,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    transmitted: false,
    safety: PHASE52_RELEASE_SAFETY,
  });
}
