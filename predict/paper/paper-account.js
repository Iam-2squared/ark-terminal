export const PAPER_ACCOUNT_VERSION =
  "paper-account-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function positiveOr(
  value,
  fallback,
) {
  return (
    finite(value) &&
    Number(value) > 0
  )
    ? Number(value)
    : fallback;
}

function nonNegativeOr(
  value,
  fallback = 0,
) {
  return (
    finite(value) &&
    Number(value) >= 0
  )
    ? Number(value)
    : fallback;
}

export function createPaperAccount({
  accountId =
    "paper-default",

  initialCash =
    1_000_000,

  currency =
    "JPY",

  createdAt =
    new Date().toISOString(),
} = {}) {
  const resolvedCash =
    positiveOr(
      initialCash,
      1_000_000,
    );

  return {
    version:
      PAPER_ACCOUNT_VERSION,

    accountId:
      String(accountId),

    mode:
      "paper",

    currency:
      String(currency),

    initialCash:
      resolvedCash,

    cash:
      resolvedCash,

    reservedCash:
      0,

    marketValue:
      0,

    equity:
      resolvedCash,

    buyingPower:
      resolvedCash,

    realizedPnl:
      0,

    unrealizedPnl:
      0,

    totalPnl:
      0,

    totalReturnPercent:
      0,

    positions:
      {},

    openOrders:
      [],

    orderHistory:
      [],

    tradeHistory:
      [],

    ledger:
      [],

    createdAt,
    updatedAt:
      createdAt,
  };
}

export function clonePaperAccount(
  account = {},
) {
  return structuredClone(
    account,
  );
}

export function updateAccountValuation({
  account,
  marketValue = 0,
  unrealizedPnl = 0,
  updatedAt =
    new Date().toISOString(),
} = {}) {
  const next =
    clonePaperAccount(
      account,
    );

  next.marketValue =
    nonNegativeOr(
      marketValue,
      0,
    );

  next.unrealizedPnl =
    finite(unrealizedPnl)
      ? Number(unrealizedPnl)
      : 0;

  next.equity =
    Number(next.cash || 0) +
    next.marketValue;

  next.buyingPower =
    Math.max(
      0,
      Number(next.cash || 0) -
      Number(
        next.reservedCash || 0,
      ),
    );

  next.totalPnl =
    Number(
      next.realizedPnl || 0,
    ) +
    next.unrealizedPnl;

  next.totalReturnPercent =
    Number(
      next.initialCash || 0,
    ) > 0
      ? (
          next.totalPnl /
          Number(
            next.initialCash,
          )
        ) * 100
      : 0;

  next.updatedAt =
    updatedAt;

  return next;
}

export function assertPaperAccount(
  account = {},
) {
  if (
    account.mode !==
    "paper"
  ) {
    throw new Error(
      "Paper account mode is required.",
    );
  }

  if (
    !finite(account.cash) ||
    Number(account.cash) < 0
  ) {
    throw new Error(
      "Paper account cash is invalid.",
    );
  }

  if (
    !account.positions ||
    typeof account.positions !==
      "object"
  ) {
    throw new Error(
      "Paper account positions are invalid.",
    );
  }

  return true;
}

export const PaperAccountInternals = {
  finite,
  positiveOr,
  nonNegativeOr,
};