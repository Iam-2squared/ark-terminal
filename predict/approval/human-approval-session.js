export const HUMAN_APPROVAL_SESSION_VERSION = "phase27-human-approval-session-v1";

const normalize = (value, fallback = "UNKNOWN") => String(value ?? fallback).trim().toUpperCase() || fallback;

export function createHumanApprovalSession({ candidateId, candidateHash, expiresAt, requestedBy = "ARK_TERMINAL" } = {}) {
  const blockers = [];
  if (!candidateId) blockers.push("CANDIDATE_ID_MISSING");
  if (!candidateHash) blockers.push("CANDIDATE_HASH_MISSING");
  if (!expiresAt || Number.isNaN(Date.parse(expiresAt))) blockers.push("EXPIRY_INVALID");

  return {
    version: HUMAN_APPROVAL_SESSION_VERSION,
    sessionId: blockers.length ? null : `${candidateId}:${candidateHash}`,
    candidateId: candidateId ?? null,
    candidateHash: candidateHash ?? null,
    requestedBy: normalize(requestedBy),
    status: blockers.length ? "BLOCKED" : "AWAITING_FIRST_APPROVAL",
    blockers,
    expiresAt: expiresAt ?? null,
    approvals: [],
    safety: {
      executionAllowed: false,
      brokerWriteAllowed: false,
      humanApprovalRequired: true,
      twoStepApprovalRequired: true,
    },
  };
}

export function recordApproval(session = {}, { actorId, step, approvedAt, candidateHash } = {}) {
  const blockers = [...(session.blockers ?? [])];
  const timestamp = approvedAt ? Date.parse(approvedAt) : NaN;
  const expired = !session.expiresAt || Date.parse(session.expiresAt) <= timestamp;

  if (!actorId) blockers.push("ACTOR_ID_MISSING");
  if (![1, 2].includes(Number(step))) blockers.push("APPROVAL_STEP_INVALID");
  if (!Number.isFinite(timestamp)) blockers.push("APPROVAL_TIME_INVALID");
  if (expired) blockers.push("APPROVAL_SESSION_EXPIRED");
  if (candidateHash !== session.candidateHash) blockers.push("CANDIDATE_CHANGED_REAPPROVAL_REQUIRED");

  const approvals = Array.isArray(session.approvals) ? [...session.approvals] : [];
  if (!blockers.length) approvals.push({ actorId, step: Number(step), approvedAt, candidateHash });

  let status = blockers.length ? "BLOCKED" : "AWAITING_FIRST_APPROVAL";
  if (!blockers.length && approvals.some((entry) => entry.step === 1)) status = "AWAITING_FINAL_CONFIRMATION";
  if (!blockers.length && approvals.some((entry) => entry.step === 1) && approvals.some((entry) => entry.step === 2)) {
    status = "DRY_RUN_APPROVED";
  }

  return {
    ...session,
    status,
    blockers: [...new Set(blockers)],
    approvals,
    safety: {
      ...(session.safety ?? {}),
      executionAllowed: false,
      brokerWriteAllowed: false,
      humanApprovalRequired: true,
      twoStepApprovalRequired: true,
    },
  };
}

export default createHumanApprovalSession;
