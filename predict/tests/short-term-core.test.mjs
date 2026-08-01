import assert from "node:assert/strict";
import test from "node:test";

import {
  createPaperOrder,
  createShortTermTradePlan,
  DEFAULT_SHORT_TERM_POLICY,
  directionToSide,
  evaluateOpenPosition,
  POSITION_SIDES,
  TRADE_ACTIONS,
} from "../trading/short-term-core.js";

function account(overrides = {}) {
  return {
    executionMode: "paper",
    equity: 1_000_000,
    openPositions: 0,
    dailyPnlPercent: 0,
    consecutiveLosses: 0,
    ...overrides,
  };
}

function signal(overrides = {}) {
  return {
    direction: "強気",
    confidenceScore: 80,
    dataQualityScore: 95,
    currentPrice: 1_000,
    atr: 20,
    spreadPercent: 0.1,
    dataAgeSeconds: 10,
    setup: "breakout",
    entryCondition: "直近高値突破",
    ...overrides,
  };
}

test("強気・弱気・中立を売買方向へ変換する", () => {
  assert.equal(
    directionToSide("強気"),
    POSITION_SIDES.LONG,
  );
  assert.equal(
    directionToSide("弱気"),
    POSITION_SIDES.SHORT,
  );
  assert.equal(
    directionToSide("中立"),
    POSITION_SIDES.FLAT,
  );
});

test("中立シグナルは注文せず待機する", () => {
  const plan = createShortTermTradePlan({
    signal: signal({
      direction: "中立",
    }),
    account: account(),
  });

  assert.equal(plan.executable, false);
  assert.equal(
    plan.action,
    TRADE_ACTIONS.WAIT,
  );
});

test("信頼度不足や古いデータを拒否する", () => {
  const plan = createShortTermTradePlan({
    signal: signal({
      confidenceScore: 40,
      dataAgeSeconds: 300,
    }),
    account: account(),
  });

  assert.equal(plan.executable, false);
  assert.equal(
    plan.action,
    TRADE_ACTIONS.BLOCKED,
  );
  assert.equal(
    plan.reasons.some((reason) =>
      reason.includes("信頼度"),
    ),
    true,
  );
  assert.equal(
    plan.reasons.some((reason) =>
      reason.includes("古い"),
    ),
    true,
  );
});

test("買い計画にATR損切り・2段階利確・数量を設定する", () => {
  const plan = createShortTermTradePlan({
    signal: signal(),
    account: account(),
    lotSize: 100,
  });

  assert.equal(plan.executable, true);
  assert.equal(
    plan.action,
    TRADE_ACTIONS.ENTER_LONG,
  );
  assert.equal(plan.entryPrice, 1_000);
  assert.equal(plan.stopPrice, 976);
  assert.equal(
    plan.firstTargetPrice,
    1_030,
  );
  assert.equal(
    plan.secondTargetPrice,
    1_050,
  );
  assert.equal(plan.quantity, 200);
  assert.ok(plan.riskReward > 2);
  assert.equal(
    plan.liveExecutionAllowed,
    false,
  );
});

test("弱気シグナルから空売り計画を作成する", () => {
  const plan = createShortTermTradePlan({
    signal: signal({
      direction: "弱気",
    }),
    account: account(),
    lotSize: 100,
  });

  assert.equal(plan.executable, true);
  assert.equal(
    plan.action,
    TRADE_ACTIONS.ENTER_SHORT,
  );
  assert.equal(plan.stopPrice, 1_024);
  assert.equal(
    plan.firstTargetPrice,
    970,
  );
  assert.equal(
    plan.secondTargetPrice,
    950,
  );
});

test("1日の損失上限到達後は新規取引を停止する", () => {
  const plan = createShortTermTradePlan({
    signal: signal(),
    account: account({
      dailyPnlPercent: -2.1,
    }),
  });

  assert.equal(plan.executable, false);
  assert.equal(
    plan.reasons.some((reason) =>
      reason.includes("1日の最大損失"),
    ),
    true,
  );
});

test("同じ足で損切りと利確に触れた場合は損切りを優先する", () => {
  const result = evaluateOpenPosition({
    position: {
      side: POSITION_SIDES.LONG,
      entryPrice: 1_000,
      stopPrice: 980,
      firstTargetPrice: 1_030,
      secondTargetPrice: 1_050,
    },
    candle: {
      high: 1_060,
      low: 970,
      close: 1_020,
    },
    barsHeld: 2,
  });

  assert.equal(
    result.action,
    TRADE_ACTIONS.EXIT,
  );
  assert.equal(result.reason, "損切り");
  assert.equal(result.exitPrice, 980);
  assert.equal(result.returnPercent, -2);
});

test("最大保有バー到達時は時間切れで決済する", () => {
  const result = evaluateOpenPosition({
    position: {
      side: POSITION_SIDES.LONG,
      entryPrice: 1_000,
      stopPrice: 970,
      firstTargetPrice: 1_040,
      secondTargetPrice: 1_080,
    },
    candle: {
      high: 1_020,
      low: 990,
      close: 1_010,
    },
    barsHeld:
      DEFAULT_SHORT_TERM_POLICY
        .maximumHoldingBars,
  });

  assert.equal(
    result.action,
    TRADE_ACTIONS.EXIT,
  );
  assert.equal(result.reason, "時間切れ");
  assert.equal(result.exitPrice, 1_010);
  assert.equal(result.returnPercent, 1);
});

test("Paper注文は作れるが実注文へ変更できない", () => {
  const plan = createShortTermTradePlan({
    signal: signal(),
    account: account(),
    lotSize: 100,
  });

  const order = createPaperOrder(plan, {
    orderId: "paper-test-1",
  });

  assert.equal(
    order.environment,
    "paper",
  );
  assert.equal(
    order.liveExecutionAllowed,
    false,
  );
  assert.equal(
    order.status,
    "pending_trigger",
  );

  assert.throws(
    () =>
      createPaperOrder({
        ...plan,
        executionMode: "live",
      }),
    /実注文/,
  );
});