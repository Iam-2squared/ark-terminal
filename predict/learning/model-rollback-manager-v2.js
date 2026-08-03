export const MODEL_ROLLBACK_MANAGER_V2_VERSION =
  "model-rollback-manager-v2";

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

function normalizeModel(
  model,
  role,
) {
  if (
    !model ||
    typeof model !== "object" ||
    Array.isArray(model)
  ) {
    throw new TypeError(
      `${role} model must be an object.`,
    );
  }

  const id =
    String(
      model.id ??
      model.modelId ??
      model.name ??
      "",
    ).trim();

  if (!id) {
    throw new TypeError(
      `${role} model requires an id.`,
    );
  }

  return {
    id,

    version:
      String(
        model.version ??
        "unknown",
      ),

    family:
      String(
        model.family ??
        model.type ??
        "GENERAL",
      )
        .trim()
        .toUpperCase(),

    status:
      String(
        model.status ??
        role,
      )
        .trim()
        .toUpperCase(),

    deployedAt:
      model.deployedAt ??
      null,

    metadata:
      model.metadata ??
      {},
  };
}

function normalizeMetrics(
  metrics = {},
) {
  if (
    !metrics ||
    typeof metrics !== "object" ||
    Array.isArray(metrics)
  ) {
    return {
      accuracy:
        null,

      averageReturn:
        null,

      maximumDrawdown:
        null,

      profitFactor:
        null,

      calibrationError:
        null,

      rejectionRate:
        null,

      errorRate:
        null,

      sampleCount:
        0,
    };
  }

  return {
    accuracy:
      finiteOrNull(
        metrics.accuracy ??
        metrics.directionalAccuracy ??
        metrics.meanAccuracy,
      ),

    averageReturn:
      finiteOrNull(
        metrics.averageReturn ??
        metrics.meanReturn,
      ),

    maximumDrawdown:
      finiteOrNull(
        metrics.maximumDrawdown ??
        metrics.maxDrawdown,
      ),

    profitFactor:
      finiteOrNull(
        metrics.profitFactor,
      ),

    calibrationError:
      finiteOrNull(
        metrics.calibrationError ??
        metrics.confidenceCalibrationError,
      ),

    rejectionRate:
      finiteOrNull(
        metrics.rejectionRate,
      ),

    errorRate:
      finiteOrNull(
        metrics.errorRate ??
        metrics.failureRate,
      ),

    sampleCount:
      Math.max(
        0,
        Math.floor(
          finiteOrNull(
            metrics.sampleCount ??
            metrics.recordCount,
          ) ?? 0,
        ),
      ),
  };
}

function normalizeDrift(
  drift = {},
) {
  return {
    ready:
      drift?.ready === true,

    detected:
      drift?.driftDetected === true,

    score:
      clamp(
        drift?.driftScore,
      ) ?? 0,

    level:
      String(
        drift?.driftLevel ??
        "UNKNOWN",
      )
        .trim()
        .toUpperCase(),

    recommendation:
      String(
        drift?.recommendation
          ?.action ??
        "UNKNOWN",
      )
        .trim()
        .toUpperCase(),
  };
}

function percentRegression(
  current,
  baseline,
  lowerIsBetter = false,
) {
  if (
    current === null ||
    baseline === null
  ) {
    return null;
  }

  if (
    Math.abs(
      baseline,
    ) <
    0.0000001
  ) {
    const difference =
      current -
      baseline;

    return lowerIsBetter
      ? -difference
      : difference;
  }

  const change =
    (
      current -
      baseline
    ) /
    Math.abs(
      baseline,
    ) *
    100;

  return lowerIsBetter
    ? -change
    : change;
}

function createCheck({
  name,
  triggered,
  severity,
  value,
  threshold,
  reason,
}) {
  return {
    name,

    triggered:
      triggered === true,

    severity,

    value:
      Number.isFinite(value)
        ? round(value)
        : value,

    threshold,

    reason:
      triggered
        ? reason
        : "PASSED",
  };
}

function calculateRiskScore(
  checks,
) {
  const weights = {
    CRITICAL:
      35,

    HIGH:
      22,

    MEDIUM:
      12,

    LOW:
      5,
  };

  return clamp(
    checks.reduce(
      (
        sum,
        check,
      ) =>
        sum +
        (
          check.triggered
            ? weights[
                check.severity
              ] ?? 0
            : 0
        ),
      0,
    ),
  ) ?? 0;
}

function determineAction({
  checks,
  riskScore,
  automaticRollbackThreshold,
  freezeThreshold,
}) {
  const critical =
    checks.filter(
      (
        check,
      ) =>
        check.triggered &&
        check.severity ===
          "CRITICAL",
    );

  const high =
    checks.filter(
      (
        check,
      ) =>
        check.triggered &&
        check.severity ===
          "HIGH",
    );

  if (
    critical.length > 0 ||
    riskScore >=
      automaticRollbackThreshold
  ) {
    return {
      action:
        "ROLLBACK",

      automatic:
        true,

      reason:
        critical[0]?.reason ??
        "ROLLBACK_RISK_THRESHOLD_EXCEEDED",
    };
  }

  if (
    high.length > 0 ||
    riskScore >=
      freezeThreshold
  ) {
    return {
      action:
        "FREEZE",

      automatic:
        false,

      reason:
        high[0]?.reason ??
        "MODEL_REQUIRES_REVIEW",
    };
  }

  return {
    action:
      "CONTINUE",

    automatic:
      false,

    reason:
      "MODEL_PERFORMANCE_WITHIN_LIMITS",
  };
}

export function evaluateModelRollback({
  activeModel,
  fallbackModel,
  activeMetrics = {},
  baselineMetrics = {},
  drift = {},
  minimumSamples = 30,
  minimumAccuracy = 50,
  maximumAccuracyRegression = 12,
  maximumReturnRegression = 30,
  maximumDrawdownIncrease = 40,
  minimumProfitFactor = 0.9,
  maximumCalibrationError = 30,
  maximumErrorRate = 10,
  maximumRejectionRate = 40,
  criticalDriftScore = 75,
  automaticRollbackThreshold = 70,
  freezeThreshold = 35,
} = {}) {
  const normalizedActive =
    normalizeModel(
      activeModel,
      "Active",
    );

  const normalizedFallback =
    normalizeModel(
      fallbackModel,
      "Fallback",
    );

  if (
    normalizedActive.id ===
      normalizedFallback.id &&
    normalizedActive.version ===
      normalizedFallback.version
  ) {
    throw new TypeError(
      "Active and fallback models must be different.",
    );
  }

  const current =
    normalizeMetrics(
      activeMetrics,
    );

  const baseline =
    normalizeMetrics(
      baselineMetrics,
    );

  const normalizedDrift =
    normalizeDrift(
      drift,
    );

  const accuracyRegression =
    percentRegression(
      current.accuracy,
      baseline.accuracy,
      false,
    );

  const returnRegression =
    percentRegression(
      current.averageReturn,
      baseline.averageReturn,
      false,
    );

  const drawdownRegression =
    percentRegression(
      current.maximumDrawdown,
      baseline.maximumDrawdown,
      true,
    );

  const checks = [
    createCheck({
      name:
        "INSUFFICIENT_SAMPLES",

      triggered:
        current.sampleCount <
        minimumSamples,

      severity:
        "LOW",

      value:
        current.sampleCount,

      threshold:
        minimumSamples,

      reason:
        "ROLLBACK_EVALUATION_NEEDS_MORE_DATA",
    }),

    createCheck({
      name:
        "ABSOLUTE_ACCURACY_FAILURE",

      triggered:
        current.accuracy !== null &&
        current.accuracy <
          minimumAccuracy,

      severity:
        "CRITICAL",

      value:
        current.accuracy,

      threshold:
        minimumAccuracy,

      reason:
        "ACTIVE_MODEL_ACCURACY_TOO_LOW",
    }),

    createCheck({
      name:
        "ACCURACY_REGRESSION",

      triggered:
        accuracyRegression !== null &&
        accuracyRegression <
          -maximumAccuracyRegression,

      severity:
        "HIGH",

      value:
        accuracyRegression,

      threshold:
        -maximumAccuracyRegression,

      reason:
        "ACTIVE_MODEL_ACCURACY_REGRESSED",
    }),

    createCheck({
      name:
        "RETURN_REGRESSION",

      triggered:
        returnRegression !== null &&
        returnRegression <
          -maximumReturnRegression,

      severity:
        "HIGH",

      value:
        returnRegression,

      threshold:
        -maximumReturnRegression,

      reason:
        "ACTIVE_MODEL_RETURN_REGRESSED",
    }),

    createCheck({
      name:
        "DRAWDOWN_INCREASE",

      triggered:
        drawdownRegression !== null &&
        drawdownRegression <
          -maximumDrawdownIncrease,

      severity:
        "CRITICAL",

      value:
        drawdownRegression,

      threshold:
        -maximumDrawdownIncrease,

      reason:
        "ACTIVE_MODEL_DRAWDOWN_SPIKE",
    }),

    createCheck({
      name:
        "PROFIT_FACTOR_FAILURE",

      triggered:
        current.profitFactor !== null &&
        current.profitFactor <
          minimumProfitFactor,

      severity:
        "HIGH",

      value:
        current.profitFactor,

      threshold:
        minimumProfitFactor,

      reason:
        "ACTIVE_MODEL_PROFIT_FACTOR_TOO_LOW",
    }),

    createCheck({
      name:
        "CALIBRATION_FAILURE",

      triggered:
        current.calibrationError !== null &&
        current.calibrationError >
          maximumCalibrationError,

      severity:
        "MEDIUM",

      value:
        current.calibrationError,

      threshold:
        maximumCalibrationError,

      reason:
        "ACTIVE_MODEL_CONFIDENCE_UNRELIABLE",
    }),

    createCheck({
      name:
        "ERROR_RATE_FAILURE",

      triggered:
        current.errorRate !== null &&
        current.errorRate >
          maximumErrorRate,

      severity:
        "CRITICAL",

      value:
        current.errorRate,

      threshold:
        maximumErrorRate,

      reason:
        "ACTIVE_MODEL_RUNTIME_ERROR_RATE_HIGH",
    }),

    createCheck({
      name:
        "REJECTION_RATE_FAILURE",

      triggered:
        current.rejectionRate !== null &&
        current.rejectionRate >
          maximumRejectionRate,

      severity:
        "MEDIUM",

      value:
        current.rejectionRate,

      threshold:
        maximumRejectionRate,

      reason:
        "ACTIVE_MODEL_REJECTION_RATE_HIGH",
    }),

    createCheck({
      name:
        "CRITICAL_CONCEPT_DRIFT",

      triggered:
        normalizedDrift.detected &&
        (
          normalizedDrift.score >=
            criticalDriftScore ||
          normalizedDrift.level ===
            "CRITICAL"
        ),

      severity:
        "CRITICAL",

      value:
        normalizedDrift.score,

      threshold:
        criticalDriftScore,

      reason:
        "CRITICAL_CONCEPT_DRIFT_DETECTED",
    }),

    createCheck({
      name:
        "HIGH_CONCEPT_DRIFT",

      triggered:
        normalizedDrift.detected &&
        normalizedDrift.level ===
          "HIGH" &&
        normalizedDrift.score <
          criticalDriftScore,

      severity:
        "HIGH",

      value:
        normalizedDrift.score,

      threshold:
        criticalDriftScore,

      reason:
        "HIGH_CONCEPT_DRIFT_DETECTED",
    }),
  ];

  const riskScore =
    calculateRiskScore(
      checks,
    );

  const decision =
    determineAction({
      checks,

      riskScore,

      automaticRollbackThreshold:
        clamp(
          automaticRollbackThreshold,
        ) ?? 70,

      freezeThreshold:
        clamp(
          freezeThreshold,
        ) ?? 35,
    });

  const blockers =
    checks
      .filter(
        (
          check,
        ) =>
          check.triggered,
      )
      .map(
        (
          check,
        ) =>
          check.name,
      );

  return {
    version:
      MODEL_ROLLBACK_MANAGER_V2_VERSION,

    ready:
      current.sampleCount >=
      minimumSamples,

    action:
      decision.action,

    automatic:
      decision.automatic,

    reason:
      decision.reason,

    riskScore:
      round(
        riskScore,
        2,
      ),

    activeModel:
      normalizedActive,

    fallbackModel:
      normalizedFallback,

    metrics: {
      active:
        current,

      baseline,
    },

    regression: {
      accuracyPercent:
        accuracyRegression === null
          ? null
          : round(
              accuracyRegression,
            ),

      returnPercent:
        returnRegression === null
          ? null
          : round(
              returnRegression,
            ),

      drawdownPercent:
        drawdownRegression === null
          ? null
          : round(
              drawdownRegression,
            ),
    },

    drift:
      normalizedDrift,

    checks,

    blockers,

    rollbackRequired:
      decision.action ===
      "ROLLBACK",

    reviewRequired:
      decision.action ===
        "FREEZE" ||
      decision.action ===
        "ROLLBACK",

    audit: {
      evaluatedAt:
        new Date().toISOString(),

      activeModelId:
        normalizedActive.id,

      activeModelVersion:
        normalizedActive.version,

      fallbackModelId:
        normalizedFallback.id,

      fallbackModelVersion:
        normalizedFallback.version,

      triggeredCheckCount:
        blockers.length,

      totalCheckCount:
        checks.length,
    },
  };
}

export function executeModelRollback({
  evaluation,
  executedBy,
  note = null,
  requireHumanApproval = true,
} = {}) {
  if (
    !evaluation ||
    typeof evaluation !== "object"
  ) {
    throw new TypeError(
      "Model rollback evaluation is required.",
    );
  }

  if (
    evaluation.action !==
    "ROLLBACK"
  ) {
    return {
      version:
        MODEL_ROLLBACK_MANAGER_V2_VERSION,

      executed:
        false,

      reason:
        "ROLLBACK_NOT_REQUIRED",

      evaluation,
    };
  }

  const executor =
    String(
      executedBy ??
      "",
    ).trim();

  if (
    requireHumanApproval &&
    !executor
  ) {
    throw new TypeError(
      "Model rollback requires executedBy.",
    );
  }

  return {
    version:
      MODEL_ROLLBACK_MANAGER_V2_VERSION,

    executed:
      true,

    action:
      "ROLLBACK",

    previousModel:
      evaluation.activeModel,

    restoredModel:
      evaluation.fallbackModel,

    executedBy:
      executor ||
      "automatic-safety-system",

    executedAt:
      new Date().toISOString(),

    note,

    riskScore:
      evaluation.riskScore,

    reason:
      evaluation.reason,

    registryPatch: {
      champion:
        evaluation.fallbackModel,

      retired: {
        ...evaluation.activeModel,

        status:
          "ROLLED_BACK",
      },

      rollbackMetadata: {
        executedAt:
          new Date().toISOString(),

        reason:
          evaluation.reason,

        riskScore:
          evaluation.riskScore,
      },
    },

    evaluation,
  };
}

export function createRollbackSnapshot({
  activeModel,
  fallbackModel,
  registry = {},
} = {}) {
  return {
    version:
      MODEL_ROLLBACK_MANAGER_V2_VERSION,

    createdAt:
      new Date().toISOString(),

    activeModel:
      normalizeModel(
        activeModel,
        "Active",
      ),

    fallbackModel:
      normalizeModel(
        fallbackModel,
        "Fallback",
      ),

    registry:
      structuredClone(
        registry,
      ),
  };
}

export class ModelRollbackManagerV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  evaluate(input = {}) {
    return evaluateModelRollback({
      ...this.config,

      ...input,
    });
  }

  execute(input = {}) {
    return executeModelRollback(
      input,
    );
  }

  snapshot(input = {}) {
    return createRollbackSnapshot(
      input,
    );
  }
}

export const modelRollbackManagerV2 =
  new ModelRollbackManagerV2();

export default evaluateModelRollback;