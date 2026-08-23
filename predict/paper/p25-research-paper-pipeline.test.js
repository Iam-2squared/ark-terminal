import test from 'node:test';
import assert from 'node:assert/strict';
import { runP25ResearchPaperPipeline } from './p25-research-paper-pipeline.js';

function frozenLedger({ symbol='7203.T', date='2026-08-24', ts='2026-08-24T00:10:00.000Z', direction='LONG', signalDirection=1 } = {}) {
  return { frozenTrades:[{ symbol, sessionDate:date, entryTimestamp:ts, featureCutoff:ts, direction, signalDirection, modelId:'frozen-p25', confidence:0.7, probability:0.7, selectedFeatureFamily:'MOMENTUM', baseHorizonBars:12, artifactSha256:'artifact', selectedThreshold:0.6, variantMemberships:['DYNAMIC_30','DYNAMIC_40','DYNAMIC_50'], frozenBeforeOutcome:true, currentOutcomeUsed:false }] };
}

function session(date, price, markPrice) {
  const ts = `${date}T00:10:00.000Z`;
  return {
    sessionDate: date,
    frozenLedger: frozenLedger({ date, ts }),
    sessionBarsBySymbol: { '7203.T': [{ timestamp:ts, close:price }] },
    markPrices: { '7203.T': markPrice },
    lineageHeadSha256: `lineage-${date}`,
    sourceEvaluationSha256: `evaluation-${date}`,
    shadowObservations: { '7203.T': { spreadPercent:0.1, dailyVolume:1_000_000, availableAtPrice:100 } },
  };
}

test('runs multiple sessions on one cumulative research-only account and hash ledger', () => {
  const out = runP25ResearchPaperPipeline({
    sessions:[session('2026-08-24',1000,1010), session('2026-08-25',1020,1030)],
    initialCash:1_000_000,
    quantity:100,
    commissionPerFill:0,
    slippageBps:0,
  });
  assert.equal(out.mode, 'research_offline_only');
  assert.equal(out.executable, false);
  assert.equal(out.completedSessionCount, 2);
  assert.equal(out.halted, false);
  assert.equal(out.account.positions['7203.T'].quantity, 200);
  assert.equal(out.ledger.sessions.length, 2);
  assert.equal(out.ledger.sessions[1].previousHeadSha256, out.ledger.sessions[0].sessionSha256);
  for (const value of Object.values(out.safety)) assert.equal(value, false);
});

test('missing Shadow observation trips fail-closed kill switch and stops later sessions', () => {
  const first = session('2026-08-24',1000,1010);
  first.shadowObservations = {};
  const out = runP25ResearchPaperPipeline({ sessions:[first, session('2026-08-25',1020,1030)], killSwitchPolicy:{ maximumBlockedShadowShare:0 } });
  assert.equal(out.halted, true);
  assert.equal(out.completedSessionCount, 1);
  assert.ok(out.reports[0].killSwitch.reasons.includes('SHADOW_BLOCKED_SHARE_EXCEEDED'));
});

test('DOWN stays observation-only and cannot create a short position', () => {
  const date='2026-08-24', ts=`${date}T00:10:00.000Z`;
  const out = runP25ResearchPaperPipeline({ sessions:[{ sessionDate:date, frozenLedger:frozenLedger({date,ts,direction:'SHORT',signalDirection:-1}), sessionBarsBySymbol:{'7203.T':[{timestamp:ts,close:1000}]}, lineageHeadSha256:'lineage', shadowObservations:{} }] });
  assert.equal(Object.keys(out.account.positions).length,0);
  assert.equal(out.reports[0].replay.events[0].status,'observe_only');
});
