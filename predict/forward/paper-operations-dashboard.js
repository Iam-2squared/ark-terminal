export const PAPER_OPERATIONS_DASHBOARD_VERSION = "phase25-paper-operations-dashboard-v1";

const finite = (value) => Number.isFinite(Number(value));
const normalize = (value, fallback = "UNKNOWN") => String(value ?? fallback).trim().toUpperCase() || fallback;
const average = (values) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

function summarize(rows = []) {
  const resolved = rows.filter((row) => normalize(row.status) === "RESOLVED" && finite(row.netReturn));
  const returns = resolved.map((row) => Number(row.netReturn));
  const wins = returns.filter((value) => value > 0);
  const losses = returns.filter((value) => value < 0);
  const grossProfit = wins.reduce((sum, value) => sum + value, 0);
  const grossLoss = Math.abs(losses.reduce((sum, value) => sum + value, 0));

  let equity = 0;
  let peak = 0;
  let maxDrawdown = 0;
  for (const value of returns) {
    equity += value;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak - equity);
  }

  return {
    resolvedCount: resolved.length,
    netReturn: returns.reduce((sum, value) => sum + value, 0),
    averageReturn: average(returns),
    winRate: resolved.length ? wins.length / resolved.length : null,
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : null,
    maxDrawdown,
    exposure: finite(resolved[0]?.exposure) ? average(resolved.map((row) => Number(row.exposure ?? 0))) : null,
    turnover: resolved.reduce((sum, row) => sum + (finite(row.turnover) ? Number(row.turnover) : 0), 0),
  };
}

function groupBy(rows, selector) {
  const groups = new Map();
  for (const row of rows) {
    const key = normalize(selector(row));
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return [...groups.entries()]
    .map(([key, groupedRows]) => ({ key, ...summarize(groupedRows) }))
    .sort((a, b) => a.key.localeCompare(b.key));
}

export function buildPaperOperationsDashboard(rows = [], context = {}) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");

  return {
    version: PAPER_OPERATIONS_DASHBOARD_VERSION,
    generatedAt: context.generatedAt ?? null,
    sessions: finite(context.sessions) ? Number(context.sessions) : null,
    overall: summarize(rows),
    byMarketRegime: groupBy(rows, (row) => row.marketRegime),
    byStrategy: groupBy(rows, (row) => row.strategy),
    byCandidate: groupBy(rows, (row) => row.candidateVersion ?? row.modelVersion),
    pendingCount: rows.filter((row) => normalize(row.status) !== "RESOLVED").length,
    safety: {
      paperOnly: true,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
    },
  };
}

export default buildPaperOperationsDashboard;
