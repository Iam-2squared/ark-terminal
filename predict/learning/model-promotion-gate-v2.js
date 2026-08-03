export const MODEL_PROMOTION_GATE_V2_VERSION =
  "model-promotion-gate-v2";

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

function round(
  value,
  digits = 4,
) {
  if (!Number.isFinite(value)) {
    return value;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value * factor,
    ) / factor
  );
}

function normalizeDecision(value) {
  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "PROMOTE",
      "APPROVE",
      "ACCEPT",
    ].includes(text)
  ) {
    return "PROMOTE";
  }

  if (
    [
      "RETRAIN",
      "REJECT",
      "DEMOTE",
    ].includes(text)
  ) {
    return "RETRAIN";
  }

  return "HOLD";
}

function normalizeCandidate(
  candidate = {},
) {
  if (
    !candidate ||
    typeof candidate !== "object" ||
    Array.isArray(candidate)
  ) {
    throw new TypeError(
      "Model promotion candidate must be an object.",
    );
  }

  const id =
    String(
      candidate.id ??
      candidate.modelId ??
      candidate.name ??
      "",
    ).trim();

  if (!id) {
    throw new TypeError(
      "Model promotion candidate requires an id.",
    );
  }

  return {
    id,

    version:
      String(
        candidate.version ??
        "unknown",
      ),

    family:
      String(
        candidate.family ??
        candidate.type ??
        "GENERAL",
      )
        .trim()
        .toUpperCase(),

    status:
      String(
        candidate.status ??
        "CANDIDATE",
      )
        .trim()
        .toUpperCase(),

    metadata:
      candidate.metadata ??
      {},
  };
}

function normalizeBenchmark(
  benchmark = {},
) {
  if (
    !benchmark ||
    typeof benchmark !== "object" ||
    Array.isArray(benchmark)
  ) {
    return {};
  }

  return benchmark;
}

function metricValue(
  object,
  paths,
  fallback = null,
) {
  for (
    const path
    of paths
  ) {
    const segments =
      path.split(".");

    let current =
      object;

    let valid =
      true;

    for (
      const segment
      of segments
    ) {
      if (
        current === null ||
        current === undefined ||
        typeof current !== "object" ||
        !(segment in current)
      ) {
        valid = false;
        break;
      }

      current =
        current[segment];
    }

    if (valid) {
      const number =
        finiteOrNull(
          current,
        );

      if (number !== null) {
        return number;
      }
    }
  }

  return fallback;
}

function normalizeMetrics(
  metrics = {},
) {
  if (
    !metrics ||
    typeof metrics !== "object" ||
    Array.isArray(metrics)
  ) {
    throw new TypeError(
      "Model promotion metrics must be an object.",
    );
  }

  return {
    accuracy:
      metricValue(
        metrics,
        [
          "accuracy",
          "directionalAccuracy",
          "meanAccuracy",
          "aggregate.meanAccuracy",
          "summary.accuracy",
        ],
      ),

    confidenceCalibrationError:
      metricValue(
        metrics,
        [
          "confidenceCalibrationError",
          "calibrationError",
          "summary.calibrationError",
          "ece",
        ],
      ),

    profitFactor:
      metricValue(
        metrics,
        [
          "profitFactor",
          "summary.profitFactor",
          "metrics.profitFactor",
        ],
      ),

    maximumDrawdown:
      metricValue(
        metrics,
        [
          "maximumDrawdown",
          "maxDrawdown",
          "summary.maximumDrawdown",
          "metrics.maximumDrawdown",
        ],
      ),

    averageReturn:
      metricValue(
        metrics,
        [
          "averageReturn",
          "meanReturn",
          "summary.averageReturn",
          "metrics.averageReturn",
        ],
      ),

    sampleCount:
      metricValue(
        metrics,
        [
          "sampleCount",
          "count",
          "recordCount",
          "summary.sampleCount",
        ],
        0,
      ),

    stabilityScore:
      metricValue(
        metrics,
        [
          "stabilityScore",
          "summary.stabilityScore",
          "robustnessScore",
        ],
      ),

    monteCarloSuccessRate:
      metricValue(
        metrics,
        [
          "monteCarloSuccessRate",
          "successRate",
          "summary.successRate",
        ],
      ),
  };
}

function normalizeDrift(
  drift = {},
) {
  if (
    !drift ||
    typeof drift !== "object"
  ) {
    return {
      ready:
        false,

      detected:
        false,

      score:
        0,

      level:
        "UNKNOWN",

      allowPromotion:
        false,
    };
  }

  return {
    ready:
      drift.ready === true,

    detected:
      drift.driftDetected === true,

    score:
      clamp(
        drift.driftScore,
      ) ?? 0,

    level:
      String(
        drift.driftLevel ??
        "UNKNOWN",
      )
        .trim()
        .toUpperCase(),

    allowPromotion:
      drift.recommendation
        ?.allowPromotion === true,
  };
}

function normalizeLearning(
  learning = {},
) {
  if (
    !learning ||
    typeof learning !== "object"
  ) {
    return {
      ready:
        false,

      action:
        "HOLD",

      performanceScore:
        null,

      sampleCount:
        0,
    };
  }

  const action =
    normalizeDecision(
      learning.recommendation
        ?.action ??
      learning.action,
    );

  return {
    ready:
      learning.ready !== false,

    action,

    performanceScore:
      metricValue(
        learning,
        [
          "performanceScore",
          "overall.performanceScore",
          "summary.performanceScore",
        ],
      ),

    sampleCount:
      metricValue(
        learning,
        [
          "sampleCount",
          "overall.sampleCount",
          "recordCount",
        ],
        0,
      ),
  };
}

function calculateImprovement(
  candidateValue,
  benchmarkValue,
  higherIsBetter = true,
) {
  if (
    candidateValue === null ||
    benchmarkValue === null
  ) {
    return null;
  }

  if (
    Math.abs(
      benchmarkValue,
    ) < 0.0000001
  ) {
    return candidateValue -
      benchmarkValue;
  }

  const raw =
    (
      candidateValue -
      benchmarkValue
    ) /
    Math.abs(
      benchmarkValue,
    ) *
    100;

  return higherIsBetter
    ? raw
    : -raw;
}

function buildMetricCheck({
  name,
  value,
  minimum = null,
  maximum = null,
  required = true,
  weight = 1,
}) {
  if (value === null) {
    return {
      name,

      available:
        false,

      passed:
        !required,

      value:
        null,

      minimum,

      maximum,

      weight,

      reason:
        required
          ? "MISSING_REQUIRED_METRIC"
          : "OPTIONAL_METRIC_MISSING",
    };
  }

  const aboveMinimum =
    minimum === null ||
    value >= minimum;

  const belowMaximum =
    maximum === null ||
    value <= maximum;

  return {
    name,

    available:
      true,

    passed:
      aboveMinimum &&
      belowMaximum,

    value:
      round(
        value,
      ),

    minimum,

    maximum,

    weight,

    reason:
      aboveMinimum &&
      belowMaximum
        ? "PASSED"
        : "THRESHOLD_NOT_MET",
  };
}

function weightedPassScore(
  checks,
) {
  const totalWeight =
    checks.reduce(
      (
        sum,
        check,
      ) =>
        sum +
        check.weight,
      0,
    );

  if (totalWeight <= 0) {
    return 0;
  }

  const passedWeight =
    checks.reduce(
      (
        sum,
        check,
      ) =>
        sum +
        (
          check.passed
            ? check.weight
            : 0
        ),
      0,
    );

  return (
    passedWeight /
    totalWeight *
    100
  );
}

function buildImprovementChecks({
  metrics,
  benchmark,
  minimumAccuracyImprovement,
  minimumReturnImprovement,
  maximumDrawdownRegression,
}) {
  const benchmarkMetrics =
    normalizeMetrics(
      benchmark,
    );

  const accuracyImprovement =
    calculateImprovement(
      metrics.accuracy,
      benchmarkMetrics.accuracy,
      true,
    );

  const returnImprovement =
    calculateImprovement(
      metrics.averageReturn,
      benchmarkMetrics.averageReturn,
      true,
    );

  const drawdownImprovement =
    calculateImprovement(
      metrics.maximumDrawdown,
      benchmarkMetrics.maximumDrawdown,
      false,
    );

  const checks = [];

  if (
    benchmarkMetrics.accuracy !== null
  ) {
    checks.push({
      name:
        "ACCURACY_IMPROVEMENT",

      available:
        accuracyImprovement !== null,

      passed:
        accuracyImprovement !== null &&
        accuracyImprovement >=
          minimumAccuracyImprovement,

      value:
        accuracyImprovement === null
          ? null
          : round(
              accuracyImprovement,
            ),

      minimum:
        minimumAccuracyImprovement,

      maximum:
        null,

      weight:
        2,

      reason:
        accuracyImprovement !== null &&
        accuracyImprovement >=
          minimumAccuracyImprovement
          ? "PASSED"
          : "BENCHMARK_IMPROVEMENT_NOT_MET",
    });
  }

  if (
    benchmarkMetrics.averageReturn !== null
  ) {
    checks.push({
      name:
        "RETURN_IMPROVEMENT",

      available:
        returnImprovement !== null,

      passed:
        returnImprovement !== null &&
        returnImprovement >=
          minimumReturnImprovement,

      value:
        returnImprovement === null
          ? null
          : round(
              returnImprovement,
            ),

      minimum:
        minimumReturnImprovement,

      maximum:
        null,

      weight:
        1.5,

      reason:
        returnImprovement !== null &&
        returnImprovement >=
          minimumReturnImprovement
          ? "PASSED"
          : "BENCHMARK_IMPROVEMENT_NOT_MET",
    });
  }

  if (
    benchmarkMetrics.maximumDrawdown !== null
  ) {
    checks.push({
      name:
        "DRAWDOWN_REGRESSION",

      available:
        drawdownImprovement !== null,

      passed:
        drawdownImprovement !== null &&
        drawdownImprovement >=
          -maximumDrawdownRegression,

      value:
        drawdownImprovement === null
          ? null
          : round(
              drawdownImprovement,
            ),

      minimum:
        -maximumDrawdownRegression,

      maximum:
        null,

      weight:
        2,

      reason:
        drawdownImprovement !== null &&
        drawdownImprovement >=
          -maximumDrawdownRegression
          ? "PASSED"
          : "DRAWDOWN_REGRESSION_TOO_LARGE",
    });
  }

  return {
    benchmarkMetrics,

    accuracyImprovement:
      accuracyImprovement === null
        ? null
        : round(
            accuracyImprovement,
          ),

    returnImprovement:
      returnImprovement === null
        ? null
        : round(
            returnImprovement,
          ),

    drawdownImprovement:
      drawdownImprovement === null
        ? null
        : round(
            drawdownImprovement,
          ),

    checks,
  };
}

function determineDecision({
  blockers,
  warnings,
  drift,
  learning,
  score,
  minimumPromotionScore,
}) {
  if (
    drift.detected ||
    drift.level === "CRITICAL"
  ) {
    return {
      action:
        "RETRAIN",

      reason:
        "CONCEPT_DRIFT_BLOCKED_PROMOTION",
    };
  }

  if (
    learning.action === "RETRAIN"
  ) {
    return {
      action:
        "RETRAIN",

      reason:
        "LEARNING_ENGINE_REQUESTED_RETRAIN",
    };
  }

  if (blockers.length > 0) {
    return {
      action:
        "HOLD",

      reason:
        "PROMOTION_REQUIREMENTS_NOT_MET",
    };
  }

  if (
    score <
    minimumPromotionScore
  ) {
    return {
      action:
        "HOLD",

      reason:
        "PROMOTION_SCORE_BELOW_THRESHOLD",
    };
  }

  if (
    warnings.length > 0
  ) {
    return {
      action:
        "HOLD",

      reason:
        "PROMOTION_WARNINGS_REQUIRE_REVIEW",
    };
  }

  return {
    action:
      "PROMOTE",

    reason:
      "ALL_PROMOTION_GATES_PASSED",
  };
}

export function evaluateModelPromotion({
  candidate,
  metrics = {},
  benchmark = {},
  drift = {},
  learning = {},
  minimumAccuracy = 60,
  maximumCalibrationError = 20,
  minimumProfitFactor = 1.1,
  maximumDrawdown = 20,
  minimumAverageReturn = 0,
  minimumSamples = 100,
  minimumStabilityScore = 55,
  minimumMonteCarloSuccessRate = 55,
  minimumAccuracyImprovement = 0,
  minimumReturnImprovement = -5,
  maximumDrawdownRegression = 10,
  maximumDriftScore = 30,
  minimumPromotionScore = 85,
  requireBenchmark = false,
  requireHumanApproval = true,
} = {}) {
  const normalizedCandidate =
    normalizeCandidate(
      candidate,
    );

  const normalizedMetrics =
    normalizeMetrics(
      metrics,
    );

  const normalizedDrift =
    normalizeDrift(
      drift,
    );

  const normalizedLearning =
    normalizeLearning(
      learning,
    );

  const checks = [
    buildMetricCheck({
      name:
        "ACCURACY",

      value:
        normalizedMetrics.accuracy,

      minimum:
        minimumAccuracy,

      required:
        true,

      weight:
        3,
    }),

    buildMetricCheck({
      name:
        "CALIBRATION_ERROR",

      value:
        normalizedMetrics
          .confidenceCalibrationError,

      maximum:
        maximumCalibrationError,

      required:
        true,

      weight:
        1.5,
    }),

    buildMetricCheck({
      name:
        "PROFIT_FACTOR",

      value:
        normalizedMetrics
          .profitFactor,

      minimum:
        minimumProfitFactor,

      required:
        true,

      weight:
        2,
    }),

    buildMetricCheck({
      name:
        "MAXIMUM_DRAWDOWN",

      value:
        normalizedMetrics
          .maximumDrawdown,

      maximum:
        maximumDrawdown,

      required:
        true,

      weight:
        2,
    }),

    buildMetricCheck({
      name:
        "AVERAGE_RETURN",

      value:
        normalizedMetrics
          .averageReturn,

      minimum:
        minimumAverageReturn,

      required:
        true,

      weight:
        1.5,
    }),

    buildMetricCheck({
      name:
        "SAMPLE_COUNT",

      value:
        normalizedMetrics
          .sampleCount,

      minimum:
        minimumSamples,

      required:
        true,

      weight:
        2,
    }),

    buildMetricCheck({
      name:
        "STABILITY_SCORE",

      value:
        normalizedMetrics
          .stabilityScore,

      minimum:
        minimumStabilityScore,

      required:
        false,

      weight:
        1,
    }),

    buildMetricCheck({
      name:
        "MONTE_CARLO_SUCCESS_RATE",

      value:
        normalizedMetrics
          .monteCarloSuccessRate,

      minimum:
        minimumMonteCarloSuccessRate,

      required:
        false,

      weight:
        1,
    }),

    {
      name:
        "CONCEPT_DRIFT",

      available:
        normalizedDrift.ready,

      passed:
        normalizedDrift.ready &&
        !normalizedDrift.detected &&
        normalizedDrift.score <=
          maximumDriftScore &&
        normalizedDrift.allowPromotion,

      value:
        normalizedDrift.score,

      minimum:
        null,

      maximum:
        maximumDriftScore,

      weight:
        3,

      reason:
        normalizedDrift.ready &&
        !normalizedDrift.detected &&
        normalizedDrift.score <=
          maximumDriftScore &&
        normalizedDrift.allowPromotion
          ? "PASSED"
          : "DRIFT_GATE_BLOCKED",
    },

    {
      name:
        "LEARNING_RECOMMENDATION",

      available:
        normalizedLearning.ready,

      passed:
        normalizedLearning.ready &&
        normalizedLearning.action !==
          "RETRAIN",

      value:
        normalizedLearning.action,

      minimum:
        null,

      maximum:
        null,

      weight:
        1.5,

      reason:
        normalizedLearning.ready &&
        normalizedLearning.action !==
          "RETRAIN"
          ? "PASSED"
          : "LEARNING_GATE_BLOCKED",
    },
  ];

  const improvement =
    buildImprovementChecks({
      metrics:
        normalizedMetrics,

      benchmark,

      minimumAccuracyImprovement,

      minimumReturnImprovement,

      maximumDrawdownRegression,
    });

  if (
    requireBenchmark &&
    improvement.checks.length === 0
  ) {
    checks.push({
      name:
        "BENCHMARK_REQUIRED",

      available:
        false,

      passed:
        false,

      value:
        null,

      minimum:
        null,

      maximum:
        null,

      weight:
        2,

      reason:
        "BENCHMARK_METRICS_MISSING",
    });
  } else {
    checks.push(
      ...improvement.checks,
    );
  }

  const score =
    weightedPassScore(
      checks,
    );

  const blockers =
    checks
      .filter(
        (
          check,
        ) =>
          !check.passed &&
          (
            check.reason ===
              "MISSING_REQUIRED_METRIC" ||
            check.name ===
              "CONCEPT_DRIFT" ||
            check.name ===
              "LEARNING_RECOMMENDATION" ||
            check.name ===
              "BENCHMARK_REQUIRED" ||
            check.reason ===
              "THRESHOLD_NOT_MET" ||
            check.reason ===
              "DRAWDOWN_REGRESSION_TOO_LARGE"
          ),
      )
      .map(
        (
          check,
        ) =>
          check.name,
      );

  const warnings =
    checks
      .filter(
        (
          check,
        ) =>
          !check.passed &&
          !blockers.includes(
            check.name,
          ),
      )
      .map(
        (
          check,
        ) =>
          check.name,
      );

  const decision =
    determineDecision({
      blockers,

      warnings,

      drift:
        normalizedDrift,

      learning:
        normalizedLearning,

      score,

      minimumPromotionScore,
    });

  const humanApprovalRequired =
    decision.action ===
      "PROMOTE" &&
    requireHumanApproval;

  return {
    version:
      MODEL_PROMOTION_GATE_V2_VERSION,

    ready:
      true,

    candidate:
      normalizedCandidate,

    decision:
      decision.action,

    reason:
      decision.reason,

    promotionScore:
      round(
        score,
        2,
      ),

    minimumPromotionScore,

    automaticallyPromotable:
      decision.action ===
        "PROMOTE" &&
      !humanApprovalRequired,

    humanApprovalRequired,

    approved:
      decision.action ===
        "PROMOTE" &&
      !humanApprovalRequired,

    blockers,

    warnings,

    checks,

    metrics:
      normalizedMetrics,

    benchmark:
      improvement,

    drift:
      normalizedDrift,

    learning:
      normalizedLearning,

    audit: {
      candidateId:
        normalizedCandidate.id,

      candidateVersion:
        normalizedCandidate.version,

      evaluatedAt:
        new Date().toISOString(),

      passedCheckCount:
        checks.filter(
          (
            check,
          ) =>
            check.passed,
        ).length,

      totalCheckCount:
        checks.length,

      requireHumanApproval,

      requireBenchmark,
    },
  };
}

export function approveModelPromotion({
  evaluation,
  approvedBy,
  note = null,
} = {}) {
  if (
    !evaluation ||
    typeof evaluation !== "object"
  ) {
    throw new TypeError(
      "Model promotion evaluation is required.",
    );
  }

  if (
    evaluation.decision !==
    "PROMOTE"
  ) {
    return {
      version:
        MODEL_PROMOTION_GATE_V2_VERSION,

      approved:
        false,

      promoted:
        false,

      reason:
        "EVALUATION_NOT_PROMOTABLE",

      evaluation,
    };
  }

  const approver =
    String(
      approvedBy ??
      "",
    ).trim();

  if (!approver) {
    throw new TypeError(
      "Model promotion approval requires approvedBy.",
    );
  }

  return {
    version:
      MODEL_PROMOTION_GATE_V2_VERSION,

    approved:
      true,

    promoted:
      true,

    modelId:
      evaluation.candidate?.id ??
      null,

    modelVersion:
      evaluation.candidate?.version ??
      null,

    approvedBy:
      approver,

    approvedAt:
      new Date().toISOString(),

    note,

    promotionScore:
      evaluation.promotionScore,

    evaluation,
  };
}

export class ModelPromotionGateV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  evaluate(input = {}) {
    return evaluateModelPromotion({
      ...this.config,

      ...input,
    });
  }

  approve(input = {}) {
    return approveModelPromotion(
      input,
    );
  }
}

export const modelPromotionGateV2 =
  new ModelPromotionGateV2();

export default evaluateModelPromotion;