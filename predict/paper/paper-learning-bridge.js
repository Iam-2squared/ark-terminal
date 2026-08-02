import {
  createPaperLearningController,
} from "./paper-learning-controller.js";

export const PAPER_LEARNING_BRIDGE_VERSION =
  "paper-learning-bridge-v1";

function clone(value) {
  return structuredClone(value);
}

function resolveAccount(
  dashboardController,
) {
  if (
    !dashboardController ||
    typeof dashboardController
      .getBroker !==
      "function"
  ) {
    throw new Error(
      "Paper dashboard controller is required.",
    );
  }

  const broker =
    dashboardController.getBroker();

  if (!broker?.account) {
    throw new Error(
      "Paper account is missing.",
    );
  }

  return broker.account;
}

export function createPaperLearningBridge({
  dashboardController,

  learningController = null,

  equityHistoryProvider =
    () => [],
} = {}) {
  if (
    !dashboardController ||
    typeof dashboardController
      .getBroker !==
      "function"
  ) {
    throw new Error(
      "Paper dashboard controller is required.",
    );
  }

  const learning =
    learningController ||
    createPaperLearningController();

  function resolveEquityHistory() {
    const history =
      equityHistoryProvider();

    return Array.isArray(history)
      ? clone(history)
      : [];
  }

  function analyze() {
    return learning.generateFeedback({
      account:
        resolveAccount(
          dashboardController,
        ),

      equityHistory:
        resolveEquityHistory(),
    });
  }

  function enqueue({
    itemId,
    metadata = {},
  } = {}) {
    const feedback =
      analyze();

    const enqueueResult =
      learning.enqueueFeedback({
        feedback,
        itemId,
        metadata: {
          ...metadata,

          accountId:
            dashboardController
              .getSnapshot()
              .accountId,

          generatedFrom:
            "paper-dashboard",
        },
      });

    return {
      feedback,
      enqueue:
        enqueueResult,
    };
  }

  function review({
    itemId,
    approved,
    reviewer =
      "owner",
    reason = null,
  } = {}) {
    return learning.review({
      itemId,
      approved,
      reviewer,
      reason,
    });
  }

  function apply({
    itemId,
    applyProvider,
  } = {}) {
    return learning.applyApproved({
      itemId,
      applyProvider,
    });
  }

  function getState() {
    return learning.getState();
  }

  function getSummary() {
    return learning.getSummary();
  }

  function getQueue() {
    return learning.getQueue();
  }

  function list({
    status = null,
  } = {}) {
    return learning.list({
      status,
    });
  }

  return {
    version:
      PAPER_LEARNING_BRIDGE_VERSION,

    analyze,
    enqueue,
    review,
    apply,

    getState,
    getSummary,
    getQueue,
    list,
  };
}

export const PaperLearningBridgeInternals = {
  clone,
  resolveAccount,
};