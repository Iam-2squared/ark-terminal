const PHASE32_REVALIDATION_SAFETY = Object.freeze({
  mode: "CANDIDATE_SPEC_REVALIDATION_ONLY",
  automaticCandidateCreationAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  excelOrderWriteAllowed: false,
  orderTriggerWriteAllowed: false,
  humanApprovalRequired: true,
});

function finiteNumber(value, fallback = null) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function assertReviewOnlyProposal(proposal) {
  if (!proposal || typeof proposal !== "object") throw new TypeError("proposal is required");
  if (proposal.candidatePatchCreated === true) throw new Error("BLOCKED_PREBUILT_CANDIDATE_PATCH");
  if (proposal.productionChangeAllowed === true) throw new Error("BLOCKED_PRODUCTION_CHANGE_REQUEST");
  if (proposal.humanReviewRequired !== true) throw new Error("BLOCKED_HUMAN_REVIEW_NOT_REQUIRED");
}

export function buildPhase32CandidateSpecification({ proposal, metadata = {} } = {}) {
  assertReviewOnlyProposal(proposal);
  const specificationId = metadata.specificationId ?? `phase32-spec-${Date.now()}`;
  return {
    specificationId,
    createdAt: metadata.createdAt ?? new Date().toISOString(),
    sourceProposal: {
      type: String(proposal.type ?? "UNKNOWN"),
      scope: String(proposal.scope ?? "UNKNOWN"),
      target: String(proposal.target ?? "UNKNOWN"),
      rationale: String(proposal.rationale ?? ""),
    },
    requestedChanges: [{
      kind: "HUMAN_DEFINED_CANDIDATE_CHANGE",
      scope: String(proposal.scope ?? "UNKNOWN"),
      target: String(proposal.target ?? "UNKNOWN"),
      instructions: metadata.instructions ?? null,
    }],
    status: "SPECIFICATION_ONLY",
    executable: false,
    candidateCodeCreated: false,
    candidateModelCreated: false,
    productionChangeAllowed: false,
    immutable: true,
    safety: { ...PHASE32_REVALIDATION_SAFETY },
  };
}

export function buildPhase32RevalidationPlan({ specification, forwardContract = {}, metadata = {} } = {}) {
  if (!specification?.immutable || specification.status !== "SPECIFICATION_ONLY") {
    throw new Error("BLOCKED_INVALID_CANDIDATE_SPECIFICATION");
  }
  const required = [
    "outOfSample",
    "paperOnly",
    "futureLeakCheckPassed",
    "sameDataContract",
    "sameCostContract",
    "sameHoldingPeriodContract",
  ];
  const blockers = required.filter((key) => forwardContract[key] !== true).map((key) => `FORWARD_CONTRACT_${key.toUpperCase()}_REQUIRED`);
  return {
    planId: metadata.planId ?? `phase32-plan-${Date.now()}`,
    createdAt: metadata.createdAt ?? new Date().toISOString(),
    specificationId: specification.specificationId,
    forwardContract: { ...forwardContract },
    requiredStages: [
      "BUILD_CANDIDATE_MANUALLY",
      "RUN_PHASE31_PAIRED_FORWARD_VALIDATION",
      "RUN_BOOTSTRAP_REVIEW",
      "RUN_REGIME_STABILITY_REVIEW",
      "HUMAN_REVIEW",
    ],
    blockers,
    status: blockers.length ? "BLOCKED" : "READY_FOR_REVALIDATION",
    automaticExecutionAllowed: false,
    safety: { ...PHASE32_REVALIDATION_SAFETY },
  };
}

export function buildPhase32RevalidationDashboard({ specification, plan, phase31Result = null } = {}) {
  const comparison = phase31Result?.comparison ?? null;
  const statisticalReview = phase31Result?.statisticalReview ?? phase31Result?.review ?? null;
  const blockers = [
    ...(plan?.blockers ?? []),
    ...(comparison?.blockers ?? []),
    ...(statisticalReview?.blockers ?? []),
  ];
  const readyForHumanReview = plan?.status === "READY_FOR_REVALIDATION" &&
    phase31Result?.status === "READY_FOR_HUMAN_REVIEW" &&
    blockers.length === 0;
  return {
    status: readyForHumanReview ? "READY_FOR_HUMAN_REVIEW" : "CONTINUE_REVALIDATION",
    specification: {
      specificationId: specification?.specificationId ?? null,
      sourceProposal: specification?.sourceProposal ?? null,
      candidateCodeCreated: specification?.candidateCodeCreated ?? false,
      candidateModelCreated: specification?.candidateModelCreated ?? false,
    },
    plan: {
      planId: plan?.planId ?? null,
      status: plan?.status ?? "BLOCKED",
      requiredStages: plan?.requiredStages ?? [],
    },
    forwardValidation: phase31Result ? {
      status: phase31Result.status ?? null,
      pairedSamples: comparison?.pairedSamples ?? null,
      champion: comparison?.champion ?? null,
      candidate: comparison?.candidate ?? null,
      deltas: comparison?.deltas ?? null,
      bootstrap: statisticalReview?.bootstrap ?? null,
      regimeStability: statisticalReview?.regimeStability ?? null,
    } : null,
    blockers,
    promotionAllowed: false,
    productionUpdateAllowed: false,
    automaticCandidateCreationAllowed: false,
    humanApprovalRequired: true,
    safety: { ...PHASE32_REVALIDATION_SAFETY },
  };
}

export function applyPhase32HumanReviewGate({ dashboard, approval = {} } = {}) {
  const blockers = [...(dashboard?.blockers ?? [])];
  if (dashboard?.status !== "READY_FOR_HUMAN_REVIEW") blockers.push("REVALIDATION_NOT_READY");
  if (approval.reviewed !== true) blockers.push("HUMAN_REVIEW_REQUIRED");
  if (approval.approved !== true) blockers.push("HUMAN_APPROVAL_REQUIRED");
  return {
    status: blockers.length ? "BLOCKED" : "APPROVED_FOR_MANUAL_CANDIDATE_REGISTRATION",
    blockers,
    approvalRecorded: blockers.length === 0,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE32_REVALIDATION_SAFETY },
  };
}

export function runPhase32CandidateRevalidation(input = {}) {
  const specification = buildPhase32CandidateSpecification({ proposal: input.proposal, metadata: input.specificationMetadata });
  const plan = buildPhase32RevalidationPlan({ specification, forwardContract: input.forwardContract, metadata: input.planMetadata });
  const dashboard = buildPhase32RevalidationDashboard({ specification, plan, phase31Result: input.phase31Result });
  const gate = applyPhase32HumanReviewGate({ dashboard, approval: input.approval });
  return {
    status: gate.status,
    specification,
    plan,
    dashboard,
    gate,
    automaticCandidateCreationAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE32_REVALIDATION_SAFETY },
  };
}

export { PHASE32_REVALIDATION_SAFETY };
