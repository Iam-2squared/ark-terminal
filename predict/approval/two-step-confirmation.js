export const TWO_STEP_CONFIRMATION_VERSION = "phase27-two-step-confirmation-v1";

function unique(values = []) {
  return [...new Set(values)];
}

export function evaluateTwoStepConfirmation(session = {}) {
  const approvals = Array.isArray(session.approvals) ? session.approvals : [];
  const blockers = [...(session.blockers ?? [])];
  const first = approvals.find((entry) => Number(entry.step) === 1);
  const second = approvals.find((entry) => Number(entry.step) === 2);

  if (second && !first) blockers.push("FINAL_CONFIRMATION_WITHOUT_FIRST_APPROVAL");
  if (first && second && Date.parse(second.approvedAt) < Date.parse(first.approvedAt)) {
    blockers.push("APPROVAL_ORDER_INVALID");
  }
  if (first && second && first.candidateHash !== second.candidateHash) {
    blockers.push("CANDIDATE_CHANGED_REAPPROVAL_REQUIRED");
  }

  let status = "AWAITING_FIRST_APPROVAL";
  if (first) status = "AWAITING_FINAL_CONFIRMATION";
  if (first && second && !blockers.length) status = "DRY_RUN_READY";
  if (blockers.length) status = "BLOCKED";

  return {
    version: TWO_STEP_CONFIRMATION_VERSION,
    sessionId: session.sessionId ?? null,
    status,
    blockers: unique(blockers),
    checks: {
      firstApprovalPresent: Boolean(first),
      finalConfirmationPresent: Boolean(second),
      sameCandidateHash: Boolean(first && second && first.candidateHash === second.candidateHash),
      orderValid: Boolean(!second || (first && Date.parse(second.approvedAt) >= Date.parse(first.approvedAt))),
    },
    auditEvents: approvals.map((entry) => ({
      type: Number(entry.step) === 1 ? "ORDER_CANDIDATE_APPROVED" : "ORDER_FINAL_CONFIRMED",
      actorId: entry.actorId,
      approvedAt: entry.approvedAt,
      candidateHash: entry.candidateHash,
    })),
    safety: {
      mode: "DRY_RUN_ONLY",
      executionAllowed: false,
      brokerWriteAllowed: false,
      orderCreationAllowed: false,
      liveTradingAllowed: false,
      humanApprovalRequired: true,
    },
  };
}

export default evaluateTwoStepConfirmation;
