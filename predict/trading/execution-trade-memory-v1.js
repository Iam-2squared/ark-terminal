import {
  saveTradeMemoryRecord,
} from "./trade-memory.js";

export const EXECUTION_TRADE_MEMORY_V1_VERSION =
  "execution-trade-memory-v1";

function finiteOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number)
    ? number
    : null;
}

function normalizeAction(value) {
  const action = String(value ?? "")
    .trim()
    .toUpperCase();

  return ["BUY", "SELL"].includes(action)
    ? action
    : null;
}

function executionId(execution = {}, cycle = {}) {
  return String(
    execution.id ??
    execution.executionId ??
    execution.orderId ??
    cycle.executionOrderId ??
    cycle.id ??
    "unknown",
  );
}

export function createExecutionTradeMemoryRecord({
  cycle = {},
  execution = {},
  transactionCost = {},
  portfolio = {},
  modelVersion = null,
  timestamp = null,
} = {}) {
  const action = normalizeAction(
    execution.side ?? cycle.decision,
  );

  if (!action) {
    throw new TypeError(
      "Execution Trade Memory requires BUY or SELL.",
    );
  }

  const symbol = String(
    execution.symbol ?? cycle.symbol ?? "",
  )
    .trim()
    .toUpperCase();

  if (!symbol) {
    throw new TypeError(
      "Execution Trade Memory symbol is required.",
    );
  }

  const occurredAt =
    timestamp ??
    execution.timestamp ??
    cycle.timestamp ??
    new Date().toISOString();

  const price = finiteOrNull(
    execution.executionPrice ??
    execution.price ??
    cycle.order?.price,
  );

  const quantity = finiteOrNull(
    execution.quantity ??
    cycle.order?.quantity,
  );

  const id = executionId(
    execution,
    cycle,
  );

  return {
    id: `execution-${id}`,
    version: EXECUTION_TRADE_MEMORY_V1_VERSION,
    createdAt: new Date(occurredAt).toISOString(),
    candidateKey: `execution|${id}`,
    executionId: id,
    cycleId: cycle.id ?? null,
    symbol,
    action,
    decision: action.toLowerCase(),
    executionMode: "paper",
    liveExecutionAllowed: false,
    cashBuyOnly: true,
    shortSellingEnabled: false,
    status: action === "SELL" ? "resolved" : "open",
    outcome: action === "SELL" ? "決済約定" : "新規約定",
    quantity,
    entryPrice: action === "BUY" ? price : null,
    exitPrice: action === "SELL" ? price : null,
    executionPrice: price,
    fee: finiteOrNull(
      transactionCost.totalCost ??
      transactionCost.fee,
    ),
    pnl: finiteOrNull(
      execution.pnl ??
      execution.realizedPnl,
    ),
    holdingPeriod: execution.holdingPeriod ?? null,
    aiScore: finiteOrNull(
      cycle.strategy?.finalScore ??
      cycle.strategy?.score,
    ),
    confidence: finiteOrNull(
      cycle.strategy?.confidence,
    ),
    risk: cycle.risk ?? null,
    strategyReasons:
      cycle.strategy?.reasons ??
      cycle.strategy?.explanations ??
      [],
    technical:
      cycle.strategy?.technical ??
      cycle.technical ??
      null,
    marketIntelligence:
      cycle.marketIntelligence ??
      null,
    model: modelVersion,
    modelVersion,
    portfolioAfter: portfolio,
    evaluation: {
      evaluatedAt:
        action === "SELL"
          ? new Date(occurredAt).toISOString()
          : null,
      exitPrice:
        action === "SELL"
          ? price
          : null,
      actualReturnPercent:
        finiteOrNull(
          execution.returnPercent,
        ),
      maximumFavorableMovePercent: null,
      maximumAdverseMovePercent: null,
      hit:
        finiteOrNull(execution.pnl) === null
          ? null
          : Number(execution.pnl) > 0,
    },
  };
}

export function saveProcessedExecutionToTradeMemory({
  cycle,
  processedResult,
  modelVersion = null,
  timestamp = null,
} = {}) {
  const execution =
    processedResult?.execution;

  if (!execution) {
    return {
      saved: false,
      duplicate: false,
      skipped: true,
      reason: "NO_EXECUTION",
      record: null,
    };
  }

  const record =
    createExecutionTradeMemoryRecord({
      cycle,
      execution,
      transactionCost:
        processedResult.transactionCost,
      portfolio:
        processedResult.portfolio,
      modelVersion,
      timestamp,
    });

  return {
    ...saveTradeMemoryRecord(record),
    skipped: false,
  };
}
