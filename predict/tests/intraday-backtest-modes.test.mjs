import assert from "node:assert/strict";
import test from "node:test";

import {
  runIntradayBacktestModes,
} from "../trading/intraday-backtest-modes.js";

const START = 1_700_000_000;

function candle(
  index,
  overrides = {},
) {
  const close =
    overrides.close ?? 3_000;

  return {
    time:
      START +
      index * 900,

    open:
      overrides.open ??
      close,

    high:
      overrides.high ??
      close + 5,

    low:
      overrides.low ??
      close - 5,

    close,

    volume:
      overrides.volume ??
      100,

    sessionDate:
      "2026-08-03",

    isClosed: true,
  };
}

function waitDecision() {
  return {
    paperCandidate: false,
    action: "wait",

    plan: {
      action: "wait",
    },

    analysis: {
      setup: "wait",
    },
  };
}

function candidateDecision(
  candles,
) {
  const latest =
    candles.at(-1);

  return {
    paperCandidate: true,
    action: "enter_long",

    plan: {
      side: "long",
    },

    analysis: {
      ready: true,

      setup:
        "breakout_long",

      entryCondition:
        "テストシグナル",

      atr: 10,

      setupStrengthScore:
        90,

      dataQualityScore:
        100,

      tradeSignal: {
        direction: "強気",

        currentPrice:
          latest.close,

        atr: 10,

        confidenceScore:
          90,

        dataQualityScore:
          100,

        spreadPercent:
          0,

        dataAgeSeconds:
          0,

        setup:
          "breakout_long",

        entryCondition:
          "テストシグナル",

        marketBlocked:
          false,
      },
    },
  };
}

test("シグナル性能と実行可能性を分離して比較する", () => {
  const candles = [
    candle(0),
    candle(1),

    candle(2, {
      open: 3_000,
      high: 3_020,
      low: 2_990,
      close: 3_010,
    }),

    candle(3, {
      open: 3_010,
      high: 3_030,
      low: 3_005,
      close: 3_025,
    }),
  ];

  const decisionProvider = ({
    intradayHistory,
  }) =>
    intradayHistory
      .candles.length === 2
      ? candidateDecision(
          intradayHistory.candles,
        )
      : waitDecision();

  const modes =
    runIntradayBacktestModes({
      symbol: "7203.T",

      intradayHistory: {
        candles,
      },

      initialEquity:
        1_000_000,

      executableLotSize:
        100,

      signalLotSize:
        1,

      commonPolicy: {
        minimumWarmupBars:
          2,

        commissionPercentPerSide:
          0,

        spreadPercent:
          0,

        slippagePercentPerSide:
          0,
      },

      decisionProvider,
    });

  assert.equal(
    modes.signal
      .evaluationMode,
    "signal",
  );

  assert.equal(
    modes.executable
      .evaluationMode,
    "executable",
  );

  assert.equal(
    modes.signal
      .metrics
      .tradeCount,
    1,
  );

  assert.equal(
    modes.executable
      .metrics
      .tradeCount,
    0,
  );

  assert.equal(
    modes.comparison
      .tradeCountDifference,
    1,
  );

  assert.equal(
    modes.signal
      .modeConstraints
      .lotSize,
    1,
  );

  assert.equal(
    modes.executable
      .modeConstraints
      .lotSize,
    100,
  );
});