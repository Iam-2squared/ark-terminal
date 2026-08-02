export const PAPER_LEDGER_VERSION =
  "paper-ledger-v1";

function createId(
  prefix = "ledger",
) {
  return (
    prefix +
    "-" +
    Date.now().toString(36) +
    "-" +
    Math.random()
      .toString(36)
      .slice(2, 10)
  );
}

export function createLedgerEntry({
  entryId =
    createId(),

  type,

  amount = 0,

  symbol = null,

  quantity = null,

  price = null,

  orderId = null,

  description = "",

  createdAt =
    new Date().toISOString(),

  metadata = {},
} = {}) {
  return {
    version:
      PAPER_LEDGER_VERSION,

    entryId:
      String(entryId),

    type:
      String(type),

    amount:
      Number(amount || 0),

    symbol:
      symbol === null
        ? null
        : String(symbol),

    quantity:
      quantity === null
        ? null
        : Number(quantity),

    price:
      price === null
        ? null
        : Number(price),

    orderId:
      orderId === null
        ? null
        : String(orderId),

    description:
      String(description),

    createdAt,

    metadata: {
      ...metadata,
    },
  };
}

export function appendLedgerEntry({
  ledger = [],
  entry,
} = {}) {
  return [
    ...ledger,
    entry,
  ];
}

export function calculateLedgerBalance(
  ledger = [],
) {
  return ledger.reduce(
    (sum, entry) =>
      sum +
      Number(
        entry.amount || 0,
      ),
    0,
  );
}