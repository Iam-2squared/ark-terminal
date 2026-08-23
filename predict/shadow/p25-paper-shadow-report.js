import { assessShadowFillFeasibility } from './fill-feasibility.js';

export const P25_PAPER_SHADOW_REPORT_VERSION = 'p25-paper-shadow-report-v1';

export function buildP25PaperShadowReport({ replayResult, observations = {}, options = {} } = {}) {
  if (!replayResult || replayResult.mode !== 'research_offline_only' || replayResult.executable !== false) {
    throw new Error('research-only replayResult is required.');
  }
  const rows = replayResult.events.map(event => {
    if (event.status !== 'simulated_fill') {
      return Object.freeze({ intentId: event.intentId, symbol: event.symbol, paperStatus: event.status, shadowStatus: 'NOT_APPLICABLE', divergence: null });
    }
    const observation = observations[event.intentId] ?? observations[event.symbol] ?? null;
    if (!observation) {
      return Object.freeze({ intentId: event.intentId, symbol: event.symbol, paperStatus: event.status, shadowStatus: 'BLOCKED', blockers: Object.freeze(['MARKET_OBSERVATION_MISSING']), divergence: 'paper_fill_without_shadow_observation' });
    }
    const assessment = assessShadowFillFeasibility({ quantity: replayResult.assumptions.quantity, ...observation }, options);
    return Object.freeze({
      intentId: event.intentId,
      symbol: event.symbol,
      paperStatus: event.status,
      shadowStatus: assessment.status,
      blockers: Object.freeze([...assessment.blockers]),
      metrics: Object.freeze({ ...assessment.metrics }),
      divergence: assessment.status === 'FEASIBLE' ? null : 'paper_fill_shadow_blocked',
    });
  });
  const simulatedFillCount = rows.filter(row => row.paperStatus === 'simulated_fill').length;
  const feasibleCount = rows.filter(row => row.shadowStatus === 'FEASIBLE').length;
  const blockedCount = rows.filter(row => row.shadowStatus === 'BLOCKED').length;
  return Object.freeze({
    version: P25_PAPER_SHADOW_REPORT_VERSION,
    mode: 'shadow_observation_only',
    executable: false,
    summary: Object.freeze({ simulatedFillCount, feasibleCount, blockedCount, feasibleShare: simulatedFillCount ? feasibleCount / simulatedFillCount : null }),
    rows: Object.freeze(rows),
    safety: Object.freeze({ executionAllowed: false, brokerWriteAllowed: false, orderCreationAllowed: false, liveTradingAllowed: false, paperTradingAllowed: false, automaticPromotionAllowed: false }),
  });
}
