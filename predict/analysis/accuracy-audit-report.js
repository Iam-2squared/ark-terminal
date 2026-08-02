function finiteNumber(
  value,
  fallback = 0,
) {
  const parsed =
    Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function formatMetric(
  value,
  suffix = "",
) {
  if (
    value === Infinity
  ) {
    return `∞${suffix}`;
  }

  const parsed =
    Number(value);

  if (
    !Number.isFinite(parsed)
  ) {
    return "--";
  }

  return `${parsed}${suffix}`;
}

export function buildAccuracyAuditRating(
  summary = {},
) {
  const total =
    finiteNumber(
      summary.total,
      0,
    );

  const accuracy =
    finiteNumber(
      summary.accuracy,
      0,
    );

  const profitFactor =
    finiteNumber(
      summary.profitFactor,
      0,
    );

  const averageStrategyReturn =
    finiteNumber(
      summary.averageStrategyReturn,
      0,
    );

  const maximumDrawdown =
    finiteNumber(
      summary.maximumDrawdown,
      0,
    );

  if (total < 50) {
    return {
      grade: "N",
      label:
        "サンプル不足",
      usable:
        false,
    };
  }

  if (
    accuracy >= 58 &&
    profitFactor >= 1.4 &&
    averageStrategyReturn > 0 &&
    maximumDrawdown <= 15
  ) {
    return {
      grade: "A",
      label:
        "有望",
      usable:
        true,
    };
  }

  if (
    accuracy >= 53 &&
    profitFactor >= 1.1 &&
    averageStrategyReturn > 0
  ) {
    return {
      grade: "B",
      label:
        "改善しながら検証継続",
      usable:
        true,
    };
  }

  if (
    accuracy >= 50 &&
    averageStrategyReturn >= 0
  ) {
    return {
      grade: "C",
      label:
        "優位性は未確定",
      usable:
        false,
    };
  }

  return {
    grade: "D",
    label:
      "実運用不可",
    usable:
      false,
  };
}

export function buildAccuracyAuditReport(
  audit = {},
) {
  const summary =
    audit.summary ??
    {};

  const rating =
    buildAccuracyAuditRating(
      summary,
    );

  return {
    version:
      "accuracy-audit-report-v1",

    generatedAt:
      new Date()
        .toISOString(),

    auditVersion:
      audit.version ??
      null,

    horizon:
      audit.horizon ??
      null,

    sourceRows:
      audit.sourceRows ??
      0,

    predictionCount:
      summary.total ??
      0,

    rating,

    metrics: {
      accuracy:
        summary.accuracy ??
        0,

      buyPrecision:
        summary.buyPrecision ??
        0,

      sellPrecision:
        summary.sellPrecision ??
        0,

      averageStrategyReturn:
        summary.averageStrategyReturn ??
        0,

      profitFactor:
        summary.profitFactor ??
        0,

      maximumDrawdown:
        summary.maximumDrawdown ??
        0,

      calibrationError:
        summary.calibrationError ??
        null,
    },

    labels: {
      accuracy:
        formatMetric(
          summary.accuracy,
          "%",
        ),

      buyPrecision:
        formatMetric(
          summary.buyPrecision,
          "%",
        ),

      sellPrecision:
        formatMetric(
          summary.sellPrecision,
          "%",
        ),

      averageStrategyReturn:
        formatMetric(
          summary.averageStrategyReturn,
          "%",
        ),

      profitFactor:
        formatMetric(
          summary.profitFactor,
        ),

      maximumDrawdown:
        formatMetric(
          summary.maximumDrawdown,
          "%",
        ),

      calibrationError:
        summary.calibrationError ===
        null
          ? "--"
          : formatMetric(
              summary.calibrationError,
            ),
    },
  };
}

export function exportAccuracyAuditJson(
  report = {},
) {
  return JSON.stringify(
    report,
    null,
    2,
  );
}

export function exportAccuracyAuditCsv(
  audit = {},
) {
  const predictions =
    Array.isArray(
      audit.predictions,
    )
      ? audit.predictions
      : [];

  const headers = [
    "symbol",
    "entryDate",
    "exitDate",
    "horizon",
    "entryPrice",
    "exitPrice",
    "action",
    "predictedDirection",
    "actualDirection",
    "correct",
    "score",
    "confidence",
    "returnPercent",
    "strategyReturn",
  ];

  const escapeCsv =
    (value) => {
      const text =
        String(value ?? "");

      if (
        text.includes(",") ||
        text.includes('"') ||
        text.includes("\n")
      ) {
        return `"${text.replaceAll(
          '"',
          '""',
        )}"`;
      }

      return text;
    };

  const rows =
    predictions.map(
      (prediction) =>
        headers
          .map(
            (header) =>
              escapeCsv(
                prediction[header],
              ),
          )
          .join(","),
    );

  return [
    headers.join(","),
    ...rows,
  ].join("\n");
}