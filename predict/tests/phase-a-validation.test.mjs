import test from "node:test";
import assert from "node:assert/strict";

import {
  validateBacktestModes,
  validateBacktestResult,
} from "../trading/phase-a-validation.js";

function validModeResult() {
  return {
    metrics: {
      tradeCount: 2,
      totalReturnPercent: 1.2,
      netPnl: 12_000,
    },

    analytics: {
      tradeCount: 2,
      totalNetPnl: 12_000,
      totalTradingCost: 400,
      expectancy: 6_000,
      payoffRatio: 1.5,
    },

    equityCurve: [
      {
        equity: 1_000_000,
      },
      {
        equity: 1_012_000,
      },
    ],
  };
}

test(
  "正常な結果は検証を通過",
  () => {
    const result =
      validateBacktestResult({
        result: {
          signal:
            validModeResult(),
        },
      });

    assert.equal(
      result.passed,
      true,
    );

    assert.equal(
      result.summary.tradeCount,
      2,
    );

    assert.equal(
      result.errors.length,
      0,
    );
  },
);

test(
  "Analytics欠落を検出",
  () => {
    const result =
      validateBacktestResult({
        result: {
          signal: {
            metrics: {
              tradeCount: 1,
              totalReturnPercent: 1,
              netPnl: 100,
            },

            equityCurve: [
              {
                equity: 1_000_100,
              },
            ],
          },
        },
      });

    assert.equal(
      result.passed,
      false,
    );

    assert.ok(
      result.errors.some(
        (row) =>
          row.id ===
          "analytics-exist",
      ),
    );
  },
);

test(
  "最低取引件数不足は警告",
  () => {
    const mode =
      validModeResult();

    mode.metrics.tradeCount = 2;
    mode.analytics.tradeCount = 2;

    const result =
      validateBacktestResult({
        result: {
          signal: mode,
        },

        minimumTrades: 5,
      });

    assert.equal(
      result.passed,
      true,
    );

    assert.equal(
      result.status,
      "warning",
    );

    assert.ok(
      result.warnings.some(
        (row) =>
          row.id ===
          "trade-count",
      ),
    );
  },
);

test(
  "SignalとExecutableを一括検証",
  () => {
    const result =
      validateBacktestModes({
        result: {
          signal:
            validModeResult(),

          executable:
            validModeResult(),
        },
      });

    assert.equal(
      result.passed,
      true,
    );

    assert.equal(
      result.signal.passed,
      true,
    );

    assert.equal(
      result.executable.passed,
      true,
    );
  },
);