import test from 'node:test';
import assert from 'node:assert/strict';
import { runRealCaptureReplayOos, PHASE57_P19_SAFETY } from './phase57-real-capture-replay-oos.js';

function realRows(n = 40) {
  return Array.from({ length: n }, (_, i) => ({
    symbol: ['7203.T', '6758.T', '8306.T'][i % 3],
    sessionDate: `2026-08-${String(1 + (i % 5)).padStart(2, '0')}`,
    featureCutoff: new Date(Date.UTC(2026, 7, 1, 0, i, 0)).toISOString(),
    outcomeAt: new Date(Date.UTC(2026, 7, 1, 0, i, 30)).toISOString(),
    pointInTimeValid: true,
    label: i % 2,
    sourceMode: 'MARKETSPEED_II_RSS_READ_ONLY',
    features: {
      returnFromOpen: i % 2 ? 0.002 : -0.002,
      spreadBps: 4,
      bookImbalance: i % 2 ? 0.3 : -0.3,
      depthImbalance: i % 2 ? 0.2 : -0.2,
      aggressiveBuyRatio: i % 2 ? 0.7 : 0.3,
      tradeCount: 10 + i,
      volume: 1000 + i,
    },
    interactions: {},
  }));
}

test('blocks artifacts that do not prove real point-in-time source integrity', () => {
  const out = runRealCaptureReplayOos({ rows: realRows(10), syntheticDataUsed: true });
  assert.equal(out.status, 'REAL_CAPTURE_REPLAY_BLOCKED_BY_SOURCE_INTEGRITY');
  assert.equal(out.nestedReplay, null);
  assert.equal(out.edgeClaimAllowed, false);
});

test('passes only real rows into the predeclared replay gate and stays research-only', () => {
  const rows = realRows(60);
  rows.push({ ...rows[0], sourceMode: 'SYNTHETIC' });
  const out = runRealCaptureReplayOos({
    rows,
    syntheticDataUsed: false,
    futureUsedForFeatures: false,
    futureUsedOnlyForLabels: true,
  }, {
    protocol: { minTrainRows: 10, innerMinTrainRows: 5, minInnerSignals: 1 },
    readiness: { minRows: 1000, minSessions: 20, minSymbols: 3, minMicroCoverage: 0.8, minOuterSignals: 200, minOuterFolds: 3 },
  });
  assert.equal(out.rowCount, 60);
  assert.equal(out.status, 'REAL_CAPTURE_REPLAY_OOS_BLOCKED_BY_READINESS');
  assert.equal(out.nextStep, 'CONTINUE_READ_ONLY_INTRADAY_CAPTURE');
  for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) {
    assert.equal(out[key], false);
  }
  assert.equal(PHASE57_P19_SAFETY.executionAllowed, false);
});
