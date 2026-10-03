import { simulateP25ExitV3DualGate } from './phase57-p25-exit-v3-dual-gate.js';
import { simulateP25ExitV4 } from './phase57-p25-exit-v4-structural-risk.js';

export const PHASE57_EXIT_RESEARCH_TRACE_SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
  researchOnly: true,
});

const signOf = (direction) => direction === 'LONG' || direction === 'UP' || direction === 1 ? 1 : -1;
const directionalReturnPct = (entryPrice, price, sign) => (Number(price) / Number(entryPrice) - 1) * 100 * sign;

function normalizeBars(rows = []) {
  return rows.map((row) => ({
    timestamp: new Date(Date.parse(row.timestamp ?? row.time)).toISOString(),
    open: Number(row.open),
    high: Number(row.high),
    low: Number(row.low),
    close: Number(row.close),
    volume: Number(row.volume ?? 0),
  })).filter((row) => [row.open, row.high, row.low, row.close, row.volume].every(Number.isFinite) && row.close > 0)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

function finiteOrNull(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function horizonOne(baseScore) {
  return (baseScore?.horizonScores ?? []).find((score) => Number(score?.horizonBars) === 1) ?? null;
}

function diagnosticRow({ decision, bar, entryPrice, sign, runningMfePct, runningMaePct }) {
  const currentReturnPct = directionalReturnPct(entryPrice, bar.close, sign);
  const barMfePct = directionalReturnPct(entryPrice, sign === 1 ? bar.high : bar.low, sign);
  const barMaePct = directionalReturnPct(entryPrice, sign === 1 ? bar.low : bar.high, sign);
  const mfePct = Math.max(runningMfePct, barMfePct, 0);
  const maePct = Math.min(runningMaePct, barMaePct, 0);
  const givebackPct = Math.max(0, mfePct - currentReturnPct);
  const captureRatio = mfePct > 0 ? currentReturnPct / mfePct : null;
  const h1 = horizonOne(decision.baseScore);
  const gateDecision = String(decision.gate?.decision ?? 'HOLD');
  const reason = String(decision.gate?.reason ?? '');

  return {
    row: Object.freeze({
      timestamp: decision.timestamp,
      price: bar.close,
      unrealizedReturnPct: currentReturnPct,
      mfePct,
      maePct,
      givebackPct,
      captureRatio,
      stateBucket: String(decision.baseScore?.stateBucket ?? ''),
      baseReady: Boolean(decision.baseScore?.ready),
      baseDecision: String(decision.baseScore?.decision ?? 'HOLD'),
      baseReason: String(decision.baseScore?.reason ?? ''),
      bestHorizonBars: finiteOrNull(decision.baseScore?.bestHorizonBars),
      bestUpper90Pct: finiteOrNull(decision.baseScore?.bestUpper90Pct),
      downsideProbabilityH1: finiteOrNull(h1?.downsideProbability),
      upper90PctH1: finiteOrNull(h1?.upper90Pct),
      winnerExitStreak: finiteOrNull(decision.gate?.winnerExitStreak) ?? 0,
      neutralLossStreak: finiteOrNull(decision.gate?.neutralLossStreak) ?? 0,
      gateResult: gateDecision,
      holdReason: gateDecision === 'HOLD' ? reason : null,
      exitReason: gateDecision === 'EXIT' ? reason : null,
    }),
    mfePct,
    maePct,
  };
}

function assertResearchRow(row) {
  if (row?.entryAccepted !== true || row?.frozenBeforeOutcome !== true || row?.currentOutcomeUsed !== false) {
    throw new Error('EXIT research trace requires outcome-free frozen Entry');
  }
  if (!Number.isFinite(Number(row?.entryPrice)) || Number(row.entryPrice) <= 0) {
    throw new Error('EXIT research trace requires a finite positive entryPrice');
  }
}

export function buildP25ExitDecisionTrace({ row, analogPool, model, roundTripCostPct = 0.05 } = {}) {
  assertResearchRow(row);
  const modelId = String(model ?? '').toUpperCase();
  if (!['V3', 'V4'].includes(modelId)) throw new Error(`unsupported EXIT research trace model: ${model}`);

  const simulation = modelId === 'V3'
    ? simulateP25ExitV3DualGate({ row, analogPool, roundTripCostPct })
    : simulateP25ExitV4({ row, analogPool, roundTripCostPct });

  const bars = new Map(normalizeBars(row.futureBars ?? []).map((bar) => [bar.timestamp, bar]));
  const direction = signOf(row.signalDirection ?? row.direction) === 1 ? 'LONG' : 'SHORT';
  const sign = signOf(direction);
  const entryPrice = Number(row.entryPrice);
  const trace = [];
  let runningMfePct = 0;
  let runningMaePct = 0;

  for (const decision of simulation.managementDecisions ?? []) {
    const bar = bars.get(decision.timestamp);
    if (!bar) throw new Error(`EXIT research trace missing finalized bar for decision ${decision.timestamp}`);
    const diagnostic = diagnosticRow({ decision, bar, entryPrice, sign, runningMfePct, runningMaePct });
    runningMfePct = diagnostic.mfePct;
    runningMaePct = diagnostic.maePct;
    trace.push(diagnostic.row);
  }

  return Object.freeze({
    model: modelId,
    symbol: String(row.symbol ?? ''),
    sessionDate: String(row.sessionDate ?? ''),
    entryTimestamp: String(row.entryTimestamp ?? ''),
    entryPrice,
    direction,
    policySha256: simulation.policySha256,
    trace: Object.freeze(trace),
    summary: Object.freeze({
      exitTimestamp: simulation.exitTimestamp,
      exitPrice: simulation.exitPrice,
      exitReason: simulation.exitReason,
      barsHeld: simulation.barsHeld,
      grossReturnPct: simulation.grossReturnPct,
      netReturnPct: simulation.netReturnPct,
      mfePct: simulation.mfePct,
      maePct: simulation.maePct,
      givebackPct: simulation.givebackPct,
      captureRatio: simulation.captureRatio,
    }),
    safety: PHASE57_EXIT_RESEARCH_TRACE_SAFETY,
  });
}

export function buildP25ExitPairedDecisionTrace({ row, analogPool, roundTripCostPct = 0.05 } = {}) {
  assertResearchRow(row);
  const invariant = Object.freeze({
    symbol: String(row.symbol ?? ''),
    sessionDate: String(row.sessionDate ?? ''),
    entryTimestamp: String(row.entryTimestamp ?? ''),
    entryPrice: Number(row.entryPrice),
    direction: signOf(row.signalDirection ?? row.direction) === 1 ? 'LONG' : 'SHORT',
    roundTripCostPct: Number(roundTripCostPct),
    selectorEntryMarketDataAndAllocationFrozen: true,
  });
  const v3 = buildP25ExitDecisionTrace({ row, analogPool, model: 'V3', roundTripCostPct });
  const v4 = buildP25ExitDecisionTrace({ row, analogPool, model: 'V4', roundTripCostPct });
  return Object.freeze({ invariant, v3, v4, safety: PHASE57_EXIT_RESEARCH_TRACE_SAFETY });
}

export default {
  PHASE57_EXIT_RESEARCH_TRACE_SAFETY,
  buildP25ExitDecisionTrace,
  buildP25ExitPairedDecisionTrace,
};
