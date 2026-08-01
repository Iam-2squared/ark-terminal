import {
  runIntradayPaperBacktest,
} from "./intraday-paper-backtest.js";

export const INTRADAY_BACKTEST_MODES_VERSION =
  "intraday-backtest-modes-v1";

export const BACKTEST_EVALUATION_MODES =
  Object.freeze({
    SIGNAL: "signal",
    EXECUTABLE: "executable",
  });

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function positive(value) {
  return finite(value) &&
    Number(value) > 0;
}

export function runIntradayBacktestModes({
  symbol,
  intradayHistory,

  initialEquity = 1_000_000,
  executableLotSize = 100,
  signalLotSize = 1,

  signalMaximumPositionPercent = 100,
  executableMaximumPositionPercent = 20,

  commonPolicy = {},
  commonStrategyPolicy = {},

  decisionProvider,
} = {}) {
  const resolvedEquity =
    positive(initialEquity)
      ? Number(initialEquity)
      : 1_000_000;

  const providerOption =
    typeof decisionProvider === "function"
      ? {
          decisionProvider,
        }
      : {};

  const basePolicy = {
    initialEquity:
      resolvedEquity,

    commissionPercentPerSide:
      0.05,

    spreadPercent:
      0.1,

    slippagePercentPerSide:
      0.05,

    closeAtSessionEnd:
      true,

    allowOvernightEntry:
      false,

    ...(commonPolicy || {}),
  };

  const executableStrategyPolicy = {
    ...(commonStrategyPolicy || {}),

    trading: {
      ...(
        commonStrategyPolicy
          ?.trading || {}
      ),

      maximumPositionPercent:
        Number(
          executableMaximumPositionPercent,
        ),
    },
  };

  const signalStrategyPolicy = {
    ...(commonStrategyPolicy || {}),

    trading: {
      ...(
        commonStrategyPolicy
          ?.trading || {}
      ),

      maximumPositionPercent:
        Number(
          signalMaximumPositionPercent,
        ),
    },
  };

  const executableResult =
    runIntradayPaperBacktest({
      symbol,
      intradayHistory,

      policy: {
        ...basePolicy,

        lotSize:
          Math.max(
            1,
            Math.floor(
              Number(
                executableLotSize,
              ) || 1,
            ),
          ),
      },

      strategyPolicy:
        executableStrategyPolicy,

      ...providerOption,
    });

  const signalResult =
    runIntradayPaperBacktest({
      symbol,
      intradayHistory,

      policy: {
        ...basePolicy,

        lotSize:
          Math.max(
            1,
            Math.floor(
              Number(signalLotSize) ||
              1,
            ),
          ),
      },

      strategyPolicy:
        signalStrategyPolicy,

      ...providerOption,
    });

  const executable = {
    ...executableResult,

    evaluationMode:
      BACKTEST_EVALUATION_MODES
        .EXECUTABLE,

    evaluationModeLabel:
      "実行可能性",

    modeConstraints: {
      lotSize:
        Math.max(
          1,
          Math.floor(
            Number(
              executableLotSize,
            ) || 1,
          ),
        ),

      maximumPositionPercent:
        Number(
          executableMaximumPositionPercent,
        ),
    },
  };

  const signal = {
    ...signalResult,

    evaluationMode:
      BACKTEST_EVALUATION_MODES
        .SIGNAL,

    evaluationModeLabel:
      "シグナル性能",

    modeConstraints: {
      lotSize:
        Math.max(
          1,
          Math.floor(
            Number(signalLotSize) ||
            1,
          ),
        ),

      maximumPositionPercent:
        Number(
          signalMaximumPositionPercent,
        ),
    },
  };

  return {
    version:
      INTRADAY_BACKTEST_MODES_VERSION,

    symbol,

    signal,
    executable,

    comparison: {
      signalTradeCount:
        Number(
          signal.metrics
            ?.tradeCount || 0,
        ),

      executableTradeCount:
        Number(
          executable.metrics
            ?.tradeCount || 0,
        ),

      tradeCountDifference:
        Number(
          signal.metrics
            ?.tradeCount || 0,
        ) -
        Number(
          executable.metrics
            ?.tradeCount || 0,
        ),

      signalCandidateCount:
        Number(
          signal.meta
            ?.candidateCount || 0,
        ),

      executableCandidateCount:
        Number(
          executable.meta
            ?.candidateCount || 0,
        ),

      candidateCountDifference:
        Number(
          signal.meta
            ?.candidateCount || 0,
        ) -
        Number(
          executable.meta
            ?.candidateCount || 0,
        ),

      signalReturnPercent:
        signal.metrics
          ?.totalReturnPercent ??
        null,

      executableReturnPercent:
        executable.metrics
          ?.totalReturnPercent ??
        null,

      signalRejectedCount:
        Number(
          signal.diagnostics
            ?.planRejectedCount || 0,
        ),

      executableRejectedCount:
        Number(
          executable.diagnostics
            ?.planRejectedCount || 0,
        ),
    },

    interpretation: {
      signalMode:
        "1株単位・最大投資額100%で、売買シグナル自体を検証します。",

      executableMode:
        "実際の売買単元・仮想資産・最大投資額20%を含めて検証します。",

      detailedDisplay:
        "資産曲線と売買履歴はシグナル性能モードを表示します。",
    },
  };
}

export const IntradayBacktestModesInternals = {
  finite,
  positive,
};