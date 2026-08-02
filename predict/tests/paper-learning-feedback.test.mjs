import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperLearningFeedback,
  createPaperTradeLearningSample,
} from "../paper/paper-learning-feedback.js";

test(
  "Paper取引を学習サンプルへ変換",
  () => {
    const sample =
      createPaperTradeLearningSample({
        trade: {
          tradeId:
            "trade-1",

          symbol:
            "7203.T",

          side:
            "long",

          quantity:
            100,

          entryPrice:
            2_000,

          exitPrice:
            2_100,

          realizedPnl:
            10_000,

          aiScore:
            78,

          confidence:
            0.74,

          features: {
            rsi: 55,
          },
        },
      });

    assert.equal(
      sample.sampleId,
      "trade-1",
    );

    assert.equal(
      sample.direction,
      "up",
    );

    assert.equal(
      sample.outcome,
      "win",
    );

    assert.equal(
      sample.features.rsi,
      55,
    );
  },
);

test(
  "10件未満は学習対象外",
  () => {
    const feedback =
      createPaperLearningFeedback({
        account: {
          initialCash:
            1_000_000,

          tradeHistory: [
            {
              tradeId:
                "trade-small",
              symbol:
                "7203.T",
              realizedPnl:
                1_000,
            },
          ],
        },
      });

    assert.equal(
      feedback.eligibleForLearning,
      false,
    );

    assert.equal(
      feedback
        .eligibleForPromotionReview,
      false,
    );

    assert.equal(
      feedback.guardrails
        .automaticLivePromotion,
      false,
    );
  },
);

test(
  "十分な件数を学習候補へする",
  () => {
    const trades =
      Array.from(
        {
          length: 10,
        },
        (
          _,
          index,
        ) => ({
          tradeId:
            "trade-" +
            index,

          symbol:
            "7203.T",

          realizedPnl:
            index % 2 === 0
              ? 2_000
              : -1_000,
        }),
      );

    const feedback =
      createPaperLearningFeedback({
        account: {
          initialCash:
            1_000_000,

          tradeHistory:
            trades,
        },
      });

    assert.equal(
      feedback.sampleCount,
      10,
    );

    assert.equal(
      feedback.eligibleForLearning,
      true,
    );

    assert.equal(
      feedback.guardrails
        .requiresHumanApproval,
      true,
    );
  },
);