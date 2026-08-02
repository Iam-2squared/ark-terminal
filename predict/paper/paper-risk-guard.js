export const PAPER_RISK_GUARD_VERSION =
  "paper-risk-guard-v1";

export const DEFAULT_PAPER_GUARD_POLICY =
  Object.freeze({
    enabled: true,
    emergencyStop: false,

    maximumDailyLoss:
      30_000,

    maximumDrawdownPercent:
      10,

    maximumConsecutiveLosses:
      3,

    maximumPositionPercent:
      30,

    maximumPortfolioExposurePercent:
      80,

    minimumCashReserve:
      50_000,
  });

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function numberOr(
  value,
  fallback = 0,
) {
  return finite(value)
    ? Number(value)
    : fallback;
}

export function resolvePaperGuardPolicy(
  policy = {},
) {
  return {
    ...DEFAULT_PAPER_GUARD_POLICY,
    ...(policy || {}),
  };
}

export function calculateConsecutiveLosses(
  trades = [],
) {
  let count = 0;

  for (
    let index =
      trades.length - 1;
    index >= 0;
    index--
  ) {
    const pnl =
      numberOr(
        trades[index]
          ?.realizedPnl,
        0,
      );

    if (pnl < 0) {
      count++;
      continue;
    }

    break;
  }

  return count;
}

export function calculateDrawdownPercent({
  peakEquity,
  currentEquity,
} = {}) {
  const peak =
    numberOr(
      peakEquity,
      0,
    );

  const current =
    numberOr(
      currentEquity,
      0,
    );

  if (peak <= 0) {
    return 0;
  }

  return (
    (
      peak -
      current
    ) /
    peak
  ) * 100;
}

export function evaluatePaperTradingGuard({
  account = {},
  order = null,
  estimatedPrice = null,
  dailyRealizedPnl = 0,
  peakEquity = null,
  policy = {},
} = {}) {
  const resolved =
    resolvePaperGuardPolicy(
      policy,
    );

  const reasons = [];

  if (!resolved.enabled) {
    return {
      passed: true,
      reasons,
      policy:
        resolved,
      disabled: true,
    };
  }

  if (resolved.emergencyStop) {
    reasons.push(
      "emergency_stop_enabled",
    );
  }

  const currentEquity =
    numberOr(
      account.equity,
      account.cash,
    );

  const resolvedPeak =
    finite(peakEquity)
      ? Number(peakEquity)
      : Math.max(
          currentEquity,
          numberOr(
            account.initialCash,
            currentEquity,
          ),
        );

  const drawdownPercent =
    calculateDrawdownPercent({
      peakEquity:
        resolvedPeak,
      currentEquity,
    });

  if (
    drawdownPercent >=
    Number(
      resolved
        .maximumDrawdownPercent,
    )
  ) {
    reasons.push(
      "maximum_drawdown_reached",
    );
  }

  if (
    numberOr(
      dailyRealizedPnl,
      0,
    ) <=
    -Math.abs(
      Number(
        resolved
          .maximumDailyLoss,
      ),
    )
  ) {
    reasons.push(
      "maximum_daily_loss_reached",
    );
  }

  const consecutiveLosses =
    calculateConsecutiveLosses(
      account.tradeHistory || [],
    );

  if (
    consecutiveLosses >=
    Number(
      resolved
        .maximumConsecutiveLosses,
    )
  ) {
    reasons.push(
      "maximum_consecutive_losses_reached",
    );
  }

  let orderValue = 0;
  let projectedExposurePercent = 0;
  let projectedPositionPercent = 0;

  if (
    order &&
    finite(estimatedPrice)
  ) {
    orderValue =
      numberOr(
        order.quantity,
        0,
      ) *
      Number(
        estimatedPrice,
      );

    if (
      order.side === "buy"
    ) {
      const equity =
        Math.max(
          1,
          currentEquity,
        );

      const currentExposure =
        numberOr(
          account.marketValue,
          0,
        );

      const currentPositionValue =
        numberOr(
          account.positions
            ?.[order.symbol]
            ?.marketValue,
          0,
        );

      projectedExposurePercent =
        (
          (
            currentExposure +
            orderValue
          ) /
          equity
        ) * 100;

      projectedPositionPercent =
        (
          (
            currentPositionValue +
            orderValue
          ) /
          equity
        ) * 100;

      if (
        projectedExposurePercent >
        Number(
          resolved
            .maximumPortfolioExposurePercent,
        )
      ) {
        reasons.push(
          "maximum_portfolio_exposure_exceeded",
        );
      }

      if (
        projectedPositionPercent >
        Number(
          resolved
            .maximumPositionPercent,
        )
      ) {
        reasons.push(
          "maximum_position_percent_exceeded",
        );
      }

      const projectedCash =
        numberOr(
          account.cash,
          0,
        ) -
        orderValue;

      if (
        projectedCash <
        Number(
          resolved
            .minimumCashReserve,
        )
      ) {
        reasons.push(
          "minimum_cash_reserve_breached",
        );
      }
    }
  }

  return {
    passed:
      reasons.length === 0,

    reasons,

    policy:
      resolved,

    metrics: {
      drawdownPercent,
      consecutiveLosses,
      dailyRealizedPnl:
        numberOr(
          dailyRealizedPnl,
          0,
        ),
      orderValue,
      projectedExposurePercent,
      projectedPositionPercent,
    },
  };
}

export function createPaperKillSwitch({
  enabled = false,
  reason = null,
  activatedAt = null,
} = {}) {
  return {
    enabled:
      Boolean(enabled),

    reason:
      reason === null
        ? null
        : String(reason),

    activatedAt:
      enabled
        ? (
            activatedAt ||
            new Date()
              .toISOString()
          )
        : null,
  };
}

export const PaperRiskGuardInternals = {
  finite,
  numberOr,
};