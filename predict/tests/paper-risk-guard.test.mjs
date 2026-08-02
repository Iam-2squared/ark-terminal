import test from "node:test";
import assert from "node:assert/strict";

import {
  calculateConsecutiveLosses,
  calculateDrawdownPercent,
  createPaperKillSwitch,
  evaluatePaperTradingGuard,
} from "../paper/paper-risk-guard.js";

test(
  "連敗数を計算",
  () => {
    assert.equal(
      calculateConsecutiveLosses([
        {
          realizedPnl: 500,
        },
        {
          realizedPnl: -200,
        },
        {
          realizedPnl: -300,
        },
      ]),
      2,
    );
  },
);

test(
  "ドローダウン率を計算",
  () => {
    assert.equal(
      calculateDrawdownPercent({
        peakEquity:
          1_000_000,
        currentEquity:
          900_000,
      }),
      10,
    );
  },
);

test(
  "緊急停止を検出",
  () => {
    const result =
      evaluatePaperTradingGuard({
        account: {
          cash:
            1_000_000,
          equity:
            1_000_000,
          marketValue:
            0,
          positions: {},
          tradeHistory: [],
        },

        policy: {
          emergencyStop:
            true,
        },
      });

    assert.equal(
      result.passed,
      false,
    );

    assert.ok(
      result.reasons.includes(
        "emergency_stop_enabled",
      ),
    );
  },
);

test(
  "連敗上限で停止",
  () => {
    const result =
      evaluatePaperTradingGuard({
        account: {
          cash:
            1_000_000,
          equity:
            1_000_000,
          marketValue:
            0,
          positions: {},
          tradeHistory: [
            {
              realizedPnl: -100,
            },
            {
              realizedPnl: -200,
            },
            {
              realizedPnl: -300,
            },
          ],
        },
      });

    assert.equal(
      result.passed,
      false,
    );

    assert.ok(
      result.reasons.includes(
        "maximum_consecutive_losses_reached",
      ),
    );
  },
);

test(
  "集中投資注文を拒否",
  () => {
    const result =
      evaluatePaperTradingGuard({
        account: {
          cash:
            1_000_000,
          equity:
            1_000_000,
          marketValue:
            0,
          positions: {},
          tradeHistory: [],
        },

        order: {
          symbol:
            "7203.T",
          side:
            "buy",
          quantity:
            200,
        },

        estimatedPrice:
          2_000,

        policy: {
          maximumPositionPercent:
            30,
        },
      });

    assert.equal(
      result.passed,
      false,
    );

    assert.ok(
      result.reasons.includes(
        "maximum_position_percent_exceeded",
      ),
    );
  },
);

test(
  "Kill Switchを作成",
  () => {
    const state =
      createPaperKillSwitch({
        enabled: true,
        reason:
          "manual_stop",
      });

    assert.equal(
      state.enabled,
      true,
    );

    assert.equal(
      state.reason,
      "manual_stop",
    );

    assert.ok(
      state.activatedAt,
    );
  },
);