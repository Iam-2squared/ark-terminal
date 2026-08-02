import {
  createTradeAnalyticsViewModel,
} from "./trade-analytics-presenter.js";

export const BACKTEST_DIAGNOSTICS_REPORT_VERSION =
  "backtest-diagnostics-report-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function numberOrNull(value) {
  return finite(value)
    ? Number(value)
    : null;
}

function resolveModeResult(
  result = {},
  preferredMode = "signal",
) {
  if (
    preferredMode === "executable" &&
    result.executable
  ) {
    return result.executable;
  }

  if (result.signal) {
    return result.signal;
  }

  if (result.executable) {
    return result.executable;
  }

  return result;
}

function createCostSummary(
  modeResult = {},
) {
  const analytics =
    modeResult.analytics || {};

  const metrics =
    modeResult.metrics || {};

  const totalTradingCost =
    numberOrNull(
      analytics.totalTradingCost ??
      metrics.totalTradingCost ??
      metrics.estimatedTradingCost,
    );

  const grossPnlBeforeCosts =
    numberOrNull(
      analytics.grossPnlBeforeCosts ??
      metrics.grossPnlBeforeCosts,
    );

  const totalNetPnl =
    numberOrNull(
      analytics.totalNetPnl ??
      metrics.netPnl ??
      metrics.totalPnl,
    );

  return {
    totalTradingCost,
    grossPnlBeforeCosts,
    totalNetPnl,

    commissionCost:
      numberOrNull(
        analytics.commissionCost ??
        metrics.commissionCost,
      ),

    spreadCost:
      numberOrNull(
        analytics.spreadCost ??
        metrics.spreadCost,
      ),

    slippageCost:
      numberOrNull(
        analytics.slippageCost ??
        metrics.slippageCost,
      ),

    costDragPercent:
      numberOrNull(
        analytics.costDragPercent,
      ),
  };
}

function createFailureReasons(
  modeResult = {},
) {
  const diagnostics =
    modeResult.diagnostics || {};

  const rows = [
    {
      id: "plan-rejected",
      label: "最終ゲート拒否",
      count:
        Number(
          diagnostics.planRejectedCount ||
          diagnostics.rejectedCount ||
          0,
        ),
    },
    {
      id: "insufficient-bars",
      label: "15分足不足判定",
      count:
        Number(
          diagnostics.insufficientBarsCount ||
          diagnostics.insufficientHistoryCount ||
          0,
        ),
    },
    {
      id: "stale-data",
      label: "古いデータ拒否",
      count:
        Number(
          diagnostics.staleDataCount ||
          diagnostics.staleRejectedCount ||
          0,
        ),
    },
    {
      id: "duplicate-order",
      label: "重複注文拒否",
      count:
        Number(
          diagnostics.duplicateOrderCount ||
          diagnostics.duplicateRejectedCount ||
          0,
        ),
    },
    {
      id: "risk-limit",
      label: "リスク制限拒否",
      count:
        Number(
          diagnostics.riskLimitCount ||
          diagnostics.riskRejectedCount ||
          0,
        ),
    },
    {
      id: "position-size",
      label: "数量不足拒否",
      count:
        Number(
          diagnostics.positionSizeRejectedCount ||
          diagnostics.lotSizeRejectedCount ||
          0,
        ),
    },
  ];

  return rows.filter(
    (row) => row.count > 0,
  );
}

function createDiagnosis({
  analytics = {},
  cost = {},
  failureReasons = [],
} = {}) {
  const messages = [];

  const tradeCount =
    Number(
      analytics.tradeCount || 0,
    );

  const expectancy =
    numberOrNull(
      analytics.expectancy,
    );

  const payoffRatio =
    numberOrNull(
      analytics.payoffRatio,
    );

  const winRate =
    numberOrNull(
      analytics.winRate,
    );

  if (tradeCount === 0) {
    messages.push({
      level: "info",
      code: "NO_TRADES",
      message:
        "確定取引がないため、戦略の収益性はまだ評価できません。",
    });
  }

  if (
    tradeCount > 0 &&
    finite(expectancy) &&
    expectancy < 0
  ) {
    messages.push({
      level: "danger",
      code: "NEGATIVE_EXPECTANCY",
      message:
        "1取引期待値がマイナスです。エントリー条件または決済条件の改善が必要です。",
    });
  }

  if (
    tradeCount > 0 &&
    finite(payoffRatio) &&
    payoffRatio < 1
  ) {
    messages.push({
      level: "warning",
      code: "WEAK_PAYOFF_RATIO",
      message:
        "平均利益より平均損失が大きく、損益比が不利です。",
    });
  }

  if (
    tradeCount >= 5 &&
    finite(winRate) &&
    winRate < 40
  ) {
    messages.push({
      level: "warning",
      code: "LOW_WIN_RATE",
      message:
        "勝率が40%未満です。シグナル選別精度を確認してください。",
    });
  }

  if (
    finite(cost.costDragPercent) &&
    cost.costDragPercent > 30
  ) {
    messages.push({
      level: "warning",
      code: "HIGH_COST_DRAG",
      message:
        "取引コストがコスト控除前損益の30%以上を占めています。",
    });
  }

  const totalRejected =
    failureReasons.reduce(
      (sum, row) =>
        sum + row.count,
      0,
    );

  if (
    tradeCount > 0 &&
    totalRejected >
      tradeCount * 10
  ) {
    messages.push({
      level: "info",
      code: "STRICT_GATE",
      message:
        "取引回数に対して拒否件数が非常に多く、最終ゲートはかなり厳格です。",
    });
  }

  if (!messages.length) {
    messages.push({
      level: "success",
      code: "NO_MAJOR_WARNING",
      message:
        "現時点で重大な異常は検出されていません。",
    });
  }

  return messages;
}

export function createBacktestDiagnosticsReport({
  result = {},
  preferredMode = "signal",
  symbol = null,
  generatedAt =
    new Date().toISOString(),
} = {}) {
  const modeResult =
    resolveModeResult(
      result,
      preferredMode,
    );

  const analytics =
    modeResult.analytics || {};

  const analyticsView =
    createTradeAnalyticsViewModel(
      analytics,
    );

  const cost =
    createCostSummary(
      modeResult,
    );

  const failureReasons =
    createFailureReasons(
      modeResult,
    );

  const diagnosis =
    createDiagnosis({
      analytics,
      cost,
      failureReasons,
    });

  return {
    version:
      BACKTEST_DIAGNOSTICS_REPORT_VERSION,

    generatedAt,

    symbol:
      symbol ??
      result.symbol ??
      modeResult.symbol ??
      null,

    preferredMode,

    evaluationMode:
      modeResult.evaluationMode ??
      preferredMode,

    evaluationModeLabel:
      modeResult.evaluationModeLabel ??
      (
        preferredMode ===
        "executable"
          ? "実行可能性"
          : "シグナル性能"
      ),

    status:
      analyticsView.status,

    analytics:
      analyticsView,

    cost,

    failureReasons,

    diagnosis,

    metrics:
      modeResult.metrics || {},

    diagnostics:
      modeResult.diagnostics || {},

    meta:
      modeResult.meta || {},
  };
}

export function exportBacktestDiagnosticsJson(
  report = {},
) {
  return JSON.stringify(
    report,
    null,
    2,
  );
}

function csvEscape(value) {
  const text =
    String(
      value ?? "",
    );

  if (
    text.includes(",") ||
    text.includes('"') ||
    text.includes("\n")
  ) {
    return (
      '"' +
      text.replaceAll(
        '"',
        '""',
      ) +
      '"'
    );
  }

  return text;
}

export function exportBacktestDiagnosticsCsv(
  report = {},
) {
  const rows = [
    [
      "category",
      "id",
      "label",
      "value",
    ],
  ];

  rows.push([
    "summary",
    "symbol",
    "銘柄",
    report.symbol ?? "",
  ]);

  rows.push([
    "summary",
    "mode",
    "評価モード",
    report.evaluationModeLabel ??
      "",
  ]);

  for (
    const card of
    report.analytics?.cards || []
  ) {
    rows.push([
      "analytics",
      card.id,
      card.label,
      card.rawValue ??
        card.value ??
        "",
    ]);
  }

  for (
    const row of
    report.failureReasons || []
  ) {
    rows.push([
      "failure_reason",
      row.id,
      row.label,
      row.count,
    ]);
  }

  for (
    const row of
    report.diagnosis || []
  ) {
    rows.push([
      "diagnosis",
      row.code,
      row.level,
      row.message,
    ]);
  }

  return rows
    .map(
      (row) =>
        row
          .map(csvEscape)
          .join(","),
    )
    .join("\n");
}

export const BacktestDiagnosticsReportInternals = {
  finite,
  numberOrNull,
  resolveModeResult,
  createCostSummary,
  createFailureReasons,
  createDiagnosis,
  csvEscape,
};