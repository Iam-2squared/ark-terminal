import {
  PAPER_ORDER_STATUS,
} from "./paper-orders.js";

export const PAPER_ORDER_BOOK_VERSION =
  "paper-order-book-v1";

function clone(value) {
  return structuredClone(value);
}

function orderTimestamp(order = {}) {
  return String(
    order.submittedAt ||
    order.acceptedAt ||
    "",
  );
}

function isOpenStatus(status) {
  return [
    PAPER_ORDER_STATUS.PENDING,
    PAPER_ORDER_STATUS.ACCEPTED,
    PAPER_ORDER_STATUS.PARTIALLY_FILLED,
  ].includes(status);
}

export function createPaperOrderBook({
  createdAt =
    new Date().toISOString(),
} = {}) {
  return {
    version:
      PAPER_ORDER_BOOK_VERSION,

    orders: [],

    createdAt,

    updatedAt:
      createdAt,
  };
}

export function addOrderToBook({
  book,
  order,
  updatedAt =
    new Date().toISOString(),
} = {}) {
  if (!book || !Array.isArray(book.orders)) {
    throw new Error(
      "Paper order book is invalid.",
    );
  }

  if (!order?.orderId) {
    throw new Error(
      "Paper order is invalid.",
    );
  }

  if (
    book.orders.some(
      (row) =>
        row.orderId ===
        order.orderId,
    )
  ) {
    throw new Error(
      "Duplicate paper order id.",
    );
  }

  const next =
    clone(book);

  next.orders.push(
    clone(order),
  );

  next.updatedAt =
    updatedAt;

  return next;
}

export function updateOrderInBook({
  book,
  order,
  updatedAt =
    new Date().toISOString(),
} = {}) {
  if (!book || !Array.isArray(book.orders)) {
    throw new Error(
      "Paper order book is invalid.",
    );
  }

  const index =
    book.orders.findIndex(
      (row) =>
        row.orderId ===
        order?.orderId,
    );

  if (index < 0) {
    throw new Error(
      "Paper order was not found.",
    );
  }

  const next =
    clone(book);

  next.orders[index] =
    clone(order);

  next.updatedAt =
    updatedAt;

  return next;
}

export function findOrderById({
  book,
  orderId,
} = {}) {
  return (
    book?.orders?.find(
      (order) =>
        order.orderId ===
        orderId,
    ) || null
  );
}

export function listOrders({
  book,
  symbol = null,
  side = null,
  status = null,
} = {}) {
  return (
    book?.orders || []
  )
    .filter(
      (order) =>
        symbol === null ||
        order.symbol ===
          String(symbol)
            .trim()
            .toUpperCase(),
    )
    .filter(
      (order) =>
        side === null ||
        order.side === side,
    )
    .filter(
      (order) =>
        status === null ||
        order.status === status,
    )
    .sort(
      (a, b) =>
        orderTimestamp(a)
          .localeCompare(
            orderTimestamp(b),
          ),
    )
    .map(clone);
}

export function listOpenOrders({
  book,
  symbol = null,
} = {}) {
  return listOrders({
    book,
    symbol,
  }).filter(
    (order) =>
      isOpenStatus(
        order.status,
      ),
  );
}

export function listFilledOrders({
  book,
  symbol = null,
} = {}) {
  return listOrders({
    book,
    symbol,
    status:
      PAPER_ORDER_STATUS.FILLED,
  });
}

export function expireOrders({
  book,
  now =
    new Date().toISOString(),
} = {}) {
  if (!book || !Array.isArray(book.orders)) {
    throw new Error(
      "Paper order book is invalid.",
    );
  }

  const nowMs =
    Date.parse(now);

  const next =
    clone(book);

  next.orders =
    next.orders.map(
      (order) => {
        if (
          !isOpenStatus(
            order.status,
          )
        ) {
          return order;
        }

        const expiresAt =
          order.expiresAt ||
          order.metadata?.expiresAt ||
          null;

        if (!expiresAt) {
          return order;
        }

        const expiresAtMs =
          Date.parse(expiresAt);

        if (
          Number.isFinite(
            expiresAtMs,
          ) &&
          expiresAtMs <= nowMs
        ) {
          return {
            ...order,

            status:
              "expired",

            expiredAt:
              now,

            remainingQuantity:
              Math.max(
                0,
                Number(
                  order.remainingQuantity ||
                  0,
                ),
              ),
          };
        }

        return order;
      },
    );

  next.updatedAt =
    now;

  return next;
}

export function summarizeOrderBook(
  book = {},
) {
  const orders =
    book.orders || [];

  return {
    total:
      orders.length,

    open:
      orders.filter(
        (order) =>
          isOpenStatus(
            order.status,
          ),
      ).length,

    filled:
      orders.filter(
        (order) =>
          order.status ===
          PAPER_ORDER_STATUS.FILLED,
      ).length,

    cancelled:
      orders.filter(
        (order) =>
          order.status ===
          PAPER_ORDER_STATUS.CANCELLED,
      ).length,

    rejected:
      orders.filter(
        (order) =>
          order.status ===
          PAPER_ORDER_STATUS.REJECTED,
      ).length,

    expired:
      orders.filter(
        (order) =>
          order.status ===
          "expired",
      ).length,
  };
}

export const PaperOrderBookInternals = {
  clone,
  orderTimestamp,
  isOpenStatus,
};