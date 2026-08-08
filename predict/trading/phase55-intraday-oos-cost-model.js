export const PHASE55_SAFETY = Object.freeze({
  mode: 'INTRADAY_OOS_COST_MODEL_READ_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

export const DEFAULT_PHASE55_COST_POLICY = Object.freeze({
  feeRate: 0.0005,
  spreadBps: 8,
  slippageBps: 6,
  latencyBps: 2,
  liquidityPenaltyBps: 4,
  minimumLiquidityYen: 10_000_000,
  annualizationPeriods: 252,
});

const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, Number(value)));
const finite = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const mean = (values) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
const std = (values) => {
  if (values.length < 2) return 0;
  const average = mean(values);
  return Math.sqrt(mean(values.map((value) => (value - average) ** 2)));
};

export function estimatePhase55ExecutionCost(row = {}, policy = {}) {
  const resolved = { ...DEFAULT_PHASE55_COST_POLICY, ...(policy || {}) };
  const liquidityYen = finite(row.liquidityYen) ? Number(row.liquidityYen) : null;
  const baseBps = Number(resolved.spreadBps) + Number(resolved.slippageBps) + Number(resolved.latencyBps);
  const liquidityPenaltyBps = liquidityYen !== null && liquidityYen < Number(resolved.minimumLiquidityYen)
    ? Number(resolved.liquidityPenaltyBps)
    : 0;
  const variableRate = (baseBps + liquidityPenaltyBps) / 10_000;
  const feeRate = Number(resolved.feeRate);
  const totalRate = Math.max(0, feeRate + variableRate);
  return Object.freeze({
    totalRate,
    feeRate,
    spreadRate: Number(resolved.spreadBps) / 10_000,
    slippageRate: Number(resolved.slippageBps) / 10_000,
    latencyRate: Number(resolved.latencyBps) / 10_000,
    liquidityPenaltyRate: liquidityPenaltyBps / 10_000,
    liquidityConstrained: liquidityPenaltyBps > 0,
  });
}

function normalizeRows(rows = []) {
  if (!Array.isArray(rows) || rows.length < 2) throw new RangeError('at least two OOS rows are required');
  return rows.map((row, index) => {
    const sessionDate = String(row?.sessionDate || row?.date || '');
    if (!/^\d{4}-\d{2}-\d{2}/.test(sessionDate)) throw new TypeError(`row ${index} has invalid sessionDate`);
    const probability = Number(row.probability);
    const actualReturn = Number(row.actualReturn);
    if (!Number.isFinite(probability) || probability < 0 || probability > 1) throw new TypeError(`row ${index} probability must be 0..1`);
    if (!Number.isFinite(actualReturn)) throw new TypeError(`row ${index} actualReturn must be finite`);
    return Object.freeze({
      id: String(row.id || `${row.symbol || 'UNKNOWN'}:${sessionDate}:${index}`),
      symbol: String(row.symbol || 'UNKNOWN'),
      sessionDate: sessionDate.slice(0, 10),
      probability,
      actualReturn,
      liquidityYen: finite(row.liquidityYen) ? Number(row.liquidityYen) : null,
    });
  }).sort((a, b) => a.sessionDate.localeCompare(b.sessionDate) || a.id.localeCompare(b.id));
}

function metrics(returns, annualizationPeriods) {
  const gains = returns.filter((value) => value > 0).reduce((sum, value) => sum + value, 0);
  const losses = Math.abs(returns.filter((value) => value < 0).reduce((sum, value) => sum + value, 0));
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  for (const value of returns) {
    equity *= 1 + value;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak ? (peak - equity) / peak : 0);
  }
  const sigma = std(returns);
  return Object.freeze({
    netReturn: equity - 1,
    profitFactor: losses ? gains / losses : gains > 0 ? 999 : 0,
    sharpe: sigma ? mean(returns) / sigma * Math.sqrt(Number(annualizationPeriods) || 252) : 0,
    maxDrawdown,
    tradeCount: returns.length,
    winRate: returns.length ? returns.filter((value) => value > 0).length / returns.length : 0,
  });
}

export function evaluatePhase55IntradayOos({
  rows,
  threshold = 0.55,
  costPolicy = {},
  benchmarkReturns = [],
} = {}) {
  const normalized = normalizeRows(rows);
  const resolved = { ...DEFAULT_PHASE55_COST_POLICY, ...(costPolicy || {}) };
  const tradeReturns = normalized.map((row) => {
    const direction = row.probability >= Number(threshold) ? 1 : -1;
    const grossReturn = direction * row.actualReturn;
    const cost = estimatePhase55ExecutionCost(row, resolved);
    return grossReturn - cost.totalRate;
  });
  const strategy = metrics(tradeReturns, resolved.annualizationPeriods);
  const benchmark = Array.isArray(benchmarkReturns) && benchmarkReturns.length === tradeReturns.length
    ? metrics(benchmarkReturns.map(Number), resolved.annualizationPeriods)
    : null;
  const benchmarkExcessReturn = benchmark ? strategy.netReturn - benchmark.netReturn : null;
  const promotionEligible = Boolean(
    benchmark &&
    strategy.tradeCount >= 20 &&
    strategy.profitFactor > 1 &&
    strategy.sharpe > 0 &&
    strategy.maxDrawdown < 0.35 &&
    benchmarkExcessReturn > 0
  );

  return Object.freeze({
    phase: '55',
    status: 'OOS_COST_EVALUATED',
    threshold: clamp(threshold, 0, 1),
    strategy,
    benchmark,
    benchmarkExcessReturn,
    promotionEligible,
    automaticPromotionAllowed: false,
    reviewOnly: true,
    transmitted: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    humanApprovalRequired: true,
    costPolicy: Object.freeze(resolved),
    safety: PHASE55_SAFETY,
  });
}
