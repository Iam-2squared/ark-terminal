export const PAPER_LEARNING_QUEUE_VERSION =
  "paper-learning-queue-v1";

export const PAPER_LEARNING_STATUS =
  Object.freeze({
    PENDING:
      "pending",

    APPROVED:
      "approved",

    REJECTED:
      "rejected",

    APPLIED:
      "applied",
  });

function clone(value) {
  return structuredClone(value);
}

function createId(
  prefix =
    "paper-learning",
) {
  return (
    prefix +
    "-" +
    Date.now().toString(36) +
    "-" +
    Math.random()
      .toString(36)
      .slice(2, 10)
  );
}

export function createPaperLearningQueue({
  createdAt =
    new Date().toISOString(),
} = {}) {
  return {
    version:
      PAPER_LEARNING_QUEUE_VERSION,

    items: [],

    createdAt,

    updatedAt:
      createdAt,
  };
}

export function createPaperLearningQueueItem({
  itemId =
    createId(),

  feedback,

  createdAt =
    new Date().toISOString(),

  metadata = {},
} = {}) {
  if (
    !feedback ||
    typeof feedback !==
      "object"
  ) {
    throw new Error(
      "Paper learning feedback is required.",
    );
  }

  return {
    version:
      PAPER_LEARNING_QUEUE_VERSION,

    itemId:
      String(itemId),

    source:
      "paper-trading",

    status:
      PAPER_LEARNING_STATUS
        .PENDING,

    feedback:
      clone(feedback),

    metadata: {
      ...metadata,
    },

    review: null,

    createdAt,

    updatedAt:
      createdAt,
  };
}

export function enqueuePaperLearningFeedback({
  queue,
  feedback,
  itemId,
  createdAt =
    new Date().toISOString(),
  metadata = {},
} = {}) {
  if (
    !queue ||
    !Array.isArray(
      queue.items,
    )
  ) {
    throw new Error(
      "Paper learning queue is invalid.",
    );
  }

  const resolvedItemId =
    itemId ||
    (
      "paper-feedback-" +
      String(
        feedback?.generatedAt ||
        Date.now(),
      )
    );

  const duplicate =
    queue.items.find(
      (item) =>
        item.itemId ===
          resolvedItemId ||
        (
          item.feedback
            ?.generatedAt &&
          item.feedback
            ?.generatedAt ===
            feedback?.generatedAt
        ),
    );

  if (duplicate) {
    return {
      queue:
        clone(queue),

      item:
        clone(duplicate),

      added:
        false,

      reason:
        "duplicate",
    };
  }

  const item =
    createPaperLearningQueueItem({
      itemId:
        resolvedItemId,

      feedback,

      createdAt,
      metadata,
    });

  const next =
    clone(queue);

  next.items.push(
    item,
  );

  next.updatedAt =
    createdAt;

  return {
    queue:
      next,

    item,

    added:
      true,

    reason:
      null,
  };
}

export function findPaperLearningItem({
  queue,
  itemId,
} = {}) {
  return (
    queue?.items?.find(
      (item) =>
        item.itemId ===
        itemId,
    ) || null
  );
}

export function reviewPaperLearningItem({
  queue,
  itemId,
  approved,
  reviewer =
    "human",

  reason = null,

  reviewedAt =
    new Date().toISOString(),
} = {}) {
  if (
    !queue ||
    !Array.isArray(
      queue.items,
    )
  ) {
    throw new Error(
      "Paper learning queue is invalid.",
    );
  }

  const index =
    queue.items.findIndex(
      (item) =>
        item.itemId ===
        itemId,
    );

  if (index < 0) {
    throw new Error(
      "Paper learning item was not found.",
    );
  }

  const next =
    clone(queue);

  const item =
    next.items[index];

  if (
    item.status !==
    PAPER_LEARNING_STATUS
      .PENDING
  ) {
    throw new Error(
      "Only pending learning items can be reviewed.",
    );
  }

  const status =
    approved
      ? PAPER_LEARNING_STATUS
          .APPROVED
      : PAPER_LEARNING_STATUS
          .REJECTED;

  next.items[index] = {
    ...item,

    status,

    review: {
      approved:
        Boolean(approved),

      reviewer:
        String(reviewer),

      reason:
        reason === null
          ? null
          : String(reason),

      reviewedAt,
    },

    updatedAt:
      reviewedAt,
  };

  next.updatedAt =
    reviewedAt;

  return {
    queue:
      next,

    item:
      clone(
        next.items[index],
      ),
  };
}

export function markPaperLearningItemApplied({
  queue,
  itemId,
  appliedAt =
    new Date().toISOString(),
  result = null,
} = {}) {
  const index =
    queue?.items?.findIndex(
      (item) =>
        item.itemId ===
        itemId,
    ) ?? -1;

  if (index < 0) {
    throw new Error(
      "Paper learning item was not found.",
    );
  }

  if (
    queue.items[index]
      .status !==
    PAPER_LEARNING_STATUS
      .APPROVED
  ) {
    throw new Error(
      "Only approved learning items can be applied.",
    );
  }

  const next =
    clone(queue);

  next.items[index] = {
    ...next.items[index],

    status:
      PAPER_LEARNING_STATUS
        .APPLIED,

    appliedAt,

    applicationResult:
      result === null
        ? null
        : clone(result),

    updatedAt:
      appliedAt,
  };

  next.updatedAt =
    appliedAt;

  return {
    queue:
      next,

    item:
      clone(
        next.items[index],
      ),
  };
}

export function listPaperLearningItems({
  queue,
  status = null,
} = {}) {
  return (
    queue?.items || []
  )
    .filter(
      (item) =>
        status === null ||
        item.status ===
          status,
    )
    .map(clone);
}

export function summarizePaperLearningQueue(
  queue = {},
) {
  const items =
    queue.items || [];

  const count =
    (status) =>
      items.filter(
        (item) =>
          item.status ===
          status,
      ).length;

  return {
    total:
      items.length,

    pending:
      count(
        PAPER_LEARNING_STATUS
          .PENDING,
      ),

    approved:
      count(
        PAPER_LEARNING_STATUS
          .APPROVED,
      ),

    rejected:
      count(
        PAPER_LEARNING_STATUS
          .REJECTED,
      ),

    applied:
      count(
        PAPER_LEARNING_STATUS
          .APPLIED,
      ),
  };
}

export const PaperLearningQueueInternals = {
  clone,
  createId,
};