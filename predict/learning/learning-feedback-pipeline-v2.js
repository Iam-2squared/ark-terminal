export const LEARNING_FEEDBACK_PIPELINE_V2_VERSION =
  "learning-feedback-pipeline-v2";

function finiteOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function clamp(
  value,
  minimum = 0,
  maximum = 100,
) {
  const number =
    finiteOrNull(value);

  if (number === null) {
    return null;
  }

  return Math.min(
    maximum,
    Math.max(
      minimum,
      number,
    ),
  );
}

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

function normalizeSymbol(value) {
  return normalizeText(
    value,
    "UNKNOWN",
  ).toUpperCase();
}

function normalizeDirection(value) {
  if (typeof value === "number") {
    if (value > 0) {
      return "BUY";
    }

    if (value < 0) {
      return "SELL";
    }

    return "NEUTRAL";
  }

  const text =
    normalizeText(
      value,
      "NEUTRAL",
    ).toUpperCase();

  if (
    [
      "BUY",
      "LONG",
      "BULLISH",
      "UP",
      "1",
    ].includes(text)
  ) {
    return "BUY";
  }

  if (
    [
      "SELL",
      "SHORT",
      "BEARISH",
      "DOWN",
      "-1",
    ].includes(text)
  ) {
    return "SELL";
  }

  return "NEUTRAL";
}

function normalizeTimestamp(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const parsed =
    typeof value === "number"
      ? value
      : Date.parse(value);

  return Number.isFinite(parsed)
    ? parsed
    : null;
}

function isoOrNull(value) {
  const timestamp =
    normalizeTimestamp(value);

  return timestamp === null
    ? null
    : new Date(
        timestamp,
      ).toISOString();
}

function normalizeRegime(value) {
  return normalizeText(
    value,
    "UNKNOWN",
  )
    .toUpperCase()
    .replaceAll(
      "-",
      "_",
    )
    .replaceAll(
      " ",
      "_",
    );
}

function normalizePrediction(
  prediction,
  index,
) {
  if (
    !prediction ||
    typeof prediction !== "object" ||
    Array.isArray(prediction)
  ) {
    return null;
  }

  const generatedAt =
    normalizeTimestamp(
      prediction.generatedAt ??
      prediction.timestamp ??
      prediction.createdAt,
    );

  const horizon =
    Math.max(
      1,
      Math.floor(
        finiteOrNull(
          prediction.horizon ??
          prediction.predictionHorizon ??
          1,
        ) ?? 1,
      ),
    );

  const symbol =
    normalizeSymbol(
      prediction.symbol ??
      prediction.code ??
      prediction.ticker,
    );

  const modelId =
    normalizeText(
      prediction.modelId ??
      prediction.model ??
      prediction.engine,
      "default-model",
    );

  const direction =
    normalizeDirection(
      prediction.direction ??
      prediction.signal ??
      prediction.recommendation
        ?.action,
    );

  const confidence =
    clamp(
      prediction.confidence ??
      prediction.probability ??
      prediction.recommendation
        ?.confidence ??
      50,
    ) ?? 50;

  const score =
    clamp(
      prediction.score ??
      prediction.aiScore ??
      confidence,
    ) ?? confidence;

  const referencePrice =
    finiteOrNull(
      prediction.referencePrice ??
      prediction.price ??
      prediction.entryPrice ??
      prediction.close,
    );

  const id =
    normalizeText(
      prediction.id ??
      prediction.predictionId,
      [
        modelId,
        symbol,
        generatedAt ?? index,
        horizon,
      ].join(":"),
    );

  return {
    id,
    symbol,
    modelId,

    modelVersion:
      normalizeText(
        prediction.modelVersion ??
        prediction.version,
        "unknown",
      ),

    family:
      normalizeText(
        prediction.family ??
        prediction.modelFamily,
        "GENERAL",
      ).toUpperCase(),

    direction,
    confidence,
    score,
    referencePrice,

    generatedAt,
    generatedAtIso:
      generatedAt === null
        ? null
        : new Date(
            generatedAt,
          ).toISOString(),

    horizon,

    regime:
      normalizeRegime(
        prediction.regime ??
        prediction.marketRegime,
      ),

    features:
      prediction.features &&
      typeof prediction.features === "object" &&
      !Array.isArray(
        prediction.features,
      )
        ? {
            ...prediction.features,
          }
        : {},

    metadata:
      prediction.metadata &&
      typeof prediction.metadata === "object" &&
      !Array.isArray(
        prediction.metadata,
      )
        ? {
            ...prediction.metadata,
          }
        : {},
  };
}

function normalizeOutcome(
  outcome,
  index,
) {
  if (
    !outcome ||
    typeof outcome !== "object" ||
    Array.isArray(outcome)
  ) {
    return null;
  }

  const observedAt =
    normalizeTimestamp(
      outcome.observedAt ??
      outcome.timestamp ??
      outcome.date ??
      outcome.createdAt,
    );

  const symbol =
    normalizeSymbol(
      outcome.symbol ??
      outcome.code ??
      outcome.ticker,
    );

  return {
    id:
      normalizeText(
        outcome.id ??
        outcome.outcomeId,
        [
          symbol,
          observedAt ?? index,
        ].join(":"),
      ),

    symbol,

    predictionId:
      normalizeText(
        outcome.predictionId,
        "",
      ),

    observedAt,

    observedAtIso:
      observedAt === null
        ? null
        : new Date(
            observedAt,
          ).toISOString(),

    referencePrice:
      finiteOrNull(
        outcome.referencePrice ??
        outcome.entryPrice ??
        outcome.startPrice,
      ),

    realizedPrice:
      finiteOrNull(
        outcome.realizedPrice ??
        outcome.exitPrice ??
        outcome.endPrice ??
        outcome.close,
      ),

    realizedReturn:
      finiteOrNull(
        outcome.realizedReturn ??
        outcome.actualReturn ??
        outcome.returnPercent ??
        outcome.pnlPercent,
      ),

    transactionCostPercent:
      Math.max(
        0,
        finiteOrNull(
          outcome.transactionCostPercent ??
          outcome.costPercent ??
          outcome.feesPercent,
        ) ?? 0,
      ),

    metadata:
      outcome.metadata &&
      typeof outcome.metadata === "object" &&
      !Array.isArray(
        outcome.metadata,
      )
        ? {
            ...outcome.metadata,
          }
        : {},
  };
}

function calculateReturn({
  prediction,
  outcome,
}) {
  if (
    outcome.realizedReturn !==
    null
  ) {
    return outcome.realizedReturn;
  }

  const startPrice =
    outcome.referencePrice ??
    prediction.referencePrice;

  const endPrice =
    outcome.realizedPrice;

  if (
    startPrice === null ||
    endPrice === null ||
    startPrice <= 0
  ) {
    return null;
  }

  return (
    (
      endPrice -
      startPrice
    ) /
    startPrice
  ) *
  100;
}

function findOutcome({
  prediction,
  outcomes,
  horizonMilliseconds,
  maximumDelayMilliseconds,
}) {
  const direct =
    outcomes.find(
      (
        outcome,
      ) =>
        outcome.predictionId &&
        outcome.predictionId ===
          prediction.id,
    );

  if (direct) {
    return direct;
  }

  if (
    prediction.generatedAt ===
    null
  ) {
    return null;
  }

  const targetTime =
    prediction.generatedAt +
    horizonMilliseconds;

  return outcomes
    .filter(
      (
        outcome,
      ) =>
        outcome.symbol ===
          prediction.symbol &&
        outcome.observedAt !==
          null &&
        outcome.observedAt >=
          targetTime &&
        outcome.observedAt <=
          targetTime +
          maximumDelayMilliseconds,
    )
    .sort(
      (
        left,
        right,
      ) =>
        Math.abs(
          left.observedAt -
          targetTime,
        ) -
        Math.abs(
          right.observedAt -
          targetTime,
        ),
    )[0] ?? null;
}

function createLearningRecord({
  prediction,
  outcome,
  actualReturn,
}) {
  return {
    id:
      `feedback:${prediction.id}`,

    symbol:
      prediction.symbol,

    modelId:
      prediction.modelId,

    modelVersion:
      prediction.modelVersion,

    family:
      prediction.family,

    regime:
      prediction.regime,

    horizon:
      prediction.horizon,

    prediction: {
      direction:
        prediction.direction,

      confidence:
        prediction.confidence,

      score:
        prediction.score,
    },

    actualReturn,

    transactionCostPercent:
      outcome.transactionCostPercent,

    timestamp:
      prediction.generatedAtIso,

    resolvedAt:
      outcome.observedAtIso,

    features: {
      ...prediction.features,
    },

    metadata: {
      ...prediction.metadata,

      feedbackPipelineVersion:
        LEARNING_FEEDBACK_PIPELINE_V2_VERSION,

      predictionId:
        prediction.id,

      outcomeId:
        outcome.id,

      referencePrice:
        outcome.referencePrice ??
        prediction.referencePrice,

      realizedPrice:
        outcome.realizedPrice,
    },
  };
}

export function buildLearningFeedback({
  predictions = [],
  outcomes = [],
  existingRecordIds = [],
  horizonUnitMilliseconds = 86400000,
  maximumDelayMilliseconds = 86400000,
  now = Date.now(),
  rejectFutureOutcomes = true,
} = {}) {
  if (!Array.isArray(predictions)) {
    throw new TypeError(
      "Learning feedback predictions must be an array.",
    );
  }

  if (!Array.isArray(outcomes)) {
    throw new TypeError(
      "Learning feedback outcomes must be an array.",
    );
  }

  if (!Array.isArray(existingRecordIds)) {
    throw new TypeError(
      "Learning feedback existingRecordIds must be an array.",
    );
  }

  const normalizedNow =
    normalizeTimestamp(now);

  if (normalizedNow === null) {
    throw new TypeError(
      "Learning feedback now value is invalid.",
    );
  }

  const normalizedPredictions =
    predictions
      .map(
        (
          prediction,
          index,
        ) =>
          normalizePrediction(
            prediction,
            index,
          ),
      )
      .filter(Boolean);

  const normalizedOutcomes =
    outcomes
      .map(
        (
          outcome,
          index,
        ) =>
          normalizeOutcome(
            outcome,
            index,
          ),
      )
      .filter(Boolean);

  const knownIds =
    new Set(
      existingRecordIds.map(
        String,
      ),
    );

  const records = [];
  const rejected = [];
  const pending = [];
  const seenPredictionIds =
    new Set();

  for (
    const prediction
    of normalizedPredictions
  ) {
    const recordId =
      `feedback:${prediction.id}`;

    if (
      seenPredictionIds.has(
        prediction.id,
      ) ||
      knownIds.has(
        recordId,
      )
    ) {
      rejected.push({
        predictionId:
          prediction.id,

        code:
          "DUPLICATE_FEEDBACK",
      });

      continue;
    }

    seenPredictionIds.add(
      prediction.id,
    );

    if (
      prediction.direction ===
      "NEUTRAL"
    ) {
      rejected.push({
        predictionId:
          prediction.id,

        code:
          "NEUTRAL_PREDICTION",
      });

      continue;
    }

    if (
      prediction.generatedAt ===
      null
    ) {
      rejected.push({
        predictionId:
          prediction.id,

        code:
          "INVALID_PREDICTION_TIMESTAMP",
      });

      continue;
    }

    if (
      prediction.generatedAt >
      normalizedNow
    ) {
      rejected.push({
        predictionId:
          prediction.id,

        code:
          "FUTURE_PREDICTION",
      });

      continue;
    }

    const horizonMilliseconds =
      prediction.horizon *
      Math.max(
        1,
        finiteOrNull(
          horizonUnitMilliseconds,
        ) ?? 86400000,
      );

    const targetTime =
      prediction.generatedAt +
      horizonMilliseconds;

    if (
      targetTime >
      normalizedNow
    ) {
      pending.push({
        predictionId:
          prediction.id,

        symbol:
          prediction.symbol,

        targetTime:
          new Date(
            targetTime,
          ).toISOString(),

        code:
          "HORIZON_NOT_COMPLETE",
      });

      continue;
    }

    const outcome =
      findOutcome({
        prediction,

        outcomes:
          normalizedOutcomes,

        horizonMilliseconds,

        maximumDelayMilliseconds:
          Math.max(
            0,
            finiteOrNull(
              maximumDelayMilliseconds,
            ) ?? 86400000,
          ),
      });

    if (!outcome) {
      pending.push({
        predictionId:
          prediction.id,

        symbol:
          prediction.symbol,

        targetTime:
          new Date(
            targetTime,
          ).toISOString(),

        code:
          "OUTCOME_NOT_AVAILABLE",
      });

      continue;
    }

    if (
      rejectFutureOutcomes &&
      outcome.observedAt !==
        null &&
      outcome.observedAt >
        normalizedNow
    ) {
      rejected.push({
        predictionId:
          prediction.id,

        outcomeId:
          outcome.id,

        code:
          "FUTURE_OUTCOME",
      });

      continue;
    }

    if (
      outcome.observedAt !==
        null &&
      outcome.observedAt <
        targetTime
    ) {
      rejected.push({
        predictionId:
          prediction.id,

        outcomeId:
          outcome.id,

        code:
          "PREMATURE_OUTCOME",
      });

      continue;
    }

    const actualReturn =
      calculateReturn({
        prediction,
        outcome,
      });

    if (actualReturn === null) {
      rejected.push({
        predictionId:
          prediction.id,

        outcomeId:
          outcome.id,

        code:
          "RETURN_NOT_CALCULABLE",
      });

      continue;
    }

    records.push(
      createLearningRecord({
        prediction,
        outcome,
        actualReturn,
      }),
    );

    knownIds.add(
      recordId,
    );
  }

  return {
    version:
      LEARNING_FEEDBACK_PIPELINE_V2_VERSION,

    ready:
      records.length > 0,

    records,

    pending,

    rejected,

    summary: {
      predictionCount:
        normalizedPredictions.length,

      outcomeCount:
        normalizedOutcomes.length,

      createdCount:
        records.length,

      pendingCount:
        pending.length,

      rejectedCount:
        rejected.length,

      duplicateCount:
        rejected.filter(
          (
            item,
          ) =>
            item.code ===
            "DUPLICATE_FEEDBACK",
        ).length,
    },

    audit: {
      generatedAt:
        new Date(
          normalizedNow,
        ).toISOString(),

      rejectFutureOutcomes:
        rejectFutureOutcomes ===
        true,

      horizonUnitMilliseconds:
        Math.max(
          1,
          finiteOrNull(
            horizonUnitMilliseconds,
          ) ?? 86400000,
        ),

      maximumDelayMilliseconds:
        Math.max(
          0,
          finiteOrNull(
            maximumDelayMilliseconds,
          ) ?? 86400000,
        ),
    },
  };
}

export function mergeLearningFeedback({
  existingRecords = [],
  feedback,
} = {}) {
  if (!Array.isArray(existingRecords)) {
    throw new TypeError(
      "Existing learning records must be an array.",
    );
  }

  const incoming =
    Array.isArray(
      feedback?.records,
    )
      ? feedback.records
      : [];

  const recordsById =
    new Map();

  for (
    const record
    of [
      ...existingRecords,
      ...incoming,
    ]
  ) {
    if (
      !record ||
      typeof record !== "object"
    ) {
      continue;
    }

    const id =
      normalizeText(
        record.id,
        "",
      );

    if (!id) {
      continue;
    }

    if (!recordsById.has(id)) {
      recordsById.set(
        id,
        {
          ...record,
        },
      );
    }
  }

  return {
    version:
      LEARNING_FEEDBACK_PIPELINE_V2_VERSION,

    records:
      Array.from(
        recordsById.values(),
      ),

    addedCount:
      Math.max(
        0,
        recordsById.size -
        existingRecords.length,
      ),

    totalCount:
      recordsById.size,
  };
}

export class LearningFeedbackPipelineV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.records = [];
  }

  process(input = {}) {
    const result =
      buildLearningFeedback({
        ...this.config,
        ...input,

        existingRecordIds: [
          ...new Set([
            ...(
              this.config
                .existingRecordIds ??
              []
            ),

            ...this.records.map(
              (
                record,
              ) =>
                record.id,
            ),
          ]),
        ],
      });

    this.records =
      mergeLearningFeedback({
        existingRecords:
          this.records,

        feedback:
          result,
      }).records;

    return result;
  }

  getRecords() {
    return this.records.map(
      (
        record,
      ) => ({
        ...record,
      }),
    );
  }

  reset() {
    this.records = [];

    return [];
  }
}

export const learningFeedbackPipelineV2 =
  new LearningFeedbackPipelineV2();

export default buildLearningFeedback;