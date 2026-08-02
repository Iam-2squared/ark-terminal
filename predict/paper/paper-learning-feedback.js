import {
  analyzePaperAiPerformance,
} from "./paper-ai-performance-analyzer.js";

export const PAPER_LEARNING_FEEDBACK_VERSION =
  "paper-learning-feedback-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function normalizeDirection(
  value,
) {
  const direction =
    String(value || "")
      .trim()
      .toLowerCase();

  if (
    [
      "buy",
      "long",
      "bullish",
      "up",
    ].includes(
      direction,
    )
  ) {
    return "up";
  }

  if (
    [
      "sell",
      "short",
      "bearish",
      "down",
    ].includes(
      direction,
    )
  ) {
    return "down";
  }

  return "neutral";
}

function outcomeFromPnl(
  pnl,
) {
  if (!finite(pnl)) {
    return "unknown";
  }

  if (Number(pnl) > 0) {
    return "win";
  }

  if (Number(pnl) < 0) {
    return "loss";
  }

  return "flat";
}

export function createPaperTradeLearningSample({
  trade,
  source =
    "paper-trading",
} = {}) {
  if (!trade) {
    throw new Error(
      "Paper trade is required.",
    );
  }

  if (
    !finite(
      trade.realizedPnl,
    )
  ) {
    throw new Error(
      "Paper trade realizedPnl is required.",
    );
  }

  return {
    version:
      PAPER_LEARNING_FEEDBACK_VERSION,

    source,

    sampleId:
      String(
        trade.tradeId ||
        trade.orderId ||
        (
          "paper-sample-" +
          Date.now()
        ),
      ),

    symbol:
      String(
        trade.symbol ||
        "",
      ).toUpperCase(),

    direction:
      normalizeDirection(
        trade.direction ||
        trade.side,
      ),

    outcome:
      outcomeFromPnl(
        trade.realizedPnl,
      ),

    realizedPnl:
      Number(
        trade.realizedPnl,
      ),

    commission:
      finite(
        trade.commission,
      )
        ? Number(
            trade.commission,
          )
        : 0,

    quantity:
      finite(
        trade.quantity,
      )
        ? Number(
            trade.quantity,
          )
        : null,

    entryPrice:
      finite(
        trade.entryPrice,
      )
        ? Number(
            trade.entryPrice,
          )
        : null,

    exitPrice:
      finite(
        trade.exitPrice,
      )
        ? Number(
            trade.exitPrice,
          )
        : null,

    aiScore:
      finite(
        trade.aiScore,
      )
        ? Number(
            trade.aiScore,
          )
        : null,

    confidence:
      finite(
        trade.confidence,
      )
        ? Number(
            trade.confidence,
          )
        : null,

    modelVersion:
      trade.modelVersion ||
      null,

    features:
      trade.features &&
      typeof trade.features ===
        "object"
        ? structuredClone(
            trade.features,
          )
        : {},

    openedAt:
      trade.openedAt ||
      null,

    closedAt:
      trade.closedAt ||
      null,

    createdAt:
      new Date()
        .toISOString(),
  };
}

export function createPaperLearningFeedback({
  account = {},
  equityHistory = [],
} = {}) {
  const trades =
    Array.isArray(
      account.tradeHistory,
    )
      ? account.tradeHistory
      : [];

  const samples =
    trades
      .filter(
        (trade) =>
          finite(
            trade.realizedPnl,
          ),
      )
      .map(
        (trade) =>
          createPaperTradeLearningSample({
            trade,
          }),
      );

  const performance =
    analyzePaperAiPerformance({
      account,
      equityHistory,
    });

  return {
    version:
      PAPER_LEARNING_FEEDBACK_VERSION,

    generatedAt:
      new Date()
        .toISOString(),

    source:
      "paper-trading",

    eligibleForLearning:
      samples.length >= 10,

    eligibleForPromotionReview:
      (
        samples.length >= 30 &&
        Number(
          performance.metrics
            .profitFactor || 0,
        ) > 1 &&
        Number(
          performance.metrics
            .maximumDrawdownPercent || 0,
        ) < 10
      ),

    sampleCount:
      samples.length,

    samples,

    performance,

    guardrails: {
      minimumLearningSamples:
        10,

      minimumPromotionSamples:
        30,

      requiresHumanApproval:
        true,

      automaticLivePromotion:
        false,
    },
  };
}

export const PaperLearningFeedbackInternals = {
  finite,
  normalizeDirection,
  outcomeFromPnl,
};