export const PAPER_RISK_VERSION =
  "paper-risk-v1";

export const DEFAULT_PAPER_RISK_POLICY =
  Object.freeze({
    maximumOrderValue:
      300_000,

    maximumPositionValue:
      300_000,

    maximumPortfolioExposurePercent:
      80,

    maximumOpenOrders:
      10,

    minimumCashReserve:
      50_000,

    allowShort:
      false,

    requireHundredShareLot:
      true,
  });

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

export function resolvePaperRiskPolicy(
  policy = {},
) {
  return {
    ...DEFAULT_PAPER_RISK_POLICY,
    ...(policy || {}),
  };
}

export function evaluatePaperOrderRisk({
  account,
  order,
  estimatedPrice,
  policy = {},
} = {}) {
  const resolved =
    resolvePaperRiskPolicy(
      policy,
    );

  const reasons = [];

  if (
    !finite(estimatedPrice) ||
    Number(estimatedPrice) <= 0
  ) {
    reasons.push(
      "invalid_estimated_price",
    );
  }

  const orderValue =
    Number(order.quantity || 0) *
    Number(estimatedPrice || 0);

  if (
    order.side === "sell" &&
    !resolved.allowShort
  ) {
    const held =
      Number(
        account.positions
          ?.[order.symbol]
          ?.quantity || 0,
      );

    if (
      held <
      Number(order.quantity)
    ) {
      reasons.push(
        "insufficient_position",
      );
    }
  }

  if (
    resolved.requireHundredShareLot &&
    Number(order.quantity) % 100 !== 0
  ) {
    reasons.push(
      "invalid_lot_size",
    );
  }

  if (
    orderValue >
    Number(
      resolved.maximumOrderValue,
    )
  ) {
    reasons.push(
      "maximum_order_value_exceeded",
    );
  }

  if (
    order.side === "buy"
  ) {
    const cashAfterOrder =
      Number(account.cash || 0) -
      orderValue;

    if (
      cashAfterOrder <
      Number(
        resolved.minimumCashReserve,
      )
    ) {
      reasons.push(
        "minimum_cash_reserve_breached",
      );
    }

    const currentPositionValue =
      Number(
        account.positions
          ?.[order.symbol]
          ?.marketValue || 0,
      );

    if (
      currentPositionValue +
      orderValue >
      Number(
        resolved.maximumPositionValue,
      )
    ) {
      reasons.push(
        "maximum_position_value_exceeded",
      );
    }
  }

  if (
    Number(
      account.openOrders
        ?.length || 0,
    ) >=
    Number(
      resolved.maximumOpenOrders,
    )
  ) {
    reasons.push(
      "maximum_open_orders_exceeded",
    );
  }

  return {
    passed:
      reasons.length === 0,

    reasons,

    orderValue,

    policy:
      resolved,
  };
}