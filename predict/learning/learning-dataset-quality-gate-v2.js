export const LEARNING_DATASET_QUALITY_GATE_V2_VERSION =
  "learning-dataset-quality-gate-v2";

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

function normalizeTimestamp(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const timestamp =
    typeof value === "number"
      ? value
      : Date.parse(value);

  return Number.isFinite(timestamp)
    ? timestamp
    : null;
}

function normalizeDirection(value) {
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

function normalizeRecord(
  record,
  index,
) {
  if (
    !record ||
    typeof record !== "object" ||
    Array.isArray(record)
  ) {
    return null;
  }

  const prediction =
    record.prediction &&
    typeof record.prediction === "object"
      ? record.prediction
      : {};

  const timestamp =
    normalizeTimestamp(
      record.timestamp ??
      record.generatedAt ??
      record.createdAt,
    );

  const resolvedAt =
    normalizeTimestamp(
      record.resolvedAt ??
      record.observedAt ??
      record.outcomeTimestamp,
    );

  const direction =
    normalizeDirection(
      prediction.direction ??
      record.predictedDirection ??
      record.direction,
    );

  const confidence =
    clamp(
      prediction.confidence ??
      record.confidence,
    );

  const score =
    clamp(
      prediction.score ??
      record.score ??
      record.aiScore,
    );

  const actualReturn =
    finiteOrNull(
      record.actualReturn ??
      record.realizedReturn ??
      record.returnPercent ??
      record.pnlPercent,
    );

  const transactionCostPercent =
    Math.max(
      0,
      finiteOrNull(
        record.transactionCostPercent ??
        record.costPercent ??
        record.feesPercent,
      ) ?? 0,
    );

  return {
    original:
      record,

    index,

    id:
      normalizeText(
        record.id,
        `record-${index}`,
      ),

    symbol:
      normalizeText(
        record.symbol ??
        record.code ??
        record.ticker,
        "UNKNOWN",
      ).toUpperCase(),

    modelId:
      normalizeText(
        record.modelId ??
        record.model,
        "default-model",
      ),

    modelVersion:
      normalizeText(
        record.modelVersion ??
        record.version,
        "unknown",
      ),

    regime:
      normalizeText(
        record.regime ??
        record.marketRegime,
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
        ),

    horizon:
      Math.max(
        1,
        Math.floor(
          finiteOrNull(
            record.horizon ??
            record.predictionHorizon,
          ) ?? 1,
        ),
      ),

    direction,

    confidence,

    score,

    actualReturn,

    transactionCostPercent,

    timestamp,

    resolvedAt,

    features:
      record.features &&
      typeof record.features === "object" &&
      !Array.isArray(record.features)
        ? {
            ...record.features,
          }
        : {},

    metadata:
      record.metadata &&
      typeof record.metadata === "object" &&
      !Array.isArray(record.metadata)
        ? {
            ...record.metadata,
          }
        : {},
  };
}

function createIssue({
  severity,
  code,
  message,
  recordId = null,
  field = null,
  value = null,
}) {
  return {
    severity,
    code,
    message,
    recordId,
    field,
    value,
  };
}

function validateRecord({
  record,
  now,
  maximumAbsoluteReturn,
  maximumTransactionCostPercent,
  minimumConfidence,
  maximumConfidence,
  minimumScore,
  maximumScore,
  requireResolvedTimestamp,
  rejectNeutralDirection,
}) {
  const issues = [];

  if (!record.id) {
    issues.push(
      createIssue({
        severity:
          "ERROR",

        code:
          "MISSING_ID",

        message:
          "Learning record id is missing.",
      }),
    );
  }

  if (
    !record.symbol ||
    record.symbol ===
      "UNKNOWN"
  ) {
    issues.push(
      createIssue({
        severity:
          "ERROR",

        code:
          "MISSING_SYMBOL",

        message:
          "Learning record symbol is missing.",

        recordId:
          record.id,
      }),
    );
  }

  if (
    record.timestamp ===
    null
  ) {
    issues.push(
      createIssue({
        severity:
          "ERROR",

        code:
          "INVALID_TIMESTAMP",

        message:
          "Prediction timestamp is invalid.",

        recordId:
          record.id,

        field:
          "timestamp",
      }),
    );
  }

  if (
    record.timestamp !==
      null &&
    record.timestamp >
      now
  ) {
    issues.push(
      createIssue({
        severity:
          "CRITICAL",

        code:
          "FUTURE_PREDICTION_TIMESTAMP",

        message:
          "Prediction timestamp is in the future.",

        recordId:
          record.id,

        field:
          "timestamp",

        value:
          record.timestamp,
      }),
    );
  }

  if (
    requireResolvedTimestamp &&
    record.resolvedAt ===
      null
  ) {
    issues.push(
      createIssue({
        severity:
          "ERROR",

        code:
          "MISSING_RESOLVED_TIMESTAMP",

        message:
          "Resolved timestamp is required.",

        recordId:
          record.id,

        field:
          "resolvedAt",
      }),
    );
  }

  if (
    record.resolvedAt !==
      null &&
    record.resolvedAt >
      now
  ) {
    issues.push(
      createIssue({
        severity:
          "CRITICAL",

        code:
          "FUTURE_OUTCOME_TIMESTAMP",

        message:
          "Outcome timestamp is in the future.",

        recordId:
          record.id,

        field:
          "resolvedAt",

        value:
          record.resolvedAt,
      }),
    );
  }

  if (
    record.timestamp !==
      null &&
    record.resolvedAt !==
      null &&
    record.resolvedAt <
      record.timestamp
  ) {
    issues.push(
      createIssue({
        severity:
          "CRITICAL",

        code:
          "OUTCOME_BEFORE_PREDICTION",

        message:
          "Outcome timestamp occurs before prediction timestamp.",

        recordId:
          record.id,
      }),
    );
  }

  if (
    rejectNeutralDirection &&
    record.direction ===
      "NEUTRAL"
  ) {
    issues.push(
      createIssue({
        severity:
          "ERROR",

        code:
          "NEUTRAL_DIRECTION",

        message:
          "Neutral predictions are not eligible for supervised learning.",

        recordId:
          record.id,

        field:
          "direction",

        value:
          record.direction,
      }),
    );
  }

  if (
    record.confidence ===
      null ||
    record.confidence <
      minimumConfidence ||
    record.confidence >
      maximumConfidence
  ) {
    issues.push(
      createIssue({
        severity:
          "ERROR",

        code:
          "INVALID_CONFIDENCE",

        message:
          "Prediction confidence is outside the allowed range.",

        recordId:
          record.id,

        field:
          "confidence",

        value:
          record.confidence,
      }),
    );
  }

  if (
    record.score ===
      null ||
    record.score <
      minimumScore ||
    record.score >
      maximumScore
  ) {
    issues.push(
      createIssue({
        severity:
          "ERROR",

        code:
          "INVALID_SCORE",

        message:
          "Prediction score is outside the allowed range.",

        recordId:
          record.id,

        field:
          "score",

        value:
          record.score,
      }),
    );
  }

  if (
    record.actualReturn ===
      null
  ) {
    issues.push(
      createIssue({
        severity:
          "ERROR",

        code:
          "MISSING_ACTUAL_RETURN",

        message:
          "Actual return is required for learning.",

        recordId:
          record.id,

        field:
          "actualReturn",
      }),
    );
  }
  else if (
    Math.abs(
      record.actualReturn,
    ) >
    maximumAbsoluteReturn
  ) {
    issues.push(
      createIssue({
        severity:
          "ERROR",

        code:
          "EXTREME_RETURN",

        message:
          "Actual return exceeds the configured limit.",

        recordId:
          record.id,

        field:
          "actualReturn",

        value:
          record.actualReturn,
      }),
    );
  }

  if (
    record.transactionCostPercent >
    maximumTransactionCostPercent
  ) {
    issues.push(
      createIssue({
        severity:
          "WARNING",

        code:
          "HIGH_TRANSACTION_COST",

        message:
          "Transaction cost exceeds the preferred limit.",

        recordId:
          record.id,

        field:
          "transactionCostPercent",

        value:
          record.transactionCostPercent,
      }),
    );
  }

  for (
    const [
      featureName,
      featureValue,
    ]
    of Object.entries(
      record.features,
    )
  ) {
    if (
      featureValue === null ||
      featureValue ===
        undefined
    ) {
      continue;
    }

    if (
      !Number.isFinite(
        Number(featureValue),
      )
    ) {
      issues.push(
        createIssue({
          severity:
            "WARNING",

          code:
            "INVALID_FEATURE_VALUE",

          message:
            "Feature value is not numeric.",

          recordId:
            record.id,

          field:
            `features.${featureName}`,

          value:
            featureValue,
        }),
      );
    }
  }

  return issues;
}

function calculateDistribution(
  records,
  selector,
) {
  const distribution = {};

  for (const record of records) {
    const key =
      String(
        selector(record),
      );

    distribution[key] =
      (
        distribution[key] ??
        0
      ) +
      1;
  }

  return distribution;
}

function calculateLargestShare(
  distribution,
  total,
) {
  if (total <= 0) {
    return 0;
  }

  const counts =
    Object.values(
      distribution,
    );

  if (!counts.length) {
    return 0;
  }

  return (
    Math.max(
      ...counts,
    ) /
    total
  ) *
  100;
}

export function evaluateLearningDatasetQuality({
  records = [],
  now = Date.now(),
  minimumSamples = 5,
  maximumAbsoluteReturn = 100,
  maximumTransactionCostPercent = 10,
  minimumConfidence = 0,
  maximumConfidence = 100,
  minimumScore = 0,
  maximumScore = 100,
  maximumSingleSymbolSharePercent = 80,
  maximumSingleRegimeSharePercent = 90,
  requireResolvedTimestamp = true,
  rejectNeutralDirection = true,
  rejectWarnings = false,
} = {}) {
  if (!Array.isArray(records)) {
    throw new TypeError(
      "Learning dataset records must be an array.",
    );
  }

  const normalizedNow =
    normalizeTimestamp(now);

  if (normalizedNow === null) {
    throw new TypeError(
      "Learning dataset quality gate now value is invalid.",
    );
  }

  const normalizedRecords =
    records
      .map(
        (
          record,
          index,
        ) =>
          normalizeRecord(
            record,
            index,
          ),
      )
      .filter(Boolean);

  const issues = [];
  const duplicateIds =
    new Set();

  const seenIds =
    new Set();

  for (
    const record
    of normalizedRecords
  ) {
    if (
      seenIds.has(
        record.id,
      )
    ) {
      duplicateIds.add(
        record.id,
      );

      issues.push(
        createIssue({
          severity:
            "CRITICAL",

          code:
            "DUPLICATE_RECORD_ID",

          message:
            "Duplicate learning record id detected.",

          recordId:
            record.id,
        }),
      );
    }
    else {
      seenIds.add(
        record.id,
      );
    }

    issues.push(
      ...validateRecord({
        record,
        now:
          normalizedNow,

        maximumAbsoluteReturn:
          Math.max(
            0,
            finiteOrNull(
              maximumAbsoluteReturn,
            ) ?? 100,
          ),

        maximumTransactionCostPercent:
          Math.max(
            0,
            finiteOrNull(
              maximumTransactionCostPercent,
            ) ?? 10,
          ),

        minimumConfidence:
          finiteOrNull(
            minimumConfidence,
          ) ?? 0,

        maximumConfidence:
          finiteOrNull(
            maximumConfidence,
          ) ?? 100,

        minimumScore:
          finiteOrNull(
            minimumScore,
          ) ?? 0,

        maximumScore:
          finiteOrNull(
            maximumScore,
          ) ?? 100,

        requireResolvedTimestamp:
          requireResolvedTimestamp ===
          true,

        rejectNeutralDirection:
          rejectNeutralDirection ===
          true,
      }),
    );
  }

  const symbolDistribution =
    calculateDistribution(
      normalizedRecords,
      (
        record,
      ) =>
        record.symbol,
    );

  const regimeDistribution =
    calculateDistribution(
      normalizedRecords,
      (
        record,
      ) =>
        record.regime,
    );

  const directionDistribution =
    calculateDistribution(
      normalizedRecords,
      (
        record,
      ) =>
        record.direction,
    );

  const symbolConcentration =
    calculateLargestShare(
      symbolDistribution,
      normalizedRecords.length,
    );

  const regimeConcentration =
    calculateLargestShare(
      regimeDistribution,
      normalizedRecords.length,
    );

  if (
    normalizedRecords.length <
    minimumSamples
  ) {
    issues.push(
      createIssue({
        severity:
          "WARNING",

        code:
          "INSUFFICIENT_SAMPLE_COUNT",

        message:
          "Dataset contains fewer samples than recommended.",

        value:
          normalizedRecords.length,
      }),
    );
  }

  if (
    symbolConcentration >
    maximumSingleSymbolSharePercent
  ) {
    issues.push(
      createIssue({
        severity:
          "WARNING",

        code:
          "SYMBOL_CONCENTRATION",

        message:
          "A single symbol dominates the learning dataset.",

        value:
          symbolConcentration,
      }),
    );
  }

  if (
    regimeConcentration >
    maximumSingleRegimeSharePercent
  ) {
    issues.push(
      createIssue({
        severity:
          "WARNING",

        code:
          "REGIME_CONCENTRATION",

        message:
          "A single market regime dominates the learning dataset.",

        value:
          regimeConcentration,
      }),
    );
  }

  const rejectedIds =
    new Set(
      issues
        .filter(
          (
            issue,
          ) =>
            [
              "ERROR",
              "CRITICAL",
            ].includes(
              issue.severity,
            ) ||
            (
              rejectWarnings &&
              issue.severity ===
                "WARNING"
            ),
        )
        .map(
          (
            issue,
          ) =>
            issue.recordId,
        )
        .filter(Boolean),
    );

  for (
    const duplicateId
    of duplicateIds
  ) {
    rejectedIds.add(
      duplicateId,
    );
  }

  const acceptedRecords =
    normalizedRecords
      .filter(
        (
          record,
        ) =>
          !rejectedIds.has(
            record.id,
          ),
      )
      .map(
        (
          record,
        ) =>
          record.original,
      );

  const rejectedRecords =
    normalizedRecords
      .filter(
        (
          record,
        ) =>
          rejectedIds.has(
            record.id,
          ),
      )
      .map(
        (
          record,
        ) => ({
          record:
            record.original,

          recordId:
            record.id,

          issues:
            issues.filter(
              (
                issue,
              ) =>
                issue.recordId ===
                record.id,
            ),
        }),
      );

  const criticalCount =
    issues.filter(
      (
        issue,
      ) =>
        issue.severity ===
        "CRITICAL",
    ).length;

  const errorCount =
    issues.filter(
      (
        issue,
      ) =>
        issue.severity ===
        "ERROR",
    ).length;

  const warningCount =
    issues.filter(
      (
        issue,
      ) =>
        issue.severity ===
        "WARNING",
    ).length;

  const qualityScore =
    Math.max(
      0,
      Math.min(
        100,
        100 -
        criticalCount *
          25 -
        errorCount *
          10 -
        warningCount *
          3,
      ),
    );

  const passed =
    acceptedRecords.length > 0 &&
    criticalCount === 0 &&
    errorCount === 0 &&
    (
      !rejectWarnings ||
      warningCount === 0
    );

  return {
    version:
      LEARNING_DATASET_QUALITY_GATE_V2_VERSION,

    ready:
      normalizedRecords.length > 0,

    passed,

    qualityScore,

    acceptedRecords,

    rejectedRecords,

    issues,

    summary: {
      inputCount:
        records.length,

      normalizedCount:
        normalizedRecords.length,

      acceptedCount:
        acceptedRecords.length,

      rejectedCount:
        rejectedRecords.length,

      criticalCount,

      errorCount,

      warningCount,

      duplicateCount:
        duplicateIds.size,

      symbolCount:
        Object.keys(
          symbolDistribution,
        ).length,

      regimeCount:
        Object.keys(
          regimeDistribution,
        ).length,

      directionCount:
        Object.keys(
          directionDistribution,
        ).length,

      symbolConcentrationPercent:
        symbolConcentration,

      regimeConcentrationPercent:
        regimeConcentration,
    },

    distributions: {
      symbols:
        symbolDistribution,

      regimes:
        regimeDistribution,

      directions:
        directionDistribution,
    },

    audit: {
      evaluatedAt:
        new Date(
          normalizedNow,
        ).toISOString(),

      rejectWarnings:
        rejectWarnings ===
        true,

      requireResolvedTimestamp:
        requireResolvedTimestamp ===
        true,

      rejectNeutralDirection:
        rejectNeutralDirection ===
        true,
    },
  };
}

export function assertLearningDatasetQuality(
  result,
) {
  if (
    !result ||
    typeof result !== "object"
  ) {
    throw new TypeError(
      "Learning dataset quality result is required.",
    );
  }

  if (!result.passed) {
    const error =
      new Error(
        "Learning dataset quality gate failed.",
      );

    error.code =
      "LEARNING_DATASET_QUALITY_FAILED";

    error.issues =
      result.issues ??
      [];

    throw error;
  }

  return result.acceptedRecords;
}

export class LearningDatasetQualityGateV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  evaluate(input = {}) {
    return evaluateLearningDatasetQuality({
      ...this.config,
      ...input,
    });
  }

  assert(input = {}) {
    const result =
      this.evaluate(input);

    return assertLearningDatasetQuality(
      result,
    );
  }
}

export const learningDatasetQualityGateV2 =
  new LearningDatasetQualityGateV2();

export default evaluateLearningDatasetQuality;