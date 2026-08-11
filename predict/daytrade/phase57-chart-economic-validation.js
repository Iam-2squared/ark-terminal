import { PHASE57_P23_8D_SAFETY, P23_8D_FROZEN_RATCHET_CONFIG } from './phase57-frozen-ratchet-exit.js';

export const P23_10F_ECONOMIC_POLICY = Object.freeze({
  phase: '57.p23.10f',
  q4MinScore: 0.70,
  q4ThresholdFrozenFromP23_10D: true,
  signalObservedAtCompletedBarClose: true,
  entryAtNextFiveMinuteBarOpen: true,
  oneActiveTradePerSymbol: true,
  sameSessionOnly: true,
  exitConfigId: P23_8D_FROZEN_RATCHET_CONFIG.configId,
  roundTripFrictionPct: Number(P23_8D_FROZEN_RATCHET_CONFIG.roundTripCostPct),
  frictionInterpretation: 'aggregate round-trip execution-friction proxy already frozen in P23.8D; no additional post-hoc slippage tuning',
  setupRuleRetuningAllowed: false,
  qualityRuleRetuningAllowed: false,
  exitRetuningAllowed: false,
  outerOutcomeSelectionAllowed: false,
  recommendationAllowed: false,
  edgeClaimAllowed: false,
});

export const PHASE57_P23_10F_SAFETY = Object.freeze({
  ...PHASE57_P23_8D_SAFETY,
  mode: 'PHASE57_P23_10F_FROZEN_CHART_ECONOMIC_VALIDATION_READ_ONLY_RESEARCH',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  transmitted: false,
});

const finite = value => Number.isFinite(Number(value));
const mean = values => values.length ? values.reduce((sum, value) => sum + Number(value), 0) / values.length : null;

export function frozenQualityBand(score) {
  const s = Number(score);
  if (!finite(s)) return 'UNSCORED';
  if (s < 0.40) return 'Q1_LOW';
  if (s < 0.55) return 'Q2';
  if (s < P23_10F_ECONOMIC_POLICY.q4MinScore) return 'Q3';
  return 'Q4_HIGH';
}

export function isFrozenQ4Candidate(score) {
  return finite(score) && Number(score) >= P23_10F_ECONOMIC_POLICY.q4MinScore;
}

export function maxSequentialDrawdownPctPoints(trades = []) {
  let equity = 0;
  let peak = 0;
  let maxDrawdown = 0;
  for (const trade of [...trades].sort((a, b) => String(a.entryTimestamp).localeCompare(String(b.entryTimestamp)))) {
    equity += Number(trade.netReturnPct || 0);
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak - equity);
  }
  return maxDrawdown;
}

export function summarizeEconomicTrades(trades = []) {
  const rows = trades.filter(row => finite(row?.netReturnPct));
  const net = rows.map(row => Number(row.netReturnPct));
  const gross = rows.map(row => Number(row.grossReturnPct));
  const positive = net.filter(value => value > 0);
  const negative = net.filter(value => value < 0);
  const grossProfit = positive.reduce((sum, value) => sum + value, 0);
  const grossLoss = Math.abs(negative.reduce((sum, value) => sum + value, 0));
  const bySymbol = new Map();
  for (const row of rows) bySymbol.set(row.symbol, (bySymbol.get(row.symbol) ?? 0) + 1);
  const maxSymbolCount = bySymbol.size ? Math.max(...bySymbol.values()) : 0;
  return Object.freeze({
    tradeCount: rows.length,
    uniqueSymbols: bySymbol.size,
    winRate: rows.length ? positive.length / rows.length : null,
    averageGrossReturnPct: mean(gross),
    averageNetReturnPct: mean(net),
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : (grossProfit > 0 ? Infinity : null),
    averageMfePct: mean(rows.map(row => Number(row.mfePct)).filter(finite)),
    averageMaePct: mean(rows.map(row => Number(row.maePct)).filter(finite)),
    averageGivebackPctPoints: mean(rows.map(row => Number(row.profitGivebackPctPoints)).filter(finite)),
    averageCaptureRatio: mean(rows.map(row => Number(row.captureRatio)).filter(finite)),
    averageBarsHeld: mean(rows.map(row => Number(row.barsHeld)).filter(finite)),
    maxSequentialDrawdownPctPoints: maxSequentialDrawdownPctPoints(rows),
    maxSingleSymbolShare: rows.length ? maxSymbolCount / rows.length : null,
    positiveTradeCount: positive.length,
    negativeTradeCount: negative.length,
    zeroTradeCount: rows.length - positive.length - negative.length,
  });
}

export default {
  P23_10F_ECONOMIC_POLICY,
  PHASE57_P23_10F_SAFETY,
  frozenQualityBand,
  isFrozenQ4Candidate,
  maxSequentialDrawdownPctPoints,
  summarizeEconomicTrades,
};
