import assert from "node:assert/strict";
import test from "node:test";

import {
  createIntradayTradingDecision,
} from "../trading/intraday-trading-decision.js";

const START = 1_700_000_000;

function candle(
  index,
  overrides = {},
) {
  const close =
    overrides.close ??
    100 + index * 0.01;

  return {
    time: START + index * 900,
    open:
      overrides.open ??
      close - 0.05,
    high:
      overrides.high ??
      close + 0.2,
    low:
      overrides.low ??
      close - 0.2,
    close,
    volume:
      overrides.volume ?? 100,
    sessionDate: "2026-08-01",
    isClosed: true,
  };
}

function history(count = 25) {
  return {
    candles: Array.from(
      { length: count },
      (_, index) =>
        candle(index),
    ),
  };
}

function account() {
  return {
    executionMode: "paper",
    equity: 5_000_000,
    openPositions: 0,
    dailyPnlPercent: 0,
    consecutiveLosses: 0,
  };
}

test("出来高を伴う高値突破からPaper買い候補を作る", () => {
  const data = history();
  const latest =
    data.candles.at(-1);

  latest.open = 101.5;
  latest.low = 101.4;
  latest.high = 103.2;
  latest.close = 103;
  latest.volume = 300;

  const decision =
    createIntradayTradingDecision({
      symbol: "7203.T",
      intradayHistory: data,
      account: account(),
      nowSeconds:
        latest.time + 901,
    });

  assert.equal(
    decision.action,
    "enter_long",
  );

  assert.equal(
    decision.paperCandidate,
    true,
  );

  assert.equal(
    decision.liveExecutionAllowed,
    false,
  );

  assert.equal(
    decision.plan.quantity % 100,
    0,
  );
});

test("セットアップ未成立時は注文せず待機する", () => {
  const data = history();
  const latest =
    data.candles.at(-1);

  const decision =
    createIntradayTradingDecision({
      symbol: "7203.T",
      intradayHistory: data,
      account: account(),
      nowSeconds:
        latest.time + 901,
    });

  assert.equal(
    decision.action,
    "wait",
  );

  assert.equal(
    decision.paperCandidate,
    false,
  );
});

test("古い15分足ではPaper取引も停止する", () => {
  const data = history();
  const latest =
    data.candles.at(-1);

  const decision =
    createIntradayTradingDecision({
      symbol: "7203.T",
      intradayHistory: data,
      account: account(),
      nowSeconds:
        latest.time + 900 + 5000,
    });

  assert.equal(
    decision.action,
    "blocked",
  );

  assert.equal(
    decision.analysis.marketBlocked,
    true,
  );
});

test("15分足がない場合は取得失敗として扱う", () => {
  const decision =
    createIntradayTradingDecision({
      symbol: "7203.T",
      intradayHistory: null,
      account: account(),
    });

  assert.equal(
    decision.available,
    false,
  );

  assert.equal(
    decision.action,
    "blocked",
  );
});

test("下降セットアップでも空売りせず現物買いを見送る", () => {
  const data = history();

  const latest =
    data.candles.at(-1);

  latest.open = 98;
  latest.high = 98.1;
  latest.low = 96.8;
  latest.close = 97;
  latest.volume = 300;

  const decision =
    createIntradayTradingDecision({
      symbol: "7203.T",

      intradayHistory:
        data,

      account:
        account(),

      nowSeconds:
        latest.time + 901,
    });

  assert.equal(
    decision.analysis.setup,
    "breakout_short",
  );

  assert.equal(
    decision.action,
    "wait",
  );

  assert.equal(
    decision.paperCandidate,
    false,
  );

  assert.equal(
    decision.reasons.some(
      (reason) =>
        reason.includes(
          "現物買いを見送",
        ),
    ),
    true,
  );
});
