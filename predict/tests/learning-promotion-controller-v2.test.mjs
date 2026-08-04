import test from "node:test";
import assert from "node:assert/strict";

import {
  LearningPromotionControllerV2,
  applyLearningPromotion,
  cancelLearningPromotionRequest,
  createLearningPromotionRequest,
  reviewLearningPromotionRequest,
} from "../learning/learning-promotion-controller-v2.js";

function learningState({
  revision = 1,
  version = "v1",
} = {}) {
  return {
    modelId:
      "ark-learning",

    modelVersion:
      version,

    revision,

    metrics: {
      ready:
        true,

      sampleCount:
        100,

      accuracy:
        60,
    },

    weights: {
      base:
        0.5,
    },
  };
}

function approvalEvaluation(
  overrides = {},
) {
  return {
    decision:
      "REQUIRE_HUMAN_APPROVAL",

    approved:
      false,

    requiresHumanApproval:
      true,

    evaluationScore:
      75,

    blockers:
      [],

    warnings:
      [],

    recommendation: {
      allowRegistryChange:
        false,
    },

    ...overrides,
  };
}

function automaticEvaluation(
  overrides = {},
) {
  return {
    decision:
      "PROMOTE",

    approved:
      true,

    requiresHumanApproval:
      false,

    evaluationScore:
      85,

    blockers:
      [],

    warnings:
      [],

    recommendation: {
      allowRegistryChange:
        true,
    },

    ...overrides,
  };
}

function createPendingRequest(
  overrides = {},
) {
  return createLearningPromotionRequest({
    evaluation:
      approvalEvaluation(),

    currentState:
      learningState({
        revision:
          1,

        version:
          "v1",
      }),

    candidateState:
      learningState({
        revision:
          2,

        version:
          "v2",
      }),

    requestedBy:
      "learning-system",

    createdAt:
      "2026-08-04T00:00:00.000Z",

    ...overrides,
  });
}

test(
  "Promotion request waits for human approval",
  () => {
    const request =
      createPendingRequest();

    assert.equal(
      request.status,
      "PENDING_APPROVAL",
    );

    assert.equal(
      request.current.revision,
      1,
    );

    assert.equal(
      request.candidate.revision,
      2,
    );

    assert.equal(
      request.approval,
      null,
    );

    assert.equal(
      request.auditTrail.length,
      1,
    );
  },
);

test(
  "Automatically approved evaluation creates approved request",
  () => {
    const request =
      createLearningPromotionRequest({
        evaluation:
          automaticEvaluation(),

        currentState:
          learningState({
            revision:
              1,

            version:
              "v1",
          }),

        candidateState:
          learningState({
            revision:
              2,

            version:
              "v2",
          }),

        requestedBy:
          "automatic-policy",

        createdAt:
          "2026-08-04T00:00:00.000Z",
      });

    assert.equal(
      request.status,
      "APPROVED",
    );

    assert.equal(
      request.approval
        .approvedBy,
      "automatic-policy",
    );
  },
);

test(
  "Human reviewer approves pending request",
  () => {
    const reviewed =
      reviewLearningPromotionRequest({
        request:
          createPendingRequest(),

        action:
          "APPROVE",

        reviewedBy:
          "human-reviewer",

        reason:
          "Validation passed.",

        reviewedAt:
          "2026-08-04T01:00:00.000Z",
      });

    assert.equal(
      reviewed.status,
      "APPROVED",
    );

    assert.equal(
      reviewed.approval
        .approvedBy,
      "human-reviewer",
    );

    assert.equal(
      reviewed.rejection,
      null,
    );

    assert.equal(
      reviewed.auditTrail.at(-1)
        .action,
      "PROMOTION_APPROVED",
    );
  },
);

test(
  "Human reviewer rejects pending request",
  () => {
    const reviewed =
      reviewLearningPromotionRequest({
        request:
          createPendingRequest(),

        action:
          "REJECT",

        reviewedBy:
          "risk-reviewer",

        reason:
          "Drawdown risk.",

        reviewedAt:
          "2026-08-04T01:00:00.000Z",
      });

    assert.equal(
      reviewed.status,
      "REJECTED",
    );

    assert.equal(
      reviewed.rejection
        .rejectedBy,
      "risk-reviewer",
    );

    assert.equal(
      reviewed.approval,
      null,
    );

    assert.equal(
      reviewed.auditTrail.at(-1)
        .action,
      "PROMOTION_REJECTED",
    );
  },
);

test(
  "Approved promotion is applied",
  () => {
    const approved =
      reviewLearningPromotionRequest({
        request:
          createPendingRequest(),

        action:
          "APPROVE",

        reviewedBy:
          "human-reviewer",

        reviewedAt:
          "2026-08-04T01:00:00.000Z",
      });

    const result =
      applyLearningPromotion({
        request:
          approved,

        appliedBy:
          "model-registry",

        appliedAt:
          "2026-08-04T02:00:00.000Z",

        registryVersion:
          "registry-v10",
      });

    assert.equal(
      result.request.status,
      "APPLIED",
    );

    assert.equal(
      result.promotedState.revision,
      2,
    );

    assert.equal(
      result.previousState.revision,
      1,
    );

    assert.equal(
      result.registryEntry.active,
      true,
    );

    assert.equal(
      result.registryEntry
        .registryVersion,
      "registry-v10",
    );

    assert.equal(
      result.promotedState
        .promotionApprovedBy,
      "human-reviewer",
    );
  },
);

test(
  "Pending request cannot be applied",
  () => {
    assert.throws(
      () =>
        applyLearningPromotion({
          request:
            createPendingRequest(),
        }),

      /Only approved promotion requests can be applied/,
    );
  },
);

test(
  "Pending promotion can be cancelled",
  () => {
    const cancelled =
      cancelLearningPromotionRequest({
        request:
          createPendingRequest(),

        cancelledBy:
          "operator",

        reason:
          "New validation required.",

        cancelledAt:
          "2026-08-04T01:30:00.000Z",
      });

    assert.equal(
      cancelled.status,
      "CANCELLED",
    );

    assert.equal(
      cancelled.cancellation
        .cancelledBy,
      "operator",
    );

    assert.equal(
      cancelled.auditTrail.at(-1)
        .action,
      "PROMOTION_CANCELLED",
    );
  },
);

test(
  "Blocked candidate cannot create promotion request",
  () => {
    assert.throws(
      () =>
        createLearningPromotionRequest({
          evaluation:
            approvalEvaluation({
              blockers: [
                "LOW_ACCURACY",
              ],
            }),

          currentState:
            learningState({
              revision:
                1,
            }),

          candidateState:
            learningState({
              revision:
                2,
            }),
        }),

      /Blocked candidate cannot create a promotion request/,
    );
  },
);

test(
  "Rejected evaluation cannot create promotion request",
  () => {
    assert.throws(
      () =>
        createLearningPromotionRequest({
          evaluation:
            approvalEvaluation({
              decision:
                "REJECT",
            }),

          currentState:
            learningState({
              revision:
                1,
            }),

          candidateState:
            learningState({
              revision:
                2,
            }),
        }),

      /is not promotable/,
    );
  },
);

test(
  "Candidate revision must be newer",
  () => {
    assert.throws(
      () =>
        createLearningPromotionRequest({
          evaluation:
            approvalEvaluation(),

          currentState:
            learningState({
              revision:
                2,
            }),

          candidateState:
            learningState({
              revision:
                2,
            }),
        }),

      /Candidate revision must be newer/,
    );
  },
);

test(
  "Only pending request can be reviewed",
  () => {
    const approved =
      reviewLearningPromotionRequest({
        request:
          createPendingRequest(),

        action:
          "APPROVE",

        reviewedBy:
          "reviewer",
      });

    assert.throws(
      () =>
        reviewLearningPromotionRequest({
          request:
            approved,

          action:
            "REJECT",

          reviewedBy:
            "reviewer",
        }),

      /Only pending promotion requests can be reviewed/,
    );
  },
);

test(
  "Promotion controller stores and updates requests",
  () => {
    const controller =
      new LearningPromotionControllerV2();

    const created =
      controller.create({
        evaluation:
          approvalEvaluation(),

        currentState:
          learningState({
            revision:
              1,

            version:
              "v1",
          }),

        candidateState:
          learningState({
            revision:
              2,

            version:
              "v2",
          }),

        requestedBy:
          "learning-system",

        createdAt:
          "2026-08-04T00:00:00.000Z",
      });

    assert.equal(
      controller.list().length,
      1,
    );

    const approved =
      controller.review({
        requestId:
          created.id,

        action:
          "APPROVE",

        reviewedBy:
          "human-reviewer",

        reviewedAt:
          "2026-08-04T01:00:00.000Z",
      });

    assert.equal(
      approved.status,
      "APPROVED",
    );

    const applied =
      controller.apply({
        requestId:
          created.id,

        appliedBy:
          "model-registry",

        appliedAt:
          "2026-08-04T02:00:00.000Z",
      });

    assert.equal(
      applied.request.status,
      "APPLIED",
    );

    assert.equal(
      controller.get(
        created.id,
      ).status,
      "APPLIED",
    );

    controller.reset();

    assert.equal(
      controller.list().length,
      0,
    );
  },
);

test(
  "Promotion controller returns cloned request data",
  () => {
    const controller =
      new LearningPromotionControllerV2();

    const created =
      controller.create({
        evaluation:
          approvalEvaluation(),

        currentState:
          learningState({
            revision:
              1,
          }),

        candidateState:
          learningState({
            revision:
              2,
          }),

        createdAt:
          "2026-08-04T00:00:00.000Z",
      });

    const fetched =
      controller.get(
        created.id,
      );

    fetched.status =
      "MUTATED";

    assert.equal(
      controller.get(
        created.id,
      ).status,
      "PENDING_APPROVAL",
    );
  },
);