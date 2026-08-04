export const LEARNING_CANDIDATE_EVALUATOR_V2_VERSION =
  "learning-candidate-evaluator-v2";

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

function finiteNumber(
  value,
  fallback = 0,
) {
  return (
    finiteOrNull(value) ??
    fallback
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
      value *
      factor,
    ) /
    factor
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

function normalizeMetrics(
  source,
) {
  const metrics =
    source?.metrics ??
    source?.performance ??
    source ??
    {};

  return {
    ready:
      metrics.ready === true ||
      finiteOrNull(
        metrics.sampleCount,
      ) !== null,

    sampleCount:
      Math.max(
        0,
        Math.floor(
          finiteNumber(
            metrics.sampleCount,
            0,
          ),
        ),
      ),

    accuracy:
      finiteOrNull(
        metrics.weightedAccuracy ??
        metrics.accuracy,
      ),

    rawAccuracy:
      finiteOrNull(
        metrics.accuracy,
      ),

    averageReturn:
      finiteOrNull(
        metrics.averageReturn,
      ),

    medianReturn:
      finiteOrNull(
        metrics.medianReturn,
      ),

    profitFactor:
      finiteOrNull(
        metrics.profitFactor,
      ),

    profitFactorInfinite:
      metrics.profitFactorInfinite ===
      true,

    maximumDrawdown:
      finiteOrNull(
        metrics.maximumDrawdown,
      ),

    calibrationError:
      finiteOrNull(
        metrics.calibrationError,
      ),

    volatility:
      finiteOrNull(
        metrics.volatility,
      ),

    currentLossStreak:
      Math.max(
        0,
        Math.floor(
          finiteNumber(
            metrics.streaks
              ?.currentLossStreak ??
            metrics.currentLossStreak,
            0,
          ),
        ),
      ),
  };
}

function difference(
  candidate,
  current,
) {
  if (
    candidate === null ||
    current === null
  ) {
    return null;
  }

  return round(
    candidate -
    current,
  );
}

function relativeImprovement(
  candidate,
  current,
) {
  if (
    candidate === null ||
    current === null
  ) {
    return null;
  }

  if (current === 0) {
    return candidate === 0
      ? 0
      : null;
  }

  return round(
    (
      (
        candidate -
        current
      ) /
      Math.abs(current)
    ) *
    100,
  );
}

function addReason(
  reasons,
  {
    severity,
    code,
    message,
    metric = null,
    current = null,
    candidate = null,
    threshold = null,
  },
) {
  reasons.push({
    severity,
    code,
    message,
    metric,
    current,
    candidate,
    threshold,
  });
}

function scoreHigherIsBetter({
  current,
  candidate,
  neutralTolerance = 0,
  positiveWeight = 10,
  negativeWeight = 15,
}) {
  if (
    current === null ||
    candidate === null
  ) {
    return 0;
  }

  const delta =
    candidate -
    current;

  if (
    Math.abs(delta) <=
    neutralTolerance
  ) {
    return 0;
  }

  return delta > 0
    ? Math.min(
        positiveWeight,
        Math.abs(delta),
      )
    : -Math.min(
        negativeWeight,
        Math.abs(delta),
      );
}

function scoreLowerIsBetter({
  current,
  candidate,
  neutralTolerance = 0,
  positiveWeight = 10,
  negativeWeight = 15,
}) {
  if (
    current === null ||
    candidate === null
  ) {
    return 0;
  }

  const delta =
    current -
    candidate;

  if (
    Math.abs(delta) <=
    neutralTolerance
  ) {
    return 0;
  }

  return delta > 0
    ? Math.min(
        positiveWeight,
        Math.abs(delta),
      )
    : -Math.min(
        negativeWeight,
        Math.abs(delta),
      );
}

export function evaluateLearningCandidate({
  currentState,
  candidateState,
  minimumCandidateSamples = 20,
  minimumAccuracy = 45,
  minimumAccuracyImprovement = 0,
  minimumAverageReturn = 0,
  minimumReturnImprovement = 0,
  maximumDrawdown = 25,
  maximumDrawdownIncrease = 3,
  maximumCalibrationError = 35,
  maximumCalibrationRegression = 5,
  minimumProfitFactor = 1,
  maximumLossStreak = 8,
  minimumEvaluationScore = 60,
  requireCandidateRevisionIncrease = true,
  requireHumanApproval = true,
} = {}) {
  if (
    !currentState ||
    typeof currentState !==
      "object"
  ) {
    throw new TypeError(
      "Current learning state is required.",
    );
  }

  if (
    !candidateState ||
    typeof candidateState !==
      "object"
  ) {
    throw new TypeError(
      "Candidate learning state is required.",
    );
  }

  const current =
    normalizeMetrics(
      currentState,
    );

  const candidate =
    normalizeMetrics(
      candidateState,
    );

  const currentRevision =
    Math.max(
      0,
      Math.floor(
        finiteNumber(
          currentState.revision,
          0,
        ),
      ),
    );

  const candidateRevision =
    Math.max(
      0,
      Math.floor(
        finiteNumber(
          candidateState.revision,
          0,
        ),
      ),
    );

  const reasons = [];
  const blockers = [];
  const warnings = [];
  const strengths = [];

  if (!candidate.ready) {
    addReason(
      reasons,
      {
        severity:
          "BLOCKER",

        code:
          "CANDIDATE_NOT_READY",

        message:
          "Candidate metrics are not ready.",
      },
    );
  }

  if (
    candidate.sampleCount <
    minimumCandidateSamples
  ) {
    addReason(
      reasons,
      {
        severity:
          "WARNING",

        code:
          "INSUFFICIENT_CANDIDATE_SAMPLES",

        message:
          "Candidate has fewer samples than recommended.",

        metric:
          "sampleCount",

        candidate:
          candidate.sampleCount,

        threshold:
          minimumCandidateSamples,
      },
    );
  }

  if (
    requireCandidateRevisionIncrease &&
    candidateRevision <=
      currentRevision
  ) {
    addReason(
      reasons,
      {
        severity:
          "BLOCKER",

        code:
          "REVISION_NOT_ADVANCED",

        message:
          "Candidate revision must be newer than the current revision.",

        metric:
          "revision",

        current:
          currentRevision,

        candidate:
          candidateRevision,
      },
    );
  }

  if (
    candidate.accuracy ===
    null
  ) {
    addReason(
      reasons,
      {
        severity:
          "BLOCKER",

        code:
          "MISSING_ACCURACY",

        message:
          "Candidate accuracy is unavailable.",
      },
    );
  }
  else if (
    candidate.accuracy <
    minimumAccuracy
  ) {
    addReason(
      reasons,
      {
        severity:
          "BLOCKER",

        code:
          "ACCURACY_BELOW_MINIMUM",

        message:
          "Candidate accuracy is below the minimum.",

        metric:
          "accuracy",

        current:
          current.accuracy,

        candidate:
          candidate.accuracy,

        threshold:
          minimumAccuracy,
      },
    );
  }
  else if (
    current.accuracy !==
      null &&
    candidate.accuracy -
      current.accuracy <
      minimumAccuracyImprovement
  ) {
    addReason(
      reasons,
      {
        severity:
          "WARNING",

        code:
          "ACCURACY_IMPROVEMENT_TOO_SMALL",

        message:
          "Candidate accuracy improvement is below the preferred amount.",

        metric:
          "accuracy",

        current:
          current.accuracy,

        candidate:
          candidate.accuracy,

        threshold:
          minimumAccuracyImprovement,
      },
    );
  }
  else {
    addReason(
      reasons,
      {
        severity:
          "STRENGTH",

        code:
          "ACCURACY_ACCEPTABLE",

        message:
          "Candidate accuracy meets the evaluation standard.",

        metric:
          "accuracy",

        current:
          current.accuracy,

        candidate:
          candidate.accuracy,
      },
    );
  }

  if (
    candidate.averageReturn ===
    null
  ) {
    addReason(
      reasons,
      {
        severity:
          "WARNING",

        code:
          "MISSING_AVERAGE_RETURN",

        message:
          "Candidate average return is unavailable.",
      },
    );
  }
  else if (
    candidate.averageReturn <
    minimumAverageReturn
  ) {
    addReason(
      reasons,
      {
        severity:
          "BLOCKER",

        code:
          "RETURN_BELOW_MINIMUM",

        message:
          "Candidate average return is below the minimum.",

        metric:
          "averageReturn",

        current:
          current.averageReturn,

        candidate:
          candidate.averageReturn,

        threshold:
          minimumAverageReturn,
      },
    );
  }
  else if (
    current.averageReturn !==
      null &&
    candidate.averageReturn -
      current.averageReturn <
      minimumReturnImprovement
  ) {
    addReason(
      reasons,
      {
        severity:
          "WARNING",

        code:
          "RETURN_IMPROVEMENT_TOO_SMALL",

        message:
          "Candidate return improvement is below the preferred amount.",

        metric:
          "averageReturn",

        current:
          current.averageReturn,

        candidate:
          candidate.averageReturn,

        threshold:
          minimumReturnImprovement,
      },
    );
  }
  else {
    addReason(
      reasons,
      {
        severity:
          "STRENGTH",

        code:
          "RETURN_ACCEPTABLE",

        message:
          "Candidate average return meets the evaluation standard.",

        metric:
          "averageReturn",

        current:
          current.averageReturn,

        candidate:
          candidate.averageReturn,
      },
    );
  }

  if (
    candidate.maximumDrawdown ===
    null
  ) {
    addReason(
      reasons,
      {
        severity:
          "WARNING",

        code:
          "MISSING_DRAWDOWN",

        message:
          "Candidate maximum drawdown is unavailable.",
      },
    );
  }
  else if (
    candidate.maximumDrawdown >
    maximumDrawdown
  ) {
    addReason(
      reasons,
      {
        severity:
          "BLOCKER",

        code:
          "DRAWDOWN_ABOVE_MAXIMUM",

        message:
          "Candidate maximum drawdown exceeds the hard limit.",

        metric:
          "maximumDrawdown",

        current:
          current.maximumDrawdown,

        candidate:
          candidate.maximumDrawdown,

        threshold:
          maximumDrawdown,
      },
    );
  }
  else if (
    current.maximumDrawdown !==
      null &&
    candidate.maximumDrawdown -
      current.maximumDrawdown >
      maximumDrawdownIncrease
  ) {
    addReason(
      reasons,
      {
        severity:
          "BLOCKER",

        code:
          "DRAWDOWN_REGRESSION",

        message:
          "Candidate drawdown increased beyond the allowed amount.",

        metric:
          "maximumDrawdown",

        current:
          current.maximumDrawdown,

        candidate:
          candidate.maximumDrawdown,

        threshold:
          maximumDrawdownIncrease,
      },
    );
  }
  else {
    addReason(
      reasons,
      {
        severity:
          "STRENGTH",

        code:
          "DRAWDOWN_ACCEPTABLE",

        message:
          "Candidate drawdown is within the allowed range.",

        metric:
          "maximumDrawdown",

        current:
          current.maximumDrawdown,

        candidate:
          candidate.maximumDrawdown,
      },
    );
  }

  if (
    candidate.calibrationError !==
      null &&
    candidate.calibrationError >
      maximumCalibrationError
  ) {
    addReason(
      reasons,
      {
        severity:
          "BLOCKER",

        code:
          "CALIBRATION_ERROR_TOO_HIGH",

        message:
          "Candidate confidence calibration error is too high.",

        metric:
          "calibrationError",

        current:
          current.calibrationError,

        candidate:
          candidate.calibrationError,

        threshold:
          maximumCalibrationError,
      },
    );
  }
  else if (
    current.calibrationError !==
      null &&
    candidate.calibrationError !==
      null &&
    candidate.calibrationError -
      current.calibrationError >
      maximumCalibrationRegression
  ) {
    addReason(
      reasons,
      {
        severity:
          "WARNING",

        code:
          "CALIBRATION_REGRESSION",

        message:
          "Candidate confidence calibration became worse.",

        metric:
          "calibrationError",

        current:
          current.calibrationError,

        candidate:
          candidate.calibrationError,

        threshold:
          maximumCalibrationRegression,
      },
    );
  }

  if (
    !candidate
      .profitFactorInfinite &&
    candidate.profitFactor !==
      null &&
    candidate.profitFactor <
      minimumProfitFactor
  ) {
    addReason(
      reasons,
      {
        severity:
          "BLOCKER",

        code:
          "PROFIT_FACTOR_TOO_LOW",

        message:
          "Candidate profit factor is below the minimum.",

        metric:
          "profitFactor",

        current:
          current.profitFactor,

        candidate:
          candidate.profitFactor,

        threshold:
          minimumProfitFactor,
      },
    );
  }

  if (
    candidate.currentLossStreak >=
    maximumLossStreak
  ) {
    addReason(
      reasons,
      {
        severity:
          "BLOCKER",

        code:
          "LOSS_STREAK_LIMIT",

        message:
          "Candidate loss streak reached the configured limit.",

        metric:
          "currentLossStreak",

        candidate:
          candidate.currentLossStreak,

        threshold:
          maximumLossStreak,
      },
    );
  }

  for (const reason of reasons) {
    if (
      reason.severity ===
      "BLOCKER"
    ) {
      blockers.push(
        reason.code,
      );
    }

    if (
      reason.severity ===
      "WARNING"
    ) {
      warnings.push(
        reason.code,
      );
    }

    if (
      reason.severity ===
      "STRENGTH"
    ) {
      strengths.push(
        reason.code,
      );
    }
  }

  let evaluationScore = 50;

  evaluationScore +=
    scoreHigherIsBetter({
      current:
        current.accuracy,

      candidate:
        candidate.accuracy,

      neutralTolerance:
        0.25,

      positiveWeight:
        15,

      negativeWeight:
        20,
    });

  evaluationScore +=
    scoreHigherIsBetter({
      current:
        current.averageReturn,

      candidate:
        candidate.averageReturn,

      neutralTolerance:
        0.01,

      positiveWeight:
        15,

      negativeWeight:
        20,
    });

  evaluationScore +=
    scoreLowerIsBetter({
      current:
        current.maximumDrawdown,

      candidate:
        candidate.maximumDrawdown,

      neutralTolerance:
        0.1,

      positiveWeight:
        10,

      negativeWeight:
        20,
    });

  evaluationScore +=
    scoreLowerIsBetter({
      current:
        current.calibrationError,

      candidate:
        candidate.calibrationError,

      neutralTolerance:
        0.25,

      positiveWeight:
        10,

      negativeWeight:
        15,
    });

  if (
    candidate.profitFactorInfinite
  ) {
    evaluationScore += 10;
  }
  else {
    evaluationScore +=
      scoreHigherIsBetter({
        current:
          current.profitFactor,

        candidate:
          candidate.profitFactor,

        neutralTolerance:
          0.05,

        positiveWeight:
          10,

        negativeWeight:
          15,
      });
  }

  if (
    candidate.sampleCount >=
    minimumCandidateSamples
  ) {
    evaluationScore += 5;
  }

  evaluationScore -=
    blockers.length *
    25;

  evaluationScore -=
    warnings.length *
    3;

  evaluationScore =
    round(
      Math.max(
        0,
        Math.min(
          100,
          evaluationScore,
        ),
      ),
      2,
    );

  let decision;

  if (
    blockers.length >
    0
  ) {
    decision =
      "REJECT";
  }
  else if (
    evaluationScore <
      minimumEvaluationScore ||
    candidate.sampleCount <
      minimumCandidateSamples
  ) {
    decision =
      "HOLD";
  }
  else if (
    requireHumanApproval
  ) {
    decision =
      "REQUIRE_HUMAN_APPROVAL";
  }
  else {
    decision =
      "PROMOTE";
  }

  const approved =
    decision ===
    "PROMOTE";

  return {
    version:
      LEARNING_CANDIDATE_EVALUATOR_V2_VERSION,

    ready:
      candidate.ready,

    decision,

    approved,

    requiresHumanApproval:
      decision ===
      "REQUIRE_HUMAN_APPROVAL",

    evaluationScore,

    minimumEvaluationScore,

    currentRevision,

    candidateRevision,

    current,

    candidate,

    comparison: {
      accuracyDelta:
        difference(
          candidate.accuracy,
          current.accuracy,
        ),

      accuracyRelativeImprovementPercent:
        relativeImprovement(
          candidate.accuracy,
          current.accuracy,
        ),

      averageReturnDelta:
        difference(
          candidate.averageReturn,
          current.averageReturn,
        ),

      returnRelativeImprovementPercent:
        relativeImprovement(
          candidate.averageReturn,
          current.averageReturn,
        ),

      drawdownDelta:
        difference(
          candidate.maximumDrawdown,
          current.maximumDrawdown,
        ),

      calibrationErrorDelta:
        difference(
          candidate.calibrationError,
          current.calibrationError,
        ),

      profitFactorDelta:
        difference(
          candidate.profitFactor,
          current.profitFactor,
        ),

      sampleCountDelta:
        candidate.sampleCount -
        current.sampleCount,
    },

    blockers,

    warnings,

    strengths,

    reasons,

    recommendation: {
      action:
        decision,

      allowRegistryChange:
        approved,

      humanApprovalRequired:
        decision ===
        "REQUIRE_HUMAN_APPROVAL",

      rollbackCurrentModel:
        false,

      candidateModelId:
        normalizeText(
          candidateState.modelId,
          null,
        ),

      candidateModelVersion:
        normalizeText(
          candidateState.modelVersion,
          null,
        ),
    },
  };
}

export function approveLearningCandidate({
  evaluation,
  approvedBy,
  approvedAt = new Date().toISOString(),
} = {}) {
  if (
    !evaluation ||
    typeof evaluation !==
      "object"
  ) {
    throw new TypeError(
      "Learning candidate evaluation is required.",
    );
  }

  if (
    evaluation.decision !==
      "REQUIRE_HUMAN_APPROVAL"
  ) {
    throw new Error(
      "Learning candidate is not awaiting human approval.",
    );
  }

  const actor =
    normalizeText(
      approvedBy,
      "",
    );

  if (!actor) {
    throw new TypeError(
      "Learning candidate approver is required.",
    );
  }

  return {
    ...structuredClone(
      evaluation,
    ),

    decision:
      "PROMOTE",

    approved:
      true,

    requiresHumanApproval:
      false,

    approval: {
      approvedBy:
        actor,

      approvedAt:
        normalizeText(
          approvedAt,
          new Date().toISOString(),
        ),
    },

    recommendation: {
      ...evaluation.recommendation,

      action:
        "PROMOTE",

      allowRegistryChange:
        true,

      humanApprovalRequired:
        false,
    },
  };
}

export class LearningCandidateEvaluatorV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  evaluate(input = {}) {
    const result =
      evaluateLearningCandidate({
        ...this.config,
        ...input,
      });

    this.history.push({
      decision:
        result.decision,

      evaluationScore:
        result.evaluationScore,

      currentRevision:
        result.currentRevision,

      candidateRevision:
        result.candidateRevision,

      blockers: [
        ...result.blockers,
      ],

      timestamp:
        new Date().toISOString(),
    });

    return result;
  }

  approve(input = {}) {
    return approveLearningCandidate(
      input,
    );
  }

  getHistory() {
    return structuredClone(
      this.history,
    );
  }

  resetHistory() {
    this.history = [];

    return [];
  }
}

export const learningCandidateEvaluatorV2 =
  new LearningCandidateEvaluatorV2();

export default evaluateLearningCandidate;