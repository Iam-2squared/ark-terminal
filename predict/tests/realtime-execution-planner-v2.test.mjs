import test from "node:test";
import assert from "node:assert/strict";

import {
  RealtimeExecutionPlannerV2,
  confirmRealtimeExecutionPlan,
  createRealtimeExecutionPlan,
} from "../realtime/realtime-execution-planner-v2.js";

function healthyInput() {
  return {
    gate: {
      version:
        "realtime-decision-gate-v2",

      ready:
        true,

      decision:
        "ALLOW",

      tradable:
        true,

      reason:
        "ALL_REALTIME_DECISION_GATES_PASSED",

      symbol:
        "285A",

      direction:
        "BUY",

      gateScore:
        100,

      positionMultiplier:
        70,

      blockers:
        [],

      executionPlan: {
        allowed:
          true,

        requireHumanConfirmation:
          true,
      },
    },

    market: {
      bid:
        499,

      ask:
        500,

      lastPrice:
        500,

      averageVolume:
        1000000,

      currentVolume:
        500000,

      lotSize:
        100,

      tickSize:
        1,

      halted:
        false,

      session:
        "REGULAR",
    },

    portfolio: {
      availableCash:
        500000,

      totalEquity:
        1000000,

      currentPosition:
        0,

      maximumPositionValue:
        300000,

      maximumOrderValue:
        200000,
    },

    risk: {
      atr:
        8,

      stopLossPercent:
        3,

      takeProfitPercent:
        6,

      maximumRiskPerTradePercent:
        1,

      maximumSpreadPercent:
        1.5,

      maximumVolumeParticipationPercent:
        5,
    },
  };
}

test(
  "Execution planner creates protected buy plan",
  () => {
    const result =
      createRealtimeExecutionPlan(
        healthyInput(),
      );

    assert.equal(
      result.version,
      "realtime-execution-planner-v2",
    );

    assert.equal(
      result.allowed,
      true,
    );

    assert.equal(
      result.status,
      "AWAITING_HUMAN_CONFIRMATION",
    );

    assert.equal(
      result.direction,
      "BUY",
    );

    assert.ok(
      result.order.quantity >
      0,
    );

    assert.ok(
      result.protection
        .stopLossPrice <
      result.order.entryPrice,
    );

    assert.ok(
      result.protection
        .takeProfitPrice >
      result.order.entryPrice,
    );
  },
);

test(
  "Execution planner never enables automatic execution",
  () => {
    const result =
      createRealtimeExecutionPlan({
        ...healthyInput(),

        requireHumanConfirmation:
          false,
      });

    assert.equal(
      result.audit
        .automaticExecution,
      false,
    );
  },
);

test(
  "Execution planner blocks rejected gate",
  () => {
    const input =
      healthyInput();

    input.gate.decision =
      "BLOCK";

    input.gate.tradable =
      false;

    input.gate.executionPlan
      .allowed =
      false;

    const result =
      createRealtimeExecutionPlan(
        input,
      );

    assert.equal(
      result.allowed,
      false,
    );

    assert.equal(
      result.status,
      "BLOCKED",
    );

    assert.equal(
      result.order.quantity,
      0,
    );

    assert.ok(
      result.blockers.some(
        (
          blocker,
        ) =>
          blocker.code ===
          "GATE_BLOCKED_EXECUTION",
      ),
    );
  },
);

test(
  "Execution planner blocks excessive spread",
  () => {
    const input =
      healthyInput();

    input.market.bid =
      480;

    input.market.ask =
      520;

    const result =
      createRealtimeExecutionPlan(
        input,
      );

    assert.equal(
      result.allowed,
      false,
    );

    assert.ok(
      result.blockers.some(
        (
          blocker,
        ) =>
          blocker.code ===
          "SPREAD_LIMIT_EXCEEDED",
      ),
    );
  },
);

test(
  "Execution planner blocks halted market",
  () => {
    const input =
      healthyInput();

    input.market.halted =
      true;

    const result =
      createRealtimeExecutionPlan(
        input,
      );

    assert.equal(
      result.allowed,
      false,
    );

    assert.ok(
      result.blockers.some(
        (
          blocker,
        ) =>
          blocker.code ===
          "MARKET_HALTED",
      ),
    );
  },
);

test(
  "Execution planner respects lot size",
  () => {
    const result =
      createRealtimeExecutionPlan(
        healthyInput(),
      );

    assert.equal(
      result.order.quantity %
      result.order.lotSize,
      0,
    );
  },
);

test(
  "Execution planner blocks buy without cash",
  () => {
    const input =
      healthyInput();

    input.portfolio.availableCash =
      0;

    const result =
      createRealtimeExecutionPlan(
        input,
      );

    assert.equal(
      result.allowed,
      false,
    );

    assert.ok(
      result.blockers.some(
        (
          blocker,
        ) =>
          blocker.code ===
          "INSUFFICIENT_CASH",
      ),
    );
  },
);

test(
  "Execution planner confirms human-approved plan",
  () => {
    const plan =
      createRealtimeExecutionPlan(
        healthyInput(),
      );

    const confirmed =
      confirmRealtimeExecutionPlan({
        plan,

        confirmedBy:
          "human-reviewer",

        confirmationNote:
          "Reviewed risk and order size.",
      });

    assert.equal(
      confirmed.status,
      "CONFIRMED",
    );

    assert.equal(
      confirmed
        .humanConfirmation
        .confirmed,
      true,
    );

    assert.equal(
      confirmed
        .humanConfirmation
        .executable,
      true,
    );

    assert.equal(
      confirmed.confirmation
        .confirmedBy,
      "human-reviewer",
    );

    assert.equal(
      confirmed.audit
        .automaticExecution,
      false,
    );
  },
);

test(
  "Execution planner requires named approver",
  () => {
    const plan =
      createRealtimeExecutionPlan(
        healthyInput(),
      );

    assert.throws(
      () =>
        confirmRealtimeExecutionPlan({
          plan,
        }),

      /requires confirmedBy/,
    );
  },
);

test(
  "Execution planner refuses blocked plan confirmation",
  () => {
    const input =
      healthyInput();

    input.gate.decision =
      "BLOCK";

    input.gate.tradable =
      false;

    input.gate.executionPlan
      .allowed =
      false;

    const plan =
      createRealtimeExecutionPlan(
        input,
      );

    const result =
      confirmRealtimeExecutionPlan({
        plan,

        confirmedBy:
          "reviewer",
      });

    assert.equal(
      result.confirmation
        .accepted,
      false,
    );
  },
);

test(
  "Execution planner class is deterministic for plan values",
  () => {
    const engine =
      new RealtimeExecutionPlannerV2();

    const first =
      engine.create(
        healthyInput(),
      );

    const second =
      engine.create(
        healthyInput(),
      );

    assert.equal(
      first.allowed,
      second.allowed,
    );

    assert.deepEqual(
      first.order,
      second.order,
    );

    assert.deepEqual(
      first.protection,
      second.protection,
    );

    assert.deepEqual(
      first.blockers,
      second.blockers,
    );
  },
);