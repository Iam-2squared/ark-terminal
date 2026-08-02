import {
  createBacktestDiagnosticsReport,
} from "./backtest-diagnostics-report.js";

export const PHASE_A_VALIDATION_VERSION =
  "phase-a-validation-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function check({
  id,
  label,
  passed,
  actual = null,
  expected = null,
  severity = "error",
}) {
  return {
    id,
    label,
    passed:
      Boolean(passed),
    actual,
    expected,
    severity,
  };
}

function resolveMode(
  result = {},
  mode = "signal",
) {
  if (
    mode === "executable" &&
    result.executable
  ) {
    return result.executable;
  }

  return (
    result.signal ||
    result.executable ||
    result
  );
}

export function validateBacktestResult({
  result = {},
  mode = "signal",
  minimumTrades = 1,
} = {}) {
  const selected =
    resolveMode(
      result,
      mode,
    );

  const metrics =
    selected.metrics || {};

  const analytics =
    selected.analytics || {};

  const trades =
    selected.trades ||
    selected.tradeHistory ||
    selected.completedTrades ||
    [];

  const tradeCount =
    Number(
      metrics.tradeCount ??
      analytics.tradeCount ??
      trades.length ??
      0,
    );

  const checks = [
    check({
      id: "result-exists",
      label:
        "バックテスト結果が存在する",
      passed:
        Boolean(selected),
    }),

    check({
      id: "metrics-exist",
      label:
        "主要指標が生成される",
      passed:
        Boolean(
          selected.metrics,
        ),
    }),

    check({
      id: "analytics-exist",
      label:
        "詳細損益分析が生成される",
      passed:
        Boolean(
          selected.analytics,
        ),
    }),

    check({
      id: "trade-count",
      label:
        "最低取引件数を満たす",
      passed:
        tradeCount >=
        Number(minimumTrades),
      actual:
        tradeCount,
      expected:
        `>= ${minimumTrades}`,
      severity:
        "warning",
    }),

    check({
      id: "return-finite",
      label:
        "総リターンが有限値",
      passed:
        finite(
          metrics
            .totalReturnPercent,
        ),
      actual:
        metrics
          .totalReturnPercent ??
        null,
    }),

    check({
      id: "net-pnl-finite",
      label:
        "純損益が有限値",
      passed:
        finite(
          metrics.netPnl ??
          analytics.totalNetPnl,
        ),
      actual:
        metrics.netPnl ??
        analytics.totalNetPnl ??
        null,
    }),

    check({
      id: "cost-finite",
      label:
        "取引コストが有限値",
      passed:
        finite(
          analytics
            .totalTradingCost,
        ),
      actual:
        analytics
          .totalTradingCost ??
        null,
    }),

    check({
      id: "expectancy-finite",
      label:
        "1取引期待値が有限値",
      passed:
        tradeCount === 0 ||
        finite(
          analytics.expectancy,
        ),
      actual:
        analytics.expectancy ??
        null,
    }),

    check({
      id: "payoff-ratio-valid",
      label:
        "平均損益比が妥当",
      passed:
        tradeCount === 0 ||
        analytics.payoffRatio ===
          null ||
        finite(
          analytics.payoffRatio,
        ),
      actual:
        analytics.payoffRatio ??
        null,
    }),

    check({
      id: "equity-curve-exists",
      label:
        "資産曲線データが存在する",
      passed:
        Array.isArray(
          selected.equityCurve,
        ) &&
        selected.equityCurve.length >
          0,
      actual:
        Array.isArray(
          selected.equityCurve,
        )
          ? selected
              .equityCurve
              .length
          : 0,
      severity:
        "warning",
    }),
  ];

  const errors =
    checks.filter(
      (row) =>
        !row.passed &&
        row.severity ===
          "error",
    );

  const warnings =
    checks.filter(
      (row) =>
        !row.passed &&
        row.severity ===
          "warning",
    );

  const report =
    createBacktestDiagnosticsReport({
      result,
      preferredMode:
        mode,
    });

  return {
    version:
      PHASE_A_VALIDATION_VERSION,

    mode,

    passed:
      errors.length === 0,

    status:
      errors.length > 0
        ? "failed"
        : warnings.length > 0
          ? "warning"
          : "passed",

    checks,
    errors,
    warnings,

    summary: {
      total:
        checks.length,

      passed:
        checks.filter(
          (row) =>
            row.passed,
        ).length,

      failed:
        errors.length,

      warning:
        warnings.length,

      tradeCount,
    },

    diagnostics:
      report,
  };
}

export function validateBacktestModes({
  result = {},
  minimumSignalTrades = 1,
  minimumExecutableTrades = 0,
} = {}) {
  const signal =
    validateBacktestResult({
      result,
      mode:
        "signal",
      minimumTrades:
        minimumSignalTrades,
    });

  const executable =
    validateBacktestResult({
      result,
      mode:
        "executable",
      minimumTrades:
        minimumExecutableTrades,
    });

  return {
    version:
      PHASE_A_VALIDATION_VERSION,

    passed:
      signal.passed &&
      executable.passed,

    status:
      !signal.passed ||
      !executable.passed
        ? "failed"
        : signal.status ===
            "warning" ||
          executable.status ===
            "warning"
          ? "warning"
          : "passed",

    signal,
    executable,
  };
}