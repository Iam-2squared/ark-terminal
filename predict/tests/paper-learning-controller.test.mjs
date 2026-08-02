import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperLearningController,
} from "../paper/paper-learning-controller.js";

function createTrades(
  count,
) {
  return Array.from(
    {
      length:
        count,
    },
    (
      _,
      index,
    ) => ({
      tradeId:
        "trade-" +
        index,

      symbol:
        index % 2 === 0
          ? "7203.T"
          : "6758.T",

      realizedPnl:
        index % 3 === 0
          ? -1_000
          : 2_000,
    }),
  );
}

test(
  "少数サンプルはQueueへ追加しない",
  () => {
    const controller =
      createPaperLearningController();

    const result =
      controller.generateAndEnqueue({
        account: {
          initialCash:
            1_000_000,

          tradeHistory:
            createTrades(5),
        },

        itemId:
          "small-feedback",
      });

    assert.equal(
      result.feedback
        .eligibleForLearning,
      false,
    );

    assert.equal(
      result.enqueue.added,
      false,
    );

    assert.equal(
      controller
        .getSummary()
        .total,
      0,
    );
  },
);

test(
  "十分なPaper実績を承認待ちへ追加",
  () => {
    const controller =
      createPaperLearningController();

    const result =
      controller.generateAndEnqueue({
        account: {
          initialCash:
            1_000_000,

          tradeHistory:
            createTrades(10),
        },

        itemId:
          "learning-feedback-1",
      });

    assert.equal(
      result.feedback
        .eligibleForLearning,
      true,
    );

    assert.equal(
      result.enqueue.added,
      true,
    );

    assert.equal(
      controller
        .getSummary()
        .pending,
      1,
    );
  },
);

test(
  "未承認の学習候補は適用不可",
  () => {
    const controller =
      createPaperLearningController();

    controller.generateAndEnqueue({
      account: {
        initialCash:
          1_000_000,

        tradeHistory:
          createTrades(10),
      },

      itemId:
        "learning-feedback-2",
    });

    assert.throws(
      () =>
        controller.applyApproved({
          itemId:
            "learning-feedback-2",

          applyProvider() {
            return {
              accepted:
                true,
            };
          },
        }),
      /must be approved/,
    );
  },
);

test(
  "人間承認後のみLearning Providerへ渡す",
  () => {
    const controller =
      createPaperLearningController();

    controller.generateAndEnqueue({
      account: {
        initialCash:
          1_000_000,

        tradeHistory:
          createTrades(10),
      },

      itemId:
        "learning-feedback-3",
    });

    controller.review({
      itemId:
        "learning-feedback-3",

      approved:
        true,

      reviewer:
        "owner",
    });

    let received = null;

    const result =
      controller.applyApproved({
        itemId:
          "learning-feedback-3",

        applyProvider(
          feedback,
        ) {
          received =
            feedback;

          return {
            accepted:
              true,

            sampleCount:
              feedback
                .sampleCount,
          };
        },
      });

    assert.equal(
      received.sampleCount,
      10,
    );

    assert.equal(
      result.item.status,
      "applied",
    );

    assert.equal(
      result.result.accepted,
      true,
    );

    assert.equal(
      controller
        .getSummary()
        .applied,
      1,
    );
  },
);

test(
  "実口座への自動昇格は禁止",
  () => {
    const controller =
      createPaperLearningController();

    assert.equal(
      controller
        .getState()
        .policy
        .automaticLivePromotion,
      false,
    );
  },
);