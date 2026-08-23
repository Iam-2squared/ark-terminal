import test from 'node:test';
import assert from 'node:assert/strict';
import { P25_RESEARCH_COST_POLICY_V1, validateP25ResearchCostPolicy } from './p25-research-cost-policy.js';
import { buildP25ResearchPaperScoreboard } from './p25-research-paper-scoreboard.js';

test('research cost policy is predeclared, non-executable, and includes sensitivity grid', () => {
  assert.equal(validateP25ResearchCostPolicy(), true);
  assert.equal(P25_RESEARCH_COST_POLICY_V1.slippageBps, 10);
  assert.deepEqual(P25_RESEARCH_COST_POLICY_V1.sensitivitySlippageBps, [0, 5, 10, 20]);
  assert.equal(P25_RESEARCH_COST_POLICY_V1.tunedFromProspectivePerformance, false);
  assert.equal(P25_RESEARCH_COST_POLICY_V1.brokerTariffClaimed, false);
  assert.equal(P25_RESEARCH_COST_POLICY_V1.executable, false);
});

test('scoreboard computes cumulative return and peak-to-trough maximum drawdown', () => {
  const state = {
    mode: 'research_offline_only', executable: false, assumptions: { slippageBps: 10 }, reports: [],
    ledger: {
      initialCash: 1_000_000,
      sessions: [
        { sessionDate: '2026-08-24', eventCount: 4, account: { equity: 1_020_000 } },
        { sessionDate: '2026-08-25', eventCount: 6, account: { equity: 990_000 } },
        { sessionDate: '2026-08-26', eventCount: 5, account: { equity: 1_030_000 } },
      ],
    },
  };
  const board = buildP25ResearchPaperScoreboard({ state });
  assert.equal(board.completedSessionCount, 3);
  assert.equal(board.totalReplayEvents, 15);
  assert.equal(board.endingEquity, 1_030_000);
  assert.equal(board.cumulativeReturnPct, 3);
  assert.ok(Math.abs(board.maximumDrawdownPct - (30_000 / 1_020_000 * 100)) < 1e-12);
  assert.equal(board.methodology.performanceConclusionAllowed, false);
  assert.equal(board.methodology.noDynamicNSelectionFromScoreboard, true);
  assert.equal(board.executable, false);
});

test('scoreboard fails closed on executable or malformed state', () => {
  assert.throws(() => buildP25ResearchPaperScoreboard({ state: { mode: 'research_offline_only', executable: true } }), /valid research-only/);
  assert.throws(() => buildP25ResearchPaperScoreboard({ state: { mode: 'research_offline_only', executable: false, ledger: { initialCash: 0, sessions: [] } } }), /initialCash/);
});
