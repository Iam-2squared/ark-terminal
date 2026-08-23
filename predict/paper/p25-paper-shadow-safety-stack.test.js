import test from 'node:test';
import assert from 'node:assert/strict';
import { replayP25ResearchSignals } from './p25-offline-paper-replay.js';
import { createResearchPaperLedger, appendResearchPaperSession, verifyResearchPaperLedger } from './p25-research-paper-ledger.js';
import { buildP25PaperShadowReport } from '../shadow/p25-paper-shadow-report.js';
import { evaluateP25PaperKillSwitch } from '../shadow/p25-paper-kill-switch.js';

const SAFETY = Object.freeze({
  executionAllowed:false, brokerWriteAllowed:false, excelOrderWriteAllowed:false, rssOrderFunctionAllowed:false,
  liveTradingAllowed:false, paperTradingAllowed:false, automaticPromotionAllowed:false, productionUpdateAllowed:false,
});

function signal() {
  return { signalId:'sig-1', evidenceDate:'2026-08-24', sourceTimestamp:'2026-08-24T00:05:00.000Z', symbol:'7203.T', direction:'UP', universeVariant:'Dynamic50', modelVersion:'frozen-p25', lineageHeadSha256:'lineage' };
}

test('append-only Paper ledger verifies and rejects duplicate session', () => {
  const replay = replayP25ResearchSignals({ signals:[{ signal:signal(), referencePrice:2500, markPrice:2520 }], initialCash:1_000_000, quantity:100 });
  const base = createResearchPaperLedger();
  const next = appendResearchPaperSession({ ledger:base, sessionDate:'2026-08-24', replayResult:replay, sourceEvaluationSha256:'eval-sha' });
  assert.equal(next.sessions.length, 1);
  assert.equal(verifyResearchPaperLedger(next), true);
  assert.throws(() => appendResearchPaperSession({ ledger:next, sessionDate:'2026-08-24', replayResult:replay }), /already exists/);
});

test('Shadow report blocks missing observations and never creates orders', () => {
  const replay = replayP25ResearchSignals({ signals:[{ signal:signal(), referencePrice:2500 }], initialCash:1_000_000, quantity:100 });
  const report = buildP25PaperShadowReport({ replayResult:replay, observations:{} });
  assert.equal(report.summary.simulatedFillCount, 1);
  assert.equal(report.summary.blockedCount, 1);
  assert.equal(report.rows[0].divergence, 'paper_fill_without_shadow_observation');
  assert.equal(report.executable, false);
  for (const value of Object.values(report.safety)) assert.equal(value, false);
});

test('Shadow report can mark a simulated fill feasible from observation only', () => {
  const replay = replayP25ResearchSignals({ signals:[{ signal:signal(), referencePrice:2500 }], initialCash:1_000_000, quantity:100 });
  const report = buildP25PaperShadowReport({ replayResult:replay, observations:{'sig-1':{dailyVolume:100000,availableAtPrice:1000,spreadPercent:0.2}} });
  assert.equal(report.summary.feasibleCount, 1);
  assert.equal(report.rows[0].shadowStatus, 'FEASIBLE');
});

test('Kill switch is healthy only when all write/trading capabilities are explicitly false', () => {
  const account = { initialCash:1_000_000, equity:990_000 };
  const healthy = evaluateP25PaperKillSwitch({ account, safety:SAFETY });
  assert.equal(healthy.tripped, false);
  const unsafe = evaluateP25PaperKillSwitch({ account, safety:{...SAFETY, liveTradingAllowed:true} });
  assert.equal(unsafe.tripped, true);
  assert.ok(unsafe.reasons.includes('LIVE_TRADING_NOT_DISABLED'));
});

test('Kill switch trips on excessive drawdown or Paper/Shadow divergence', () => {
  const drawdown = evaluateP25PaperKillSwitch({ account:{initialCash:1_000_000,equity:850_000}, safety:SAFETY, policy:{maximumDrawdownPct:10} });
  assert.ok(drawdown.reasons.includes('MAX_DRAWDOWN_EXCEEDED'));
  const shadowReport = { summary:{ simulatedFillCount:10, blockedCount:8 } };
  const divergence = evaluateP25PaperKillSwitch({ account:{initialCash:1_000_000,equity:1_000_000}, shadowReport, safety:SAFETY });
  assert.ok(divergence.reasons.includes('SHADOW_BLOCKED_SHARE_EXCEEDED'));
});
