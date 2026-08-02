import {
  assertPaperAccount,
  clonePaperAccount,
  updateAccountValuation,
} from "./paper-account.js";

import {
  acceptPaperOrder,
  createPaperOrder,
  fillPaperOrder,
  PAPER_ORDER_SIDES,
  rejectPaperOrder,
} from "./paper-orders.js";

import {
  applyBuyFill,
  applySellFill,
  markPosition,
  summarizePositions,
} from "./paper-positions.js";

import {
  appendLedgerEntry,
  createLedgerEntry,
} from "./paper-ledger.js";

import {
  evaluatePaperOrderRisk,
} from "./paper-risk.js";

export const PAPER_ENGINE_VERSION =
  "paper-engine-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function recalculateAccount(
  account,
  updatedAt =
    new Date().toISOString(),
) {
  const summary =
    summarizePositions(
      account.positions,
    );

  return updateAccountValuation({
    account,
    marketValue:
      summary.marketValue,

    unrealizedPnl:
      summary.unrealizedPnl,

    updatedAt,
  });
}

function replaceOrder(
  orders,
  updatedOrder,
) {
  return orders.map(
    (order) =>
      order.orderId ===
      updatedOrder.orderId
        ? updatedOrder
        : order,
  );
}

export function submitPaperOrder({
  account,
  orderInput,
  estimatedPrice,
  riskPolicy = {},
  submittedAt =
    new Date().toISOString(),
} = {}) {
  assertPaperAccount(
    account,
  );

  const next =
    clonePaperAccount(
      account,
    );

  const order =
    createPaperOrder({
      ...orderInput,
      submittedAt,
    });

  const risk =
    evaluatePaperOrderRisk({
      account: next,
      order,
      estimatedPrice,
      policy:
        riskPolicy,
    });

  if (!risk.passed) {
    const rejected =
      rejectPaperOrder({
        order,
        reason:
          risk.reasons.join(","),
        rejectedAt:
          submittedAt,
      });

    next.orderHistory.push(
      rejected,
    );

    next.updatedAt =
      submittedAt;

    return {
      account:
        next,

      order:
        rejected,

      risk,
    };
  }

  const accepted =
    acceptPaperOrder({
      order,
      acceptedAt:
        submittedAt,
    });

  next.openOrders.push(
    accepted,
  );

  next.orderHistory.push(
    accepted,
  );

  if (
    accepted.side ===
      PAPER_ORDER_SIDES.BUY
  ) {
    next.reservedCash +=
      risk.orderValue;
  }

  next.updatedAt =
    submittedAt;

  return {
    account:
      next,

    order:
      accepted,

    risk,
  };
}

export function executePaperOrder({
  account,
  orderId,
  fillPrice,
  fillQuantity = null,
  commission = 0,
  filledAt =
    new Date().toISOString(),
} = {}) {
  assertPaperAccount(
    account,
  );

  if (
    !finite(fillPrice) ||
    Number(fillPrice) <= 0
  ) {
    throw new Error(
      "Fill price is invalid.",
    );
  }

  const next =
    clonePaperAccount(
      account,
    );

  const order =
    next.openOrders.find(
      (row) =>
        row.orderId ===
        orderId,
    );

  if (!order) {
    throw new Error(
      "Open order was not found.",
    );
  }

  const quantity =
    fillQuantity === null
      ? Number(
          order.remainingQuantity,
        )
      : Number(
          fillQuantity,
        );

  const filledOrder =
    fillPaperOrder({
      order,
      fillPrice,
      fillQuantity:
        quantity,
      filledAt,
    });

  const notional =
    quantity *
    Number(fillPrice);

  const fee =
    Math.max(
      0,
      Number(
        commission || 0,
      ),
    );

  if (
    order.side ===
      PAPER_ORDER_SIDES.BUY
  ) {
    const totalDebit =
      notional +
      fee;

    if (
      totalDebit >
      Number(next.cash)
    ) {
      throw new Error(
        "Insufficient paper cash.",
      );
    }

    next.cash -=
      totalDebit;

    next.reservedCash =
      Math.max(
        0,
        Number(
          next.reservedCash,
        ) -
        notional,
      );

    next.positions[
      order.symbol
    ] =
      applyBuyFill({
        position:
          next.positions[
            order.symbol
          ],

        symbol:
          order.symbol,

        quantity,
        price:
          fillPrice,

        filledAt,
      });

    next.ledger =
      appendLedgerEntry({
        ledger:
          next.ledger,

        entry:
          createLedgerEntry({
            type:
              "buy_fill",

            amount:
              -totalDebit,

            symbol:
              order.symbol,

            quantity,

            price:
              fillPrice,

            orderId:
              order.orderId,

            createdAt:
              filledAt,
          }),
      });
  }
  else {
    const sellResult =
      applySellFill({
        position:
          next.positions[
            order.symbol
          ],

        quantity,
        price:
          fillPrice,

        filledAt,
      });

    const credit =
      notional -
      fee;

    next.cash +=
      credit;

    next.realizedPnl +=
      sellResult.realizedPnl -
      fee;

    if (
      sellResult.position
    ) {
      next.positions[
        order.symbol
      ] =
        sellResult.position;
    }
    else {
      delete next.positions[
        order.symbol
      ];
    }

    next.tradeHistory.push({
      tradeId:
        order.orderId,

      symbol:
        order.symbol,

      side:
        "long",

      quantity,

      exitPrice:
        Number(fillPrice),

      realizedPnl:
        sellResult.realizedPnl -
        fee,

      commission:
        fee,

      closedAt:
        filledAt,
    });

    next.ledger =
      appendLedgerEntry({
        ledger:
          next.ledger,

        entry:
          createLedgerEntry({
            type:
              "sell_fill",

            amount:
              credit,

            symbol:
              order.symbol,

            quantity,

            price:
              fillPrice,

            orderId:
              order.orderId,

            createdAt:
              filledAt,

            metadata: {
              realizedPnl:
                sellResult.realizedPnl -
                fee,
            },
          }),
      });
  }

  next.openOrders =
    filledOrder.remainingQuantity ===
      0
      ? next.openOrders.filter(
          (row) =>
            row.orderId !==
            orderId,
        )
      : replaceOrder(
          next.openOrders,
          filledOrder,
        );

  next.orderHistory =
    replaceOrder(
      next.orderHistory,
      filledOrder,
    );

  const recalculated =
    recalculateAccount(
      next,
      filledAt,
    );

  return {
    account:
      recalculated,

    order:
      filledOrder,

    fill: {
      symbol:
        order.symbol,

      side:
        order.side,

      quantity,

      price:
        Number(fillPrice),

      commission:
        fee,

      notional,
    },
  };
}

export function markPaperAccount({
  account,
  prices = {},
  updatedAt =
    new Date().toISOString(),
} = {}) {
  assertPaperAccount(
    account,
  );

  const next =
    clonePaperAccount(
      account,
    );

  for (
    const [
      symbol,
      position,
    ] of Object.entries(
      next.positions,
    )
  ) {
    const price =
      prices[symbol];

    if (
      finite(price) &&
      Number(price) > 0
    ) {
      next.positions[symbol] =
        markPosition({
          position,
          marketPrice:
            price,
          updatedAt,
        });
    }
  }

  return recalculateAccount(
    next,
    updatedAt,
  );
}

export const PaperEngineInternals = {
  finite,
  recalculateAccount,
  replaceOrder,
};