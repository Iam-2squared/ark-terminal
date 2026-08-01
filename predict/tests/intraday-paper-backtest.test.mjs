import assert from "node:assert/strict";
import test from "node:test";

import {
  runIntradayPaperBacktest,
} from "../trading/intraday-paper-backtest.js";

const START = 1_700_000_000;

function candle(
  index,
  overrides = {},
) {
  const close =
    overrides.close ?? 100;

  return {
    time:
      START +
      index * 900,

    open:
      overrides.open ??
      close,

    high:
      overrides.high ??
      close + 0.5,

    low:
      overrides.low ??
      close - 0.5,

    close,

    volume:
      overrides.volume ??
      100,

    sessionDate:
      overrides.sessionDate ??
      "2026-08-03",

    isClosed: true,
  };
}

function candidateDecision(
  side,
  candles,
  atr = 2,
) {
  const latest =
    candles.at(-1);

  const long =
    side === "long";

  return {
    paperCandidate: true,

    action:
      long
        ? "enter_long"
        : "enter_short",

    plan: {
      side,
    },

    analysis: {
      setup:
        long
          ? "breakout_long"
          : "breakout_short",

      entryCondition:
        "テストシグナル",

      atr,

      setupStrengthScore: 90,
      dataQualityScore: 100,

      tradeSignal: {
        direction:
          long
            ? "強気"
            : "弱気",

        currentPrice:
          latest.close,

        atr,

        confidenceScore: 90,
        dataQualityScore: 100,
        spreadPercent: 0,
        dataAgeSeconds: 0,

        setup:
          long
            ? "breakout_long"
            : "breakout_short",

        entryCondition:
          "テストシグナル",

        marketBlocked: false,
      },
    },
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

function providerAt(
  targetLength,
  side = "long",
  observedLengths = [],
) {
  return ({
    intradayHistory,
  }) => {
    const length =
      intradayHistory
        .candles.length;

    observedLengths.push(
      length,
    );

    return length ===
      targetLength
      ? candidateDecision(
          side,
          intradayHistory.candles,
        )
      : waitDecision();
  };
}

function zeroCosts(
  overrides = {},
) {
  return {
    initialEquity: 100_000,
    minimumWarmupBars: 2,
    lotSize: 1,

    commissionPercentPerSide: 0,
    spreadPercent: 0,
    slippagePercentPerSide: 0,
    minimumCommission: 0,

    ...overrides,
  };
}

test("シグナル確定後の次足始値で入り未来の足を渡さない", () => {
  const observed = [];

  const candles = [
    candle(0),
    candle(1),
    candle(2, {
      open: 101,
      high: 101.5,
      low: 100.5,
      close: 101,
    }),
    candle(3, {
      open: 101,
      high: 102.2,
      low: 100.8,
      close: 102,
    }),
  ];

  const result =
    runIntradayPaperBacktest({
      symbol: "7203.T",

      intradayHistory: {
        candles,
      },

      policy:
        zeroCosts(),

      decisionProvider:
        providerAt(
          2,
          "long",
          observed,
        ),
    });

  assert.deepEqual(
    observed,
    [2],
  );

  assert.equal(
    result.trades.length,
    1,
  );

  assert.equal(
    result.trades[0].signalTime,
    candles[1].time,
  );

  assert.equal(
    result.trades[0].entryTime,
    candles[2].time,
  );

  assert.equal(
    result.trades[0].entryPrice,
    101,
  );

  assert.equal(
    result.dataPolicy.entryTiming,
    "next_bar_open",
  );
});

test("同じ足で損切りと利確に触れた場合は損切りを優先する", () => {
  const candles = [
    candle(0),
    candle(1),
    candle(2, {
      open: 100,
      high: 106,
      low: 97,
      close: 100,
    }),
  ];

  const result =
    runIntradayPaperBacktest({
      symbol: "7203.T",

      intradayHistory: {
        candles,
      },

      policy:
        zeroCosts(),

      decisionProvider:
        providerAt(2),
    });

  assert.equal(
    result.trades.length,
    1,
  );

  assert.match(
    result.trades[0].exitReason,
    /損切り/,
  );

  assert.ok(
    result.trades[0].netPnl < 0,
  );
});

test("損切り価格を飛び越えた場合は不利な始値で決済する", () => {
  const candles = [
    candle(0),
    candle(1),

    candle(2, {
      open: 100,
      high: 101,
      low: 99,
      close: 100,
    }),

    candle(3, {
      open: 95,
      high: 96,
      low: 94,
      close: 95,
    }),
  ];

  const result =
    runIntradayPaperBacktest({
      symbol: "7203.T",

      intradayHistory: {
        candles,
      },

      policy:
        zeroCosts(),

      decisionProvider:
        providerAt(2),
    });

  assert.equal(
    result.trades[0].exitReason,
    "損切りギャップ",
  );

  assert.equal(
    result.trades[0].exitPrice,
    95,
  );
});

test("第1利確後に残数量を第2利確できる", () => {
  const candles = [
    candle(0),
    candle(1),

    candle(2, {
      open: 100,
      high: 103.5,
      low: 99,
      close: 103,
    }),

    candle(3, {
      open: 103,
      high: 105.5,
      low: 102,
      close: 105,
    }),
  ];

  const result =
    runIntradayPaperBacktest({
      symbol: "7203.T",

      intradayHistory: {
        candles,
      },

      policy:
        zeroCosts(),

      decisionProvider:
        providerAt(2),
    });

  assert.equal(
    result.trades.length,
    1,
  );

  assert.equal(
    result.trades[0].fills.length,
    3,
  );

  assert.equal(
    result.trades[0].fills[1].reason,
    "第1利確",
  );

  assert.equal(
    result.trades[0].fills[2].reason,
    "第2利確",
  );

  assert.ok(
    result.trades[0].netPnl > 0,
  );
});

test("空売り候補も次足始値から利益を計算できる", () => {
  const candles = [
    candle(0),
    candle(1),

    candle(2, {
      open: 100,
      high: 100.5,
      low: 94.5,
      close: 95,
    }),
  ];

  const result =
    runIntradayPaperBacktest({
      symbol: "7203.T",

      intradayHistory: {
        candles,
      },

      policy:
        zeroCosts(),

      decisionProvider:
        providerAt(
          2,
          "short",
        ),
    });

  assert.equal(
    result.trades[0].side,
    "short",
  );

  assert.ok(
    result.trades[0].netPnl > 0,
  );
});

test("手数料・スプレッド・スリッページを損益へ反映する", () => {
  const candles = [
    candle(0),
    candle(1),

    candle(2, {
      open: 100,
      high: 100.5,
      low: 99.5,
      close: 100,
    }),

    candle(3, {
      open: 100,
      high: 100.5,
      low: 99.5,
      close: 100,
    }),
  ];

  const result =
    runIntradayPaperBacktest({
      symbol: "7203.T",

      intradayHistory: {
        candles,
      },

      policy:
        zeroCosts({
          commissionPercentPerSide: 0.1,
          spreadPercent: 0.2,
          slippagePercentPerSide: 0.1,
        }),

      decisionProvider:
        providerAt(2),
    });

  assert.ok(
    result.trades[0].netPnl < 0,
  );

  assert.ok(
    result.estimatedCosts.total > 0,
  );

  assert.ok(
    result.metrics.maximumDrawdownPercent <
      0,
  );

  assert.equal(
    result.comparison.noTradeReturnPercent,
    0,
  );

  assert.equal(
    result.equityCurve.length,
    candles.length,
  );
});

test("セッションをまたぐ次足エントリーは標準設定で拒否する", () => {
  const candles = [
    candle(0, {
      sessionDate:
        "2026-08-03",
    }),

    candle(1, {
      sessionDate:
        "2026-08-03",
    }),

    candle(2, {
      sessionDate:
        "2026-08-04",
    }),
  ];

  const result =
    runIntradayPaperBacktest({
      symbol: "7203.T",

      intradayHistory: {
        candles,
      },

      policy:
        zeroCosts(),

      decisionProvider:
        providerAt(2),
    });

  assert.equal(
    result.trades.length,
    0,
  );

  assert.equal(
    result.meta.candidateCount,
    1,
  );

  assert.equal(
    result.meta.skippedCandidateCount,
    1,
  );
});