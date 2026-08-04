export const LEARNING_REPORT_V2_VERSION =
  "learning-report-v2";

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

function normalizeTimestamp(
  value,
  fallback =
    new Date().toISOString(),
) {
  const source =
    value ??
    fallback;

  const milliseconds =
    typeof source === "number"
      ? source
      : Date.parse(source);

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(
      "Learning report timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function round(
  value,
  digits = 2,
) {
  if (!Number.isFinite(value)) {
    return null;
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

function normalizeMetrics(state = {}) {
  const metrics =
    state.metrics ??
    state.performance ??
    {};

  return {
    ready:
      metrics.ready === true,

    sampleCount:
      Math.max(
        0,
        Math.floor(
          finiteOrNull(
            metrics.sampleCount,
          ) ?? 0,
        ),
      ),

    accuracy:
      round(
        finiteOrNull(
          metrics.weightedAccuracy ??
          metrics.accuracy,
        ),
      ),

    rawAccuracy:
      round(
        finiteOrNull(
          metrics.accuracy,
        ),
      ),

    averageReturn:
      round(
        finiteOrNull(
          metrics.averageReturn,
        ),
        4,
      ),

    medianReturn:
      round(
        finiteOrNull(
          metrics.medianReturn,
        ),
        4,
      ),

    profitFactor:
      round(
        finiteOrNull(
          metrics.profitFactor,
        ),
        4,
      ),

    profitFactorInfinite:
      metrics.profitFactorInfinite ===
      true,

    maximumDrawdown:
      round(
        finiteOrNull(
          metrics.maximumDrawdown,
        ),
        4,
      ),

    calibrationError:
      round(
        finiteOrNull(
          metrics.calibrationError,
        ),
      ),

    volatility:
      round(
        finiteOrNull(
          metrics.volatility,
        ),
        4,
      ),

    averageConfidence:
      round(
        finiteOrNull(
          metrics.averageConfidence,
        ),
      ),

    currentLossStreak:
      Math.max(
        0,
        Math.floor(
          finiteOrNull(
            metrics.streaks
              ?.currentLossStreak,
          ) ?? 0,
        ),
      ),
  };
}

function normalizeAuditSummary(
  audit = {},
) {
  const source =
    audit.summary ??
    audit;

  return {
    valid:
      source.valid === true,

    entryCount:
      Math.max(
        0,
        Math.floor(
          finiteOrNull(
            source.entryCount,
          ) ?? 0,
        ),
      ),

    issueCount:
      Math.max(
        0,
        Math.floor(
          finiteOrNull(
            source.issueCount,
          ) ?? 0,
        ),
      ),

    headHash:
      source.headHash ??
      null,

    firstTimestamp:
      source.firstTimestamp ??
      null,

    latestTimestamp:
      source.latestTimestamp ??
      null,

    byEventType: {
      ...(
        source.byEventType ??
        {}
      ),
    },

    byActor: {
      ...(
        source.byActor ??
        {}
      ),
    },
  };
}

function normalizePromotion(
  promotion = {},
) {
  const request =
    promotion.request ??
    promotion;

  return {
    requestId:
      request.id ??
      null,

    status:
      normalizeText(
        request.status,
        "NOT_AVAILABLE",
      ).toUpperCase(),

    requestedBy:
      request.requestedBy ??
      null,

    createdAt:
      request.createdAt ??
      null,

    updatedAt:
      request.updatedAt ??
      null,

    approvedBy:
      request.approval
        ?.approvedBy ??
      null,

    appliedBy:
      request.application
        ?.appliedBy ??
      null,

    candidateRevision:
      request.candidate
        ?.revision ??
      request.candidateState
        ?.revision ??
      null,

    currentRevision:
      request.current
        ?.revision ??
      request.currentState
        ?.revision ??
      null,
  };
}

function normalizeEvaluation(
  evaluation = {},
) {
  return {
    decision:
      normalizeText(
        evaluation.decision,
        "NOT_EVALUATED",
      ).toUpperCase(),

    approved:
      evaluation.approved === true,

    requiresHumanApproval:
      evaluation.requiresHumanApproval ===
      true,

    evaluationScore:
      round(
        finiteOrNull(
          evaluation.evaluationScore,
        ),
      ),

    blockers:
      Array.isArray(
        evaluation.blockers,
      )
        ? [
            ...evaluation.blockers,
          ]
        : [],

    warnings:
      Array.isArray(
        evaluation.warnings,
      )
        ? [
            ...evaluation.warnings,
          ]
        : [],

    strengths:
      Array.isArray(
        evaluation.strengths,
      )
        ? [
            ...evaluation.strengths,
          ]
        : [],

    comparison: {
      ...(
        evaluation.comparison ??
        {}
      ),
    },
  };
}

function deriveHealth({
  metrics,
  audit,
  evaluation,
  safeguards,
}) {
  const blockers = [];
  const warnings = [];

  if (!metrics.ready) {
    blockers.push(
      "METRICS_NOT_READY",
    );
  }

  if (
    safeguards?.frozen ===
    true
  ) {
    blockers.push(
      safeguards.freezeReason ??
      "LEARNING_FROZEN",
    );
  }

  if (
    safeguards
      ?.rollbackRequired ===
    true
  ) {
    blockers.push(
      "ROLLBACK_REQUIRED",
    );
  }

  if (
    audit.entryCount > 0 &&
    !audit.valid
  ) {
    blockers.push(
      "AUDIT_INVALID",
    );
  }

  if (
    evaluation.blockers.length >
    0
  ) {
    blockers.push(
      ...evaluation.blockers,
    );
  }

  if (
    metrics.sampleCount <
    20
  ) {
    warnings.push(
      "LOW_SAMPLE_COUNT",
    );
  }

  if (
    metrics.calibrationError !==
      null &&
    metrics.calibrationError >
      30
  ) {
    warnings.push(
      "HIGH_CALIBRATION_ERROR",
    );
  }

  warnings.push(
    ...evaluation.warnings,
  );

  let status =
    "HEALTHY";

  if (blockers.length > 0) {
    status =
      "CRITICAL";
  }
  else if (warnings.length > 0) {
    status =
      "WATCH";
  }

  return {
    status,

    blockers: [
      ...new Set(
        blockers,
      ),
    ],

    warnings: [
      ...new Set(
        warnings,
      ),
    ],
  };
}

function buildRecommendation({
  health,
  evaluation,
  promotion,
}) {
  if (
    health.status ===
    "CRITICAL"
  ) {
    return {
      action:
        "STOP_AND_REVIEW",

      message:
        "Learning changes should not be promoted until blockers are resolved.",
    };
  }

  if (
    evaluation.decision ===
    "REQUIRE_HUMAN_APPROVAL"
  ) {
    return {
      action:
        "REQUEST_HUMAN_APPROVAL",

      message:
        "Candidate passed automated checks and requires human approval.",
    };
  }

  if (
    evaluation.decision ===
    "PROMOTE" &&
    promotion.status !==
    "APPLIED"
  ) {
    return {
      action:
        "APPLY_APPROVED_PROMOTION",

      message:
        "Candidate is approved and ready for controlled promotion.",
    };
  }

  if (
    promotion.status ===
    "APPLIED"
  ) {
    return {
      action:
        "MONITOR_PROMOTED_MODEL",

      message:
        "Promotion is applied. Continue monitoring live performance.",
    };
  }

  if (
    health.status ===
    "WATCH"
  ) {
    return {
      action:
        "COLLECT_MORE_DATA",

      message:
        "Continue collecting outcomes before making larger learning changes.",
    };
  }

  return {
    action:
      "CONTINUE_MONITORING",

    message:
      "Learning system is healthy and can continue operating.",
  };
}

export function buildLearningReport({
  state = {},
  evaluation = {},
  promotion = {},
  audit = {},
  feedback = {},
  quality = {},
  generatedAt =
    new Date().toISOString(),
  generatedBy =
    "ark-terminal",
  title =
    "Ark Terminal Learning Report",
} = {}) {
  const timestamp =
    normalizeTimestamp(
      generatedAt,
    );

  const metrics =
    normalizeMetrics(
      state,
    );

  const auditSummary =
    normalizeAuditSummary(
      audit,
    );

  const candidateEvaluation =
    normalizeEvaluation(
      evaluation,
    );

  const promotionSummary =
    normalizePromotion(
      promotion,
    );

  const safeguards = {
    ...(
      state.safeguards ??
      {}
    ),
  };

  const health =
    deriveHealth({
      metrics,

      audit:
        auditSummary,

      evaluation:
        candidateEvaluation,

      safeguards,
    });

  const recommendation =
    buildRecommendation({
      health,

      evaluation:
        candidateEvaluation,

      promotion:
        promotionSummary,
    });

  return {
    version:
      LEARNING_REPORT_V2_VERSION,

    title:
      normalizeText(
        title,
        "Ark Terminal Learning Report",
      ),

    generatedAt:
      timestamp,

    generatedBy:
      normalizeText(
        generatedBy,
        "ark-terminal",
      ),

    model: {
      modelId:
        state.modelId ??
        null,

      modelVersion:
        state.modelVersion ??
        null,

      revision:
        state.revision ??
        0,

      enabled:
        state.enabled !== false,

      updatedAt:
        state.updatedAt ??
        null,
    },

    health,

    kpis:
      metrics,

    training: {
      recordCount:
        state.history
          ?.recordCount ??
        metrics.sampleCount,

      latestRecordId:
        state.history
          ?.latestRecordId ??
        null,

      latestTimestamp:
        state.history
          ?.latestTimestamp ??
        null,

      baseWeight:
        state.weights
          ?.base ??
        null,

      regimeWeightCount:
        Object.keys(
          state.weights
            ?.byRegime ??
          {},
        ).length,

      horizonWeightCount:
        Object.keys(
          state.weights
            ?.byHorizon ??
          {},
        ).length,

      safeguards,
    },

    feedback: {
      createdCount:
        feedback.summary
          ?.createdCount ??
        feedback.records
          ?.length ??
        0,

      pendingCount:
        feedback.summary
          ?.pendingCount ??
        feedback.pending
          ?.length ??
        0,

      rejectedCount:
        feedback.summary
          ?.rejectedCount ??
        feedback.rejected
          ?.length ??
        0,
    },

    quality: {
      passed:
        quality.passed ===
        true,

      qualityScore:
        quality.qualityScore ??
        null,

      acceptedCount:
        quality.summary
          ?.acceptedCount ??
        quality.acceptedRecords
          ?.length ??
        0,

      rejectedCount:
        quality.summary
          ?.rejectedCount ??
        quality.rejectedRecords
          ?.length ??
        0,

      criticalCount:
        quality.summary
          ?.criticalCount ??
        0,

      errorCount:
        quality.summary
          ?.errorCount ??
        0,

      warningCount:
        quality.summary
          ?.warningCount ??
        0,
    },

    candidateEvaluation,

    promotion:
      promotionSummary,

    audit:
      auditSummary,

    recommendation,
  };
}

function displayValue(
  value,
  suffix = "",
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "N/A";
  }

  return `${value}${suffix}`;
}

export function renderLearningReportMarkdown(
  report,
) {
  if (
    !report ||
    typeof report !== "object"
  ) {
    throw new TypeError(
      "Learning report is required.",
    );
  }

  const lines = [
    `# ${report.title}`,
    "",
    `Generated: ${report.generatedAt}`,
    `Model: ${report.model.modelId ?? "N/A"} ${report.model.modelVersion ?? ""}`,
    `Revision: ${report.model.revision}`,
    `Health: **${report.health.status}**`,
    "",
    "## KPI Summary",
    "",
    `- Samples: ${report.kpis.sampleCount}`,
    `- Accuracy: ${displayValue(report.kpis.accuracy, "%")}`,
    `- Average return: ${displayValue(report.kpis.averageReturn, "%")}`,
    `- Profit factor: ${report.kpis.profitFactorInfinite ? "Infinity" : displayValue(report.kpis.profitFactor)}`,
    `- Maximum drawdown: ${displayValue(report.kpis.maximumDrawdown, "%")}`,
    `- Calibration error: ${displayValue(report.kpis.calibrationError, "%")}`,
    "",
    "## Training Summary",
    "",
    `- Records: ${report.training.recordCount}`,
    `- Base weight: ${displayValue(report.training.baseWeight)}`,
    `- Regime weights: ${report.training.regimeWeightCount}`,
    `- Horizon weights: ${report.training.horizonWeightCount}`,
    "",
    "## Dataset Quality",
    "",
    `- Passed: ${report.quality.passed}`,
    `- Quality score: ${displayValue(report.quality.qualityScore)}`,
    `- Accepted: ${report.quality.acceptedCount}`,
    `- Rejected: ${report.quality.rejectedCount}`,
    "",
    "## Candidate Evaluation",
    "",
    `- Decision: ${report.candidateEvaluation.decision}`,
    `- Score: ${displayValue(report.candidateEvaluation.evaluationScore)}`,
    `- Human approval required: ${report.candidateEvaluation.requiresHumanApproval}`,
    "",
    "## Promotion",
    "",
    `- Status: ${report.promotion.status}`,
    `- Current revision: ${displayValue(report.promotion.currentRevision)}`,
    `- Candidate revision: ${displayValue(report.promotion.candidateRevision)}`,
    "",
    "## Audit",
    "",
    `- Valid: ${report.audit.valid}`,
    `- Entries: ${report.audit.entryCount}`,
    `- Issues: ${report.audit.issueCount}`,
    "",
    "## Recommendation",
    "",
    `**${report.recommendation.action}**`,
    "",
    report.recommendation.message,
  ];

  if (
    report.health.blockers.length >
    0
  ) {
    lines.push(
      "",
      "## Blockers",
      "",
      ...report.health.blockers.map(
        (
          blocker,
        ) =>
          `- ${blocker}`,
      ),
    );
  }

  if (
    report.health.warnings.length >
    0
  ) {
    lines.push(
      "",
      "## Warnings",
      "",
      ...report.health.warnings.map(
        (
          warning,
        ) =>
          `- ${warning}`,
      ),
    );
  }

  return lines.join(
    "\n",
  );
}

export function exportLearningReportJson(
  report,
  {
    pretty = true,
  } = {},
) {
  if (
    !report ||
    typeof report !== "object"
  ) {
    throw new TypeError(
      "Learning report is required.",
    );
  }

  return JSON.stringify(
    report,
    null,
    pretty
      ? 2
      : 0,
  );
}

export function createLearningReportExport({
  report,
  format = "json",
} = {}) {
  const normalizedFormat =
    normalizeText(
      format,
      "json",
    ).toLowerCase();

  if (
    normalizedFormat ===
    "json"
  ) {
    return {
      format:
        "json",

      mimeType:
        "application/json",

      extension:
        "json",

      content:
        exportLearningReportJson(
          report,
        ),
    };
  }

  if (
    [
      "markdown",
      "md",
    ].includes(
      normalizedFormat,
    )
  ) {
    return {
      format:
        "markdown",

      mimeType:
        "text/markdown",

      extension:
        "md",

      content:
        renderLearningReportMarkdown(
          report,
        ),
    };
  }

  throw new TypeError(
    `Unsupported learning report format: ${format}`,
  );
}

export class LearningReportV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  build(input = {}) {
    const report =
      buildLearningReport({
        ...this.config,
        ...input,
      });

    this.history.push(
      clone(report),
    );

    return clone(report);
  }

  markdown(report) {
    return renderLearningReportMarkdown(
      report,
    );
  }

  json(
    report,
    options = {},
  ) {
    return exportLearningReportJson(
      report,
      options,
    );
  }

  export(
    report,
    format = "json",
  ) {
    return createLearningReportExport({
      report,
      format,
    });
  }

  getHistory() {
    return clone(
      this.history,
    );
  }

  reset() {
    this.history = [];

    return [];
  }
}

export const learningReportV2 =
  new LearningReportV2();

export default buildLearningReport;