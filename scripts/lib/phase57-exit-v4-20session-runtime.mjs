// Measurement accounting only: never changes a frozen v3/v4 decision.
export function summarizeManagementReadiness(decisions, minimumNeighbors = 30) {
  const audit = {total: 0, warmup: 0, neutral: 0, scored: 0, insufficient: 0, unexpectedNotReady: 0, invalidReady: 0, minimumScoredNeighbors: null};
  for (const decision of decisions) {
    const score = decision?.baseScore;
    audit.total++;
    if (score?.ready !== true) {
      if (score?.reason === 'STATE_NOT_READY') audit.warmup++;
      else if (String(score?.reason ?? '').includes('INSUFFICIENT')) audit.insufficient++;
      else audit.unexpectedNotReady++;
      continue;
    }
    if (score.stateBucket === 'NEUTRAL_HOLD') { audit.neutral++; continue; }
    const n = score.neighborCount;
    if (!Number.isInteger(n) || n < minimumNeighbors) { audit.invalidReady++; continue; }
    audit.scored++;
    audit.minimumScoredNeighbors = audit.minimumScoredNeighbors === null ? n : Math.min(audit.minimumScoredNeighbors, n);
  }
  return audit;
}

export function combineManagementReadiness(audits) {
  const result = summarizeManagementReadiness([]);
  for (const audit of audits) {
    for (const key of ['total', 'warmup', 'neutral', 'scored', 'insufficient', 'unexpectedNotReady', 'invalidReady']) result[key] += audit[key];
    if (Number.isFinite(audit.minimumScoredNeighbors)) result.minimumScoredNeighbors = result.minimumScoredNeighbors === null ? audit.minimumScoredNeighbors : Math.min(result.minimumScoredNeighbors, audit.minimumScoredNeighbors);
  }
  return result;
}

export function managementIntegrity(audit, tradeCount) {
  if (audit.insufficient || audit.unexpectedNotReady || audit.invalidReady) return 'INTEGRITY_BLOCKED';
  if (!tradeCount || !audit.scored) return 'CAPACITY_LOW';
  return 'SCORING_READY';
}

// Retry infrastructure failures only. Integrity, auth and policy failures stop.
export function isTransientDiagnosticFailure(text) {
  if (/AssertionError|ERR_ASSERTION|AUTH_REJECTED|BLOCKED_ENTITLEMENT|HTTP_40[13]|SHA_MISMATCH|SAFETY_FLAG|PIT_VIOLATION|CAUSAL_.*FAILED|SESSION_NOT_ALLOCATED|OUTCOME_IN_STATE_INPUT|MISSING_SESSION_BUNDLE/.test(text)) return false;
  return /JQUANTS_HTTP_(429|500|502|503|504)|RATE_LIMITED|ECONNRESET|ETIMEDOUT|EAI_AGAIN|UND_ERR_(CONNECT_TIMEOUT|HEADERS_TIMEOUT|SOCKET)|TypeError: fetch failed/.test(text);
}
