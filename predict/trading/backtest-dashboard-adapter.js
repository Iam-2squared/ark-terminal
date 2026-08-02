import {
  createBacktestDiagnosticsReport,
} from "./backtest-diagnostics-report.js";

export const BACKTEST_DASHBOARD_ADAPTER_VERSION =
  "backtest-dashboard-adapter-v1";

export function createBacktestDashboardModel({
  result={},
  preferredMode="signal",
}={}){

  const report=
    createBacktestDiagnosticsReport({
      result,
      preferredMode,
    });

  return{

    version:
      BACKTEST_DASHBOARD_ADAPTER_VERSION,

    report,

    summary:
      report.analytics.summary,

    cards:
      report.analytics.cards,

    diagnosis:
      report.diagnosis,

    exitReasons:
      report.analytics.exitReasons,

    cost:
      report.cost,

    comparison:
      result.comparison??{},
  };

}

export function mergeDashboardModel(
  dashboard={},
  prediction={},
){

  return{

    ...dashboard,

    prediction,

    generatedAt:
      new Date()
        .toISOString(),

  };

}