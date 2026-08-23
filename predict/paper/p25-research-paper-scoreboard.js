export const P25_RESEARCH_PAPER_SCOREBOARD_VERSION = 'p25-research-paper-scoreboard-v1';

function finite(value) { return Number.isFinite(Number(value)); }

function equityCurveFromLedger(ledger) {
  if (!ledger || !Array.isArray(ledger.sessions)) throw new Error('research Paper ledger sessions required');
  const initialCash = Number(ledger.initialCash);
  if (!finite(initialCash) || initialCash <= 0) throw new Error('valid initialCash required');
  return ledger.sessions.map(row => {
    const equity = Number(row?.account?.equity);
    if (!finite(equity)) throw new Error(`equity missing for ${row?.sessionDate ?? 'unknown session'}`);
    return Object.freeze({ sessionDate: String(row.sessionDate), equity, eventCount: Number(row.eventCount || 0) });
  });
}

function maximumDrawdownPct(curve, initialCash) {
  let peak = Number(initialCash);
  let max = 0;
  for (const row of curve) {
    peak = Math.max(peak, row.equity);
    if (peak > 0) max = Math.max(max, ((peak - row.equity) / peak) * 100);
  }
  return max;
}

export function buildP25ResearchPaperScoreboard({ state } = {}) {
  if (!state || state.mode !== 'research_offline_only' || state.executable !== false) throw new Error('valid research-only Paper state required');
  const ledger = state.ledger;
  const curve = equityCurveFromLedger(ledger);
  const initialCash = Number(ledger.initialCash);
  const endingEquity = curve.length ? curve[curve.length - 1].equity : initialCash;
  const totalEvents = curve.reduce((sum, row) => sum + row.eventCount, 0);
  const reports = Array.isArray(state.reports) ? state.reports : [];
  const killSwitchTripped = reports.some(row => row?.killSwitch?.tripped === true);
  const latestKillSwitch = reports.length ? reports[reports.length - 1]?.killSwitch ?? null : null;
  const shadowObservedSessionCount = reports.filter(row => row?.shadowReport).length;

  return Object.freeze({
    version: P25_RESEARCH_PAPER_SCOREBOARD_VERSION,
    mode: 'research_offline_only',
    executable: false,
    completedSessionCount: curve.length,
    totalReplayEvents: totalEvents,
    averageReplayEventsPerSession: curve.length ? totalEvents / curve.length : 0,
    initialCash,
    endingEquity,
    cumulativeReturnPct: initialCash > 0 ? ((endingEquity / initialCash) - 1) * 100 : null,
    maximumDrawdownPct: maximumDrawdownPct(curve, initialCash),
    equityCurve: Object.freeze(curve),
    shadowObservedSessionCount,
    killSwitchTripped,
    latestKillSwitch,
    assumptions: Object.freeze({ ...(state.assumptions || {}) }),
    methodology: Object.freeze({
      cumulativeEquityFromAppendOnlyLedger: true,
      noModelSelectionFromScoreboard: true,
      noDynamicNSelectionFromScoreboard: true,
      performanceConclusionAllowed: false,
      freshHoldoutConsumed: false,
    }),
  });
}

export const P25ResearchPaperScoreboardInternals = Object.freeze({ equityCurveFromLedger, maximumDrawdownPct });
