import {
  createPaperLearningFeedback,
} from "./paper-learning-feedback.js";

import {
  createPaperLearningQueue,
  enqueuePaperLearningFeedback,
  listPaperLearningItems,
  markPaperLearningItemApplied,
  reviewPaperLearningItem,
  summarizePaperLearningQueue,
} from "./paper-learning-queue.js";

export const PAPER_LEARNING_CONTROLLER_VERSION =
  "paper-learning-controller-v1";

function clone(value) {
  return structuredClone(value);
}

export function createPaperLearningController({
  queue = null,

  minimumSamples = 10,

  minimumPromotionSamples = 30,

  requireHumanApproval = true,
} = {}) {
  let state = {
    version:
      PAPER_LEARNING_CONTROLLER_VERSION,

    queue:
      queue ||
      createPaperLearningQueue(),

    policy: {
      minimumSamples:
        Number(
          minimumSamples,
        ),

      minimumPromotionSamples:
        Number(
          minimumPromotionSamples,
        ),

      requireHumanApproval:
        Boolean(
          requireHumanApproval,
        ),

      automaticLivePromotion:
        false,
    },

    lastFeedback:
      null,

    lastError:
      null,
  };

  function setError(
    error,
  ) {
    state = {
      ...state,

      lastError:
        error instanceof Error
          ? error.message
          : String(error),
    };
  }

  function generateFeedback({
    account,
    equityHistory = [],
  } = {}) {
    try {
      const feedback =
        createPaperLearningFeedback({
          account,
          equityHistory,
        });

      feedback.eligibleForLearning =
        feedback.sampleCount >=
        state.policy
          .minimumSamples;

      feedback
        .eligibleForPromotionReview =
        (
          feedback.sampleCount >=
            state.policy
              .minimumPromotionSamples &&
          Number(
            feedback.performance
              ?.metrics
              ?.profitFactor || 0,
          ) > 1 &&
          Number(
            feedback.performance
              ?.metrics
              ?.maximumDrawdownPercent ||
              0,
          ) < 10
        );

      feedback.guardrails = {
        ...feedback.guardrails,

        minimumLearningSamples:
          state.policy
            .minimumSamples,

        minimumPromotionSamples:
          state.policy
            .minimumPromotionSamples,

        requiresHumanApproval:
          state.policy
            .requireHumanApproval,

        automaticLivePromotion:
          false,
      };

      state = {
        ...state,

        lastFeedback:
          clone(feedback),

        lastError:
          null,
      };

      return clone(
        feedback,
      );
    }
    catch (error) {
      setError(error);
      throw error;
    }
  }

  function enqueueFeedback({
    feedback,
    itemId,
    metadata = {},
  } = {}) {
    try {
      if (
        !feedback
          ?.eligibleForLearning
      ) {
        return {
          added: false,

          reason:
            "insufficient_samples",

          queue:
            clone(
              state.queue,
            ),

          item: null,
        };
      }

      const result =
        enqueuePaperLearningFeedback({
          queue:
            state.queue,

          feedback,

          itemId,
          metadata,
        });

      state = {
        ...state,

        queue:
          result.queue,

        lastError:
          null,
      };

      return {
        ...result,

        queue:
          clone(
            result.queue,
          ),

        item:
          result.item
            ? clone(
                result.item,
              )
            : null,
      };
    }
    catch (error) {
      setError(error);
      throw error;
    }
  }

  function generateAndEnqueue({
    account,
    equityHistory = [],
    itemId,
    metadata = {},
  } = {}) {
    const feedback =
      generateFeedback({
        account,
        equityHistory,
      });

    const enqueue =
      enqueueFeedback({
        feedback,
        itemId,
        metadata,
      });

    return {
      feedback,
      enqueue,
    };
  }

  function review({
    itemId,
    approved,
    reviewer =
      "human",
    reason = null,
  } = {}) {
    try {
      const result =
        reviewPaperLearningItem({
          queue:
            state.queue,

          itemId,
          approved,
          reviewer,
          reason,
        });

      state = {
        ...state,

        queue:
          result.queue,

        lastError:
          null,
      };

      return clone(
        result.item,
      );
    }
    catch (error) {
      setError(error);
      throw error;
    }
  }

  function applyApproved({
    itemId,
    applyProvider,
  } = {}) {
    try {
      const item =
        state.queue.items.find(
          (row) =>
            row.itemId ===
            itemId,
        );

      if (!item) {
        throw new Error(
          "Paper learning item was not found.",
        );
      }

      if (
        item.status !==
        "approved"
      ) {
        throw new Error(
          "Learning item must be approved before application.",
        );
      }

      if (
        typeof applyProvider !==
        "function"
      ) {
        throw new Error(
          "Learning apply provider is required.",
        );
      }

      const result =
        applyProvider(
          clone(
            item.feedback,
          ),
        );

      if (
        result &&
        typeof result.then ===
          "function"
      ) {
        throw new Error(
          "Async apply provider is not supported by this method.",
        );
      }

      const applied =
        markPaperLearningItemApplied({
          queue:
            state.queue,

          itemId,

          result:
            result ?? null,
        });

      state = {
        ...state,

        queue:
          applied.queue,

        lastError:
          null,
      };

      return {
        item:
          clone(
            applied.item,
          ),

        result:
          clone(
            result ?? null,
          ),
      };
    }
    catch (error) {
      setError(error);
      throw error;
    }
  }

  function getState() {
    return clone(state);
  }

  function getQueue() {
    return clone(
      state.queue,
    );
  }

  function list({
    status = null,
  } = {}) {
    return listPaperLearningItems({
      queue:
        state.queue,

      status,
    });
  }

  function getSummary() {
    return summarizePaperLearningQueue(
      state.queue,
    );
  }

  return {
    version:
      PAPER_LEARNING_CONTROLLER_VERSION,

    generateFeedback,
    enqueueFeedback,
    generateAndEnqueue,

    review,
    applyApproved,

    getState,
    getQueue,
    getSummary,
    list,
  };
}

export const PaperLearningControllerInternals = {
  clone,
};