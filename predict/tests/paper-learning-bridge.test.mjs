import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperLearningBridge,
} from "../paper/paper-learning-bridge.js";

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
        "bridge-trade-" +
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

function createDashboardController(
  tradeCount = 0,
) {
  const account = {
    accountId:
      "paper-test",

    initialCash:
      1_000_000,

    tradeHistory:
      createTrades(
        tradeCount,
      ),
  };

  return {
    getBroker() {
      return {
        account:
          structuredClone(
            account,
          ),
      };
    },

    getSnapshot() {
      return {
        accountId:
          account.accountId,
      };
    },
  };
}

test(
  "Paper実績を分析",
  () => {
    const bridge =
      createPaperLearningBridge({
        dashboardController:
          createDashboardController(
            10,
          ),
      });

    const feedback =
      bridge.analyze();

    assert.equal(
      feedback.sampleCount,
      10,
    );

    assert.equal(
      feedback
        .eligibleForLearning,
      true,
    );
  },
);

test(
  "十分な実績を承認待ちQueueへ追加",
  () => {
    const bridge =
      createPaperLearningBridge({
        dashboardController:
          createDashboardController(
            10,
          ),
      });

    const result =
      bridge.enqueue({
        itemId:
          "bridge-feedback-1",
      });

    assert.equal(
      result.enqueue.added,
      true,
    );

    assert.equal(
      bridge
        .getSummary()
        .pending,
      1,
    );
  },
);

test(
  "実績不足はQueueへ追加しない",
  () => {
    const bridge =
      createPaperLearningBridge({
        dashboardController:
          createDashboardController(
            5,
          ),
      });

    const result =
      bridge.enqueue({
        itemId:
          "bridge-small",
      });

    assert.equal(
      result.enqueue.added,
      false,
    );

    assert.equal(
      result.enqueue.reason,
      "insufficient_samples",
    );
  },
);

test(
  "人間承認後のみProviderへ渡す",
  () => {
    const bridge =
      createPaperLearningBridge({
        dashboardController:
          createDashboardController(
            10,
          ),
      });

    bridge.enqueue({
      itemId:
        "bridge-feedback-2",
    });

    bridge.review({
      itemId:
        "bridge-feedback-2",

      approved:
        true,

      reviewer:
        "owner",
    });

    let received = null;

    const result =
      bridge.apply({
        itemId:
          "bridge-feedback-2",

        applyProvider(
          feedback,
        ) {
          received =
            feedback;

          return {
            accepted:
              true,
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
      bridge
        .getSummary()
        .applied,
      1,
    );
  },
);

test(
  "未承認データは適用不可",
  () => {
    const bridge =
      createPaperLearningBridge({
        dashboardController:
          createDashboardController(
            10,
          ),
      });

    bridge.enqueue({
      itemId:
        "bridge-feedback-3",
    });

    assert.throws(
      () =>
        bridge.apply({
          itemId:
            "bridge-feedback-3",

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