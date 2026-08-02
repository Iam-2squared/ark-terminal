import {
  assertBrokerAdapter,
  BROKER_MODES,
} from "./broker-adapter-contract.js";

export const LIVE_TRADING_READINESS_VERSION =
  "live-trading-readiness-v1";

function boolean(
  value,
) {
  return value === true;
}

export function evaluateLiveTradingReadiness({
  adapter,

  policy = {},

  environment = {},

  evidence = {},
} = {}) {
  assertBrokerAdapter(
    adapter,
  );

  const adapterInfo =
    adapter.getInfo();

  const resolvedPolicy = {
    allowLiveTrading:
      false,

    requireHumanApproval:
      true,

    requireKillSwitch:
      true,

    requirePaperMinimumTrades:
      true,

    minimumPaperTrades:
      100,

    minimumPaperProfitFactor:
      1.1,

    maximumPaperDrawdownPercent:
      10,

    requireCredentialIsolation:
      true,

    requireAuditLogging:
      true,

    ...policy,
  };

  const checks = [];

  function addCheck({
    code,
    passed,
    required = true,
    details = null,
  }) {
    checks.push({
      code,

      passed:
        Boolean(passed),

      required:
        Boolean(required),

      details,
    });
  }

  addCheck({
    code:
      "adapter_mode_live",

    passed:
      adapterInfo.mode ===
      BROKER_MODES.LIVE,

    details: {
      actualMode:
        adapterInfo.mode,
    },
  });

  addCheck({
    code:
      "adapter_connected",

    passed:
      boolean(
        adapterInfo.connected,
      ),
  });

  addCheck({
    code:
      "adapter_authenticated",

    passed:
      boolean(
        adapterInfo.authenticated,
      ),
  });

  addCheck({
    code:
      "adapter_live_enabled",

    passed:
      boolean(
        adapterInfo.liveTradingEnabled,
      ),
  });

  addCheck({
    code:
      "policy_live_enabled",

    passed:
      boolean(
        resolvedPolicy.allowLiveTrading,
      ),
  });

  addCheck({
    code:
      "human_approval_enabled",

    passed:
      resolvedPolicy.requireHumanApproval
        ? boolean(
            environment.humanApprovalEnabled,
          )
        : true,

    required:
      resolvedPolicy.requireHumanApproval,
  });

  addCheck({
    code:
      "kill_switch_available",

    passed:
      resolvedPolicy.requireKillSwitch
        ? boolean(
            environment.killSwitchAvailable,
          )
        : true,

    required:
      resolvedPolicy.requireKillSwitch,
  });

  addCheck({
    code:
      "credential_isolation",

    passed:
      resolvedPolicy.requireCredentialIsolation
        ? boolean(
            environment.credentialsIsolated,
          )
        : true,

    required:
      resolvedPolicy.requireCredentialIsolation,
  });

  addCheck({
    code:
      "audit_logging",

    passed:
      resolvedPolicy.requireAuditLogging
        ? boolean(
            environment.auditLoggingEnabled,
          )
        : true,

    required:
      resolvedPolicy.requireAuditLogging,
  });

  const paperTradeCount =
    Number(
      evidence.paperTradeCount ||
      0,
    );

  addCheck({
    code:
      "paper_trade_sample",

    passed:
      resolvedPolicy.requirePaperMinimumTrades
        ? paperTradeCount >=
          Number(
            resolvedPolicy.minimumPaperTrades,
          )
        : true,

    required:
      resolvedPolicy.requirePaperMinimumTrades,

    details: {
      actual:
        paperTradeCount,

      required:
        Number(
          resolvedPolicy.minimumPaperTrades,
        ),
    },
  });

  const paperProfitFactor =
    Number(
      evidence.paperProfitFactor ||
      0,
    );

  addCheck({
    code:
      "paper_profit_factor",

    passed:
      paperProfitFactor >=
      Number(
        resolvedPolicy.minimumPaperProfitFactor,
      ),

    details: {
      actual:
        paperProfitFactor,

      required:
        Number(
          resolvedPolicy.minimumPaperProfitFactor,
        ),
    },
  });

  const paperDrawdown =
    Number(
      evidence.paperMaximumDrawdownPercent ??
      Infinity,
    );

  addCheck({
    code:
      "paper_drawdown",

    passed:
      paperDrawdown <=
      Number(
        resolvedPolicy.maximumPaperDrawdownPercent,
      ),

    details: {
      actual:
        paperDrawdown,

      maximum:
        Number(
          resolvedPolicy.maximumPaperDrawdownPercent,
        ),
    },
  });

  const failedRequiredChecks =
    checks.filter(
      (check) =>
        check.required &&
        !check.passed,
    );

  return {
    version:
      LIVE_TRADING_READINESS_VERSION,

    ready:
      failedRequiredChecks.length === 0,

    mode:
      adapterInfo.mode,

    provider:
      adapterInfo.provider ||
      null,

    checks,

    failedChecks:
      failedRequiredChecks.map(
        (check) =>
          check.code,
      ),

    policy:
      resolvedPolicy,

    recommendation:
      failedRequiredChecks.length === 0
        ? "manual_review_required"
        : "live_trading_blocked",
  };
}

export function assertLiveTradingReady(
  options,
) {
  const result =
    evaluateLiveTradingReadiness(
      options,
    );

  if (!result.ready) {
    const error =
      new Error(
        "Live trading readiness checks failed: " +
        result.failedChecks.join(","),
      );

    error.code =
      "LIVE_TRADING_NOT_READY";

    error.readiness =
      result;

    throw error;
  }

  return result;
}