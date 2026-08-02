import {
  createPaperAccount,
  clonePaperAccount,
} from "./paper-account.js";

import {
  submitPaperOrder,
  executePaperOrder,
  markPaperAccount,
} from "./paper-engine.js";

import {
  createPaperOrderBook,
  addOrderToBook,
  updateOrderInBook,
  findOrderById,
  listOpenOrders,
  summarizeOrderBook,
} from "./paper-order-book.js";

import {
  cancelOpenOrder,
} from "./paper-execution.js";

export const PAPER_BROKER_VERSION =
  "paper-broker-v1";

function clone(value) {
  return structuredClone(value);
}

function replaceOrder(
  orders = [],
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

function synchronizeOrder({
  account,
  order,
} = {}) {
  const next =
    clonePaperAccount(account);

  next.openOrders =
    replaceOrder(
      next.openOrders || [],
      order,
    );

  next.orderHistory =
    replaceOrder(
      next.orderHistory || [],
      order,
    );

  return next;
}

export function createPaperBroker({
  account = null,
  orderBook = null,
  initialCash = 1_000_000,
  createdAt =
    new Date().toISOString(),
} = {}) {
  return {
    version:
      PAPER_BROKER_VERSION,

    mode:
      "paper",

    account:
      account ||
      createPaperAccount({
        initialCash,
        createdAt,
      }),

    orderBook:
      orderBook ||
      createPaperOrderBook({
        createdAt,
      }),

    createdAt,

    updatedAt:
      createdAt,
  };
}

export function submitBrokerOrder({
  broker,
  orderInput,
  estimatedPrice,
  riskPolicy = {},
  submittedAt =
    new Date().toISOString(),
} = {}) {
  if (!broker?.account) {
    throw new Error(
      "Paper broker account is missing.",
    );
  }

  const submission =
    submitPaperOrder({
      account:
        broker.account,

      orderInput,
      estimatedPrice,
      riskPolicy,
      submittedAt,
    });

  let account =
    submission.account;

  let order =
    submission.order;

  if (
    order.status ===
    "accepted"
  ) {
    order = {
      ...order,

      metadata: {
        ...(order.metadata || {}),

        estimatedPrice:
          Number(estimatedPrice),

        reservedValue:
          Number(
            submission.risk
              ?.orderValue || 0,
          ),
      },
    };

    account =
      synchronizeOrder({
        account,
        order,
      });
  }

  const orderBook =
    addOrderToBook({
      book:
        broker.orderBook,

      order,

      updatedAt:
        submittedAt,
    });

  return {
    broker: {
      ...clone(broker),

      account,
      orderBook,

      updatedAt:
        submittedAt,
    },

    order,
    risk:
      submission.risk,
  };
}

export function fillBrokerOrder({
  broker,
  orderId,
  fillPrice,
  fillQuantity = null,
  commission = 0,
  filledAt =
    new Date().toISOString(),
} = {}) {
  const bookOrder =
    findOrderById({
      book:
        broker.orderBook,

      orderId,
    });

  if (!bookOrder) {
    throw new Error(
      "Broker order was not found.",
    );
  }

  const execution =
    executePaperOrder({
      account:
        broker.account,

      orderId,

      fillPrice,
      fillQuantity,
      commission,
      filledAt,
    });

  const orderBook =
    updateOrderInBook({
      book:
        broker.orderBook,

      order:
        execution.order,

      updatedAt:
        filledAt,
    });

  return {
    broker: {
      ...clone(broker),

      account:
        execution.account,

      orderBook,

      updatedAt:
        filledAt,
    },

    order:
      execution.order,

    fill:
      execution.fill,
  };
}

export function cancelBrokerOrder({
  broker,
  orderId,
  cancelledAt =
    new Date().toISOString(),
} = {}) {
  const order =
    findOrderById({
      book:
        broker.orderBook,

      orderId,
    });

  if (!order) {
    throw new Error(
      "Broker order was not found.",
    );
  }

  const cancelled =
    cancelOpenOrder({
      order,
      cancelledAt,
    });

  const account =
    clonePaperAccount(
      broker.account,
    );

  account.openOrders =
    account.openOrders.filter(
      (row) =>
        row.orderId !==
        orderId,
    );

  account.orderHistory =
    replaceOrder(
      account.orderHistory,
      cancelled,
    );

  if (order.side === "buy") {
    account.reservedCash =
      Math.max(
        0,
        Number(
          account.reservedCash || 0,
        ) -
        Number(
          order.metadata
            ?.reservedValue || 0,
        ),
      );

    account.buyingPower =
      Math.max(
        0,
        Number(
          account.cash || 0,
        ) -
        Number(
          account.reservedCash || 0,
        ),
      );
  }

  account.updatedAt =
    cancelledAt;

  const orderBook =
    updateOrderInBook({
      book:
        broker.orderBook,

      order:
        cancelled,

      updatedAt:
        cancelledAt,
    });

  return {
    broker: {
      ...clone(broker),

      account,
      orderBook,

      updatedAt:
        cancelledAt,
    },

    order:
      cancelled,
  };
}

export function markPaperBroker({
  broker,
  prices = {},
  updatedAt =
    new Date().toISOString(),
} = {}) {
  const account =
    markPaperAccount({
      account:
        broker.account,

      prices,
      updatedAt,
    });

  return {
    ...clone(broker),

    account,

    updatedAt,
  };
}

export function createPaperBrokerSnapshot(
  broker = {},
) {
  const account =
    broker.account || {};

  return {
    version:
      PAPER_BROKER_VERSION,

    mode:
      broker.mode ||
      "paper",

    accountId:
      account.accountId ||
      null,

    cash:
      Number(
        account.cash || 0,
      ),

    reservedCash:
      Number(
        account.reservedCash || 0,
      ),

    buyingPower:
      Number(
        account.buyingPower || 0,
      ),

    marketValue:
      Number(
        account.marketValue || 0,
      ),

    equity:
      Number(
        account.equity || 0,
      ),

    realizedPnl:
      Number(
        account.realizedPnl || 0,
      ),

    unrealizedPnl:
      Number(
        account.unrealizedPnl || 0,
      ),

    totalPnl:
      Number(
        account.totalPnl || 0,
      ),

    totalReturnPercent:
      Number(
        account.totalReturnPercent || 0,
      ),

    positionCount:
      Object.keys(
        account.positions || {},
      ).length,

    openOrders:
      listOpenOrders({
        book:
          broker.orderBook,
      }),

    orderSummary:
      summarizeOrderBook(
        broker.orderBook,
      ),

    updatedAt:
      broker.updatedAt ||
      null,
  };
}

export const PaperBrokerInternals = {
  clone,
  replaceOrder,
  synchronizeOrder,
};