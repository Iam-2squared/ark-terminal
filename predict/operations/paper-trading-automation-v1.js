export const PAPER_TRADING_AUTOMATION_V1 = "paper-trading-automation-v1";

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function runPaperTradingAutomationV1({
  predictions = [],
  portfolio = { cash: 0, positions: [] },
  prices = {},
  maxPositionRate = 0.1,
  killSwitch = false,
  asOf = new Date().toISOString(),
} = {}) {
  const currentPositions = new Map((portfolio.positions ?? []).map((p) => [p.symbol, { ...p }]));
  const startingCash = finite(portfolio.cash);
  let cash = startingCash;
  const orders = [];
  const fills = [];
  const memory = [];

  if (!killSwitch) {
    for (const prediction of predictions) {
      const symbol = prediction?.symbol;
      const price = finite(prices?.[symbol], 0);
      if (!symbol || price <= 0 || prediction?.brokerExecutionAllowed !== false) continue;
      const action = String(prediction.action ?? "NO_TRADE").toUpperCase();
      const confidence = finite(prediction.confidence);
      const aiScore = finite(prediction.aiScore);
      if (action === "BUY") {
        const budget = Math.max(0, startingCash * maxPositionRate);
        const quantity = Math.floor(budget / price);
        if (quantity > 0 && cash >= quantity * price) {
          const cost = quantity * price;
          cash -= cost;
          const prior = currentPositions.get(symbol) ?? { symbol, quantity: 0, averagePrice: 0 };
          const nextQuantity = prior.quantity + quantity;
          const averagePrice = nextQuantity ? ((prior.quantity * prior.averagePrice) + cost) / nextQuantity : 0;
          currentPositions.set(symbol, { symbol, quantity: nextQuantity, averagePrice });
          orders.push({ symbol, side: "BUY", quantity, type: "MARKET", status: "FILLED" });
          fills.push({ symbol, side: "BUY", quantity, price, filledAt: asOf });
        }
      } else if (action === "SELL") {
        const prior = currentPositions.get(symbol);
        const quantity = Math.max(0, finite(prior?.quantity));
        if (quantity > 0) {
          cash += quantity * price;
          currentPositions.delete(symbol);
          orders.push({ symbol, side: "SELL", quantity, type: "MARKET", status: "FILLED" });
          fills.push({ symbol, side: "SELL", quantity, price, filledAt: asOf });
        }
      }
      memory.push({ symbol, action, confidence, aiScore, recordedAt: asOf });
    }
  }

  return {
    version: PAPER_TRADING_AUTOMATION_V1,
    generatedAt: asOf,
    status: killSwitch ? "HALTED" : "READY",
    killSwitch,
    orders,
    fills,
    portfolio: { cash, positions: [...currentPositions.values()] },
    tradeMemory: memory,
    paperOnly: true,
    brokerExecutionAllowed: false,
    liveTradingAllowed: false,
    humanApprovalRequired: true,
  };
}

export default runPaperTradingAutomationV1;
