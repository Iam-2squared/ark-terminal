import assert from "node:assert/strict";
import test from "node:test";

import { evaluateRiskGovernor } from "../approval/risk-governor.js";
import { evaluateKillSwitch } from "../approval/kill-switch.js";
import { buildDryRunRecord } from "../approval/dry-run.js";

test("risk governor blocks leverage, limits and out-of-window activity", () => {
  const result = evaluateRiskGovernor({
    symbol: "7203.T",
    side: "BUY",
    instrumentType: "MARGIN",
    quantity: 100,
    price: 3000,
    currentSymbolExposure: 0,
    totalExposure: 0,
    dailyLoss: 6000,
    consecutiveLosses: 4,
    maxDrawdown: 12,
    ordersToday: 4,
    now: "2026-08-06T17:00:00+09:00",
  }, {
    allowedSymbols: ["7203.T"],
    maxSymbolExposure: 50000,
    maxTotalExposure: 200000,
    maxDailyLoss: 5000,
    maxConsecutiveLosses: 3,
    maxDrawdown: 10,
    maxOrdersPerDay: 3,
    startHour: 9,
    endHour: 15,
  });

  assert.equal(result.status, "BLOCKED");
  assert.ok(result.blockers.includes("CASH_EQUITY_ONLY"));
  assert.ok(result.blockers.includes("SYMBOL_EXPOSURE_LIMIT"));
  assert.ok(result.blockers.includes("TOTAL_EXPOSURE_LIMIT"));
  assert.ok(result.blockers.includes("DAILY_LOSS_LIMIT"));
  assert.ok(result.blockers.includes("CONSECUTIVE_LOSS_LIMIT"));
  assert.ok(result.blockers.includes("MAX_DRAWDOWN_LIMIT"));
  assert.ok(result.blockers.includes("DAILY_ORDER_COUNT_LIMIT"));
  assert.ok(result.blockers.includes("OUTSIDE_TRADING_WINDOW"));
  assert.equal(result.safety.brokerWriteAllowed, false);
});

test("risk governor allows only compliant dry-run candidates", () => {
  const result = evaluateRiskGovernor({
    symbol: "7203.T",
    side: "BUY",
    instrumentType: "CASH_EQUITY",
    quantity: 10,
    price: 3000,
    currentSymbolExposure: 0,
    totalExposure: 50000,
    dailyLoss: 0,
    consecutiveLosses: 0,
    maxDrawdown: 2,
    ordersToday: 1,
    now: "2026-08-06T10:00:00+09:00",
  }, {
    allowedSymbols: ["7203.T"],
  });

  assert.equal(result.status, "DRY_RUN_ALLOWED");
  assert.deepEqual(result.blockers, []);
});

test("kill switch halts approval flow on any critical safety fault", () => {
  const result = evaluateKillSwitch({
    manualStop: false,
    apiHealthy: true,
    rssHealthy: false,
    bridgeHealthy: true,
    dataQualityPassed: true,
    priceFresh: true,
    clockSynchronized: true,
    criticalIncidents: 0,
    recoveryMode: "MANUAL_ONLY",
  });

  assert.equal(result.status, "HALTED");
  assert.ok(result.reasons.includes("RSS_UNHEALTHY"));
  assert.equal(result.controls.dryRunAllowed, false);
  assert.equal(result.safety.mode, "READ_ONLY");
  assert.equal(result.safety.brokerWriteAllowed, false);
});

test("dry run completes only after approvals, risk and kill switch all pass", () => {
  const record = buildDryRunRecord({
    generatedAt: "2026-08-06T06:30:00.000Z",
    candidate: {
      symbol: "7203.T",
      side: "BUY",
      quantity: 10,
      orderType: "LIMIT",
      limitPrice: 3000,
      stopLossPrice: 2910,
      takeProfitPrice: 3180,
      maxLoss: 900,
    },
    approval: {
      status: "DRY_RUN_READY",
      firstApprovedBy: "user-1",
      finalApprovedBy: "user-1",
      candidateHash: "abc123",
    },
    risk: {
      status: "DRY_RUN_ALLOWED",
      blockers: [],
      limits: { maxDailyLoss: 5000 },
    },
    killSwitch: {
      status: "ARMED",
      reasons: [],
    },
  });

  assert.equal(record.status, "DRY_RUN_COMPLETED");
  assert.equal(record.sideEffects.brokerWrites, 0);
  assert.equal(record.sideEffects.liveOrders, 0);
  assert.equal(record.safety.orderCreationAllowed, false);
  assert.equal(Object.isFrozen(record), true);
  assert.equal(Object.isFrozen(record.candidate), true);
});

test("dry run blocks incomplete approval or halted safety state", () => {
  const record = buildDryRunRecord({
    candidate: { symbol: "7203.T", side: "BUY", quantity: 10, price: 3000 },
    approval: { status: "FIRST_APPROVED" },
    risk: { status: "BLOCKED", blockers: ["DAILY_LOSS_LIMIT"] },
    killSwitch: { status: "HALTED", reasons: ["API_UNHEALTHY"] },
  });

  assert.equal(record.status, "BLOCKED");
  assert.ok(record.blockers.includes("TWO_STEP_APPROVAL_INCOMPLETE"));
  assert.ok(record.blockers.includes("RISK_GOVERNOR_BLOCKED"));
  assert.ok(record.blockers.includes("KILL_SWITCH_HALTED"));
  assert.equal(record.sideEffects.brokerWrites, 0);
});
