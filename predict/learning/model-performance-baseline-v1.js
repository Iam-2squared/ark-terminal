export const MODEL_PERFORMANCE_BASELINE_V1_VERSION = "model-performance-baseline-v1";

const DEFAULT_STORAGE_KEY = "ark.phase11.modelPerformanceBaseline.v1";

function number(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function isClosedTrade(record = {}) {
  const action = String(record.action ?? record.decision ?? "").toUpperCase();
  const status = String(record.status ?? record.outcome ?? "").toUpperCase();
  return ["BUY", "SELL"].includes(action) && ["WIN", "LOSS", "FLAT", "CLOSED"].includes(status);
}

function tradeReturn(record = {}) {
  return number(record.returnPercent ?? record.pnlPercent ?? record.return, 0);
}

function maxDrawdown(returns = []) {
  let equity = 1;
  let peak = 1;
  let worst = 0;
  for (const value of returns) {
    equity *= 1 + value / 100;
    peak = Math.max(peak, equity);
    const dd = peak ? ((peak - equity) / peak) * 100 : 0;
    worst = Math.max(worst, dd);
  }
  return worst;
}

function sharpe(returns = []) {
  if (returns.length < 2) return null;
  const mean = returns.reduce((sum, value) => sum + value, 0) / returns.length;
  const variance = returns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / returns.length;
  const sd = Math.sqrt(variance);
  return sd ? (mean / sd) * Math.sqrt(252) : null;
}

function summarize(records = []) {
  const closed = records.filter(isClosedTrade);
  const returns = closed.map(tradeReturn);
  const wins = returns.filter((value) => value > 0);
  const losses = returns.filter((value) => value < 0);
  const grossProfit = wins.reduce((sum, value) => sum + value, 0);
  const grossLoss = Math.abs(losses.reduce((sum, value) => sum + value, 0));
  return {
    count: closed.length,
    wins: wins.length,
    losses: losses.length,
    winRate: closed.length ? (wins.length / closed.length) * 100 : null,
    accuracy: closed.length ? (wins.length / closed.length) * 100 : null,
    profitFactor: grossLoss ? grossProfit / grossLoss : (grossProfit > 0 ? Infinity : null),
    sharpe: sharpe(returns),
    maxDrawdown: maxDrawdown(returns),
    averageReturn: returns.length ? returns.reduce((sum, value) => sum + value, 0) / returns.length : null,
  };
}

function group(records, selector) {
  const grouped = new Map();
  for (const record of records.filter(isClosedTrade)) {
    const key = String(selector(record) ?? "UNKNOWN").toUpperCase();
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(record);
  }
  return Object.fromEntries([...grouped].map(([key, items]) => [key, summarize(items)]));
}

export function createModelPerformanceBaseline({
  records = [],
  productionModel = {},
  generatedAt = new Date().toISOString(),
  source = "TRADE_MEMORY",
} = {}) {
  const closed = (Array.isArray(records) ? records : []).filter(isClosedTrade);
  const baseline = {
    id: `production-baseline-${productionModel.version ?? "unknown"}-${generatedAt}`,
    version: MODEL_PERFORMANCE_BASELINE_V1_VERSION,
    generatedAt,
    source,
    productionModelVersion: productionModel.version ?? null,
    sourceTradeCount: closed.length,
    overall: summarize(closed),
    byAction: group(closed, (record) => record.action ?? record.decision),
    byRegime: group(closed, (record) => record.marketRegime ?? record.regime),
    bySector: group(closed, (record) => record.sector),
    frozen: true,
    safety: {
      productionUpdateAllowed: false,
      humanApprovalRequired: true,
      brokerExecutionAllowed: false,
    },
    warnings: closed.length < 30 ? ["INSUFFICIENT_BASELINE_SAMPLE"] : [],
  };
  return Object.freeze(baseline);
}

function parse(raw) {
  try {
    const value = JSON.parse(raw ?? "null");
    return value && typeof value === "object" ? value : null;
  } catch {
    return null;
  }
}

export class ModelPerformanceBaselineStoreV1 {
  constructor({ storage = globalThis?.localStorage ?? null, key = DEFAULT_STORAGE_KEY } = {}) {
    this.storage = storage;
    this.key = key;
  }

  load() {
    if (!this.storage?.getItem) return null;
    return parse(this.storage.getItem(this.key));
  }

  freeze(baseline, { replace = false } = {}) {
    if (!baseline || typeof baseline !== "object") throw new TypeError("baseline must be an object");
    const current = this.load();
    if (current && !replace) throw new Error("BASELINE_ALREADY_FROZEN");
    if (this.storage?.setItem) this.storage.setItem(this.key, JSON.stringify(baseline));
    return baseline;
  }

  clear({ approvedBy } = {}) {
    if (!approvedBy) throw new Error("HUMAN_APPROVAL_REQUIRED");
    if (this.storage?.removeItem) this.storage.removeItem(this.key);
  }
}

export default createModelPerformanceBaseline;
