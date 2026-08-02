import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperLearningQueue,
  enqueuePaperLearningFeedback,
  markPaperLearningItemApplied,
  reviewPaperLearningItem,
  summarizePaperLearningQueue,
} from "../paper/paper-learning-queue.js";

function feedback() {
  return {
    generatedAt:
      "2026-08-02T00:00:00.000Z",

    eligibleForLearning:
      true,

    sampleCount:
      10,
  };
}

test(
  "学習候補をQueueへ追加",
  () => {
    const result =
      enqueuePaperLearningFeedback({
        queue:
          createPaperLearningQueue(),

        feedback:
          feedback(),

        itemId:
          "feedback-1",
      });

    assert.equal(
      result.added,
      true,
    );

    assert.equal(
      result.item.status,
      "pending",
    );

    assert.equal(
      result.queue.items.length,
      1,
    );
  },
);

test(
  "重複学習候補を拒否",
  () => {
    let queue =
      createPaperLearningQueue();

    queue =
      enqueuePaperLearningFeedback({
        queue,
        feedback:
          feedback(),
        itemId:
          "feedback-1",
      }).queue;

    const duplicate =
      enqueuePaperLearningFeedback({
        queue,
        feedback:
          feedback(),
        itemId:
          "feedback-1",
      });

    assert.equal(
      duplicate.added,
      false,
    );

    assert.equal(
      duplicate.reason,
      "duplicate",
    );

    assert.equal(
      duplicate.queue.items.length,
      1,
    );
  },
);

test(
  "人間承認後に適用済みへ変更",
  () => {
    let queue =
      enqueuePaperLearningFeedback({
        queue:
          createPaperLearningQueue(),

        feedback:
          feedback(),

        itemId:
          "feedback-2",
      }).queue;

    const reviewed =
      reviewPaperLearningItem({
        queue,
        itemId:
          "feedback-2",

        approved:
          true,

        reviewer:
          "owner",
      });

    assert.equal(
      reviewed.item.status,
      "approved",
    );

    const applied =
      markPaperLearningItemApplied({
        queue:
          reviewed.queue,

        itemId:
          "feedback-2",

        result: {
          accepted:
            true,
        },
      });

    assert.equal(
      applied.item.status,
      "applied",
    );

    assert.equal(
      summarizePaperLearningQueue(
        applied.queue,
      ).applied,
      1,
    );
  },
);