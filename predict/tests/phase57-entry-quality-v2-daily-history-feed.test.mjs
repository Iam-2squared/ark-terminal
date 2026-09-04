import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ENTRY_V2_DAILY_HISTORY_POLICY,
  buildEntryV2PriorDailyHistoryFeed,
} from '../daytrade/phase57-entry-quality-v2-daily-history-feed.js';

function record(sessionDate, close, extra = {}) {
  return {
    kind: 'OHLCV',
    symbol: '7203.T',
    sessionDate,
    source: 'YAHOO_CHART',
    currency: 'JPY',
    open: close - 2,
    high: close + 5,
    low: close - 5,
    close,
    adjustedClose: close - 1,
    volume: 1000000,
    ...extra,
  };
}

test('daily history policy is research-only and does not use adjusted close as a feature', () => {
  assert.equal(ENTRY_V2_DAILY_HISTORY_POLICY.priorSessionOnly, true);
  assert.equal(ENTRY_V2_DAILY_HISTORY_POLICY.useAdjustedCloseAsFeature, false);
  assert.equal(ENTRY_V2_DAILY_HISTORY_POLICY.automaticPromotionAllowed, false);
});

test('builds a bounded prior-session daily prefix with deterministic lineage', () => {
  const result = buildEntryV2PriorDailyHistoryFeed({
    symbol: '7203.T',
    asOf: '2026-09-04T01:30:00.000Z',
    records: [
      record('2026-09-01', 1000),
      record('2026-09-02', 1010),
      record('2026-09-03', 1020),
    ],
    retentionBars: 2,
  });

  assert.equal(result.status, 'ENTRY_V2_PRIOR_DAILY_HISTORY_READY');
  assert.equal(result.bars.length, 2);
  assert.equal(result.bars[0].close, 1010);
  assert.equal(result.bars[1].close, 1020);
  assert.equal(result.lineage.decisionSessionDate, '2026-09-04');
  assert.equal(result.lineage.lastRetainedSessionDate, '2026-09-03');
  assert.equal(result.lineage.adjustedCloseFeatureBasis, false);
  assert.equal(result.lineage.adjustedCloseAuditAvailable, true);
  assert.match(result.sourceFingerprintSha256, /^[a-f0-9]{64}$/);
  assert.match(result.retainedBarsFingerprintSha256, /^[a-f0-9]{64}$/);
});

test('same-session daily records are rejected rather than silently filtered', () => {
  assert.throws(() => buildEntryV2PriorDailyHistoryFeed({
    symbol: '7203.T',
    asOf: '2026-09-04T01:30:00.000Z',
    records: [record('2026-09-03', 1020), record('2026-09-04', 1030)],
  }), /ENTRY_V2_DAILY_FEED_NOT_PRIOR_SESSION/);
});

test('future session records are rejected', () => {
  assert.throws(() => buildEntryV2PriorDailyHistoryFeed({
    symbol: '7203.T',
    asOf: '2026-09-04T01:30:00.000Z',
    records: [record('2026-09-05', 1030)],
  }), /ENTRY_V2_DAILY_FEED_NOT_PRIOR_SESSION/);
});

test('duplicate sessions and symbol mismatches fail closed', () => {
  assert.throws(() => buildEntryV2PriorDailyHistoryFeed({
    symbol: '7203.T',
    asOf: '2026-09-04T01:30:00.000Z',
    records: [record('2026-09-03', 1020), record('2026-09-03', 1021)],
  }), /ENTRY_V2_DAILY_FEED_DUPLICATE_SESSION/);

  assert.throws(() => buildEntryV2PriorDailyHistoryFeed({
    symbol: '7203.T',
    asOf: '2026-09-04T01:30:00.000Z',
    records: [record('2026-09-03', 1020, { symbol: '6758.T' })],
  }), /ENTRY_V2_DAILY_FEED_SYMBOL_MISMATCH/);
});

test('unsupported providers are rejected', () => {
  assert.throws(() => buildEntryV2PriorDailyHistoryFeed({
    symbol: '7203.T',
    asOf: '2026-09-04T01:30:00.000Z',
    records: [record('2026-09-03', 1020, { source: 'UNKNOWN' })],
  }), /ENTRY_V2_DAILY_FEED_SOURCE_NOT_ALLOWED/);
});
