export const P25_PAPER_KILL_SWITCH_VERSION = 'p25-paper-kill-switch-v1';

export const DEFAULT_P25_PAPER_KILL_SWITCH_POLICY = Object.freeze({
  maximumDrawdownPct: 10,
  minimumEquity: 0,
  maximumBlockedShadowShare: 0.5,
  requirePaperTradingDisabled: true,
  requireLiveTradingDisabled: true,
});

function finite(value) { return Number.isFinite(Number(value)); }

export function evaluateP25PaperKillSwitch({ account, shadowReport = null, safety = {}, policy = {} } = {}) {
  const resolved = { ...DEFAULT_P25_PAPER_KILL_SWITCH_POLICY, ...(policy || {}) };
  const reasons = [];
  if (!account || !finite(account.equity) || !finite(account.initialCash)) reasons.push('ACCOUNT_INVALID');
  const equity = finite(account?.equity) ? Number(account.equity) : null;
  const initialCash = finite(account?.initialCash) ? Number(account.initialCash) : null;
  const drawdownPct = initialCash > 0 && equity !== null ? Math.max(0, ((initialCash - equity) / initialCash) * 100) : null;
  if (drawdownPct === null) reasons.push('DRAWDOWN_UNAVAILABLE');
  else if (drawdownPct > Number(resolved.maximumDrawdownPct)) reasons.push('MAX_DRAWDOWN_EXCEEDED');
  if (equity !== null && equity < Number(resolved.minimumEquity)) reasons.push('MINIMUM_EQUITY_BREACHED');

  if (shadowReport) {
    const total = Number(shadowReport.summary?.simulatedFillCount || 0);
    const blocked = Number(shadowReport.summary?.blockedCount || 0);
    const blockedShare = total > 0 ? blocked / total : 0;
    if (blockedShare > Number(resolved.maximumBlockedShadowShare)) reasons.push('SHADOW_BLOCKED_SHARE_EXCEEDED');
  }

  if (resolved.requirePaperTradingDisabled && safety.paperTradingAllowed !== false) reasons.push('PAPER_TRADING_NOT_DISABLED');
  if (resolved.requireLiveTradingDisabled && safety.liveTradingAllowed !== false) reasons.push('LIVE_TRADING_NOT_DISABLED');
  for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','automaticPromotionAllowed','productionUpdateAllowed']) {
    if (safety[key] !== false) reasons.push(`${key.toUpperCase()}_NOT_DISABLED`);
  }

  return Object.freeze({
    version: P25_PAPER_KILL_SWITCH_VERSION,
    tripped: reasons.length > 0,
    status: reasons.length > 0 ? 'HALT_RESEARCH_PAPER_PIPELINE' : 'RESEARCH_PIPELINE_HEALTHY',
    reasons: Object.freeze(reasons),
    metrics: Object.freeze({ equity, initialCash, drawdownPct }),
    policy: Object.freeze(resolved),
    executable: false,
  });
}
