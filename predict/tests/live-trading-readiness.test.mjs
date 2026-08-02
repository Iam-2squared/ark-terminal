import test from "node:test";
import assert from "node:assert/strict";

import {
  createDisabledLiveBrokerAdapter,
} from "../broker/disabled-live-broker-adapter.js";

import {
  assertLiveTradingReady,
  evaluateLiveTradingReadiness,
} from "../broker/live-trading-readiness.js";

test(
  "未設定AdapterはLive準備未完了",
  () => {
    const readiness =
      evaluateLiveTradingReadiness({
        adapter:
          createDisabledLiveBrokerAdapter(),

        policy: {
          allowLiveTrading:
            false,
        },

        environment: {
          humanApprovalEnabled:
            true,

          killSwitchAvailable:
            true,

          credentialsIsolated:
            true,

          auditLoggingEnabled:
            true,
        },

        evidence: {
          paperTradeCount:
            200,

          paperProfitFactor:
            1.5,

          paperMaximumDrawdownPercent:
            5,
        },
      });

    assert.equal(
      readiness.ready,
      false,
    );

    assert.ok(
      readiness.failedChecks.includes(
        "adapter_connected",
      ),
    );

    assert.ok(
      readiness.failedChecks.includes(
        "adapter_authenticated",
      ),
    );

    assert.ok(
      readiness.failedChecks.includes(
        "adapter_live_enabled",
      ),
    );

    assert.ok(
      readiness.failedChecks.includes(
        "policy_live_enabled",
      ),
    );
  },
);

test(
  "Paper実績不足を検出",
  () => {
    const readiness =
      evaluateLiveTradingReadiness({
        adapter:
          createDisabledLiveBrokerAdapter(),

        policy: {
          allowLiveTrading:
            true,

          minimumPaperTrades:
            100,
        },

        environment: {
          humanApprovalEnabled:
            true,

          killSwitchAvailable:
            true,

          credentialsIsolated:
            true,

          auditLoggingEnabled:
            true,
        },

        evidence: {
          paperTradeCount:
            20,

          paperProfitFactor:
            0.8,

          paperMaximumDrawdownPercent:
            15,
        },
      });

    assert.ok(
      readiness.failedChecks.includes(
        "paper_trade_sample",
      ),
    );

    assert.ok(
      readiness.failedChecks.includes(
        "paper_profit_factor",
      ),
    );

    assert.ok(
      readiness.failedChecks.includes(
        "paper_drawdown",
      ),
    );
  },
);

test(
  "準備不足時は例外で停止",
  () => {
    assert.throws(
      () =>
        assertLiveTradingReady({
          adapter:
            createDisabledLiveBrokerAdapter(),
        }),
      /Live trading readiness checks failed/,
    );
  },
);