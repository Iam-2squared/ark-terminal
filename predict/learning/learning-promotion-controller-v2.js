export const LEARNING_PROMOTION_CONTROLLER_V2_VERSION =
  "learning-promotion-controller-v2";

const VALID_EVALUATION_DECISIONS =
  new Set([
    "PROMOTE",
    "REQUIRE_HUMAN_APPROVAL",
    "HOLD",
    "REJECT",
  ]);

const VALID_REQUEST_STATUSES =
  new Set([
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "CANCELLED",
    "APPLIED",
  ]);

function normalizeText(
  value,
  fallback = "",
) {
  const text =
    String(
      value ??
      fallback,
    ).trim();

  return text || fallback;
}

function normalizeTimestamp(
  value,
  fallback = null,
) {
  const source =
    value ??
    fallback;

  if (
    source === null ||
    source === undefined ||
    source === ""
  ) {
    return null;
  }

  const milliseconds =
    typeof source === "number"
      ? source
      : Date.parse(source);

  if (!Number.isFinite(milliseconds)) {
    return null;
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function createId({
  modelId,
  candidateRevision,
  createdAt,
}) {
  return [
    "learning-promotion",
    normalizeText(
      modelId,
      "default-model",
    ),
    candidateRevision,
    Date.parse(createdAt),
  ].join(":");
}

function requireObject(
  value,
  message,
) {
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value)
  ) {
    throw new TypeError(
      message,
    );
  }
}

function normalizeEvaluation(
  evaluation,
) {
  requireObject(
    evaluation,
    "Learning candidate evaluation is required.",
  );

  const decision =
    normalizeText(
      evaluation.decision,
      "",
    ).toUpperCase();

  if (
    !VALID_EVALUATION_DECISIONS.has(
      decision,
    )
  ) {
    throw new TypeError(
      `Unsupported candidate evaluation decision: ${decision}`,
    );
  }

  return {
    ...clone(evaluation),

    decision,

    approved:
      evaluation.approved === true,

    requiresHumanApproval:
      evaluation.requiresHumanApproval === true,

    blockers:
      Array.isArray(
        evaluation.blockers,
      )
        ? [
            ...evaluation.blockers,
          ]
        : [],

    warnings:
      Array.isArray(
        evaluation.warnings,
      )
        ? [
            ...evaluation.warnings,
          ]
        : [],
  };
}

function normalizeState(
  state,
  label,
) {
  requireObject(
    state,
    `${label} learning state is required.`,
  );

  return {
    ...clone(state),

    revision:
      Math.max(
        0,
        Math.floor(
          Number(
            state.revision ??
            0,
          ),
        ),
      ),

    modelId:
      normalizeText(
        state.modelId,
        "default-model",
      ),

    modelVersion:
      normalizeText(
        state.modelVersion,
        "unknown",
      ),
  };
}

export function createLearningPromotionRequest({
  evaluation,
  currentState,
  candidateState,
  requestedBy = "system",
  createdAt = new Date().toISOString(),
  metadata = {},
} = {}) {
  const normalizedEvaluation =
    normalizeEvaluation(
      evaluation,
    );

  const current =
    normalizeState(
      currentState,
      "Current",
    );

  const candidate =
    normalizeState(
      candidateState,
      "Candidate",
    );

  const normalizedCreatedAt =
    normalizeTimestamp(
      createdAt,
    );

  if (!normalizedCreatedAt) {
    throw new TypeError(
      "Promotion request timestamp is invalid.",
    );
  }

  if (
    candidate.revision <=
    current.revision
  ) {
    throw new Error(
      "Candidate revision must be newer than current revision.",
    );
  }

  if (
    normalizedEvaluation.blockers
      .length >
    0
  ) {
    throw new Error(
      "Blocked candidate cannot create a promotion request.",
    );
  }

  if (
    [
      "HOLD",
      "REJECT",
    ].includes(
      normalizedEvaluation.decision,
    )
  ) {
    throw new Error(
      `Candidate decision ${normalizedEvaluation.decision} is not promotable.`,
    );
  }

  const automaticApproval =
    normalizedEvaluation.decision ===
      "PROMOTE" &&
    normalizedEvaluation.approved ===
      true &&
    normalizedEvaluation
      .requiresHumanApproval !==
      true;

  const status =
    automaticApproval
      ? "APPROVED"
      : "PENDING_APPROVAL";

  const request = {
    version:
      LEARNING_PROMOTION_CONTROLLER_V2_VERSION,

    id:
      createId({
        modelId:
          candidate.modelId,

        candidateRevision:
          candidate.revision,

        createdAt:
          normalizedCreatedAt,
      }),

    status,

    requestedBy:
      normalizeText(
        requestedBy,
        "system",
      ),

    createdAt:
      normalizedCreatedAt,

    updatedAt:
      normalizedCreatedAt,

    current: {
      modelId:
        current.modelId,

      modelVersion:
        current.modelVersion,

      revision:
        current.revision,
    },

    candidate: {
      modelId:
        candidate.modelId,

      modelVersion:
        candidate.modelVersion,

      revision:
        candidate.revision,
    },

    evaluation:
      normalizedEvaluation,

    currentState:
      current,

    candidateState:
      candidate,

    approval:
      automaticApproval
        ? {
            approvedBy:
              "automatic-policy",

            approvedAt:
              normalizedCreatedAt,

            reason:
              "Candidate evaluation permits automatic promotion.",
          }
        : null,

    rejection:
      null,

    cancellation:
      null,

    application:
      null,

    metadata:
      metadata &&
      typeof metadata ===
        "object" &&
      !Array.isArray(metadata)
        ? {
            ...metadata,
          }
        : {},

    auditTrail: [
      {
        action:
          "PROMOTION_REQUEST_CREATED",

        status,

        actor:
          normalizeText(
            requestedBy,
            "system",
          ),

        timestamp:
          normalizedCreatedAt,
      },
    ],
  };

  return request;
}

export function reviewLearningPromotionRequest({
  request,
  action,
  reviewedBy,
  reason = "",
  reviewedAt = new Date().toISOString(),
} = {}) {
  requireObject(
    request,
    "Learning promotion request is required.",
  );

  const currentStatus =
    normalizeText(
      request.status,
      "",
    ).toUpperCase();

  if (
    !VALID_REQUEST_STATUSES.has(
      currentStatus,
    )
  ) {
    throw new TypeError(
      `Unsupported promotion request status: ${currentStatus}`,
    );
  }

  if (
    currentStatus !==
    "PENDING_APPROVAL"
  ) {
    throw new Error(
      "Only pending promotion requests can be reviewed.",
    );
  }

  const normalizedAction =
    normalizeText(
      action,
      "",
    ).toUpperCase();

  if (
    ![
      "APPROVE",
      "REJECT",
    ].includes(
      normalizedAction,
    )
  ) {
    throw new TypeError(
      "Promotion review action must be APPROVE or REJECT.",
    );
  }

  const actor =
    normalizeText(
      reviewedBy,
      "",
    );

  if (!actor) {
    throw new TypeError(
      "Promotion reviewer is required.",
    );
  }

  const timestamp =
    normalizeTimestamp(
      reviewedAt,
    );

  if (!timestamp) {
    throw new TypeError(
      "Promotion review timestamp is invalid.",
    );
  }

  const approved =
    normalizedAction ===
    "APPROVE";

  return {
    ...clone(request),

    status:
      approved
        ? "APPROVED"
        : "REJECTED",

    updatedAt:
      timestamp,

    approval:
      approved
        ? {
            approvedBy:
              actor,

            approvedAt:
              timestamp,

            reason:
              normalizeText(
                reason,
                "Human approval granted.",
              ),
          }
        : null,

    rejection:
      approved
        ? null
        : {
            rejectedBy:
              actor,

            rejectedAt:
              timestamp,

            reason:
              normalizeText(
                reason,
                "Human reviewer rejected the candidate.",
              ),
          },

    auditTrail: [
      ...(
        request.auditTrail ??
        []
      ),

      {
        action:
          approved
            ? "PROMOTION_APPROVED"
            : "PROMOTION_REJECTED",

        status:
          approved
            ? "APPROVED"
            : "REJECTED",

        actor,

        reason:
          normalizeText(
            reason,
            "",
          ),

        timestamp,
      },
    ],
  };
}

export function cancelLearningPromotionRequest({
  request,
  cancelledBy,
  reason = "",
  cancelledAt = new Date().toISOString(),
} = {}) {
  requireObject(
    request,
    "Learning promotion request is required.",
  );

  if (
    ![
      "PENDING_APPROVAL",
      "APPROVED",
    ].includes(
      request.status,
    )
  ) {
    throw new Error(
      "Only pending or approved promotion requests can be cancelled.",
    );
  }

  const actor =
    normalizeText(
      cancelledBy,
      "",
    );

  if (!actor) {
    throw new TypeError(
      "Promotion cancellation actor is required.",
    );
  }

  const timestamp =
    normalizeTimestamp(
      cancelledAt,
    );

  if (!timestamp) {
    throw new TypeError(
      "Promotion cancellation timestamp is invalid.",
    );
  }

  return {
    ...clone(request),

    status:
      "CANCELLED",

    updatedAt:
      timestamp,

    cancellation: {
      cancelledBy:
        actor,

      cancelledAt:
        timestamp,

      reason:
        normalizeText(
          reason,
          "Promotion request cancelled.",
        ),
    },

    auditTrail: [
      ...(
        request.auditTrail ??
        []
      ),

      {
        action:
          "PROMOTION_CANCELLED",

        status:
          "CANCELLED",

        actor,

        reason:
          normalizeText(
            reason,
            "",
          ),

        timestamp,
      },
    ],
  };
}

export function applyLearningPromotion({
  request,
  appliedBy = "system",
  appliedAt = new Date().toISOString(),
  registryVersion = null,
} = {}) {
  requireObject(
    request,
    "Learning promotion request is required.",
  );

  if (
    request.status !==
    "APPROVED"
  ) {
    throw new Error(
      "Only approved promotion requests can be applied.",
    );
  }

  if (
    !request.candidateState
  ) {
    throw new Error(
      "Promotion request candidate state is missing.",
    );
  }

  const actor =
    normalizeText(
      appliedBy,
      "system",
    );

  const timestamp =
    normalizeTimestamp(
      appliedAt,
    );

  if (!timestamp) {
    throw new TypeError(
      "Promotion application timestamp is invalid.",
    );
  }

  const promotedState = {
    ...clone(
      request.candidateState,
    ),

    promotedAt:
      timestamp,

    promotionRequestId:
      request.id,

    promotionApprovedBy:
      request.approval
        ?.approvedBy ??
      null,

    promotionAppliedBy:
      actor,
  };

  return {
    request: {
      ...clone(request),

      status:
        "APPLIED",

      updatedAt:
        timestamp,

      application: {
        appliedBy:
          actor,

        appliedAt:
          timestamp,

        registryVersion:
          registryVersion ===
            null
            ? null
            : normalizeText(
                registryVersion,
                null,
              ),
      },

      auditTrail: [
        ...(
          request.auditTrail ??
          []
        ),

        {
          action:
            "PROMOTION_APPLIED",

          status:
            "APPLIED",

          actor,

          timestamp,
        },
      ],
    },

    promotedState,

    previousState:
      clone(
        request.currentState,
      ),

    registryEntry: {
      modelId:
        promotedState.modelId,

      modelVersion:
        promotedState.modelVersion,

      revision:
        promotedState.revision,

      active:
        true,

      promotedAt:
        timestamp,

      promotionRequestId:
        request.id,

      registryVersion:
        registryVersion ===
          null
          ? null
          : normalizeText(
              registryVersion,
              null,
            ),
    },
  };
}

export class LearningPromotionControllerV2 {
  constructor() {
    this.requests =
      new Map();
  }

  create(input = {}) {
    const request =
      createLearningPromotionRequest(
        input,
      );

    this.requests.set(
      request.id,
      clone(request),
    );

    return clone(request);
  }

  review(input = {}) {
    const id =
      normalizeText(
        input.requestId ??
        input.request?.id,
        "",
      );

    const request =
      input.request ??
      this.requests.get(id);

    const reviewed =
      reviewLearningPromotionRequest({
        ...input,
        request,
      });

    this.requests.set(
      reviewed.id,
      clone(reviewed),
    );

    return clone(reviewed);
  }

  cancel(input = {}) {
    const id =
      normalizeText(
        input.requestId ??
        input.request?.id,
        "",
      );

    const request =
      input.request ??
      this.requests.get(id);

    const cancelled =
      cancelLearningPromotionRequest({
        ...input,
        request,
      });

    this.requests.set(
      cancelled.id,
      clone(cancelled),
    );

    return clone(cancelled);
  }

  apply(input = {}) {
    const id =
      normalizeText(
        input.requestId ??
        input.request?.id,
        "",
      );

    const request =
      input.request ??
      this.requests.get(id);

    const result =
      applyLearningPromotion({
        ...input,
        request,
      });

    this.requests.set(
      result.request.id,
      clone(
        result.request,
      ),
    );

    return clone(result);
  }

  get(requestId) {
    const request =
      this.requests.get(
        requestId,
      );

    return request
      ? clone(request)
      : null;
  }

  list() {
    return Array.from(
      this.requests.values(),
    ).map(clone);
  }

  reset() {
    this.requests.clear();

    return [];
  }
}

export const learningPromotionControllerV2 =
  new LearningPromotionControllerV2();

export default createLearningPromotionRequest;