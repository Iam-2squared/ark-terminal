import test from "node:test";
import assert from "node:assert/strict";

import {
  createBacktestDiagnosticsReport,
  exportBacktestDiagnosticsCsv,
  exportBacktestDiagnosticsJson,
} from "../trading/backtest-diagnostics-report.js";

test(
  "Signalモードから診断レポートを生成",
  () => {
    const report =
      createBacktestDiagnosticsReport({
        result: {
          symbol: "2805.T",

          signal: {
            evaluationMode:
              "signal",

            evaluationModeLabel:
              "シグナル性能",

            analytics: {
              tradeCount: 10,
              winCount: 4,
              lossCount: 6,
              winRate: 40,
              expectancy: -200,
              payoffRatio: 0.8,
              averageWin: 500,
              averageLoss: -625,
              totalTradingCost: 1_000,
              grossPnlBeforeCosts: -1_000,
              totalNetPnl: -2_000,
              costDragPercent: 100,
            },

            diagnostics: {
              planRejectedCount: 120,
              insufficientBarsCount: 30,
            },
          },
        },
      });

    assert.equal(
      report.symbol,
      "2805.T",
    );

    assert.equal(
      report.evaluationMode,
      "signal",
    );

    assert.equal(
      report.analytics
        .summary.tradeCount,
      10,
    );

    assert.equal(
      report.cost.totalTradingCost,
      1_000,
    );

    assert.equal(
      report.failureReasons.length,
      2,
    );

    assert.ok(
      report.diagnosis.some(
        (row) =>
          row.code ===
          "NEGATIVE_EXPECTANCY",
      ),
    );

    assert.ok(
      report.diagnosis.some(
        (row) =>
          row.code ===
          "WEAK_PAYOFF_RATIO",
      ),
    );

    assert.ok(
      report.diagnosis.some(
        (row) =>
          row.code ===
          "HIGH_COST_DRAG",
      ),
    );
  },
);

test(
  "Executableモードを指定可能",
  () => {
    const report =
      createBacktestDiagnosticsReport({
        preferredMode:
          "executable",

        result: {
          signal: {
            analytics: {
              tradeCount: 5,
            },
          },

          executable: {
            evaluationMode:
              "executable",

            analytics: {
              tradeCount: 2,
              winCount: 2,
              lossCount: 0,
              expectancy: 300,
            },
          },
        },
      });

    assert.equal(
      report.evaluationMode,
      "executable",
    );

    assert.equal(
      report.analytics
        .summary.tradeCount,
      2,
    );
  },
);

test(
  "確定取引0件ではNO_TRADES診断",
  () => {
    const report =
      createBacktestDiagnosticsReport({
        result: {
          signal: {
            analytics: {
              tradeCount: 0,
            },
          },
        },
      });

    assert.ok(
      report.diagnosis.some(
        (row) =>
          row.code ===
          "NO_TRADES",
      ),
    );
  },
);

test(
  "JSONへ書き出し",
  () => {
    const report =
      createBacktestDiagnosticsReport({
        result: {
          symbol: "7203.T",

          signal: {
            analytics: {
              tradeCount: 1,
              winCount: 1,
              lossCount: 0,
              expectancy: 100,
            },
          },
        },
      });

    const json =
      exportBacktestDiagnosticsJson(
        report,
      );

    const parsed =
      JSON.parse(json);

    assert.equal(
      parsed.symbol,
      "7203.T",
    );

    assert.equal(
      parsed.analytics
        .summary.tradeCount,
      1,
    );
  },
);

test(
  "CSVへ主要指標と診断を書き出し",
  () => {
    const report =
      createBacktestDiagnosticsReport({
        result: {
          symbol: "7203.T",

          signal: {
            analytics: {
              tradeCount: 1,
              winCount: 0,
              lossCount: 1,
              expectancy: -500,
              payoffRatio: 0.5,
            },

            diagnostics: {
              planRejectedCount: 20,
            },
          },
        },
      });

    const csv =
      exportBacktestDiagnosticsCsv(
        report,
      );

    assert.match(
      csv,
      /category,id,label,value/,
    );

    assert.match(
      csv,
      /7203\.T/,
    );

    assert.match(
      csv,
      /NEGATIVE_EXPECTANCY/,
    );

    assert.match(
      csv,
      /plan-rejected/,
    );
  },
);