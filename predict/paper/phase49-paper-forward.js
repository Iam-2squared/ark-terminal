import crypto from "node:crypto";

export const PHASE49_SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

function checksum(value) {
  return crypto.createHash("sha256").update(JSON.stringify(stable(value))).digest("hex");
}

function num(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function buildPaperOrderIdea({ symbol, probabilityUp, confidence, expectedReturn, close, quantity = 100 } = {}) {
  const side = num(probabilityUp) >= 0.5 ? "BUY" : "SELL";
  const price = num(close);
  const order = {
    symbol: String(symbol || "").toUpperCase(),
    side,
    quantity: Math.max(1, Math.floor(num(quantity, 100))),
    intendedPrice: price,
    probabilityUp: num(probabilityUp),
    confidence: num(confidence),
    expectedReturn: num(expectedReturn),
    mode: "PAPER_ONLY",
    transmissionAllowed: false,
  };
  return Object.freeze({ ...order, orderId: checksum(order).slice(0, 24), safety: PHASE49_SAFETY });
}

export function simulatePaperFill(order, market = {}, costs = {}) {
  if (!order || order.mode !== "PAPER_ONLY") throw new TypeError("paper order required");
  const spreadBps = Math.max(0, num(costs.spreadBps, 5));
  const slippageBps = Math.max(0, num(costs.slippageBps, 8));
  const feeBps = Math.max(0, num(costs.feeBps, 2));
  const sign = order.side === "BUY" ? 1 : -1;
  const reference = num(market.open ?? market.close ?? order.intendedPrice);
  const fillPrice = reference * (1 + sign * (spreadBps + slippageBps) / 10000);
  const grossNotional = fillPrice * order.quantity;
  const fee = grossNotional * feeBps / 10000;
  return Object.freeze({
    fillId: checksum({ orderId: order.orderId, reference, fillPrice, fee }).slice(0, 24),
    orderId: order.orderId,
    symbol: order.symbol,
    side: order.side,
    quantity: order.quantity,
    referencePrice: reference,
    fillPrice,
    fee,
    grossNotional,
    mode: "PAPER_ONLY",
    transmitted: false,
    safety: PHASE49_SAFETY,
  });
}

export function settlePaperTrade(fill, outcome = {}) {
  const exitPrice = num(outcome.exitPrice ?? outcome.close);
  const direction = fill.side === "BUY" ? 1 : -1;
  const grossPnl = direction * (exitPrice - fill.fillPrice) * fill.quantity;
  const netPnl = grossPnl - fill.fee;
  const returnPct = fill.grossNotional > 0 ? netPnl / fill.grossNotional : 0;
  return Object.freeze({
    tradeId: checksum({ fillId: fill.fillId, exitPrice }).slice(0, 24),
    fillId: fill.fillId,
    symbol: fill.symbol,
    side: fill.side,
    quantity: fill.quantity,
    entryPrice: fill.fillPrice,
    exitPrice,
    grossPnl,
    fee: fill.fee,
    netPnl,
    returnPct,
    won: netPnl > 0,
    status: "SETTLED_PAPER",
    safety: PHASE49_SAFETY,
  });
}

export function summarizePaperTrades(trades = []) {
  const settled = trades.filter((t) => t?.status === "SETTLED_PAPER");
  const wins = settled.filter((t) => t.netPnl > 0);
  const losses = settled.filter((t) => t.netPnl < 0);
  const grossProfit = wins.reduce((s, t) => s + t.netPnl, 0);
  const grossLoss = Math.abs(losses.reduce((s, t) => s + t.netPnl, 0));
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  for (const trade of settled) {
    equity *= 1 + trade.returnPct;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak ? (peak - equity) / peak : 0);
  }
  return Object.freeze({
    tradeCount: settled.length,
    winRate: settled.length ? wins.length / settled.length : 0,
    netPnl: settled.reduce((s, t) => s + t.netPnl, 0),
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0,
    maxDrawdown,
    equityMultiple: equity,
    safety: PHASE49_SAFETY,
  });
}

export function buildPaperForwardCycle({ predictions = [], marketBySymbol = {}, outcomeBySymbol = {}, costs = {} } = {}) {
  const orders = predictions.map((prediction) => buildPaperOrderIdea(prediction));
  const fills = orders.map((order) => simulatePaperFill(order, marketBySymbol[order.symbol] || {}, costs));
  const trades = fills.map((fill) => settlePaperTrade(fill, outcomeBySymbol[fill.symbol] || {}));
  const summary = summarizePaperTrades(trades);
  const payload = {
    schemaVersion: 1,
    status: "PAPER_FORWARD_COMPLETE",
    orders,
    fills,
    trades,
    summary,
    brokerWrites: 0,
    excelOrderWrites: 0,
    rssOrderCalls: 0,
    liveOrders: 0,
    safety: PHASE49_SAFETY,
  };
  return Object.freeze({ ...payload, checksum: checksum(payload) });
}

export function auditPaperForwardCycle(cycle) {
  const blockers = [];
  if (!cycle || cycle.status !== "PAPER_FORWARD_COMPLETE") blockers.push("INVALID_STATUS");
  if (cycle?.brokerWrites !== 0) blockers.push("BROKER_WRITE_DETECTED");
  if (cycle?.excelOrderWrites !== 0) blockers.push("EXCEL_ORDER_WRITE_DETECTED");
  if (cycle?.rssOrderCalls !== 0) blockers.push("RSS_ORDER_CALL_DETECTED");
  if (cycle?.liveOrders !== 0) blockers.push("LIVE_ORDER_DETECTED");
  const copy = { ...cycle };
  const actual = copy.checksum;
  delete copy.checksum;
  if (actual !== checksum(copy)) blockers.push("CHECKSUM_MISMATCH");
  return Object.freeze({ status: blockers.length ? "BLOCKED" : "VALID", blockers, safety: PHASE49_SAFETY });
}
