import {
  assertBrokerAdapter,
  BROKER_MODES,
} from "./broker-adapter-contract.js";

import {
  evaluateLiveTradingReadiness,
} from "./live-trading-readiness.js";

import {
  analyzePaperAiPerformance,
} from "../paper/paper-ai-performance-analyzer.js";

import {
  createPaperPortfolioSummary,
} from "../paper/paper-portfolio.js";

export const PART260_VALIDATION_VERSION =
  "part260-validation-v1";

function check({
  code,
  label,
  passed,
  severity = "error",
  details = null,
} = {}) {
  return {
    code,
    label,
    passed:
      Boolean(passed),
    severity,
    details,
  };
}

function countFailures(
  checks,
  severity,
) {
  return checks.filter(
    (row) =>
      !row.passed &&
      row.severity ===
        severity,
  );
}

export function validatePaperTradingSystem({
  broker,
  learningSummary = null,
} = {}) {
  const account =
    broker?.account || {};

  const orderBook =
    broker?.orderBook || {};

  const portfolio =
    createPaperPortfolioSummary({
      account,
    });

  const performance =
    analyzePaperAiPerformance({
      account,
    });

  const checks = [
    check({
      code:
        "paper_mode",

      label:
        "Paperモードで動作",

      passed:
        broker?.mode ===
        "paper",
    }),

    check({
      code:
        "account_exists",

      label:
        "仮想口座が存在",

      passed:
        Boolean(
          broker?.account,
        ),
    }),

    check({
      code:
        "cash_valid",

      label:
        "現金残高が有効",

      passed:
        Number.isFinite(
          Number(
            account.cash,
          ),
        ) &&
        Number(
          account.cash,
        ) >= 0,

      details: {
        cash:
          account.cash ??
          null,
      },
    }),

    check({
      code:
        "positions_valid",

      label:
        "保有株管理が有効",

      passed:
        Boolean(
          account.positions &&
          typeof account.positions ===
            "object",
        ),
    }),

    check({
      code:
        "orders_valid",

      label:
        "注文簿が有効",

      passed:
        Array.isArray(
          orderBook.orders,
        ),
    }),

    check({
      code:
        "ledger_valid",

      label:
        "取引台帳が有効",

      passed:
        Array.isArray(
          account.ledger,
        ),
    }),

    check({
      code:
        "portfolio_equity_valid",

      label:
        "資産評価が有効",

      passed:
        Number.isFinite(
          Number(
            portfolio.equity,
          ),
        ),
    }),

    check({
      code:
        "learning_human_approval",

      label:
        "学習適用に人間承認が必要",

      passed:
        learningSummary ===
          null ||
        learningSummary
          ?.automaticLivePromotion !==
          true,
    }),

    check({
      code:
        "paper_sample_size",

      label:
        "Paper取引実績が十分",

      passed:
        performance.sampleSize >=
        30,

      severity:
        "warning",

      details: {
        actual:
          performance.sampleSize,

        recommended:
          30,
      },
    }),

    check({
      code:
        "paper_profit_factor",

      label:
        "Paper Profit Factorが1以上",

      passed:
        performance.sampleSize ===
          0 ||
        Number(
          performance.metrics
            .profitFactor || 0,
        ) >= 1,

      severity:
        "warning",

      details: {
        actual:
          performance.metrics
            .profitFactor ??
          null,
      },
    }),
  ];

  const errors =
    countFailures(
      checks,
      "error",
    );

  const warnings =
    countFailures(
      checks,
      "warning",
    );

  return {
    version:
      PART260_VALIDATION_VERSION,

    passed:
      errors.length === 0,

    status:
      errors.length > 0
        ? "failed"
        : warnings.length > 0
          ? "warning"
          : "passed",

    checks,
    errors,
    warnings,

    summary: {
      total:
        checks.length,

      passed:
        checks.filter(
          (row) =>
            row.passed,
        ).length,

      errors:
        errors.length,

      warnings:
        warnings.length,
    },

    portfolio,
    performance,
  };
}

export function validateBrokerExecutionSystem({
  adapter,
  livePolicy = {},
  environment = {},
  evidence = {},
} = {}) {
  assertBrokerAdapter(
    adapter,
  );

  const info =
    adapter.getInfo();

  const checks = [
    check({
      code:
        "adapter_contract",

      label:
        "Broker Adapter契約を満たす",

      passed:
        true,
    }),

    check({
      code:
        "mode_defined",

      label:
        "Brokerモードが定義済み",

      passed:
        Object.values(
          BROKER_MODES,
        ).includes(
          info.mode,
        ),

      details: {
        mode:
          info.mode,
      },
    }),

    check({
      code:
        "dry_run_not_transmitted",

      label:
        "Dry Runは実送信しない",

      passed:
        info.mode !==
          BROKER_MODES.DRY_RUN ||
        info.liveTradingEnabled ===
          false,
    }),
  ];

  let readiness = null;

  if (
    info.mode ===
    BROKER_MODES.LIVE
  ) {
    readiness =
      evaluateLiveTradingReadiness({
        adapter,
        policy:
          livePolicy,
        environment,
        evidence,
      });

    checks.push(
      check({
        code:
          "live_readiness",

        label:
          "Live取引準備条件",

        passed:
          readiness.ready,

        severity:
          "warning",

        details: {
          failedChecks:
            readiness.failedChecks,
        },
      }),
    );
  }

  const errors =
    countFailures(
      checks,
      "error",
    );

  const warnings =
    countFailures(
      checks,
      "warning",
    );

  return {
    version:
      PART260_VALIDATION_VERSION,

    passed:
      errors.length === 0,

    status:
      errors.length > 0
        ? "failed"
        : warnings.length > 0
          ? "warning"
          : "passed",

    adapterInfo:
      info,

    checks,
    errors,
    warnings,
    readiness,
  };
}

export function validatePart260({
  broker,
  adapter,
  learningSummary = null,
  livePolicy = {},
  environment = {},
  evidence = {},
} = {}) {
  const paper =
    validatePaperTradingSystem({
      broker,
      learningSummary,
    });

  const execution =
    validateBrokerExecutionSystem({
      adapter,
      livePolicy,
      environment,
      evidence,
    });

  return {
    version:
      PART260_VALIDATION_VERSION,

    passed:
      paper.passed &&
      execution.passed,

    status:
      !paper.passed ||
      !execution.passed
        ? "failed"
        : paper.status ===
            "warning" ||
          execution.status ===
            "warning"
          ? "warning"
          : "passed",

    paper,
    execution,

    liveTradingAllowed:
      execution.readiness
        ?.ready === true,
  };
}